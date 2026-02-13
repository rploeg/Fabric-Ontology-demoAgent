"""Verify seed files have correct headers, FK integrity, and timestamp range."""
import csv
import os

seeds = {
    "Data/Eventhouse/MachineStateTelemetry.csv": ("EquipmentId", "Timestamp"),
    "Data/Eventhouse/ProductionCounterTelemetry.csv": ("EquipmentId", "Timestamp"),
}

equip_ids = set()
with open("Data/Lakehouse/DimEquipment.csv") as f:
    for row in csv.DictReader(f):
        equip_ids.add(row["EquipmentId"])

all_ok = True
for path, (key_col, ts_col) in seeds.items():
    with open(path) as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        rows = list(reader)

    print(f"\n{path}:")
    print(f"  Headers: {headers}")
    print(f"  Rows: {len(rows)}")

    if key_col in headers:
        print(f"  OK: key column '{key_col}' present")
    else:
        print(f"  FAIL: key column '{key_col}' MISSING!")
        all_ok = False

    if ts_col in headers:
        print(f"  OK: timestamp column '{ts_col}' present")
    else:
        print(f"  FAIL: timestamp column '{ts_col}' MISSING!")
        all_ok = False

    seed_keys = set(r[key_col] for r in rows)
    bad = seed_keys - equip_ids
    if bad:
        print(f"  FAIL: {len(bad)} orphan keys: {list(bad)[:5]}")
        all_ok = False
    else:
        print(f"  OK: all {len(seed_keys)} distinct keys exist in DimEquipment")

    ts_vals = sorted(set(r[ts_col][:10] for r in rows))
    print(f"  Timestamp range: {ts_vals[0]} to {ts_vals[-1]}")

    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"  File size: {size_mb:.1f} MB")

print()
if all_ok:
    print("ALL SEED FILE CHECKS PASSED")
else:
    print("SOME CHECKS FAILED!")
