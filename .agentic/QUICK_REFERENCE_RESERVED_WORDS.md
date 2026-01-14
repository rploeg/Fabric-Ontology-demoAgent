# Quick Reference: Reserved Word Validation

## 🚨 CRITICAL - Must Check FIRST

Before naming ANY entity, property, or relationship, verify against:
- **Canonical Source**: [`porting/contracts/validation-rules.yaml`](https://github.com/falloutxAY/Unofficial-Fabric-Ontology-SDK/blob/main/porting/contracts/validation-rules.yaml)
- **Common Violations**: See Phase 1 of agent-instructions.md

---

## ❌ Most Common Reserved Words (by violation frequency)

| Word | Recommendation | Reason |
|------|----------------|--------|
| `Product` | `ManufacturedProduct`, `ServiceProduct` | GQL reserved (REAL FAILURE: Rockwell demo) |
| `Order` | `SalesOrder`, `PurchaseOrder`, `TradeOrder`, `StockOrder` | GQL reserved |
| `Match` | `TradeMatch`, `OrderMatch` | GQL reserved |
| `Return` | `ProductReturn`, `OrderReturn` | GQL reserved |
| `Record` | `DataRecord`, `TradeRecord` | GQL reserved |
| `Node` | `NetworkNode`, `GraphNode` | GQL reserved |
| `Edge` | `NetworkEdge`, `Connection` | GQL reserved |
| `Path` | `RoutePath`, `NetworkPath` | GQL reserved |
| `Key` | `AccessKey`, `PrimaryKey` | GQL reserved |
| `Type` | `AssetType`, `OrderType` | GQL reserved |
| `Count` | `ItemCount`, `TradeCount` | GQL reserved |
| `Sum` | `TotalSum`, `OrderSum` | GQL reserved |

---

## ⚠️ Query Alias Reserved Words

**GQL reserved words also apply to `AS` aliases in RETURN statements!**

| ❌ Will Fail | ✅ Use Instead |
|--------------|---------------|
| `AS Product` | `AS ProductName` |
| `AS Type` | `AS TypeName`, `AS AssetKind` |
| `AS Name` | `AS EntityName`, `AS DisplayName` |
| `AS Id` | `AS EntityId`, `AS RecordId` |
| `AS Value` | `AS MetricValue`, `AS DataValue` |
| `AS Data` | `AS DataContent`, `AS RecordData` |
| `AS Date` | `AS EventDate`, `AS RecordDate` |
| `AS Time` | `AS EventTime`, `AS RecordTime` |
| `AS Start` | `AS StartTime`, `AS StartDate` |
| `AS End` | `AS EndTime`, `AS EndDate` |

**Real failure**: `AS Product` caused syntax error in Dairy demo Q3.

---

## 🔴 If Validation FAILS with "Entity 'X' is a reserved word"

### Step 1: Rename Entity
Change `Product` → `ManufacturedProduct`

### Step 2: Bulk Update ALL Files (11+ total)

```
1. Ontology/
   - {demo-slug}.ttl
     • Class definition: :Product → :ManufacturedProduct
     • Property domains: rdfs:domain :Product → :ManufacturedProduct
   
2. Data/
   - Lakehouse/*.csv
     • Table names: DimProduct.csv → DimManufacturedProduct.csv
     • Column headers: ProductId → ManufacturedProductId
     
3. Bindings/
   - bindings.yaml
     • Entity definition: Product → ManufacturedProduct
     • Relationship target: targetEntity: Product → ManufacturedProduct
     
4. Documentation/
   - demo-questions.md
     • Variable names: p: → mp:
     • Property references: ProductId → ManufacturedProductId
     • Query examples: MATCH (p:Product) → MATCH (mp:ManufacturedProduct)
   
   - ontology-structure.md
     • Entity tables: Product → ManufacturedProduct
   
   - .demo-metadata.yaml
     • Entity names: Product → ManufacturedProduct
   
   - README.md
     • Entity summary: Product → ManufacturedProduct
   
   - Bindings/*.md
     • Step names, procedures, examples
```

### Step 3: Re-run Validation
```bash
python -m demo_automation validate ../../{DemoName}
```

### Step 4: Verify Result
- ✅ Should show: `0 errors, 0 warnings`
- ✅ Demo is ready for `fabric-demo setup`

---

## ✅ Validation Checklist (Pre-Generation)

Before generating ontology, verify:

- [ ] **Entity names** - Check against reserved words (all 6-8 entities)
- [ ] **Property names** - Check derived names too (ProductName, ProductFamily, etc.)
- [ ] **Key types** - Only string or int (no decimal, datetime, boolean)
- [ ] **Property uniqueness** - Unique across ALL entities
- [ ] **Binding keys** - sourceKeyColumn and targetKeyColumn match entity key names exactly

---

## 📋 Validation Order (Phase 8)

1. **Check Entity Names** → reserved words list
2. **Check Property Names** → reserved words + uniqueness
3. **Check Data Types** → no decimal, keys are string/int
4. **Check Bindings** → sourceKeyColumn/targetKeyColumn naming
5. **Check CSV Data** → no NULL keys, unique values
6. **Run Validator** → `python -m demo_automation validate`
7. **Fix Errors** → Priority: entity names, then property names, then data
8. **Re-validate** → Repeat until 0 errors

---

## 🔗 References

- **Validation Rules**: `Unofficial-Fabric-Ontology-SDK/porting/contracts/validation-rules.yaml`
- **GQL Reserved Terms**: https://learn.microsoft.com/en-us/fabric/graph/gql-reference-reserved-terms
- **Agent Workflow**: `.agentic/agent-instructions.md` (Phase 1, Phase 4, Phase 8)
- **Real Example**: Rockwell Automation demo (Product → ManufacturedProduct refactoring)

---

## 📊 Real-World Stats

- **Reserved Words**: 280+ in validation-rules.yaml
- **Rockwell Failure**: 1 entity name + 5+ derived properties = 11+ files updated
- **Validation Time**: ~30 seconds
- **Bulk Refactor Time**: ~5 minutes for systematic replacement
- **Success Rate**: 100% after refactoring (0 errors, 0 warnings)

