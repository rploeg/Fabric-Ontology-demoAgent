# Demo Questions (Water Treatment Plant)

Below are five questions with traversal guidance, GQL notes, and why ontology helps.

---

## 1) Identify units with turbidity excursions and low flow in the last 24 hours
- Natural language: Which units show TurbidityNTU > 5 and FlowRateLps < 20 in the last 24 hours?
- Expected insight: Units potentially causing water quality issues under low flow.
- Traversal:
  - Plant → operates → Unit
  - Unit → hasReading → SensorEvent (timeseries)
  - Plant → sampledAt → WaterQualitySample (static samples)
- GQL (conceptual sketch):
  ```gql
  MATCH (u:Unit)-[:hasReading]->(t:SensorEvent)
  WHERE t.Timestamp >= NOW() - INTERVAL 24 HOURS
    AND t.FlowRateLps < 20
  MATCH (p:Plant)-[:operates]->(u)
  MATCH (p)-[:sampledAt]->(s:WaterQualitySample)
  WHERE s.TurbidityNTU > 5
  RETURN u.UnitId, p.PlantId, s.TurbidityNTU, t.FlowRateLps
  ```
- Explanation:
  - Filter recent telemetry, join via ontology relationships to samples.
- Ontology value: Queries over concepts (Unit, Plant, Sample) unify semantics across heterogeneous tables.

---

## 2) Plants with pH outside 6.5–8.5 range in the past week
- Natural language: Which plants had samples with pH < 6.5 or > 8.5 in the past week?
- Expected insight: Plants needing chemical adjustment.
- Traversal:
  - Plant → sampledAt → WaterQualitySample
- GQL (conceptual sketch):
  ```gql
  MATCH (p:Plant)-[:sampledAt]->(s:WaterQualitySample)
  WHERE s.SampleTimestamp >= NOW() - INTERVAL 7 DAYS
    AND (s.pH < 6.5 OR s.pH > 8.5)
  RETURN p.PlantId, s.SampleId, s.pH
  ```
- Explanation: Filter samples by timestamp and pH range.
- Ontology value: Consistent thresholds and units tied to property definitions.

---

## 3) Detect units with pressure spikes preceding turbidity increases
- Natural language: Find units where PressureBar rose > 30% in 2 hours before turbidity rose above 5 NTU.
- Expected insight: Potential filter clogging or valve malfunction.
- Traversal:
  - Unit → hasReading → SensorEvent
  - Plant → sampledAt → WaterQualitySample
- GQL (conceptual sketch):
  ```gql
  MATCH (u:Unit)-[:hasReading]->(t:SensorEvent)
  MATCH (p:Plant)-[:operates]->(u)
  MATCH (p)-[:sampledAt]->(s:WaterQualitySample)
  WHERE s.TurbidityNTU > 5
    AND t.Timestamp BETWEEN s.SampleTimestamp - INTERVAL 2 HOURS AND s.SampleTimestamp
  // Apply windowed pressure change logic (engine-specific aggregation)
  RETURN u.UnitId, p.PlantId, s.SampleId
  ```
- Explanation: Time-window join between telemetry and samples.
- Ontology value: Encodes temporal context between telemetry and lab samples.

---

## 4) Regional overview of quality excursions grouped by plant
- Natural language: For each region, how many plants had any quality excursion last 30 days?
- Expected insight: Hotspots for operational review.
- Traversal:
  - Plant → sampledAt → WaterQualitySample
- GQL (conceptual sketch):
  ```gql
  MATCH (p:Plant)-[:sampledAt]->(s:WaterQualitySample)
  WHERE s.SampleTimestamp >= NOW() - INTERVAL 30 DAYS
    AND (s.pH < 6.5 OR s.pH > 8.5 OR s.TurbidityNTU > 5)
  RETURN p.Region, COUNT(DISTINCT p.PlantId) AS plantsWithExcursions
  ```
- Explanation: Group by region; distinct plants with excursions.
- Ontology value: Aggregation over business-level concepts; add agent instruction “Support group by in GQL”.

---

## 5) Units with sustained low flow despite normal pressure
- Natural language: Which units had FlowRateLps < 15 for >3 hours while PressureBar between 1–4 bar?
- Expected insight: Potential flow measurement or blockage issues.
- Traversal:
  - Unit → hasReading → SensorEvent
- GQL (conceptual sketch):
  ```gql
  MATCH (u:Unit)-[:hasReading]->(t:SensorEvent)
  WHERE t.FlowRateLps < 15 AND t.PressureBar >= 1 AND t.PressureBar <= 4
  // Apply duration window logic (engine-specific)
  RETURN u.UnitId
  ```
- Explanation: Cross-metric condition over telemetry.
- Ontology value: Domain semantics (Unit, flow, pressure) provide reusable, governed metrics across sources.
