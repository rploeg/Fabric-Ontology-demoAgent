# Credit Fraud Detection - Demo Questions

> **Version**: 1.0  
> **Last Updated**: January 2026  
> **Ontology**: CreditFraud  
> **Company**: FinanceGuard Bank

---

## Question 1: Fraud Ring Detection (Supply Chain Traceability)

### Business Question

> "Which other customers might be connected to a known fraudster through shared merchant activity?"

### Why It Matters

Fraud rings often operate across multiple accounts, targeting the same high-risk merchants. By identifying customers who transact at the same merchants as confirmed fraud victims, investigators can proactively flag at-risk accounts before fraud occurs.

### Graph Traversal

```
Customer (Fraud Victim)
    ↓ OWNS
CreditCard
    ↓ HAS_TRANSACTION
Transaction
    ↓ OCCURRED_AT
Merchant (High-Risk)
    ↑ OCCURRED_AT
Transaction
    ↑ HAS_TRANSACTION
CreditCard
    ↑ OWNS
Customer (Potentially At-Risk)
```

**Hops**: 5 (Customer → CreditCard → Transaction → Merchant → Transaction → CreditCard → Customer)

### GQL Query

```gql
MATCH (victim:Customer)-[:OWNS]->(vc:CreditCard)-[:HAS_TRANSACTION]->(vt:Transaction)-[:OCCURRED_AT]->(m:Merchant)<-[:OCCURRED_AT]-(ot:Transaction)<-[:HAS_TRANSACTION]-(oc:CreditCard)<-[:OWNS]-(other:Customer)
WHERE victim.CustomerId = 'CUST005' 
  AND m.RiskTier = 'High'
  AND other.CustomerId <> victim.CustomerId
RETURN DISTINCT 
    other.FullName AS AtRiskCustomer,
    other.RiskScore AS CurrentRiskScore,
    m.MerchantName AS SharedMerchant,
    m.MerchantCategory AS Category,
    COUNT(ot) AS TransactionCount
ORDER BY TransactionCount DESC
```

### Expected Results

| AtRiskCustomer | CurrentRiskScore | SharedMerchant | Category | TransactionCount |
|----------------|------------------|----------------|----------|------------------|
| Joshua Hall | 52.8 | WireMoney Transfer | Money Transfer | 2 |
| Amanda Foster | 22.4 | GamingWorld Online | Gaming | 1 |
| Emily Chen | 45.8 | Offshore Betting Ltd | Gambling | 1 |
| Rachel Taylor | 88.9 | CryptoExchange Pro | Cryptocurrency | 1 |

### Why Ontology is Better

| Traditional SQL Approach | Ontology Graph Approach |
|--------------------------|------------------------|
| 6+ table JOINs required | Single MATCH pattern |
| Complex subqueries for path finding | Intuitive traversal syntax |
| Performance degrades with data volume | Optimized for relationship queries |
| Difficult to modify for new patterns | Easy to extend traversal depth |
| Results require manual correlation | Automatic relationship inference |

---

## Question 2: Device Compromise Impact Assessment

### Business Question

> "If device DEV005 is confirmed compromised, which customers, cards, and transactions are potentially affected?"

### Why It Matters

When a device is compromised (malware, stolen credentials), banks must immediately identify all accounts that used that device. This enables rapid response: freezing cards, notifying customers, and reviewing transactions for unauthorized activity.

### Graph Traversal

```
Device (Compromised)
    ↑ USED_DEVICE
Transaction
    ↑ HAS_TRANSACTION
CreditCard
    ↑ OWNS
Customer
    ↓ HAS_ALERT
FraudAlert
```

**Hops**: 4 (Device → Transaction → CreditCard → Customer → FraudAlert)

### GQL Query

```gql
MATCH (d:Device)<-[:USED_DEVICE]-(t:Transaction)<-[:HAS_TRANSACTION]-(card:CreditCard)<-[:OWNS]-(c:Customer)
WHERE d.DeviceId = 'DEV005'
OPTIONAL MATCH (c)-[:HAS_ALERT]->(alert:FraudAlert)
RETURN DISTINCT
    c.FullName AS CustomerName,
    c.CustomerId AS CustomerId,
    card.CardId AS AffectedCard,
    card.CardType AS CardType,
    t.TransactionId AS TransactionId,
    t.Amount AS Amount,
    t.RiskFlag AS RiskFlag,
    alert.AlertId AS ExistingAlert,
    alert.Resolution AS AlertStatus
ORDER BY t.Amount DESC
```

### Expected Results

| CustomerName | CustomerId | AffectedCard | CardType | TransactionId | Amount | RiskFlag | ExistingAlert | AlertStatus |
|--------------|------------|--------------|----------|---------------|--------|----------|---------------|-------------|
| Jessica Williams | CUST005 | CARD008 | Visa Platinum | TXN012 | 15000.00 | Critical | ALERT005 | Confirmed Fraud |
| Jessica Williams | CUST005 | CARD007 | Mastercard Gold | TXN075 | 9500.00 | Critical | ALERT022 | Confirmed Fraud |
| Jessica Williams | CUST005 | CARD005 | Visa Standard | TXN008 | 45.00 | None | NULL | NULL |
| Robert Garcia | CUST008 | CARD008 | Visa Platinum | TXN076 | 2800.00 | Critical | ALERT023 | Confirmed Fraud |

### Why Ontology is Better

| Traditional SQL Approach | Ontology Graph Approach |
|--------------------------|------------------------|
| Multiple queries to trace impact | Single query captures full blast radius |
| Manual correlation of results | Automatic relationship traversal |
| Difficult to include optional data | OPTIONAL MATCH handles missing alerts |
| Schema changes break queries | Flexible pattern matching |
| No visual path understanding | Clear traversal path in query |

---

## Question 3: Operational Correlation (Timeseries + Graph)

### Business Question

> "Which credit cards showed anomalous transaction velocity on the same day they were used from untrusted devices?"

### Why It Matters

Combining real-time telemetry (transaction velocity, decline rates) with relationship data (device trust status) enables early fraud detection. Cards with sudden velocity spikes used from untrusted devices are high-probability fraud indicators.

### Graph Traversal

```
CreditCard (High Velocity - Timeseries)
    ↓ HAS_TRANSACTION
Transaction
    ↓ USED_DEVICE
Device (Untrusted)
    ↑ REGISTERED_DEVICE
Customer
```

**Hops**: 2 + Timeseries correlation

### GQL Query

```gql
MATCH (card:CreditCard)-[:HAS_TRANSACTION]->(t:Transaction)-[:USED_DEVICE]->(d:Device)
WHERE card.TxnVelocity > 10 
  AND card.DeclineRate > 20
  AND d.IsTrusted = false
MATCH (c:Customer)-[:OWNS]->(card)
RETURN 
    c.FullName AS CustomerName,
    card.CardId AS CardId,
    card.TxnVelocity AS Velocity,
    card.DeclineRate AS DeclineRate,
    d.DeviceId AS DeviceId,
    d.DeviceType AS DeviceType,
    d.FailedLogins AS FailedLogins,
    t.TransactionId AS FlaggedTransaction,
    t.Amount AS Amount
ORDER BY card.DeclineRate DESC
```

### Expected Results

| CustomerName | CardId | Velocity | DeclineRate | DeviceId | DeviceType | FailedLogins | FlaggedTransaction | Amount |
|--------------|--------|----------|-------------|----------|------------|--------------|-------------------|--------|
| Joshua Hall | CARD024 | 25.8 | 62.5 | DEV024 | Mobile | 18 | TXN059 | 11500.00 |
| Jessica Williams | CARD007 | 15.2 | 35.0 | DEV005 | Mobile | 28 | TXN075 | 9500.00 |
| Jessica Williams | CARD008 | 18.5 | 45.0 | DEV005 | Mobile | 22 | TXN012 | 15000.00 |
| Amanda Foster | CARD011 | 11.2 | 18.5 | DEV010 | Desktop | 12 | TXN050 | 6700.00 |

### Why Ontology is Better

| Traditional SQL Approach | Ontology Graph Approach |
|--------------------------|------------------------|
| Separate queries for telemetry and relationships | Unified query across both |
| Complex time-based JOINs | Timeseries properties on entities |
| Manual correlation of metrics | Automatic property aggregation |
| Two systems to query (SQL + KQL) | Single GQL interface |
| Difficult to explain to business | Intuitive pattern matching |

---

## Question 4: Regulatory Compliance - Geographic Risk Exposure

### Business Question

> "Which customers have made transactions in high-risk geographic zones, and what is their total exposure?"

### Why It Matters

Regulatory frameworks (AML, KYC, OFAC) require banks to monitor transactions in sanctioned or high-risk regions. Graph queries can instantly identify exposed customers and aggregate their risk metrics for compliance reporting.

### Graph Traversal

```
GeoLocation (High Risk Zone)
    ↑ LOCATED_IN_TXN
Transaction
    ↑ HAS_TRANSACTION
CreditCard
    ↑ OWNS
Customer
```

**Hops**: 3 (GeoLocation → Transaction → CreditCard → Customer)

### GQL Query

```gql
MATCH (geo:GeoLocation)<-[:LOCATED_IN_TXN]-(t:Transaction)<-[:HAS_TRANSACTION]-(card:CreditCard)<-[:OWNS]-(c:Customer)
WHERE geo.RiskZone = 'High'
RETURN 
    c.FullName AS CustomerName,
    c.CustomerId AS CustomerId,
    c.AccountStatus AS AccountStatus,
    geo.City AS HighRiskCity,
    geo.Country AS Country,
    COUNT(t) AS TransactionCount,
    SUM(t.Amount) AS TotalExposure
ORDER BY TotalExposure DESC
```

### Expected Results

| CustomerName | CustomerId | AccountStatus | HighRiskCity | Country | TransactionCount | TotalExposure |
|--------------|------------|---------------|--------------|---------|------------------|---------------|
| Jessica Williams | CUST005 | Suspended | Moscow | Russia | 3 | 27300.00 |
| Joshua Hall | CUST024 | Under Review | Kiev | Ukraine | 2 | 19500.00 |
| Sarah Mitchell | CUST001 | Active | Lagos | Nigeria | 2 | 10300.00 |
| Emily Chen | CUST003 | Under Review | Moscow | Russia | 1 | 12000.00 |
| Timothy Clark | CUST020 | Under Review | Moscow | Russia | 1 | 4500.00 |
| Rachel Taylor | CUST015 | Suspended | Cayman Islands | Cayman Islands | 1 | 8200.00 |

### Why Ontology is Better

| Traditional SQL Approach | Ontology Graph Approach |
|--------------------------|------------------------|
| JOIN Location → Transaction → Card → Customer | Single pattern match |
| Aggregation requires GROUP BY with complex keys | Built-in aggregation in RETURN |
| Hard to filter on intermediate nodes | WHERE clause on any node |
| Compliance reports need custom ETL | Direct query for reporting |
| Changes require DBA involvement | Business users can modify |

---

## Question 5: End-to-End Fraud Genealogy

### Business Question

> "Trace the complete fraud chain: From the compromised device, through all transactions, to the fraud alerts, and identify the merchants involved."

### Why It Matters

Post-incident forensics require tracing the complete attack path. Understanding how fraud propagated—from initial device compromise through transactions to triggered alerts—enables root cause analysis and prevention of future attacks.

### Graph Traversal

```
Device (Compromised, Untrusted)
    ↑ USED_DEVICE
Transaction
    ↓ TRIGGERED
FraudAlert
    ↓ FLAGGED_CARD
CreditCard
    ↑ OWNS
Customer
Transaction
    ↓ OCCURRED_AT
Merchant
```

**Hops**: 5+ (Multiple paths converging)

### GQL Query

```gql
MATCH path = (d:Device)<-[:USED_DEVICE]-(t:Transaction)-[:TRIGGERED]->(alert:FraudAlert)-[:FLAGGED_CARD]->(card:CreditCard)<-[:OWNS]-(c:Customer)
WHERE d.IsTrusted = false 
  AND alert.Resolution = 'Confirmed Fraud'
MATCH (t)-[:OCCURRED_AT]->(m:Merchant)
MATCH (t)-[:LOCATED_IN_TXN]->(geo:GeoLocation)
RETURN 
    d.DeviceId AS CompromisedDevice,
    d.DeviceType AS DeviceType,
    d.FailedLogins AS FailedLoginAttempts,
    t.TransactionId AS TransactionId,
    t.Amount AS FraudAmount,
    t.TransactionDate AS FraudDate,
    m.MerchantName AS Merchant,
    m.RiskTier AS MerchantRisk,
    geo.City AS Location,
    geo.RiskZone AS GeoRisk,
    alert.AlertId AS AlertId,
    alert.AlertType AS AlertType,
    card.CardId AS AffectedCard,
    c.FullName AS VictimName,
    c.CustomerId AS VictimId
ORDER BY t.Amount DESC
```

### Expected Results

| CompromisedDevice | DeviceType | FailedLoginAttempts | TransactionId | FraudAmount | Merchant | MerchantRisk | Location | GeoRisk | AlertType | AffectedCard | VictimName |
|-------------------|------------|---------------------|---------------|-------------|----------|--------------|----------|---------|-----------|--------------|------------|
| DEV005 | Mobile | 28 | TXN012 | 15000.00 | WireMoney Transfer | High | Kiev | High | Large Wire Transfer | CARD008 | Jessica Williams |
| DEV005 | Mobile | 28 | TXN075 | 9500.00 | WireMoney Transfer | High | Kiev | High | Wire High Risk | CARD007 | Jessica Williams |
| DEV005 | Mobile | 28 | TXN076 | 2800.00 | QuickCash ATM Network | High | Moscow | High | ATM Fraud Pattern | CARD008 | Jessica Williams |
| DEV024 | Mobile | 18 | TXN059 | 11500.00 | WireMoney Transfer | High | Kiev | High | High Risk Wire | CARD024 | Joshua Hall |
| DEV024 | Mobile | 18 | TXN060 | 3500.00 | QuickCash ATM Network | High | Moscow | High | Linked ATM Fraud | CARD024 | Joshua Hall |
| DEV026 | Mobile | 15 | TXN044 | 2500.00 | QuickCash ATM Network | High | Lagos | High | Geographic Anomaly | CARD001 | Sarah Mitchell |
| DEV026 | Mobile | 15 | TXN045 | 7800.00 | Offshore Betting Ltd | High | Cayman Islands | High | Gambling After ATM | CARD001 | Sarah Mitchell |

### Why Ontology is Better

| Traditional SQL Approach | Ontology Graph Approach |
|--------------------------|------------------------|
| 8+ table JOINs minimum | Single coherent pattern |
| Query planning nightmare | Optimized graph traversal |
| Results scattered across rows | Complete path in each row |
| No path visualization | Clear genealogy structure |
| Impossible to explain to executives | Visual, intuitive results |

---

## Data Agent Instructions

When using the Fabric Data Agent with this ontology, configure the following:

### System Prompt for Data Agent

```
You are a Fraud Investigation Assistant for FinanceGuard Bank. You have access to a knowledge graph ontology that models credit card fraud detection.

ENTITIES YOU CAN QUERY:
- Customer: Bank customers (key: CustomerId)
- CreditCard: Credit cards with velocity metrics (key: CardId)
- Transaction: Individual transactions (key: TransactionId)
- Merchant: Transaction merchants with risk tiers (key: MerchantId)
- FraudAlert: ML-generated fraud alerts (key: AlertId)
- Device: Devices with login metrics (key: DeviceId)
- GeoLocation: Geographic locations with risk zones (key: LocationId)

RELATIONSHIPS:
- Customer OWNS CreditCard
- CreditCard HAS_TRANSACTION Transaction
- Transaction OCCURRED_AT Merchant
- Transaction TRIGGERED FraudAlert
- Transaction USED_DEVICE Device
- Transaction LOCATED_IN_TXN GeoLocation
- Customer REGISTERED_DEVICE Device
- Merchant LOCATED_IN_MERCHANT GeoLocation
- FraudAlert FLAGGED_CARD CreditCard
- Customer HAS_ALERT FraudAlert

TIMESERIES PROPERTIES (real-time metrics):
- CreditCard: TxnVelocity, DailySpend, DeclineRate
- Device: LoginAttempts, FailedLogins, SessionDuration

RISK INDICATORS:
- Merchant.RiskTier: Low, Medium, High
- GeoLocation.RiskZone: Low, Medium, High
- Device.IsTrusted: true/false
- Transaction.RiskFlag: None, Low, Medium, High, Critical
- FraudAlert.Severity: High, Critical
- FraudAlert.Resolution: Confirmed Fraud, Under Investigation, False Positive

COMMON INVESTIGATION PATTERNS:
1. Fraud ring detection: Find customers connected through shared high-risk merchants
2. Device compromise: Trace all accounts affected by a compromised device
3. Geographic anomalies: Identify impossible travel patterns
4. Velocity spikes: Correlate transaction velocity with fraud alerts

When users ask questions:
1. Identify the entities and relationships needed
2. Consider both graph traversals and timeseries metrics
3. Filter by risk indicators when investigating fraud
4. Aggregate results for compliance reporting
5. Always explain the traversal path in your response
```

### Sample Agent Interactions

**User**: "Show me all fraud confirmed for customer Jessica Williams"

**Agent Response**: 
"I'll query the fraud alerts for Jessica Williams (CUST005). She has 5 confirmed fraud alerts totaling $49,600 in fraudulent transactions. The fraud originated from compromised device DEV005 and targeted wire transfers and ATM withdrawals in high-risk locations (Moscow, Kiev). Her cards CARD007 and CARD008 have been permanently blocked."

**User**: "Which devices should we blacklist based on fraud patterns?"

**Agent Response**:
"Based on fraud correlation analysis, I recommend blacklisting these devices:
1. DEV005 - 28 failed logins, linked to 4 confirmed fraud alerts ($27,300)
2. DEV024 - 18 failed logins, linked to 2 confirmed fraud alerts ($15,000)
3. DEV026 - 15 failed logins, linked to 2 confirmed fraud alerts ($10,300)

All three devices show the pattern: high failed logins → wire transfer to high-risk country → ATM withdrawal in different high-risk country within minutes."

---

## Summary

| # | Theme | Hops | Key Insight |
|---|-------|------|-------------|
| 1 | Fraud Ring Detection | 5 | Connect customers through shared merchants |
| 2 | Device Compromise Impact | 4 | Trace blast radius of compromised device |
| 3 | Operational Correlation | 2 + TS | Combine timeseries with graph traversal |
| 4 | Regulatory Compliance | 3 | Geographic risk exposure reporting |
| 5 | End-to-End Genealogy | 5+ | Complete fraud chain forensics |

---

## Next Steps

1. Run these queries in Graph Explorer after completing bindings
2. Configure Data Agent with the system prompt above
3. Create custom dashboards using query results
4. Set up alerts for high-risk patterns
