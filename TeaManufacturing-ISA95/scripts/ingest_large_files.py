#!/usr/bin/env python3
"""
Ingest large Eventhouse CSV parts into Fabric.

Uploads the split part files to OneLake and runs .ingest for each,
working around the ~200MB single-file ingestion limit.

Usage:
    python3 scripts/ingest_large_files.py

Prerequisites:
    - az login (or DefaultAzureCredential)
    - The main demo setup must have completed first (Eventhouse + KQL tables exist)
    - Part files must exist in Data/Eventhouse/ (*_part*.csv)

Configuration is read from ~/.fabric-demo/config.yaml (workspace_id)
and from the deployment's state or hardcoded IDs below.
"""

import logging
import sys
import time
from pathlib import Path

import yaml
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — update these after the initial deployment
# ---------------------------------------------------------------------------
WORKSPACE_ID = None  # Will be read from config
LAKEHOUSE_ID = None  # Lakehouse where eventhouse CSVs are staged
EVENTHOUSE_ID = None  # Eventhouse to ingest into
DATABASE_NAME = "TeaManufacturingDB"

ONELAKE_URL = "https://onelake.dfs.fabric.microsoft.com"

# The seed files (deployed by the automation tool) contain the first N data rows.
# The part files contain ALL data including those seed rows.
# We ingest parts that start AFTER the seed to avoid duplicates.
SEED_ROWS = {
    "MachineStateTelemetry": 75000,       # seed = first 75K rows
    "ProductionCounterTelemetry": 50000,   # seed = first 50K rows
}

# Map: KQL table name -> list of part file globs (from full_data split)
TABLES = {
    "MachineStateTelemetry": "MachineStateTelemetry_part*.csv",
    "ProductionCounterTelemetry": "ProductionCounterTelemetry_part*.csv",
}

DEMO_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = DEMO_DIR / "Data" / "Eventhouse" / "parts"


def load_config():
    """Load workspace ID from ~/.fabric-demo/config.yaml."""
    global WORKSPACE_ID, LAKEHOUSE_ID, EVENTHOUSE_ID

    config_path = Path.home() / ".fabric-demo" / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        WORKSPACE_ID = cfg.get("defaults", {}).get("workspace_id")
        log.info(f"Workspace ID from config: {WORKSPACE_ID}")
    
    if not WORKSPACE_ID:
        log.error("No workspace_id found in ~/.fabric-demo/config.yaml")
        sys.exit(1)

    # Try to read IDs from the setup state file or prompt
    state_path = DEMO_DIR / ".setup-state.yaml"
    if state_path.exists():
        with open(state_path) as f:
            state = yaml.safe_load(f)
        LAKEHOUSE_ID = state.get("lakehouse_id")
        EVENTHOUSE_ID = state.get("eventhouse_id")

    if not LAKEHOUSE_ID or not EVENTHOUSE_ID:
        # Prompt user for IDs
        print("\nThe Lakehouse and Eventhouse IDs are needed.")
        print("You can find these in the Fabric portal URL or from the setup output.\n")
        if not LAKEHOUSE_ID:
            LAKEHOUSE_ID = input("Lakehouse ID (GUID): ").strip()
        if not EVENTHOUSE_ID:
            EVENTHOUSE_ID = input("Eventhouse ID (GUID): ").strip()


def upload_file(fs_client, local_file: Path, remote_name: str) -> str:
    """Upload a single file to OneLake eventhouse staging folder."""
    dir_path = f"{LAKEHOUSE_ID}/Files/eventhouse"
    dir_client = fs_client.get_directory_client(dir_path)

    try:
        dir_client.create_directory()
    except Exception:
        pass

    file_client = dir_client.get_file_client(remote_name)
    file_size = local_file.stat().st_size
    size_mb = file_size / (1024 * 1024)

    log.info(f"Uploading {remote_name} ({size_mb:.1f} MB)...")

    chunk_size = 4 * 1024 * 1024  # 4MB
    file_client.create_file()

    offset = 0
    with open(local_file, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            file_client.append_data(chunk, offset=offset)
            offset += len(chunk)
            pct = offset / file_size * 100
            if offset % (20 * 1024 * 1024) < chunk_size:  # Log every ~20MB
                log.info(f"  {remote_name}: {pct:.0f}% ({offset // (1024*1024)} MB)")

    file_client.flush_data(offset)
    full_path = f"https://onelake.dfs.fabric.microsoft.com/{WORKSPACE_ID}/{dir_path}/{remote_name};impersonate"
    log.info(f"Uploaded: {remote_name}")
    return full_path


def ingest_from_onelake(credential, table_name: str, onelake_path: str):
    """Run .ingest KQL command to pull data from OneLake into a KQL table."""
    import requests

    # Get token for Kusto
    token = credential.get_token("https://api.fabric.microsoft.com/.default")

    # Build .ingest command
    command = (
        f".ingest into table {table_name} "
        f"(h'{onelake_path}') "
        f"with (format='csv', ignoreFirstRecord=true)"
    )

    # Find the Kusto query endpoint
    query_url = f"https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE_ID}/eventhouses/{EVENTHOUSE_ID}/kqlDatabases"
    headers = {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json",
    }

    # Get database ID
    resp = requests.get(query_url, headers=headers)
    resp.raise_for_status()
    databases = resp.json().get("value", [])
    
    db_id = None
    for db in databases:
        if db.get("databaseName", "") == DATABASE_NAME or db.get("displayName", "") == DATABASE_NAME:
            db_id = db.get("id")
            break
    
    if not db_id:
        log.error(f"Database '{DATABASE_NAME}' not found. Available: {[d.get('displayName', d.get('databaseName')) for d in databases]}")
        return False

    # Execute management command via Kusto REST API
    mgmt_url = f"https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE_ID}/kqlDatabases/{db_id}/executeManagementCommand"
    
    payload = {"command": command}
    log.info(f"Ingesting into {table_name} from OneLake...")
    
    resp = requests.post(mgmt_url, headers=headers, json=payload, timeout=600)
    
    if resp.status_code == 200:
        log.info(f"Successfully ingested into {table_name}")
        return True
    else:
        log.error(f"Ingestion failed for {table_name}: {resp.status_code} - {resp.text[:500]}")
        return False


def main():
    load_config()

    credential = DefaultAzureCredential()
    service_client = DataLakeServiceClient(
        account_url=ONELAKE_URL,
        credential=credential,
    )
    fs_client = service_client.get_file_system_client(WORKSPACE_ID)

    total_success = 0
    total_failed = 0

    for table_name, glob_pattern in TABLES.items():
        part_files = sorted(DATA_DIR.glob(glob_pattern))

        if not part_files:
            log.warning(f"No part files found for {table_name} (pattern: {glob_pattern})")
            continue

        log.info(f"\n{'='*60}")
        log.info(f"Processing {table_name}: {len(part_files)} parts")
        log.info(f"{'='*60}")

        for i, part_file in enumerate(part_files, 1):
            log.info(f"\n--- Part {i}/{len(part_files)}: {part_file.name} ---")

            # Step 1: Upload to OneLake
            try:
                onelake_path = upload_file(fs_client, part_file, part_file.name)
            except Exception as e:
                log.error(f"Upload failed for {part_file.name}: {e}")
                total_failed += 1
                continue

            # Step 2: Ingest into KQL table
            try:
                success = ingest_from_onelake(credential, table_name, onelake_path)
                if success:
                    total_success += 1
                else:
                    total_failed += 1
            except Exception as e:
                log.error(f"Ingestion failed for {part_file.name}: {e}")
                total_failed += 1

            # Brief pause between parts
            if i < len(part_files):
                log.info("Waiting 5s before next part...")
                time.sleep(5)

    log.info(f"\n{'='*60}")
    log.info(f"DONE: {total_success} parts ingested, {total_failed} failed")
    log.info(f"{'='*60}")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
