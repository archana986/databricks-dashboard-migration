# Quick Start: Modular Dashboard Migration

## What Changed?

You now have a **modular, configuration-driven workflow** that's much simpler to use:

### Before (5 notebooks, manual config in each)
```
00_Prerequisite_Generation.ipynb    ← Edit config here
01_Setup_and_Configuration.ipynb    ← Edit config here
02_Export_and_Transform.ipynb       ← Edit config here
03_Import_and_Migrate.ipynb         ← Edit config here (+ timeouts)
```

### After (2 notebooks, single config file)
```
config/config.yaml                  ← Edit config ONCE here
↓
notebooks/01_Export_and_Transform.ipynb  ← Just run (no editing needed)
↓
[Manual Import - Bundle or UI]
↓
notebooks/02_Apply_Permissions.ipynb     ← Just run (no editing needed)
```

## 3-Step Setup

### 1. Configure (One Time)

Edit `config/config.yaml`:

```yaml
source:
  workspace_url: "https://e2-demo-field-eng.cloud.databricks.com"
  auth:
    method: "pat"  # Options: "pat", "oauth", "service_principal"
    pat:
      secret_scope: "migration"
      secret_key: "source-token"
    
    # OAuth (RECOMMENDED by Databricks - uncomment to use)
    # method: "oauth"
    # Note: No secrets needed with OAuth

target:
  workspace_url: "https://fevm-akrishn-stable-classic-vv5y0k.cloud.databricks.com"
  auth:
    method: "pat"  # Options: "pat", "oauth", "service_principal"
    pat:
      secret_scope: "migration"
      secret_key: "target-token"
    
    # OAuth (RECOMMENDED by Databricks - uncomment to use)
    # method: "oauth"
    # Note: No secrets needed with OAuth

paths:
  volume_base: "/Volumes/archana_krish_fe_dsa/vizient_deep_dive/dashboard_migration"

dashboard_selection:
  method: "catalog_filter"
  catalog_filter:
    catalog: "archana_krish_fe_dsa"
```

**That's it for configuration!** You never need to edit the notebooks.

### 2. Run Notebooks

#### Step A: Export & Transform
Open `notebooks/01_Export_and_Transform.ipynb` and run all cells.

**What it does:**
- Loads your config automatically
- Discovers dashboards using your configured method
- Exports JSONs and permissions
- **Applies transformations correctly** (fixed regex logic)
- Saves to `/Volumes/.../transformed/`

#### Step B: Import Manually

**Option 1 (Recommended): Bundle Approach**
```
1. Run Bundle/Bundle_03_Export_and_Transform.ipynb
2. Run Bundle/Bundle_04_Generate_and_Deploy.ipynb
```
**No timeouts, batch deployment, most reliable**

**Option 2: Databricks UI**
```
1. Download transformed files
2. Import via Lakeview UI
```

#### Step C: Apply Permissions
Open `notebooks/02_Apply_Permissions.ipynb` and run all cells.

**First run (dry-run):**
- Set `permissions.dry_run = true` in config
- Preview what permissions would be applied

**Second run (apply):**
- Set `permissions.dry_run = false` in config
- Actually apply permissions

### 3. Verify

Check target workspace:
- Dashboards appear in `/Shared/Migrated_Dashboards`
- Data loads correctly (catalog/schema transformed)
- Permissions are applied

## Key Fixes

### 1. Transformation Fixed ✅

**Before (broken):**
```python
result = result.replace(old_ref, new_ref)  # Misses many cases
```

**After (fixed):**
```python
result = re.sub(rf'\b{re.escape(old_ref)}\b', new_ref, result)  # Regex with boundaries
```

**Result:** All catalog/schema/table references are now transformed correctly, including:
- `"catalog": "old_catalog"` → `"catalog": "new_catalog"`
- `old_catalog.old_schema.table` → `new_catalog.new_schema.table`
- `old_catalog.old_schema` → `new_catalog.new_schema`

### 2. No More Configuration Duplication ✅

**Before:** Edit 5 places
**After:** Edit 1 file (`config/config.yaml`)

### 3. No More Timeout Issues ✅

**Before:** SDK import with 5-minute timeouts
**After:** Manual import (Bundle or UI) - no timeouts

## What's in Each Folder

```
config/          ← Your configuration (edit here)
helpers/         ← Reusable Python functions (don't edit unless customizing)
notebooks/       ← Run these notebooks (no editing needed)
Bundle/          ← Alternative deployment method
_archive/        ← Old notebooks (for reference only)
```

## Environment Switching

### Development vs Production

**Create multiple config files:**
```
config/
├── config_dev.yaml
├── config_prod.yaml
└── config.yaml  ← Symlink or copy from dev/prod
```

**Switch environments:**
```python
# In notebook Cell 2:
config = load_config('../config/config_dev.yaml')
# OR
config = load_config('../config/config_prod.yaml')
```

## Troubleshooting

### Transformation Still Not Working?

Check your CSV mapping file:

```bash
# View in notebook:
dbutils.fs.head("/Volumes/.../mappings/catalog_schema_mapping.csv", 1000)
```

Verify format:
```csv
old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
your_old_catalog,your_old_schema,table1,your_new_catalog,your_new_schema,table1,,
```

### Can't Find Config File?

Error: `FileNotFoundError: config.yaml not found`

**Fix:**
```bash
# Check if file exists:
ls config/

# If not, copy from example:
cp config/config_example.yaml config/config.yaml
# Then edit config/config.yaml
```

### Module Import Error?

Error: `No module named 'helpers'`

**Fix:** Verify you're running notebooks from `notebooks/` folder and helpers exist:
```bash
ls helpers/
# Should show: __init__.py, auth.py, config_loader.py, etc.
```

## Next Steps

1. **Review your config:** `config/config.yaml`
2. **Update CSV mappings:** `/Volumes/.../mappings/catalog_schema_mapping.csv`
3. **Run NB01:** `notebooks/01_Export_and_Transform.ipynb`
4. **Import dashboards:** Use Bundle approach or UI
5. **Run NB02:** `notebooks/02_Apply_Permissions.ipynb`

## Comparison Chart

| Task | Old Way | New Way |
|------|---------|---------|
| **Configuration** | Edit 5 notebooks | Edit 1 YAML file |
| **Discovery** | Separate notebook | Integrated in NB01 |
| **Export** | NB02 | NB01 Cell 4 |
| **Transform** | NB02 (buggy) | NB01 Cell 5 (fixed) |
| **Import** | NB03 (timeouts) | Manual (no timeouts) |
| **Permissions** | NB03 | NB02 |
| **Total steps** | Run 5 notebooks | Edit config + Run 2 notebooks |
| **Code duplication** | High | None |
| **Maintainability** | Poor | Excellent |

## Success!

You now have a production-ready, modular dashboard migration workflow that's:
- Easier to configure
- Simpler to use
- More reliable
- Better maintained

**Start with:** `notebooks/01_Export_and_Transform.ipynb`
