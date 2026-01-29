# ✨ What's New: Permissions Migration Feature

## 🎉 Summary

Your dashboard migration notebook now includes **automatic permissions migration**! When you migrate a dashboard, user permissions (ACLs) can be automatically copied from source to target.

---

## 📦 Files Updated & Created

### Updated Files

1. **`02_Migrate_Dashboard.ipynb`** ✨ ENHANCED
   - Added permissions migration configuration
   - New Step 7.5: Migrate Dashboard Permissions
   - User/group mapping capability
   - Automatic backup of permissions to JSON

### New Documentation Files

2. **`PERMISSIONS_MIGRATION_GUIDE.md`** (9.9 KB)
   - Complete guide to using permissions migration
   - Configuration examples
   - Troubleshooting tips
   - Best practices and FAQ

3. **`PERMISSIONS_UPDATE_SUMMARY.md`** (9.1 KB)
   - Quick reference for what changed
   - Usage instructions
   - Example outputs

4. **`WHATS_NEW_PERMISSIONS.md`** (This file)
   - Quick overview of new features

### Lookup Files for Your Migration

5. **`catalog_mapping_vizient_simple.csv`** ✅ USE THIS
   - Pre-configured for your Vizient migration
   - Maps: `archana_krish_fe_dsa.vizient_deep_dive` → `vizient_migration_edl_demo.edl_vizient_deep_dive`

6. **`catalog_mapping_vizient.csv`**
   - Enhanced version with workspace fields

---

## 🚀 Quick Start

### 1. Configure Permissions Migration

In `02_Migrate_Dashboard.ipynb`, Cell 2:

```python
# Enable permissions migration
MIGRATE_PERMISSIONS = True

# Map users if names differ (optional)
USER_GROUP_MAPPING = {
    # "old_user@company.com": "new_user@company.com"
}
```

### 2. Set Source Dashboard ID

In the new Cell 24:

```python
# Get this from your source dashboard URL:
# https://e2-demo-field-eng.../sql/dashboardsv3/01f0fb1aabc91dc88f09650d5c307b00
#                                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

SOURCE_DASHBOARD_ID = "01f0fb1aabc91dc88f09650d5c307b00"
```

### 3. Run the Notebook

Execute all cells. When you reach Step 7.5, you'll see:

```
🔐 Step 7.5: Migrating dashboard permissions...

   ℹ️  Using manually configured SOURCE_DASHBOARD_ID
   Source Dashboard ID: 01f0fb1aabc91dc88f09650d5c307b00
   Target Dashboard ID: abc123def456

   ✅ Found 3 permission(s) in source dashboard

   📋 Source Permissions:
      - alice@company.com: CAN_MANAGE
      - data_team: CAN_EDIT
      - viewers: CAN_VIEW

   💾 Permissions backed up to: dashboard_permissions_backup.json

   🔄 Applying permissions to target dashboard...
   ✅ Permissions migrated successfully!
```

---

## 🎯 What Gets Migrated

### Dashboard Permissions (ACLs)
- ✅ **CAN_VIEW** - View dashboards
- ✅ **CAN_RUN** - View and refresh  
- ✅ **CAN_EDIT** - View, refresh, edit
- ✅ **CAN_MANAGE** - Full control

### Principal Types
- ✅ Individual users (`user@company.com`)
- ✅ Groups (`data_analysts`, `viewers`)
- ✅ Service principals (`sp-prod-dashboard`)

### What's Saved
- ✅ Backup file: `dashboard_permissions_backup.json`
- ✅ Complete ACL list
- ✅ Source/target dashboard IDs
- ✅ Timestamp for audit

---

## 💡 Common Use Cases

### Case 1: Same Users in Both Workspaces ✅ EASIEST

```python
SOURCE_DASHBOARD_ID = "01f0fb1aabc91dc88f09650d5c307b00"
MIGRATE_PERMISSIONS = True
USER_GROUP_MAPPING = {}  # Empty - users have same names
```

**Result:** Permissions copied exactly as-is.

---

### Case 2: Different User Names

```python
SOURCE_DASHBOARD_ID = "01f0fb1aabc91dc88f09650d5c307b00"
MIGRATE_PERMISSIONS = True
USER_GROUP_MAPPING = {
    "dev_admin@company.com": "prod_admin@company.com",
    "dev_viewers": "prod_viewers"
}
```

**Result:** User/group names automatically mapped during migration.

---

### Case 3: Skip Permissions (Manual Setup)

```python
MIGRATE_PERMISSIONS = False
```

**Result:** Set permissions manually via dashboard UI after migration.

---

## 📂 Generated Files

After running the migration, you'll have:

### `dashboard_permissions_backup.json`
```json
{
  "source_dashboard_id": "01f0fb1aabc91dc88f09650d5c307b00",
  "target_dashboard_id": "abc123def456",
  "source_permissions": {
    "access_control_list": [
      {
        "user_name": "alice@company.com",
        "all_permissions": [{"permission_level": "CAN_MANAGE"}]
      }
    ]
  },
  "timestamp": "2026-01-27T10:30:00"
}
```

**Use this for:**
- Audit what was migrated
- Manual application if automatic fails
- Rollback or verification

---

## ⚠️ Important Notes

### 1. Data Access Separate from Dashboard Access

Users need BOTH:

**Dashboard Permission** (migrated automatically):
```
alice@company.com → CAN_VIEW on dashboard
```

**Data Permission** (grant manually):
```sql
GRANT SELECT ON SCHEMA vizient_migration_edl_demo.edl_vizient_deep_dive 
  TO `alice@company.com`;
```

### 2. Users Must Exist in Target Workspace

If a user doesn't exist, you'll see:
```
⚠️ Could not set permissions: 404
User xyz@company.com not found
```

**Solutions:**
- Create user in target first
- Use `USER_GROUP_MAPPING` to map to existing user
- Or skip that user and add manually

### 3. Source Dashboard ID Required

Get it from URL:
```
https://e2-demo-field-eng.../sql/dashboardsv3/01f0fb1aabc91dc88f09650d5c307b00
                                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                              This is your SOURCE_DASHBOARD_ID
```

---

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| **"Source dashboard ID not found"** | Set `SOURCE_DASHBOARD_ID = "..."` in Cell 24 |
| **"Could not retrieve permissions: 403"** | Ensure you have CAN_MANAGE on source dashboard |
| **"User not found: 404"** | Add user to target or use USER_GROUP_MAPPING |
| **"No permissions found"** | Normal if dashboard is private - set manually |

**Full troubleshooting guide:** See `PERMISSIONS_MIGRATION_GUIDE.md`

---

## 📚 Documentation Guide

| File | When to Read |
|------|--------------|
| **`PERMISSIONS_UPDATE_SUMMARY.md`** | Overview of what was added |
| **`PERMISSIONS_MIGRATION_GUIDE.md`** | Complete how-to guide |
| **`WHATS_NEW_PERMISSIONS.md`** | This file - quick reference |
| **`LOOKUP_FILE_GUIDE.md`** | Catalog mapping guide |
| **`DASHBOARD_MIGRATION_README.md`** | Main migration guide |

---

## ✅ Migration Checklist

For your Vizient migration:

- [ ] **Configure source/target** (Cell 2)
  ```python
  SOURCE_WORKSPACE_URL = "https://e2-demo-field-eng.cloud.databricks.com"
  TARGET_WORKSPACE_URL = "https://sytable-classic-jddaet.cloud.databricks.net"
  TARGET_CATALOG = "vizient_migration_edl_demo"
  TARGET_SCHEMA = "edl_vizient_deep_dive"
  ```

- [ ] **Set lookup file** (Cell 2)
  ```python
  LOOKUP_FILE_NAME = "catalog_mapping_vizient_simple.csv"
  ```

- [ ] **Enable permissions** (Cell 2)
  ```python
  MIGRATE_PERMISSIONS = True
  ```

- [ ] **Set source dashboard ID** (Cell 24)
  ```python
  SOURCE_DASHBOARD_ID = "your-dashboard-id-here"
  ```

- [ ] **Configure authentication** (Cell 2)
  ```python
  SOURCE_PAT_TOKEN = "..."  # or use dbutils.secrets
  TARGET_PAT_TOKEN = "..."
  ```

- [ ] **Run all cells** in the notebook

- [ ] **Review backup file**: `dashboard_permissions_backup.json`

- [ ] **Grant data access**:
  ```sql
  GRANT SELECT ON SCHEMA vizient_migration_edl_demo.edl_vizient_deep_dive 
    TO `data_analysts`;
  ```

- [ ] **Test with non-admin user**

---

## 🎓 Learn More

### Step-by-Step Tutorial
Read: `PERMISSIONS_MIGRATION_GUIDE.md`

### Configuration Examples
Read: `PERMISSIONS_UPDATE_SUMMARY.md`

### Overall Migration Guide
Read: `DASHBOARD_MIGRATION_README.md`

### API Reference
- [Databricks Permissions API](https://docs.databricks.com/api/workspace/permissions)
- [Lakeview Sharing](https://docs.databricks.com/dashboards/lakeview/sharing.html)

---

## 🤝 Need Help?

1. **Check the backup file**: `dashboard_permissions_backup.json`
2. **Review logs**: Look at Step 7.5 output in notebook
3. **Read troubleshooting**: `PERMISSIONS_MIGRATION_GUIDE.md` § Troubleshooting
4. **Manual fallback**: Dashboard Share button in UI

---

## 🎉 Benefits

### Before
- ❌ Manual permission setup in target
- ❌ Risk of missing users
- ❌ No audit trail
- ❌ Time-consuming for many dashboards

### After  
- ✅ Automatic permission migration
- ✅ User/group mapping capability
- ✅ Automatic backup for audit
- ✅ Batch migrate multiple dashboards

---

**Ready to migrate?** Open `02_Migrate_Dashboard.ipynb` and follow the configuration steps above!

For detailed guidance, see:
- `PERMISSIONS_MIGRATION_GUIDE.md` - Complete guide
- `PERMISSIONS_UPDATE_SUMMARY.md` - Feature overview
- `catalog_mapping_vizient_simple.csv` - Your catalog mappings
