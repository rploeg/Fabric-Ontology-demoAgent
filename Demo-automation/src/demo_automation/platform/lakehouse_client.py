"""
Lakehouse Client for Fabric Lakehouse operations.

Includes the optimized Load to Tables API for CSV→Delta conversion
without requiring Spark compute.
"""

import logging
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

from .fabric_client import FabricClient, FABRIC_BASE_URL
from demo_automation.core.errors import FabricAPIError, LROTimeoutError


logger = logging.getLogger(__name__)


class LoadMode(Enum):
    """Mode for loading data into tables."""
    OVERWRITE = "overwrite"
    APPEND = "append"


class LoadPathType(Enum):
    """Type of path for load operation."""
    FILE = "File"
    FOLDER = "Folder"


class OperationStatus(Enum):
    """Status of a load operation."""
    NOT_STARTED = 1
    RUNNING = 2
    SUCCESS = 3
    FAILED = 4


@dataclass
class LoadTableRequest:
    """Configuration for Load to Tables API."""
    relative_path: str  # e.g., "Files/DimProduct.csv"
    path_type: LoadPathType = LoadPathType.FILE
    mode: LoadMode = LoadMode.OVERWRITE
    header: bool = True
    delimiter: str = ","
    file_format: str = "CSV"  # "CSV" or "Parquet"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API request body."""
        result = {
            "relativePath": self.relative_path,
            "pathType": self.path_type.value,
            "mode": self.mode.value,
        }
        
        # Add formatOptions for CSV files
        if self.file_format == "CSV":
            result["formatOptions"] = {
                "format": self.file_format,
                "header": str(self.header).lower(),  # API expects "true"/"false" strings
                "delimiter": self.delimiter,
            }
        
        return result


class LakehouseClient:
    """
    Client for Lakehouse operations including the Load to Tables API.

    The Load to Tables API is the OPTIMIZED approach for CSV→Delta conversion:
    - No Notebook/Spark compute required
    - Pure REST API
    - Faster execution
    """

    def __init__(self, fabric_client: FabricClient, workspace_id: str):
        """
        Initialize Lakehouse client.

        Args:
            fabric_client: Base Fabric client for API calls
            workspace_id: Workspace ID
        """
        self.fabric = fabric_client
        self.workspace_id = workspace_id

    def create_lakehouse(
        self,
        display_name: str,
        description: str = "",
        skip_if_exists: bool = True,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new Lakehouse.

        Args:
            display_name: Display name for the lakehouse
            description: Optional description
            skip_if_exists: If True, return existing lakehouse instead of error
            progress_callback: Optional progress callback

        Returns:
            Lakehouse details including ID and OneLake paths
        """
        if skip_if_exists:
            existing = self.fabric.find_lakehouse_by_name(display_name)
            if existing:
                logger.info(f"Lakehouse '{display_name}' already exists, skipping creation")
                # Fetch full details to get properties
                return self.fabric.get_lakehouse(existing["id"])

        return self.fabric.create_lakehouse(
            display_name=display_name,
            description=description,
            progress_callback=progress_callback,
        )

    def get_lakehouse(self, lakehouse_id: str) -> Dict[str, Any]:
        """Get Lakehouse properties including OneLake paths."""
        return self.fabric.get_lakehouse(lakehouse_id)

    def list_lakehouses(self) -> List[Dict[str, Any]]:
        """List all Lakehouses in the workspace."""
        return self.fabric.list_lakehouses()

    def delete_lakehouse(self, lakehouse_id: str) -> None:
        """Delete a Lakehouse."""
        self.fabric.delete_lakehouse(lakehouse_id)

    def list_tables(self, lakehouse_id: str) -> List[Dict[str, Any]]:
        """
        List all tables in a Lakehouse.

        Args:
            lakehouse_id: Lakehouse ID

        Returns:
            List of table metadata
        """
        url = f"{FABRIC_BASE_URL}/workspaces/{self.workspace_id}/lakehouses/{lakehouse_id}/tables"
        response = self.fabric._make_request("GET", url)
        result = self.fabric._handle_response(response)
        return result.get("data", [])

    def load_table(
        self,
        lakehouse_id: str,
        table_name: str,
        request: LoadTableRequest,
        timeout_seconds: int = 300,
        poll_interval: int = 5,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Load data from Files folder into a Delta table.

        This uses the Lakehouse Load to Tables API - no Notebook required!

        Args:
            lakehouse_id: Lakehouse ID
            table_name: Target table name (will be created if not exists)
            request: Load configuration
            timeout_seconds: Maximum time to wait for operation
            poll_interval: Seconds between status checks
            progress_callback: Optional callback(status, percent)

        Returns:
            Operation result
        """
        url = f"{FABRIC_BASE_URL}/workspaces/{self.workspace_id}/lakehouses/{lakehouse_id}/tables/{table_name}/load"

        body = request.to_dict()
        # Remove None values
        body = {k: v for k, v in body.items() if v is not None}

        logger.info(f"Loading table '{table_name}' from {request.relative_path}")
        response = self.fabric._make_request("POST", url, json=body)

        # Handle 202 Accepted (async operation)
        if response.status_code == 202:
            # Extract operation ID from response or Location header
            result = response.json() if response.text else {}
            operation_id = result.get("operationId")

            if operation_id:
                return self._wait_for_load_operation(
                    lakehouse_id=lakehouse_id,
                    operation_id=operation_id,
                    timeout_seconds=timeout_seconds,
                    poll_interval=poll_interval,
                    progress_callback=progress_callback,
                )

            # Fallback to Location header
            location = response.headers.get("Location")
            if location:
                return self.fabric._wait_for_lro(
                    location,
                    timeout_seconds=timeout_seconds,
                    poll_interval=poll_interval,
                    progress_callback=progress_callback,
                )

        return self.fabric._handle_response(response)

    def _wait_for_load_operation(
        self,
        lakehouse_id: str,
        operation_id: str,
        timeout_seconds: int,
        poll_interval: int,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Wait for a load operation to complete.

        Args:
            lakehouse_id: Lakehouse ID
            operation_id: Operation ID to poll
            timeout_seconds: Maximum wait time
            poll_interval: Seconds between polls
            progress_callback: Optional callback

        Returns:
            Final operation result
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                raise LROTimeoutError(
                    f"Load operation timed out after {elapsed:.1f}s",
                    operation_id=operation_id,
                    elapsed_seconds=elapsed,
                )

            status = self.get_operation_status(lakehouse_id, operation_id)
            status_value = status.get("Status", 2)  # Default to RUNNING

            # Map status codes
            if status_value == OperationStatus.SUCCESS.value:
                logger.info(f"Load operation completed successfully")
                if progress_callback:
                    progress_callback("succeeded", 100)
                return status
            elif status_value == OperationStatus.FAILED.value:
                error = status.get("Error", {})
                raise FabricAPIError(
                    f"Load operation failed: {error.get('message', 'Unknown error')}",
                    error_code=error.get("code", ""),
                )
            elif status_value == OperationStatus.NOT_STARTED.value:
                if progress_callback:
                    progress_callback("pending", 0)
            else:  # RUNNING
                progress = status.get("Progress", 0)
                if progress_callback:
                    progress_callback("running", progress)

            logger.debug(f"Load operation status: {status_value}, waiting {poll_interval}s")
            time.sleep(poll_interval)

    def get_operation_status(
        self,
        lakehouse_id: str,
        operation_id: str,
    ) -> Dict[str, Any]:
        """
        Get status of a load operation.

        Args:
            lakehouse_id: Lakehouse ID
            operation_id: Operation ID

        Returns:
            Operation status with Status, Progress, Error fields
        """
        url = f"{FABRIC_BASE_URL}/workspaces/{self.workspace_id}/lakehouses/{lakehouse_id}/operations/{operation_id}"
        response = self.fabric._make_request("GET", url)
        return self.fabric._handle_response(response)

    def load_csv_to_table(
        self,
        lakehouse_id: str,
        csv_filename: str,
        table_name: Optional[str] = None,
        mode: LoadMode = LoadMode.OVERWRITE,
        timeout_seconds: int = 300,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Convenience method to load a CSV file from Files folder to a table.

        Args:
            lakehouse_id: Lakehouse ID
            csv_filename: Name of CSV file in Files folder
            table_name: Target table name (defaults to CSV name without extension)
            mode: Load mode (overwrite or append)
            timeout_seconds: Timeout for operation
            progress_callback: Optional callback

        Returns:
            Operation result
        """
        if table_name is None:
            table_name = Path(csv_filename).stem

        request = LoadTableRequest(
            relative_path=f"Files/{csv_filename}",
            path_type=LoadPathType.FILE,
            mode=mode,
            header=True,
            file_format="CSV",
        )

        return self.load_table(
            lakehouse_id=lakehouse_id,
            table_name=table_name,
            request=request,
            timeout_seconds=timeout_seconds,
            progress_callback=progress_callback,
        )

    def load_all_csv_files(
        self,
        lakehouse_id: str,
        csv_files: List[str],
        mode: LoadMode = LoadMode.OVERWRITE,
        timeout_per_table: int = 300,
        progress_callback: Optional[Callable[[str, str, float], None]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Load multiple CSV files to tables.

        Args:
            lakehouse_id: Lakehouse ID
            csv_files: List of CSV filenames in Files folder
            mode: Load mode
            timeout_per_table: Timeout per table load
            progress_callback: Optional callback(table_name, status, percent)

        Returns:
            Dict mapping table names to results
        """
        results = {}

        for csv_file in csv_files:
            table_name = Path(csv_file).stem

            def table_progress(status: str, percent: float):
                if progress_callback:
                    progress_callback(table_name, status, percent)

            try:
                logger.info(f"Loading table: {table_name}")
                result = self.load_csv_to_table(
                    lakehouse_id=lakehouse_id,
                    csv_filename=csv_file,
                    table_name=table_name,
                    mode=mode,
                    timeout_seconds=timeout_per_table,
                    progress_callback=table_progress,
                )
                results[table_name] = {"status": "success", "result": result}
            except Exception as e:
                logger.error(f"Failed to load table {table_name}: {e}")
                results[table_name] = {"status": "failed", "error": str(e)}

        return results
