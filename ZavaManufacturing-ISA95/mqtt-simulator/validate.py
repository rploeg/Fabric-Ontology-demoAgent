#!/usr/bin/env python3
"""Quick validation script — run from mqtt-simulator/ directory."""
import sys; sys.path.insert(0, ".")

from src.config import SimulatorConfig, load_config
from src.utils import utcnow, current_shift, iter_machines, resolve_uns_topic
from src.streams.base import BaseStream
from src.streams.equipment_telemetry import EquipmentTelemetryStream
from src.streams.machine_state import MachineStateTelemetryStream
from src.streams.process_segment import ProcessSegmentTelemetryStream
from src.streams.production_counter import ProductionCounterTelemetryStream
from src.streams.safety_incident import SafetyIncidentStream
from src.streams.predictive_maintenance import PredictiveMaintenanceStream
from src.streams.digital_twin import DigitalTwinStream
from src.streams.material_consumption import MaterialConsumptionStream
from src.streams.quality_vision import QualityVisionStream
from src.streams.supply_chain import SupplyChainStream
from src.anomaly_engine import AnomalyEngine

print("All imports successful!")
print(f"Shift: {current_shift()}  |  Time: {utcnow()}")

machines = list(iter_machines())
print(f"Machines: {len(machines)}  |  First: {machines[0][0]}  |  Last: {machines[-1][0]}")

cfg = load_config("simulator-config.yaml")
print(f"Broker: {cfg.mqtt.broker}:{cfg.mqtt.port}  |  Mode: {cfg.topic_mode}")

topic = resolve_uns_topic(
    cfg.uns,
    stream_slug="machine-state",
    equipment_id_val="EQP-034",
    line_name="WeaveLine-Bravo",
    machine_name_val="Bravo-FiberWeaver-02",
)
print(f"UNS example: {topic}")

topic2 = resolve_uns_topic(cfg.uns, stream_slug="supply-chain", shipment_id="SHP-012")
print(f"Supply chain: {topic2}")

print("\nVALIDATION PASSED")
