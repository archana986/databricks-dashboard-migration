# Your First Steps - Execute This Now

## Step 1: Upload Files to Databricks (2 Minutes)

**Open your terminal and run these commands:**

```bash
# Navigate to the migration folder
cd "/Users/archana.krishnamurthy/Downloads/Career & Growth/Cursor/Customer-Work/Catalog Migration"

# Configure Databricks CLI (first time only)
databricks configure --token --profile e2-demo-field-eng
```

**When prompted:**
- **Databricks Host:** `https://e2-demo-field-eng.cloud.databricks.com`
- **Token:** Your PAT token from Databricks User Settings → Access Tokens

**Then sync all files:**
```bash
python sync_to_databricks.py
```

**Wait ~30 seconds for upload to complete.**

✅ **Verify:** Go to https://e2-demo-field-eng.cloud.databricks.com and check:
```
Workspace → Users → archana.krishnamurthy@databricks.com → 
01-Customer-Projects → Vizient → Dashboard-Migration
```

You should see: `config/`, `helpers/`, `Bundle/`, `notebooks/` folders

---

## Step 2: Edit Configuration (5 Minutes)

**In Databricks workspace, edit:** `config/config.yaml`

**Update these values:**

```yaml
source:
  workspace_url: "https://e2-demo-field-eng.cloud.databricks.com"  # ← Your source workspace
  auth:
    method: "pat"
    pat:
      secret_scope: "migration"
      secret_key: "source-token"  # ← Your secret key name

target:
  workspace_url: "https://your-target-workspace.cloud.databricks.com"  # ← Your target workspace
  auth:
    method: "pat"
    pat:
      secret_scope: "migration"
      secret_key: "target-token"  # ← Your secret key name

paths:
  volume_base: "/Volumes/archana_krish_fe_dsa/vizient_deep_dive/dashboard_migration"  # ← Your volume

dashboard_selection:
  catalog_filter:
    catalog: "archana_krish_fe_dsa"  # ← Catalog with dashboards to migrate

warehouse:
  warehouse_name: "Main Warehouse"  # ← Your target warehouse name
```

**Save the file in Databricks.**

---

## Step 3: Create Secrets (3 Minutes)

**In a Databricks notebook, run:**

```python
# Create secrets scope
dbutils.secrets.createScope(scope="migration")

# Add source workspace PAT token
dbutils.secrets.put(scope="migration", key="source-token", string_value="dapi...")

# Add target workspace PAT token
dbutils.secrets.put(scope="migration", key="target-token", string_value="dapi...")
```

---

## Step 4: Create Volume (2 Minutes)

**In a Databricks SQL cell or notebook, run:**

```sql
-- Create catalog if needed
CREATE CATALOG IF NOT EXISTS archana_krish_fe_dsa;

-- Create schema if needed
CREATE SCHEMA IF NOT EXISTS archana_krish_fe_dsa.vizient_deep_dive;

-- Create volume
CREATE VOLUME IF NOT EXISTS archana_krish_fe_dsa.vizient_deep_dive.dashboard_migration;
```

---

## Step 5: Create CSV Mapping (3 Minutes)

**In a Databricks notebook, run:**

```python
# Create mappings directory
dbutils.fs.mkdirs("/Volumes/archana_krish_fe_dsa/vizient_deep_dive/dashboard_migration/mappings")

# Create CSV mapping file (UPDATE WITH YOUR ACTUAL CATALOG/SCHEMA NAMES)
csv_content = """old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
archana_krish_fe_dsa,old_schema,customers,new_catalog,new_schema,customers,,
archana_krish_fe_dsa,old_schema,orders,new_catalog,new_schema,orders,,"""

# Save to volume
dbutils.fs.put(
    "/Volumes/archana_krish_fe_dsa/vizient_deep_dive/dashboard_migration/mappings/catalog_schema_mapping.csv",
    csv_content,
    overwrite=True
)

# Verify it was created
display(dbutils.fs.head("/Volumes/archana_krish_fe_dsa/vizient_deep_dive/dashboard_migration/mappings/catalog_schema_mapping.csv", 500))
```

**Important:** Update the CSV with your **actual old and new catalog/schema names!**

---

## Step 6: Run Bundle_01 (2 Minutes)

**In Databricks, navigate to:**
```
Workspace → Users → archana.krishnamurthy@databricks.com → 
01-Customer-Projects → Vizient → Dashboard-Migration → 
Bundle → Bundle_01_Export_and_Transform.ipynb
```

**Click "Run All"**

**Expected:** Dashboards discovered, exported, and transformed

---

## Step 7: Run Bundle_02 (3 Minutes)

**Open:** `Bundle/Bundle_02_Generate_and_Deploy.ipynb`

**Click "Run All"**

**Expected:** Bundle generated, validated, and deployed to target workspace

---

## Step 8: Verify (2 Minutes)

**Go to target workspace and check:**
- Dashboards visible at `/Shared/Migrated_Dashboards`
- Dashboards load correctly
- Data uses new catalog/schema
- Permissions are applied

**If all checks pass:** ✅ Migration successful!

---

## Complete Timeline

| Step | Time | What You Do |
|------|------|-------------|
| 0. Upload files | 2 min | Run sync script |
| 1. Edit config | 5 min | Update config.yaml |
| 2. Create secrets | 3 min | Run dbutils commands |
| 3. Create volume | 2 min | Run SQL |
| 4. Create CSV | 3 min | Run Python in notebook |
| 5. Run Bundle_01 | 2 min | Click "Run All" |
| 6. Run Bundle_02 | 3 min | Click "Run All" |
| 7. Verify | 2 min | Check target workspace |
| **TOTAL** | **~20 min** | **First migration complete!** |

---

## After First Success

### To Migrate More Dashboards:

**Just update config and re-run:**

```yaml
# In config.yaml, change catalog filter or add explicit IDs
dashboard_selection:
  method: "explicit_ids"
  explicit_ids:
    dashboard_ids:
      - "dashboard_id_1"
      - "dashboard_id_2"
      - "dashboard_id_3"
```

Then run Bundle_01 → Bundle_02 again. That's it!

### To Update Code:

**Option A: Using Sync Script**
```bash
# Edit files locally
# Then re-sync:
cd "/Users/archana.krishnamurthy/Downloads/Career & Growth/Cursor/Customer-Work/Catalog Migration"
python sync_to_databricks.py
```

**Option B: Using Databricks Repos (better)**
```bash
# Edit files locally
git add .
git commit -m "Updated configuration"
git push
# Auto-syncs to Databricks!
```

---

## If Something Goes Wrong

**Check these in order:**

1. **Sync failed?**
   - See: `SYNC_SCRIPT_README.md` troubleshooting

2. **Config not loading?**
   - Verify `config/config.yaml` exists in Databricks
   - Check file path in notebook: `../config/config.yaml`

3. **Helpers not found?**
   - Verify `helpers/` folder exists in Databricks
   - Check: `sys.path.insert(0, '../helpers')` in notebook

4. **Dashboards not found?**
   - Check catalog name in config
   - Try explicit IDs instead of catalog filter

5. **Transformation not working?**
   - Check CSV mapping file exists
   - Verify old/new catalog names are correct

6. **Other issues?**
   - See: `TESTING_GUIDE.md` troubleshooting section

---

## Documentation Quick Reference

| File | When to Use |
|------|-------------|
| **FIRST_STEPS.md** | ← YOU ARE HERE - Do this now |
| **SYNC_SCRIPT_README.md** | Sync script details |
| **DATABRICKS_REPOS_SETUP.md** | Repos setup (later) |
| **TESTING_GUIDE.md** | Complete testing instructions |
| **START_HERE.md** | Overview of solution |
| **Bundle/README.md** | Bundle approach details |

---

## Ready? Execute These Commands Now:

```bash
# 1. Configure Databricks CLI
databricks configure --token --profile e2-demo-field-eng

# 2. Sync files
cd "/Users/archana.krishnamurthy/Downloads/Career & Growth/Cursor/Customer-Work/Catalog Migration"
python sync_to_databricks.py

# 3. Open Databricks and follow TESTING_GUIDE.md from Step 1
```

**You're ready to start testing! 🚀**
