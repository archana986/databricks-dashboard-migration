# ⚡ Quick Migration Guide

## 🎯 Quick Start (PAT Authentication)

```bash
# 1. Install dependencies
pip install databricks-sdk

# 2. Run migration script
python migrate_dashboard.py \
    --source-workspace https://e2-demo-field-eng.cloud.databricks.com \
    --source-dashboard-id 01f0fb1aabc91dc88f09650d5c307b00 \
    --source-pat-token YOUR_SOURCE_PAT \
    --target-workspace https://adb-7405609619727450.10.azuredatabricks.net \
    --target-dashboard-name "Category Insights - Healthcare Supply Chain" \
    --target-path "/Workspace/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration" \
    --target-warehouse-id YOUR_WAREHOUSE_ID \
    --target-pat-token YOUR_TARGET_PAT \
    --validate-queries \
    --publish \
    --create-backup
```

## 🔐 Quick Start (OAuth Authentication)

```bash
# 1. Set environment variables
export ARM_CLIENT_ID="your-client-id"
export ARM_TENANT_ID="your-tenant-id"
export ARM_CLIENT_SECRET="your-client-secret"

# 2. Install dependencies
pip install databricks-sdk

# 3. Run migration script
python migrate_dashboard.py \
    --source-workspace https://e2-demo-field-eng.cloud.databricks.com \
    --source-dashboard-id 01f0fb1aabc91dc88f09650d5c307b00 \
    --target-workspace https://adb-7405609619727450.10.azuredatabricks.net \
    --target-dashboard-name "Category Insights - Healthcare Supply Chain" \
    --target-path "/Workspace/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration" \
    --target-warehouse-id YOUR_WAREHOUSE_ID \
    --auth-method oauth \
    --validate-queries \
    --publish \
    --create-backup
```

## 📋 Pre-Migration Checklist

- [ ] PAT tokens generated for both workspaces (if using PAT)
- [ ] OAuth credentials configured (if using OAuth)
- [ ] Target SQL Warehouse ID identified
- [ ] Target workspace path confirmed
- [ ] Source dashboard ID copied from URL
- [ ] Catalog/schema mapping prepared (if needed)

## 🔍 Finding Your Warehouse ID

1. Go to **SQL** → **SQL Warehouses** in target workspace
2. Select your warehouse
3. Click **Connection details**
4. Copy the **Warehouse ID**

## 📝 Key Configuration Values

| Parameter | Value |
|-----------|-------|
| Source Workspace | `https://e2-demo-field-eng.cloud.databricks.com` |
| Source Dashboard ID | `01f0fb1aabc91dc88f09650d5c307b00` |
| Target Workspace | `https://adb-7405609619727450.10.azuredatabricks.net` |
| Target Path | `/Workspace/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration` |

## 🚨 Common Issues

**Issue**: "PAT token required"  
**Fix**: Add `--source-pat-token` and `--target-pat-token` flags

**Issue**: "Warehouse ID not found"  
**Fix**: Find warehouse ID in SQL Warehouses → Connection details

**Issue**: "Dashboard not found"  
**Fix**: Verify dashboard ID from URL: `/sql/dashboardsv3/{id}`

## 📚 Full Documentation

See [DASHBOARD_MIGRATION_README.md](./DASHBOARD_MIGRATION_README.md) for detailed instructions.
