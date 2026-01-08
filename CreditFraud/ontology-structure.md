# Credit Fraud Detection - Ontology Structure

> **Company**: FinanceGuard Bank  
> **Domain**: Credit Card Fraud Detection  
> **Version**: 1.0  
> **Created**: January 2026

---

## Entity Definitions

| Entity | Key | Key Type | Properties | Binding Source |
|--------|-----|----------|------------|----------------|
| **Customer** | CustomerId | string | FullName, Email, PhoneNumber, RiskScore, AccountStatus, CreatedDate | Lakehouse: DimCustomer |
| **CreditCard** | CardId | string | CardNumber, CardType, CreditLimit, IssuedDate, ExpiryDate, IsActive | Lakehouse: DimCreditCard |
| **Transaction** | TransactionId | string | Amount, TransactionType, TransactionDate, IsOnline, RiskFlag | Lakehouse: FactTransaction |
| **Merchant** | MerchantId | string | MerchantName, MerchantCategory, RiskTier, RegistrationDate | Lakehouse: DimMerchant |
| **FraudAlert** | AlertId | string | AlertType, Severity, AlertDate, Resolution, InvestigatorNotes | Lakehouse: FactFraudAlert |
| **Device** | DeviceId | string | DeviceType, DeviceOS, FirstSeen, LastSeen, IsTrusted | Lakehouse: DimDevice |
| **GeoLocation** | LocationId | string | City, Country, Region, Latitude, Longitude, RiskZone | Lakehouse: DimGeoLocation |

---

## Timeseries Properties

| Entity | Timeseries Properties | Binding Source |
|--------|----------------------|----------------|
| **CreditCard** | TxnVelocity, DailySpend, DeclineRate | Eventhouse: CardTelemetry |
| **Device** | LoginAttempts, FailedLogins, SessionDuration | Eventhouse: DeviceTelemetry |

---

## Relationship Definitions

| Relationship | Source Entity | Target Entity | Source Table | Cardinality |
|--------------|---------------|---------------|--------------|-------------|
| OWNS | Customer | CreditCard | DimCreditCard | 1:N |
| HAS_TRANSACTION | CreditCard | Transaction | FactTransaction | 1:N |
| OCCURRED_AT | Transaction | Merchant | FactTransaction | N:1 |
| TRIGGERED | Transaction | FraudAlert | FactFraudAlert | 1:N |
| USED_DEVICE | Transaction | Device | FactTransaction | N:1 |
| LOCATED_IN_TXN | Transaction | GeoLocation | FactTransaction | N:1 |
| REGISTERED_DEVICE | Customer | Device | FactCustomerDevice | N:N |
| LOCATED_IN_MERCHANT | Merchant | GeoLocation | DimMerchant | N:1 |
| FLAGGED_CARD | FraudAlert | CreditCard | FactFraudAlert | N:1 |
| HAS_ALERT | Customer | FraudAlert | FactFraudAlert | 1:N |

---

## Entity-Relationship Diagram

```mermaid
erDiagram
    Customer ||--o{ CreditCard : OWNS
    Customer ||--o{ Device : REGISTERED_DEVICE
    Customer ||--o{ FraudAlert : HAS_ALERT
    CreditCard ||--o{ Transaction : HAS_TRANSACTION
    Transaction }o--|| Merchant : OCCURRED_AT
    Transaction }o--|| Device : USED_DEVICE
    Transaction }o--|| GeoLocation : LOCATED_IN_TXN
    Transaction ||--o{ FraudAlert : TRIGGERED
    Merchant }o--|| GeoLocation : LOCATED_IN_MERCHANT
    FraudAlert }o--|| CreditCard : FLAGGED_CARD

    Customer {
        string CustomerId PK
        string FullName
        string Email
        string PhoneNumber
        double RiskScore
        string AccountStatus
        datetime CreatedDate
    }

    CreditCard {
        string CardId PK
        string CardNumber
        string CardType
        double CreditLimit
        datetime IssuedDate
        datetime ExpiryDate
        boolean IsActive
        double TxnVelocity TS
        double DailySpend TS
        double DeclineRate TS
    }

    Transaction {
        string TransactionId PK
        double Amount
        string TransactionType
        datetime TransactionDate
        boolean IsOnline
        string RiskFlag
    }

    Merchant {
        string MerchantId PK
        string MerchantName
        string MerchantCategory
        string RiskTier
        datetime RegistrationDate
    }

    FraudAlert {
        string AlertId PK
        string AlertType
        string Severity
        datetime AlertDate
        string Resolution
        string InvestigatorNotes
    }

    Device {
        string DeviceId PK
        string DeviceType
        string DeviceOS
        datetime FirstSeen
        datetime LastSeen
        boolean IsTrusted
        int LoginAttempts TS
        int FailedLogins TS
        double SessionDuration TS
    }

    GeoLocation {
        string LocationId PK
        string City
        string Country
        string Region
        double Latitude
        double Longitude
        string RiskZone
    }
```

---

## Multi-Hop Traversal Examples

### 1. Fraud Ring Detection (5 hops)
**Question**: "Which other customers share transaction patterns with a known fraudster?"

```
Customer → OWNS → CreditCard → HAS_TRANSACTION → Transaction → OCCURRED_AT → Merchant → OCCURRED_AT ← Transaction → HAS_TRANSACTION ← CreditCard → OWNS ← Customer
```

### 2. Device Compromise Analysis (4 hops)
**Question**: "If a device is compromised, which customers and cards are affected?"

```
Device → USED_DEVICE ← Transaction → TRIGGERED → FraudAlert → FLAGGED_CARD → CreditCard → OWNS ← Customer
```

### 3. Impossible Travel Detection (3 hops)
**Question**: "Did this customer make transactions in distant locations within a short time?"

```
Customer → OWNS → CreditCard → HAS_TRANSACTION → Transaction → LOCATED_IN_TXN → GeoLocation
```

### 4. Merchant Risk Propagation (3 hops)
**Question**: "Which customers are exposed to high-risk merchants?"

```
Merchant → OCCURRED_AT ← Transaction → HAS_TRANSACTION ← CreditCard → OWNS ← Customer
```

---

## Data Volume Estimates

| Table | Expected Rows | Notes |
|-------|---------------|-------|
| DimCustomer | 25 | Core customer base |
| DimCreditCard | 35 | ~1.4 cards per customer |
| FactTransaction | 150 | ~4-5 transactions per card |
| DimMerchant | 20 | Various merchant categories |
| FactFraudAlert | 25 | ~15% fraud rate for demo |
| DimDevice | 30 | Multiple devices per customer |
| DimGeoLocation | 15 | Key geographic locations |
| FactCustomerDevice | 40 | Customer-device mappings |
| CardTelemetry | 50 | Timeseries for cards |
| DeviceTelemetry | 50 | Timeseries for devices |

---

## Validation Checklist

- [x] All entity keys are string type
- [x] Property names are unique across ALL entities
- [x] Property names ≤26 characters, alphanumeric with hyphens/underscores
- [x] No reserved GQL words in property names
- [x] Relationships have distinct source and target entities
- [x] No xsd:decimal types (using double instead)
