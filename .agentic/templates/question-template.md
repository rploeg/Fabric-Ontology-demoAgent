# Demo Question Template

Use this template for each of the 5 demo questions.

---

## Question {N}: {Title}

### Business Question

**"{Natural language question that a business user would ask}"**

### Why This Matters

{2-3 sentences explaining the business context and value of answering this question}

### Graph Traversal

```
Entity1 -[relationship1]-> Entity2 -[relationship2]-> Entity3
```

### GQL Query

```gql
MATCH (a:EntityType)-[:relationship]->(b:EntityType)
WHERE a.property = 'value'
RETURN a.prop1, b.prop2
ORDER BY a.prop1
LIMIT 10
```

### Expected Results

| Column1 | Column2 | Column3 |
|---------|---------|---------|
| value1  | value2  | value3  |
| value4  | value5  | value6  |

### Why Ontology is Better

**Traditional Approach:**
{Describe how this would be solved with SQL - mention the complexity, number of JOINs, domain knowledge required}

**Ontology Advantage:**
- {Benefit 1 - e.g., "Natural traversal follows business relationships"}
- {Benefit 2 - e.g., "No JOIN syntax required"}
- {Benefit 3 - e.g., "Query intent is clear from relationship names"}

---

## GQL Syntax Reference

### Supported Patterns

```gql
-- Basic match
MATCH (n:EntityType)
RETURN n.property

-- Relationship traversal
MATCH (a:Entity1)-[:relationship]->(b:Entity2)
RETURN a.prop, b.prop

-- Multi-hop with bounded quantifier
MATCH (a:Entity1)-[:rel]->{1,4}(b:EntityN)
RETURN a, b

-- Filtering (use FILTER, not WHERE after MATCH)
MATCH (n:Entity)
FILTER n.property = 'value'
RETURN n
```

### ⛔ CRITICAL: Aggregation with GROUP BY

**Fabric Graph requires LET statements for GROUP BY columns.**
Property access (node.Property) is NOT allowed in GROUP BY clause.

**❌ WRONG:**
```gql
MATCH (a:Entity1)-[:rel]->(b:Entity2)
RETURN a.category, count(b) AS total
GROUP BY a.category  -- ERROR: Cannot use a.category
```

**✅ CORRECT:**
```gql
MATCH (a:Entity1)-[:rel]->(b:Entity2)
LET category = a.category
RETURN category, count(b) AS total
GROUP BY category
```

### Aggregation Query Template

```gql
MATCH (a:Entity1)-[:rel]->(b:Entity2)
FILTER a.status = 'Active'                    -- Use FILTER not WHERE
LET groupCol1 = a.Property1                   -- Assign to variable
LET groupCol2 = b.Property2                   -- for GROUP BY
RETURN groupCol1,
       groupCol2,
       count(*) AS recordCount,
       sum(b.Amount) AS totalAmount
GROUP BY groupCol1, groupCol2                 -- Use variable names
ORDER BY totalAmount DESC
```

### DateTime Filtering

```gql
-- Use zoned_datetime(), NOT datetime()
MATCH (n:Entity)
FILTER n.Timestamp > zoned_datetime('2025-01-10T00:00:00Z')
RETURN n
```

### NOT Supported

- OPTIONAL MATCH
- Unbounded quantifiers (use {1,8} max)
- UNION DISTINCT (only UNION ALL)
- Multiple labels on nodes/edges
- `datetime()` function - use `zoned_datetime()`
- Property access in GROUP BY - use LET variables
- count(DISTINCT var) with GROUP BY may cause issues

---

## Question Themes

| # | Theme | Minimum Hops | Example Focus |
|---|-------|--------------|---------------|
| 1 | Supply Chain Traceability | 3 | Which suppliers provided components for problematic batches? |
| 2 | Impact Assessment | 4 | For a complaint, trace back through the entire supply chain |
| 3 | Operational Correlation | 2 + timeseries | Which facilities have declining metrics AND quality events? |
| 4 | Compliance/Regulatory | 2 | Which products have pending submissions with complaints? |
| 5 | End-to-End Genealogy | 4 | Complete product history from materials to post-market |
