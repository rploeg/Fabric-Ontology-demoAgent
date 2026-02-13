#!/usr/bin/env python3
"""Trigger a graph refresh for the TeaManufacturing ontology."""

import sys
import time
sys.path.insert(0, "/Users/remco/repo/Fabric-Ontology-demoAgent/Demo-automation/src")

from demo_automation.platform.fabric_client import FabricClient

WORKSPACE_ID = "4d4dab11-9b44-4af4-b866-158e57acbbe7"
GRAPH_ID = "9be1bd74-1567-44d8-842d-0f04b0a79e6d"

client = FabricClient(workspace_id=WORKSPACE_ID)

ONTOLOGY_ID = "7245e83c-3541-42ca-a905-005c29ef05e1"

# Try path-based URL format (newer API) vs query parameter format
urls_to_try = [
    ("Graph Refresh (path)", f"https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE_ID}/items/{GRAPH_ID}/jobs/Refresh/instances"),
    ("Graph DefaultJob (path)", f"https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE_ID}/items/{GRAPH_ID}/jobs/DefaultJob/instances"),
    ("Ontology Refresh (path)", f"https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE_ID}/items/{ONTOLOGY_ID}/jobs/Refresh/instances"),
    ("Ontology DefaultJob (path)", f"https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE_ID}/items/{ONTOLOGY_ID}/jobs/DefaultJob/instances"),
]

for label, url in urls_to_try:
    print(f"Trying {label}...")
    response = client._make_request("POST", url)
    print(f"  Status: {response.status_code} - {response.text[:200]}")
    if response.status_code in (200, 202):
        print(f"  SUCCESS!")
        break
else:
    print("\nNone of the API approaches worked.")
    print("The GraphModel refresh must be triggered manually from the Fabric portal.")
    print(f"\nOpen: https://app.fabric.microsoft.com/groups/{WORKSPACE_ID}")
    print(f"Find: TeaManufacturing_ISA95_Ontology_graph_...")
    print("Click ... > Refresh now")

if response.status_code == 202:
    location = response.headers.get("Location")
    retry_after = int(response.headers.get("Retry-After", 30))
    print(f"Job accepted! Polling every {retry_after}s...")

    for i in range(30):
        time.sleep(retry_after)
        poll = client._make_request("GET", location)
        try:
            data = poll.json()
            status = data.get("status", str(poll.status_code))
        except Exception:
            status = str(poll.status_code)
        print(f"  Poll {i+1}: status={status}")
        if status in ("Completed", "Failed", "Cancelled"):
            if status == "Completed":
                print("\nGraph refresh completed successfully!")
            else:
                print(f"\nFinal status: {status}")
                print(data.get("failureReason", ""))
            break
    else:
        print("\nTimed out waiting for refresh. Check Fabric portal.")
elif response.status_code == 200:
    print("Refresh completed (sync).")
else:
    txt = response.text[:500]
    print(f"Response: {txt}")
    if response.status_code == 409:
        print("A refresh is already in progress.")
        url2 = f"https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE_ID}/items/{GRAPH_ID}/jobs/instances"
        r2 = client._make_request("GET", url2)
        for job in r2.json().get("value", [])[:3]:
            print(f"  Job {job['id']}: {job['status']} ({job['invokeType']})")
