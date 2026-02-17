"""Pydantic configuration models for the Zava MQTT Simulator.

Every section of simulator-config.yaml maps to a typed model here.
The root model is ``SimulatorConfig`` which is loaded via ``load_config(path)``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

import yaml
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# MQTT
# ---------------------------------------------------------------------------

class MqttConfig(BaseModel):
    broker: str = "aio-broker.azure-iot-operations.svc.cluster.local"
    port: int = 1883
    use_tls: bool = Field(False, alias="useTls")
    auth_method: Literal["none", "serviceAccountToken", "usernamePassword"] = Field(
        "serviceAccountToken", alias="authMethod"
    )
    username: str = ""
    password: str = ""
    client_id: str = Field("zava-simulator", alias="clientId")
    keep_alive: int = Field(60, alias="keepAlive")
    reconnect_delay_sec: int = Field(5, alias="reconnectDelaySec")
    qos: int = 1

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# UNS (Unified Namespace)
# ---------------------------------------------------------------------------

class UnsAreaConfig(BaseModel):
    """An area can be a plain string slug or have nested lines."""
    slug: Optional[str] = None
    lines: Optional[Dict[str, str]] = None


class UnsSiteConfig(BaseModel):
    slug: str
    areas: Dict[str, Union[str, UnsAreaConfig]] = {}


class UnsCategoryConfig(BaseModel):
    telemetry: List[str] = [
        "equipment", "machine-state", "process-segment",
        "production-counter", "predictive-maintenance",
    ]
    events: List[str] = [
        "safety-incident", "quality-vision",
        "material-consumption", "supply-chain",
        "batch-lifecycle",
    ]
    state: List[str] = ["digital-twin"]


class UnsConfig(BaseModel):
    enterprise: str = "zava"
    hierarchy: Dict[str, Any] = {}
    categories: UnsCategoryConfig = UnsCategoryConfig()


# ---------------------------------------------------------------------------
# Simulation globals
# ---------------------------------------------------------------------------

class ShiftConfig(BaseModel):
    day_start: str = Field("06:00", alias="dayStart")
    night_start: str = Field("18:00", alias="nightStart")
    model_config = {"populate_by_name": True}


class ActiveBatch(BaseModel):
    batch_id: str = Field(..., alias="batchId")
    product: str
    sku: str
    model_config = {"populate_by_name": True}


class SimulationConfig(BaseModel):
    tick_interval_sec: int = Field(1, alias="tickIntervalSec")
    time_mode: Literal["realtime", "accelerated"] = Field("realtime", alias="timeMode")
    acceleration_factor: int = Field(10, alias="accelerationFactor")
    shifts: ShiftConfig = ShiftConfig()
    active_batches: List[ActiveBatch] = Field(default_factory=list, alias="activeBatches")
    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Stream: Equipment Telemetry
# ---------------------------------------------------------------------------

class EquipmentDef(BaseModel):
    id: str
    name: str
    energy_range: List[float] = Field([200, 500], alias="energyRange")
    humidity_range: List[float] = Field([35, 45], alias="humidityRange")
    production_rate: Union[int, List[int]] = Field(0, alias="productionRate")
    model_config = {"populate_by_name": True}


class EquipmentTelemetryConfig(BaseModel):
    enabled: bool = True
    topic: str = "zava/telemetry/equipment"
    interval_sec: int = Field(30, alias="intervalSec")
    equipment: List[EquipmentDef] = Field(default_factory=list)
    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Stream: Machine State Telemetry
# ---------------------------------------------------------------------------

class MachineLineConfig(BaseModel):
    name: str
    machines_per_line: int = Field(12, alias="machinesPerLine")
    equipment_id_start: int = Field(16, alias="equipmentIdStart")
    model_config = {"populate_by_name": True}


class StateTransitionConfig(BaseModel):
    min_dwell_sec: int = Field(5, alias="minDwellSec")
    max_dwell_sec: int = Field(300, alias="maxDwellSec")
    probabilities: Dict[str, float] = Field(default_factory=lambda: {
        "Running": 0.70, "Stopped": 0.10, "Blocked": 0.05,
        "Waiting": 0.10, "Idle": 0.05,
    })
    error_probability: float = Field(0.02, alias="errorProbability")
    error_codes: List[str] = Field(
        default_factory=lambda: ["E101", "E202", "E303", "E404"],
        alias="errorCodes",
    )
    model_config = {"populate_by_name": True}


class MachineStateTelemetryConfig(BaseModel):
    enabled: bool = True
    topic: str = "zava/telemetry/machine-state"
    lines: List[MachineLineConfig] = Field(default_factory=list)
    auto_discover: bool = Field(True, alias="autoDiscover")
    total_machines: int = Field(134, alias="totalMachines")
    state_transition: StateTransitionConfig = Field(
        default_factory=StateTransitionConfig, alias="stateTransition"
    )
    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Stream: Process Segment Telemetry
# ---------------------------------------------------------------------------

class SegmentDef(BaseModel):
    id: str
    type: str
    temperature_range: List[float] = Field([80, 95], alias="temperatureRange")
    moisture_range: List[float] = Field([3.0, 5.0], alias="moistureRange")
    cycle_time_range: List[float] = Field([100, 120], alias="cycleTimeRange")
    model_config = {"populate_by_name": True}


class AutoGenerateSegments(BaseModel):
    enabled: bool = False
    count: int = 5
    types: List[str] = Field(
        default_factory=lambda: ["Coating", "Weaving", "SensorEmbed", "Packaging"]
    )


class ProcessSegmentTelemetryConfig(BaseModel):
    enabled: bool = True
    topic: str = "zava/telemetry/process-segment"
    interval_sec: int = Field(30, alias="intervalSec")
    segments: List[SegmentDef] = Field(default_factory=list)
    auto_generate: AutoGenerateSegments = Field(
        default_factory=AutoGenerateSegments, alias="autoGenerate"
    )
    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Stream: Production Counter Telemetry
# ---------------------------------------------------------------------------

class ProductionCounterTelemetryConfig(BaseModel):
    enabled: bool = True
    topic: str = "zava/telemetry/production-counter"
    interval_sec: int = Field(30, alias="intervalSec")
    unit_count_increment_range: List[int] = Field([0, 25], alias="unitCountIncrementRange")
    fiber_produced_gram_range: List[float] = Field([0, 100], alias="fiberProducedGramRange")
    reject_rate: float = Field(0.02, alias="rejectRate")
    oee_range: List[float] = Field([0.75, 0.95], alias="oeeRange")
    vot_range: List[float] = Field([0, 1800], alias="votRange")
    loading_time_base: float = Field(20000, alias="loadingTimeBase")
    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Stream: Safety Incident Events
# ---------------------------------------------------------------------------

class CameraDef(BaseModel):
    id: str
    zone: str
    equipment_id: str = Field(..., alias="equipmentId")
    model_config = {"populate_by_name": True}


class IncidentTypeDef(BaseModel):
    type: str
    severity: str
    weight: float
    descriptions: List[str] = Field(default_factory=list)


class SafetyIncidentConfig(BaseModel):
    enabled: bool = True
    topic: str = "zava/telemetry/safety-incident"
    min_interval_sec: int = Field(60, alias="minIntervalSec")
    max_interval_sec: int = Field(1800, alias="maxIntervalSec")
    cameras: List[CameraDef] = Field(default_factory=list)
    incident_types: List[IncidentTypeDef] = Field(default_factory=list, alias="incidentTypes")
    confidence_range: List[float] = Field([0.75, 0.99], alias="confidenceRange")
    image_ref_template: str = Field(
        "blob://safety-captures/{year}/{month}/{day}/{cameraId}_{timestamp}.jpg",
        alias="imageRefTemplate",
    )
    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Stream: Predictive Maintenance
# ---------------------------------------------------------------------------

class DegradationConfig(BaseModel):
    enabled: bool = True
    degradation_rate_per_hour: float = Field(0.002, alias="degradationRatePerHour")
    critical_threshold: float = Field(0.40, alias="criticalThreshold")
    warning_threshold: float = Field(0.60, alias="warningThreshold")
    reset_on_maintenance: bool = Field(True, alias="resetOnMaintenance")
    machines_with_degradation: int = Field(5, alias="machinesWithDegradation")
    model_config = {"populate_by_name": True}


class PredictiveMaintenanceConfig(BaseModel):
    enabled: bool = True
    topic: str = "zava/telemetry/predictive-maintenance"
    interval_sec: int = Field(10, alias="intervalSec")
    machines: Union[str, List[str]] = "auto"
    vibration_range: List[float] = Field([0.5, 4.0], alias="vibrationRange")
    bearing_temp_range: List[float] = Field([40, 75], alias="bearingTempRange")
    acoustic_db_range: List[float] = Field([65, 90], alias="acousticDBRange")
    motor_current_range: List[float] = Field([10, 20], alias="motorCurrentRange")
    spindle_speed_range: List[float] = Field([2800, 3600], alias="spindleSpeedRange")
    degradation: DegradationConfig = Field(default_factory=DegradationConfig)
    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Stream: Digital Twin State Sync
# ---------------------------------------------------------------------------

class RecipeDef(BaseModel):
    sku: str
    recipe_id: str = Field(..., alias="recipeId")
    target_speed_pct: int = Field(85, alias="targetSpeedPct")
    model_config = {"populate_by_name": True}


class DigitalTwinConfig(BaseModel):
    enabled: bool = True
    topic: str = "zava/telemetry/digital-twin"
    heartbeat_interval_sec: int = Field(60, alias="heartbeatIntervalSec")
    retain_messages: bool = Field(True, alias="retainMessages")
    statuses: List[str] = Field(default_factory=lambda: [
        "Producing", "ProducingAtRate", "Idle", "Setup", "Maintenance",
        "Changeover", "Blocked", "ScheduledDowntime", "UnscheduledDowntime",
    ])
    transition_probabilities: Dict[str, float] = Field(
        default_factory=lambda: {
            "Producing": 0.60, "Idle": 0.10, "Setup": 0.08,
            "Maintenance": 0.05, "Changeover": 0.07, "Blocked": 0.04,
            "ScheduledDowntime": 0.03, "UnscheduledDowntime": 0.02,
            "ProducingAtRate": 0.01,
        },
        alias="transitionProbabilities",
    )
    recipes: List[RecipeDef] = Field(default_factory=list)
    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Stream: Material Consumption Events
# ---------------------------------------------------------------------------

class MaterialBomEntry(BaseModel):
    material_id: str = Field(..., alias="materialId")
    expected_per_batch: float = Field(..., alias="expectedPerBatch")
    model_config = {"populate_by_name": True}


class MaterialConsumptionConfig(BaseModel):
    enabled: bool = True
    topic: str = "zava/telemetry/material-consumption"
    min_interval_sec: int = Field(30, alias="minIntervalSec")
    max_interval_sec: int = Field(120, alias="maxIntervalSec")
    materials: Dict[str, List[MaterialBomEntry]] = Field(default_factory=dict)
    variance_pct_range: List[float] = Field([-20, 10], alias="variancePctRange")
    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Stream: Quality Vision Events
# ---------------------------------------------------------------------------

class VisionStationDef(BaseModel):
    id: str
    line_name: str = Field(..., alias="lineName")
    equipment_id: str = Field(..., alias="equipmentId")
    model_config = {"populate_by_name": True}


class DefectTypeDef(BaseModel):
    type: str
    weight: float


class QualityVisionConfig(BaseModel):
    enabled: bool = True
    topic: str = "zava/telemetry/quality-vision"
    interval_sec: int = Field(10, alias="intervalSec")
    pass_rate: float = Field(0.92, alias="passRate")
    marginal_rate: float = Field(0.03, alias="marginalRate")
    stations: List[VisionStationDef] = Field(default_factory=list)
    defect_types: List[DefectTypeDef] = Field(default_factory=list, alias="defectTypes")
    confidence_range: List[float] = Field([0.70, 0.99], alias="confidenceRange")
    model_version: str = Field("yolov8-zava-defect-v3.2", alias="modelVersion")
    image_ref_template: str = Field(
        "blob://quality-vision/{year}/{month}/{day}/{stationId}_{timestamp}.jpg",
        alias="imageRefTemplate",
    )
    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Stream: Supply Chain Alerts
# ---------------------------------------------------------------------------

class ActiveShipmentDef(BaseModel):
    shipment_id: str = Field(..., alias="shipmentId")
    tracking_num: str = Field(..., alias="trackingNum")
    carrier: str
    origin_equipment_id: str = Field(..., alias="originEquipmentId")
    dest_equipment_id: str = Field(..., alias="destEquipmentId")
    material_ids: List[str] = Field(default_factory=list, alias="materialIds")
    initial_status: str = Field("InTransit", alias="initialStatus")
    model_config = {"populate_by_name": True}


class SupplyChainConfig(BaseModel):
    enabled: bool = True
    topic: str = "zava/telemetry/supply-chain"
    min_interval_sec: int = Field(300, alias="minIntervalSec")
    max_interval_sec: int = Field(3600, alias="maxIntervalSec")
    active_shipments: List[ActiveShipmentDef] = Field(
        default_factory=list, alias="activeShipments"
    )
    status_flow: List[str] = Field(
        default_factory=lambda: [
            "Booked", "PickedUp", "InTransit", "CustomsHold",
            "OutForDelivery", "Delivered",
        ],
        alias="statusFlow",
    )
    delay_probability: float = Field(0.15, alias="delayProbability")
    exception_probability: float = Field(0.03, alias="exceptionProbability")
    delay_reasons: List[str] = Field(
        default_factory=lambda: [
            "Port congestion", "Customs inspection", "Weather delay",
            "Carrier equipment failure", "Documentation missing",
            "Capacity shortage",
        ],
        alias="delayReasons",
    )
    impacted_batch_lookup: bool = Field(True, alias="impactedBatchLookup")
    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Stream: Batch Lifecycle
# ---------------------------------------------------------------------------

class BatchLifecycleConfig(BaseModel):
    enabled: bool = False
    topic: str = "zava/events/batch-lifecycle"
    interval_sec: int = Field(30, alias="intervalSec")
    max_concurrent_batches: int = Field(3, alias="maxConcurrentBatches")
    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Multi-Site Support
# ---------------------------------------------------------------------------

class SiteProfile(BaseModel):
    """Describes an additional site to simulate alongside the default one.

    The simulator clones its streams for each extra site, applying the
    offsets/overrides so that equipment IDs, line names, batch IDs, and
    UNS topics are unique per site.
    """
    site_id: str = Field(..., alias="siteId")
    uns_slug: str = Field(..., alias="unsSlug")
    equipment_id_offset: int = Field(200, alias="equipmentIdOffset")
    batch_prefix: str = Field("BTC-S", alias="batchPrefix")
    line_suffix: str = Field("-S", alias="lineSuffix")
    scale: float = 1.0
    enabled_streams: List[str] = Field(
        default_factory=list, alias="enabledStreams",
    )
    uns_areas: Dict[str, Any] = Field(
        default_factory=dict, alias="unsAreas",
    )
    model_config = {"populate_by_name": True}


class MultiSiteConfig(BaseModel):
    enabled: bool = False
    sites: List[SiteProfile] = Field(default_factory=list)
    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Anomaly Engine
# ---------------------------------------------------------------------------

class AnomalyScenario(BaseModel):
    name: str
    enabled: bool = True
    description: str = ""
    topic: str = ""
    stream: str = ""
    duration_sec: int = Field(0, alias="durationSec")
    overrides: Dict[str, Any] = Field(default_factory=dict)
    model_config = {"populate_by_name": True}


class AnomalyConfig(BaseModel):
    enabled: bool = True
    default_topic: str = Field("zava/anomalies", alias="defaultTopic")
    scenario_interval_min: int = Field(15, alias="scenarioIntervalMin")
    scenarios: List[AnomalyScenario] = Field(default_factory=list)
    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Event Hub output
# ---------------------------------------------------------------------------

class EventHubConfig(BaseModel):
    """Configuration for Azure Event Hub output.

    Used when ``outputMode`` is ``"eventHub"``.

    Authentication options:
      1. ``connectionString`` — easiest for dev/testing (requires local auth enabled).
      2. ``credential: "defaultCredential"`` + ``fullyQualifiedNamespace``
         — uses Azure CLI / environment creds (great for local testing).
      3. ``credential: "managedIdentity"`` + ``fullyQualifiedNamespace``
         — recommended for AKS with workload identity (no secrets).
    """
    connection_string: str = Field("", alias="connectionString")
    eventhub_name: str = Field("", alias="eventhubName")
    fully_qualified_namespace: str = Field("", alias="fullyQualifiedNamespace")
    credential: Literal["connectionString", "defaultCredential", "managedIdentity"] = "connectionString"
    # Batching settings
    max_batch_size: int = Field(100, alias="maxBatchSize")
    max_wait_time_sec: float = Field(1.0, alias="maxWaitTimeSec")
    # Partition key strategy: "topic" = use topic name, "stream" = use stream slug, "none" = round-robin
    partition_key_mode: Literal["topic", "stream", "none"] = Field(
        "topic", alias="partitionKeyMode"
    )
    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

class LoggingConfig(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    format: Literal["json", "text"] = "json"
    publish_metrics: bool = Field(True, alias="publishMetrics")
    metrics_interval_sec: int = Field(60, alias="metricsIntervalSec")
    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Root configuration
# ---------------------------------------------------------------------------

class SimulatorConfig(BaseModel):
    # --- Output mode: choose where messages are sent ---
    output_mode: Literal["mqtt", "eventHub"] = Field(
        "mqtt", alias="outputMode",
        description="Where to send simulated data: 'mqtt' for an MQTT broker, "
                    "'eventHub' for Azure Event Hub.",
    )

    mqtt: MqttConfig = Field(default_factory=MqttConfig)
    eventhub: EventHubConfig = Field(default_factory=EventHubConfig, alias="eventHub")

    topic_prefix: str = Field("zava/telemetry", alias="topicPrefix")
    topic_mode: Literal["flat", "uns"] = Field("uns", alias="topicMode")
    uns: UnsConfig = Field(default_factory=UnsConfig)
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)

    equipment_telemetry: EquipmentTelemetryConfig = Field(
        default_factory=EquipmentTelemetryConfig, alias="equipmentTelemetry"
    )
    machine_state_telemetry: MachineStateTelemetryConfig = Field(
        default_factory=MachineStateTelemetryConfig, alias="machineStateTelemetry"
    )
    process_segment_telemetry: ProcessSegmentTelemetryConfig = Field(
        default_factory=ProcessSegmentTelemetryConfig, alias="processSegmentTelemetry"
    )
    production_counter_telemetry: ProductionCounterTelemetryConfig = Field(
        default_factory=ProductionCounterTelemetryConfig, alias="productionCounterTelemetry"
    )
    safety_incident_events: SafetyIncidentConfig = Field(
        default_factory=SafetyIncidentConfig, alias="safetyIncidentEvents"
    )
    predictive_maintenance_signals: PredictiveMaintenanceConfig = Field(
        default_factory=PredictiveMaintenanceConfig, alias="predictiveMaintenanceSignals"
    )
    digital_twin_state_sync: DigitalTwinConfig = Field(
        default_factory=DigitalTwinConfig, alias="digitalTwinStateSync"
    )
    material_consumption_events: MaterialConsumptionConfig = Field(
        default_factory=MaterialConsumptionConfig, alias="materialConsumptionEvents"
    )
    quality_vision_events: QualityVisionConfig = Field(
        default_factory=QualityVisionConfig, alias="qualityVisionEvents"
    )
    supply_chain_alerts: SupplyChainConfig = Field(
        default_factory=SupplyChainConfig, alias="supplyChainAlerts"
    )
    batch_lifecycle: BatchLifecycleConfig = Field(
        default_factory=BatchLifecycleConfig, alias="batchLifecycle"
    )

    multi_site: MultiSiteConfig = Field(
        default_factory=MultiSiteConfig, alias="multiSite"
    )

    anomalies: AnomalyConfig = Field(default_factory=AnomalyConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    model_config = {"populate_by_name": True}


def load_config(path: str | Path) -> SimulatorConfig:
    """Load and validate a simulator-config.yaml file."""
    with open(path) as f:
        raw = yaml.safe_load(f)
    return SimulatorConfig.model_validate(raw or {})
