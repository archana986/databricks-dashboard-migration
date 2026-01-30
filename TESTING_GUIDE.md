# Dashboard Migration: Complete Testing Guide

## Overview

This guide provides **step-by-step instructions** to test the dashboard migration end-to-end. You'll test the **Bundle approach first** (recommended), then optionally the Manual approach.

**Two approaches available:**
- **Bundle Approach** ← **Test this first** (automated, no timeouts)
- Manual Approach (manual import + permissions)

---

## Step 0: Upload Files to Databricks (Do This First!)

Before you can test anything, you need to get your migration files into Databricks workspace.

### Quick Upload: Use Sync Script (Recommended for Testing)

**From your computer terminal:**

```bash
# 1. Navigate to migration folder
cd "/Users/archana.krishnamurthy/Downloads/Career & Growth/Cursor/Customer-Work/Catalog Migration"

# 2. Configure Databricks CLI (one-time only)
databricks configure --token --profile e2-demo-field-eng

# When prompted, enter:
# Host: https://e2-demo-field-eng.cloud.databricks.com
# Token: [your PAT token from Databricks User Settings → Access Tokens]

# 3. Sync all files
python sync_to_databricks.py
```

**Expected output:**
```
================================================================================
DATABRICKS WORKSPACE SYNC
================================================================================

✅ Connected to workspace
   User: archana.krishnamurthy@databricks.com
   Workspace: https://e2-demo-field-eng.cloud.databricks.com

✅ Target directory ready

================================================================================
UPLOADING FILES
================================================================================

ℹ️  Uploading: config/config.yaml
✅ ✓ config/config.yaml
ℹ️  Uploading: helpers/__init__.py
✅ ✓ helpers/__init__.py
...
(32 more files)

================================================================================
SYNC SUMMARY
================================================================================

Results:
  ✅ Uploaded:  32 files
  ❌ Failed:    0 files
  ⊘ Skipped:   0 files

✅ Sync completed!

View files at:
  https://e2-demo-field-eng.cloud.databricks.com#workspace/Workspace/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration
```

**Verify:** Open that URL and check all folders are there!

**For detailed sync instructions:** See `SYNC_SCRIPT_README.md`

**For automatic syncing (better for production):** See `DATABRICKS_REPOS_SETUP.md`

---

## Prerequisites (Do These Next!)

### 1. Setup Authentication

**You are using PAT tokens.** (OAuth is recommended by Databricks but requires no setup)

#### Option A: PAT Token Authentication (You are using this)

Store your credentials securely:

```python
# In Databricks notebook or CLI
dbutils.secrets.createScope(scope="migration")

# Source workspace PAT token
dbutils.secrets.put(scope="migration", key="source-token", string_value="your-source-token-here")

# Target workspace PAT token  
dbutils.secrets.put(scope="migration", key="target-token", string_value="your-target-token-here")
```

**How to get PAT tokens:**
1. Go to workspace → User Settings → Developer → Access Tokens
2. Click "Generate New Token"
3. Copy and store in secrets above

#### Option B: OAuth Authentication (RECOMMENDED by Databricks)

**No setup needed!** Just update config:

```yaml
# In config/config.yaml
source:
  auth:
    method: "oauth"
    # No secrets or tokens needed - uses notebook authentication automatically

target:
  auth:
    method: "oauth"
    # No secrets or tokens needed
```

**Benefits of OAuth:**
- ✅ No token expiration
- ✅ Better security (no secrets to manage)
- ✅ Automatic credential renewal
- ✅ Uses your identity when running notebooks

**Limitation:** Requires running notebooks in workspace (not external scripts)

#### Comparison: OAuth vs PAT

| Feature | OAuth (Recommended) | PAT (You are using) |
|---------|-------------------|---------------------|
| **Setup** | None - automatic | Create & store tokens |
| **Expiration** | Never | 90 days (default) |
| **Security** | Better (no secrets) | Good (if secrets secured) |
| **Rotation** | Automatic | Manual |
| **Identity** | Your user | Token identity |
| **Best for** | Interactive notebooks | Scripts/automation |
| **Configuration** | `method: "oauth"` | `method: "pat"` + secrets |

**Your choice (PAT) is fine for:**
- Testing and development
- When you need explicit control
- When tokens are properly secured in secrets

**Consider OAuth when:**
- Moving to production
- Want zero maintenance
- Running interactively in notebooks

### 2. Create Unity Catalog Volume

Create the volume that will store migration files:

```sql
-- In Databricks SQL or notebook
CREATE CATALOG IF NOT EXISTS your_catalog;
CREATE SCHEMA IF NOT EXISTS your_catalog.your_schema;

CREATE VOLUME IF NOT EXISTS your_catalog.your_schema.dashboard_migration;
```

### 3. Create CSV Mapping File

Create the catalog/schema mapping file:

**Location:** `/Volumes/your_catalog/your_schema/dashboard_migration/mappings/catalog_schema_mapping.csv`

**Content:**
```csv
old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
old_catalog,old_schema,customers,new_catalog,new_schema,customers,,
old_catalog,old_schema,orders,new_catalog,new_schema,orders,,
```

**How to create:**

```python
# In Databricks notebook
csv_content = """old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
old_catalog,old_schema,customers,new_catalog,new_schema,customers,,
old_catalog,old_schema,orders,new_catalog,new_schema,orders,,"""

dbutils.fs.put(
    "/Volumes/your_catalog/your_schema/dashboard_migration/mappings/catalog_schema_mapping.csv",
    csv_content,
    overwrite=True
)
```

### 4. Configure config.yaml

Edit `/config/config.yaml` with your values:

```yaml
source:
  workspace_url: "https://your-source-workspace.cloud.databricks.com"
  auth:
    method: "pat"  # You are using PAT
    pat:
      secret_scope: "migration"
      secret_key: "source-token"
    
    # OAuth (recommended - uncomment to use instead of PAT)
    # method: "oauth"
    # Note: No secrets needed with OAuth

target:
  workspace_url: "https://your-target-workspace.cloud.databricks.com"
  auth:
    method: "pat"  # You are using PAT
    pat:
      secret_scope: "migration"
      secret_key: "target-token"
    
    # OAuth (recommended - uncomment to use instead of PAT)
    # method: "oauth"
    # Note: No secrets needed with OAuth

paths:
  volume_base: "/Volumes/your_catalog/your_schema/dashboard_migration"
  target_parent_path: "/Shared/Migrated_Dashboards"

dashboard_selection:
  method: "catalog_filter"
  catalog_filter:
    catalog: "your_source_catalog"
    use_system_tables: true

transformation:
  enabled: true
  mapping_csv: "mappings/catalog_schema_mapping.csv"

permissions:
  capture: true
  dry_run: true

warehouse:
  use_name_lookup: true
  warehouse_name: "Your Warehouse Name"

bundle:
  name: "dashboard_migration"
  embed_credentials: true
  mode: "production"
```

**Key values to update:**
- `source.workspace_url` → Your source workspace URL
- `target.workspace_url` → Your target workspace URL
- `paths.volume_base` → Your UC Volume path
- `dashboard_selection.catalog_filter.catalog` → Catalog containing dashboards
- `warehouse.warehouse_name` → Target warehouse name
- Update CSV mapping with your actual old/new catalog/schema names

---

## Part 1: Bundle Approach (Test First)

The Bundle approach is **faster, more reliable**, and has **no timeout issues**.

### Step 1: Open Bundle_01 Notebook

**Path:** `Bundle/Bundle_03_Export_and_Transform.ipynb`

**Where to run:** Source workspace (where dashboards currently exist)

### Step 2: Run All Cells in Bundle_01

Click **Run All** or run each cell sequentially.

**What it does:**
- Cell 0: Installs dependencies
- Cell 1: Imports helper modules
- Cell 2: Loads config from `config/config.yaml`
- Cell 3: Discovers dashboards from source
- Cell 4: Exports JSONs and permissions
- Cell 5: Transforms catalog/schema names

**Expected output:**
```
================================================================================
LOADING CONFIGURATION
================================================================================

✅ Configuration loaded

   Source: https://your-source-workspace.cloud.databricks.com
   Volume base: /Volumes/your_catalog/your_schema/dashboard_migration
   Discovery method: catalog_filter

📁 Ensuring directories exist...
   ✅ Export: /Volumes/.../exported
   ✅ Transformed: /Volumes/.../transformed

================================================================================
DISCOVERING DASHBOARDS
================================================================================

🔗 Connecting to source workspace...
   ✅ Connected

🔍 Discovering dashboards using: catalog_filter

✅ Found 3 dashboard(s)

[Table showing discovered dashboards]

================================================================================
EXPORTING DASHBOARDS & PERMISSIONS
================================================================================

[1/3] Exporting: Dashboard Name 1
   ✅ Exported JSON
   🔐 Permissions: 5 ACL(s)

[2/3] Exporting: Dashboard Name 2
   ✅ Exported JSON
   🔐 Permissions: 3 ACL(s)

...

✅ Successfully exported: 3/3

================================================================================
TRANSFORMING DASHBOARDS
================================================================================

📋 Loading mappings: /Volumes/.../mappings/catalog_schema_mapping.csv
   ✅ Loaded 2 mapping rule(s)

[1/3] Transforming: Dashboard Name 1
   ✅ Transformed
[2/3] Transforming: Dashboard Name 2
   ✅ Transformed
...

================================================================================
SUMMARY
================================================================================

✅ Exported: 3/3
✅ Transformed: 3/3

📁 Files ready at: /Volumes/.../transformed

▶️  Next: Run Bundle_04_Generate_and_Deploy.ipynb
```

**✅ Verification:**

Check that files were created:

```python
# Run this in a new cell
dbutils.fs.ls("/Volumes/your_catalog/your_schema/dashboard_migration/exported")
dbutils.fs.ls("/Volumes/your_catalog/your_schema/dashboard_migration/transformed")
```

You should see:
- `exported/dashboard_*_*.lvdash.json` (original files)
- `exported/dashboard_*_*_permissions.json` (permissions)
- `transformed/dashboard_*_*.lvdash.json` (transformed files)

**Check transformations worked:**

```python
# Read a transformed file
content = dbutils.fs.head("/Volumes/.../transformed/dashboard_XXX.lvdash.json", 1000)
print(content)
# You should see NEW catalog/schema names, not old ones
```

### Step 3: Open Bundle_02 Notebook

**Path:** `Bundle/Bundle_04_Generate_and_Deploy.ipynb`

**Where to run:** Can run in either workspace (it deploys to target)

### Step 4: Run All Cells in Bundle_02

Click **Run All** or run each cell sequentially.

**What it does:**
- Cell 0: Installs dependencies
- Cell 1: Imports helper modules
- Cell 2: Loads config
- Cell 3: Loads transformed dashboards and permissions
- Cell 4: Generates bundle structure
- Cell 5: Validates bundle
- Cell 6: Deploys to target workspace
- Cell 7: Verifies deployment

**Expected output:**
```
================================================================================
LOADING CONFIGURATION
================================================================================

✅ Configuration loaded

   Target workspace: https://your-target-workspace.cloud.databricks.com
   Bundle name: dashboard_migration
   Parent path: /Shared/Migrated_Dashboards
   Warehouse: Your Warehouse Name

================================================================================
LOADING DASHBOARDS & PERMISSIONS
================================================================================

📂 Loading transformed dashboards from: /Volumes/.../transformed
   ✅ Found 3 dashboard(s)

🔐 Loading permissions from: /Volumes/.../exported
   ✅ Loaded permissions for 3 dashboard(s)

[Table showing dashboards to deploy]

================================================================================
GENERATING BUNDLE STRUCTURE
================================================================================

📦 Generating bundle: dashboard_migration
   Output path: /Volumes/.../bundles

✅ Bundle generated at: /Volumes/.../bundles/dashboard_migration

📋 Bundle structure:
   ├── databricks.yml
   ├── resources/
   │   └── dashboards.yml
   └── src/
       └── dashboards/
           └── 3 .lvdash.json file(s)

================================================================================
VALIDATING BUNDLE
================================================================================

🔍 Running: databricks bundle validate

✅ Bundle validation passed

================================================================================
DEPLOYING BUNDLE
================================================================================

🚀 Deploying to: https://your-target-workspace.cloud.databricks.com
   This may take a few minutes...

✅ Bundle deployed successfully!

================================================================================
DEPLOYMENT SUMMARY
================================================================================

📊 Dashboards deployed: 3
📁 Location: /Shared/Migrated_Dashboards
🔗 Workspace: https://your-target-workspace.cloud.databricks.com

✅ Next steps:
   1. Navigate to target workspace
   2. Go to /Shared/Migrated_Dashboards
   3. Verify dashboards load correctly
   4. Test data with new catalog/schema
   5. Verify permissions applied

================================================================================
VERIFYING DEPLOYMENT
================================================================================

🔍 Connecting to target workspace...

📋 Listing deployed dashboards...

✅ Found 3 deployed dashboard(s)

[Table showing deployed dashboards]

🎉 Migration complete!
```

### Step 5: Verify in Target Workspace

**Go to target workspace UI:**

1. Navigate to **Workspace** → **Shared** → **Migrated_Dashboards**
2. You should see your migrated dashboards

**For each dashboard:**

✅ **Check dashboard loads:**
- Click on dashboard
- Dashboard should open without errors

✅ **Check data loads with new catalog:**
- Click "Refresh" on dashboard
- Data should load successfully
- Check SQL queries use new catalog/schema (not old)

✅ **Check visualizations:**
- All charts/tables should render
- No "Table not found" errors

✅ **Check permissions:**
- Click three-dot menu → "Permissions"
- Verify users/groups from source have correct access levels
- Expected levels: CAN_VIEW, CAN_RUN, CAN_EDIT, CAN_MANAGE

✅ **Check warehouse connection:**
- Dashboard should be connected to configured warehouse
- Queries should execute successfully

---

## Part 2: Manual Approach (Optional)

If you want to test the manual approach (not using bundles):

### Step 1: Open Manual Notebook 01

**Path:** `notebooks/01_Export_and_Transform.ipynb`

**Where to run:** Source workspace

### Step 2: Run All Cells

Same as Bundle_01 - exports and transforms dashboards.

### Step 3: Manual Import Options

**Option A: Use Bundle (same as Part 1)**

**Option B: Import via Databricks UI**

1. Download transformed files from `/Volumes/.../transformed/`
2. In target workspace, go to **Workspace**
3. Click **Create** → **Dashboard**
4. Click **Import** → Upload `.lvdash.json` file
5. Select warehouse
6. Click **Import**

**Option C: Custom script (advanced)**

### Step 4: Apply Permissions

**Path:** `notebooks/02_Apply_Permissions.ipynb`

**Where to run:** Target workspace

**Configuration:**
- Ensure `permissions.dry_run = true` in config first (to preview)
- Run notebook to see what permissions would be applied
- Set `permissions.dry_run = false` in config
- Run again to actually apply

---

## Troubleshooting

### Error: "config.yaml not found"

**Fix:**
```bash
# Check file exists
ls config/

# If missing, copy from example
cp config/config_example.yaml config/config.yaml
# Then edit config/config.yaml with your values
```

### Error: "No dashboards found"

**Causes:**
1. Wrong catalog filter
2. No dashboards use that catalog
3. Connection issue

**Fix:**
```yaml
# In config.yaml, try explicit IDs:
dashboard_selection:
  method: "explicit_ids"
  explicit_ids:
    dashboard_ids:
      - "your_dashboard_id_here"
```

### Error: "Mapping CSV not found"

**Fix:**
```python
# Create the CSV file
csv_content = """old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
old_cat,old_schema,,new_cat,new_schema,,, """

dbutils.fs.put(
    "/Volumes/.../mappings/catalog_schema_mapping.csv",
    csv_content,
    overwrite=True
)
```

### Error: "Warehouse not found"

**Fix:**
```python
# List available warehouses
from databricks.sdk import WorkspaceClient
client = WorkspaceClient()
for w in client.warehouses.list():
    print(w.name, w.id)

# Update config.yaml with exact warehouse name (case-sensitive)
```

### Error: "Bundle validation failed"

**Fix:**
```bash
# Update Databricks CLI
%pip install -U databricks-cli

# Check bundle manually
cd /dbfs/Volumes/.../bundles/dashboard_migration
databricks bundle validate
```

### Error: "Transformation didn't work"

**Check:**
```python
# Read transformed file
content = dbutils.fs.head("/Volumes/.../transformed/dashboard_*.json", 2000)
print(content)

# Should show NEW catalog names, not old

# If old names still there:
# 1. Check CSV mapping is correct
# 2. Check transformation.enabled = true in config
# 3. Re-run Bundle_01
```

### Error: "Permission denied"

**Check:**
1. PAT tokens have correct permissions
2. Service principal has workspace access
3. Target warehouse is accessible
4. Parent folder has correct permissions

---

## Success Criteria

Your migration is successful when:

- [ ] All dashboards appear in target workspace
- [ ] Dashboards load without errors
- [ ] Data queries use NEW catalog/schema names
- [ ] All visualizations render correctly
- [ ] Permissions are applied (users/groups have access)
- [ ] Warehouse connection works
- [ ] No "Table not found" errors
- [ ] Historical dashboard functionality preserved

---

## Quick Reference

### File Locations

```
config/
└── config.yaml                          # Main configuration

helpers/
├── bundle_generator.py                  # Bundle generation
└── [other modules]                      # Reusable functions

Bundle/                                   # BUNDLE APPROACH
├── Bundle_03_Export_and_Transform.ipynb # Export & transform
└── Bundle_04_Generate_and_Deploy.ipynb  # Generate & deploy

notebooks/                                # MANUAL APPROACH
├── 01_Export_and_Transform.ipynb        # Export & transform
└── 02_Apply_Permissions.ipynb           # Apply ACLs

/Volumes/.../dashboard_migration/
├── mappings/
│   └── catalog_schema_mapping.csv       # Transformation rules
├── exported/
│   ├── dashboard_*.lvdash.json          # Original files
│   └── dashboard_*_permissions.json     # Permissions
├── transformed/
│   └── dashboard_*.lvdash.json          # Transformed files
└── bundles/
    └── dashboard_migration/             # Generated bundle
```

### Common Commands

```python
# List files
dbutils.fs.ls("/Volumes/.../dashboard_migration/exported")

# Read file
dbutils.fs.head("/Volumes/.../file.json", 1000)

# List dashboards
from databricks.sdk import WorkspaceClient
client = WorkspaceClient()
for dash in client.lakeview.list():
    print(dash.display_name, dash.dashboard_id)

# Check warehouse
for w in client.warehouses.list():
    print(w.name, w.id)
```

---

## Next Steps After Testing

Once testing is successful:

1. **Document your process** - Note any config changes needed
2. **Test with more dashboards** - Scale up gradually
3. **Automate** - Schedule bundle deployments if needed
4. **Version control** - Commit config and bundles to Git
5. **Production deployment** - Use tested config for prod migration

---

## Support

**Issues? Check:**
1. This testing guide troubleshooting section
2. `README_MODULAR.md` for architecture details
3. `Bundle/README.md` for bundle-specific info
4. Notebook cell outputs for specific errors

**Still stuck?**
- Review config values carefully
- Check PAT token permissions
- Verify volume paths exist
- Test with single dashboard first
