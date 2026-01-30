# QC Workflow Guide

This guide explains the Quality Control (QC) workflow for dashboard migration with separate inventory approval stage.

---

## Workflow Overview

```
Step 1: Inventory Generation
    ↓
    Creates volume (if not exists)
    Creates dashboard_inventory/ with inventory.csv
    Creates dashboard_inventory_approved/ (empty)
    ↓
Step 1a: Review & Approve (MANUAL - Choose Option)
    ↓
    ┌──────────────────┬──────────────────────┐
    │   Option A       │    Option B          │
    │   Manual CSV     │    Helper Notebook   │
    │   Edit           │    Interactive       │
    └──────────────────┴──────────────────────┘
    │                  │                      │
    Download CSV       Open Bundle_00a        
    Edit in Excel      View stats & issues    
    Upload to          Apply filters          
    approved/          Upload with CONFIRM    
    │                  │                      │
    └──────────────────┴──────────────────────┘
                       ↓
    dashboard_inventory_approved/inventory.csv uploaded
                       ↓
Step 2: Export & Transform
    ↓
    Verifies approved CSV exists & is recent
    Exports approved dashboards only
    ↓
Step 3: Generate & Deploy
```

---

## 📋 Step-by-Step Instructions

### Step 1: Generate Initial Inventory

```bash
databricks bundle run inventory_generation -t dev --profile e2-field-engg
```

**What Step 1 does:**
- ✅ Checks if volume exists
- ✅ Creates volume if not exists (using path from databricks.yml)
- ✅ Creates `dashboard_inventory/` directory
- ✅ Creates `dashboard_inventory_approved/` directory (empty)
- ✅ Generates inventory CSV

**Output:**
- `dashboard_inventory/inventory.csv` (raw inventory)
- `dashboard_inventory_approved/` (empty, ready for manual upload)

---

### Step 1a: Review & Approve Inventory (CHOOSE ONE OPTION)

## Option A: Manual CSV Editing

**Best for:** Users who prefer Excel/text editor workflow

### Steps:

**1. Download the inventory CSV**

Via Databricks UI:
- Navigate to **Catalog Explorer**
- Browse to your volume → `dashboard_inventory/`
- Download `inventory.csv`

Via code:
```python
volume_base = "/Volumes/archana_krish_fe_dsa/vizient_deep_dive/dashboard_migration"
df = spark.read.csv(f"{volume_base}/dashboard_inventory/inventory.csv", header=True, inferSchema=True)

# Display to review
display(df)

# Or export to local
df.toPandas().to_csv("local_inventory.csv", index=False)
```

**2. Edit the CSV file**

- Open in Excel or text editor
- Identify dashboards to exclude:
  - Dashboards with names like `Dashboard_<id>` (failed API lookups)
  - Inactive dashboards
  - Dashboards with `table_count = 0`
- **Delete entire rows** for unwanted dashboards
- Save your changes

**3. Upload to approved location**

Via Databricks UI:
- Navigate to **Catalog Explorer**
- Browse to your volume → `dashboard_inventory_approved/`
- Click **Upload**
- Select your edited CSV
- Name it: `inventory.csv`

Via code:
```python
# Read your edited CSV
with open("edited_inventory.csv", "r") as f:
    csv_content = f.read()

# Upload
volume_base = "/Volumes/archana_krish_fe_dsa/vizient_deep_dive/dashboard_migration"
approved_path = f"{volume_base}/dashboard_inventory_approved/inventory.csv"
dbutils.fs.put(approved_path, csv_content, overwrite=True)

print(f"✅ Uploaded to: {approved_path}")
```

**4. Verify upload**

```python
volume_base = "/Volumes/archana_krish_fe_dsa/vizient_deep_dive/dashboard_migration"
approved_path = f"{volume_base}/dashboard_inventory_approved/inventory.csv"

df = spark.read.csv(approved_path, header=True, inferSchema=True)
print(f"✅ Approved: {df.count()} dashboards")
display(df)
```

---

## Option B: Interactive Helper Notebook

**Best for:** Users who prefer interactive filtering in Databricks

### Steps:

**1. Open the helper notebook**

In Databricks UI, navigate to:
```
Bundle/Bundle_00a_Review_and_Approve_Inventory.ipynb
```

**2. Run Cell 1: Configuration**

The notebook auto-detects UI vs CLI mode:
- **UI Mode**: Uses default volume path (update if needed)
- **CLI Mode**: Uses parameters from job

**3. Run Cells 2-4: Review Inventory**

- **Cell 2**: Load inventory and see summary stats
  - Total dashboards
  - Activity level distribution
  - Complexity distribution
  - Table usage stats

- **Cell 3**: View full inventory sorted by table count

- **Cell 4**: Identify potential issues
  - Dashboards with fallback names (failed API lookups)
  - Inactive dashboards
  - Dashboards with zero tables

**4. Run Cell 5: Apply Filters**

Customize the filtering logic:

```python
# Example filters (uncomment/modify as needed)

# Filter 1: Remove failed API lookups (RECOMMENDED)
df_approved = df.filter(~df.dashboard_name.startswith('Dashboard_'))

# Filter 2: Only dashboards with tables
df_approved = df_approved.filter(df_approved.table_count > 0)

# Filter 3: Only active dashboards
# df_approved = df_approved.filter(df_approved.activity_level.isin(['Very Active', 'Active']))

# Filter 4: Custom dashboard IDs
# approved_ids = ['id1', 'id2', 'id3']
# df_approved = df_approved.filter(df_approved.dashboard_id.isin(approved_ids))
```

**5. Run Cell 6: Review Approved List**

- View approved inventory
- See summary statistics
- Verify counts look correct

**6. Run Cell 7: Upload with Confirmation**

- **UI Mode**: Type `CONFIRM` to upload
- **CLI Mode**: Auto-uploads

The cell will:
- Show dashboard count and size
- Require explicit confirmation in UI mode
- Upload to `dashboard_inventory_approved/inventory.csv`

**7. Run Cell 8: Verify Upload**

Confirms:
- File exists at correct location
- Dashboard count matches
- Shows file modification timestamp
- Ready for Step 2

---

## Comparison: Option A vs Option B

| Aspect | Option A (Manual CSV) | Option B (Helper Notebook) |
|--------|----------------------|----------------------------|
| **Best for** | Excel power users | SQL/Python users |
| **Learning curve** | Low | Medium |
| **Flexibility** | Very high (any tool) | High (code-based) |
| **Speed** | Fast for small edits | Fast for filters |
| **Automation** | Manual | Semi-automated |
| **Issue detection** | Manual | Automatic |
| **Confirmation** | Manual verify | Built-in verify |
| **Audit trail** | File-based | Code-based |

---

### Step 1b: Verification (Both Options)

After using either option, verify the approved inventory is ready:

```python
volume_base = "/Volumes/archana_krish_fe_dsa/vizient_deep_dive/dashboard_migration"
approved_path = f"{volume_base}/dashboard_inventory_approved/inventory.csv"

# Verify file exists
try:
    df = spark.read.csv(approved_path, header=True, inferSchema=True)
    
    # Check file metadata
    file_info = dbutils.fs.ls(f"{volume_base}/dashboard_inventory_approved/")
    for file in file_info:
        if file.name == 'inventory.csv':
            from datetime import datetime
            modified = datetime.fromtimestamp(file.modificationTime / 1000)
            print(f"✅ Approved inventory ready")
            print(f"   Location: {approved_path}")
            print(f"   Dashboards: {df.count()}")
            print(f"   Modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Size: {file.size / 1024:.1f} KB")
            break
except Exception as e:
    print(f"❌ Verification failed: {e}")
    print("   Make sure you completed Step 1a (Option A or B)")
```

---

## Step 2: Export & Transform

**Prerequisites:**
- ✅ Step 1 completed (inventory generated)
- ✅ Step 1a completed (Option A or B)
- ✅ Approved CSV exists at `dashboard_inventory_approved/inventory.csv`

**Run Step 2:**
```bash
# Deploy bundle (if not already done)
databricks bundle deploy -t dev --profile e2-field-engg

# Run export & transform
databricks bundle run export_transform -t dev --profile e2-field-engg
```

**What Step 2 does:**
1. **Verifies** approved inventory exists and is recent
   - Checks file modification date
   - Warns if file is older than 7 days
   - **Fails immediately** if file is missing
2. **Exports** only the approved dashboards
3. **Applies** transformations (if enabled)
4. **Captures** permissions

**Error handling:**
If approved CSV is missing, you'll see:
```
❌ ERROR: APPROVED INVENTORY NOT FOUND
Expected location: /Volumes/.../dashboard_inventory_approved/inventory.csv

🎯 REQUIRED ACTIONS:
   1. Run Step 1 if you haven't
   2. Then either:
      Option A: Manually edit and upload CSV
      Option B: Run helper notebook
```

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
