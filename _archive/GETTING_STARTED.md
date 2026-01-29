# Getting Started - Quick Setup Guide

## What You Have

### 📓 Notebooks (4 total)

1. **`00_Prerequisite_Generation.ipynb`** ⭐ NEW!
   - Discover dashboards in your workspace
   - Identify top dashboards for testing
   - Generate custom CSV template with actual references
   - Get ready-to-use configuration

2. **`01_Setup_and_Configuration.ipynb`**
   - Install libraries
   - Configure authentication (OAuth, Service Principal, or PAT)
   - Create volume structure
   - Validate setup

3. **`02_Export_and_Transform.ipynb`**
   - Export dashboards from source
   - Apply CSV transformations
   - Prepare for import

4. **`03_Import_and_Migrate.ipynb`**
   - Import to target (Manual or Automated workflow)
   - Restore permissions
   - Generate reports

### 📚 Documentation

- **`COMPLETE_MIGRATION_GUIDE.md`** - Full guide (1,200+ lines)
- **`README.md`** - Quick overview
- **`SYNC_README.md`** - How to upload to Databricks
- **`GETTING_STARTED.md`** - This file

### 🔧 Sync Scripts

- **`sync_to_databricks.sh`** - Bash script to upload files
- **`sync_to_databricks.py`** - Python script to upload files

### 📊 Template

- **`catalog_schema_mapping_template.csv`** - CSV template

---

## Quick Start (5 Steps)

### Step 1: Upload Notebooks to Databricks

```bash
# Option A: Use bash script
./sync_to_databricks.sh

# Option B: Use Python script  
python sync_to_databricks.py

# Option C: Use dry run to test first
python sync_to_databricks.py --dry-run
```

**First time?** Configure your profile:
```bash
databricks configure --token --profile e2-demo-field-eng
```

### Step 2: Run Prerequisite Generation

1. Open `00_Prerequisite_Generation.ipynb` in Databricks
2. Update Cell 2 with your folder path:
   ```python
   SEARCH_FOLDER = "/Workspace/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient"
   TOP_N = 5  # Number of dashboards to test
   ```
3. Run all cells
4. Download generated CSV file
5. Copy configuration from Cell 8

### Step 3: Prepare CSV Mappings

1. Open downloaded CSV file
2. Replace `CHANGE_ME` with your target values:
   ```csv
   old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
   vizient_dev,bronze,claims,vizient_prod,gold,claims,dev_vol,prod_vol
   ```
3. Upload to volume (you'll create this in Step 4)

### Step 4: Run Setup Notebook

1. Open `01_Setup_and_Configuration.ipynb`
2. Configure Cell 3:
   ```python
   AUTH_METHOD = "oauth"  # Recommended (just run: az login)
   SOURCE_WORKSPACE_URL = "https://e2-demo-field-eng.cloud.databricks.com"
   ```
3. Configure Cell 4:
   ```python
   VOLUME_BASE_PATH = "/Volumes/catalog/schema/volume/dashboard_migration"
   ```
4. Run all cells
5. Verify all checks pass (Cell 8)

### Step 5: Run Migration

#### Option A: Test with 1 Dashboard First

**Notebook 2 (Export & Transform):**
```python
# Use just one dashboard for testing
DASHBOARD_IDS = ["dashboard_id_from_cell8"]
USE_FOLDER_PATH = False
```

**Notebook 3 (Import & Migrate):**
```python
# Enable dry run
DRY_RUN = True

# Choose workflow
# Run Cells 8-9 for automated workflow
```

#### Option B: Full Migration

Run Notebooks 2 and 3 with your full dashboard list from `00_Prerequisite_Generation.ipynb`.

---

## Workflow Diagram

```
┌─────────────────────────────────────┐
│ 00_Prerequisite_Generation          │  ⭐ NEW! Start here
│ • Discover dashboards               │
│ • Generate CSV template             │
│ • Get configuration                 │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 01_Setup_and_Configuration          │
│ • Install libraries                 │
│ • Configure auth                    │
│ • Create volume                     │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 02_Export_and_Transform              │
│ • Export dashboards                 │
│ • Apply transformations             │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 03_Import_and_Migrate                │
│ Choose:                             │
│ • Manual workflow (Cells 5-7)       │
│ • Automated workflow (Cells 8-9)    │
└─────────────────────────────────────┘
```

---

## Authentication Setup

### Option 1: OAuth (RECOMMENDED) ⭐

```bash
# Install Azure CLI
brew install azure-cli  # macOS
# or: https://docs.microsoft.com/cli/azure/install-azure-cli

# Login
az login

# That's it! Use in notebooks:
AUTH_METHOD = "oauth"
```

### Option 2: PAT Token

```bash
# Configure Databricks CLI with PAT
databricks configure --token --profile e2-demo-field-eng

# When prompted:
# Host: https://e2-demo-field-eng.cloud.databricks.com
# Token: [your PAT token from Databricks UI]

# Use in notebooks:
AUTH_METHOD = "pat"
```

### Option 3: Service Principal

```bash
# Store credentials in Databricks secrets
databricks secrets create-scope migration
databricks secrets put --scope migration --key source-sp-client-id
databricks secrets put --scope migration --key source-sp-secret
databricks secrets put --scope migration --key source-sp-tenant

# Use in notebooks:
AUTH_METHOD = "service_principal"
```

---

## Testing Your Setup

### 1. Test Connection

Run this in any Databricks notebook:

```python
from databricks.sdk import WorkspaceClient

client = WorkspaceClient()
user = client.current_user.me()

print(f"✅ Connected as: {user.user_name}")
print(f"   Workspace: {client.config.host}")
```

### 2. Test Volume Access

```python
# List volume contents
dbutils.fs.ls("/Volumes/catalog/schema/volume/")
```

### 3. Test Dashboard Discovery

Run `00_Prerequisite_Generation.ipynb` Cell 4 to discover dashboards.

---

## Troubleshooting

### Issue: "databricks-sdk not installed"

```python
%pip install databricks-sdk pandas --quiet
dbutils.library.restartPython()
```

### Issue: "Cannot access folder"

Check permissions:
```python
# Try listing parent folder
dbutils.fs.ls("/Workspace/Users/archana.krishnamurthy@databricks.com/")
```

### Issue: "No dashboards found"

1. Check `SEARCH_FOLDER` path is correct
2. Verify dashboards are `.lvdash.json` files
3. Try explicit dashboard IDs instead

### Issue: "Sync script fails"

```bash
# Check Databricks CLI is installed
databricks --version

# Test connection
databricks --profile e2-demo-field-eng workspace ls /

# Reconfigure if needed
databricks configure --token --profile e2-demo-field-eng
```

---

## File Locations

### After Sync

Your files will be at:
```
https://e2-demo-field-eng.cloud.databricks.com
Workspace → Users → archana.krishnamurthy@databricks.com → 
01-Customer-Projects → Vizient → Dashboard-Migration
```

### Volume Structure

After running Notebook 1, your volume will have:
```
/Volumes/[catalog]/[schema]/[volume]/dashboard_migration/
├── mappings/              # Your CSV file goes here
├── exported/              # Exported dashboards (auto-generated)
├── transformed/           # Transformed dashboards (auto-generated)
└── logs/                  # Migration reports (auto-generated)
```

---

## Quick Reference Commands

### Upload to Databricks
```bash
./sync_to_databricks.sh                    # Bash
python sync_to_databricks.py               # Python
python sync_to_databricks.py --dry-run     # Test first
```

### Databricks CLI
```bash
databricks configure --token --profile e2-demo-field-eng
databricks workspace ls /
databricks workspace import notebook.ipynb /Workspace/path
```

### Azure CLI (for OAuth)
```bash
az login
az account show
```

---

## Support

- **Sync issues**: See `SYNC_README.md`
- **Migration questions**: See `COMPLETE_MIGRATION_GUIDE.md`
- **Quick reference**: See `README.md`

---

## Summary

You now have:

✅ **4 notebooks** (including new prerequisite generation)  
✅ **2 sync scripts** (bash and Python)  
✅ **Comprehensive documentation** (1,200+ lines)  
✅ **Ready-to-use templates**  

**Start with**: Upload files → Run `00_Prerequisite_Generation.ipynb` → Follow the workflow!

---

**Questions?** All documentation is in the `COMPLETE_MIGRATION_GUIDE.md` file.
