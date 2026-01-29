# Permissions Migration Feature - Update Summary

## What Was Added

Your `02_Migrate_Dashboard.ipynb` notebook has been enhanced with **automatic dashboard permissions migration** capability.

---

## New Features

### 1. **Configuration Options** (Cell 2)

Added to the configuration cell:

```python
# Migration Options
MIGRATE_PERMISSIONS = True  # Enable/disable permissions migration

# Permissions Configuration
USER_GROUP_MAPPING = {
    # Map users/groups if names differ between workspaces
}
PERMISSIONS_BACKUP_FILE = "dashboard_permissions_backup.json"
```

### 2. **Step 7.5: Migrate Dashboard Permissions** (New Cells)

A complete permissions migration workflow:

- **Cell 23**: Introduction and setup instructions (Markdown)
- **Cell 24**: Optional SOURCE_DASHBOARD_ID configuration (Python)
- **Cell 25**: Full permissions migration logic (Python)

#### Key Functions Added:

**`get_dashboard_permissions(client, workspace_url, dashboard_id)`**
- Retrieves ACLs from source dashboard
- Uses Workspace Permissions API
- Handles authentication (PAT/OAuth)

**`map_principal(principal, mapping)`**
- Maps user/group names between workspaces
- Uses `USER_GROUP_MAPPING` configuration

**`set_dashboard_permissions(client, workspace_url, dashboard_id, acl_list)`**
- Applies ACLs to target dashboard
- Validates and reports success/failure

### 3. **Automatic Workflow**

The permissions migration:
1. ✅ Detects source dashboard ID (from JSON or manual config)
2. ✅ Exports permissions from source workspace
3. ✅ Maps principals using `USER_GROUP_MAPPING`
4. ✅ Saves backup to `dashboard_permissions_backup.json`
5. ✅ Applies permissions to target dashboard
6. ✅ Reports success with detailed logs

---

## How to Use

### Basic Usage (Same users in both workspaces)

1. **Set source dashboard ID:**
   ```python
   SOURCE_DASHBOARD_ID = "01f0fb1aabc91dc88f09650d5c307b00"
   ```

2. **Enable migration:**
   ```python
   MIGRATE_PERMISSIONS = True
   ```

3. **Run the notebook**
   - Permissions will automatically migrate when Step 7.5 executes

### Advanced Usage (Different user names)

```python
SOURCE_DASHBOARD_ID = "01f0fb1aabc91dc88f09650d5c307b00"
MIGRATE_PERMISSIONS = True

USER_GROUP_MAPPING = {
    "dev_user@company.com": "prod_user@company.com",
    "dev_team": "prod_team"
}
```

### Skip Permissions Migration

```python
MIGRATE_PERMISSIONS = False
```

---

## What Gets Backed Up

File: `dashboard_permissions_backup.json`

Contains:
- Source dashboard ID
- Target dashboard ID
- Complete ACL list from source
- Timestamp
- All permission levels and principal names

**Use this for:**
- Audit trail
- Manual application if automatic fails
- Rollback reference
- Documentation

---

## Example Output

When Step 7.5 runs successfully:

```
🔐 Step 7.5: Migrating dashboard permissions...

   Attempting to migrate dashboard permissions...

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

   📋 Target Permissions:
      - alice@company.com: CAN_MANAGE
      - data_team: CAN_EDIT
      - viewers: CAN_VIEW
```

---

## Migration Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Step 7: Import Dashboard to Target Workspace               │
│  → Creates new dashboard in target                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 7.5: Migrate Permissions (NEW!)                       │
│  1. Get SOURCE_DASHBOARD_ID                                 │
│  2. Export ACLs from source dashboard                       │
│  3. Map users/groups via USER_GROUP_MAPPING                 │
│  4. Save backup → dashboard_permissions_backup.json         │
│  5. Apply ACLs to target dashboard                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 8: Publish Dashboard                                   │
│  → Makes dashboard accessible to permitted users            │
└─────────────────────────────────────────────────────────────┘
```

---

## Error Handling

The feature includes comprehensive error handling:

### Scenario 1: Source Dashboard ID Not Found
```
⚠️  Source dashboard ID not found in JSON
💡 To migrate permissions, you need the source dashboard ID
   You can set it manually:
   SOURCE_DASHBOARD_ID = 'your-source-dashboard-id'

Skipping permissions migration...
```

### Scenario 2: Cannot Access Source Permissions
```
⚠️  Could not retrieve permissions: 403

ℹ️  No permissions found or could not access source permissions
💡 This is normal if:
   - Source dashboard is private
   - You don't have admin access to source workspace
   - Dashboard uses default permissions only

You can manually share the dashboard in the target workspace
```

### Scenario 3: User Doesn't Exist in Target
```
⚠️  Could not set permissions: 404
Response: {"error_code":"RESOURCE_DOES_NOT_EXIST","message":"User xyz@company.com not found"}

💡 You may need to set permissions manually in the target workspace
   Or check that users/groups exist in target workspace
```

---

## Documentation Created

1. **`PERMISSIONS_MIGRATION_GUIDE.md`**
   - Complete guide to using the permissions feature
   - Configuration examples
   - Troubleshooting section
   - Best practices
   - FAQ

2. **`PERMISSIONS_UPDATE_SUMMARY.md`** (This file)
   - Quick reference for what was added
   - Usage instructions
   - Example outputs

---

## Quick Start

### For Your Vizient Migration

Based on your setup:

```python
# In Cell 2 (Configuration)
SOURCE_WORKSPACE_URL = "https://e2-demo-field-eng.cloud.databricks.com"
TARGET_WORKSPACE_URL = "https://sytable-classic-jddaet.cloud.databricks.net"

MIGRATE_PERMISSIONS = True

# In Cell 24 (Source Dashboard ID)
SOURCE_DASHBOARD_ID = "01f0fb1aabc91dc88f09650d5c307b00"  # Your source dashboard ID

# If users have same email addresses in both workspaces:
USER_GROUP_MAPPING = {}  # Leave empty

# If users differ:
USER_GROUP_MAPPING = {
    "dev_admin@company.com": "prod_admin@company.com"
}
```

Then run all cells - permissions will migrate automatically!

---

## Important Notes

### What IS Migrated
✅ User permissions (CAN_VIEW, CAN_RUN, CAN_EDIT, CAN_MANAGE)  
✅ Group permissions  
✅ Service principal permissions  

### What IS NOT Migrated
❌ Refresh schedules  
❌ Email/Slack alerts  
❌ Comments on dashboard  
❌ View history/analytics  
❌ Inherited permissions from folders  

### Additional Grants Needed

Users also need Unity Catalog permissions to access data:

```sql
-- After dashboard migration, grant data access:
GRANT SELECT ON SCHEMA vizient_migration_edl_demo.edl_vizient_deep_dive 
  TO `data_analysts`;

GRANT READ FILES ON VOLUME vizient_migration_edl_demo.edl_vizient_deep_dive.migration_files 
  TO `data_analysts`;
```

---

## Testing Checklist

After running the migration:

- [ ] Check `dashboard_permissions_backup.json` was created
- [ ] Review permissions in backup file match source
- [ ] Open target dashboard as admin - verify it loads
- [ ] Open target dashboard as regular user - verify access
- [ ] Check all visuals render with correct data
- [ ] Verify filters work correctly
- [ ] Test with a user who should NOT have access (should be denied)

---

## Next Steps

1. **Review the full guide**: `PERMISSIONS_MIGRATION_GUIDE.md`
2. **Update your configuration**: Set `SOURCE_DASHBOARD_ID` in Cell 24
3. **Run the migration**: Execute all notebook cells
4. **Grant data access**: Run SQL grants for Unity Catalog
5. **Test access**: Log in as different users to verify

---

## Questions?

- Review `PERMISSIONS_MIGRATION_GUIDE.md` for detailed guidance
- Check `DASHBOARD_MIGRATION_README.md` for overall migration process
- Backup file location: `dashboard_permissions_backup.json`

**The permissions migration is optional** - you can disable it with `MIGRATE_PERMISSIONS = False` and set permissions manually if preferred.
