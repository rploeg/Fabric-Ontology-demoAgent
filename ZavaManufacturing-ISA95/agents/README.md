# Agent Definitions — Zava Smart Textile Manufacturing

This directory contains agent definition files for conversational AI agents
that leverage the Zava Manufacturing ontology graph, Lakehouse data, and
Eventhouse telemetry.

## Agents

| Agent | Focus Area | Primary Data Sources |
|-------|-----------|---------------------|
| **Factory Floor Operator Agent** | **General-purpose — all factory data** | **All graph, KQL, and SQL sources** |
| Quality Root-Cause Agent | Quality failures & traceability | QualityTest, ProcessSegment, Material |
| Maintenance & Downtime Agent | Machine health & OEE | MachineStateTelemetry, Equipment, ProductionCounterTelemetry |
| Supplier Risk Agent | Supply chain risk & delivery | Supplier, Shipment, Material |
| Production Planner Agent | Order fulfilment & scheduling | ProductionOrder, ProductBatch, ProcessSegment |
