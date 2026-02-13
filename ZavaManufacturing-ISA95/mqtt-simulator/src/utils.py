"""Shared utility helpers for the Zava MQTT simulator."""

from __future__ import annotations

import random
import string
import uuid
from datetime import datetime, timezone, time as dt_time
from typing import Any, Dict, List, Sequence

from .config import SimulatorConfig, UnsConfig


# ------------------------------------------------------------------
# Timestamp
# ------------------------------------------------------------------

def utcnow() -> str:
    """ISO-8601 UTC timestamp (no microseconds)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utcnow_dt() -> datetime:
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------
# Shift calculation
# ------------------------------------------------------------------

def current_shift(day_start: str = "06:00", night_start: str = "18:00") -> str:
    """Return ``'Day'`` or ``'Night'`` based on UTC hour boundaries."""
    now = datetime.now(timezone.utc).time()
    ds = dt_time.fromisoformat(day_start)
    ns = dt_time.fromisoformat(night_start)
    if ds <= now < ns:
        return "Day"
    return "Night"


# ------------------------------------------------------------------
# Random helpers
# ------------------------------------------------------------------

def rand_float(lo: float, hi: float, decimals: int = 1) -> float:
    return round(random.uniform(lo, hi), decimals)


def rand_int(lo: int, hi: int) -> int:
    return random.randint(lo, hi)


def weighted_choice(options: Sequence[str], weights: Sequence[float]) -> str:
    return random.choices(options, weights=weights, k=1)[0]


def random_id(prefix: str, ts: datetime | None = None) -> str:
    """Generate a unique event ID like ``INC-20260213-104217-001``."""
    ts = ts or datetime.now(timezone.utc)
    short = uuid.uuid4().hex[:4].upper()
    return f"{prefix}-{ts.strftime('%Y%m%d-%H%M%S')}-{short}"


def random_operator() -> str:
    shift = "A" if current_shift() == "Day" else "B"
    return f"Shift-{shift}-Op-{random.randint(1, 20):02d}"


def random_lot_number(material_id: str) -> str:
    """Generate a realistic lot number."""
    now = datetime.now(timezone.utc)
    seq = random.randint(1, 9999)
    return f"LOT-{material_id.split('-')[1] if '-' in material_id else material_id}-{now.year}-{seq:04d}"


def random_serial(sku: str, batch_id: str) -> str:
    """Generate a unit serial like ZF-STD-011-004821."""
    prefix = "".join(w[0] for w in sku.split()[:2]).upper()
    batch_num = batch_id.replace("BTC-", "")
    seq = random.randint(1, 999999)
    return f"Z{prefix}-{batch_num}-{seq:06d}"


# ------------------------------------------------------------------
# Equipment / line helpers
# ------------------------------------------------------------------

# Machine types assigned round-robin per line (matching Zava ontology)
MACHINE_TYPES: List[str] = [
    "FiberWeaver", "LabelApplicator", "CasePacker",
    "Laminator", "HeatSealer", "Cutter",
    "SensorEmbedder", "Coater", "SpoolWinder",
    "MeshStitcher", "InspectionCamera", "Palletizer",
    "NanowireDepositor", "UVCurer",
]

LINE_NAMES: List[str] = [
    "WeaveLine-Alpha", "WeaveLine-Bravo", "WeaveLine-Charlie",
    "WeaveLine-Delta", "WeaveLine-Echo", "WeaveLine-Foxtrot",
    "WeaveLine-Golf", "WeaveLine-Hotel", "WeaveLine-India",
    "WeaveLine-Juliet", "WeaveLine-Kilo",
]

# Default machines per line and starting EQP IDs
LINE_MACHINE_MAP: Dict[str, tuple[int, int]] = {
    "WeaveLine-Alpha":   (12, 16),
    "WeaveLine-Bravo":   (12, 28),
    "WeaveLine-Charlie": (14, 40),
    "WeaveLine-Delta":   (12, 54),
    "WeaveLine-Echo":    (12, 66),
    "WeaveLine-Foxtrot": (12, 78),
    "WeaveLine-Golf":    (12, 90),
    "WeaveLine-Hotel":   (12, 102),
    "WeaveLine-India":   (12, 114),
    "WeaveLine-Juliet":  (12, 126),
    "WeaveLine-Kilo":    (12, 138),
}


def equipment_id(n: int) -> str:
    return f"EQP-{n:03d}"


def machine_name(line_name: str, idx_in_line: int) -> str:
    """e.g. ``Alpha-FiberWeaver-02``."""
    short = line_name.replace("WeaveLine-", "")
    machine_type = MACHINE_TYPES[idx_in_line % len(MACHINE_TYPES)]
    return f"{short}-{machine_type}-{(idx_in_line + 1):02d}"


def iter_machines():
    """Yield ``(equipment_id, line_name, machine_name, idx_in_line)`` for all 134 machines."""
    for line, (count, start) in LINE_MACHINE_MAP.items():
        for i in range(count):
            eqp = equipment_id(start + i)
            name = machine_name(line, i)
            yield eqp, line, name, i


# ------------------------------------------------------------------
# Material name lookup
# ------------------------------------------------------------------

MATERIAL_NAMES: Dict[str, str] = {
    "MAT-002": "Silver Nanowire Solution",
    "MAT-003": "Conductive Polymer Ink",
    "MAT-005": "UV-Cured Encapsulant",
    "MAT-011": "Carbon Fiber Tow",
    "MAT-012": "Piezo-Sensor Wafer",
    "MAT-013": "Flex-PCB Strip",
    "MAT-014": "Solder Paste (Lead-Free)",
    "MAT-015": "Shrink-Wrap Film",
    "MAT-016": "Corrugated Carton",
    "MAT-022": "Aramid Thread",
}


def material_name(material_id: str) -> str:
    return MATERIAL_NAMES.get(material_id, material_id)


# ------------------------------------------------------------------
# UNS topic resolver
# ------------------------------------------------------------------

def resolve_uns_topic(
    uns: UnsConfig,
    *,
    stream_slug: str,
    category: str | None = None,
    equipment_id_val: str | None = None,
    line_name: str | None = None,
    machine_name_val: str | None = None,
    station_id: str | None = None,
    shipment_id: str | None = None,
) -> str:
    """
    Build a UNS topic like::

        zava/portland-production/weave-hall-a/weaveline-alpha/alpha-fiberweaver-02/telemetry/machine-state

    Falls back to a sensible short path when elements are unknown.
    """
    # Determine category (telemetry / events / state)
    if category is None:
        for cat, slugs in [
            ("telemetry", uns.categories.telemetry),
            ("events", uns.categories.events),
            ("state", uns.categories.state),
        ]:
            if stream_slug in slugs:
                category = cat
                break
        if category is None:
            category = "telemetry"

    enterprise = uns.enterprise

    # Special case: supply-chain has no physical location
    if stream_slug == "supply-chain" and shipment_id:
        return f"{enterprise}/supply-chain/inbound/{_slug(shipment_id)}/{category}/{stream_slug}"

    # Try to locate equipment in the hierarchy
    sites_map: Dict[str, Any] = uns.hierarchy.get("sites", {})

    # If we have a machine-level piece of context, walk the tree
    if equipment_id_val and sites_map:
        for site_eqp, site_data in sites_map.items():
            if isinstance(site_data, dict):
                site_slug = site_data.get("slug", _slug(site_eqp))
                areas = site_data.get("areas", {})
                for area_eqp, area_data in areas.items():
                    if isinstance(area_data, dict):
                        area_slug = area_data.get("slug", _slug(area_eqp))
                        lines = area_data.get("lines", {})
                        if line_name and line_name in lines:
                            line_slug = lines[line_name]
                            cell = _slug(machine_name_val or station_id or equipment_id_val)
                            return f"{enterprise}/{site_slug}/{area_slug}/{line_slug}/{cell}/{category}/{stream_slug}"
                    elif isinstance(area_data, str):
                        area_slug = area_data
                        # Area-level equipment (no lines)
                        if equipment_id_val == area_eqp or _eqp_in_area(equipment_id_val, area_eqp):
                            cell = _slug(station_id or equipment_id_val)
                            return f"{enterprise}/{site_slug}/{area_slug}/{cell}/{category}/{stream_slug}"

            # Site-level equipment match
            if equipment_id_val == site_eqp:
                site_slug = site_data.get("slug", _slug(site_eqp)) if isinstance(site_data, dict) else _slug(site_eqp)
                return f"{enterprise}/{site_slug}/{category}/{stream_slug}"

    # Fallback: enterprise / stream
    return f"{enterprise}/{category}/{stream_slug}"


def _slug(val: str) -> str:
    """Lowercase, replace spaces/underscores with hyphens."""
    return val.lower().replace(" ", "-").replace("_", "-")


def _eqp_in_area(equipment_id_val: str, area_eqp: str) -> bool:
    """Heuristic: check if equipment_id is 'near' the area equipment."""
    # In the Zava model, area equipment like EQP-004 hosts cameras like CAM-COAT-01
    # This is a rough association — in production this would be a proper lookup
    return False
