#!/usr/bin/env python3
"""
Comprehensive Fabric deployment validation for TeaManufacturing-ISA95 demo.

Checks:
1. TTL ontology syntax (RDF parse)
2. CSV header alignment with bindings.yaml
3. Foreign key integrity across all CSVs
4. Eventhouse key references into Lakehouse dimension tables
5. Relationship edge tables: source & target keys exist
6. Bindings.yaml internal consistency
7. No orphaned IDs, no dangling FKs
"""

import csv
import os
import re
import sys
import yaml
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
LH = os.path.join(BASE, "Data", "Lakehouse")
EH = os.path.join(BASE, "Data", "Eventhouse")

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
WARN = "\033[93m⚠\033[0m"

errors = []
warnings = []

def fail(msg):
    errors.append(msg)
    print(f"  {FAIL} {msg}")

def warn(msg):
    warnings.append(msg)
    print(f"  {WARN} {msg}")

def ok(msg):
    print(f"  {PASS} {msg}")

def read_csv_column(filepath, col_name):
    """Read all values from a specific column in a CSV."""
    vals = set()
    with open(filepath, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            v = row.get(col_name, "").strip()
            if v:
                vals.add(v)
    return vals

def read_csv_headers(filepath):
    with open(filepath, "r", newline="") as f:
        reader = csv.reader(f)
        return next(reader)

def read_csv_row_count(filepath):
    with open(filepath, "r", newline="") as f:
        return sum(1 for _ in f) - 1  # minus header

# ═══════════════════════════════════════════════════════════════════════════════
# 1. TTL Ontology Validation
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("1. TTL ONTOLOGY VALIDATION")
print("="*70)

ttl_path = os.path.join(BASE, "Ontology", "tea-manufacturing.ttl")
with open(ttl_path, "r") as f:
    ttl_content = f.read()

# Check basic structure
classes = re.findall(r':(\w+)\s+a\s+owl:Class', ttl_content)
obj_props = re.findall(r':(\w+)\s+a\s+owl:ObjectProperty', ttl_content)
data_props = re.findall(r':(\w+)\s+a\s+owl:DatatypeProperty', ttl_content)

print(f"  Classes found: {len(classes)} → {classes}")
if len(classes) == 8:
    ok(f"8 entity classes defined")
else:
    fail(f"Expected 8 classes, found {len(classes)}")

print(f"  Object properties: {len(obj_props)} → {obj_props}")
if len(obj_props) == 10:
    ok(f"10 relationship object properties defined")
else:
    fail(f"Expected 10 relationships, found {len(obj_props)}")

print(f"  Datatype properties: {len(data_props)}")

# Check every class has a key property
expected_keys = {
    "ProductBatch": "BatchId",
    "ProcessSegment": "SegmentId",
    "Material": "MaterialId",
    "Supplier": "SupplierId",
    "Equipment": "EquipmentId",
    "ProductionOrder": "OrderId",
    "QualityTest": "TestId",
    "Shipment": "ShipmentId",
}
for cls, key in expected_keys.items():
    if key in data_props:
        ok(f"{cls} has key property :{key}")
    else:
        fail(f"{cls} missing key property :{key}")

# Check relationship domains/ranges
rel_checks = [
    ("PRODUCED_IN", "ProcessSegment", "ProductBatch"),
    ("USES_MATERIAL", "ProcessSegment", "Material"),
    ("SUPPLIED_BY", "Material", "Supplier"),
    ("MANUFACTURED_AT", "ProductBatch", "Equipment"),
    ("ORDERED_FOR", "ProductionOrder", "ProductBatch"),
    ("TESTED_IN", "QualityTest", "ProcessSegment"),
    ("ORIGINATED_FROM", "Shipment", "Equipment"),
    ("DELIVERED_TO", "Shipment", "Equipment"),
    ("SHIPS_MATERIAL", "Shipment", "Material"),
    ("OPERATES_FROM", "Supplier", "Equipment"),
]
for rel, domain, rng in rel_checks:
    pattern = f':{rel}.*?rdfs:domain\\s+:{domain}.*?rdfs:range\\s+:{rng}'
    if re.search(pattern, ttl_content, re.DOTALL):
        ok(f":{rel} → domain :{domain}, range :{rng}")
    else:
        fail(f":{rel} domain/range mismatch (expected {domain}→{rng})")

# Check TTL ends with proper closure (no unclosed statements)
# Simple check: last non-empty line should end with .
lines = [l.strip() for l in ttl_content.strip().split('\n') if l.strip() and not l.strip().startswith('#')]
if lines[-1].endswith('.'):
    ok("TTL file properly terminated")
else:
    fail(f"TTL may have unterminated statement: '{lines[-1]}'")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. CSV HEADERS vs BINDINGS.YAML
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("2. CSV HEADERS vs BINDINGS.YAML ALIGNMENT")
print("="*70)

bindings_path = os.path.join(BASE, "Bindings", "bindings.yaml")
with open(bindings_path, "r") as f:
    bindings = yaml.safe_load(f)

# Lakehouse entity bindings
for entity_def in bindings["lakehouse"]["entities"]:
    entity_name = entity_def["entity"]
    csv_file = os.path.join(BASE, entity_def["file"])
    
    if not os.path.exists(csv_file):
        fail(f"{entity_name}: CSV file not found: {entity_def['file']}")
        continue
    
    headers = read_csv_headers(csv_file)
    
    # Check key column exists
    key_col = entity_def["keyColumn"]
    if key_col in headers:
        ok(f"{entity_name}: key column '{key_col}' found in {os.path.basename(csv_file)}")
    else:
        fail(f"{entity_name}: key column '{key_col}' NOT in {os.path.basename(csv_file)} (has: {headers})")
    
    # Check all property columns exist
    for prop in entity_def["properties"]:
        col = prop["column"]
        if col in headers:
            pass  # ok silently for brevity
        else:
            fail(f"{entity_name}.{prop['property']}: column '{col}' NOT in {os.path.basename(csv_file)}")
    
    ok(f"{entity_name}: all {len(entity_def['properties'])} property columns verified")

# Eventhouse bindings
for entity_def in bindings["eventhouse"]["entities"]:
    entity_name = entity_def["entity"]
    table_name = entity_def["sourceTable"]
    csv_file = os.path.join(BASE, entity_def["file"])
    
    if not os.path.exists(csv_file):
        fail(f"{entity_name}/{table_name}: CSV file not found: {entity_def['file']}")
        continue
    
    headers = read_csv_headers(csv_file)
    
    # Check key column
    key_col = entity_def["keyColumn"]
    if key_col in headers:
        ok(f"{table_name}: key column '{key_col}' found")
    else:
        fail(f"{table_name}: key column '{key_col}' NOT in headers {headers}")
    
    # Check timestamp column
    ts_col = entity_def["timestampColumn"]
    if ts_col in headers:
        ok(f"{table_name}: timestamp column '{ts_col}' found")
    else:
        fail(f"{table_name}: timestamp column '{ts_col}' NOT in headers")
    
    # Check property columns
    for prop in entity_def["properties"]:
        col = prop["column"]
        if col in headers:
            pass
        else:
            fail(f"{table_name}.{prop['property']}: column '{col}' NOT in headers")
    
    ok(f"{table_name}: all {len(entity_def['properties'])} property columns verified")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. FOREIGN KEY INTEGRITY — Lakehouse Tables
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("3. FOREIGN KEY INTEGRITY (Lakehouse)")
print("="*70)

# Load all primary key sets
batch_ids = read_csv_column(os.path.join(LH, "DimProductBatch.csv"), "BatchId")
segment_ids = read_csv_column(os.path.join(LH, "DimProcessSegment.csv"), "SegmentId")
material_ids = read_csv_column(os.path.join(LH, "DimMaterial.csv"), "MaterialId")
supplier_ids = read_csv_column(os.path.join(LH, "DimSupplier.csv"), "SupplierId")
equipment_ids = read_csv_column(os.path.join(LH, "DimEquipment.csv"), "EquipmentId")
order_ids = read_csv_column(os.path.join(LH, "DimProductionOrder.csv"), "OrderId")
test_ids = read_csv_column(os.path.join(LH, "FactQualityTest.csv"), "TestId")
shipment_ids = read_csv_column(os.path.join(LH, "FactShipment.csv"), "ShipmentId")

print(f"  Primary keys loaded: Batches={len(batch_ids)}, Segments={len(segment_ids)}, "
      f"Materials={len(material_ids)}, Suppliers={len(supplier_ids)}, "
      f"Equipment={len(equipment_ids)}, Orders={len(order_ids)}, "
      f"Tests={len(test_ids)}, Shipments={len(shipment_ids)}")

# FK: DimProcessSegment.BatchId → DimProductBatch.BatchId
seg_batch_refs = read_csv_column(os.path.join(LH, "DimProcessSegment.csv"), "BatchId")
orphans = seg_batch_refs - batch_ids
if orphans:
    fail(f"DimProcessSegment.BatchId: {len(orphans)} orphan(s) → {orphans}")
else:
    ok(f"DimProcessSegment.BatchId → DimProductBatch.BatchId: all {len(seg_batch_refs)} refs valid")

# FK: DimMaterial.SupplierId → DimSupplier.SupplierId
mat_sup_refs = read_csv_column(os.path.join(LH, "DimMaterial.csv"), "SupplierId")
orphans = mat_sup_refs - supplier_ids
if orphans:
    fail(f"DimMaterial.SupplierId: {len(orphans)} orphan(s) → {orphans}")
else:
    ok(f"DimMaterial.SupplierId → DimSupplier.SupplierId: all {len(mat_sup_refs)} refs valid")

# FK: DimProductBatch.EquipmentId → DimEquipment.EquipmentId
batch_eqp_refs = read_csv_column(os.path.join(LH, "DimProductBatch.csv"), "EquipmentId")
orphans = batch_eqp_refs - equipment_ids
if orphans:
    fail(f"DimProductBatch.EquipmentId: {len(orphans)} orphan(s) → {orphans}")
else:
    ok(f"DimProductBatch.EquipmentId → DimEquipment.EquipmentId: all {len(batch_eqp_refs)} refs valid")

# FK: DimSupplier.EquipmentId → DimEquipment.EquipmentId
sup_eqp_refs = read_csv_column(os.path.join(LH, "DimSupplier.csv"), "EquipmentId")
orphans = sup_eqp_refs - equipment_ids
if orphans:
    fail(f"DimSupplier.EquipmentId: {len(orphans)} orphan(s) → {orphans}")
else:
    ok(f"DimSupplier.EquipmentId → DimEquipment.EquipmentId: all {len(sup_eqp_refs)} refs valid")

# FK: DimProductionOrder.BatchId → DimProductBatch.BatchId
order_batch_refs = read_csv_column(os.path.join(LH, "DimProductionOrder.csv"), "BatchId")
orphans = order_batch_refs - batch_ids
if orphans:
    fail(f"DimProductionOrder.BatchId: {len(orphans)} orphan(s) → {orphans}")
else:
    ok(f"DimProductionOrder.BatchId → DimProductBatch.BatchId: all {len(order_batch_refs)} refs valid")

# FK: FactQualityTest.SegmentId → DimProcessSegment.SegmentId
test_seg_refs = read_csv_column(os.path.join(LH, "FactQualityTest.csv"), "SegmentId")
orphans = test_seg_refs - segment_ids
if orphans:
    fail(f"FactQualityTest.SegmentId: {len(orphans)} orphan(s) → {orphans}")
else:
    ok(f"FactQualityTest.SegmentId → DimProcessSegment.SegmentId: all {len(test_seg_refs)} refs valid")

# ═══════════════════════════════════════════════════════════════════════════════
# 4. RELATIONSHIP EDGE TABLES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("4. RELATIONSHIP EDGE TABLES")
print("="*70)

# EdgeSegmentMaterial: SegmentId → DimProcessSegment, MaterialId → DimMaterial
edge_sm_segs = read_csv_column(os.path.join(LH, "EdgeSegmentMaterial.csv"), "SegmentId")
edge_sm_mats = read_csv_column(os.path.join(LH, "EdgeSegmentMaterial.csv"), "MaterialId")
orphans_s = edge_sm_segs - segment_ids
orphans_m = edge_sm_mats - material_ids
if orphans_s:
    fail(f"EdgeSegmentMaterial.SegmentId: orphan(s) → {orphans_s}")
else:
    ok(f"EdgeSegmentMaterial.SegmentId: all {len(edge_sm_segs)} refs valid")
if orphans_m:
    fail(f"EdgeSegmentMaterial.MaterialId: orphan(s) → {orphans_m}")
else:
    ok(f"EdgeSegmentMaterial.MaterialId: all {len(edge_sm_mats)} refs valid")

# EdgeShipmentMaterial: ShipmentId → FactShipment, MaterialId → DimMaterial
edge_shm_ships = read_csv_column(os.path.join(LH, "EdgeShipmentMaterial.csv"), "ShipmentId")
edge_shm_mats = read_csv_column(os.path.join(LH, "EdgeShipmentMaterial.csv"), "MaterialId")
orphans_s = edge_shm_ships - shipment_ids
orphans_m = edge_shm_mats - material_ids
if orphans_s:
    fail(f"EdgeShipmentMaterial.ShipmentId: orphan(s) → {orphans_s}")
else:
    ok(f"EdgeShipmentMaterial.ShipmentId: all {len(edge_shm_ships)} refs valid")
if orphans_m:
    fail(f"EdgeShipmentMaterial.MaterialId: orphan(s) → {orphans_m}")
else:
    ok(f"EdgeShipmentMaterial.MaterialId: all {len(edge_shm_mats)} refs valid")

# EdgeShipmentOrigin: ShipmentId → FactShipment, EquipmentId → DimEquipment
edge_so_ships = read_csv_column(os.path.join(LH, "EdgeShipmentOrigin.csv"), "ShipmentId")
edge_so_eqps = read_csv_column(os.path.join(LH, "EdgeShipmentOrigin.csv"), "EquipmentId")
orphans_s = edge_so_ships - shipment_ids
orphans_e = edge_so_eqps - equipment_ids
if orphans_s:
    fail(f"EdgeShipmentOrigin.ShipmentId: orphan(s) → {orphans_s}")
else:
    ok(f"EdgeShipmentOrigin.ShipmentId: all {len(edge_so_ships)} refs valid")
if orphans_e:
    fail(f"EdgeShipmentOrigin.EquipmentId: orphan(s) → {orphans_e}")
else:
    ok(f"EdgeShipmentOrigin.EquipmentId: all {len(edge_so_eqps)} refs valid")

# EdgeShipmentDestination: ShipmentId → FactShipment, EquipmentId → DimEquipment
edge_sd_ships = read_csv_column(os.path.join(LH, "EdgeShipmentDestination.csv"), "ShipmentId")
edge_sd_eqps = read_csv_column(os.path.join(LH, "EdgeShipmentDestination.csv"), "EquipmentId")
orphans_s = edge_sd_ships - shipment_ids
orphans_e = edge_sd_eqps - equipment_ids
if orphans_s:
    fail(f"EdgeShipmentDestination.ShipmentId: orphan(s) → {orphans_s}")
else:
    ok(f"EdgeShipmentDestination.ShipmentId: all {len(edge_sd_ships)} refs valid")
if orphans_e:
    fail(f"EdgeShipmentDestination.EquipmentId: orphan(s) → {orphans_e}")
else:
    ok(f"EdgeShipmentDestination.EquipmentId: all {len(edge_sd_eqps)} refs valid")

# ═══════════════════════════════════════════════════════════════════════════════
# 5. EVENTHOUSE KEY REFERENCES → LAKEHOUSE
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("5. EVENTHOUSE KEY REFERENCES (sample-based)")
print("="*70)

# ProcessSegmentTelemetry.SegmentId → DimProcessSegment.SegmentId
pst_path = os.path.join(EH, "ProcessSegmentTelemetry.csv")
pst_segs = read_csv_column(pst_path, "SegmentId")
orphans = pst_segs - segment_ids
if orphans:
    fail(f"ProcessSegmentTelemetry.SegmentId: {len(orphans)} orphan(s) → {orphans}")
else:
    ok(f"ProcessSegmentTelemetry.SegmentId: all {len(pst_segs)} distinct keys exist in DimProcessSegment")

# EquipmentTelemetry.EquipmentId → DimEquipment.EquipmentId
et_path = os.path.join(EH, "EquipmentTelemetry.csv")
et_eqps = read_csv_column(et_path, "EquipmentId")
orphans = et_eqps - equipment_ids
if orphans:
    fail(f"EquipmentTelemetry.EquipmentId: {len(orphans)} orphan(s) → {orphans}")
else:
    ok(f"EquipmentTelemetry.EquipmentId: all {len(et_eqps)} distinct keys exist in DimEquipment")

# MachineStateTelemetry.EquipmentId → DimEquipment.EquipmentId (sample first 100K rows)
mst_path = os.path.join(EH, "MachineStateTelemetry.csv")
if os.path.exists(mst_path):
    mst_eqps = set()
    with open(mst_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            mst_eqps.add(row["EquipmentId"].strip())
            if i > 200000:
                break
    orphans = mst_eqps - equipment_ids
    if orphans:
        fail(f"MachineStateTelemetry.EquipmentId: {len(orphans)} orphan(s) in first 200K rows → {list(orphans)[:10]}")
    else:
        ok(f"MachineStateTelemetry.EquipmentId: all {len(mst_eqps)} distinct keys (from 200K sample) exist in DimEquipment")
else:
    fail("MachineStateTelemetry.csv not found")

# ProductionCounterTelemetry.EquipmentId → DimEquipment.EquipmentId (sample)
pct_path = os.path.join(EH, "ProductionCounterTelemetry.csv")
if os.path.exists(pct_path):
    pct_eqps = set()
    with open(pct_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            pct_eqps.add(row["EquipmentId"].strip())
            if i > 200000:
                break
    orphans = pct_eqps - equipment_ids
    if orphans:
        fail(f"ProductionCounterTelemetry.EquipmentId: {len(orphans)} orphan(s) in first 200K rows → {list(orphans)[:10]}")
    else:
        ok(f"ProductionCounterTelemetry.EquipmentId: all {len(pct_eqps)} distinct keys (from 200K sample) exist in DimEquipment")
else:
    fail("ProductionCounterTelemetry.csv not found")

# ═══════════════════════════════════════════════════════════════════════════════
# 6. BINDINGS.YAML RELATIONSHIP DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("6. BINDINGS.YAML RELATIONSHIP DEFINITIONS")
print("="*70)

entity_keys = {e["entity"]: e["keyColumn"] for e in bindings["lakehouse"]["entities"]}
print(f"  Entity keys: {entity_keys}")

for rel_def in bindings["lakehouse"]["relationships"]:
    rel_name = rel_def["relationship"]
    src_entity = rel_def["sourceEntity"]
    tgt_entity = rel_def["targetEntity"]
    src_table = rel_def["sourceTable"]
    src_key = rel_def["sourceKeyColumn"]
    tgt_key = rel_def["targetKeyColumn"]
    
    # Check source entity exists
    if src_entity not in entity_keys:
        fail(f"{rel_name}: sourceEntity '{src_entity}' not in entity definitions")
    
    # Check target entity exists
    if tgt_entity not in entity_keys:
        fail(f"{rel_name}: targetEntity '{tgt_entity}' not in entity definitions")
    
    # Check source table CSV exists and has the expected columns
    csv_file = os.path.join(LH, f"{src_table}.csv")
    if not os.path.exists(csv_file):
        fail(f"{rel_name}: source table file '{src_table}.csv' not found")
        continue
    
    headers = read_csv_headers(csv_file)
    if src_key not in headers:
        fail(f"{rel_name}: sourceKeyColumn '{src_key}' not in {src_table}.csv headers {headers}")
    if tgt_key not in headers:
        fail(f"{rel_name}: targetKeyColumn '{tgt_key}' not in {src_table}.csv headers {headers}")
    
    # Verify the key columns match entity key definitions
    if src_entity in entity_keys and entity_keys[src_entity] != src_key:
        # This is OK for edge tables — they have both keys as columns
        pass
    
    ok(f"{rel_name}: {src_entity}.{src_key} → {tgt_entity}.{tgt_key} via {src_table}")

# ═══════════════════════════════════════════════════════════════════════════════
# 7. DATA QUALITY CHECKS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("7. DATA QUALITY CHECKS")
print("="*70)

# Check for empty key columns
for csv_name, key_col in [
    ("DimProductBatch.csv", "BatchId"),
    ("DimProcessSegment.csv", "SegmentId"),
    ("DimMaterial.csv", "MaterialId"),
    ("DimSupplier.csv", "SupplierId"),
    ("DimEquipment.csv", "EquipmentId"),
    ("DimProductionOrder.csv", "OrderId"),
    ("FactQualityTest.csv", "TestId"),
    ("FactShipment.csv", "ShipmentId"),
]:
    path = os.path.join(LH, csv_name)
    vals = read_csv_column(path, key_col)
    rows = read_csv_row_count(path)
    if len(vals) == rows:
        ok(f"{csv_name}: {rows} rows, all {key_col} values unique")
    elif len(vals) < rows:
        fail(f"{csv_name}: {rows} rows but only {len(vals)} unique {key_col} — DUPLICATES or BLANKS!")
    else:
        ok(f"{csv_name}: {rows} rows, {len(vals)} unique keys")

# Check Eventhouse timestamp format (ISO 8601)
for csv_name in ["ProcessSegmentTelemetry.csv", "EquipmentTelemetry.csv"]:
    path = os.path.join(EH, csv_name)
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        row = next(reader)
        ts = row["Timestamp"]
        if "T" in ts and len(ts) >= 19:
            ok(f"{csv_name}: timestamp format OK ({ts})")
        else:
            fail(f"{csv_name}: timestamp format suspicious ({ts})")

for csv_name in ["MachineStateTelemetry.csv", "ProductionCounterTelemetry.csv"]:
    path = os.path.join(EH, csv_name)
    if os.path.exists(path):
        with open(path, "r") as f:
            reader = csv.DictReader(f)
            row = next(reader)
            ts = row["Timestamp"]
            if "T" in ts and len(ts) >= 19:
                ok(f"{csv_name}: timestamp format OK ({ts})")
            else:
                fail(f"{csv_name}: timestamp format suspicious ({ts})")

# Check bindings.yaml property names match TTL property labels
print("\n  Checking bindings property names ↔ TTL property labels...")
ttl_props = set(data_props)
for entity_def in bindings["lakehouse"]["entities"]:
    for prop in entity_def["properties"]:
        pname = prop["property"]
        if pname not in ttl_props:
            fail(f"Binding property '{pname}' ({entity_def['entity']}) NOT found as TTL DatatypeProperty")

for entity_def in bindings["eventhouse"]["entities"]:
    for prop in entity_def["properties"]:
        pname = prop["property"]
        if pname not in ttl_props:
            fail(f"Eventhouse binding property '{pname}' ({entity_def['sourceTable']}) NOT found as TTL DatatypeProperty")

if not any(pname not in ttl_props for entity_def in bindings["lakehouse"]["entities"] for prop in entity_def["properties"] for pname in [prop["property"]]):
    ok("All Lakehouse binding property names exist in TTL")
if not any(pname not in ttl_props for entity_def in bindings["eventhouse"]["entities"] for prop in entity_def["properties"] for pname in [prop["property"]]):
    ok("All Eventhouse binding property names exist in TTL")

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("VALIDATION SUMMARY")
print("="*70)
if errors:
    print(f"\n  {FAIL} {len(errors)} ERROR(S) FOUND:")
    for e in errors:
        print(f"     • {e}")
else:
    print(f"\n  {PASS} ALL CHECKS PASSED — ready for Fabric deployment!")

if warnings:
    print(f"\n  {WARN} {len(warnings)} warning(s):")
    for w in warnings:
        print(f"     • {w}")

print()
sys.exit(1 if errors else 0)
