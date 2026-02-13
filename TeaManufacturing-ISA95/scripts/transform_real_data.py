#!/usr/bin/env python3
"""
Transform real factory machine data into the Golden Leaf Tea Co. demo dataset.

Produces 4 Eventhouse CSVs covering July 2025 – July 2026:
  1. MachineStateTelemetry.csv   (from real Machine State data, tiled over 12 months)
  2. ProductionCounterTelemetry.csv (from real OEE data, tiled over 12 months)
  3. ProcessSegmentTelemetry.csv  (synthetic, ~300K+ rows for all 30 segments)
  4. EquipmentTelemetry.csv       (synthetic, ~200K+ rows for 15 equipment items)

Also produces an expanded DimEquipment.csv with WorkUnit-level machines.
"""

import csv
import os
import random
import math
from datetime import datetime, timedelta
from collections import defaultdict

random.seed(42)

# ── paths ──────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(os.path.dirname(BASE), "tmp")
SRC_MS = os.path.join(TMP, "Calcukated Machine State Data.csv")
SRC_OEE = os.path.join(TMP, "Calculated OEE data.csv")
OUT_EH = os.path.join(BASE, "Data", "Eventhouse")
OUT_LH = os.path.join(BASE, "Data", "Lakehouse")

# ── Demo timeline ─────────────────────────────────────────────────────────────
DEMO_START = datetime(2025, 7, 1, 0, 0, 0)
DEMO_END = datetime(2026, 7, 1, 0, 0, 0)
DEMO_SPAN_SEC = (DEMO_END - DEMO_START).total_seconds()

# Original data range: 2023-12-16 04:41:00 → 2024-01-12 14:19:28  (~27.4 days)
ORIG_START = datetime(2023, 12, 16, 4, 41, 0)
ORIG_END = datetime(2024, 1, 12, 14, 20, 0)
ORIG_SPAN_SEC = (ORIG_END - ORIG_START).total_seconds()

# Number of times to tile the original data to fill the demo window
TILE_COUNT = math.ceil(DEMO_SPAN_SEC / ORIG_SPAN_SEC)  # ~13

# ── Line mapping  (11 real lines → 11 fictional) ──────────────────────────────
LINE_MAP = {
    "Line 1":  "PackLine-Alpha",
    "Line 3":  "PackLine-Bravo",
    "Line 4A": "PackLine-Charlie",
    "Line 4B": "PackLine-Delta",
    "Line 7":  "PackLine-Echo",
    "Line 9":  "PackLine-Foxtrot",
    "Line 10": "PackLine-Golf",
    "Line 12": "PackLine-Hotel",
    "Line 13": "PackLine-India",
    "Line 14": "PackLine-Juliet",
    "Line 15": "PackLine-Kilo",
}

# ── Machine-type prefix mapping ───────────────────────────────────────────────
# Real name root → (demo type, demo suffix pattern)
MACHINE_TYPE_MAP = {
    "Perfecta":      "TeaBagFormer",
    "Cermex":        "CasePacker",
    "Mohrbach":      "Cartoner",
    "Sandiacre":     "Overwrapper",
    "BFB":           "BulkPacker",
    "GBE":           "EnvelopeMachine",
    "Kliklok":       "BoxFormer",
    "IMA":           "SealingUnit",
    "Conveyor":      "ConveyorBelt",
    "EB_Conveyor":   "ConveyorBelt",
    "FB_Conveyor":   "ConveyorBelt",
    "ME":            "MetalDetector",
    "Cobot":         "PackingRobot",
    "Cama":          "CartoonPacker",
    "Petri":         "LabelApplicator",
    "Sollas":        "FilmWrapper",
    "Vara":          "StackerUnit",
    "Bradman_Lake":  "TrayFormer",
    "Apsol":         "PouchSealer",
    "Corazza":       "FoilWrapper",
    "Mohrbach_MKV":  "Cartoner",
    "Mohrbach_MWA":  "Cartoner",
}

# Cache for deterministic machine-name remapping
_machine_name_cache = {}

def remap_machine_name(orig: str) -> str:
    """L3_Perfecta1 → Bravo-TeaBagFormer-01"""
    if orig in _machine_name_cache:
        return _machine_name_cache[orig]
    if not orig or orig in ("MachineName", "NULL", " "):
        _machine_name_cache[orig] = orig
        return orig

    # Parse line prefix
    parts = orig.split("_", 1)
    if len(parts) < 2:
        _machine_name_cache[orig] = orig
        return orig

    line_prefix = parts[0]  # e.g. "L3"
    machine_part = parts[1]  # e.g. "Perfecta1" or "EB_Conveyor1"

    # Map line prefix → demo line short name
    line_num_map = {
        "L1": "Alpha", "L3": "Bravo", "L4A": "Charlie", "L4B": "Delta",
        "L7": "Echo", "L9": "Foxtrot", "L10": "Golf", "L12": "Hotel",
        "L13": "India", "L14": "Juliet", "L15": "Kilo",
    }
    demo_line = line_num_map.get(line_prefix, line_prefix)

    # Find the machine type
    demo_type = None
    for real_root, dtype in MACHINE_TYPE_MAP.items():
        # Check for compound names first (EB_Conveyor, Mohrbach_MKV etc.)
        if machine_part.startswith(real_root):
            demo_type = dtype
            suffix = machine_part[len(real_root):]
            break
    if demo_type is None:
        # Fallback: keep original
        demo_type = machine_part.rstrip("0123456789")
        suffix = machine_part[len(demo_type):]

    # Normalise suffix to 2-digit number
    num = "".join(c for c in suffix if c.isdigit())
    if num:
        num = f"{int(num):02d}"
    else:
        num = "01"

    result = f"{demo_line}-{demo_type}-{num}"
    _machine_name_cache[orig] = result
    return result


# ── SKU mapping (real brand → Golden Leaf fictional) ──────────────────────────
SKU_MAP = {}

GOLDEN_LEAF_PRODUCTS = [
    "GL English Breakfast",
    "GL Earl Grey",
    "GL Green Tea Sencha",
    "GL Chamomile Blossom",
    "GL Darjeeling Premium",
    "GL Kenyan Bold",
    "GL Nilgiri Frost",
    "GL Peppermint Fresh",
    "GL Jasmine Dragon",
    "GL Ceylon Gold",
    "GL Rooibos Sunset",
    "GL Oolong Harmony",
]

def remap_sku_name(orig: str) -> str:
    if not orig or orig in ("SKU_Name", "NULL", " "):
        return orig
    if orig in SKU_MAP:
        return SKU_MAP[orig]
    # Deterministic mapping: hash-based index
    idx = hash(orig) % len(GOLDEN_LEAF_PRODUCTS)
    SKU_MAP[orig] = GOLDEN_LEAF_PRODUCTS[idx]
    return SKU_MAP[orig]


# ── SKU number mapping ────────────────────────────────────────────────────────
_sku_num_cache = {}
_sku_counter = [70000000]

def remap_sku_number(orig: str) -> str:
    if not orig or orig in ("SKU_Number", "NULL", " "):
        return orig
    if orig in _sku_num_cache:
        return _sku_num_cache[orig]
    _sku_counter[0] += 1
    _sku_num_cache[orig] = str(_sku_counter[0])
    return _sku_num_cache[orig]


# ── Machine state cleaning ────────────────────────────────────────────────────
STATE_CLEAN = {
    "Running": "Running",
    "Stopped": "Stopped",
    "Stopped ": "Stopped",
    "Stooped ": "Stopped",
    "Blocked": "Blocked",
    "Waiting": "Waiting",
    "NULL": "Idle",
    "": "Idle",
}


def remap_line(orig: str) -> str:
    return LINE_MAP.get(orig.strip(), orig.strip())


# ── Machine Location mapping ─────────────────────────────────────────────────
LOCATION_MAP = {
    "Production": "Production",
    "Supply": "Supply",
    "EOL": "EndOfLine",
    "EOL_Case_F": "EndOfLine-CaseForming",
    "EOL_Case_Packer": "EndOfLine-CasePacking",
    "NULL": "Unknown",
}


# ── Timestamp shifting ────────────────────────────────────────────────────────
def shift_timestamp(orig_str: str, tile_idx: int) -> str:
    """Shift an original timestamp into the demo window.
    
    Each tile covers the original span but offset by tile_idx * ORIG_SPAN_SEC
    into the demo window.  Timestamps that land past DEMO_END are discarded
    by the caller.
    """
    if not orig_str or orig_str.strip() in ("", "NULL"):
        return ""
    try:
        orig_dt = datetime.strptime(orig_str.strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            orig_dt = datetime.strptime(orig_str.strip(), "%d/%m/%Y")
            orig_dt = orig_dt.replace(hour=0, minute=0, second=0)
        except ValueError:
            return orig_str

    offset_from_orig_start = (orig_dt - ORIG_START).total_seconds()
    new_offset = tile_idx * ORIG_SPAN_SEC + offset_from_orig_start
    new_dt = DEMO_START + timedelta(seconds=new_offset)
    if new_dt >= DEMO_END:
        return None  # signal to drop this row
    return new_dt.strftime("%Y-%m-%dT%H:%M:%S")


def shift_date_only(orig_str: str, tile_idx: int) -> str:
    """Shift a date string (DD/MM/YYYY or YYYY-MM-DD)."""
    if not orig_str or orig_str.strip() in ("", "NULL"):
        return ""
    try:
        if "/" in orig_str:
            orig_dt = datetime.strptime(orig_str.strip(), "%d/%m/%Y")
        else:
            orig_dt = datetime.strptime(orig_str.strip(), "%Y-%m-%d")
    except ValueError:
        return orig_str
    offset_from_orig_start = (orig_dt - ORIG_START).total_seconds()
    new_offset = tile_idx * ORIG_SPAN_SEC + offset_from_orig_start
    new_dt = DEMO_START + timedelta(seconds=new_offset)
    if new_dt >= DEMO_END:
        return None
    return new_dt.strftime("%Y-%m-%d")


def shift_time_only(orig_str: str) -> str:
    """Keep the original time-of-day unchanged."""
    return orig_str.strip() if orig_str else ""


# ── Equipment ID assignment ───────────────────────────────────────────────────
# Line → WorkCenter EQP ID (from existing DimEquipment)
_line_to_wc = {}
# Machine name → WorkUnit EQP ID
_machine_to_eqp = {}
_next_eqp = [16]  # Continue from EQP-015

# Map existing lines to WorkCenters
# We'll expand: add more WorkCenters for lines beyond the original 2
LINE_TO_WORKCENTER = {}

def get_equipment_id(demo_machine_name: str) -> str:
    if demo_machine_name in _machine_to_eqp:
        return _machine_to_eqp[demo_machine_name]
    eqp_id = f"EQP-{_next_eqp[0]:03d}"
    _next_eqp[0] += 1
    _machine_to_eqp[demo_machine_name] = eqp_id
    return eqp_id


# ── Batch assignment (round-robin from existing batches) ──────────────────────
BATCH_IDS = [f"BTC-{i:03d}" for i in range(1, 21)]

def assign_batch(tile_idx: int, row_idx: int) -> str:
    return BATCH_IDS[(tile_idx * 1000 + row_idx) % len(BATCH_IDS)]


# ══════════════════════════════════════════════════════════════════════════════
# 1. MachineStateTelemetry  (from real Machine State CSV)
# ══════════════════════════════════════════════════════════════════════════════
def generate_machine_state_telemetry():
    print("Generating MachineStateTelemetry.csv ...")
    out_path = os.path.join(OUT_EH, "MachineStateTelemetry.csv")
    out_header = [
        "Timestamp", "EquipmentId", "LineName", "Shift",
        "MachineState", "ErrorCode", "DurationSec", "BatchId"
    ]

    total_written = 0
    with open(out_path, "w", newline="") as fout:
        writer = csv.writer(fout)
        writer.writerow(out_header)

        for tile in range(TILE_COUNT):
            with open(SRC_MS, "r", newline="") as fin:
                reader = csv.DictReader(fin)
                for row_idx, row in enumerate(reader):
                    ts = shift_timestamp(row["TIMESTAMP_String"], tile)
                    if ts is None:
                        continue  # past demo end

                    line = remap_line(row["Line"])
                    machine = remap_machine_name(row["MachineName"])
                    eqp_id = get_equipment_id(machine)
                    shift = row["Shift"].strip() if row["Shift"].strip() not in ("", "NULL") else "Day"
                    state = STATE_CLEAN.get(row["MachineState"].strip(), "Idle")
                    error = row["Error_Code"].strip() if row["Error_Code"].strip() not in ("", "NULL") else "0"
                    dur = row["TimeSpan_Sec"].strip() if row["TimeSpan_Sec"].strip() not in ("", "NULL") else "0"
                    batch = assign_batch(tile, row_idx)

                    writer.writerow([ts, eqp_id, line, shift, state, error, dur, batch])
                    total_written += 1

            print(f"  Tile {tile+1}/{TILE_COUNT} done — {total_written:,} rows so far")
            if total_written > 6_500_000:
                break  # safety cap

    print(f"  ✓ MachineStateTelemetry.csv → {total_written:,} rows")
    return total_written


# ══════════════════════════════════════════════════════════════════════════════
# 2. ProductionCounterTelemetry  (from real OEE CSV)
# ══════════════════════════════════════════════════════════════════════════════
def generate_production_counter_telemetry():
    print("Generating ProductionCounterTelemetry.csv ...")
    out_path = os.path.join(OUT_EH, "ProductionCounterTelemetry.csv")
    out_header = [
        "Timestamp", "EquipmentId", "LineName", "SKU", "Shift",
        "BagCount", "BagCountDelta", "TeaProducedGram",
        "BagsRejected", "TeaRejectedGram",
        "VOT", "LoadingTime", "OEE", "BatchId"
    ]

    total_written = 0
    with open(out_path, "w", newline="") as fout:
        writer = csv.writer(fout)
        writer.writerow(out_header)

        for tile in range(TILE_COUNT):
            with open(SRC_OEE, "r", newline="") as fin:
                reader = csv.DictReader(fin)
                for row_idx, row in enumerate(reader):
                    ts = shift_timestamp(row["TIMESTAMP"], tile)
                    if ts is None:
                        continue

                    line = remap_line(row["Line"])
                    machine = remap_machine_name(row["MachineName"])
                    eqp_id = get_equipment_id(machine)
                    sku = remap_sku_name(row["SKU_Name"])
                    shift = row["Shift"].strip() if row.get("Shift", "").strip() not in ("", "NULL") else "Day"

                    def safe_num(val, default="0"):
                        v = val.strip() if val else ""
                        return v if v and v != "NULL" else default

                    bag_count = safe_num(row.get("New_Count", ""))
                    bag_delta = safe_num(row.get("Count_Difference", ""))
                    tea_gram = safe_num(row.get("Diff_Tea_Produced_Gram", ""))
                    bags_rej = safe_num(row.get("Teabags_Rejected", ""))
                    tea_rej_gram = safe_num(row.get("Tea_Rejected_Gram", ""))
                    vot = safe_num(row.get("SUM_VOT", ""))
                    lt = safe_num(row.get("SUM_LT", ""))
                    oee = safe_num(row.get("SUM_OEE", ""))
                    batch = assign_batch(tile, row_idx)

                    writer.writerow([
                        ts, eqp_id, line, sku, shift,
                        bag_count, bag_delta, tea_gram,
                        bags_rej, tea_rej_gram,
                        vot, lt, oee, batch
                    ])
                    total_written += 1

            print(f"  Tile {tile+1}/{TILE_COUNT} done — {total_written:,} rows so far")
            if total_written > 13_500_000:
                break

    print(f"  ✓ ProductionCounterTelemetry.csv → {total_written:,} rows")
    return total_written


# ══════════════════════════════════════════════════════════════════════════════
# 3. ProcessSegmentTelemetry  (synthetic, ~300K+ rows)
# ══════════════════════════════════════════════════════════════════════════════
def generate_process_segment_telemetry():
    print("Generating ProcessSegmentTelemetry.csv (synthetic) ...")
    out_path = os.path.join(OUT_EH, "ProcessSegmentTelemetry.csv")

    # Segment types and typical sensor profiles
    PROFILES = {
        "Blending": {"temp": (80, 90), "moisture": (4.0, 6.0), "cycle": (100, 140)},
        "Filling":  {"temp": (22, 28), "moisture": (4.5, 5.5), "cycle": (2.5, 4.0)},
        "Sealing":  {"temp": (180, 220), "moisture": (1.5, 3.0), "cycle": (1.0, 2.5)},
        "Packaging":{"temp": (20, 25), "moisture": (3.0, 5.0), "cycle": (5.0, 8.0)},
    }

    # Segments from DimProcessSegment.csv
    segments = [
        # (id, type)
        ("SEG-001", "Blending"), ("SEG-002", "Filling"), ("SEG-003", "Sealing"), ("SEG-004", "Packaging"),
        ("SEG-005", "Blending"), ("SEG-006", "Filling"), ("SEG-007", "Sealing"), ("SEG-008", "Packaging"),
        ("SEG-009", "Blending"), ("SEG-010", "Filling"), ("SEG-011", "Sealing"), ("SEG-012", "Packaging"),
        ("SEG-013", "Blending"), ("SEG-014", "Filling"), ("SEG-015", "Sealing"), ("SEG-016", "Packaging"),
        ("SEG-017", "Blending"), ("SEG-018", "Filling"), ("SEG-019", "Sealing"), ("SEG-020", "Packaging"),
        ("SEG-021", "Blending"), ("SEG-022", "Filling"), ("SEG-023", "Sealing"), ("SEG-024", "Packaging"),
        ("SEG-025", "Blending"), ("SEG-026", "Filling"), ("SEG-027", "Sealing"), ("SEG-028", "Packaging"),
        ("SEG-029", "Blending"), ("SEG-030", "Blending"),
    ]

    # Generate one reading every 15 minutes for 365 days → ~35K readings per segment
    # With 30 segments that would be ~1M. Let's do every 30 min to get ~500K
    INTERVAL_MIN = 30
    total_minutes = int(DEMO_SPAN_SEC / 60)
    readings_per_seg = total_minutes // INTERVAL_MIN  # ~17,520

    total_written = 0
    with open(out_path, "w", newline="") as fout:
        writer = csv.writer(fout)
        writer.writerow(["Timestamp", "SegmentId", "Temperature", "MoistureContent", "CycleTime"])

        for seg_id, seg_type in segments:
            prof = PROFILES[seg_type]
            t_base = random.uniform(*prof["temp"])
            m_base = random.uniform(*prof["moisture"])
            c_base = random.uniform(*prof["cycle"])

            # Add slow drift + daily seasonality + noise
            for i in range(readings_per_seg):
                dt = DEMO_START + timedelta(minutes=i * INTERVAL_MIN)
                if dt >= DEMO_END:
                    break

                # Hour-of-day effect (warmer in day shifts)
                hour_factor = math.sin((dt.hour - 6) * math.pi / 12) * 0.03

                # Seasonal drift (slightly warmer in summer)
                month_offset = (dt - DEMO_START).days / 365
                season_factor = math.sin(month_offset * 2 * math.pi) * 0.02

                # Random walk component (persistent noise)
                drift = random.gauss(0, 0.005) 

                temp = t_base * (1 + hour_factor + season_factor + drift)
                moist = m_base * (1 - hour_factor * 0.5 + random.gauss(0, 0.02))
                cycle = c_base * (1 + random.gauss(0, 0.03))

                # Inject anomalies for SEG-013 and SEG-025 (correlated with quality failures)
                if seg_id == "SEG-013" and 100 < i < 200:
                    temp -= 5 + random.gauss(0, 1)
                    moist += 2 + random.gauss(0, 0.3)
                if seg_id == "SEG-025" and 300 < i < 400:
                    moist += 3 + random.gauss(0, 0.5)

                writer.writerow([
                    dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    seg_id,
                    f"{temp:.1f}",
                    f"{moist:.1f}",
                    f"{cycle:.1f}",
                ])
                total_written += 1

            print(f"  {seg_id} ({seg_type}) — {total_written:,} rows")

    print(f"  ✓ ProcessSegmentTelemetry.csv → {total_written:,} rows")
    return total_written


# ══════════════════════════════════════════════════════════════════════════════
# 4. EquipmentTelemetry  (synthetic, ~200K+ rows)
# ══════════════════════════════════════════════════════════════════════════════
def generate_equipment_telemetry():
    print("Generating EquipmentTelemetry.csv (synthetic) ...")
    out_path = os.path.join(OUT_EH, "EquipmentTelemetry.csv")

    # Equipment from DimEquipment (EQP-001 to EQP-015)
    equipment = [
        ("EQP-001", "Blending", 3500),     # Site: London Blendery
        ("EQP-002", "Packing", 5500),       # Site: Manchester Packing
        ("EQP-003", "Distribution", 2000),   # Site: Distribution Centre
        ("EQP-004", "Blending", 2500),       # Area: Blending Hall Alpha
        ("EQP-005", "Packing", 4000),        # WC: Packing Line 1
        ("EQP-006", "Packing", 4000),        # WC: Packing Line 2
        ("EQP-007", "QualityControl", 800),  # Area: Quality Lab
        ("EQP-008", "Warehouse", 1500),      # Area: Warehouse
        ("EQP-009", "Supplier", 500),        # Darjeeling
        ("EQP-010", "Supplier", 600),        # Assam
        ("EQP-011", "Supplier", 550),        # Ceylon
        ("EQP-012", "Supplier", 700),        # Hangzhou
        ("EQP-013", "Supplier", 300),        # PackRight 
        ("EQP-014", "Supplier", 250),        # FlexiPack
        ("EQP-015", "Supplier", 400),        # Nile Valley
    ]

    # Generate 1 reading per hour for 365 days → 8,760 per equipment × 15 = ~131K
    # Use 30 min for more data → 17,520 × 15 = ~263K
    INTERVAL_MIN = 30
    total_minutes = int(DEMO_SPAN_SEC / 60)
    readings_per_equip = total_minutes // INTERVAL_MIN

    total_written = 0
    with open(out_path, "w", newline="") as fout:
        writer = csv.writer(fout)
        writer.writerow(["Timestamp", "EquipmentId", "EnergyConsumption", "Humidity", "ProductionRate"])

        for eqp_id, eqp_type, base_energy in equipment:
            for i in range(readings_per_equip):
                dt = DEMO_START + timedelta(minutes=i * INTERVAL_MIN)
                if dt >= DEMO_END:
                    break

                # Production hours: 6am-10pm weekdays, reduced weekends
                is_weekend = dt.weekday() >= 5
                is_production = 6 <= dt.hour <= 22

                if is_weekend:
                    energy_factor = 0.3 if is_production else 0.1
                    prod_rate = random.gauss(30, 10) if is_production else 0
                elif is_production:
                    energy_factor = 0.7 + random.gauss(0.2, 0.05)
                    prod_rate = random.gauss(120, 20)
                else:
                    energy_factor = 0.15
                    prod_rate = 0

                # Seasonal energy (heating in winter, cooling in summer)
                month = dt.month
                if month in (11, 12, 1, 2):
                    energy_factor *= 1.15
                elif month in (6, 7, 8):
                    energy_factor *= 1.08

                energy = base_energy * energy_factor + random.gauss(0, base_energy * 0.02)
                energy = max(0, energy)
                humidity = 41.0 + math.sin((dt.hour - 8) * math.pi / 10) * 3 + random.gauss(0, 1.5)
                humidity = max(20, min(75, humidity))
                prod_rate = max(0, prod_rate)

                # Supplier sites have different patterns (just energy, no prod rate)
                if eqp_type == "Supplier":
                    prod_rate = 0
                    humidity = 35 + random.gauss(0, 5)

                writer.writerow([
                    dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    eqp_id,
                    f"{energy:.1f}",
                    f"{humidity:.1f}",
                    f"{prod_rate:.1f}",
                ])
                total_written += 1

        print(f"  ✓ EquipmentTelemetry.csv → {total_written:,} rows")
    return total_written


# ══════════════════════════════════════════════════════════════════════════════
# 5. Expanded DimEquipment  (add WorkUnit machines)
# ══════════════════════════════════════════════════════════════════════════════
def generate_expanded_equipment():
    print("Generating expanded DimEquipment.csv ...")

    # Start with existing equipment
    existing = [
        ["EQP-001", "Golden Leaf London Blendery", "Site", "Blending", "London UK", "50000"],
        ["EQP-002", "Golden Leaf Manchester Packing", "Site", "Packing", "Manchester UK", "80000000"],
        ["EQP-003", "Golden Leaf Distribution Centre", "Site", "Distribution", "Birmingham UK", "100000000"],
        ["EQP-004", "Blending Hall Alpha", "Area", "Blending", "London UK", "25000"],
        ["EQP-005", "Packing Line 1", "WorkCenter", "Packing", "Manchester UK", "40000000"],
        ["EQP-006", "Packing Line 2", "WorkCenter", "Packing", "Manchester UK", "40000000"],
        ["EQP-007", "Quality Laboratory", "Area", "QualityControl", "London UK", "0"],
        ["EQP-008", "Finished Goods Warehouse", "Area", "Warehouse", "Birmingham UK", "50000000"],
        ["EQP-009", "Darjeeling Estate Depot", "Site", "Supplier", "Darjeeling India", "10000"],
        ["EQP-010", "Assam Processing Mill", "Site", "Supplier", "Dibrugarh India", "15000"],
        ["EQP-011", "Ceylon Export Terminal", "Site", "Supplier", "Colombo Sri Lanka", "12000"],
        ["EQP-012", "Hangzhou Tea Factory", "Site", "Supplier", "Hangzhou China", "20000"],
        ["EQP-013", "PackRight Hamburg Hub", "Site", "Supplier", "Hamburg Germany", "0"],
        ["EQP-014", "FlexiPack Chicago Warehouse", "Site", "Supplier", "Chicago USA", "0"],
        ["EQP-015", "Nile Valley Collection Point", "Site", "Supplier", "Cairo Egypt", "8000"],
    ]

    # Add WorkCenter entries for each production line
    line_wcs = []
    for line_name_orig, line_name_demo in LINE_MAP.items():
        eqp_id = f"EQP-{_next_eqp[0]:03d}"
        _next_eqp[0] += 1
        line_wcs.append([
            eqp_id, line_name_demo, "WorkCenter", "Packing", "Manchester UK", "20000000"
        ])

    # Now add WorkUnit entries for each unique machine we encountered
    machine_units = []
    for demo_name, eqp_id in sorted(_machine_to_eqp.items(), key=lambda x: x[1]):
        # Determine type from name
        mtype = "Packing"
        for tname in ["TeaBagFormer", "SealingUnit", "EnvelopeMachine"]:
            if tname in demo_name:
                mtype = "Forming"
                break
        for tname in ["CasePacker", "BulkPacker", "CartoonPacker", "BoxFormer"]:
            if tname in demo_name:
                mtype = "Packing"
                break
        for tname in ["Cartoner", "Overwrapper", "FilmWrapper"]:
            if tname in demo_name:
                mtype = "Wrapping"
                break
        for tname in ["ConveyorBelt"]:
            if tname in demo_name:
                mtype = "Transport"
                break
        for tname in ["MetalDetector"]:
            if tname in demo_name:
                mtype = "QualityControl"
                break

        machine_units.append([
            eqp_id, demo_name, "WorkUnit", mtype, "Manchester UK", "0"
        ])

    all_rows = existing + line_wcs + machine_units
    out_path = os.path.join(OUT_LH, "DimEquipment.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["EquipmentId", "Equipment_Name", "Equipment_Level",
                         "Equipment_Type", "Equipment_Location", "Equipment_Capacity"])
        for row in all_rows:
            writer.writerow(row)

    print(f"  ✓ DimEquipment.csv → {len(all_rows)} equipment entries "
          f"({len(existing)} existing + {len(line_wcs)} WorkCenters + {len(machine_units)} WorkUnits)")
    return len(all_rows)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    os.makedirs(OUT_EH, exist_ok=True)
    os.makedirs(OUT_LH, exist_ok=True)

    print("=" * 70)
    print("Golden Leaf Tea Co. — Data Transformation")
    print(f"Demo window: {DEMO_START.date()} → {DEMO_END.date()}")
    print(f"Source span: {ORIG_START} → {ORIG_END}  ({ORIG_SPAN_SEC/86400:.1f} days)")
    print(f"Tile count:  {TILE_COUNT}")
    print("=" * 70)

    n1 = generate_machine_state_telemetry()
    n2 = generate_production_counter_telemetry()
    n3 = generate_process_segment_telemetry()
    n4 = generate_equipment_telemetry()
    n5 = generate_expanded_equipment()

    print()
    print("=" * 70)
    print("Summary:")
    print(f"  MachineStateTelemetry:       {n1:>12,} rows")
    print(f"  ProductionCounterTelemetry:  {n2:>12,} rows")
    print(f"  ProcessSegmentTelemetry:     {n3:>12,} rows")
    print(f"  EquipmentTelemetry:          {n4:>12,} rows")
    print(f"  DimEquipment:                {n5:>12} entries")
    print(f"  TOTAL time-series rows:      {n1+n2+n3+n4:>12,}")
    print("=" * 70)
