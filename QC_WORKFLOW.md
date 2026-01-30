# QC Workflow Guide

This guide explains the Quality Control (QC) workflow for dashboard migration with separate inventory approval stage.

---

## 🔄 Workflow Overview

```
Step 1: Inventory Generation
    ↓
    Generates: dashboard_inventory/inventory.csv
    ↓
Step 1a: Review & Approve (THIS STEP)
    ↓
    Review → Filter → Approve
    ↓
    Generates: dashboard_inventory_approved/inventory.csv
    ↓
Step 2: Export & Transform
    ↓
    Reads from: dashboard_inventory_approved/inventory.csv
    ↓
Step 3: Generate & Deploy
```

---

## 📋 Step-by-Step Instructions

### Step 1: Generate Initial Inventory (Already Done)

```bash
databricks bundle run inventory_generation -t dev --profile e2-field-engg
```

**Output:** `dashboard_inventory/inventory.csv`

---

### Step 1a: Review & Approve Inventory

#### Option A: Via Notebook (Recommended)

1. **Open the review notebook** in Databricks UI:
   ```
   Bundle/Bundle_00a_Review_and_Approve_Inventory.ipynb
   ```

2. **Update Cell 1** with your volume path (if different):
   ```python
   VOLUME_BASE = "/Volumes/your_catalog/your_schema/dashboard_migration"
   ```

3. **Run Cells 1-4** to review:
   - Cell 2: Load inventory and see summary stats
   - Cell 3: View full inventory
   - Cell 4: Identify potential issues (failed lookups, inactive dashboards, etc.)

4. **Customize Cell 5** filtering logic:
   ```python
   # Example: Remove failed API lookups
   df_approved = df.filter(~df.dashboard_name.startswith('Dashboard_'))
   
   # Example: Only active dashboards
   df_approved = df_approved.filter(df_approved.activity_level != 'Inactive')
   
   # Example: Only dashboards with tables
   df_approved = df_approved.filter(df_approved.table_count > 0)
   ```

5. **Run Cell 6** to review approved list

6. **Run Cell 7** to save approved inventory

**Output:** `dashboard_inventory_approved/inventory.csv`

#### Option B: Via SQL/Python (Quick)

```python
# Load inventory
df = spark.read.csv(
    "/Volumes/archana_krish_fe_dsa/vizient_deep_dive/dashboard_migration/dashboard_inventory/inventory.csv",
    header=True, inferSchema=True
)

# Apply your filters
df_approved = df.filter(
    (~df.dashboard_name.startswith('Dashboard_')) &  # Remove fallback names
    (df.table_count > 0)  # Only dashboards with table references
)

# Save to approved location
df_approved.toPandas().to_csv(
    "/Volumes/archana_krish_fe_dsa/vizient_deep_dive/dashboard_migration/dashboard_inventory_approved/inventory.csv",
    index=False
)

print(f"✅ Approved {df_approved.count()} dashboards")
```

---

### Step 2: Export & Transform (Uses Approved Inventory)

The configuration is **already set up** to read from `dashboard_inventory_approved/`.

**Run Step 2:**
```bash
# Redeploy to pick up config changes
databricks bundle deploy -t dev --profile e2-field-engg

# Run export & transform
databricks bundle run export_transform -t dev --profile e2-field-engg
```

**What Step 2 does:**
- Reads `dashboard_inventory_approved/inventory.csv`
- Exports only the approved dashboards
- Applies transformations
- Exports permissions

---

## 🎯 Common Filtering Scenarios

### Scenario 1: Remove Failed API Lookups
```python
df_approved = df.filter(~df.dashboard_name.startswith('Dashboard_'))
```

### Scenario 2: Only Active Dashboards
```python
df_approved = df.filter(df.activity_level.isin(['Very Active', 'Active', 'Moderate']))
```

### Scenario 3: Minimum Usage Threshold
```python
df_approved = df.filter((df.unique_users >= 2) & (df.total_access_count >= 10))
```

### Scenario 4: By Complexity
```python
# Only migrate simple and medium complexity
df_approved = df.filter(df.complexity.isin(['Low', 'Medium']))
```

### Scenario 5: Specific Dashboards
```python
approved_ids = ['01efeeea51701a2c949822fad50b0981', '01efeef2957a1f0a82d4b82ac128a87f']
df_approved = df.filter(df.dashboard_id.isin(approved_ids))
```

---

## 🔧 Configuration Details

### databricks.yml Settings

**Step 1 Output:**
```yaml
inventory_path: dashboard_inventory  # Where Step 1 writes
```

**Step 2 Input:**
```yaml
inventory_path: dashboard_inventory_approved  # Where Step 2 reads from
```

This separation allows QC review between steps!

---

## 📊 Inventory Fields Reference

| Field | Description |
|-------|-------------|
| `dashboard_id` | Unique dashboard identifier |
| `dashboard_name` | Dashboard display name |
| `table_count` | Number of tables referenced |
| `unique_tables` | Count of unique table references |
| `catalog_count` | Number of catalogs used |
| `activity_level` | Very Active / Active / Moderate / Inactive |
| `complexity` | High / Medium / Low (based on table count) |
| `last_accessed` | Most recent access timestamp |
| `unique_users` | Number of unique users |
| `total_access_count` | Total access events |

---

## ✅ Best Practices

1. **Always Review First**: Don't blindly approve all dashboards
2. **Check Failed Lookups**: Dashboards with `Dashboard_<id>` names likely don't exist
3. **Consider Activity**: Inactive dashboards may not need migration
4. **Test with Small Set**: For first migration, approve 2-3 dashboards only
5. **Document Decisions**: Keep notes on why dashboards were excluded
6. **Backup Original**: The original inventory.csv is preserved for reference

---

## 🚨 Troubleshooting

### Issue: "No dashboards in approved inventory"
**Solution**: Check your filters in Cell 5 - they may be too restrictive

### Issue: "Step 2 still reads from dashboard_inventory"
**Solution**: 
1. Verify `databricks.yml` line ~100 has `inventory_path: ${var.inventory_approved_path}`
2. Redeploy: `databricks bundle deploy -t dev`

### Issue: "Approved CSV not found"
**Solution**: Make sure you ran Cell 7 in the review notebook

---

**Last Updated**: 2026-01-30  
**Related Files**: 
- `Bundle/Bundle_00a_Review_and_Approve_Inventory.ipynb` (Review notebook)
- `databricks.yml` (Configuration)
