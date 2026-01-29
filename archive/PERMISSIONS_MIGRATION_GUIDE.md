# Dashboard Permissions Migration Guide

## Overview

The updated `02_Migrate_Dashboard.ipynb` now includes automatic dashboard permissions migration. This feature exports permissions (ACLs) from the source dashboard and applies them to the target dashboard.

---

## What Gets Migrated

### Permission Levels
- **CAN_VIEW** - View dashboards only
- **CAN_RUN** - View and refresh dashboards
- **CAN_EDIT** - View, refresh, and edit dashboards
- **CAN_MANAGE** - Full control including sharing and deletion

### Principal Types
- **Users** - Individual user accounts
- **Groups** - Workspace or account-level groups
- **Service Principals** - Application service accounts

---

## Configuration

### 1. Enable Permissions Migration

In the Configuration cell:

```python
MIGRATE_PERMISSIONS = True  # Set to False to skip permissions migration
```

### 2. Set Source Dashboard ID (Required)

**Option A: From Dashboard URL**

If you know the source dashboard URL, extract the ID:
```
URL: https://e2-demo-field-eng.cloud.databricks.com/sql/dashboardsv3/01f0fb1aabc91dc88f09650d5c307b00
ID:  01f0fb1aabc91dc88f09650d5c307b00
```

Set it in the optional configuration cell:
```python
SOURCE_DASHBOARD_ID = "01f0fb1aabc91dc88f09650d5c307b00"
```

**Option B: From JSON File**

If your `.lvdash.json` file contains a `dashboard_id` field, it will be used automatically.

### 3. Map Users/Groups (Optional)

If user or group names differ between workspaces, add mappings:

```python
USER_GROUP_MAPPING = {
    "old_user@company.com": "new_user@company.com",
    "dev_team": "prod_team",
    "service_principal_old": "service_principal_new"
}
```

---

## How It Works

### Step 7.5: Migrate Permissions

1. **Export from Source**
   - Connects to source workspace
   - Retrieves dashboard ACLs via Workspace API
   - Displays current permissions

2. **Map Principals**
   - Applies `USER_GROUP_MAPPING` if configured
   - Keeps original names if no mapping exists

3. **Backup Permissions**
   - Saves to `dashboard_permissions_backup.json`
   - Includes source/target IDs and timestamp
   - Useful for audit and rollback

4. **Apply to Target**
   - Connects to target workspace
   - Sets permissions on newly created dashboard
   - Displays applied permissions

---

## Example Workflow

### Scenario 1: Same Users in Both Workspaces

```python
# Configuration
SOURCE_DASHBOARD_ID = "01f0fb1aabc91dc88f09650d5c307b00"
MIGRATE_PERMISSIONS = True
USER_GROUP_MAPPING = {}  # Empty - users have same names

# Result:
# Source: alice@company.com (CAN_MANAGE), bob@company.com (CAN_VIEW)
# Target: alice@company.com (CAN_MANAGE), bob@company.com (CAN_VIEW)
```

### Scenario 2: Different User Names

```python
# Configuration
SOURCE_DASHBOARD_ID = "01f0fb1aabc91dc88f09650d5c307b00"
MIGRATE_PERMISSIONS = True
USER_GROUP_MAPPING = {
    "alice@dev.company.com": "alice@prod.company.com",
    "dev_team": "prod_team"
}

# Result:
# Source: alice@dev.company.com (CAN_MANAGE), dev_team (CAN_EDIT)
# Target: alice@prod.company.com (CAN_MANAGE), prod_team (CAN_EDIT)
```

### Scenario 3: Manual Permissions Only

```python
# Configuration
MIGRATE_PERMISSIONS = False

# Result:
# Permissions not migrated - set manually via dashboard Share button
```

---

## Permissions Backup File

The migration creates `dashboard_permissions_backup.json`:

```json
{
  "source_dashboard_id": "01f0fb1aabc91dc88f09650d5c307b00",
  "target_dashboard_id": "abc123def456",
  "source_permissions": {
    "access_control_list": [
      {
        "user_name": "alice@company.com",
        "all_permissions": [
          {
            "permission_level": "CAN_MANAGE",
            "inherited": false
          }
        ]
      },
      {
        "group_name": "data_team",
        "all_permissions": [
          {
            "permission_level": "CAN_EDIT",
            "inherited": false
          }
        ]
      }
    ]
  },
  "timestamp": "2026-01-27T10:30:00"
}
```

**Use this file to:**
- Audit what permissions were migrated
- Manually apply permissions if automatic migration fails
- Rollback or verify permissions later

---

## Troubleshooting

### Issue: "Source dashboard ID not found"

**Cause:** Dashboard JSON doesn't contain `dashboard_id` field and `SOURCE_DASHBOARD_ID` not set.

**Solution:**
```python
# Set the source dashboard ID manually
SOURCE_DASHBOARD_ID = "your-dashboard-id-here"
```

### Issue: "Could not retrieve permissions: 403"

**Cause:** Insufficient permissions in source workspace.

**Solutions:**
- Ensure you have `CAN_MANAGE` permission on source dashboard
- Use admin credentials for source workspace
- Or set permissions manually after migration

### Issue: "Could not set permissions: 404"

**Cause:** User/group doesn't exist in target workspace.

**Solutions:**
1. Create missing users/groups in target workspace first
2. Use `USER_GROUP_MAPPING` to map to existing users/groups
3. Or set permissions manually after migration

### Issue: "No permissions found"

**Causes:**
- Dashboard is private (only owner has access)
- You don't have admin access to source
- Dashboard uses default permissions only

**Solution:**
This is expected behavior. Set permissions manually:
1. Open target dashboard
2. Click "Share" button
3. Add users/groups with appropriate levels

---

## Data Access Permissions (Separate)

Dashboard permissions control WHO can VIEW/EDIT the dashboard.

Users ALSO need Unity Catalog permissions to access the underlying data:

### Grant Table Access
```sql
-- Grant to user
GRANT SELECT ON TABLE catalog.schema.table TO `user@example.com`;

-- Grant to group
GRANT SELECT ON SCHEMA catalog.schema TO `data_analysts`;
```

### Grant Volume Access (for embedded images)
```sql
GRANT READ FILES ON VOLUME catalog.schema.volume_name TO `user@example.com`;
```

### Use Embedded Credentials (Alternative)

If you publish with embedded credentials, viewers don't need direct data access:

```python
# In Step 8: Publish Dashboard
publish_dashboard(target_client, target_dashboard_id, embed_credentials=True)
```

**Note:** Embedded credentials use the publisher's access. Use a service principal token for this.

---

## Best Practices

### 1. Use Service Principals for Production
```python
# Use service principal token instead of personal PAT
TARGET_PAT_TOKEN = dbutils.secrets.get(scope="prod", key="service_principal_token")
```

### 2. Document Permission Mappings
Keep a record of user/group mappings:
```python
# Document why mappings exist
USER_GROUP_MAPPING = {
    "dev_admin@company.com": "prod_admin@company.com",  # Different domains
    "test_viewers": "prod_viewers",  # Group rename
}
```

### 3. Test with Non-Admin User
After migration:
1. Log in as a regular user (non-admin)
2. Verify they can access the dashboard
3. Check data loads correctly

### 4. Review Backup File
Always check `dashboard_permissions_backup.json` to confirm what was migrated.

### 5. Combine with Data Grants
```sql
-- Create script to grant all necessary data access
GRANT SELECT ON SCHEMA vizient_migration_edl_demo.edl_vizient_deep_dive TO `data_analysts`;
GRANT READ FILES ON VOLUME vizient_migration_edl_demo.edl_vizient_deep_dive.migration_files TO `data_analysts`;
```

---

## Manual Permissions Setup

If automatic migration fails or you prefer manual control:

### Via UI
1. Open target dashboard: `https://workspace/sql/dashboardsv3/{dashboard_id}`
2. Click **"Share"** button (top right)
3. Add users/groups:
   - Search for user/group name
   - Select permission level (View, Run, Edit, Manage)
   - Click "Add"
4. Click "Done"

### Via API (Python)
```python
import requests

url = f"{TARGET_WORKSPACE_URL}/api/2.0/permissions/dashboards/{dashboard_id}"
headers = {
    "Authorization": f"Bearer {TARGET_PAT_TOKEN}",
    "Content-Type": "application/json"
}
payload = {
    "access_control_list": [
        {
            "user_name": "alice@company.com",
            "permission_level": "CAN_MANAGE"
        },
        {
            "group_name": "data_team",
            "permission_level": "CAN_EDIT"
        }
    ]
}
response = requests.put(url, headers=headers, json=payload)
```

### Via Databricks CLI
```bash
databricks permissions set dashboards {dashboard_id} \
  --json '{
    "access_control_list": [
      {"user_name": "alice@company.com", "permission_level": "CAN_MANAGE"}
    ]
  }'
```

---

## FAQ

**Q: Do I need admin access to both workspaces?**

A: For permissions migration, you need:
- `CAN_MANAGE` on source dashboard (to read permissions)
- `CAN_MANAGE` on target dashboard (to set permissions)
- Admin access helps but isn't strictly required

**Q: What if users don't exist in target workspace?**

A: The API will fail for non-existent users. Either:
1. Create users/groups in target first
2. Use `USER_GROUP_MAPPING` to map to existing users
3. Skip those users and add manually later

**Q: Can I migrate permissions without migrating the dashboard?**

A: Yes, but you need both dashboard IDs. The permission migration code can be extracted and run separately.

**Q: Do permissions include refresh schedules?**

A: No. Refresh schedules and alerts must be recreated manually in the target workspace.

**Q: What about inherited permissions?**

A: Inherited permissions (from workspace/folder level) are not migrated. Only direct dashboard ACLs are copied.

---

## Related Documentation

- [Databricks Permissions API](https://docs.databricks.com/api/workspace/permissions)
- [Lakeview Dashboard Sharing](https://docs.databricks.com/dashboards/lakeview/sharing.html)
- [Unity Catalog Grants](https://docs.databricks.com/sql/language-manual/sql-ref-syntax-aux-show-grants.html)

---

## Summary Checklist

- [ ] Set `MIGRATE_PERMISSIONS = True`
- [ ] Configure `SOURCE_DASHBOARD_ID`
- [ ] Configure `USER_GROUP_MAPPING` if needed
- [ ] Ensure users/groups exist in target workspace
- [ ] Run migration notebook
- [ ] Review `dashboard_permissions_backup.json`
- [ ] Grant data access via Unity Catalog
- [ ] Test with non-admin user
- [ ] Document any manual changes needed

**Questions?** Check the main `DASHBOARD_MIGRATION_README.md` for additional guidance.
