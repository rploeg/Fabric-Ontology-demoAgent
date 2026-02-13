#!/usr/bin/env python3
"""Check graph refresh job status."""
import sys, json
sys.path.insert(0, "/Users/remco/repo/Fabric-Ontology-demoAgent/Demo-automation/src")
from demo_automation.platform.fabric_client import FabricClient

c = FabricClient(workspace_id="4d4dab11-9b44-4af4-b866-158e57acbbe7")
r = c._make_request("GET", "https://api.fabric.microsoft.com/v1/workspaces/4d4dab11-9b44-4af4-b866-158e57acbbe7/items/9be1bd74-1567-44d8-842d-0f04b0a79e6d/jobs/instances")
for j in r.json().get("value", []):
    sid = j["id"][:8]
    status = j["status"]
    itype = j["invokeType"]
    start = j.get("startTimeUtc", "?")
    end = j.get("endTimeUtc", "?")
    reason = j.get("failureReason") or ""
    print(f"{sid}  status={status:<12s}  type={itype:<10s}  start={start}  end={end}  {reason}")
