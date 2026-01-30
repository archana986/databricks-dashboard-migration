# Databricks Dashboard Migration: Modular Architecture

## Overview

Modular, configuration-driven workflow for migrating Databricks Lakeview dashboards between workspaces with catalog/schema transformations and permissions preservation.

### Why Modular?

**Problems with original notebooks:**
- ❌ Configuration duplicated across 5 notebooks
- ❌ Helper functions copied in each notebook
- ❌ Manual editing required for each environment
- ❌ Difficult to test and maintain
- ❌ Transformation bugs (simple string replace)
- ❌ SDK timeout issues (5 minutes per dashboard)

**Benefits of modular approach:**
- ✅ Single configuration file (`config/config.yaml`)
- ✅ Reusable helper modules (`helpers/`)
- ✅ Clean, simplified notebooks (2 vs 5)
- ✅ Easy environment switching
- ✅ Testable, maintainable code
- ✅ Fixed transformation logic (regex-based)
- ✅ No timeout issues (manual workflow)

## Architecture

### Folder Structure

```
Customer-Work/Catalog Migration/
├── config/
│   ├── config.yaml                    # ← Edit this for your environment
│   └── config_example.yaml            # Template with documentation
│
├── helpers/                            # Reusable Python modules
│   ├── __init__.py
│   ├── config_loader.py               # Configuration management
│   ├── auth.py                        # Workspace authentication
│   ├── discovery.py                   # Dashboard discovery
│   ├── export.py                      # Dashboard export
│   ├── transform.py                   # Catalog/schema transformation
│   ├── permissions.py                 # ACL management
│   └── volume_utils.py                # Volume file operations
│
├── notebooks/                          # Simplified workflow (2 notebooks)
│   ├── 01_Export_and_Transform.ipynb  # Export + Transform
│   └── 02_Apply_Permissions.ipynb     # Apply ACLs after manual import
│
├── Bundle/                             # Alternative: Bundle-based deployment
│   ├── Bundle_03_Export_and_Transform.ipynb
│   ├── Bundle_04_Generate_and_Deploy.ipynb
│   └── README.md
│
└── _archive/                           # Old notebooks (deprecated)
    ├── 00_Prerequisite_Generation.ipynb
    ├── 01_Setup_and_Configuration.ipynb
    ├── 02_Export_and_Transform.ipynb
    ├── 03_Import_and_Migrate_DEPRECATED.ipynb
    ├── 03A_Apply_Permissions.ipynb
    └── README.md
```

## Quick Start

### Step 1: Configure

Edit `config/config.yaml`:

```yaml
source:
  workspace_url: "https://your-source-workspace.cloud.databricks.com"
  auth:
    method: "pat"
    pat:
      secret_scope: "migration"
      secret_key: "source-token"

target:
  workspace_url: "https://your-target-workspace.cloud.databricks.com"
  auth:
    method: "pat"
    pat:
      secret_scope: "migration"
      secret_key: "target-token"

paths:
  volume_base: "/Volumes/your_catalog/your_schema/dashboard_migration"

dashboard_selection:
  method: "catalog_filter"
  catalog_filter:
    catalog: "your_catalog_name"
```

### Step 2: Run Export & Transform

Open and run `notebooks/01_Export_and_Transform.ipynb`:

1. Loads config automatically
2. Discovers dashboards
3. Exports JSONs and permissions
4. Applies catalog/schema transformations
5. Saves to volume

**No manual configuration needed in the notebook!**

### Step 3: Import Dashboards Manually

Choose your preferred method:

**Option A: Bundle Approach (Recommended)**
```
1. Run Bundle/Bundle_03_Export_and_Transform.ipynb
2. Run Bundle/Bundle_04_Generate_and_Deploy.ipynb
```

**Option B: Databricks UI**
```
1. Download transformed files from /Volumes/.../transformed/
2. Import via Lakeview dashboard UI
```

**Option C: Custom Script**
```
Write your own import using transformed files
```

### Step 4: Apply Permissions

Open and run `notebooks/02_Apply_Permissions.ipynb`:

1. Loads config automatically
2. Connects to target workspace
3. Finds imported dashboards
4. Applies captured permissions

**Configuration:**
- First run: Keep `permissions.dry_run = true` to preview
- Second run: Set `permissions.dry_run = false` to apply

## Configuration Reference

### config/config.yaml Structure

```yaml
version: "1.0"

# Source & Target workspaces
source:
  workspace_url: "..."
  auth: {...}

target:
  workspace_url: "..."
  auth: {...}

# Volume paths
paths:
  volume_base: "/Volumes/..."
  exported: "exported"
  transformed: "transformed"
  mapping_csv: "mappings/catalog_schema_mapping.csv"
  target_parent_path: "/Shared/Migrated_Dashboards"

# Dashboard discovery
dashboard_selection:
  method: "catalog_filter"  # or "folder_path", "explicit_ids", "inventory_csv"
  catalog_filter:
    catalog: "your_catalog"
    use_system_tables: true

# Transformation
transformation:
  enabled: true
  mapping_csv: "mappings/catalog_schema_mapping.csv"

# Permissions
permissions:
  capture: true
  apply_after_import: true
  match_by: "name"  # or "id" or "both"
  dry_run: true

# Warehouse (for Bundle deployment)
warehouse:
  use_name_lookup: true
  warehouse_name: "Main Warehouse"

# Bundle options
bundle:
  name: "dashboard_migration"
  embed_credentials: true
  mode: "production"
```

### Authentication Methods

#### OAuth (RECOMMENDED by Databricks)
```yaml
auth:
  method: "oauth"
  # No additional configuration needed
  # Uses notebook's built-in authentication automatically
```

**Benefits:**
- ✅ No token expiration issues
- ✅ Better security (no secrets to manage)
- ✅ Automatic credential renewal
- ✅ Uses your identity

**Limitation:** Requires running in Databricks notebook (not external scripts)

#### PAT Token
```yaml
auth:
  method: "pat"
  pat:
    secret_scope: "migration"
    secret_key: "source-token"
```

**When to use:**
- Running from external scripts
- CI/CD pipelines
- Need explicit token control

#### Service Principal (For Automation)
```yaml
auth:
  method: "service_principal"
  service_principal:
    client_id_scope: "migration"
    client_id_key: "source-sp-client-id"
    client_secret_scope: "migration"
    client_secret_key: "source-sp-secret"
```

**When to use:**
- Automated deployments
- CI/CD pipelines
- Service-to-service authentication

### Discovery Methods

#### Method 1: Catalog Filter (Fast)
```yaml
dashboard_selection:
  method: "catalog_filter"
  catalog_filter:
    catalog: "my_catalog"
    use_system_tables: true  # Uses system.access.table_lineage for speed
```

#### Method 2: Folder Path
```yaml
dashboard_selection:
  method: "folder_path"
  folder_path:
    path: "/Workspace/Shared/Dashboards"
```

#### Method 3: Explicit IDs
```yaml
dashboard_selection:
  method: "explicit_ids"
  explicit_ids:
    dashboard_ids:
      - "dashboard_id_1"
      - "dashboard_id_2"
```

#### Method 4: Inventory CSV
```yaml
dashboard_selection:
  method: "inventory_csv"
  inventory_csv:
    csv_path: "dashboard_inventory/dashboard_inventory.csv"
```

## Helper Modules Reference

### config_loader.py

```python
from helpers import load_config, get_config, get_path

# Load configuration
config = load_config('../config/config.yaml')

# Get specific path
export_path = get_path('exported')  # Returns absolute path

# Get configuration value
config = get_config()
source_url = config['source']['workspace_url']
```

### auth.py

```python
from helpers import create_workspace_client

# Create source workspace client
source_client = create_workspace_client('source')

# Create target workspace client
target_client = create_workspace_client('target')
```

### discovery.py

```python
from helpers import discover_dashboards

# Discover using config method
dashboards = discover_dashboards(client)

# Override discovery method
dashboards = discover_dashboards(client, method='catalog_filter', catalog='my_catalog')
```

### export.py

```python
from helpers import export_dashboard

# Export dashboard
json_content, display_name, clean_name = export_dashboard(client, dashboard_id)
```

### transform.py

```python
from helpers import load_mapping_csv, transform_dashboard_json

# Load CSV mappings
mappings = load_mapping_csv('/Volumes/.../mappings/catalog_schema_mapping.csv')

# Transform dashboard JSON
transformed = transform_dashboard_json(original_json, mappings)
```

### permissions.py

```python
from helpers import get_dashboard_permissions, apply_dashboard_permissions

# Get permissions from source
perms = get_dashboard_permissions(source_client, dashboard_id)

# Apply to target
result = apply_dashboard_permissions(target_client, dashboard_id, perms, dry_run=True)
```

### volume_utils.py

```python
from helpers import read_volume_file, write_volume_file, list_volume_files

# Read file
content = read_volume_file('/Volumes/.../file.json')

# Write file
write_volume_file('/Volumes/.../file.json', content)

# List files
files = list_volume_files('/Volumes/.../directory/', '*.json')
```

## Workflow Comparison

| Aspect | Old (5 notebooks) | New (Modular) |
|--------|------------------|---------------|
| **Notebooks** | 00, 01, 02, 03, (04) | 01, 02 |
| **Configuration** | Duplicated in each | Single YAML file |
| **Helper functions** | Copied in each | Reusable modules |
| **Lines of code** | ~2000+ | ~600 |
| **Maintenance** | Difficult | Easy |
| **Testing** | Hard to unit test | Functions testable |
| **Environment switching** | Edit 5 notebooks | Edit 1 YAML file |
| **Transformation** | Buggy (simple replace) | Fixed (regex) |
| **Timeout issues** | Common (SDK import) | None (manual import) |

## Multi-Environment Setup

### Development, Staging, Production

Create separate config files:

```bash
config/
├── config_dev.yaml
├── config_staging.yaml
└── config_prod.yaml
```

Run notebooks with different configs:

```python
# In notebook
config = load_config('../config/config_dev.yaml')
# OR
config = load_config('../config/config_prod.yaml')
```

### Using Bundle Multi-Target

Alternatively, use Bundle approach with multiple targets:

```yaml
# In databricks.yml
targets:
  dev:
    workspace:
      host: "https://dev.cloud.databricks.com"
  prod:
    workspace:
      host: "https://prod.cloud.databricks.com"
```

```bash
databricks bundle deploy --target dev
databricks bundle deploy --target prod
```

## Troubleshooting

### Config Not Found

**Error:** `FileNotFoundError: config.yaml not found`

**Fix:**
1. Ensure `config/config.yaml` exists
2. Copy from `config/config_example.yaml` if needed
3. Check notebook is in `notebooks/` folder

### Module Import Error

**Error:** `ModuleNotFoundError: No module named 'helpers'`

**Fix:**
1. Ensure `helpers/` folder exists with all modules
2. Check `helpers/__init__.py` exists
3. Verify path in notebook: `sys.path.insert(0, '../helpers')`

### Transformation Not Working

**Error:** Old catalog/schema names still in transformed files

**Fix:**
1. Check CSV mapping file exists and has correct format
2. Verify mappings loaded: look at "Sample mappings" output in NB01 Cell 5
3. Check transformed file content to verify changes applied

### Permissions Not Matching

**Error:** "No matching permissions found"

**Fix:**
1. Try different match method: `match_by: "both"` in config
2. Check dashboard names match between source and target
3. Verify permissions files exist in `/Volumes/.../exported/`

### Directory Structure Issues

**Error:** Directories or files not found

**Fix:**
1. Ensure volume base path is correct in config
2. Run NB01 first to create directories
3. Check permissions on volume

## CSV Mapping File Format

Location: `/Volumes/.../mappings/catalog_schema_mapping.csv`

```csv
old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
dev_catalog,bronze_layer,customers,prod_catalog,gold_layer,customers,dev_files,prod_files
dev_catalog,bronze_layer,orders,prod_catalog,gold_layer,orders,dev_files,prod_files
staging_cat,raw_data,events,prod_catalog,curated_data,events,staging_vol,prod_vol
```

**Rules:**
- Header row required (exact column names)
- Leave columns empty if not used
- Transformations applied in order
- Supports fully-qualified and partial references

## Testing Workflow

### 1. Test with Sample Dashboard

```python
# In config.yaml
dashboard_selection:
  method: "explicit_ids"
  explicit_ids:
    dashboard_ids:
      - "test_dashboard_id"
```

### 2. Verify Each Step

**After NB01:**
```python
# Check exported file
dbutils.fs.head("/Volumes/.../exported/dashboard_*.lvdash.json", 1000)

# Check transformed file
dbutils.fs.head("/Volumes/.../transformed/dashboard_*.lvdash.json", 1000)

# Compare - should see new catalog/schema names in transformed
```

**After Manual Import:**
```python
# In target workspace
from databricks.sdk import WorkspaceClient
client = WorkspaceClient()
for dash in client.lakeview.list():
    print(dash.display_name, dash.dashboard_id, dash.parent_path)
```

**After NB02:**
```python
# Check permissions in target workspace UI
# Or use SDK:
perms = client.permissions.get("dashboards", dashboard_id)
for acl in perms.access_control_list:
    print(acl.user_name or acl.group_name, acl.all_permissions)
```

## Advanced Usage

### Extending Helper Modules

Add custom functions to existing modules or create new ones:

```python
# helpers/custom_logic.py
def my_custom_function():
    """Your custom logic here."""
    pass

# Update helpers/__init__.py
from .custom_logic import my_custom_function
__all__.append('my_custom_function')

# Use in notebooks
from helpers import my_custom_function
```

### Custom Discovery Logic

Override discovery in notebook:

```python
# In NB01, instead of:
dashboards = discover_dashboards(source_client)

# Use custom:
from helpers.discovery import _discover_via_sdk_list
dashboards = _discover_via_sdk_list(source_client, catalog="my_catalog")
```

### Batch Processing

Process multiple catalogs in one run:

```python
# In NB01, after loading config:
catalogs = ["catalog1", "catalog2", "catalog3"]

all_dashboards = []
for catalog in catalogs:
    dashboards = discover_dashboards(source_client, method='catalog_filter', catalog=catalog)
    all_dashboards.extend(dashboards)

# Continue with export/transform...
```

## Comparison: Modular vs Bundle vs Old

| Feature | Old Notebooks | Modular Notebooks | Bundle Approach |
|---------|--------------|------------------|-----------------|
| **Notebooks** | 5 | 2 | 2 |
| **Configuration** | In each notebook | Single YAML file | Single YAML file |
| **Code reuse** | None | Helper modules | Helper modules |
| **Deployment** | SDK (timeouts) | Manual (reliable) | CLI (most reliable) |
| **Version control** | Notebook files | Config + helpers + notebooks | Bundle structure |
| **Rollback** | Manual | Manual | Automatic |
| **CI/CD ready** | No | Partial | Yes |
| **Maintenance** | Hard | Easy | Easy |
| **Best for** | Legacy/deprecated | Manual workflows | Production/IaC |

### When to Use Each Approach

**Use Modular Notebooks (this) if:**
- ✅ You want simplest workflow
- ✅ You prefer manual control over import
- ✅ You need to customize logic frequently
- ✅ You want centralized configuration

**Use Bundle Approach if:**
- ✅ You want Infrastructure-as-Code
- ✅ You need version control integration
- ✅ You want automated deployment
- ✅ You need multi-environment support (dev/staging/prod)

**Avoid Old Notebooks because:**
- ❌ Configuration duplicated
- ❌ Transformation bugs
- ❌ Timeout issues
- ❌ Hard to maintain

## Migration from Old Notebooks

If you're currently using old notebooks:

### Option 1: Fresh Start (Recommended)

1. Create `config/config.yaml` from template
2. Run new `notebooks/01_Export_and_Transform.ipynb`
3. Import manually
4. Run new `notebooks/02_Apply_Permissions.ipynb`

### Option 2: Gradual Migration

1. Keep using old notebooks for in-progress migrations
2. Switch to modular notebooks for new migrations
3. Archive old notebooks when comfortable

## FAQ

### Q: Do I need to edit the notebooks for different environments?

**A:** No! Just edit `config/config.yaml`. The notebooks load configuration automatically.

### Q: Can I still use the Bundle approach?

**A:** Yes! The Bundle notebooks (`Bundle/`) are separate and still available. The modular notebooks are for manual workflows.

### Q: What if I need custom logic?

**A:** Extend the helper modules or add custom code in the notebooks. The modular structure makes this easier.

### Q: Will this work on serverless compute?

**A:** Yes! All code uses Unity Catalog Volumes and `dbutils.fs` APIs (serverless compatible).

### Q: How do I test changes to helper functions?

**A:** You can write unit tests for helper functions:

```python
# test_transform.py
from helpers.transform import _find_and_replace_references

def test_catalog_replacement():
    text = '"catalog": "old_catalog"'
    mappings = [{'old_catalog': 'old_catalog', 'new_catalog': 'new_catalog'}]
    result = _find_and_replace_references(text, mappings)
    assert 'new_catalog' in result
```

### Q: Can I use this with CI/CD pipelines?

**A:** Partially. For full CI/CD, use the Bundle approach. The modular notebooks are designed for interactive use.

### Q: What about the transformation issue I reported?

**A:** Fixed! The new `helpers/transform.py` uses regex with proper word boundaries. Test by running NB01 and checking transformed files.

### Q: Why are there so many files now?

**A:** Modularization trades file count for maintainability:
- **Before:** 5 notebooks, 2000+ duplicated lines
- **After:** 2 notebooks + 8 helper modules = better organized, no duplication

## Support

### Documentation
- This README: Overview and quick start
- `config/config_example.yaml`: Configuration template with comments
- `helpers/`: Each module has docstrings
- `_archive/README.md`: Info about old notebooks
- `Bundle/README.md`: Bundle approach documentation
- `MANUAL_WORKFLOW_GUIDE.md`: Manual workflow specifics

### Common Tasks

**Change source workspace:**
```yaml
# config/config.yaml
source:
  workspace_url: "https://new-workspace.cloud.databricks.com"
```

**Change discovery method:**
```yaml
# config/config.yaml
dashboard_selection:
  method: "folder_path"
  folder_path:
    path: "/Workspace/My/Dashboards"
```

**Enable/disable transformations:**
```yaml
# config/config.yaml
transformation:
  enabled: false  # Skip transformations
```

**Change permission matching:**
```yaml
# config/config.yaml
permissions:
  match_by: "both"  # Try ID first, then name
  dry_run: false    # Actually apply permissions
```

## Summary

The modular architecture provides:

1. **Single configuration file** - Edit once, use everywhere
2. **Reusable code** - Helper modules reduce duplication
3. **Cleaner notebooks** - High-level orchestration only
4. **Better testing** - Modular functions are testable
5. **Easier maintenance** - Changes in one place
6. **Fixed bugs** - Transformation logic works correctly
7. **No timeouts** - Manual workflow avoids SDK timeout issues

**Result:** Simpler, more reliable dashboard migration with better maintainability.
