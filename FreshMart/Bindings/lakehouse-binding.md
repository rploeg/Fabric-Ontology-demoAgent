# FreshMart Supermarket - Lakehouse Binding Instructions

> **Version**: 1.0  
> **Last Updated**: January 2026  
> **Purpose**: Step-by-step instructions for binding Lakehouse data to the FreshMart ontology

---

## Prerequisites

Before starting the binding process:

1. ✅ **Create a Fabric Workspace** with Fabric capacity enabled
2. ✅ **Create a Lakehouse** named `FreshMartLakehouse`
3. ✅ **Upload all CSV files** from `Data\Lakehouse\` folder to the Lakehouse Files section
4. ✅ **Create tables from CSV files** (right-click each CSV → Load to Tables)
5. ✅ **Create an Ontology** and upload `Ontology\freshmart.ttl`

> ⚠️ **CRITICAL**: Disable OneLake security before binding!
> Go to Lakehouse Settings → OneLake → Disable "OneLake security"

---

## Entity Binding Summary

| Entity | Source Table | Key Column | Properties |
|--------|--------------|------------|------------|
| Store | DimStore | StoreId | StoreName, Address, City, State, ZipCode, OpenDate, SquareFootage |
| Product | DimProduct | ProductId | ProductName, UPC, UnitPrice, UnitCost, ShelfLife |
| Supplier | DimSupplier | SupplierId | SupplierName, ContactEmail, Phone, Country, Rating |
| ProductBatch | DimProductBatch | BatchId | LotNumber, ManufactureDate, ExpiryDate, Quantity, BatchStatus |
| Category | DimCategory | CategoryId | CategoryName, Department, IsPerishable |
| Employee | DimEmployee | EmployeeId | FirstName, LastName, Role, HireDate, IsActive |
| PurchaseOrder | FactPurchaseOrder | OrderId | OrderDate, ExpectedDelivery, TotalAmount, OrderStatus |
| QualityInspection | FactQualityInspection | InspectionId | InspectionDate, Result, Notes, Score |

---

## Step-by-Step Entity Binding

### 1. Bind Store Entity

1. Open your Ontology in Fabric
2. Select the **Store** entity
3. Click **Bind Data**
4. Select source: **Lakehouse** → `FreshMartLakehouse`
5. Select table: **DimStore**
6. Map the key:
   - Key Property: `StoreId`
   - Source Column: `StoreId`
7. Map properties:
   | Property | Column |
   |----------|--------|
   | StoreName | StoreName |
   | Address | Address |
   | City | City |
   | State | State |
   | ZipCode | ZipCode |
   | OpenDate | OpenDate |
   | SquareFootage | SquareFootage |
8. Click **Save**

> ⚠️ **Note**: Timeseries properties (FootTraffic, SalesVelocity, AvgTransactionValue) are bound separately via Eventhouse. See `eventhouse-binding.md`.

---

### 2. Bind Product Entity

1. Select the **Product** entity
2. Click **Bind Data**
3. Select source: **Lakehouse** → `FreshMartLakehouse`
4. Select table: **DimProduct**
5. Map the key:
   - Key Property: `ProductId`
   - Source Column: `ProductId`
6. Map properties:
   | Property | Column |
   |----------|--------|
   | ProductName | ProductName |
   | UPC | UPC |
   | UnitPrice | UnitPrice |
   | UnitCost | UnitCost |
   | ShelfLife | ShelfLife |
7. Click **Save**

---

### 3. Bind Supplier Entity

1. Select the **Supplier** entity
2. Click **Bind Data**
3. Select source: **Lakehouse** → `FreshMartLakehouse`
4. Select table: **DimSupplier**
5. Map the key:
   - Key Property: `SupplierId`
   - Source Column: `SupplierId`
6. Map properties:
   | Property | Column |
   |----------|--------|
   | SupplierName | SupplierName |
   | ContactEmail | ContactEmail |
   | Phone | Phone |
   | Country | Country |
   | Rating | Rating |
7. Click **Save**

---

### 4. Bind ProductBatch Entity

1. Select the **ProductBatch** entity
2. Click **Bind Data**
3. Select source: **Lakehouse** → `FreshMartLakehouse`
4. Select table: **DimProductBatch**
5. Map the key:
   - Key Property: `BatchId`
   - Source Column: `BatchId`
6. Map properties:
   | Property | Column |
   |----------|--------|
   | LotNumber | LotNumber |
   | ManufactureDate | ManufactureDate |
   | ExpiryDate | ExpiryDate |
   | Quantity | Quantity |
   | BatchStatus | BatchStatus |
7. Click **Save**

> ⚠️ **Note**: Timeseries properties (StorageTemperature, Humidity, DaysToExpiry) are bound separately via Eventhouse. See `eventhouse-binding.md`.

---

### 5. Bind Category Entity

1. Select the **Category** entity
2. Click **Bind Data**
3. Select source: **Lakehouse** → `FreshMartLakehouse`
4. Select table: **DimCategory**
5. Map the key:
   - Key Property: `CategoryId`
   - Source Column: `CategoryId`
6. Map properties:
   | Property | Column |
   |----------|--------|
   | CategoryName | CategoryName |
   | Department | Department |
   | IsPerishable | IsPerishable |
7. Click **Save**

---

### 6. Bind Employee Entity

1. Select the **Employee** entity
2. Click **Bind Data**
3. Select source: **Lakehouse** → `FreshMartLakehouse`
4. Select table: **DimEmployee**
5. Map the key:
   - Key Property: `EmployeeId`
   - Source Column: `EmployeeId`
6. Map properties:
   | Property | Column |
   |----------|--------|
   | FirstName | FirstName |
   | LastName | LastName |
   | Role | Role |
   | HireDate | HireDate |
   | IsActive | IsActive |
7. Click **Save**

---

### 7. Bind PurchaseOrder Entity

1. Select the **PurchaseOrder** entity
2. Click **Bind Data**
3. Select source: **Lakehouse** → `FreshMartLakehouse`
4. Select table: **FactPurchaseOrder**
5. Map the key:
   - Key Property: `OrderId`
   - Source Column: `OrderId`
6. Map properties:
   | Property | Column |
   |----------|--------|
   | OrderDate | OrderDate |
   | ExpectedDelivery | ExpectedDelivery |
   | TotalAmount | TotalAmount |
   | OrderStatus | OrderStatus |
7. Click **Save**

---

### 8. Bind QualityInspection Entity

1. Select the **QualityInspection** entity
2. Click **Bind Data**
3. Select source: **Lakehouse** → `FreshMartLakehouse`
4. Select table: **FactQualityInspection**
5. Map the key:
   - Key Property: `InspectionId`
   - Source Column: `InspectionId`
6. Map properties:
   | Property | Column |
   |----------|--------|
   | InspectionDate | InspectionDate |
   | Result | Result |
   | Notes | Notes |
   | Score | Score |
7. Click **Save**

---

## Relationship Binding Instructions

### Relationship Summary

| Relationship | Source → Target | Source Table | Source Key Column | Target Key Column |
|--------------|-----------------|--------------|-------------------|-------------------|
| BELONGS_TO | Product → Category | DimProduct | ProductId | CategoryId |
| SUPPLIED_BY | Product → Supplier | DimProduct | ProductId | SupplierId |
| STOCKS | Store → Product | FactStoreInventory | StoreId | ProductId |
| EMPLOYS | Store → Employee | DimEmployee | StoreId | EmployeeId |
| CONTAINS | ProductBatch → Product | DimProductBatch | BatchId | ProductId |
| RECEIVED_AT | ProductBatch → Store | DimProductBatch | BatchId | StoreId |
| ORDERED_BY | PurchaseOrder → Store | FactPurchaseOrder | OrderId | StoreId |
| FULFILLED_BY | PurchaseOrder → Supplier | FactPurchaseOrder | OrderId | SupplierId |
| INSPECTED | QualityInspection → ProductBatch | FactQualityInspection | InspectionId | BatchId |
| PERFORMED_BY | QualityInspection → Employee | FactQualityInspection | InspectionId | EmployeeId |

---

### 1. Bind BELONGS_TO Relationship (Product → Category)

1. Select the **BELONGS_TO** relationship
2. Click **Bind Data**
3. Select source: **Lakehouse** → `FreshMartLakehouse`
4. Select table: **DimProduct**
5. Configure mapping:
   - Source Key Column: `ProductId` (links to Product entity)
   - Target Key Column: `CategoryId` (links to Category entity)
6. Click **Save**

---

### 2. Bind SUPPLIED_BY Relationship (Product → Supplier)

1. Select the **SUPPLIED_BY** relationship
2. Click **Bind Data**
3. Select source: **Lakehouse** → `FreshMartLakehouse`
4. Select table: **DimProduct**
5. Configure mapping:
   - Source Key Column: `ProductId` (links to Product entity)
   - Target Key Column: `SupplierId` (links to Supplier entity)
6. Click **Save**

---

### 3. Bind STOCKS Relationship (Store → Product)

1. Select the **STOCKS** relationship
2. Click **Bind Data**
3. Select source: **Lakehouse** → `FreshMartLakehouse`
4. Select table: **FactStoreInventory**
5. Configure mapping:
   - Source Key Column: `StoreId` (links to Store entity)
   - Target Key Column: `ProductId` (links to Product entity)
6. Click **Save**

> **Note**: This is a many-to-many relationship using FactStoreInventory as a junction table.

---

### 4. Bind EMPLOYS Relationship (Store → Employee)

1. Select the **EMPLOYS** relationship
2. Click **Bind Data**
3. Select source: **Lakehouse** → `FreshMartLakehouse`
4. Select table: **DimEmployee**
5. Configure mapping:
   - Source Key Column: `StoreId` (links to Store entity)
   - Target Key Column: `EmployeeId` (links to Employee entity)
6. Click **Save**

---

### 5. Bind CONTAINS Relationship (ProductBatch → Product)

1. Select the **CONTAINS** relationship
2. Click **Bind Data**
3. Select source: **Lakehouse** → `FreshMartLakehouse`
4. Select table: **DimProductBatch**
5. Configure mapping:
   - Source Key Column: `BatchId` (links to ProductBatch entity)
   - Target Key Column: `ProductId` (links to Product entity)
6. Click **Save**

---

### 6. Bind RECEIVED_AT Relationship (ProductBatch → Store)

1. Select the **RECEIVED_AT** relationship
2. Click **Bind Data**
3. Select source: **Lakehouse** → `FreshMartLakehouse`
4. Select table: **DimProductBatch**
5. Configure mapping:
   - Source Key Column: `BatchId` (links to ProductBatch entity)
   - Target Key Column: `StoreId` (links to Store entity)
6. Click **Save**

---

### 7. Bind ORDERED_BY Relationship (PurchaseOrder → Store)

1. Select the **ORDERED_BY** relationship
2. Click **Bind Data**
3. Select source: **Lakehouse** → `FreshMartLakehouse`
4. Select table: **FactPurchaseOrder**
5. Configure mapping:
   - Source Key Column: `OrderId` (links to PurchaseOrder entity)
   - Target Key Column: `StoreId` (links to Store entity)
6. Click **Save**

---

### 8. Bind FULFILLED_BY Relationship (PurchaseOrder → Supplier)

1. Select the **FULFILLED_BY** relationship
2. Click **Bind Data**
3. Select source: **Lakehouse** → `FreshMartLakehouse`
4. Select table: **FactPurchaseOrder**
5. Configure mapping:
   - Source Key Column: `OrderId` (links to PurchaseOrder entity)
   - Target Key Column: `SupplierId` (links to Supplier entity)
6. Click **Save**

---

### 9. Bind INSPECTED Relationship (QualityInspection → ProductBatch)

1. Select the **INSPECTED** relationship
2. Click **Bind Data**
3. Select source: **Lakehouse** → `FreshMartLakehouse`
4. Select table: **FactQualityInspection**
5. Configure mapping:
   - Source Key Column: `InspectionId` (links to QualityInspection entity)
   - Target Key Column: `BatchId` (links to ProductBatch entity)
6. Click **Save**

---

### 10. Bind PERFORMED_BY Relationship (QualityInspection → Employee)

1. Select the **PERFORMED_BY** relationship
2. Click **Bind Data**
3. Select source: **Lakehouse** → `FreshMartLakehouse`
4. Select table: **FactQualityInspection**
5. Configure mapping:
   - Source Key Column: `InspectionId` (links to QualityInspection entity)
   - Target Key Column: `EmployeeId` (links to Employee entity)
6. Click **Save**

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "No data found" after binding | Ensure OneLake security is disabled |
| Key column mismatch | Verify CSV column names match exactly (case-sensitive) |
| Datetime parsing errors | Ensure ISO 8601 format: `YYYY-MM-DDTHH:MM:SS` |
| Boolean values not recognized | Use `true`/`false` (lowercase), not `1`/`0` |
| Relationship returns no results | Verify both entities are bound first, then bind relationship |

### Validation Steps

After binding all entities and relationships:

1. Go to **Graph Explorer** in the Ontology
2. Run a simple query to verify data:
   ```gql
   MATCH (s:Store)
   RETURN s.StoreName, s.City
   LIMIT 5
   ```
3. Test a relationship:
   ```gql
   MATCH (p:Product)-[:BELONGS_TO]->(c:Category)
   RETURN p.ProductName, c.CategoryName
   LIMIT 10
   ```

---

## Next Steps

After completing Lakehouse bindings:

1. ➡️ Proceed to `eventhouse-binding.md` for timeseries binding
2. ➡️ Test queries in `demo-questions.md`
3. ➡️ Validate all traversal paths work correctly
