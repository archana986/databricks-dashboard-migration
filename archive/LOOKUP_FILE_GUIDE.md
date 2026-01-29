# Catalog Lookup File Guide

## Available Lookup Files

### 1. **catalog_mapping_vizient_simple.csv** ✅ RECOMMENDED FOR 02_Migrate_Dashboard.ipynb
This is compatible with the current notebook and contains your specific migration mapping.

**Contents:**
```csv
old_catalog,old_schema,old_table,new_catalog,new_schema,new_table
archana_krish_fe_dsa,vizient_deep_dive,*,vizient_migration_edl_demo,edl_vizient_deep_dive,*
```

**Use this for:**
- Running `02_Migrate_Dashboard.ipynb`
- Simple catalog/schema migrations
- Quick testing

**Configuration in notebook:**
```python
LOOKUP_FILE_NAME = "catalog_mapping_vizient_simple.csv"
```

---

### 2. **catalog_mapping_vizient.csv** - Enhanced with Workspace Fields
Includes source and target workspace tracking for documentation.

**Contents:**
```csv
source_workspace,old_catalog,old_schema,old_table,target_workspace,new_catalog,new_schema,new_table,notes
e2-field-eng,archana_krish_fe_dsa,vizient_deep_dive,*,sytable-classic-jddaet,vizient_migration_edl_demo,edl_vizient_deep_dive,*,Wildcard mapping
```

**Note:** Current notebook doesn't use workspace columns, but they're useful for documentation and future enhancements.

---

### 3. **catalog_mapping_comprehensive_template.csv** - Full Template
Comprehensive template showing all mapping types and use cases.

---

## Your Migration Details

| Field | Value |
|-------|-------|
| **Source Workspace** | e2-field-eng (https://e2-demo-field-eng.cloud.databricks.com) |
| **Source Catalog** | archana_krish_fe_dsa |
| **Source Schema** | vizient_deep_dive |
| **Target Workspace** | sytable-classic-jddaet |
| **Target Catalog** | vizient_migration_edl_demo |
| **Target Schema** | edl_vizient_deep_dive |

---

## Quick Start Steps

### Step 1: Update notebook configuration to point to new target
```python
# In 02_Migrate_Dashboard.ipynb Configuration cell:

# Target Configuration
TARGET_WORKSPACE_URL = "https://sytable-classic-jddaet.cloud.databricks.net"  # UPDATE THIS
TARGET_CATALOG = "vizient_migration_edl_demo"
TARGET_SCHEMA = "edl_vizient_deep_dive"
TARGET_VOLUME = "migration_files"
TARGET_DASHBOARD_FILENAME = "dashboard_updated.lvdash.json"

# Lookup File Configuration
LOOKUP_FILE_NAME = "catalog_mapping_vizient_simple.csv"
```

### Step 2: Run the notebook
The notebook will:
1. ✅ Verify source dashboard JSON exists in volume
2. ✅ Extract all `archana_krish_fe_dsa.vizient_deep_dive.*` references
3. ✅ Load lookup file and cross-reference
4. ✅ Rewrite to `vizient_migration_edl_demo.edl_vizient_deep_dive.*`
5. ✅ Save updated JSON to target volume
6. ✅ Import dashboard to target workspace

---

## Mapping Types Explained

### Wildcard Mapping (*)
Maps entire schema - all tables automatically mapped.
```csv
old_catalog,old_schema,old_table,new_catalog,new_schema,new_table
archana_krish_fe_dsa,vizient_deep_dive,*,vizient_migration_edl_demo,edl_vizient_deep_dive,*
```

**Result:**
- `archana_krish_fe_dsa.vizient_deep_dive.category_insights_delta` → `vizient_migration_edl_demo.edl_vizient_deep_dive.category_insights_delta`
- `archana_krish_fe_dsa.vizient_deep_dive.any_other_table` → `vizient_migration_edl_demo.edl_vizient_deep_dive.any_other_table`

### Exact Table Mapping
Maps specific table with exact name.
```csv
old_catalog,old_schema,old_table,new_catalog,new_schema,new_table
archana_krish_fe_dsa,vizient_deep_dive,category_insights_delta,vizient_migration_edl_demo,edl_vizient_deep_dive,category_insights_delta
```

**Result:**
- Only `category_insights_delta` is mapped
- Other tables are not affected

### Renamed Table Mapping
Maps table to different name.
```csv
old_catalog,old_schema,old_table,new_catalog,new_schema,new_table
archana_krish_fe_dsa,vizient_deep_dive,old_name,vizient_migration_edl_demo,edl_vizient_deep_dive,new_name
```

---

## Troubleshooting

### Issue: "Lookup file not found"
**Solution:** Ensure the CSV file is in the same directory as `02_Migrate_Dashboard.ipynb` or provide full path:
```python
LOOKUP_FILE_PATH = "/Workspace/Users/your.email@databricks.com/path/to/catalog_mapping_vizient_simple.csv"
```

### Issue: "No references matched"
**Solution:** Check that catalog/schema names in lookup file exactly match those in your dashboard JSON.

### Issue: "Some references unmatched"
**Solution:** Add specific mappings for unmatched tables or use wildcard mapping (`*`).

---

## Files Summary

| File | Purpose | Compatible with Notebook |
|------|---------|-------------------------|
| `catalog_mapping_vizient_simple.csv` | Your specific migration (simple format) | ✅ Yes |
| `catalog_mapping_vizient.csv` | Your migration with workspace fields | ⚠️ Partial (extra columns ignored) |
| `catalog_mapping_comprehensive_template.csv` | Full template with examples | ⚠️ Partial (extra columns ignored) |
| `catalog_mapping.csv` | Original example | ✅ Yes |
| `catalog_mapping_template.csv` | General template | ✅ Yes |

---

## Next Steps

1. ✅ Use `catalog_mapping_vizient_simple.csv` with your notebook
2. ✅ Update notebook configuration with target workspace URL
3. ✅ Ensure target workspace credentials are configured
4. ✅ Run the notebook step by step
5. ✅ Verify dashboard in target workspace

**Questions?** Check the main `DASHBOARD_MIGRATION_README.md` for detailed migration instructions.
