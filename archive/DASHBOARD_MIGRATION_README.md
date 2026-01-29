# 🚀 Databricks Lakeview Dashboard Migration Guide

This guide provides step-by-step instructions for migrating a Lakeview dashboard from one Databricks workspace to another.

## 📋 Overview

**Source Workspace**: `https://e2-demo-field-eng.cloud.databricks.com`  
**Source Dashboard ID**: `01f0fb1aabc91dc88f09650d5c307b00`  
**Target Workspace**: `https://adb-7405609619727450.10.azuredatabricks.net`

## 🛠️ Files Included

1. **`02_Migrate_Dashboard.ipynb`** - Interactive Jupyter notebook with manual and programmatic steps
2. **`migrate_dashboard.py`** - Standalone Python script for programmatic migration
3. **`DASHBOARD_MIGRATION_README.md`** - This file

## 🔐 Authentication Methods

### Option 1: PAT (Personal Access Token) - Recommended for Quick Testing

**Advantages:**
- Simple setup
- Good for one-time migrations
- No additional configuration needed

**Steps:**
1. Generate PAT tokens in both workspaces:
   - Source: User Settings → Developer → Access Tokens → Generate New Token
   - Target: User Settings → Developer → Access Tokens → Generate New Token
2. Copy tokens securely
3. Use tokens in configuration (see below)

### Option 2: OAuth (Azure AD Service Principal) - Recommended for Production

**Advantages:**
- More secure (no tokens in code)
- Better for CI/CD pipelines
- Automatic token refresh

**Prerequisites:**
- Azure AD Service Principal with access to both workspaces
- Client ID, Tenant ID, and Client Secret

**Steps:**
1. Create Azure AD Service Principal (if not exists)
2. Grant access to both Databricks workspaces
3. Set environment variables:
   ```bash
   export ARM_CLIENT_ID="your-client-id"
   export ARM_TENANT_ID="your-tenant-id"
   export ARM_CLIENT_SECRET="your-client-secret"
   ```

## 📓 Method 1: Using Jupyter Notebook (Interactive)

### Prerequisites

```bash
pip install databricks-sdk requests jupyter
```

### Steps

1. **Open the notebook**:
   ```bash
   jupyter notebook 02_Migrate_Dashboard.ipynb
   ```

2. **Configure settings** in the first code cell:
   ```python
   SOURCE_WORKSPACE_URL = "https://e2-demo-field-eng.cloud.databricks.com"
   SOURCE_DASHBOARD_ID = "01f0fb1aabc91dc88f09650d5c307b00"
   
   TARGET_WORKSPACE_URL = "https://adb-7405609619727450.10.azuredatabricks.net"
   TARGET_DASHBOARD_NAME = "Category Insights - Healthcare Supply Chain"
   TARGET_DASHBOARD_PATH = "/Workspace/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration"
   TARGET_WAREHOUSE_ID = "your-warehouse-id"  # Find in SQL Warehouses
   
   AUTH_METHOD = "PAT"  # or "OAUTH"
   SOURCE_PAT_TOKEN = "dapi..."  # If using PAT
   TARGET_PAT_TOKEN = "dapi..."  # If using PAT
   ```

3. **Run cells sequentially** - Each cell performs a step:
   - Setup and authentication
   - Export dashboard
   - Discover references
   - Rewrite catalog/schema (if needed)
   - Validate queries (optional)
   - Import dashboard
   - Publish dashboard

4. **Review results** - Check the summary at the end

### Finding Your Warehouse ID

1. Go to **SQL** → **SQL Warehouses** in target workspace
2. Select your warehouse
3. Click **Connection details**
4. Copy the **Warehouse ID** (format: `abc123def456`)

## 🐍 Method 2: Using Python Script (Command Line)

### Prerequisites

```bash
pip install databricks-sdk
```

### Usage with PAT

```bash
python migrate_dashboard.py \
    --source-workspace https://e2-demo-field-eng.cloud.databricks.com \
    --source-dashboard-id 01f0fb1aabc91dc88f09650d5c307b00 \
    --source-pat-token dapi123... \
    --target-workspace https://adb-7405609619727450.10.azuredatabricks.net \
    --target-dashboard-name "Category Insights - Healthcare Supply Chain" \
    --target-path "/Workspace/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration" \
    --target-warehouse-id abc123def456 \
    --target-pat-token dapi456... \
    --auth-method pat \
    --validate-queries \
    --publish \
    --create-backup
```

### Usage with OAuth

```bash
# Set environment variables first
export ARM_CLIENT_ID="your-client-id"
export ARM_TENANT_ID="your-tenant-id"
export ARM_CLIENT_SECRET="your-client-secret"

# Run migration
python migrate_dashboard.py \
    --source-workspace https://e2-demo-field-eng.cloud.databricks.com \
    --source-dashboard-id 01f0fb1aabc91dc88f09650d5c307b00 \
    --target-workspace https://adb-7405609619727450.10.azuredatabricks.net \
    --target-dashboard-name "Category Insights - Healthcare Supply Chain" \
    --target-path "/Workspace/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration" \
    --target-warehouse-id abc123def456 \
    --auth-method oauth \
    --validate-queries \
    --publish \
    --create-backup
```

### Script Options

| Option | Required | Description |
|--------|----------|-------------|
| `--source-workspace` | ✅ | Source workspace URL |
| `--source-dashboard-id` | ✅ | Source dashboard ID |
| `--source-pat-token` | ⚠️ | Source PAT (required if `--auth-method=pat`) |
| `--target-workspace` | ✅ | Target workspace URL |
| `--target-dashboard-name` | ✅ | Name for dashboard in target |
| `--target-path` | ✅ | Workspace path for dashboard |
| `--target-warehouse-id` | ✅ | SQL Warehouse ID in target |
| `--target-pat-token` | ⚠️ | Target PAT (required if `--auth-method=pat`) |
| `--auth-method` | ❌ | `pat` or `oauth` (default: `pat`) |
| `--catalog-schema-map` | ❌ | JSON mapping for catalog/schema rewrites |
| `--validate-queries` | ❌ | Validate queries before import |
| `--publish` | ❌ | Publish dashboard after import |
| `--embed-credentials` | ❌ | Embed credentials when publishing |
| `--create-backup` | ❌ | Create backup file (default: enabled) |
| `--no-backup` | ❌ | Skip creating backup |

### Catalog/Schema Mapping Example

If you need to rewrite catalog/schema references:

```bash
python migrate_dashboard.py \
    ... \
    --catalog-schema-map '{"old_catalog.old_schema": "new_catalog.new_schema"}'
```

## 🔄 Manual Migration Steps (Alternative)

If you prefer manual steps:

### Step 1: Export from Source

1. Navigate to: `https://e2-demo-field-eng.cloud.databricks.com/sql/dashboardsv3/01f0fb1aabc91dc88f09650d5c307b00`
2. Click **three dots (⋯)** menu → **Export** or **Download**
3. Save the `.lvdash.json` file

### Step 2: Update References (if needed)

1. Open the `.lvdash.json` file in a text editor
2. Search and replace catalog/schema references:
   - Find: `old_catalog.old_schema`
   - Replace: `new_catalog.new_schema`

### Step 3: Import to Target

1. Navigate to: `https://adb-7405609619727450.10.azuredatabricks.net`
2. Go to **SQL** → **Dashboards**
3. Click **Create** → **Import dashboard**
4. Upload the `.lvdash.json` file
5. Select target SQL Warehouse
6. Click **Import**

### Step 4: Publish

1. Open the imported dashboard
2. Click **Publish** button
3. Configure sharing settings if needed

## ✅ Validation Checklist

After migration, verify:

- [ ] Dashboard appears in target workspace
- [ ] All visuals render correctly
- [ ] KPIs show expected values
- [ ] Filters work properly
- [ ] Data loads from correct tables
- [ ] Dashboard is published (if needed)
- [ ] Permissions are configured correctly

## 🔍 Troubleshooting

### Error: "PAT token required"

**Solution**: Ensure `--source-pat-token` and `--target-pat-token` are set when using `--auth-method=pat`

### Error: "Missing OAuth environment variables"

**Solution**: Set `ARM_CLIENT_ID`, `ARM_TENANT_ID`, and `ARM_CLIENT_SECRET` before running

### Error: "Dashboard not found"

**Solution**: 
- Verify dashboard ID is correct (from URL)
- Ensure you have access to the dashboard
- Check workspace URL is correct

### Error: "Warehouse ID not found"

**Solution**:
- Find warehouse ID in SQL Warehouses → Connection details
- Ensure warehouse is running
- Verify you have access to the warehouse

### Error: "Query validation failed"

**Solution**:
- Check that tables exist in target workspace
- Verify catalog/schema names are correct
- Ensure you have read permissions on tables
- Review error messages for specific issues

### Dashboard shows empty visuals

**Solution**:
- Verify dataset queries reference correct tables
- Check that data exists in target tables
- Ensure SQL Warehouse has access to Unity Catalog
- Review dashboard JSON for query syntax errors

## 📚 Best Practices

1. **Always create backups** - Use `--create-backup` to save exported dashboard JSON
2. **Validate queries** - Use `--validate-queries` to catch issues before import
3. **Test in staging** - Import to a test workspace first if possible
4. **Document mappings** - Keep track of catalog/schema mappings for future migrations
5. **Use OAuth for production** - More secure than PAT tokens
6. **Review permissions** - Ensure target workspace users have necessary access
7. **Monitor after migration** - Check dashboard performance and data accuracy

## 🔗 Additional Resources

- [Databricks Lakeview API Documentation](https://docs.databricks.com/api/workspace/lakeview)
- [Databricks SDK for Python](https://databricks-sdk-py.readthedocs.io/)
- [Workspace API Reference](https://docs.databricks.com/api/workspace/workspace)
- [Lakeview Dashboard Migration Playbook](./Lakeview%20Dashboard%20Migration%20Playbook.txt)

## 📝 Notes

- Dashboard IDs are unique per workspace
- Dashboard URLs will be different in target workspace
- Permissions must be reconfigured in target workspace
- Schedules/subscriptions need to be recreated
- Embedded images from Volumes require separate permissions

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review error messages carefully
3. Verify all configuration values
4. Test authentication separately
5. Check Databricks documentation

---

**Last Updated**: 2026-01-26  
**Version**: 1.0
