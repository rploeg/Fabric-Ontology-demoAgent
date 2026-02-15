"""Multi-site support — clone a SimulatorConfig for an additional site.

Given a ``SiteProfile``, this module creates a **modified copy** of the base
``SimulatorConfig`` so that the cloned streams publish under a different UNS
branch, use offset equipment IDs, and generate unique batch IDs.

The approach is entirely config-level: individual stream classes remain
unchanged — they just receive a different config object.
"""

from __future__ import annotations

import copy
import math
import logging
from typing import Any, Dict, List

from .config import (
    SimulatorConfig,
    SiteProfile,
    EquipmentDef,
    MachineLineConfig,
    SegmentDef,
    CameraDef,
    VisionStationDef,
    ActiveShipmentDef,
    ActiveBatch,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def clone_config_for_site(
    base: SimulatorConfig,
    site: SiteProfile,
) -> SimulatorConfig:
    """Return a deep-copied config modified for *site*.

    Modifications applied:
    - UNS hierarchy extended with the new site
    - Equipment IDs offset by ``site.equipment_id_offset``
    - Line names suffixed with ``site.line_suffix``
    - Batch IDs get ``site.batch_prefix``
    - Machine/segment counts scaled by ``site.scale``
    """
    cfg = base.model_copy(deep=True)

    offset = site.equipment_id_offset
    suffix = site.line_suffix

    # ── UNS hierarchy ─────────────────────────────────────────────
    _inject_site_hierarchy(cfg, site)

    # ── Equipment Telemetry ───────────────────────────────────────
    new_eq: List[EquipmentDef] = []
    for eq in cfg.equipment_telemetry.equipment:
        n = _offset_eqp_id(eq.id, offset)
        new_eq.append(eq.model_copy(update={"id": n, "name": f"{eq.name} ({site.site_id})"}))
    cfg.equipment_telemetry.equipment = new_eq

    # ── Machine State Telemetry ───────────────────────────────────
    new_lines: List[MachineLineConfig] = []
    for ln in cfg.machine_state_telemetry.lines:
        new_lines.append(ln.model_copy(update={
            "name": ln.name + suffix,
            "equipment_id_start": ln.equipment_id_start + offset,
            "machines_per_line": max(1, int(ln.machines_per_line * site.scale)),
        }))
    cfg.machine_state_telemetry.lines = new_lines
    cfg.machine_state_telemetry.total_machines = max(
        1, int(cfg.machine_state_telemetry.total_machines * site.scale)
    )

    # ── Process Segment Telemetry ─────────────────────────────────
    new_segs: List[SegmentDef] = []
    seg_count = max(1, int(len(cfg.process_segment_telemetry.segments) * site.scale))
    for seg in cfg.process_segment_telemetry.segments[:seg_count]:
        new_segs.append(seg.model_copy(update={
            "id": f"{seg.id}{suffix}",
        }))
    cfg.process_segment_telemetry.segments = new_segs

    # ── Safety Incident ───────────────────────────────────────────
    new_cams: List[CameraDef] = []
    for cam in cfg.safety_incident_events.cameras:
        new_cams.append(cam.model_copy(update={
            "id": f"{cam.id}{suffix}",
            "equipment_id": _offset_eqp_id(cam.equipment_id, offset),
        }))
    cfg.safety_incident_events.cameras = new_cams

    # ── Quality Vision ────────────────────────────────────────────
    new_stations: List[VisionStationDef] = []
    for st in cfg.quality_vision_events.stations:
        new_stations.append(st.model_copy(update={
            "id": f"{st.id}{suffix}",
            "line_name": st.line_name + suffix,
            "equipment_id": _offset_eqp_id(st.equipment_id, offset),
        }))
    cfg.quality_vision_events.stations = new_stations

    # ── Supply Chain ──────────────────────────────────────────────
    new_ships: List[ActiveShipmentDef] = []
    for i, sh in enumerate(cfg.supply_chain_alerts.active_shipments):
        new_ships.append(sh.model_copy(update={
            "shipment_id": f"SHP-{site.site_id[:3].upper()}-{i + 1:03d}",
            "tracking_num": f"TRK-{site.site_id[:3].upper()}-{i + 1:04d}",
            "dest_equipment_id": _offset_eqp_id(sh.dest_equipment_id, offset),
        }))
    cfg.supply_chain_alerts.active_shipments = new_ships

    # ── Active Batches ────────────────────────────────────────────
    new_batches: List[ActiveBatch] = []
    for i, b in enumerate(cfg.simulation.active_batches):
        new_batches.append(b.model_copy(update={
            "batch_id": f"{site.batch_prefix}{i + 1:03d}",
        }))
    cfg.simulation.active_batches = new_batches

    # ── MQTT client ID (append site slug to avoid conflicts) ──────
    cfg.mqtt.client_id = f"{cfg.mqtt.client_id}-{site.site_id}"

    logger.info(
        "Cloned config for site '%s': offset=%d, scale=%.1f, lines=%d",
        site.site_id, offset, site.scale, len(new_lines),
    )
    return cfg


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _offset_eqp_id(eqp_id: str, offset: int) -> str:
    """Shift the numeric part of an equipment ID.

    ``_offset_eqp_id("EQP-005", 200)`` → ``"EQP-205"``
    """
    parts = eqp_id.rsplit("-", 1)
    if len(parts) == 2:
        try:
            num = int(parts[1]) + offset
            return f"{parts[0]}-{num:03d}"
        except ValueError:
            pass
    return f"{eqp_id}-{offset}"


def _inject_site_hierarchy(cfg: SimulatorConfig, site: SiteProfile) -> None:
    """Add the new site to the UNS ``hierarchy.sites`` dict.

    If the site profile provides ``unsAreas``, those are used as the
    areas dict under the new site.  Otherwise a minimal entry is created.
    """
    sites: Dict[str, Any] = cfg.uns.hierarchy.setdefault("sites", {})

    # Use the first "site-level" equipment ID from the offset range
    site_eqp = _offset_eqp_id("EQP-001", site.equipment_id_offset)

    areas: Dict[str, Any] = {}
    if site.uns_areas:
        areas = copy.deepcopy(site.uns_areas)
    else:
        # Auto-generate areas from the cloned line config
        suffix = site.line_suffix
        offset = site.equipment_id_offset
        area_eqp = _offset_eqp_id("EQP-005", offset)
        line_slugs = {}
        for ln in cfg.machine_state_telemetry.lines:
            # Lines were already suffixed by the cloner
            line_key = ln.name
            line_slugs[line_key] = line_key.lower().replace(" ", "-")
        areas[area_eqp] = {
            "slug": f"{site.uns_slug}-production",
            "lines": line_slugs,
        }

    sites[site_eqp] = {
        "slug": site.uns_slug,
        "areas": areas,
    }
