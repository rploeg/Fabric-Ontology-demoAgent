"""Unified client for all Fabric API operations."""

import base64
import json
import time
from functools import wraps
from typing import Any, Callable, List, Optional

import requests
from azure.identity import DefaultAzureCredential

from fabric_demo.errors import FabricAPIError


def retry_on_transient(max_retries: int = 3, backoff: float = 2.0) -> Callable:
    """Decorator for retrying on transient errors."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except FabricAPIError as e:
                    last_error = e

                    # Don't retry client errors (4xx except 429)
                    if e.status_code and 400 <= e.status_code < 500 and e.status_code != 429:
                        raise

                    # Rate limited - use Retry-After
                    if e.status_code == 429:
                        wait = 60  # Default
                        if e.response:
                            wait = int(e.response.get("Retry-After", 60))
                        print(f"  ⚠️  Rate limited, waiting {wait}s...")
                        time.sleep(wait)
                        continue

                    # Transient error - exponential backoff
                    if attempt < max_retries:
                        wait = backoff**attempt
                        print(f"  ⚠️  Transient error, retry in {wait:.1f}s...")
                        time.sleep(wait)

            raise last_error  # type: ignore

        return wrapper

    return decorator


class FabricClient:
    """Unified client for all Fabric API operations."""

    BASE_URL = "https://api.fabric.microsoft.com/v1"
    ONELAKE_URL = "https://onelake.dfs.fabric.microsoft.com"

    def __init__(self, workspace_id: str):
        """Initialize client with workspace ID.

        Args:
            workspace_id: The Fabric workspace ID (GUID)
        """
        self.workspace_id = workspace_id
        self.credential = DefaultAzureCredential()
        self._fabric_token: Optional[str] = None
        self._fabric_token_expiry: float = 0
        self._storage_token: Optional[str] = None
        self._storage_token_expiry: float = 0

    # --- Authentication ---

    def _get_fabric_token(self) -> str:
        """Get Fabric API token with caching."""
        if self._fabric_token and time.time() < self._fabric_token_expiry - 60:
            return self._fabric_token

        token = self.credential.get_token("https://api.fabric.microsoft.com/.default")
        self._fabric_token = token.token
        self._fabric_token_expiry = token.expires_on
        return self._fabric_token

    def _get_storage_token(self) -> str:
        """Get OneLake storage token with caching."""
        if self._storage_token and time.time() < self._storage_token_expiry - 60:
            return self._storage_token

        token = self.credential.get_token("https://storage.azure.com/.default")
        self._storage_token = token.token
        self._storage_token_expiry = token.expires_on
        return self._storage_token

    def _headers(self) -> dict:
        """Get headers for Fabric API calls."""
        return {
            "Authorization": f"Bearer {self._get_fabric_token()}",
            "Content-Type": "application/json",
        }

    def _onelake_headers(self) -> dict:
        """Get headers for OneLake operations."""
        return {
            "Authorization": f"Bearer {self._get_storage_token()}",
            "Content-Type": "application/octet-stream",
        }

    # --- HTTP Helpers ---

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make request with error handling."""
        resp = requests.request(method, url, headers=self._headers(), **kwargs)

        if resp.status_code >= 400:
            self._handle_error(resp)

        return resp

    def _handle_error(self, resp: requests.Response) -> None:
        """Handle API errors."""
        error_body = None
        try:
            error_body = resp.json()
            message = error_body.get("error", {}).get("message", resp.text)
        except Exception:
            message = resp.text

        raise FabricAPIError(message, resp.status_code, error_body)

    def _poll_lro(self, operation_url: str, timeout: int = 300) -> dict:
        """Poll long-running operation until completion.

        Args:
            operation_url: The URL to poll for operation status
            timeout: Maximum seconds to wait

        Returns:
            The final operation result

        Raises:
            FabricAPIError: If operation fails
            TimeoutError: If operation times out
        """
        start = time.time()
        while time.time() - start < timeout:
            resp = requests.get(operation_url, headers=self._headers())
            if resp.status_code >= 400:
                self._handle_error(resp)

            result = resp.json()
            status = result.get("status", "").lower()

            if status == "succeeded":
                return result
            elif status in ("failed", "cancelled"):
                error_msg = result.get("error", {}).get("message", str(result))
                raise FabricAPIError(f"LRO {status}: {error_msg}")

            # Still running - wait and retry
            retry_after = int(resp.headers.get("Retry-After", 5))
            time.sleep(min(retry_after, 30))

        raise TimeoutError(f"LRO timed out after {timeout}s")

    # --- Lakehouse Operations ---

    @retry_on_transient()
    def list_lakehouses(self) -> List[dict]:
        """List all lakehouses in workspace."""
        url = f"{self.BASE_URL}/workspaces/{self.workspace_id}/lakehouses"
        resp = self._request("GET", url)
        return resp.json().get("value", [])

    def find_lakehouse(self, name: str) -> Optional[str]:
        """Find lakehouse by name, return ID or None."""
        for lh in self.list_lakehouses():
            if lh["displayName"] == name:
                return lh["id"]
        return None

    @retry_on_transient()
    def create_lakehouse(self, name: str) -> str:
        """Create lakehouse, return ID.

        Args:
            name: Display name for the lakehouse

        Returns:
            The lakehouse ID
        """
        # Check if exists (idempotent)
        existing = self.find_lakehouse(name)
        if existing:
            return existing

        url = f"{self.BASE_URL}/workspaces/{self.workspace_id}/lakehouses"
        resp = self._request("POST", url, json={"displayName": name})

        if resp.status_code == 202:
            # Long-running operation
            result = self._poll_lro(resp.headers["Location"])
            return result.get("id") or self.find_lakehouse(name)  # type: ignore

        return resp.json()["id"]

    @retry_on_transient()
    def delete_lakehouse(self, lakehouse_id: str) -> None:
        """Delete a lakehouse by ID."""
        url = f"{self.BASE_URL}/workspaces/{self.workspace_id}/lakehouses/{lakehouse_id}"
        self._request("DELETE", url)

    @retry_on_transient(max_retries=5)
    def upload_file(self, lakehouse_id: str, remote_path: str, content: bytes) -> None:
        """Upload file to OneLake.

        Args:
            lakehouse_id: The lakehouse ID
            remote_path: Path in OneLake (e.g., "Files/data.csv")
            content: File content as bytes
        """
        base_url = f"{self.ONELAKE_URL}/{self.workspace_id}/{lakehouse_id}/{remote_path}"
        headers = self._onelake_headers()
        headers["Content-Length"] = str(len(content))

        # Step 1: Create file resource
        create_url = f"{base_url}?resource=file"
        resp = requests.put(create_url, headers=headers)
        if resp.status_code >= 400 and resp.status_code != 409:  # 409 = already exists
            raise FabricAPIError(f"Upload create failed: {resp.text}", resp.status_code)

        # Step 2: Append content
        append_url = f"{base_url}?action=append&position=0"
        resp = requests.patch(append_url, headers=headers, data=content)
        if resp.status_code >= 400:
            raise FabricAPIError(f"Upload append failed: {resp.text}", resp.status_code)

        # Step 3: Flush to finalize
        flush_url = f"{base_url}?action=flush&position={len(content)}"
        resp = requests.patch(flush_url, headers=headers)
        if resp.status_code >= 400:
            raise FabricAPIError(f"Upload flush failed: {resp.text}", resp.status_code)

    @retry_on_transient()
    def load_table(self, lakehouse_id: str, table_name: str, file_path: str) -> None:
        """Load CSV file into Delta table.

        Args:
            lakehouse_id: The lakehouse ID
            table_name: Name for the Delta table
            file_path: Relative path to CSV in OneLake (e.g., "Files/data.csv")
        """
        url = f"{self.BASE_URL}/workspaces/{self.workspace_id}/lakehouses/{lakehouse_id}/tables/{table_name}/load"

        body = {
            "relativePath": file_path,
            "pathType": "File",
            "mode": "Overwrite",
            "formatOptions": {"format": "Csv", "header": True, "delimiter": ","},
        }

        resp = self._request("POST", url, json=body)
        if resp.status_code == 202:
            self._poll_lro(resp.headers["Location"])

    # --- Eventhouse Operations ---

    @retry_on_transient()
    def list_eventhouses(self) -> List[dict]:
        """List all eventhouses in workspace."""
        url = f"{self.BASE_URL}/workspaces/{self.workspace_id}/eventhouses"
        resp = self._request("GET", url)
        return resp.json().get("value", [])

    def find_eventhouse(self, name: str) -> Optional[str]:
        """Find eventhouse by name, return ID or None."""
        for eh in self.list_eventhouses():
            if eh["displayName"] == name:
                return eh["id"]
        return None

    @retry_on_transient()
    def create_eventhouse(self, name: str) -> str:
        """Create eventhouse, return ID.

        Args:
            name: Display name for the eventhouse

        Returns:
            The eventhouse ID
        """
        existing = self.find_eventhouse(name)
        if existing:
            return existing

        url = f"{self.BASE_URL}/workspaces/{self.workspace_id}/eventhouses"
        resp = self._request("POST", url, json={"displayName": name})

        if resp.status_code == 202:
            # Eventhouses can take 30-60s to create
            result = self._poll_lro(resp.headers["Location"], timeout=120)
            return result.get("id") or self.find_eventhouse(name)  # type: ignore

        return resp.json()["id"]

    @retry_on_transient()
    def delete_eventhouse(self, eventhouse_id: str) -> None:
        """Delete an eventhouse by ID."""
        url = f"{self.BASE_URL}/workspaces/{self.workspace_id}/eventhouses/{eventhouse_id}"
        self._request("DELETE", url)

    # --- KQL Database Operations ---

    @retry_on_transient()
    def list_kql_databases(self) -> List[dict]:
        """List all KQL databases in workspace."""
        url = f"{self.BASE_URL}/workspaces/{self.workspace_id}/kqlDatabases"
        resp = self._request("GET", url)
        return resp.json().get("value", [])

    def find_kql_database(self, name: str) -> Optional[str]:
        """Find KQL database by name, return ID or None."""
        for db in self.list_kql_databases():
            if db["displayName"] == name:
                return db["id"]
        return None

    @retry_on_transient()
    def create_kql_database(self, name: str, eventhouse_id: str) -> str:
        """Create KQL database under eventhouse.

        Args:
            name: Display name for the KQL database
            eventhouse_id: Parent eventhouse ID

        Returns:
            The KQL database ID
        """
        existing = self.find_kql_database(name)
        if existing:
            return existing

        url = f"{self.BASE_URL}/workspaces/{self.workspace_id}/kqlDatabases"
        body = {
            "displayName": name,
            "creationPayload": {
                "databaseType": "ReadWrite",
                "parentEventhouseItemId": eventhouse_id,
            },
        }

        resp = self._request("POST", url, json=body)
        if resp.status_code == 202:
            result = self._poll_lro(resp.headers["Location"])
            return result.get("id") or self.find_kql_database(name)  # type: ignore

        return resp.json()["id"]

    @retry_on_transient()
    def delete_kql_database(self, kql_database_id: str) -> None:
        """Delete a KQL database by ID."""
        url = f"{self.BASE_URL}/workspaces/{self.workspace_id}/kqlDatabases/{kql_database_id}"
        self._request("DELETE", url)

    # --- Ontology Operations ---

    @retry_on_transient()
    def list_ontologies(self) -> List[dict]:
        """List all ontologies in workspace."""
        url = f"{self.BASE_URL}/workspaces/{self.workspace_id}/ontologies"
        resp = self._request("GET", url)
        return resp.json().get("value", [])

    def find_ontology(self, name: str) -> Optional[str]:
        """Find ontology by name, return ID or None."""
        for ont in self.list_ontologies():
            if ont["displayName"] == name:
                return ont["id"]
        return None

    @retry_on_transient()
    def create_ontology(self, name: str, ttl_content: str) -> str:
        """Create ontology with TTL definition.

        Args:
            name: Display name for the ontology
            ttl_content: The TTL ontology definition content

        Returns:
            The ontology ID
        """
        existing = self.find_ontology(name)
        if existing:
            return existing

        url = f"{self.BASE_URL}/workspaces/{self.workspace_id}/ontologies"
        body = {
            "displayName": name,
            "definition": {
                "parts": [
                    {
                        "path": "ontology.ttl",
                        "payload": base64.b64encode(ttl_content.encode()).decode(),
                        "payloadType": "InlineBase64",
                    }
                ]
            },
        }

        resp = self._request("POST", url, json=body)
        if resp.status_code == 202:
            result = self._poll_lro(resp.headers["Location"])
            return result.get("id") or self.find_ontology(name)  # type: ignore

        return resp.json()["id"]

    @retry_on_transient()
    def bind_ontology(self, ontology_id: str, ttl_content: str, bindings: dict) -> None:
        """Update ontology with data bindings.

        Args:
            ontology_id: The ontology ID
            ttl_content: The TTL ontology definition content
            bindings: The bindings configuration dict
        """
        url = f"{self.BASE_URL}/workspaces/{self.workspace_id}/ontologies/{ontology_id}/updateDefinition"

        body = {
            "definition": {
                "parts": [
                    {
                        "path": "ontology.ttl",
                        "payload": base64.b64encode(ttl_content.encode()).decode(),
                        "payloadType": "InlineBase64",
                    },
                    {
                        "path": "bindings.json",
                        "payload": base64.b64encode(json.dumps(bindings).encode()).decode(),
                        "payloadType": "InlineBase64",
                    },
                ]
            }
        }

        resp = self._request("POST", url, json=body)
        if resp.status_code == 202:
            self._poll_lro(resp.headers["Location"])

    @retry_on_transient()
    def refresh_ontology_graph(self, ontology_id: str) -> None:
        """Trigger graph refresh for ontology.

        Args:
            ontology_id: The ontology ID
        """
        url = f"{self.BASE_URL}/workspaces/{self.workspace_id}/ontologies/{ontology_id}/refreshGraph"
        resp = self._request("POST", url)
        if resp.status_code == 202:
            # Graph refresh can take a while
            self._poll_lro(resp.headers["Location"], timeout=600)

    @retry_on_transient()
    def delete_ontology(self, ontology_id: str) -> None:
        """Delete an ontology by ID."""
        url = f"{self.BASE_URL}/workspaces/{self.workspace_id}/ontologies/{ontology_id}"
        self._request("DELETE", url)
