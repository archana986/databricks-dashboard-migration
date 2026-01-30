# Inventory-First Workflow

## What Changed

The migration workflow now includes a **mandatory inventory review step** before any exports happen.

---

## New Workflow

### Before (Old Way):
```
1. Discover dashboards
2. Immediately export all
3. Transform all
```

### Now (New Way):
```
1. Generate comprehensive inventory
2. Save inventory to CSV
3. Display inventory for review
4. PAUSE - You review and validate
5. Confirm to proceed
6. Export only validated dashboards
7. Transform
```

---

## How It Works

### Step 1: Generate Inventory (Automatic)

```python
# In Bundle_01, Cell 3
inventory = generate_inventory(
    source_client,
    include_published_status=True,  # Shows if published
    include_metadata=True            # Shows warehouse, dates, etc.
)
```

**Output:**
```
dashboard_id | dashboard_name | published | path | warehouse_id | created_time
01f0fb1a...  | Sales Report   | Yes       | /Sh... | abc123     | 2024-01-15
01efeeea...  | Test Dashboard | No        | /Us... | abc123     | 2024-01-20
```

### Step 2: Save to CSV (Automatic)

```python
# Saves to volume
save_inventory_to_csv(inventory, csv_path)
```

**Saved at:** `/Volumes/your_catalog/your_schema/dashboard_migration/dashboard_inventory/inventory.csv`

### Step 3: Display for Review (Automatic)

```python
# Shows formatted table
display(df)

# Shows summary
Total dashboards: 25
Published: 20
Unpublished: 5
```

### Step 4: Review and Edit (MANUAL)

**You decide:**

**Option A: Accept all dashboards**
- Just proceed to next cell

**Option B: Exclude some dashboards**
1. Open CSV in volume (use Databricks UI or notebook)
2. Delete rows for dashboards you don't want
3. Save CSV
4. Proceed to next cell

**Option C: Edit in notebook**
```python
# Load CSV
df = pd.read_csv(...)

# Filter out test dashboards
df = df[~df['dashboard_name'].str.contains('test', case=False)]

# Save back
df.to_csv(...)
```

### Step 5: Confirm and Load (MANUAL)

```python
# In Bundle_01, Cell 3c
INVENTORY_CONFIRMED = False  # ← YOU CHANGE THIS TO True

if INVENTORY_CONFIRMED:
    dashboards = load_inventory_from_csv(csv_path)
    # Proceeds with migration
else:
    raise Exception("Review inventory first!")
```

**This is your safety gate!** ✅

### Step 6: Export (Automatic After Confirmation)

```python
# Only runs if INVENTORY_CONFIRMED = True
for dash in dashboards:
    export_dashboard(...)
```

---

## Benefits

**What you get:**

1. **Always see what will be migrated** before it happens
2. **Exclude test/temp dashboards** easily
3. **Audit trail** - CSV shows exactly what was migrated
4. **Business approval** - Share CSV for review before migration
5. **Repeatable** - Re-run with same exact list
6. **No surprises** - Know exactly what dashboards will migrate

**Prevents:**

- Accidentally migrating 100 dashboards when you wanted 5
- Including test dashboards in production
- Migrating wrong dashboards
- Surprises during long-running migrations

---

## CSV File Details

### Location

```
/Volumes/{catalog}/{schema}/dashboard_migration/dashboard_inventory/inventory.csv
```

### Columns

| Column | Description |
|--------|-------------|
| `dashboard_id` | UUID of dashboard (required for export) |
| `dashboard_name` | Display name |
| `published` | "Yes" or "No" |
| `path` | Workspace path |
| `warehouse_id` | SQL warehouse used |
| `created_time` | When dashboard was created |
| `updated_time` | Last update time |
| `link` | Direct link to dashboard |

### How to Edit

**Option 1: In Databricks UI**
1. Go to: Catalog → your_catalog → your_schema → dashboard_migration → dashboard_inventory
2. Click on `inventory.csv`
3. Download it
4. Edit in Excel/Numbers/CSV editor
5. Upload back to same location

**Option 2: In Notebook**
```python
# Read from volume
csv_path = "/Volumes/.../inventory.csv"
content = dbutils.fs.head(csv_path, 10485760)
df = pd.read_csv(io.StringIO(content))

# Edit (example: remove test dashboards)
df = df[~df['dashboard_name'].str.contains('test', case=False)]

# Save back
csv_content = df.to_csv(index=False)
dbutils.fs.put(csv_path, csv_content, overwrite=True)
```

---

## Example Workflow

### Scenario: Migrate 50 Dashboards, Exclude 5 Test Ones

#### Step 1: Generate Inventory
```
✅ Generated inventory: 50 dashboards

Showing:
1. Sales Report (Published)
2. Marketing Dashboard (Published)
3. Test - Sales v1 (Not Published)  ← Don't want this
4. Customer Analytics (Published)
5. Test - Marketing (Not Published)  ← Don't want this
...
```

#### Step 2: Review
You see test dashboards you don't want.

#### Step 3: Edit CSV
Remove rows 3, 5, and other test dashboards.

#### Step 4: Confirm
```python
INVENTORY_CONFIRMED = True  # Ready to proceed
```

#### Step 5: Load Validated
```
✅ Loaded 45 validated dashboards  # 50 - 5 test ones
```

#### Step 6: Export
Migration proceeds with only the 45 validated dashboards!

---

## Cell Structure in Updated Notebooks

### Bundle_03_Export_and_Transform.ipynb:

```
Cell 0: Overview
Cell 1: Install Dependencies
Cell 2: Load Config
Cell 3: STEP 1 - Generate Inventory (automatic)
Cell 3a: Save Inventory to CSV (automatic)
Cell 3b: Display for Review (automatic)
Cell 3c: Confirm and Load Validated Inventory (MANUAL - you set flag)
Cell 4: STEP 3 - Export Dashboards (automatic after confirmation)
Cell 5: Transform Dashboards (automatic)
```

**Key change:** Cells 3a, 3b, 3c are new and create the review checkpoint!

---

## Configuration Option

You can also control this via config:

```yaml
dashboard_selection:
  method: "catalog_filter"
  
  # Optional: Force inventory review
  require_inventory_review: true  # Enforces the review step
  inventory_path: "dashboard_inventory/inventory.csv"
```

---

## Testing the New Workflow

After you push and pull:

1. **Open Bundle_01** in Databricks Repos
2. **Run up to Cell 3b** - You'll see inventory
3. **Review the inventory** - Check if list is correct
4. **Edit CSV if needed** - Remove unwanted dashboards
5. **Run Cell 3c** - Set `INVENTORY_CONFIRMED = True`
6. **Run remaining cells** - Export and transform proceed

**Now you have control!** 🎯

---

## Summary

**What:** Mandatory inventory generation and review before migration

**Why:** Prevents accidental migrations, provides audit trail, enables approval workflow

**How:** New cells in notebooks generate/save/display inventory, require confirmation before proceeding

**Result:** You always know exactly what will be migrated before it happens!

**Ready to push these changes to Git!** 🚀
