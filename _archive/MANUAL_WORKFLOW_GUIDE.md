# Manual Import Workflow Guide

## Overview

The manual import workflow has been implemented to address timeout issues with the automated SDK import approach. This guide explains the changes and how to use the new workflow.

## What Changed

### ✅ Fixed Issues

1. **Transformation Logic Fixed** (Notebook 02)
   - Replaced simple `.replace()` with regex-based pattern matching
   - Now handles all dashboard JSON formats correctly:
     - Fully-qualified references: `catalog.schema.table`
     - Schema references: `catalog.schema`
     - Catalog-only references in JSON fields: `"catalog": "old_catalog"`
     - Volume paths
   - Uses word boundaries to avoid partial matches
   - Properly escapes special characters

2. **New Permissions Notebook** (Notebook 03A)
   - Standalone notebook for applying permissions after manual import
   - Works regardless of how dashboards were imported (UI, Bundle, SDK)
   - Supports dry-run mode for testing
   - Matches dashboards by name, ID, or both

3. **Deprecated SDK Import** (Notebook 03)
   - Renamed to `03_Import_and_Migrate_DEPRECATED.ipynb`
   - Added clear deprecation warning
   - Documented known issues (5-minute timeouts)
   - Provided alternatives

### 📝 Updated Documentation

- Notebook 02 header now emphasizes manual workflow
- Transform summary guides users to next steps
- Clear instructions for Bundle approach or manual UI import

## New Workflow

### Step 1: Export & Transform (Notebook 02)

```
Run: 02_Export_and_Transform.ipynb
```

**What it does:**
- Exports dashboards from source workspace
- Captures permissions
- Applies catalog/schema transformations using CSV lookup
- Saves transformed files to `/Volumes/.../transformed/`

**Output:**
- Transformed dashboard JSONs
- Permission JSON files

### Step 2: Manual Import (Your Choice)

**Option A: Bundle Approach (Recommended)**
```
1. Run: Bundle/Bundle_01_Export_and_Transform.ipynb
2. Run: Bundle/Bundle_02_Generate_and_Deploy.ipynb
```

Benefits:
- No timeouts
- Batch deployment
- Infrastructure-as-Code
- Built-in retry logic

**Option B: Databricks UI**
```
1. Download transformed files from /Volumes/.../transformed/
2. Import via Lakeview dashboard import feature in target workspace
```

**Option C: Custom SDK Script**
```
Write your own import script using transformed files
```

### Step 3: Apply Permissions (Notebook 03A)

```
Run: 03A_Apply_Permissions.ipynb
```

**What it does:**
- Connects to target workspace
- Finds imported dashboards in specified location
- Matches with captured permissions by name/ID
- Applies ACLs to each dashboard

**Configuration:**
- Set `DRY_RUN = True` for testing (recommended first)
- Set `DRY_RUN = False` to actually apply permissions
- Configure `MATCH_BY` to "name", "id", or "both"

## Key Benefits

### vs Automated SDK Import (Old Notebook 03)

| Feature | Old SDK Import | New Manual Workflow |
|---------|---------------|-------------------|
| **Timeouts** | ❌ 5-min per dashboard | ✅ No timeouts |
| **Large dashboards** | ❌ Often fails | ✅ Works reliably |
| **Retry logic** | ❌ None | ✅ Bundle has built-in retry |
| **Flexibility** | ❌ SDK only | ✅ Multiple import methods |
| **Permissions** | ❌ Coupled with import | ✅ Separate, reusable |

## Configuration Required

### Notebook 02 (Export & Transform)

```python
# Source workspace
SOURCE_WORKSPACE_URL = "https://your-source-workspace.cloud.databricks.com"
SOURCE_PAT_TOKEN = dbutils.secrets.get(scope="migration", key="source-token")

# Volume paths
VOLUME_BASE = "/Volumes/your_catalog/your_schema/dashboard_migration"
MAPPING_CSV_PATH = f"{VOLUME_BASE}/mappings/catalog_schema_mapping.csv"

# Dashboard selection
CATALOG_FILTER = "your_catalog"  # or use other selection methods
```

### Notebook 03A (Apply Permissions)

```python
# Target workspace
TARGET_WORKSPACE_URL = "https://your-target-workspace.cloud.databricks.com"
TARGET_PAT_TOKEN = dbutils.secrets.get(scope="migration", key="target-token")

# Target location
TARGET_PARENT_PATH = "/Shared/Migrated_Dashboards"

# Options
DRY_RUN = True  # Set to False to apply
MATCH_BY = "name"  # or "id" or "both"
```

## Troubleshooting

### Transformations Not Working

**Problem:** Dashboard JSONs still have old catalog/schema names after transformation.

**Solution:** The transformation logic has been fixed with regex pattern matching. Re-run Notebook 02 Cell 6 (Transform) to apply the improved logic.

**Verify:** Check transformed files in `/Volumes/.../transformed/` - they should show new catalog/schema names.

### Permissions Not Applying

**Problem:** Dashboards imported but no permissions applied.

**Common causes:**
1. Dashboard location mismatch - check `TARGET_PARENT_PATH`
2. Permission files not found - verify `EXPORT_PATH` is correct
3. Name/ID matching issue - try `MATCH_BY = "both"`
4. Dry-run mode enabled - set `DRY_RUN = False`

**Debug steps:**
1. Run Notebook 03A Cell 5 to see discovered dashboards and permissions
2. Check if names match between source and target
3. Use dry-run mode to preview what would be applied

### Dashboards Not Found in Target

**Problem:** Notebook 03A says "No dashboards found".

**Solution:**
1. Verify dashboards were imported to target workspace
2. Check `TARGET_PARENT_PATH` matches where you imported them
3. Try searching all dashboards by setting `TARGET_PARENT_PATH = "/"`

## Testing Checklist

After implementing:

- [ ] Run Notebook 02 with sample dashboard
- [ ] Verify transformed JSON has new catalog/schema names
  ```bash
  # Check file content
  dbutils.fs.head("/Volumes/.../transformed/dashboard_*.lvdash.json", 1000)
  ```
- [ ] Manually import transformed dashboard to target workspace
- [ ] Run Notebook 03A in dry-run mode (`DRY_RUN = True`)
- [ ] Verify permissions match expectations in output
- [ ] Run Notebook 03A with `DRY_RUN = False`
- [ ] Verify permissions applied correctly in target workspace UI

## Files Changed

### Modified
- `02_Export_and_Transform.ipynb`
  - Fixed `find_and_replace_references()` function
  - Updated header markdown
  - Updated transform summary

### Created
- `03A_Apply_Permissions.ipynb`
  - New standalone permissions notebook
  - Dry-run support
  - Flexible matching (name/ID/both)

### Archived
- `03_Import_and_Migrate.ipynb` → `03_Import_and_Migrate_DEPRECATED.ipynb`
  - Added deprecation warning
  - Documented alternatives

## Next Steps

1. **Test the workflow** with a sample dashboard
2. **Configure CSV mapping** for your catalog/schema transformations
3. **Run Notebook 02** to export and transform
4. **Import manually** using Bundle approach or UI
5. **Run Notebook 03A** to apply permissions

## Support

If you encounter issues:

1. Check the transformation output in Notebook 02 Cell 6
2. Verify CSV mapping file format
3. Use dry-run mode in Notebook 03A to preview changes
4. Check Bundle approach README for timeout-free deployment

## Summary

The manual workflow provides:
- ✅ Reliable transformation with regex pattern matching
- ✅ Flexibility in import methods (Bundle, UI, custom)
- ✅ Separate, reusable permissions application
- ✅ No timeout issues
- ✅ Better error handling and debugging

**Recommended approach:** Use Bundle workflow for deployment (Bundle_01 + Bundle_02) + Notebook 03A for permissions.
