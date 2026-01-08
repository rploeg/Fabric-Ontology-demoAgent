"""
Base Fabric REST API client.

Handles authentication, rate limiting, retries, and long-running operations.

Note on Ontology Operations:
    This client provides low-level HTTP methods for Fabric Ontology API operations.
    For building ontology definitions, the Fabric Ontology SDK is recommended:
    
    - Use ``fabric_ontology.builders.OntologyBuilder`` for creating definitions
    - Use ``fabric_ontology.validation.OntologyValidator`` for validation
    - Use ``demo_automation.binding.SDKBindingBridge`` for binding configuration
    
    The ontology methods in this client (create_ontology, update_ontology_definition, etc.)
    are still used by the orchestrator for HTTP transport but SDK builders should be
    used to construct the definition payloads.
"""

import logging
import time
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass

import requests
from azure.identity import (
    DefaultAzureCredential,
    InteractiveBrowserCredential,
    ClientSecretCredential,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from demo_automation.core.errors import (
    FabricAPIError,
    RateLimitError,
    LROTimeoutError,
    AuthenticationError,
    ResourceExistsError,
    ResourceNotFoundError,
)


logger = logging.getLogger(__name__)


FABRIC_BASE_URL = "https://api.fabric.microsoft.com/v1"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"


@dataclass
class RateLimitConfig:
    """Rate limiter configuration."""

    enabled: bool = True
    requests_per_minute: int = 30
    burst: int = 10


class TokenBucketRateLimiter:
    """Simple token bucket rate limiter."""

    def __init__(self, rate: float, per: float = 60.0, burst: int = 10):
        self.rate = rate
        self.per = per
        self.burst = burst
        self.tokens = burst
        self.last_refill = time.monotonic()

    def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens, blocking if necessary."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.burst, self.tokens + elapsed * (self.rate / self.per))
        self.last_refill = now

        if self.tokens < tokens:
            sleep_time = (tokens - self.tokens) * (self.per / self.rate)
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
            self.tokens = 0
        else:
            self.tokens -= tokens


class FabricClient:
    """
    Base client for Microsoft Fabric REST APIs.

    Handles:
    - Authentication (Interactive, Service Principal, Managed Identity)
    - Rate limiting
    - Automatic retries with exponential backoff
    - Long-running operation (LRO) polling
    """

    def __init__(
        self,
        workspace_id: str,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        use_interactive_auth: bool = True,
        rate_limit_config: Optional[RateLimitConfig] = None,
    ):
        """
        Initialize the Fabric client.

        Args:
            workspace_id: The Fabric workspace ID (GUID)
            tenant_id: Azure AD tenant ID (optional)
            client_id: Service principal client ID (optional)
            client_secret: Service principal client secret (optional)
            use_interactive_auth: Use interactive browser auth if no SP credentials
            rate_limit_config: Rate limiting configuration
        """
        self.workspace_id = workspace_id
        self.tenant_id = tenant_id
        self._token: Optional[str] = None
        self._token_expiry: float = 0

        # Setup credential
        if client_id and client_secret and tenant_id:
            self._credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
            logger.info("Using Service Principal authentication")
        elif use_interactive_auth:
            self._credential = InteractiveBrowserCredential(tenant_id=tenant_id)
            logger.info("Using Interactive Browser authentication")
        else:
            self._credential = DefaultAzureCredential()
            logger.info("Using Default Azure Credential chain")

        # Setup rate limiter
        self._rate_limit_config = rate_limit_config or RateLimitConfig()
        if self._rate_limit_config.enabled:
            self._rate_limiter = TokenBucketRateLimiter(
                rate=self._rate_limit_config.requests_per_minute,
                per=60.0,
                burst=self._rate_limit_config.burst,
            )
        else:
            self._rate_limiter = None

        # Session for connection pooling
        self._session = requests.Session()

    def _get_token(self) -> str:
        """Get a valid access token, refreshing if needed."""
        now = time.time()
        if self._token and now < self._token_expiry - 60:  # 60s buffer
            return self._token

        try:
            token = self._credential.get_token(FABRIC_SCOPE)
            self._token = token.token
            self._token_expiry = token.expires_on
            return self._token
        except Exception as e:
            raise AuthenticationError(f"Failed to acquire token: {e}", cause=e)

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((requests.exceptions.ConnectionError, RateLimitError)),
        reraise=True,
    )
    def _make_request(
        self,
        method: str,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: int = 60,
    ) -> requests.Response:
        """
        Make an HTTP request with rate limiting and retries.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            url: Full URL
            json: JSON body (optional)
            params: Query parameters (optional)
            timeout: Request timeout in seconds

        Returns:
            Response object
        """
        if self._rate_limiter:
            self._rate_limiter.acquire()

        logger.debug(f"Request: {method} {url}")

        response = self._session.request(
            method=method,
            url=url,
            headers=self._get_headers(),
            json=json,
            params=params,
            timeout=timeout,
        )

        # Handle rate limiting
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 30))
            logger.warning(f"Rate limited. Retry after {retry_after}s")
            raise RateLimitError(
                "Rate limited by Fabric API",
                retry_after=retry_after,
            )

        return response

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle API response and convert to dict.

        Args:
            response: HTTP response

        Returns:
            Response body as dict

        Raises:
            FabricAPIError: If the response indicates an error
        """
        request_id = response.headers.get("x-ms-request-id", "")

        if response.status_code == 404:
            try:
                error_body = response.json()
                error_message = error_body.get("message", "Resource not found")
            except Exception:
                error_message = "Resource not found"
            raise ResourceNotFoundError(
                error_message,
                details={"request_id": request_id},
            )

        if response.status_code == 409:
            try:
                error_body = response.json()
                error_code = error_body.get("errorCode", "")
                if "ItemDisplayNameAlreadyInUse" in error_code:
                    raise ResourceExistsError(
                        f"Resource already exists: {error_body.get('message', '')}",
                        details={"request_id": request_id},
                    )
            except ResourceExistsError:
                raise
            except Exception:
                pass

        if response.status_code >= 400:
            try:
                error_body = response.json()
                error_message = error_body.get("message", response.text)
                error_code = error_body.get("errorCode", "")
            except Exception:
                error_message = response.text
                error_code = ""

            raise FabricAPIError(
                error_message,
                status_code=response.status_code,
                error_code=error_code,
                request_id=request_id,
            )

        if response.status_code == 204:
            return {}

        try:
            return response.json()
        except Exception:
            return {}

    def _wait_for_lro(
        self,
        operation_url: str,
        timeout_seconds: int = 600,
        poll_interval: int = 5,
        progress_callback: Optional[Callable[[str, float], None]] = None,
        fetch_result: bool = False,
    ) -> Dict[str, Any]:
        """
        Wait for a long-running operation to complete.

        Args:
            operation_url: URL to poll for operation status
            timeout_seconds: Maximum time to wait
            poll_interval: Seconds between polls
            progress_callback: Optional callback(status, progress_percent)
            fetch_result: Whether to fetch result from result URL after success

        Returns:
            Final operation result (or fetched result if fetch_result=True)

        Raises:
            LROTimeoutError: If operation times out
            FabricAPIError: If operation fails
        """
        start_time = time.time()
        last_response = None

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                raise LROTimeoutError(
                    f"Operation timed out after {elapsed:.1f}s",
                    elapsed_seconds=elapsed,
                )

            response = self._make_request("GET", operation_url)
            last_response = response
            result = self._handle_response(response)

            status = result.get("status", "").lower()
            percent_complete = result.get("percentComplete", 0)

            logger.debug(f"LRO status: {status}, progress: {percent_complete}%")

            if progress_callback:
                progress_callback(status, percent_complete)

            if status == "succeeded":
                if fetch_result:
                    # Try to fetch actual result from result URL
                    fetched = self._fetch_lro_result(operation_url, last_response, result)
                    if fetched:
                        return fetched
                return result
            elif status == "failed":
                error = result.get("error", {})
                raise FabricAPIError(
                    f"Operation failed: {error.get('message', 'Unknown error')}",
                    error_code=error.get("code", ""),
                )
            elif status in ("cancelled", "canceled"):
                raise FabricAPIError("Operation was cancelled")

            # Get retry-after from response or use default
            retry_after = int(response.headers.get("Retry-After", poll_interval))
            time.sleep(retry_after)

    def _fetch_lro_result(
        self,
        operation_url: str,
        response: Optional[requests.Response],
        fallback_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Fetch actual result from result URL after LRO success.

        Args:
            operation_url: Original operation URL
            response: The success response
            fallback_result: Fallback if fetch fails

        Returns:
            Fetched result or fallback
        """
        # Try Location header first
        if response and response.headers.get("Location"):
            result_url = response.headers.get("Location")
            logger.debug(f"Fetching result from Location header: {result_url}")
            try:
                result_response = self._make_request("GET", result_url)
                if result_response.status_code == 200:
                    return self._handle_response(result_response)
            except Exception as e:
                logger.warning(f"Failed to fetch from Location: {e}")

        # Try appending /result to operation URL
        result_url = f"{operation_url}/result"
        logger.debug(f"Fetching result from: {result_url}")
        try:
            result_response = self._make_request("GET", result_url)
            if result_response.status_code == 200:
                return self._handle_response(result_response)
        except Exception as e:
            logger.warning(f"Failed to fetch from result URL: {e}")

        return fallback_result

    def _build_url(self, path: str) -> str:
        """Build full API URL with workspace context."""
        if path.startswith("http"):
            return path
        return f"{FABRIC_BASE_URL}/workspaces/{self.workspace_id}/{path.lstrip('/')}"

    # --- Generic Item Operations ---

    def list_items(self, item_type: str) -> List[Dict[str, Any]]:
        """
        List all items of a specific type in the workspace.

        Args:
            item_type: Type of items (lakehouses, eventhouses, ontologies, etc.)

        Returns:
            List of items
        """
        url = self._build_url(item_type)
        response = self._make_request("GET", url)
        result = self._handle_response(response)
        return result.get("value", [])

    def get_item(self, item_type: str, item_id: str) -> Dict[str, Any]:
        """
        Get a specific item by ID.

        Args:
            item_type: Type of item
            item_id: Item ID (GUID)

        Returns:
            Item details
        """
        url = self._build_url(f"{item_type}/{item_id}")
        response = self._make_request("GET", url)
        return self._handle_response(response)

    def find_item_by_name(
        self, item_type: str, display_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find an item by display name.

        Args:
            item_type: Type of item
            display_name: Display name to search for

        Returns:
            Item if found, None otherwise
        """
        items = self.list_items(item_type)
        for item in items:
            if item.get("displayName") == display_name:
                return item
        return None

    def create_item(
        self,
        item_type: str,
        display_name: str,
        description: str = "",
        definition: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 300,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new item (handles LRO if needed).

        Args:
            item_type: Type of item to create
            display_name: Display name for the item
            description: Optional description
            definition: Optional definition payload
            timeout_seconds: Timeout for LRO
            progress_callback: Optional progress callback

        Returns:
            Created item details
        """
        url = self._build_url(item_type)

        body: Dict[str, Any] = {"displayName": display_name}
        if description:
            body["description"] = description
        if definition:
            body["definition"] = definition

        response = self._make_request("POST", url, json=body)

        # Handle LRO (202 Accepted)
        if response.status_code == 202:
            operation_url = response.headers.get("Location")
            if operation_url:
                logger.info(f"Waiting for {item_type} creation LRO...")
                self._wait_for_lro(
                    operation_url,
                    timeout_seconds=timeout_seconds,
                    progress_callback=progress_callback,
                )
                # Re-fetch the item
                retry_after = int(response.headers.get("Retry-After", 2))
                time.sleep(retry_after)
                return self.find_item_by_name(item_type, display_name) or {}

        return self._handle_response(response)

    def delete_item(
        self,
        item_type: str,
        item_id: str,
        timeout_seconds: int = 120,
    ) -> None:
        """
        Delete an item by ID.

        Args:
            item_type: Type of item
            item_id: Item ID (GUID)
            timeout_seconds: Timeout for LRO
        """
        url = self._build_url(f"{item_type}/{item_id}")
        response = self._make_request("DELETE", url)

        # Handle LRO
        if response.status_code == 202:
            operation_url = response.headers.get("Location")
            if operation_url:
                self._wait_for_lro(operation_url, timeout_seconds=timeout_seconds)
        elif response.status_code not in (200, 204):
            self._handle_response(response)

    # --- Lakehouse Operations ---

    def list_lakehouses(self) -> List[Dict[str, Any]]:
        """List all lakehouses in the workspace."""
        return self.list_items("lakehouses")

    def get_lakehouse(self, lakehouse_id: str) -> Dict[str, Any]:
        """Get lakehouse by ID with properties."""
        return self.get_item("lakehouses", lakehouse_id)

    def find_lakehouse_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find lakehouse by display name."""
        return self.find_item_by_name("lakehouses", name)

    def create_lakehouse(
        self,
        display_name: str,
        description: str = "",
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new lakehouse.
        
        Note: This creates a lakehouse WITHOUT schemas enabled (Public Preview).
        Per Microsoft documentation for Ontology tutorials, the "Lakehouse schemas"
        checkbox should NOT be enabled. By not passing creationPayload with
        enableSchemas=true, we ensure the lakehouse is created without schema support.
        See: https://learn.microsoft.com/en-us/fabric/iq/ontology/tutorial-0-introduction
        """
        logger.info(f"Creating lakehouse: {display_name}")
        return self.create_item(
            "lakehouses",
            display_name,
            description,
            progress_callback=progress_callback,
        )

    def delete_lakehouse(self, lakehouse_id: str) -> None:
        """Delete a lakehouse."""
        logger.info(f"Deleting lakehouse: {lakehouse_id}")
        self.delete_item("lakehouses", lakehouse_id)

    # --- Eventhouse Operations ---

    def list_eventhouses(self) -> List[Dict[str, Any]]:
        """List all eventhouses in the workspace."""
        return self.list_items("eventhouses")

    def get_eventhouse(self, eventhouse_id: str) -> Dict[str, Any]:
        """Get eventhouse by ID."""
        return self.get_item("eventhouses", eventhouse_id)

    def find_eventhouse_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find eventhouse by display name."""
        return self.find_item_by_name("eventhouses", name)

    def create_eventhouse(
        self,
        display_name: str,
        description: str = "",
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """Create a new eventhouse."""
        logger.info(f"Creating eventhouse: {display_name}")
        return self.create_item(
            "eventhouses",
            display_name,
            description,
            progress_callback=progress_callback,
        )

    def delete_eventhouse(self, eventhouse_id: str) -> None:
        """Delete an eventhouse."""
        logger.info(f"Deleting eventhouse: {eventhouse_id}")
        self.delete_item("eventhouses", eventhouse_id)

    # --- KQL Database Operations ---

    def list_kql_databases(self) -> List[Dict[str, Any]]:
        """List all KQL databases in the workspace."""
        return self.list_items("kqlDatabases")

    def get_kql_database(self, database_id: str) -> Dict[str, Any]:
        """Get KQL database by ID."""
        return self.get_item("kqlDatabases", database_id)

    def find_kql_database_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find KQL database by display name."""
        return self.find_item_by_name("kqlDatabases", name)

    # --- Ontology Operations ---

    def list_ontologies(self) -> List[Dict[str, Any]]:
        """List all ontologies in the workspace."""
        return self.list_items("ontologies")

    def get_ontology(self, ontology_id: str) -> Dict[str, Any]:
        """Get ontology by ID."""
        return self.get_item("ontologies", ontology_id)

    def find_ontology_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find ontology by display name."""
        return self.find_item_by_name("ontologies", name)

    def create_ontology(
        self,
        display_name: str,
        description: str = "",
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """Create a new ontology."""
        logger.info(f"Creating ontology: {display_name}")
        return self.create_item(
            "ontologies",
            display_name,
            description,
            progress_callback=progress_callback,
        )

    def delete_ontology(self, ontology_id: str) -> None:
        """Delete an ontology."""
        logger.info(f"Deleting ontology: {ontology_id}")
        self.delete_item("ontologies", ontology_id)

    def get_ontology_definition(
        self,
        ontology_id: str,
        timeout_seconds: int = 300,
    ) -> Dict[str, Any]:
        """
        Get the ontology definition (LRO).

        Args:
            ontology_id: Ontology ID
            timeout_seconds: Timeout for LRO

        Returns:
            Ontology definition with parts
        """
        url = self._build_url(f"ontologies/{ontology_id}/getDefinition")
        response = self._make_request("POST", url)

        if response.status_code == 202:
            operation_url = response.headers.get("Location")
            if operation_url:
                result = self._wait_for_lro(
                    operation_url, 
                    timeout_seconds=timeout_seconds,
                    fetch_result=True,  # Fetch actual definition from result URL
                )
                # Handle different response formats
                if "definition" in result:
                    return result["definition"]
                elif "parts" in result:
                    return result
                else:
                    logger.warning(
                        f"No definition found in result. Keys: {list(result.keys())}"
                    )
                    return {"parts": []}

        return self._handle_response(response)

    def update_ontology_definition(
        self,
        ontology_id: str,
        definition: Dict[str, Any],
        timeout_seconds: int = 600,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Update the ontology definition (LRO).

        Args:
            ontology_id: Ontology ID
            definition: New definition with parts
            timeout_seconds: Timeout for LRO
            progress_callback: Optional progress callback

        Returns:
            Update result
        """
        url = self._build_url(f"ontologies/{ontology_id}/updateDefinition")
        response = self._make_request("POST", url, json={"definition": definition})

        if response.status_code == 202:
            operation_url = response.headers.get("Location")
            if operation_url:
                return self._wait_for_lro(
                    operation_url,
                    timeout_seconds=timeout_seconds,
                    progress_callback=progress_callback,
                )

        return self._handle_response(response)

    # --- Graph Operations ---

    def list_graphs(self) -> List[Dict[str, Any]]:
        """
        List all graph items in the workspace.
        
        Note: This searches for GraphQL API items. The Graph in Microsoft Fabric
        item type (used by ontology) may have a different endpoint or may not
        be accessible via public API yet.
        """
        return self.list_items("graphqlApis")

    def find_graph_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find graph item by display name."""
        return self.find_item_by_name("graphqlApis", name)

    def find_ontology_graph(
        self,
        ontology_name: str,
        ontology_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Find the graph item associated with an ontology.
        
        The graph item is typically named: {OntologyName}_graph_{ontologyIdWithoutDashes}
        
        Note: The Graph in Microsoft Fabric item type (associated with ontology)
        may not be accessible via the public REST API. The graph is managed by
        Fabric internally and can be refreshed via the Fabric portal.
        
        Args:
            ontology_name: Name of the ontology
            ontology_id: ID of the ontology (GUID)
            
        Returns:
            Graph item if found, None otherwise
        """
        # Graph name format: {OntologyName}_graph_{ontologyIdWithoutDashes}
        ontology_id_clean = ontology_id.replace("-", "")
        expected_graph_name = f"{ontology_name}_graph_{ontology_id_clean}"
        
        logger.debug(f"Looking for graph item: {expected_graph_name}")
        
        # Try exact match first with GraphQL APIs
        graph = self.find_graph_by_name(expected_graph_name)
        if graph:
            return graph
        
        # Try partial match if exact match fails
        graphs = self.list_graphs()
        for g in graphs:
            display_name = g.get("displayName", "")
            # Check if it matches the ontology pattern
            if display_name.startswith(f"{ontology_name}_graph_"):
                logger.debug(f"Found graph by partial match: {display_name}")
                return g
        
        # Note: The Graph in Microsoft Fabric item type might not be accessible
        # via REST API. The graph for an ontology is managed internally by Fabric
        # and can be refreshed manually from the Fabric portal.
        logger.info(
            f"Graph item '{expected_graph_name}' not found via API. "
            f"The graph may need to be refreshed manually from the Fabric portal."
        )
        
        return None

    def refresh_graph(
        self,
        graph_id: str,
        timeout_seconds: int = 600,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Trigger an on-demand refresh job for a graph item.
        
        This uses the Fabric Job Scheduler API to run a refresh job.
        
        Args:
            graph_id: Graph item ID (GUID)
            timeout_seconds: Timeout for the refresh job
            progress_callback: Optional progress callback
            
        Returns:
            Job result or status
        """
        logger.info(f"Triggering refresh for graph: {graph_id}")
        
        # Use the job scheduler API to run on-demand refresh
        # POST /workspaces/{workspaceId}/items/{itemId}/jobs/{jobType}/instances
        url = self._build_url(f"items/{graph_id}/jobs/DefaultJob/instances")
        
        response = self._make_request("POST", url)
        
        if response.status_code == 202:
            # Job accepted, get the location header for status tracking
            operation_url = response.headers.get("Location")
            retry_after = int(response.headers.get("Retry-After", 60))
            
            if operation_url:
                logger.info(f"Graph refresh job started, tracking at: {operation_url}")
                return self._wait_for_lro(
                    operation_url,
                    timeout_seconds=timeout_seconds,
                    progress_callback=progress_callback,
                    poll_interval=retry_after,
                )
            else:
                return {"status": "accepted", "message": "Refresh job started"}
        
        return self._handle_response(response)

    def close(self) -> None:
        """Close the client and release resources."""
        self._session.close()

    def __enter__(self) -> "FabricClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
