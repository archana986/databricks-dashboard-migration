# 🚀 Dashboard Migration: Start Here

## ✅ Everything is Ready!

Your dashboard migration solution is now **fully modularized** and **ready to test**.

---

## 📁 Clean Structure

```
Customer-Work/Catalog Migration/
├── config/
│   ├── config.yaml              ← EDIT THIS FIRST
│   └── config_example.yaml      
│
├── helpers/                      ← Reusable modules (don't edit unless customizing)
│   ├── auth.py
│   ├── discovery.py
│   ├── export.py
│   ├── transform.py
│   ├── permissions.py
│   ├── bundle_generator.py      ← NEW: Bundle helpers
│   └── ...
│
├── Bundle/                       ← BUNDLE APPROACH (test this first)
│   ├── Bundle_01_Export_and_Transform.ipynb
│   ├── Bundle_02_Generate_and_Deploy.ipynb
│   └── README.md
│
├── notebooks/                    ← MANUAL APPROACH (alternative)
│   ├── 01_Export_and_Transform.ipynb
│   └── 02_Apply_Permissions.ipynb
│
├── TESTING_GUIDE.md             ← FOLLOW THIS TO TEST
├── README_MODULAR.md            ← Architecture details
└── QUICKSTART_MODULAR.md        ← Quick reference
```

---

## 🎯 What Was Done

### ✅ 1. Bundle Notebooks Refactored

**Before:** 1200+ lines of duplicated code
**After:** 200 lines using shared helpers

**Bundle_01:**
- Uses `helpers/discovery.py`, `helpers/export.py`, `helpers/transform.py`
- Loads config from `config.yaml`
- No configuration needed in notebook

**Bundle_02:**
- Uses `helpers/bundle_generator.py`
- Generates and deploys bundles
- Validates and verifies deployment

### ✅ 2. New Bundle Helper Module

**Created:** `helpers/bundle_generator.py`

Functions:
- `generate_bundle_structure()` - Creates bundle files
- `validate_bundle()` - Validates with CLI
- `deploy_bundle()` - Deploys to target
- `convert_permissions_for_bundle()` - Formats permissions

### ✅ 3. Single Configuration

**All notebooks** (Bundle and Manual) now use: `config/config.yaml`

**No more:**
- Editing configuration in each notebook
- Duplicating settings across files
- Managing 5 different configs

### ✅ 4. Comprehensive Testing Guide

**Created:** `TESTING_GUIDE.md`

Step-by-step instructions with:
- Prerequisites (secrets, volumes, CSV)
- Bundle approach testing (Part 1)
- Manual approach testing (Part 2)
- Troubleshooting for every error
- Success criteria checklist

### ✅ 5. Cleaned Up Files

**Archived** unnecessary files:
- Old documentation → `_archive/`
- Deprecated notebooks → `_archive/`
- Legacy scripts → `_archive/`

**Kept only what's needed:**
- 2 Bundle notebooks
- 2 Manual notebooks  
- 9 Helper modules
- 1 Config file
- 4 Documentation files

---

## 📤 First: Upload to Databricks

Before testing, you need to get your files into Databricks workspace.

**Choose ONE method:**

### Option 1: Sync Script (Quick - 2 minutes)

```bash
# Navigate to folder
cd "/Users/archana.krishnamurthy/Downloads/Career & Growth/Cursor/Customer-Work/Catalog Migration"

# Configure once
databricks configure --token --profile e2-demo-field-eng

# Sync all files
python sync_to_databricks.py
```

**See:** `SYNC_SCRIPT_README.md` for complete instructions

### Option 2: Databricks Repos (Better - 10 minutes setup)

Automatic syncing with version control.

**See:** `DATABRICKS_REPOS_SETUP.md` for step-by-step guide

---

## 🚀 Quick Start (5 Steps)

### Step 1: Configure (5 minutes)

Edit `config/config.yaml`:

```yaml
source:
  workspace_url: "https://YOUR-SOURCE.cloud.databricks.com"
  auth:
    method: "pat"  # You are using PAT
    pat:
      secret_scope: "migration"
      secret_key: "source-token"
    
    # OAuth (recommended by Databricks - uncomment to use)
    # method: "oauth"
    # Note: No secrets needed with OAuth

target:
  workspace_url: "https://YOUR-TARGET.cloud.databricks.com"
  auth:
    method: "pat"  # You are using PAT
    pat:
      secret_scope: "migration"
      secret_key: "target-token"
    
    # OAuth (recommended by Databricks - uncomment to use)
    # method: "oauth"
    # Note: No secrets needed with OAuth

paths:
  volume_base: "/Volumes/YOUR_CATALOG/YOUR_SCHEMA/dashboard_migration"

dashboard_selection:
  catalog_filter:
    catalog: "YOUR_SOURCE_CATALOG"

warehouse:
  warehouse_name: "YOUR_WAREHOUSE_NAME"
```

### Step 2: Create Prerequisites (5 minutes)

```python
# In Databricks notebook:

# 1. Create secrets (for PAT authentication you are using)
dbutils.secrets.createScope(scope="migration")
dbutils.secrets.put(scope="migration", key="source-token", string_value="dapi...")
dbutils.secrets.put(scope="migration", key="target-token", string_value="dapi...")

# Note: If using OAuth (recommended), skip step 1 - no secrets needed

# 2. Create volume
CREATE VOLUME IF NOT EXISTS your_catalog.your_schema.dashboard_migration;

# 3. Create CSV mapping
csv = """old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
old_cat,old_schema,,new_cat,new_schema,,, """
dbutils.fs.put("/Volumes/.../mappings/catalog_schema_mapping.csv", csv, True)
```

### Step 3: Run Bundle_01 (2 minutes)

Open `Bundle/Bundle_01_Export_and_Transform.ipynb`

Click **Run All**

Expected output: ✅ Exported and transformed X dashboards

### Step 4: Run Bundle_02 (3 minutes)

Open `Bundle/Bundle_02_Generate_and_Deploy.ipynb`

Click **Run All**

Expected output: ✅ Bundle deployed successfully!

### Step 5: Verify (2 minutes)

1. Go to target workspace
2. Navigate to `/Shared/Migrated_Dashboards`
3. Click on a dashboard
4. Verify data loads with **new catalog/schema**
5. Check permissions are applied

**Total time:** ~15-20 minutes

---

## 📚 Documentation

| File | Purpose | When to Read |
|------|---------|--------------|
| **TESTING_GUIDE.md** | Complete testing instructions | **Read first** - follow step-by-step |
| **Bundle/README.md** | Bundle approach details | After testing bundles |
| **README_MODULAR.md** | Full architecture documentation | For understanding design |
| **QUICKSTART_MODULAR.md** | Quick reference | For quick lookup |
| **config/config_example.yaml** | Configuration template | When setting up |

---

## 🔄 Two Approaches Available

### Bundle Approach (Recommended - Test First)

**Notebooks:**
1. `Bundle/Bundle_01_Export_and_Transform.ipynb`
2. `Bundle/Bundle_02_Generate_and_Deploy.ipynb`

**Benefits:**
- ✅ Automated deployment
- ✅ No timeouts
- ✅ Batch processing
- ✅ Infrastructure-as-Code

**Use when:**
- Production deployment
- Multiple dashboards
- Want automation
- Need reliability

### Manual Approach (Alternative)

**Notebooks:**
1. `notebooks/01_Export_and_Transform.ipynb`
2. Manual import (UI/Bundle/Custom)
3. `notebooks/02_Apply_Permissions.ipynb`

**Benefits:**
- ✅ Maximum flexibility
- ✅ Step-by-step control
- ✅ Multiple import methods
- ✅ Separate permission application

**Use when:**
- Testing/development
- Custom workflows
- Need manual control
- Specific requirements

**Both use same helpers and config!**

---

## ✨ Key Benefits

### 1. No Code Duplication

**Before:** Discovery/export/transform code in 4 notebooks
**After:** Reusable helpers used by all notebooks

### 2. Single Configuration

**Before:** Config in each of 4-5 notebooks
**After:** One `config.yaml` for everything

### 3. 83% Less Code

**Before:** ~1200 lines in Bundle notebooks
**After:** ~200 lines using helpers

### 4. Easier Maintenance

**Fix transformation logic?** Edit one file (`helpers/transform.py`)
**Change discovery?** Edit one file (`helpers/discovery.py`)
**Update config?** Edit one file (`config/config.yaml`)

### 5. Testable

**Helper modules can be unit tested**
```python
from helpers.transform import transform_dashboard_json
result = transform_dashboard_json(sample_json, mappings)
assert 'new_catalog' in result
```

---

## 🎯 What to Do Now

### Immediate (Today):

1. ✅ Read `TESTING_GUIDE.md`
2. ✅ Edit `config/config.yaml`
3. ✅ Create secrets and volume
4. ✅ Run Bundle_01
5. ✅ Run Bundle_02
6. ✅ Verify in target workspace

### Soon (This Week):

1. Test with more dashboards
2. Document any config changes needed
3. Review `README_MODULAR.md` for architecture
4. Consider version control for config

### Later (Production):

1. Create prod config file
2. Test full migration
3. Deploy to production
4. Monitor and verify

---

## 💡 Pro Tips

### Tip 1: Test with Single Dashboard First

```yaml
# In config.yaml
dashboard_selection:
  method: "explicit_ids"
  explicit_ids:
    dashboard_ids:
      - "your_test_dashboard_id"
```

### Tip 2: Use Dry-Run for Permissions

```yaml
# In config.yaml
permissions:
  dry_run: true  # Preview first
```

Then set to `false` to actually apply.

### Tip 3: Check Transformations Worked

```python
# After Bundle_01
content = dbutils.fs.head("/Volumes/.../transformed/dashboard_*.json", 1000)
print(content)
# Should show NEW catalog names
```

### Tip 4: Verify Mappings CSV

```python
dbutils.fs.head("/Volumes/.../mappings/catalog_schema_mapping.csv", 500)
# Check old_catalog → new_catalog mappings
```

---

## ❓ FAQ

### Q: Where do I start?

**A:** `TESTING_GUIDE.md` - follow step-by-step

### Q: Which approach should I use?

**A:** Bundle approach (test it first per guide)

### Q: Do I edit the notebooks?

**A:** No! Just edit `config/config.yaml`

### Q: What if something breaks?

**A:** Check troubleshooting in `TESTING_GUIDE.md`

### Q: Can I customize the logic?

**A:** Yes, edit helper modules in `helpers/`

### Q: Where are old notebooks?

**A:** Archived in `_archive/` folder

---

## 🎉 You're Ready!

Your migration solution is:
- ✅ Modularized
- ✅ Configured
- ✅ Documented
- ✅ Ready to test

**Next step:** Open `TESTING_GUIDE.md` and start testing!

---

## 📞 Need Help?

1. Check `TESTING_GUIDE.md` troubleshooting
2. Review `README_MODULAR.md` architecture
3. Check `Bundle/README.md` for bundle specifics
4. Look at cell outputs for specific errors

**Happy migrating! 🚀**
