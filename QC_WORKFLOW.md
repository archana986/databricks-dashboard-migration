# QC Workflow Guide

This guide explains the Quality Control (QC) workflow for dashboard migration with mandatory inventory approval stage.

---

## Workflow Overview

```
Step 1: Inventory Generation (Automated)
    ↓
    Creates volume and directories
    Saves dashboard_inventory/inventory.csv
    ↓
Step 2: Review & Approve (REQUIRED MANUAL STEP - UI Only)
    ↓
    Load inventory → View stats → Apply filters → Type CONFIRM → Upload
    ↓
    Saves dashboard_inventory_approved/inventory.csv
    ↓
Step 3: Export & Transform (Automated)
    ↓
    Verifies approved CSV → Exports dashboards
    ↓
Step 4: Generate & Deploy (Automated)
```

---

## Step 1: Generate Inventory

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
- `dashboard_inventory_approved/` (empty, ready for Step 2)

---

## Step 2: Review & Approve (REQUIRED)

**Important:** This step MUST be completed in Databricks UI. It cannot be run via CLI or automated.

### Prerequisites
- Step 1 completed
- Databricks UI access
- Cluster running

### Instructions

#### 1. Open the Notebook

In Databricks UI, navigate to:
```
Bundle/Bundle_02_Review_and_Approve_Inventory.ipynb
```

#### 2. Update Configuration (Cell 1)

Verify the volume path is correct:
```python
volume_base = "/Volumes/archana_krish_fe_dsa/vizient_deep_dive/dashboard_migration"
```

If your path is different, edit Cell 1 and update `volume_base`.

#### 3. Load and Review Inventory (Cells 2-4)

**Cell 2: Load Inventory**
- Loads `dashboard_inventory/inventory.csv`
- Shows summary statistics:
  - Total dashboards
  - Activity level distribution
  - Complexity distribution
  - Table usage stats

**Cell 3: View Full Inventory**
- Displays all dashboards sorted by table count
- Scroll through to spot-check

**Cell 4: Identify Issues**
- **Fallback Names**: Dashboards named `Dashboard_<id>` (failed API lookups)
  - Recommendation: EXCLUDE from migration
- **Inactive Dashboards**: No recent usage
  - Consider excluding if unused
- **Zero Tables**: Dashboards with no table references
  - May be text-only or have issues

#### 4. Apply Filters (Cell 5)

Customize the filtering logic. Default filters:

```python
# Filter 1: Remove fallback names (enabled by default)
df_approved = df.filter(~df.dashboard_name.startswith('Dashboard_'))

# Filter 2: Require tables (enabled by default)
df_approved = df_approved.filter(df_approved.table_count > 0)
```

**Optional filters** (uncomment to enable):

```python
# Filter 3: Only active dashboards
# df_approved = df_approved.filter(df_approved.activity_level != 'Inactive')

# Filter 4: Minimum activity level
# df_approved = df_approved.filter(df_approved.activity_level.isin(['Very Active', 'Active']))

# Filter 5: Custom dashboard IDs
# approved_ids = ['id1', 'id2', 'id3']
# df_approved = df_approved.filter(df_approved.dashboard_id.isin(approved_ids))
```

**Tip:** Start with the default filters (1-2), then customize based on your needs.

#### 5. Review Approved List (Cell 6)

- View the filtered inventory
- Check dashboard counts match your expectations
- Verify no critical dashboards were filtered out
- Review summary statistics

#### 6. Upload with Confirmation (Cell 7)

**This is the critical step with safety checks:**

1. Cell 7 checks if a file already exists in `dashboard_inventory_approved/`
2. If exists, you'll see:
   ```
   ⚠️  WARNING: EXISTING FILE WILL BE OVERWRITTEN
   
   📋 Current approved inventory: 15 dashboards
   📋 New filtered inventory: 10 dashboards
   
   If you have manually uploaded a file to dashboard_inventory_approved/,
   it will be REPLACED with the results from Cell 5-6 filters.
   
   Typing CONFIRM means you ACCEPT this new filtered inventory
   and discard any previously uploaded file.
   ```

3. Type `CONFIRM` (uppercase, exact spelling) to proceed
4. Any other text will cancel the upload

**Example:**
```
⚠️  Type 'CONFIRM' to accept and upload this filtered inventory: CONFIRM

✅ UPLOADED SUCCESSFULLY
📁 Location: /Volumes/.../dashboard_inventory_approved/inventory.csv
📊 Dashboards: 10
```

#### 7. Verify Upload (Cell 8)

Confirms:
- File exists at correct location
- Dashboard count matches
- Shows file modification timestamp
- Confirms ready for Step 3

**Example output:**
```
======================================================================
✅ VERIFICATION SUCCESSFUL
======================================================================
📁 Location: /Volumes/.../dashboard_inventory_approved/inventory.csv
📊 Dashboards: 10
📅 Modified: 2026-01-30 14:23:45
💾 Size: 12.3 KB
======================================================================

🎯 READY FOR STEP 3
   Run: databricks bundle run export_transform -t dev
======================================================================
```

---

### Why This Step is Manual

- **Requires human judgment** to identify problematic dashboards
- **Prevents accidental migration** of deleted/broken dashboards
- **Provides audit trail** with explicit CONFIRM action
- **Allows customization** of filters based on business needs
- **Enforces quality control** - cannot be skipped or automated

---

## Step 3: Export & Transform

**Prerequisites:**
- ✅ Step 1 completed (inventory generated)
- ✅ Step 2 completed (inventory reviewed and approved)
- ✅ Approved CSV exists at `dashboard_inventory_approved/inventory.csv`

**Run Step 3:**
```bash
# Deploy bundle (if not already done)
databricks bundle deploy -t dev --profile e2-field-engg

# Run export & transform
databricks bundle run export_transform -t dev --profile e2-field-engg
```

**What Step 3 does:**
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
   1. Run Step 1: databricks bundle run inventory_generation -t dev
   2. Run Step 2: Open Bundle/Bundle_02_Review_and_Approve_Inventory.ipynb
              in Databricks UI and complete the review process
```

---

## Common Filtering Scenarios

### Scenario 1: Remove Failed API Lookups (Default)
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

## Inventory Fields Reference

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

## Troubleshooting

### Issue: "CONFIRM didn't work"
**Solution**: Make sure you typed `CONFIRM` in all uppercase, exact spelling

### Issue: "Upload cancelled accidentally"
**Solution**: Re-run Cell 7 and type CONFIRM again. No harm done.

### Issue: "Step 3 says approved inventory not found"
**Solution**: 
1. Verify Cell 8 showed "VERIFICATION SUCCESSFUL"
2. Check the file exists: `dbutils.fs.ls(f"{volume_base}/dashboard_inventory_approved/")`
3. If missing, re-run Cell 7 in Step 2

### Issue: "Wrong dashboards in approved inventory"
**Solution**: 
1. Go back to Step 2, Cell 5
2. Adjust your filters
3. Run Cells 5-8 again
4. The new upload will replace the old one

---

**Last Updated**: 2026-01-30  
**Related Files**: 
- `Bundle/Bundle_02_Review_and_Approve_Inventory.ipynb` (Step 2 notebook)
- `databricks.yml` (Configuration)
- `README.md` (Quick start guide)
