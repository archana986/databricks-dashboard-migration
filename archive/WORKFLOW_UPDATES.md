# Dashboard Migration Workflow - Updates

## What Changed

Based on your feedback, the notebook has been updated to:

1. ✅ **Make permissions migration REQUIRED** (not optional)
2. ✅ **Support manual dashboard import** (not just programmatic)
3. ✅ **Clarify what OAuth/PAT is needed for**

---

## New Workflow

### Configuration (Cell 2)

```python
# Import Method: Choose how to import dashboard
IMPORT_METHOD = "manual"  # or "programmatic"

# Permissions (REQUIRED)
SOURCE_DASHBOARD_ID = "01f0fb1aabc91dc88f09650d5c307b00"  # ⚠️ MUST SET THIS

# User/Group Mapping (if names differ)
USER_GROUP_MAPPING = {
    # "old_user@company.com": "new_user@company.com"
}
```

---

## Step-by-Step Flow

### Steps 1-6: Automatic (No Manual Intervention)

**✅ Step 1:** Verify Source Location
- Reads dashboard JSON from source volume
- **Uses: SOURCE_PAT_TOKEN (or OAuth)**

**✅ Step 2:** Extract References
- Lists all catalog.schema.table references
- **Uses: No auth needed (parses JSON)**

**✅ Step 3:** Load Lookup File
- Cross-references with catalog_mapping.csv
- **Uses: No auth needed (reads local file)**

**✅ Step 4:** Rewrite References
- Updates all catalog/schema names
- **Uses: No auth needed (modifies JSON)**

**✅ Step 5:** Save to Target Volume
- Writes updated JSON to target workspace
- **Uses: TARGET_PAT_TOKEN (or OAuth)**

**✅ Step 6:** Validate Queries (Optional)
- Tests SQL against target warehouse
- **Uses: TARGET_PAT_TOKEN (or OAuth)**

---

### Step 7: Import Dashboard (CHOOSE YOUR METHOD)

#### Option A: Manual Import (RECOMMENDED)

```python
IMPORT_METHOD = "manual"
```

**What the notebook does:**
- Displays instructions
- Tells you where to find the updated JSON file
- Pauses and waits for you

**What YOU do:**
1. Navigate to target workspace UI
2. Go to SQL > Dashboards
3. Click Create > Import dashboard
4. Upload file from target volume path (shown in notebook)
5. Select SQL warehouse
6. Click Import
7. Copy dashboard ID from URL
8. Go to **Step 7a** in notebook
9. Set: `target_dashboard_id = "your-copied-id"`

**Authentication:** Uses your browser login (no PAT/OAuth needed)

---

#### Option B: Programmatic Import (AUTOMATED)

```python
IMPORT_METHOD = "programmatic"
TARGET_WAREHOUSE_ID = "abc123def456"  # Required
```

**What happens:**
- Notebook automatically creates dashboard via API
- Returns dashboard ID
- No manual steps needed

**Authentication:** Uses TARGET_PAT_TOKEN (or OAuth)

---

### Step 7.5: Migrate Permissions (REQUIRED)

**What happens:**
1. Reads permissions from source dashboard
   - **Uses: SOURCE_PAT_TOKEN** to get ACLs

2. Maps users/groups (if configured)
   - No auth needed

3. Saves backup to `dashboard_permissions_backup.json`
   - No auth needed

4. Applies permissions to target dashboard
   - **Uses: TARGET_PAT_TOKEN** to set ACLs

**Prerequisites:**
- `SOURCE_DASHBOARD_ID` must be set in configuration
- `target_dashboard_id` must be set (from Step 7 or 7a)

**Result:**
- Permissions automatically migrated
- Backup file created for audit
- Manual fallback instructions if it fails

---

### Step 8: Publish Dashboard (OPTIONAL)

#### If IMPORT_METHOD = "manual":
- Notebook says "Not applicable for manual import"
- You can publish manually in UI if needed

#### If IMPORT_METHOD = "programmatic":
```python
PUBLISH_DASHBOARD = True  # or False
```
- Notebook publishes via API if enabled
- **Uses: TARGET_PAT_TOKEN (or OAuth)**

---

## What OAuth/PAT Is Used For

### Required Operations (Always Need Auth):

1. **Read source volume**
   - SOURCE_PAT_TOKEN
   - Access: `/Volumes/source_catalog/source_schema/source_volume/dashboard.lvdash.json`

2. **Write target volume**
   - TARGET_PAT_TOKEN
   - Access: `/Volumes/target_catalog/target_schema/target_volume/dashboard_updated.lvdash.json`

3. **Get source dashboard permissions**
   - SOURCE_PAT_TOKEN
   - API: `GET /api/2.0/permissions/dashboards/{source_dashboard_id}`

4. **Set target dashboard permissions**
   - TARGET_PAT_TOKEN
   - API: `PUT /api/2.0/permissions/dashboards/{target_dashboard_id}`

### Optional Operations (Depends on Configuration):

5. **Validate queries** (if VALIDATE_QUERIES=True)
   - TARGET_PAT_TOKEN
   - API: Statement Execution API

6. **Import dashboard programmatically** (if IMPORT_METHOD="programmatic")
   - TARGET_PAT_TOKEN
   - API: `POST /api/2.0/lakeview/dashboards`

7. **Publish dashboard** (if IMPORT_METHOD="programmatic" and PUBLISH_DASHBOARD=True)
   - TARGET_PAT_TOKEN
   - API: `POST /api/2.0/lakeview/dashboards/{id}/publish`

---

## Comparison: Manual vs Programmatic

| Aspect | Manual Import | Programmatic Import |
|--------|--------------|---------------------|
| **Configuration** | `IMPORT_METHOD = "manual"` | `IMPORT_METHOD = "programmatic"` |
| **Warehouse ID** | Not needed | Required |
| **Import Step** | You do it in UI | Notebook does it |
| **Dashboard ID** | You copy from URL | Auto-returned |
| **Permissions** | Auto-migrated ✅ | Auto-migrated ✅ |
| **Publish** | Do in UI | Optional auto |
| **Auth Needed** | Less (no import API) | More (includes import API) |
| **Best For** | First-time users, testing | Automation, batch migrations |

---

## Updated Configuration Summary

### For Manual Import (Recommended):

```python
# ============================================================================
# CONFIGURATION
# ============================================================================

# Workspace Configuration
SOURCE_WORKSPACE_URL = "https://e2-demo-field-eng.cloud.databricks.com"
TARGET_WORKSPACE_URL = "https://sytable-classic-jddaet.cloud.databricks.net"

# Volume Configuration
SOURCE_CATALOG = "demo_catalog"
SOURCE_SCHEMA = "demo_schema"
SOURCE_VOLUME = "migration_files"
SOURCE_DASHBOARD_FILENAME = "category_insights_dashboard.lvdash.json"

TARGET_CATALOG = "vizient_migration_edl_demo"
TARGET_SCHEMA = "edl_vizient_deep_dive"
TARGET_VOLUME = "migration_files"
TARGET_DASHBOARD_FILENAME = "dashboard_updated.lvdash.json"

# Dashboard Configuration
TARGET_DASHBOARD_NAME = "Category Insights - Healthcare Supply Chain"
TARGET_DASHBOARD_PATH = "/Workspace/Users/your.name@company.com/Dashboards"

# Import Method
IMPORT_METHOD = "manual"  # You'll import via UI

# Authentication
AUTH_METHOD = "PAT"
SOURCE_PAT_TOKEN = dbutils.secrets.get(scope="migration", key="source-pat")
TARGET_PAT_TOKEN = dbutils.secrets.get(scope="migration", key="target-pat")

# Permissions (REQUIRED)
SOURCE_DASHBOARD_ID = "01f0fb1aabc91dc88f09650d5c307b00"  # ⚠️ SET THIS
USER_GROUP_MAPPING = {}  # Add mappings if user names differ

# Lookup File
LOOKUP_FILE_NAME = "catalog_mapping_vizient_simple.csv"
```

---

### For Programmatic Import (Automated):

```python
# Same as above, plus:

IMPORT_METHOD = "programmatic"
TARGET_WAREHOUSE_ID = "abc123def456"  # ⚠️ REQUIRED for programmatic
PUBLISH_DASHBOARD = True  # Auto-publish after import
```

---

## Key Benefits of New Flow

### 1. Permissions Migration is Required
- ✅ Ensures access control is maintained
- ✅ No risk of forgetting to set permissions
- ✅ Automatic backup for audit trail

### 2. Manual Import Supported
- ✅ Easier for first-time users
- ✅ Visual confirmation of dashboard
- ✅ Less authentication complexity

### 3. Clear Authentication Purpose
- ✅ Documented what each token is used for
- ✅ Optional operations clearly marked
- ✅ Security best practices included

---

## Migration Checklist

### Before Running:

- [ ] Set `SOURCE_DASHBOARD_ID` in configuration
- [ ] Set `SOURCE_PAT_TOKEN` (or OAuth credentials)
- [ ] Set `TARGET_PAT_TOKEN` (or OAuth credentials)
- [ ] Create `catalog_mapping_vizient_simple.csv` lookup file
- [ ] Choose `IMPORT_METHOD` ("manual" or "programmatic")
- [ ] If programmatic: Set `TARGET_WAREHOUSE_ID`
- [ ] Configure `USER_GROUP_MAPPING` if user names differ

### During Execution:

- [ ] **Steps 1-6:** Run automatically (no action needed)
- [ ] **Step 7:** 
  - If manual: Import via UI, copy dashboard ID
  - If programmatic: Verify success message
- [ ] **Step 7a:** If manual, set `target_dashboard_id`
- [ ] **Step 7.5:** Verify permissions migrated successfully
- [ ] **Step 8:** Publish (manual or auto based on method)

### After Migration:

- [ ] Review `dashboard_permissions_backup.json`
- [ ] Open target dashboard and verify visuals
- [ ] Test with non-admin user
- [ ] Grant Unity Catalog data access:
  ```sql
  GRANT SELECT ON SCHEMA vizient_migration_edl_demo.edl_vizient_deep_dive 
    TO `data_analysts`;
  ```
- [ ] Document any manual changes made
- [ ] Archive source dashboard or mark as deprecated

---

## Troubleshooting

### "Target dashboard ID not set"

**For manual import:**
- Go back to Step 7a
- Uncomment and set: `target_dashboard_id = "your-id"`
- Rerun Step 7.5

### "Source dashboard ID not found"

**Solution:**
- Set `SOURCE_DASHBOARD_ID` in configuration (Cell 2)
- Get from source dashboard URL
- Rerun from beginning

### "Could not retrieve permissions"

**Causes:**
- Missing source workspace access
- Dashboard is private
- Insufficient permissions

**Solutions:**
- Ensure SOURCE_PAT_TOKEN has CAN_MANAGE on source dashboard
- Use admin credentials
- Or set permissions manually after migration

---

## Files Created/Updated

### Updated:
1. **`02_Migrate_Dashboard.ipynb`**
   - Permissions migration now required
   - Manual import option added
   - Clearer authentication documentation

### New Documentation:
2. **`AUTHENTICATION_GUIDE.md`** - What auth is used for
3. **`WORKFLOW_UPDATES.md`** - This file
4. **`catalog_mapping_vizient_simple.csv`** - Your lookup file

### Existing:
5. **`PERMISSIONS_MIGRATION_GUIDE.md`** - Permissions details
6. **`LOOKUP_FILE_GUIDE.md`** - Catalog mapping guide
7. **`DASHBOARD_MIGRATION_README.md`** - Main migration guide

---

## Quick Start

### For Your Vizient Migration:

1. **Open notebook:** `02_Migrate_Dashboard.ipynb`

2. **Set configuration (Cell 2):**
   ```python
   SOURCE_WORKSPACE_URL = "https://e2-demo-field-eng.cloud.databricks.com"
   SOURCE_DASHBOARD_ID = "01f0fb1aabc91dc88f09650d5c307b00"  # ⚠️ SET THIS
   
   TARGET_WORKSPACE_URL = "https://sytable-classic-jddaet.cloud.databricks.net"
   TARGET_CATALOG = "vizient_migration_edl_demo"
   TARGET_SCHEMA = "edl_vizient_deep_dive"
   
   IMPORT_METHOD = "manual"
   LOOKUP_FILE_NAME = "catalog_mapping_vizient_simple.csv"
   ```

3. **Run Steps 1-6:** Automatic

4. **Step 7 (Manual Import):**
   - Go to target workspace UI
   - Import dashboard from volume
   - Copy dashboard ID

5. **Step 7a:** Set `target_dashboard_id`

6. **Step 7.5:** Permissions migrate automatically

7. **Done!** Dashboard and permissions migrated

---

## Summary

**Before:** Permissions were optional, only programmatic import supported, unclear what auth was for

**After:** Permissions are required, manual import supported, clear authentication documentation

**Result:** More flexible, easier to use, better security with required permissions migration!

---

**Questions?** See:
- `AUTHENTICATION_GUIDE.md` - Auth details
- `PERMISSIONS_MIGRATION_GUIDE.md` - Permissions details
- `DASHBOARD_MIGRATION_README.md` - Overall guide
