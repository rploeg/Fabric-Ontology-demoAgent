"""
OneLake Data Client for file operations.

Uses Azure Data Lake Storage Gen2 compatible APIs for uploading and managing
files in Lakehouse and other OneLake-enabled items.
"""

import logging
from pathlib import Path
from typing import Optional, List, BinaryIO, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from azure.identity import DefaultAzureCredential
from azure.core.credentials import TokenCredential
from azure.storage.filedatalake import DataLakeServiceClient, FileSystemClient

from demo_automation.core.errors import OneLakeError


logger = logging.getLogger(__name__)


ONELAKE_ACCOUNT_URL = "https://onelake.dfs.fabric.microsoft.com"


@dataclass
class OneLakeConfig:
    """Configuration for OneLake data access."""

    workspace_id: str
    workspace_name: str  # Human-readable name for DFS path
    account_url: str = ONELAKE_ACCOUNT_URL


class OneLakeDataClient:
    """
    Client for OneLake file operations using ADLS Gen2 compatible APIs.

    OneLake paths follow this structure:
    - Lakehouse Files: {workspace_name}/{lakehouse_name}.Lakehouse/Files/{path}
    - Lakehouse Tables: {workspace_name}/{lakehouse_name}.Lakehouse/Tables/{table_name}
    """

    def __init__(
        self,
        workspace_name: str,
        credential: Optional[TokenCredential] = None,
        account_url: str = ONELAKE_ACCOUNT_URL,
    ):
        """
        Initialize the OneLake client.

        Args:
            workspace_name: The Fabric workspace name (human-readable)
            credential: Azure credential (defaults to DefaultAzureCredential)
            account_url: OneLake account URL
        """
        self.workspace_name = workspace_name
        self.account_url = account_url

        self._credential = credential or DefaultAzureCredential()
        self._service_client = DataLakeServiceClient(
            account_url=account_url,
            credential=self._credential,
        )
        self._fs_client: Optional[FileSystemClient] = None

    @property
    def file_system_client(self) -> FileSystemClient:
        """Get or create file system client for the workspace."""
        if self._fs_client is None:
            self._fs_client = self._service_client.get_file_system_client(
                self.workspace_name
            )
        return self._fs_client

    def _get_item_path(self, item_id: str, item_name: str = None, item_type: str = "Lakehouse") -> str:
        """
        Get the OneLake path for a Fabric item.

        Args:
            item_id: ID (GUID) of the item - REQUIRED for OneLake API
            item_name: Display name of the item (optional, for logging only)
            item_type: Type suffix (Lakehouse, Eventhouse, etc.) - used only for logging

        Returns:
            Path using just the item_id (OneLake API requires GUIDs without type suffix)
        """
        # OneLake requires item_id (GUID) in the path WITHOUT the type suffix
        # The type suffix like ".Lakehouse" is only used with friendly names
        return item_id

    def upload_file(
        self,
        item_id: str,
        local_file: Path,
        remote_path: str,
        item_name: str = None,
        item_type: str = "Lakehouse",
        folder: str = "Files",
        overwrite: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        """
        Upload a file to a Fabric item's Files folder.

        Args:
            item_id: ID (GUID) of the Fabric item - REQUIRED
            local_file: Path to local file to upload
            remote_path: Remote file name or path (relative to folder)
            item_name: Display name (optional, for logging only)
            item_type: Type suffix (default: Lakehouse)
            folder: Folder within the item (Files, Tables, etc.)
            overwrite: Whether to overwrite existing files
            progress_callback: Optional callback(bytes_uploaded, total_bytes)

        Returns:
            Full remote path of uploaded file
        """
        try:
            item_path = self._get_item_path(item_id, item_name, item_type)
            directory_path = f"{item_path}/{folder}"

            directory_client = self.file_system_client.get_directory_client(
                directory_path
            )

            # Ensure directory exists
            try:
                directory_client.create_directory()
            except Exception:
                pass  # Directory may already exist

            file_client = directory_client.get_file_client(remote_path)

            file_size = local_file.stat().st_size
            logger.debug(f"Uploading {local_file.name} ({file_size} bytes)")

            with open(local_file, "rb") as data:
                if progress_callback:
                    # Upload with progress tracking
                    chunk_size = 4 * 1024 * 1024  # 4MB chunks
                    file_client.create_file()

                    offset = 0
                    while True:
                        chunk = data.read(chunk_size)
                        if not chunk:
                            break
                        file_client.append_data(chunk, offset=offset)
                        offset += len(chunk)
                        progress_callback(offset, file_size)

                    file_client.flush_data(offset)
                else:
                    # Simple upload
                    file_client.upload_data(data, overwrite=overwrite)

            full_path = f"{directory_path}/{remote_path}"
            logger.info(f"Uploaded: {full_path}")
            return full_path

        except Exception as e:
            raise OneLakeError(
                f"Failed to upload file {local_file.name}: {e}",
                details={"local_file": str(local_file), "item_id": item_id, "item_name": item_name},
                cause=e,
            )

    def upload_files(
        self,
        item_id: str,
        files: List[Path],
        item_name: str = None,
        item_type: str = "Lakehouse",
        folder: str = "Files",
        max_workers: int = 4,
        overwrite: bool = True,
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ) -> dict:
        """
        Upload multiple files in parallel.

        Args:
            item_id: ID (GUID) of the Fabric item - REQUIRED
            files: List of local file paths
            item_name: Display name (optional, for logging)
            item_type: Type suffix
            folder: Folder within the item
            max_workers: Maximum parallel uploads
            overwrite: Whether to overwrite existing files
            progress_callback: Optional callback(file_name, status)

        Returns:
            Dict with 'success' and 'failed' lists
        """
        results = {"success": [], "failed": []}

        def upload_one(file_path: Path) -> tuple:
            try:
                remote_path = self.upload_file(
                    item_id=item_id,
                    local_file=file_path,
                    remote_path=file_path.name,
                    item_name=item_name,
                    item_type=item_type,
                    folder=folder,
                    overwrite=overwrite,
                )
                return (file_path.name, True, remote_path)
            except Exception as e:
                return (file_path.name, False, str(e))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(upload_one, f): f for f in files}

            for future in as_completed(futures):
                file_name, success, result = future.result()
                if success:
                    results["success"].append({"name": file_name, "path": result})
                    if progress_callback:
                        progress_callback(file_name, "success")
                else:
                    results["failed"].append({"name": file_name, "error": result})
                    if progress_callback:
                        progress_callback(file_name, "failed")

        return results

    def list_files(
        self,
        item_id: str,
        folder: str = "Files",
        item_type: str = "Lakehouse",
    ) -> List[str]:
        """
        List files in a Fabric item folder.

        Args:
            item_id: ID (GUID) of the Fabric item
            folder: Folder within the item
            item_type: Type suffix

        Returns:
            List of file names
        """
        try:
            item_path = self._get_item_path(item_id, item_type=item_type)
            directory_path = f"{item_path}/{folder}"

            directory_client = self.file_system_client.get_directory_client(
                directory_path
            )

            files = []
            for path in directory_client.get_paths():
                if not path.is_directory:
                    files.append(path.name.split("/")[-1])

            return files
        except Exception as e:
            logger.warning(f"Could not list files in {item_id}/{folder}: {e}")
            return []

    def delete_file(
        self,
        item_id: str,
        remote_path: str,
        folder: str = "Files",
        item_type: str = "Lakehouse",
    ) -> bool:
        """
        Delete a file from a Fabric item.

        Args:
            item_id: ID (GUID) of the Fabric item
            remote_path: File path to delete
            folder: Folder within the item
            item_type: Type suffix

        Returns:
            True if deleted, False otherwise
        """
        try:
            item_path = self._get_item_path(item_id, item_type=item_type)
            directory_path = f"{item_path}/{folder}"

            directory_client = self.file_system_client.get_directory_client(
                directory_path
            )
            file_client = directory_client.get_file_client(remote_path)
            file_client.delete_file()

            logger.info(f"Deleted: {directory_path}/{remote_path}")
            return True
        except Exception as e:
            logger.warning(f"Could not delete file: {e}")
            return False

    def file_exists(
        self,
        item_id: str,
        remote_path: str,
        folder: str = "Files",
        item_type: str = "Lakehouse",
    ) -> bool:
        """
        Check if a file exists in a Fabric item.

        Args:
            item_id: ID (GUID) of the Fabric item
            remote_path: File path to check
            folder: Folder within the item
            item_type: Type suffix

        Returns:
            True if exists, False otherwise
        """
        try:
            item_path = self._get_item_path(item_id, item_type=item_type)
            directory_path = f"{item_path}/{folder}"

            directory_client = self.file_system_client.get_directory_client(
                directory_path
            )
            file_client = directory_client.get_file_client(remote_path)
            file_client.get_file_properties()
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Close the client and release resources."""
        self._service_client.close()

    def __enter__(self) -> "OneLakeDataClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
