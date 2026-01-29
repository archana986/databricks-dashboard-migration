# Quick Start Guide - Lakeview Dashboard Migration

## What You Got

A complete file-based migration solution for Databricks Lakeview dashboards with three files:

1. **`lakeview_migration_volume_based.ipynb`** - Main Databricks notebook (ready to import)
2. **`catalog_schema_mapping_template.csv`** - CSV template for mappings
3. **`README_Volume_Migration.md`** - Comprehensive documentation

## 5-Minute Setup

### 1. Import Notebook to Databricks
- Open Databricks workspace
- Navigate to Workspace → Import
- Upload `lakeview_migration_volume_based.ipynb`

### 2. Create Volume
```sql
CREATE VOLUME IF NOT EXISTS migration_cat.migration_schema.migration_vol;
```

### 3. Upload CSV Mapping
- Edit `catalog_schema_mapping_template.csv` with your mappings
- Upload to: `/Volumes/migration_cat/migration_schema/migration_vol/dashboard_migration/mappings/catalog_schema_mapping.csv`

### 4. Choose Authentication Method (RECOMMENDED: OAuth)
```python
# In Cell 1, choose auth method:
AUTH_METHOD = "oauth"  # RECOMMENDED

# For OAuth: Run 'az login' (easiest)
# For Service Principal: Store credentials in secrets
# For PAT: Store tokens in secrets
```

### 5. Configure Notebook (Cell 1)
```python
SOURCE_WORKSPACE_URL = "https://your-source.cloud.databricks.com"
TARGET_WORKSPACE_URL = "https://your-target.cloud.databricks.com"

# Choose dashboard selection:
DASHBOARD_IDS = ["dashboard_id_1", "dashboard_id_2"]  # Option 1
# OR
SOURCE_FOLDER_PATH = "/Workspace/Shared/Dashboards"   # Option 2
USE_FOLDER_PATH = True
```

### 6. Choose Workflow & Run

**Option A: Manual Import Workflow**
- Run Cells 1-7 (shared steps)
- Follow Cell 8 instructions to manually import
- Run Cell 9 to apply ACLs
- Run Cell 10 for report

**Option B: Automated Import Workflow**
- Run Cells 1-7 (shared steps)
- Run Cell 11 to auto-import
- Run Cell 12 for report

## Authentication Methods

| Method | Setup | Best For | Recommended? |
|--------|-------|----------|--------------|
| **OAuth** | `az login` | Most scenarios | **YES** |
| Service Principal | Store in secrets | Production/CI/CD | For automation |
| PAT Token | Store in secrets | Quick tests | No |

**Quick Setup for OAuth (RECOMMENDED):**
```bash
# Install Azure CLI and login
az login
# That's it! No secrets needed.
```

## CSV Mapping Example

```csv
old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
dev_cat,raw,customers,prod_cat,gold,customers,dev_vol,prod_vol
dev_cat,raw,orders,prod_cat,gold,orders,dev_vol,prod_vol
```

## What Happens During Migration

### Shared Steps (Both Workflows)
```
┌─────────────┐
│   EXPORT    │  Dashboards → Volume (as .lvdash.json)
├─────────────┤
│  TRANSFORM  │  Apply CSV mappings → catalog.schema.table
└─────────────┘
```

### Then Choose:

**Manual Workflow:**
```
┌─────────────┐
│ MANUAL UI   │  Import dashboards via Databricks UI
├─────────────┤
│ APPLY ACLS  │  Run Cell 9 to apply permissions
├─────────────┤
│   REPORT    │  Manual workflow report
└─────────────┘
```

**Automated Workflow:**
```
┌─────────────┐
│ AUTO IMPORT │  Import dashboards programmatically
├─────────────┤
│ AUTO ACLS   │  Apply permissions automatically
├─────────────┤
│   REPORT    │  Automated workflow report
└─────────────┘
```

## Volume Structure Created

```
/Volumes/migration_cat/migration_schema/migration_vol/dashboard_migration/
├── mappings/              # Your CSV file goes here
│   └── catalog_schema_mapping.csv
├── exported/              # Source dashboards (auto-generated)
│   ├── dashboard_*.lvdash.json
│   └── dashboard_*_permissions.json
├── transformed/           # Transformed dashboards (auto-generated)
│   └── dashboard_*.lvdash.json
└── logs/                  # Migration reports (auto-generated)
    └── migration_report_*.json
```

## Key Features

✅ **Multiple Auth Methods** - OAuth (recommended), Service Principal, or PAT  
✅ **Two Workflows** - Manual import or Automated import  
✅ **Batch Migration** - Migrate multiple dashboards at once  
✅ **CSV-Based Mapping** - Simple CSV file for catalog/schema/table mappings  
✅ **Volume Storage** - All artifacts stored in Databricks volumes  
✅ **Permissions Capture** - Best-effort permissions migration  
✅ **Detailed Reporting** - See exactly what succeeded/failed  
✅ **Dry Run Mode** - Test without importing  
✅ **Modular Cells** - Run step-by-step or all at once  

## Common Commands

### Test Volume Access
```python
dbutils.fs.ls("/Volumes/migration_cat/migration_schema/migration_vol/")
```

### View Mappings
Run the "View CSV Mappings" cell at the end of the notebook

### Verify Volume Structure
Run the "Verify Volume Structure" cell at the end of the notebook

### Enable Dry Run (Test Mode)
```python
# In Cell 1:
DRY_RUN = True
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "databricks-sdk not installed" | Run: `%pip install databricks-sdk` |
| "Volume not found" | Create volume with SQL command above |
| "No dashboards to export" | Check `DASHBOARD_IDS` or `SOURCE_FOLDER_PATH` |
| "CSV mapping not found" | Upload CSV to mappings folder |
| Permissions not applied | Set `SKIP_PERMISSIONS = True` |

## Next Steps

1. ✅ Read `README_Volume_Migration.md` for detailed documentation
2. ✅ Customize CSV mappings for your environment
3. ✅ Test with dry run mode first
4. ✅ Run migration on a small set of dashboards
5. ✅ Review migration report
6. ✅ Scale to full dashboard set

## Support Files

- **README_Volume_Migration.md** - Full documentation (25+ pages)
- **catalog_schema_mapping_template.csv** - CSV template with examples
- **Lakeview Dashboard Migration Playbook.txt** - Original reference playbook

## Need Help?

1. Check `README_Volume_Migration.md` → Troubleshooting section
2. Review cell outputs for error messages
3. Enable debug mode: `logging.basicConfig(level=logging.DEBUG)`
4. Check Databricks documentation for API updates

---

**Ready to migrate?** Import the notebook and follow the 5-minute setup above! 🚀
