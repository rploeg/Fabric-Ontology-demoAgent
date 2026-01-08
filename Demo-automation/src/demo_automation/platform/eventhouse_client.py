"""
Eventhouse and KQL Database Client for Fabric operations.

Handles Eventhouse creation, KQL database management, and data ingestion
using the Kusto REST API.
"""

import base64
import logging
import time
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass

import requests

from .fabric_client import FabricClient, FABRIC_BASE_URL
from demo_automation.core.errors import FabricAPIError, LROTimeoutError


logger = logging.getLogger(__name__)


@dataclass
class KQLTableSchema:
    """Schema definition for a KQL table."""
    name: str
    columns: List[Dict[str, str]]  # [{"name": "Col1", "type": "string"}, ...]

    def to_create_command(self) -> str:
        """Generate .create-merge table command."""
        cols = ", ".join(
            f"{col['name']}: {col['type']}" for col in self.columns
        )
        return f".create-merge table {self.name} ({cols})"


class EventhouseClient:
    """
    Client for Eventhouse and KQL Database operations.

    Supports:
    - Eventhouse creation (auto-creates default KQL database)
    - KQL database schema management
    - Data ingestion via Kusto REST API
    """

    def __init__(self, fabric_client: FabricClient, workspace_id: str):
        """
        Initialize Eventhouse client.

        Args:
            fabric_client: Base Fabric client
            workspace_id: Workspace ID
        """
        self.fabric = fabric_client
        self.workspace_id = workspace_id
        self._kusto_tokens: Dict[str, str] = {}

    def create_eventhouse(
        self,
        display_name: str,
        description: str = "",
        skip_if_exists: bool = True,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new Eventhouse.

        Note: Creating an Eventhouse automatically creates a default KQL database.

        Args:
            display_name: Display name for the eventhouse
            description: Optional description
            skip_if_exists: If True, return existing eventhouse
            progress_callback: Optional progress callback

        Returns:
            Eventhouse details including KQL database IDs
        """
        if skip_if_exists:
            existing = self.fabric.find_eventhouse_by_name(display_name)
            if existing:
                logger.info(f"Eventhouse '{display_name}' already exists, skipping creation")
                return self.fabric.get_eventhouse(existing["id"])

        return self.fabric.create_eventhouse(
            display_name=display_name,
            description=description,
            progress_callback=progress_callback,
        )

    def get_eventhouse(self, eventhouse_id: str) -> Dict[str, Any]:
        """Get Eventhouse details."""
        return self.fabric.get_eventhouse(eventhouse_id)

    def list_eventhouses(self) -> List[Dict[str, Any]]:
        """List all Eventhouses in the workspace."""
        return self.fabric.list_eventhouses()

    def delete_eventhouse(self, eventhouse_id: str) -> None:
        """Delete an Eventhouse."""
        self.fabric.delete_eventhouse(eventhouse_id)

    # --- KQL Database Operations ---

    def list_kql_databases(self) -> List[Dict[str, Any]]:
        """List all KQL databases in the workspace."""
        return self.fabric.list_kql_databases()

    def get_kql_database(self, database_id: str) -> Dict[str, Any]:
        """Get KQL database details."""
        return self.fabric.get_kql_database(database_id)

    def find_kql_database_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find KQL database by name."""
        return self.fabric.find_kql_database_by_name(name)

    def get_default_database_for_eventhouse(
        self,
        eventhouse_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get the default KQL database for an Eventhouse.

        Args:
            eventhouse_id: Eventhouse ID

        Returns:
            KQL database details or None
        """
        eventhouse = self.get_eventhouse(eventhouse_id)
        properties = eventhouse.get("properties", {})
        database_ids = properties.get("databasesItemIds", [])

        if database_ids:
            return self.get_kql_database(database_ids[0])
        return None

    def create_kql_database_with_schema(
        self,
        display_name: str,
        eventhouse_id: str,
        schema_script: str,
        timeout_seconds: int = 300,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Create a KQL database with schema in a single operation.

        This uses the definition-based creation pattern where the schema
        is included as a KQL script in the definition parts.

        Args:
            display_name: Display name for the database
            eventhouse_id: Parent Eventhouse ID
            schema_script: KQL script with .create-merge table commands
            timeout_seconds: Timeout for LRO
            progress_callback: Optional callback

        Returns:
            Created KQL database details
        """
        # Build definition parts
        db_properties = {
            "databaseType": "ReadWrite",
            "parentEventhouseItemId": eventhouse_id,
        }

        definition = {
            "parts": [
                {
                    "path": "DatabaseProperties.json",
                    "payload": base64.b64encode(
                        str(db_properties).encode("utf-8")
                    ).decode("utf-8"),
                    "payloadType": "InlineBase64",
                },
                {
                    "path": "DatabaseSchema.kql",
                    "payload": base64.b64encode(
                        schema_script.encode("utf-8")
                    ).decode("utf-8"),
                    "payloadType": "InlineBase64",
                },
            ]
        }

        logger.info(f"Creating KQL database '{display_name}' with schema")
        return self.fabric.create_item(
            item_type="kqlDatabases",
            display_name=display_name,
            definition=definition,
            timeout_seconds=timeout_seconds,
            progress_callback=progress_callback,
        )

    # --- Kusto Query/Management Operations ---

    def _get_kusto_endpoint(self, eventhouse_id: str) -> str:
        """Get the Kusto query endpoint for an Eventhouse."""
        eventhouse = self.get_eventhouse(eventhouse_id)
        properties = eventhouse.get("properties", {})

        query_uri = properties.get("queryServiceUri", "")
        if not query_uri:
            raise FabricAPIError(
                "Could not determine Kusto query endpoint",
                details={"eventhouse_id": eventhouse_id},
            )
        return query_uri

    def _get_kusto_token(self, endpoint: str) -> str:
        """Get authentication token for Kusto endpoint."""
        # Kusto uses its own scope
        scope = f"{endpoint}/.default"

        if scope not in self._kusto_tokens:
            token = self.fabric._credential.get_token(scope)
            self._kusto_tokens[scope] = token.token

        return self._kusto_tokens[scope]

    def execute_kql_management(
        self,
        eventhouse_id: str,
        database_name: str,
        command: str,
    ) -> Dict[str, Any]:
        """
        Execute a KQL management command (e.g., .create-merge table).

        Args:
            eventhouse_id: Eventhouse ID
            database_name: Database name
            command: KQL management command

        Returns:
            Command result
        """
        endpoint = self._get_kusto_endpoint(eventhouse_id)
        mgmt_url = f"{endpoint}/v1/rest/mgmt"

        body = {
            "db": database_name,
            "csl": command,
        }

        headers = {
            "Authorization": f"Bearer {self._get_kusto_token(endpoint)}",
            "Content-Type": "application/json",
        }

        logger.debug(f"Executing KQL management: {command[:100]}...")
        response = requests.post(mgmt_url, json=body, headers=headers, timeout=120)

        if response.status_code != 200:
            raise FabricAPIError(
                f"KQL management command failed: {response.text}",
                status_code=response.status_code,
            )

        return response.json()

    def execute_kql_query(
        self,
        eventhouse_id: str,
        database_name: str,
        query: str,
    ) -> Dict[str, Any]:
        """
        Execute a KQL query.

        Args:
            eventhouse_id: Eventhouse ID
            database_name: Database name
            query: KQL query

        Returns:
            Query result
        """
        endpoint = self._get_kusto_endpoint(eventhouse_id)
        query_url = f"{endpoint}/v2/rest/query"

        body = {
            "db": database_name,
            "csl": query,
        }

        headers = {
            "Authorization": f"Bearer {self._get_kusto_token(endpoint)}",
            "Content-Type": "application/json",
        }

        response = requests.post(query_url, json=body, headers=headers, timeout=120)

        if response.status_code != 200:
            raise FabricAPIError(
                f"KQL query failed: {response.text}",
                status_code=response.status_code,
            )

        return response.json()

    def create_table(
        self,
        eventhouse_id: str,
        database_name: str,
        table_schema: KQLTableSchema,
    ) -> Dict[str, Any]:
        """
        Create or merge a table in the KQL database.

        Args:
            eventhouse_id: Eventhouse ID
            database_name: Database name
            table_schema: Table schema definition

        Returns:
            Command result
        """
        command = table_schema.to_create_command()
        return self.execute_kql_management(
            eventhouse_id=eventhouse_id,
            database_name=database_name,
            command=command,
        )

    def create_csv_ingestion_mapping(
        self,
        eventhouse_id: str,
        database_name: str,
        table_name: str,
        mapping_name: str,
        columns: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Create a CSV ingestion mapping for a table.

        Args:
            eventhouse_id: Eventhouse ID
            database_name: Database name
            table_name: Table name
            mapping_name: Mapping name
            columns: Column mappings [{"column": "Col1", "ordinal": 0}, ...]

        Returns:
            Command result
        """
        mapping_json = str([
            {"column": c["column"], "Properties": {"Ordinal": str(c["ordinal"])}}
            for c in columns
        ])

        command = f".create table {table_name} ingestion csv mapping \"{mapping_name}\" '{mapping_json}'"

        return self.execute_kql_management(
            eventhouse_id=eventhouse_id,
            database_name=database_name,
            command=command,
        )

    def ingest_from_onelake(
        self,
        eventhouse_id: str,
        database_name: str,
        table_name: str,
        onelake_path: str,
        file_format: str = "csv",
        ignore_first_record: bool = True,
        mapping_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Ingest data from OneLake into a KQL table.

        Args:
            eventhouse_id: Eventhouse ID
            database_name: Database name
            table_name: Target table name
            onelake_path: Full OneLake path to the data file
            file_format: File format (csv, parquet, json)
            ignore_first_record: Skip header row for CSV
            mapping_name: Optional ingestion mapping name

        Returns:
            Ingestion result
        """
        with_options = [f"format='{file_format}'"]
        if ignore_first_record:
            with_options.append("ignoreFirstRecord=true")
        if mapping_name:
            with_options.append(f"ingestionMapping='{mapping_name}'")

        with_clause = ", ".join(with_options)
        command = f".ingest into table {table_name} (h'{onelake_path}') with ({with_clause})"

        logger.info(f"Ingesting data into {table_name} from {onelake_path}")
        return self.execute_kql_management(
            eventhouse_id=eventhouse_id,
            database_name=database_name,
            command=command,
        )

    def list_tables(
        self,
        eventhouse_id: str,
        database_name: str,
    ) -> List[str]:
        """
        List all tables in a KQL database.

        Args:
            eventhouse_id: Eventhouse ID
            database_name: Database name

        Returns:
            List of table names
        """
        # Use management endpoint since .show tables is a control command
        result = self.execute_kql_management(
            eventhouse_id=eventhouse_id,
            database_name=database_name,
            command=".show tables | project TableName",
        )

        tables = []
        try:
            for frame in result.get("Tables", []):
                for row in frame.get("Rows", []):
                    if row:
                        tables.append(row[0])
        except Exception:
            pass

        return tables

    def get_table_count(
        self,
        eventhouse_id: str,
        database_name: str,
        table_name: str,
    ) -> int:
        """
        Get row count for a table.

        Args:
            eventhouse_id: Eventhouse ID
            database_name: Database name
            table_name: Table name

        Returns:
            Row count
        """
        query = f"{table_name} | count"
        result = self.execute_kql_query(
            eventhouse_id=eventhouse_id,
            database_name=database_name,
            query=query,
        )

        # Parse result
        try:
            tables = result.get("Tables", [])
            if tables:
                rows = tables[0].get("Rows", [])
                if rows:
                    return rows[0][0]
        except Exception:
            pass

        return 0
