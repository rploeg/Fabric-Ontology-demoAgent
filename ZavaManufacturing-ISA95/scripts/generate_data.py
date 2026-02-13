#!/usr/bin/env python3
"""
Generate all Lakehouse CSVs and transform Eventhouse seeds for ZavaManufacturing-ISA95.

Domain: Zava Inc. — Smart Textiles / Smart Fiber Manufacturing
Products: ZavaCore™ smart mesh units
ISA-95: Site → Area → WorkCenter → WorkUnit
"""
import csv
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LH = os.path.join(BASE, "Data", "Lakehouse")
EH = os.path.join(BASE, "Data", "Eventhouse")
TEA_EH = os.path.join(os.path.dirname(BASE), "TeaManufacturing-ISA95", "Data", "Eventhouse")

os.makedirs(LH, exist_ok=True)
os.makedirs(EH, exist_ok=True)

def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  ✓ {os.path.basename(path)}: {len(rows)} rows")

# =============================================================================
# 1) DimProductBatch  (20 rows)
# =============================================================================
products = [
    ("BTC-001", "ZavaCore Field Standard",  "ZF-STD-01", 10000, "Complete",   "2025-11-15T14:30:00", "EQP-002"),
    ("BTC-002", "ZavaCore Field Standard",  "ZF-STD-01", 10000, "Complete",   "2025-11-16T09:45:00", "EQP-002"),
    ("BTC-003", "ZavaCore Field Slim",      "ZF-SLM-01",  8000, "Complete",   "2025-11-17T16:20:00", "EQP-002"),
    ("BTC-004", "ZavaCore Field Slim",      "ZF-SLM-01",  8000, "Complete",   "2025-11-18T11:00:00", "EQP-002"),
    ("BTC-005", "ZavaCore Systems Pro",     "ZS-PRO-01",  5000, "Complete",   "2025-11-19T15:30:00", "EQP-002"),
    ("BTC-006", "ZavaCore Systems Pro",     "ZS-PRO-01",  5000, "Complete",   "2025-11-20T10:15:00", "EQP-002"),
    ("BTC-007", "ZavaCore Systems Elite",   "ZS-ELT-01",  6000, "Complete",   "2025-11-21T13:45:00", "EQP-002"),
    ("BTC-008", "ZavaCore Systems Elite",   "ZS-ELT-01",  6000, "Complete",   "2025-11-22T09:00:00", "EQP-002"),
    ("BTC-009", "ZavaCore Field Micro",     "ZF-MCR-01",  3000, "Complete",   "2025-11-23T16:00:00", "EQP-002"),
    ("BTC-010", "ZavaCore Field Micro",     "ZF-MCR-01",  3000, "Complete",   "2025-11-24T11:30:00", "EQP-002"),
    ("BTC-011", "ZavaCore Field Standard",  "ZF-STD-01", 10000, "InProgress", "",                    "EQP-002"),
    ("BTC-012", "ZavaCore Field Slim",      "ZF-SLM-01",  8000, "InProgress", "",                    "EQP-002"),
    ("BTC-013", "ZavaCore Systems Pro",     "ZS-PRO-01",  5000, "InProgress", "",                    "EQP-002"),
    ("BTC-014", "ZavaCore Systems Elite",   "ZS-ELT-01",  6000, "Planned",   "",                    "EQP-002"),
    ("BTC-015", "ZavaCore Field Standard",  "ZF-STD-01", 15000, "Planned",   "",                    "EQP-002"),
    ("BTC-016", "ZavaCore Field Active",    "ZF-ACT-01",  7000, "Complete",   "2025-11-25T14:00:00", "EQP-002"),
    ("BTC-017", "ZavaCore Systems Compact", "ZS-CMP-01",  4000, "Complete",   "2025-11-26T10:00:00", "EQP-002"),
    ("BTC-018", "ZavaCore Systems Nano",    "ZS-NAN-01",  3000, "InProgress", "",                    "EQP-002"),
    ("BTC-019", "ZavaCore Field Slim",      "ZF-SLM-01", 12000, "Planned",   "",                    "EQP-002"),
    ("BTC-020", "ZavaCore Field Standard",  "ZF-STD-01", 20000, "Planned",   "",                    "EQP-002"),
]
write_csv(os.path.join(LH, "DimProductBatch.csv"),
          ["BatchId","Batch_Product","Batch_MeshSpec","Batch_Quantity","Batch_Status","Batch_CompletionDate","EquipmentId"],
          products)

# =============================================================================
# 2) DimProcessSegment  (30 rows)
# =============================================================================
seg_types = ["Coating", "Weaving", "SensorEmbed", "Packaging"]
seg_prefix = {"Coating": "COT", "Weaving": "WEV", "SensorEmbed": "SEN", "Packaging": "PKG"}

# Product short codes for segment codes
batch_product_code = {
    "BTC-001": "FS", "BTC-002": "FS", "BTC-003": "SL", "BTC-004": "SL",
    "BTC-005": "SP", "BTC-006": "SP", "BTC-007": "SE", "BTC-008": "SE",
    "BTC-009": "FM", "BTC-010": "FM", "BTC-011": "FS", "BTC-012": "SL",
}
segments = []
seg_id = 1
# Batches 1-7 get 4 segments each = 28
for b_idx in range(7):
    batch = f"BTC-{b_idx+1:03d}"
    code = batch_product_code.get(batch, "XX")
    base_day = 10 + b_idx
    for s_idx, stype in enumerate(seg_types):
        s = f"SEG-{seg_id:03d}"
        sc = f"{seg_prefix[stype]}-{code}-{b_idx+1:03d}"
        start = f"2025-11-{base_day + s_idx*2:02d}T{6 + s_idx*2:02d}:00:00"
        segments.append((s, stype, sc, "Complete", start, batch))
        seg_id += 1
# Batches 11 & 12 get 1 InProgress segment each = 2
for b_idx, batch in enumerate(["BTC-011", "BTC-012"]):
    code = batch_product_code.get(batch, "XX")
    s = f"SEG-{seg_id:03d}"
    sc = f"COT-{code}-{3 + b_idx:03d}"
    start = f"2025-11-{25 + b_idx:02d}T08:00:00"
    segments.append((s, "Coating", sc, "InProgress", start, batch))
    seg_id += 1

write_csv(os.path.join(LH, "DimProcessSegment.csv"),
          ["SegmentId","Segment_Type","Segment_Code","Segment_Status","Segment_StartDate","BatchId"],
          segments)

# =============================================================================
# 3) DimMaterial  (25 rows)
# =============================================================================
materials = [
    ("MAT-001", "Graphite Fiber Tow",          "GFT-001", "RawMaterial",       45.00, 21, "SUP-001"),
    ("MAT-002", "Silver Nanowire Solution",     "SNW-002", "RawMaterial",       12.00, 14, "SUP-002"),
    ("MAT-003", "Copper Trace Ink",             "CTI-003", "RawMaterial",       28.00, 18, "SUP-003"),
    ("MAT-004", "FR-4 Substrate Sheet",         "FR4-004", "RawMaterial",       22.00, 25, "SUP-004"),
    ("MAT-005", "Conductive Polymer Coating",   "CPC-005", "RawMaterial",       35.00, 20, "SUP-007"),
    ("MAT-006", "Carbon Nanotube Dispersion",   "CNT-006", "RawMaterial",      120.00, 15, "SUP-008"),
    ("MAT-007", "Piezoelectric PVDF Film",      "PVD-007", "RawMaterial",       10.00, 16, "SUP-009"),
    ("MAT-008", "Thermoplastic PU Film",        "TPU-008", "RawMaterial",       18.00, 19, "SUP-001"),
    ("MAT-009", "Elastane Blend Yarn",          "EBY-009", "RawMaterial",       85.00, 12, "SUP-007"),
    ("MAT-010", "Nylon Base Yarn",              "NBY-010", "RawMaterial",       65.00, 14, "SUP-007"),
    ("MAT-011", "Sensor Module Type-A",         "SMA-011", "Component",          0.02,  7, "SUP-005"),
    ("MAT-012", "Flex PCB Connector",           "FPC-012", "Component",          0.01,  5, "SUP-010"),
    ("MAT-013", "Micro Solder Paste",           "MSP-013", "Component",          0.005, 5, "SUP-010"),
    ("MAT-014", "Conductive Adhesive Tape",     "CAT-014", "Component",          0.03, 10, "SUP-005"),
    ("MAT-015", "Moisture Barrier Film",        "MBF-015", "PackagingMaterial",  0.04,  8, "SUP-005"),
    ("MAT-016", "Anti-Static Bag Single",       "ASB-016", "PackagingMaterial",  0.15,  7, "SUP-006"),
    ("MAT-017", "Anti-Static Bag Bulk",         "ABB-017", "PackagingMaterial",  0.25,  7, "SUP-006"),
    ("MAT-018", "Outer Shipping Carton",        "OSC-018", "PackagingMaterial",  0.35,  7, "SUP-006"),
    ("MAT-019", "ESD Shielding Wrap",           "ESW-019", "PackagingMaterial",  0.02,  6, "SUP-006"),
    ("MAT-020", "Adhesive Product Labels",      "APL-020", "PackagingMaterial",  0.01,  5, "SUP-005"),
    ("MAT-021", "Pallet Wrap Film",             "PWF-021", "PackagingMaterial",  0.50,  5, "SUP-006"),
    ("MAT-022", "Desiccant Sachets",            "DSC-022", "PackagingMaterial",  0.08, 10, "SUP-005"),
    ("MAT-023", "Nitrogen Purge Gas",           "NPG-023", "PackagingMaterial",  2.00,  3, "SUP-005"),
    ("MAT-024", "Calibration Certificate Card", "CCC-024", "PackagingMaterial",  0.12,  8, "SUP-006"),
    ("MAT-025", "Tamper-Evident Seal",          "TES-025", "PackagingMaterial",  0.05,  5, "SUP-005"),
]
write_csv(os.path.join(LH, "DimMaterial.csv"),
          ["MaterialId","Material_Name","Material_PartNumber","Material_Class","Material_UnitCost","Material_LeadTimeDays","SupplierId"],
          materials)

# =============================================================================
# 4) DimSupplier  (10 rows)
# =============================================================================
suppliers = [
    ("SUP-001", "Toray Carbon Fibers",       1, "Japan",       4.7, "true", "EQP-009"),
    ("SUP-002", "NanoSilver Tech Korea",      1, "South Korea", 4.5, "true", "EQP-010"),
    ("SUP-003", "CopperTrace GmbH",           1, "Germany",     4.8, "true", "EQP-011"),
    ("SUP-004", "FR4-Global Inc",             1, "Taiwan",      4.6, "true", "EQP-012"),
    ("SUP-005", "PolyCoat Industries",        2, "USA",         4.3, "true", "EQP-013"),
    ("SUP-006", "FlexConnect Ltd",            2, "UK",          4.1, "true", "EQP-014"),
    ("SUP-007", "SensorPak GmbH",             1, "Germany",     4.4, "true", "EQP-015"),
    ("SUP-008", "CleanRoom Supplies BV",      2, "Netherlands", 4.9, "true", "EQP-013"),
    ("SUP-009", "PackSafe Industries",        1, "USA",         4.2, "true", "EQP-010"),
    ("SUP-010", "ShieldTech Corp",            2, "USA",         4.0, "true", "EQP-002"),
]
write_csv(os.path.join(LH, "DimSupplier.csv"),
          ["SupplierId","Supplier_Name","Supplier_Tier","Supplier_Country","Supplier_Rating","Supplier_Certified","EquipmentId"],
          suppliers)

# =============================================================================
# 5) DimEquipment  (160 rows)
# =============================================================================

# Machine type mapping: tea → zava
MACHINE_MAP = {
    "TeaBagFormer":    "FiberWeaver",
    "LabelApplicator": "LabelApplicator",
    "CasePacker":      "CasePacker",
    "Cartoner":        "Laminator",
    "StackerUnit":     "StackerUnit",
    "BulkPacker":      "BulkPacker",
    "BoxFormer":       "BoxFormer",
    "MetalDetector":   "ConductivityTester",
    "PouchSealer":     "HeatSealer",
    "Overwrapper":     "HeatPress",
    "FilmWrapper":     "ShieldWrapper",
    "CartoonPacker":   "CartoonPacker",
    "ConveyorBelt":    "ConveyorBelt",
    "FoilWrapper":     "ESDWrapper",
    "PackingRobot":    "PackingRobot",
    "EnvelopeMachine": "SensorPlacer",
    "SealingUnit":     "TensileTestRig",
    "TrayFormer":      "TrayFormer",
}

ETYPE_MAP = {
    "Forming":        "Weaving",
    "Packing":        "Packing",
    "Wrapping":       "Laminating",
    "Transport":      "Transport",
    "QualityControl": "QualityControl",
}

LINE_MAP = {
    "PackLine-Alpha":   "WeaveLine-Alpha",
    "PackLine-Bravo":   "WeaveLine-Bravo",
    "PackLine-Charlie": "WeaveLine-Charlie",
    "PackLine-Delta":   "WeaveLine-Delta",
    "PackLine-Echo":    "WeaveLine-Echo",
    "PackLine-Foxtrot": "WeaveLine-Foxtrot",
    "PackLine-Golf":    "WeaveLine-Golf",
    "PackLine-Hotel":   "WeaveLine-Hotel",
    "PackLine-India":   "WeaveLine-India",
    "PackLine-Juliet":  "WeaveLine-Juliet",
    "PackLine-Kilo":    "WeaveLine-Kilo",
}

# Fixed equipment: Sites, Areas, WorkCenters, Supplier depots
fixed_equipment = [
    ("EQP-001", "Zava Redmond Innovation Center",  "Site",       "CoatingDev",      "Redmond WA USA",     50000),
    ("EQP-002", "Zava Portland Production Campus",  "Site",       "Production",      "Portland OR USA",    80000000),
    ("EQP-003", "Zava Distribution Hub",             "Site",       "Distribution",    "Portland OR USA",    100000000),
    ("EQP-004", "Coating Development Lab",           "Area",       "CoatingDev",      "Redmond WA USA",     25000),
    ("EQP-005", "Weave Hall A",                      "WorkCenter", "Weaving",         "Portland OR USA",    40000000),
    ("EQP-006", "Weave Hall B",                      "WorkCenter", "Weaving",         "Portland OR USA",    40000000),
    ("EQP-007", "QA & Testing Laboratory",           "Area",       "QualityControl",  "Redmond WA USA",     0),
    ("EQP-008", "Finished Goods Warehouse",          "Area",       "Warehouse",       "Portland OR USA",    50000000),
    ("EQP-009", "Toray Iiyama Carbon Plant",         "Site",       "Supplier",        "Iiyama Japan",       10000),
    ("EQP-010", "NanoSilver Daejeon Lab",            "Site",       "Supplier",        "Daejeon South Korea",15000),
    ("EQP-011", "CopperTrace Dresden Hub",           "Site",       "Supplier",        "Dresden Germany",    12000),
    ("EQP-012", "FR4-Global Taoyuan Fab",            "Site",       "Supplier",        "Taoyuan Taiwan",     20000),
    ("EQP-013", "PolyCoat Austin Facility",          "Site",       "Supplier",        "Austin TX USA",      0),
    ("EQP-014", "FlexConnect Bristol Works",         "Site",       "Supplier",        "Bristol UK",         0),
    ("EQP-015", "SensorPak Stuttgart Center",        "Site",       "Supplier",        "Stuttgart Germany",  8000),
]

# Line WorkCenters (EQP-150 to EQP-160)
line_names = ["Alpha","Bravo","Charlie","Delta","Echo","Foxtrot","Golf","Hotel","India","Juliet","Kilo"]
line_equipment = []
for i, name in enumerate(line_names):
    eid = f"EQP-{150+i:03d}"
    line_equipment.append((eid, f"WeaveLine-{name}", "WorkCenter", "Weaving", "Portland OR USA", 20000000))

# WorkUnit machines (EQP-016 to EQP-149): read from tea and transform
tea_equip_path = os.path.join(os.path.dirname(BASE), "TeaManufacturing-ISA95", "Data", "Lakehouse", "DimEquipment.csv")
work_units = []
with open(tea_equip_path, "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        eid = row["EquipmentId"]
        # Only transform WorkUnit machines (EQP-016 to EQP-149)
        num = int(eid.split("-")[1])
        if num < 16 or num > 149:
            continue
        old_name = row["Equipment_Name"]
        old_type = row["Equipment_Type"]

        # Parse: {LineLetter}-{MachineType}-{Number}
        parts = old_name.split("-", 1)
        line_letter = parts[0]  # e.g. "Bravo"
        rest = parts[1] if len(parts) > 1 else ""
        # Find machine type and number
        new_rest = rest
        for old_mt, new_mt in MACHINE_MAP.items():
            if old_mt in rest:
                new_rest = rest.replace(old_mt, new_mt)
                break
        new_name = f"{line_letter}-{new_rest}"
        new_type = ETYPE_MAP.get(old_type, old_type)
        work_units.append((eid, new_name, "WorkUnit", new_type, "Portland OR USA", 0))

all_equipment = fixed_equipment + line_equipment + work_units
# Sort by EQP number for deterministic output
all_equipment.sort(key=lambda x: int(x[0].split("-")[1]))

write_csv(os.path.join(LH, "DimEquipment.csv"),
          ["EquipmentId","Equipment_Name","Equipment_Level","Equipment_Type","Equipment_Location","Equipment_Capacity"],
          all_equipment)

# =============================================================================
# 6) DimProductionOrder  (20 rows)
# =============================================================================
orders = [
    ("ORD-001", "WO-2025-3001", 10000, "Normal", "2025-11-15T00:00:00", "Complete",   "BTC-001"),
    ("ORD-002", "WO-2025-3002", 10000, "Normal", "2025-11-16T00:00:00", "Complete",   "BTC-002"),
    ("ORD-003", "WO-2025-3003",  8000, "High",   "2025-11-17T00:00:00", "Complete",   "BTC-003"),
    ("ORD-004", "WO-2025-3004",  8000, "Normal", "2025-11-18T00:00:00", "Complete",   "BTC-004"),
    ("ORD-005", "WO-2025-3005",  5000, "Normal", "2025-11-19T00:00:00", "Complete",   "BTC-005"),
    ("ORD-006", "WO-2025-3006",  5000, "Normal", "2025-11-20T00:00:00", "Complete",   "BTC-006"),
    ("ORD-007", "WO-2025-3007",  6000, "Normal", "2025-11-21T00:00:00", "Complete",   "BTC-007"),
    ("ORD-008", "WO-2025-3008",  6000, "High",   "2025-11-22T00:00:00", "Complete",   "BTC-008"),
    ("ORD-009", "WO-2025-3009",  3000, "High",   "2025-11-23T00:00:00", "Complete",   "BTC-009"),
    ("ORD-010", "WO-2025-3010",  3000, "Normal", "2025-11-24T00:00:00", "Complete",   "BTC-010"),
    ("ORD-011", "WO-2025-3011", 10000, "Normal", "2025-11-28T00:00:00", "InProgress", "BTC-011"),
    ("ORD-012", "WO-2025-3012",  8000, "High",   "2025-11-29T00:00:00", "InProgress", "BTC-012"),
    ("ORD-013", "WO-2025-3013",  5000, "Normal", "2025-11-30T00:00:00", "InProgress", "BTC-013"),
    ("ORD-014", "WO-2025-3014",  6000, "Normal", "2025-12-01T00:00:00", "Planned",    "BTC-014"),
    ("ORD-015", "WO-2025-3015", 15000, "Rush",   "2025-12-03T00:00:00", "Planned",    "BTC-015"),
    ("ORD-016", "WO-2025-3016",  7000, "Normal", "2025-11-25T00:00:00", "Complete",   "BTC-016"),
    ("ORD-017", "WO-2025-3017",  4000, "High",   "2025-11-26T00:00:00", "Complete",   "BTC-017"),
    ("ORD-018", "WO-2025-3018",  3000, "Normal", "2025-12-02T00:00:00", "InProgress", "BTC-018"),
    ("ORD-019", "WO-2025-3019", 12000, "Normal", "2025-12-05T00:00:00", "Planned",    "BTC-019"),
    ("ORD-020", "WO-2025-3020", 20000, "Rush",   "2025-12-07T00:00:00", "Planned",    "BTC-020"),
]
write_csv(os.path.join(LH, "DimProductionOrder.csv"),
          ["OrderId","Order_Number","Order_Quantity","Order_Priority","Order_DueDate","Order_Status","BatchId"],
          orders)

# =============================================================================
# 7) FactQualityTest  (30 rows)
# =============================================================================
tests = [
    ("TST-001", "ConductivityTest",   "Pass",            "Routine conductivity check on Field Standard coating",             "2025-11-10T10:00:00", "Approved",                              "SEG-001"),
    ("TST-002", "TensileStrength",     "Pass",            "Tensile strength within spec after fiber coating",                 "2025-11-10T11:30:00", "Approved",                              "SEG-001"),
    ("TST-003", "MeshGaugeCheck",      "Pass",            "Mesh gauge 0.8mm within tolerance",                               "2025-11-12T08:00:00", "Approved",                              "SEG-002"),
    ("TST-004", "VisualInspection",    "Pass",            "Sensor alignment and placement integrity check passed",            "2025-11-13T10:00:00", "Approved",                              "SEG-003"),
    ("TST-005", "ConductivityTest",    "Pass",            "Routine conductivity check for Field Standard",                    "2025-11-11T10:00:00", "Approved",                              "SEG-005"),
    ("TST-006", "MeshGaugeCheck",      "Fail",            "Mesh gauge underspec - 0.6mm detected",                            "2025-11-13T08:30:00", "Loom recalibrated",                     "SEG-006"),
    ("TST-007", "ConductivityTest",    "Pass",            "Field Slim conductivity profile approved",                         "2025-11-12T10:00:00", "Approved",                              "SEG-009"),
    ("TST-008", "TensileStrength",     "Pass",            "Carbon nanotube tensile integration OK",                           "2025-11-12T11:00:00", "Approved",                              "SEG-009"),
    ("TST-009", "ContaminationTest",   "Pass",            "No foreign particulates detected in cleanroom",                    "2025-11-14T09:00:00", "Approved",                              "SEG-010"),
    ("TST-010", "ConductivityTest",    "Fail",            "Low conductivity in Field Slim batch - coating under-deposited",   "2025-11-13T10:00:00", "Batch reworked with additional coating", "SEG-013"),
    ("TST-011", "MeshGaugeCheck",      "Pass",            "Gauge within tolerance 0.8mm +/- 0.05mm",                          "2025-11-15T08:00:00", "Approved",                              "SEG-014"),
    ("TST-012", "VisualInspection",    "Pass",            "Sensor module alignment and solder joint check OK",                "2025-11-16T10:00:00", "Approved",                              "SEG-015"),
    ("TST-013", "ConductivityTest",    "Pass",            "Systems Pro mesh conductivity approved",                            "2025-11-14T10:00:00", "Approved",                              "SEG-017"),
    ("TST-014", "TensileStrength",     "ConditionalPass", "Tensile at lower limit 180 MPa - monitor next batch",              "2025-11-14T11:30:00", "Conditional release",                   "SEG-017"),
    ("TST-015", "MeshGaugeCheck",      "Pass",            "Gauge check passed",                                               "2025-11-16T08:00:00", "Approved",                              "SEG-018"),
    ("TST-016", "ContaminationTest",   "Pass",            "Cleanroom particle count and ESD check clear",                      "2025-11-17T09:00:00", "Approved",                              "SEG-019"),
    ("TST-017", "ConductivityTest",    "Pass",            "Systems Pro batch 2 approved",                                      "2025-11-15T10:00:00", "Approved",                              "SEG-021"),
    ("TST-018", "MeshGaugeCheck",      "Pass",            "Gauge check passed",                                               "2025-11-17T08:00:00", "Approved",                              "SEG-022"),
    ("TST-019", "ConductivityTest",    "Pass",            "Systems Elite signal integrity and conductivity OK",                "2025-11-16T10:00:00", "Approved",                              "SEG-025"),
    ("TST-020", "TensileStrength",     "Fail",            "Tensile too low at 145 MPa - coating delamination observed",        "2025-11-16T11:30:00", "Additional coating cycle applied",      "SEG-025"),
    ("TST-021", "MeshGaugeCheck",      "Pass",            "Gauge 0.4mm within micro-mesh spec",                                "2025-11-18T08:00:00", "Approved",                              "SEG-026"),
    ("TST-022", "VisualInspection",    "Fail",            "Sensor misalignment on 3% of units - pick-and-place offset",        "2025-11-19T10:00:00", "Pick-and-place recalibrated and units reworked", "SEG-027"),
    ("TST-023", "ContaminationTest",   "Pass",            "No conductive particle contamination detected",                      "2025-11-18T09:00:00", "Approved",                              "SEG-026"),
    ("TST-024", "Audit",               "Pass",            "QMS audit - cleanroom class and ISO 14644 compliance",               "2025-11-20T14:00:00", "Certified",                             "SEG-028"),
    ("TST-025", "ConductivityTest",    "Pass",            "Routine conductivity - Field Standard (in progress)",                "2025-11-25T10:00:00", "Approved",                              "SEG-029"),
    ("TST-026", "TensileStrength",     "Pass",            "Fiber tensile at 210 MPa",                                          "2025-11-25T11:00:00", "Approved",                              "SEG-029"),
    ("TST-027", "ConductivityTest",    "ConditionalPass", "Field Slim batch - conductivity slightly below target",              "2025-11-26T10:00:00", "Additional nanowire applied",           "SEG-030"),
    ("TST-028", "VisualInspection",    "Pass",            "Packaging label and seal quality check passed",                      "2025-11-14T15:00:00", "Approved",                              "SEG-004"),
    ("TST-029", "Audit",               "Pass",            "Annual supplier raw material traceability audit",                    "2025-11-22T10:00:00", "Certified",                             "SEG-008"),
    ("TST-030", "MeshGaugeCheck",      "Pass",            "Final carton gauge verification",                                   "2025-11-20T12:00:00", "Approved",                              "SEG-028"),
]
write_csv(os.path.join(LH, "FactQualityTest.csv"),
          ["TestId","Test_Type","Test_Result","Test_Description","Test_Timestamp","Test_Resolution","SegmentId"],
          tests)

# =============================================================================
# 8) FactShipment  (25 rows)
# =============================================================================
shipments = [
    ("SHP-001", "TRK-2025-5001", "Delivered",  "2025-10-20T06:00:00", "2025-10-28T14:00:00", "PacificFreight Global",      "EQP-009", "EQP-001"),
    ("SHP-002", "TRK-2025-5002", "Delivered",  "2025-10-22T08:00:00", "2025-10-29T16:00:00", "KoreaLogistics Express",      "EQP-010", "EQP-001"),
    ("SHP-003", "TRK-2025-5003", "Delivered",  "2025-10-18T10:00:00", "2025-10-27T12:00:00", "EuroAir Cargo",               "EQP-011", "EQP-001"),
    ("SHP-004", "TRK-2025-5004", "Delivered",  "2025-10-25T07:00:00", "2025-11-02T09:00:00", "TaiwanCargo Express",         "EQP-012", "EQP-001"),
    ("SHP-005", "TRK-2025-5005", "Delivered",  "2025-10-28T10:00:00", "2025-10-30T14:00:00", "USFreight Inc",               "EQP-013", "EQP-002"),
    ("SHP-006", "TRK-2025-5006", "Delivered",  "2025-10-29T08:00:00", "2025-11-01T12:00:00", "TransAtlantic Freight",       "EQP-014", "EQP-002"),
    ("SHP-007", "TRK-2025-5007", "Delivered",  "2025-10-15T06:00:00", "2025-10-24T10:00:00", "EuroAir Cargo",               "EQP-015", "EQP-001"),
    ("SHP-008", "TRK-2025-5008", "Delivered",  "2025-10-30T07:00:00", "2025-11-05T11:00:00", "PacificFreight Global",       "EQP-009", "EQP-001"),
    ("SHP-009", "TRK-2025-5009", "Delivered",  "2025-10-26T09:00:00", "2025-10-28T15:00:00", "USFreight Inc",               "EQP-013", "EQP-002"),
    ("SHP-010", "TRK-2025-5010", "Delivered",  "2025-11-01T06:00:00", "2025-11-08T14:00:00", "KoreaLogistics Express",      "EQP-010", "EQP-001"),
    ("SHP-011", "TRK-2025-5011", "InTransit",  "2025-11-10T08:00:00", "2025-11-18T16:00:00", "EuroAir Cargo",               "EQP-011", "EQP-001"),
    ("SHP-012", "TRK-2025-5012", "InTransit",  "2025-11-12T07:00:00", "2025-11-20T10:00:00", "TaiwanCargo Express",         "EQP-012", "EQP-001"),
    ("SHP-013", "TRK-2025-5013", "Delivered",  "2025-11-05T10:00:00", "2025-11-07T14:00:00", "USFreight Inc",               "EQP-013", "EQP-002"),
    ("SHP-014", "TRK-2025-5014", "Pending",    "2025-11-20T08:00:00", "2025-11-22T12:00:00", "TransAtlantic Freight",       "EQP-014", "EQP-002"),
    ("SHP-015", "TRK-2025-5015", "Delivered",  "2025-11-03T06:00:00", "2025-11-12T09:00:00", "EuroAir Cargo",               "EQP-015", "EQP-001"),
    ("SHP-016", "TRK-2025-5016", "Delivered",  "2025-11-16T06:00:00", "2025-11-16T14:00:00", "Pacific Northwest Trucking",  "EQP-002", "EQP-003"),
    ("SHP-017", "TRK-2025-5017", "Delivered",  "2025-11-17T06:00:00", "2025-11-17T14:00:00", "Pacific Northwest Trucking",  "EQP-002", "EQP-003"),
    ("SHP-018", "TRK-2025-5018", "Delivered",  "2025-11-18T06:00:00", "2025-11-18T12:00:00", "Pacific Northwest Trucking",  "EQP-002", "EQP-003"),
    ("SHP-019", "TRK-2025-5019", "Delivered",  "2025-11-20T06:00:00", "2025-11-20T14:00:00", "Pacific Northwest Trucking",  "EQP-002", "EQP-003"),
    ("SHP-020", "TRK-2025-5020", "Delivered",  "2025-11-22T06:00:00", "2025-11-22T12:00:00", "Pacific Northwest Trucking",  "EQP-002", "EQP-003"),
    ("SHP-021", "TRK-2025-5021", "InTransit",  "2025-11-24T06:00:00", "2025-11-24T14:00:00", "Pacific Northwest Trucking",  "EQP-002", "EQP-003"),
    ("SHP-022", "TRK-2025-5022", "Delivered",  "2025-11-25T06:00:00", "2025-11-25T12:00:00", "Pacific Northwest Trucking",  "EQP-002", "EQP-003"),
    ("SHP-023", "TRK-2025-5023", "InTransit",  "2025-11-26T07:00:00", "2025-11-26T15:00:00", "Pacific Northwest Trucking",  "EQP-002", "EQP-003"),
    ("SHP-024", "TRK-2025-5024", "Pending",    "2025-11-28T06:00:00", "2025-11-28T14:00:00", "Pacific Northwest Trucking",  "EQP-002", "EQP-003"),
    ("SHP-025", "TRK-2025-5025", "Delivered",  "2025-11-02T06:00:00", "2025-11-09T14:00:00", "KoreaLogistics Express",      "EQP-010", "EQP-001"),
]
write_csv(os.path.join(LH, "FactShipment.csv"),
          ["ShipmentId","Shipment_TrackingNum","Shipment_Status","Shipment_DepartureDate","Shipment_ArrivalDate","Shipment_Carrier","OriginEquipmentId","DestEquipmentId"],
          shipments)

# =============================================================================
# 9) EdgeSegmentMaterial  (same structure as tea — 97 rows)
# =============================================================================
# Segment-Material mapping: same material IDs, same relationships.
# Coating segments use raw fibers/coatings, Weaving uses sensor modules + desiccant,
# SensorEmbed uses PCB/solder/adhesive, Packaging uses packaging materials.
edge_seg_mat = [
    # Batch 1 Coating (SEG-001): raw materials
    ("SEG-001","MAT-002"), ("SEG-001","MAT-003"), ("SEG-001","MAT-007"),
    # Batch 2 Coating (SEG-005)
    ("SEG-005","MAT-002"), ("SEG-005","MAT-003"), ("SEG-005","MAT-007"),
    # Batch 3 Coating (SEG-009): nanowire + trace + CNT + elastane
    ("SEG-009","MAT-002"), ("SEG-009","MAT-003"), ("SEG-009","MAT-006"), ("SEG-009","MAT-009"),
    # Batch 4 Coating (SEG-013)
    ("SEG-013","MAT-002"), ("SEG-013","MAT-003"), ("SEG-013","MAT-006"), ("SEG-013","MAT-009"),
    # Batch 5 Coating (SEG-017): FR-4 substrate
    ("SEG-017","MAT-004"),
    # Batch 6 Coating (SEG-021): FR-4
    ("SEG-021","MAT-004"),
    # Batch 7 Coating (SEG-025): conductive coating + nylon
    ("SEG-025","MAT-005"), ("SEG-025","MAT-010"),
    # InProgress batch 11 Coating (SEG-029)
    ("SEG-029","MAT-002"), ("SEG-029","MAT-003"), ("SEG-029","MAT-007"),
    # InProgress batch 12 Coating (SEG-030)
    ("SEG-030","MAT-002"), ("SEG-030","MAT-003"), ("SEG-030","MAT-006"), ("SEG-030","MAT-009"),
    # Weaving segments use sensor modules + desiccant
    ("SEG-002","MAT-011"), ("SEG-002","MAT-022"),
    ("SEG-006","MAT-011"), ("SEG-006","MAT-022"),
    ("SEG-010","MAT-011"), ("SEG-010","MAT-022"),
    ("SEG-014","MAT-011"), ("SEG-014","MAT-022"),
    ("SEG-018","MAT-011"), ("SEG-018","MAT-022"),
    ("SEG-022","MAT-011"), ("SEG-022","MAT-022"),
    ("SEG-026","MAT-011"), ("SEG-026","MAT-022"),
    # SensorEmbed segments use PCB, solder, adhesive
    ("SEG-003","MAT-012"), ("SEG-003","MAT-013"), ("SEG-003","MAT-014"),
    ("SEG-007","MAT-012"), ("SEG-007","MAT-013"), ("SEG-007","MAT-014"),
    ("SEG-011","MAT-012"), ("SEG-011","MAT-013"), ("SEG-011","MAT-014"),
    ("SEG-015","MAT-012"), ("SEG-015","MAT-013"), ("SEG-015","MAT-014"),
    ("SEG-019","MAT-012"), ("SEG-019","MAT-013"), ("SEG-019","MAT-014"),
    ("SEG-023","MAT-012"), ("SEG-023","MAT-013"), ("SEG-023","MAT-014"),
    ("SEG-027","MAT-012"), ("SEG-027","MAT-013"), ("SEG-027","MAT-014"),
    # Packaging segments use packaging materials
    ("SEG-004","MAT-015"), ("SEG-004","MAT-016"), ("SEG-004","MAT-019"), ("SEG-004","MAT-020"), ("SEG-004","MAT-018"),
    ("SEG-008","MAT-015"), ("SEG-008","MAT-016"), ("SEG-008","MAT-019"), ("SEG-008","MAT-020"), ("SEG-008","MAT-018"),
    ("SEG-012","MAT-015"), ("SEG-012","MAT-017"), ("SEG-012","MAT-019"), ("SEG-012","MAT-020"), ("SEG-012","MAT-018"),
    ("SEG-016","MAT-015"), ("SEG-016","MAT-017"), ("SEG-016","MAT-019"), ("SEG-016","MAT-020"), ("SEG-016","MAT-018"),
    ("SEG-020","MAT-015"), ("SEG-020","MAT-016"), ("SEG-020","MAT-019"), ("SEG-020","MAT-020"), ("SEG-020","MAT-018"),
    ("SEG-024","MAT-015"), ("SEG-024","MAT-016"), ("SEG-024","MAT-019"), ("SEG-024","MAT-020"), ("SEG-024","MAT-018"),
    ("SEG-028","MAT-015"), ("SEG-028","MAT-016"), ("SEG-028","MAT-019"), ("SEG-028","MAT-020"), ("SEG-028","MAT-018"),
]
write_csv(os.path.join(LH, "EdgeSegmentMaterial.csv"),
          ["SegmentId","MaterialId"],
          edge_seg_mat)

# =============================================================================
# 10) EdgeShipmentMaterial  (same FK structure — 58 rows)
# =============================================================================
edge_ship_mat = [
    ("SHP-001","MAT-001"), ("SHP-001","MAT-008"),
    ("SHP-002","MAT-002"),
    ("SHP-003","MAT-003"),
    ("SHP-004","MAT-004"),
    ("SHP-005","MAT-011"), ("SHP-005","MAT-014"), ("SHP-005","MAT-015"), ("SHP-005","MAT-022"), ("SHP-005","MAT-023"), ("SHP-005","MAT-025"),
    ("SHP-006","MAT-016"), ("SHP-006","MAT-017"), ("SHP-006","MAT-018"), ("SHP-006","MAT-019"), ("SHP-006","MAT-021"), ("SHP-006","MAT-024"),
    ("SHP-007","MAT-005"), ("SHP-007","MAT-009"), ("SHP-007","MAT-010"),
    ("SHP-008","MAT-001"),
    ("SHP-009","MAT-020"), ("SHP-009","MAT-012"), ("SHP-009","MAT-013"),
    ("SHP-010","MAT-002"), ("SHP-010","MAT-007"),
    ("SHP-011","MAT-003"),
    ("SHP-012","MAT-004"),
    ("SHP-013","MAT-011"), ("SHP-013","MAT-014"), ("SHP-013","MAT-015"), ("SHP-013","MAT-025"),
    ("SHP-014","MAT-016"), ("SHP-014","MAT-017"), ("SHP-014","MAT-018"), ("SHP-014","MAT-019"),
    ("SHP-015","MAT-005"), ("SHP-015","MAT-009"),
    ("SHP-016","MAT-016"), ("SHP-016","MAT-015"),
    ("SHP-017","MAT-016"), ("SHP-017","MAT-015"),
    ("SHP-018","MAT-017"), ("SHP-018","MAT-015"),
    ("SHP-019","MAT-017"), ("SHP-019","MAT-015"),
    ("SHP-020","MAT-016"), ("SHP-020","MAT-015"),
    ("SHP-021","MAT-016"), ("SHP-021","MAT-015"),
    ("SHP-022","MAT-016"), ("SHP-022","MAT-018"),
    ("SHP-023","MAT-017"), ("SHP-023","MAT-018"),
    ("SHP-024","MAT-016"), ("SHP-024","MAT-018"),
    ("SHP-025","MAT-002"), ("SHP-025","MAT-007"),
]
write_csv(os.path.join(LH, "EdgeShipmentMaterial.csv"),
          ["ShipmentId","MaterialId"],
          edge_ship_mat)

# =============================================================================
# 11) EdgeShipmentOrigin  (25 rows — same EQP FKs)
# =============================================================================
edge_ship_orig = [
    ("SHP-001","EQP-009"), ("SHP-002","EQP-010"), ("SHP-003","EQP-011"),
    ("SHP-004","EQP-012"), ("SHP-005","EQP-013"), ("SHP-006","EQP-014"),
    ("SHP-007","EQP-015"), ("SHP-008","EQP-009"), ("SHP-009","EQP-013"),
    ("SHP-010","EQP-010"), ("SHP-011","EQP-011"), ("SHP-012","EQP-012"),
    ("SHP-013","EQP-013"), ("SHP-014","EQP-014"), ("SHP-015","EQP-015"),
    ("SHP-016","EQP-002"), ("SHP-017","EQP-002"), ("SHP-018","EQP-002"),
    ("SHP-019","EQP-002"), ("SHP-020","EQP-002"), ("SHP-021","EQP-002"),
    ("SHP-022","EQP-002"), ("SHP-023","EQP-002"), ("SHP-024","EQP-002"),
    ("SHP-025","EQP-010"),
]
write_csv(os.path.join(LH, "EdgeShipmentOrigin.csv"),
          ["ShipmentId","EquipmentId"],
          edge_ship_orig)

# =============================================================================
# 12) EdgeShipmentDestination  (25 rows — same EQP FKs)
# =============================================================================
edge_ship_dest = [
    ("SHP-001","EQP-001"), ("SHP-002","EQP-001"), ("SHP-003","EQP-001"),
    ("SHP-004","EQP-001"), ("SHP-005","EQP-002"), ("SHP-006","EQP-002"),
    ("SHP-007","EQP-001"), ("SHP-008","EQP-001"), ("SHP-009","EQP-002"),
    ("SHP-010","EQP-001"), ("SHP-011","EQP-001"), ("SHP-012","EQP-001"),
    ("SHP-013","EQP-002"), ("SHP-014","EQP-002"), ("SHP-015","EQP-001"),
    ("SHP-016","EQP-003"), ("SHP-017","EQP-003"), ("SHP-018","EQP-003"),
    ("SHP-019","EQP-003"), ("SHP-020","EQP-003"), ("SHP-021","EQP-003"),
    ("SHP-022","EQP-003"), ("SHP-023","EQP-003"), ("SHP-024","EQP-003"),
    ("SHP-025","EQP-001"),
]
write_csv(os.path.join(LH, "EdgeShipmentDestination.csv"),
          ["ShipmentId","EquipmentId"],
          edge_ship_dest)

# =============================================================================
# EVENTHOUSE SEED TRANSFORMS
# =============================================================================
print("\n--- Eventhouse Seeds ---")

# SKU mapping: anything starting with "GL " → "ZC " + Zava product name
SKU_MAP = {
    "GL English Breakfast":    "ZC Field Standard",
    "GL Earl Grey":            "ZC Field Slim",
    "GL Green Tea":            "ZC Systems Pro",
    "GL Chamomile":            "ZC Systems Elite",
    "GL Darjeeling":           "ZC Field Micro",
    "GL Rooibos Sunset":       "ZC Field Active",
    "GL Jasmine Dragon":       "ZC Systems Max",
    "GL Sencha":               "ZC Systems Nano",
    "GL Kenyan Bold":          "ZC Field Flex",
    "GL Nilgiri Frost":        "ZC Systems Compact",
}

def transform_line_name(val):
    """PackLine-X → WeaveLine-X"""
    if val and val.startswith("PackLine-"):
        return val.replace("PackLine-", "WeaveLine-")
    return val

def transform_sku(val):
    """GL xxx → ZC xxx"""
    if not val:
        return val
    for old, new in SKU_MAP.items():
        if val == old:
            return new
    # Fallback: replace "GL " prefix
    if val.startswith("GL "):
        return "ZC " + val[3:]
    return val

# Column header renames
HEADER_MAP = {
    "BagCount":        "UnitCount",
    "BagCountDelta":   "UnitCountDelta",
    "TeaProducedGram": "FiberProducedGram",
    "BagsRejected":    "UnitsRejected",
    "TeaRejectedGram": "FiberRejectedGram",
}

def transform_eventhouse(src_file, dst_file):
    """Read tea Eventhouse seed, transform headers+values, write Zava seed."""
    with open(src_file, "r") as f:
        reader = csv.DictReader(f)
        old_headers = reader.fieldnames
        new_headers = [HEADER_MAP.get(h, h) for h in old_headers]

        rows = []
        for row in reader:
            new_row = []
            for h in old_headers:
                val = row[h]
                if h == "LineName":
                    val = transform_line_name(val)
                elif h == "SKU":
                    val = transform_sku(val)
                new_row.append(val)
            rows.append(new_row)

    with open(dst_file, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(new_headers)
        w.writerows(rows)
    print(f"  ✓ {os.path.basename(dst_file)}: {len(rows)} rows (transformed)")

# Transform all 4 Eventhouse seeds
for fname in ["EquipmentTelemetry.csv", "MachineStateTelemetry.csv",
              "ProcessSegmentTelemetry.csv", "ProductionCounterTelemetry.csv"]:
    src = os.path.join(TEA_EH, fname)
    dst = os.path.join(EH, fname)
    if os.path.exists(src):
        transform_eventhouse(src, dst)
    else:
        print(f"  ⚠ {fname}: source not found at {src}")

print("\n✅ All Zava data files generated successfully!")
