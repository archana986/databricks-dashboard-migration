# Lakeview Dashboard Migration - Complete Guide

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Notebook 1: Setup & Configuration](#notebook-1-setup--configuration)
5. [Notebook 2: Export & Transform](#notebook-2-export--transform)
6. [Notebook 3: Import & Migrate](#notebook-3-import--migrate)
7. [Authentication Guide](#authentication-guide)
8. [CSV Mapping Reference](#csv-mapping-reference)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)
11. [FAQ](#faq)

---

## Overview

### What This Solution Does

This solution enables you to migrate Databricks Lakeview dashboards between workspaces with automated catalog/schema/table reference transformations and permissions restoration.

### Three-Notebook Architecture

| Notebook | Purpose | Key Tasks |
|----------|---------|-----------|
| **01_Setup_and_Configuration** | Environment setup | Install libraries, configure auth, create volume, prepare CSV |
| **02_Export_and_Transform** | Data preparation | Export dashboards, apply transformations |
| **03_Import_and_Migrate** | Migration execution | Import to target, restore permissions, generate report |

### Key Features

- ✅ **Multiple Authentication Methods**: OAuth (recommended), Service Principal, or PAT
- ✅ **CSV-Based Mappings**: Simple catalog/schema/table transformations
- ✅ **Dual Import Workflows**: Manual (UI-based) or Automated (programmatic)
- ✅ **Permissions Migration**: Best-effort ACL restoration
- ✅ **Volume-Based Storage**: All artifacts stored in Databricks volumes
- ✅ **Comprehensive Reporting**: Detailed migration logs and reports
- ✅ **Dry Run Mode**: Test migrations without actual imports

---

## Prerequisites

### Required Access

1. **Source Workspace**:
   - Read access to dashboards
   - Permission to export workspace items
   
2. **Target Workspace**:
   - Permission to import workspace items
   - Permission to set dashboard permissions

3. **Unity Catalog**:
   - Permission to create/access volumes
   - Read/write access to designated volume

### Required Software

- Databricks Runtime 11.3 LTS or higher
- Python 3.8+
- Azure CLI (if using OAuth with az login)

### Authentication Setup

Choose **ONE** of the following:

#### Option A: OAuth (RECOMMENDED)

```bash
# Install Azure CLI
# Then login:
az login
```

**Advantages**: Easy, secure, no credential management  
**Best for**: Interactive use, development, most scenarios

#### Option B: Service Principal

```bash
# Create secret scope
databricks secrets create-scope migration

# Store credentials
databricks secrets put --scope migration --key source-sp-client-id
databricks secrets put --scope migration --key source-sp-secret
databricks secrets put --scope migration --key source-sp-tenant
databricks secrets put --scope migration --key target-sp-client-id
databricks secrets put --scope migration --key target-sp-secret
databricks secrets put --scope migration --key target-sp-tenant
```

**Advantages**: No token expiration, fine-grained permissions  
**Best for**: Production, CI/CD, automated pipelines

#### Option C: PAT Tokens

```bash
# Create secret scope
databricks secrets create-scope migration

# Store tokens
databricks secrets put --scope migration --key source-token
databricks secrets put --scope migration --key target-token
```

**Advantages**: Simple setup  
**Best for**: Quick tests, development  
**Considerations**: Tokens expire and need rotation

---

## Quick Start

### 5-Minute Setup

1. **Import notebooks to Databricks**:
   - Upload `01_Setup_and_Configuration.ipynb`
   - Upload `02_Export_and_Transform.ipynb`
   - Upload `03_Import_and_Migrate.ipynb`

2. **Create Unity Catalog volume**:
   ```sql
   CREATE VOLUME IF NOT EXISTS migration_catalog.migration_schema.migration_volume;
   ```

3. **Configure authentication** (choose one):
   ```bash
   # OAuth (easiest):
   az login
   
   # OR Service Principal / PAT:
   # Store credentials in secrets (see Authentication Setup above)
   ```

4. **Run Notebook 1**: Setup & Configuration
   - Configure workspace URLs
   - Create volume structure
   - Generate CSV template

5. **Edit CSV mapping file**:
   - Update with your catalog/schema/table mappings
   - Save to volume

6. **Run Notebook 2**: Export & Transform
   - Export dashboards from source
   - Apply transformations

7. **Run Notebook 3**: Import & Migrate
   - Choose manual or automated workflow
   - Import to target workspace
   - Restore permissions

---

## Notebook 1: Setup & Configuration

### Purpose

Prepare the migration environment with authentication, volumes, and CSV mappings.

### What It Does

1. Installs required libraries (`databricks-sdk`, `pandas`)
2. Configures authentication method
3. Tests workspace connectivity
4. Creates volume directory structure
5. Generates CSV mapping template
6. Validates entire setup

### Configuration Steps

#### Cell 3: Authentication Configuration

```python
# Choose authentication method
AUTH_METHOD = "oauth"  # Options: "oauth", "service_principal", "pat"

# Configure workspace URLs
SOURCE_WORKSPACE_URL = "https://your-source-workspace.cloud.databricks.com"
TARGET_WORKSPACE_URL = "https://your-target-workspace.cloud.databricks.com"
```

#### Cell 4: Volume Configuration

```python
# Update with your volume path
VOLUME_BASE_PATH = "/Volumes/your_catalog/your_schema/your_volume/dashboard_migration"
```

### Validation

Cell 8 performs comprehensive validation:

- ✅ Volume base path exists
- ✅ Subdirectories created
- ✅ CSV mapping file present
- ✅ Both workspaces accessible

**All checks must pass before proceeding to Notebook 2.**

---

## Notebook 2: Export & Transform

### Purpose

Export dashboards from source workspace and apply catalog/schema/table transformations.

### What It Does

1. Connects to source workspace
2. Discovers or selects dashboards to export
3. Exports each dashboard as `.lvdash.json`
4. Captures dashboard permissions (ACLs)
5. Loads CSV mappings
6. Transforms dashboard references
7. Saves transformed dashboards to volume

### Dashboard Selection

Two options for selecting dashboards:

#### Option A: Explicit Dashboard IDs

```python
DASHBOARD_IDS = [
    "dashboard_id_1",
    "dashboard_id_2",
]
USE_FOLDER_PATH = False
```

#### Option B: Folder-Based Discovery

```python
SOURCE_FOLDER_PATH = "/Workspace/Shared/Dashboards"
USE_FOLDER_PATH = True
```

### Cell Flow

| Cell | Function | Output |
|------|----------|--------|
| Cell 1 | Import configuration | Config validated |
| Cell 2 | Load helper functions | Auth & I/O ready |
| Cell 3 | Export helpers | Export logic ready |
| Cell 4 | Transform helpers | Transform logic ready |
| Cell 5 | **Export dashboards** | .lvdash.json + permissions in volume |
| Cell 6 | **Transform dashboards** | Transformed .lvdash.json in volume |

### Volume Structure After Notebook 2

```
/Volumes/.../dashboard_migration/
├── exported/
│   ├── dashboard_abc123_Sales_Dashboard.lvdash.json
│   ├── dashboard_abc123_Sales_Dashboard_permissions.json
│   └── ...
└── transformed/
    ├── dashboard_abc123_Sales_Dashboard.lvdash.json
    └── ...
```

---

## Notebook 3: Import & Migrate

### Purpose

Import transformed dashboards to target workspace and restore permissions.

### Two Workflow Options

#### Workflow A: Manual Import (Cells 5-7)

**Best for**: Review before import, selective migration, custom folder structure

**Process**:
1. **Cell 5**: View import instructions
2. **Manual step**: Import via Databricks UI
3. **Cell 6**: Configure mapping and apply ACLs
4. **Cell 7**: Generate report

**Advantages**:
- Full control over import process
- Review dashboards before importing
- Choose specific dashboards
- Custom placement in workspace

#### Workflow B: Automated Import (Cells 8-9)

**Best for**: Batch processing, repeated migrations, automation

**Process**:
1. **Cell 8**: Automatically import all dashboards and apply ACLs
2. **Cell 9**: Generate comprehensive report

**Advantages**:
- Fully automated
- Consistent placement
- Faster for multiple dashboards
- Supports dry run mode

### Cell Flow

| Cell | Function | Both Workflows |
|------|----------|----------------|
| Cell 1 | Import configuration | ✅ Required |
| Cell 2 | Load helper functions | ✅ Required |
| Cell 3 | Import & permissions helpers | ✅ Required |
| Cell 4 | List transformed dashboards | ✅ Required |

| Cell | Function | Manual Workflow | Automated Workflow |
|------|----------|----------------|-------------------|
| Cell 5 | Manual import instructions | ✅ | ❌ Skip |
| Cell 6 | Apply ACLs to manual imports | ✅ | ❌ Skip |
| Cell 7 | Manual workflow report | ✅ | ❌ Skip |
| Cell 8 | Automated import | ❌ Skip | ✅ |
| Cell 9 | Automated workflow report | ❌ Skip | ✅ |

### Manual Workflow Details

#### Cell 6: MANUAL_IMPORT_MAPPING Configuration

After manually importing dashboards via UI, configure the mapping:

```python
MANUAL_IMPORT_MAPPING = {
    "abc123": "/Workspace/Shared/Migrated_Dashboards/Sales Dashboard",
    "def456": "/Workspace/Shared/Migrated_Dashboards/Marketing KPIs",
}
```

Format: `"old_dashboard_id": "new_dashboard_path_in_target"`

### Automated Workflow Details

#### Dry Run Mode

Test migrations without actual imports:

```python
DRY_RUN = True  # Set in Cell 1
```

When `DRY_RUN = True`:
- Shows what would be imported
- Tests connectivity
- Validates transformed files
- No actual imports performed

---

## Authentication Guide

### Comparison Table

| Method | Setup | Security | Expiration | Best For | Recommended? |
|--------|-------|----------|------------|----------|--------------|
| **OAuth** | Low (az login) | High | Managed by Azure | Most scenarios | **YES** |
| Service Principal | Medium | High | None | Production/CI/CD | For automation |
| PAT Token | Low | Medium | Yes (needs rotation) | Quick tests | No |

### OAuth Setup (RECOMMENDED)

#### Method 1: Azure CLI (Easiest)

```bash
# Install Azure CLI
brew install azure-cli  # macOS
# or: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

# Login
az login
```

#### Method 2: Environment Variables

```bash
export ARM_CLIENT_ID="your-client-id"
export ARM_TENANT_ID="your-tenant-id"
export ARM_CLIENT_SECRET="your-client-secret"
```

#### Advantages

- ✅ No credential management in notebooks
- ✅ Tokens managed by Azure
- ✅ Secure and easy to use
- ✅ Recommended by Databricks
- ✅ Good for interactive development

#### Notebook Configuration

```python
AUTH_METHOD = "oauth"  # That's it!
# No additional credentials needed
```

### Service Principal Setup

#### Step 1: Create Service Principals in Azure AD

1. In Azure Portal → Azure Active Directory → App Registrations
2. Create two service principals (one for source, one for target)
3. Grant workspace access in each Databricks workspace

#### Step 2: Store Credentials in Databricks Secrets

```bash
databricks secrets create-scope migration

# Source service principal
databricks secrets put --scope migration --key source-sp-client-id
databricks secrets put --scope migration --key source-sp-secret
databricks secrets put --scope migration --key source-sp-tenant

# Target service principal
databricks secrets put --scope migration --key target-sp-client-id
databricks secrets put --scope migration --key target-sp-secret
databricks secrets put --scope migration --key target-sp-tenant
```

#### Notebook Configuration

```python
AUTH_METHOD = "service_principal"
# Credentials loaded from secrets automatically
```

#### Advantages

- ✅ No token expiration
- ✅ Fine-grained Azure AD permissions
- ✅ Better audit trail
- ✅ Suitable for CI/CD pipelines

### PAT Token Setup

#### Step 1: Generate PAT Tokens

1. In each Databricks workspace:
   - User Settings → Access Tokens
   - Generate New Token
   - Copy and save securely

#### Step 2: Store in Databricks Secrets

```bash
databricks secrets create-scope migration
databricks secrets put --scope migration --key source-token
databricks secrets put --scope migration --key target-token
```

#### Notebook Configuration

```python
AUTH_METHOD = "pat"
# Credentials loaded from secrets automatically
```

#### Considerations

- ⚠️ Tokens expire (90 days by default)
- ⚠️ Requires rotation management
- ✅ Simple for quick tests

---

## CSV Mapping Reference

### File Format

```csv
old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
```

### Column Definitions

| Column | Required? | Description | Example |
|--------|-----------|-------------|---------|
| `old_catalog` | Yes | Source catalog name | `dev_catalog` |
| `old_schema` | Yes | Source schema name | `bronze_layer` |
| `old_table` | Optional | Source table name (empty for schema-level) | `customers` |
| `new_catalog` | Yes | Target catalog name | `prod_catalog` |
| `new_schema` | Yes | Target schema name | `gold_layer` |
| `new_table` | Optional | Target table name | `customers` |
| `old_volume` | Optional | Source volume name | `dev_files` |
| `new_volume` | Optional | Target volume name | `prod_files` |

### Mapping Examples

#### Example 1: Table-Level Mapping

```csv
old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
dev_catalog,bronze_layer,customers,prod_catalog,gold_layer,customers,dev_files,prod_files
dev_catalog,bronze_layer,orders,prod_catalog,gold_layer,orders,dev_files,prod_files
```

**Transforms**:
- `dev_catalog.bronze_layer.customers` → `prod_catalog.gold_layer.customers`
- `dev_catalog.bronze_layer.orders` → `prod_catalog.gold_layer.orders`

#### Example 2: Schema-Level Mapping

```csv
old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
dev_catalog,bronze_layer,,prod_catalog,gold_layer,,,
```

**Transforms**:
- `dev_catalog.bronze_layer.*` → `prod_catalog.gold_layer.*`
- All tables in the schema are mapped

#### Example 3: Volume Path Mapping

```csv
old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
,,,,,,,dev_files,prod_files
```

**Transforms**:
- `/Volumes/dev_files/` → `/Volumes/prod_files/`

#### Example 4: Complex Mapping

```csv
old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
dev_catalog,raw_data,events,prod_catalog,curated_data,events,dev_vol,prod_vol
dev_catalog,raw_data,clicks,prod_catalog,analytics,clicks,dev_vol,analytics_vol
staging,sandbox,,prod_catalog,staging,,,
test_catalog,test_schema,test_table,prod_catalog,production,prod_table,test_vol,prod_vol
```

### Best Practices

1. **Order Matters**: List specific mappings before general ones
2. **Test First**: Start with a few mappings, validate, then add more
3. **Use Comments**: Add a second header row with notes (will be ignored)
4. **Version Control**: Keep CSV in version control
5. **Document Changes**: Maintain a changelog for mapping updates

---

## Troubleshooting

### Common Issues

#### Issue: "databricks-sdk not installed"

**Solution**:
```python
%pip install databricks-sdk pandas --quiet
dbutils.library.restartPython()
```

#### Issue: "Volume not found"

**Solution**:
1. Verify volume exists:
   ```sql
   SHOW VOLUMES IN migration_catalog.migration_schema;
   ```
2. Create if needed:
   ```sql
   CREATE VOLUME IF NOT EXISTS migration_catalog.migration_schema.migration_volume;
   ```
3. Update `VOLUME_BASE_PATH` in notebooks

#### Issue: "Authentication failed"

**OAuth**:
```bash
# Re-login
az login

# Or set environment variables
export ARM_CLIENT_ID="..."
export ARM_TENANT_ID="..."
export ARM_CLIENT_SECRET="..."
```

**Service Principal**:
1. Verify credentials in secrets:
   ```bash
   databricks secrets list --scope migration
   ```
2. Check service principal has workspace access
3. Verify Azure AD permissions

**PAT Tokens**:
1. Check token hasn't expired (User Settings → Access Tokens)
2. Generate new token if needed
3. Update secret:
   ```bash
   databricks secrets put --scope migration --key source-token
   ```

#### Issue: "No dashboards found"

**Solution**:
1. Verify `SOURCE_FOLDER_PATH` or `DASHBOARD_IDS` configuration
2. Check user has read access to dashboards
3. Try explicit dashboard IDs instead of folder path:
   ```python
   DASHBOARD_IDS = ["known_dashboard_id"]
   USE_FOLDER_PATH = False
   ```

#### Issue: "CSV mapping not found"

**Solution**:
1. Verify CSV file location:
   ```python
   dbutils.fs.ls(f"{VOLUME_BASE_PATH}/mappings/")
   ```
2. Re-run Notebook 1, Cell 6 to regenerate template
3. Upload CSV manually if needed

#### Issue: "Permissions not applied"

**Causes**:
- Principal (user/group) doesn't exist in target workspace
- Insufficient permissions to set ACLs
- Dashboard path incorrect

**Solutions**:
1. Set `SKIP_PERMISSIONS = True` to skip ACL restoration
2. Manually configure permissions in target workspace
3. Create missing principals in target workspace first
4. Verify dashboard paths are correct (manual workflow)

#### Issue: "Import failed - dashboard already exists"

**Solution**:
1. Delete or rename existing dashboard in target
2. Or modify target path in configuration
3. For automated workflow, set unique `TARGET_FOLDER_PATH`

#### Issue: "Transformation produced invalid JSON"

**Causes**:
- CSV mapping replaced critical JSON structure
- Regex pattern matched unintended strings

**Solutions**:
1. Review CSV mappings for overly broad patterns
2. Test with single dashboard first
3. Check transformed JSON manually:
   ```python
   content = read_volume_file(f"{TRANSFORMED_PATH}/dashboard_xxx.lvdash.json")
   json.loads(content)  # Should not raise error
   ```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Getting Help

1. **Check migration reports** in `{LOGS_PATH}/`
2. **Review cell outputs** for error messages
3. **Verify prerequisites** are met
4. **Test with dry run** mode first
5. **Test with single dashboard** before batch migration

---

## Best Practices

### Pre-Migration

1. **Test in Non-Production First**
   - Use development/staging workspaces
   - Validate with subset of dashboards
   - Verify transformations are correct

2. **Backup Source Dashboards**
   - Export originals before migration
   - Keep backups for rollback

3. **Document Mappings**
   - Maintain CSV changelog
   - Document rationale for mappings
   - Keep version controlled

4. **Validate CSV Mappings**
   - Test with 1-2 dashboards first
   - Review transformed JSON manually
   - Verify queries still work

### During Migration

1. **Use Dry Run Mode**
   ```python
   DRY_RUN = True
   ```
   - Test complete workflow
   - Validate without actual imports

2. **Monitor Progress**
   - Watch cell outputs for errors
   - Check volume for exported files
   - Review transformed JSON

3. **Start Small**
   - Migrate 1-2 dashboards first
   - Validate end-to-end
   - Scale to full migration

### Post-Migration

1. **Verify Dashboards**
   - Open each dashboard in target
   - Run queries to verify data loads
   - Test filters and parameters
   - Check visualizations render correctly

2. **Verify Permissions**
   - Confirm users can access dashboards
   - Check sharing settings
   - Validate group access

3. **Test End-to-End**
   - Refresh all dashboards
   - Test scheduled refreshes
   - Verify alerts (if any)

4. **Clean Up**
   - Archive volume artifacts if needed
   - Document what was migrated
   - Update documentation

5. **Monitor**
   - Watch for errors in first few days
   - Gather user feedback
   - Fix issues promptly

---

## FAQ

### General

**Q: Can I migrate to the same workspace?**  
A: Yes, but use different target folder path. Be careful with naming conflicts.

**Q: Do dashboards need to be published?**  
A: No, works with both draft and published dashboards.

**Q: Will dashboard history be preserved?**  
A: No, migration creates new dashboards without version history.

**Q: Can I migrate dashboards between clouds (AWS ↔ Azure)?**  
A: Yes, as long as both workspaces are accessible and target data sources exist.

### Authentication

**Q: Which auth method should I use?**  
A: OAuth is recommended for most use cases (easy, secure, no credential management).

**Q: Can I mix auth methods (OAuth for source, PAT for target)?**  
A: No, use the same method for both workspaces.

**Q: Do I need admin permissions?**  
A: No, only need read access to source dashboards and import permissions in target.

### CSV Mappings

**Q: Can one source table map to multiple target tables?**  
A: No, each source reference maps to one target reference.

**Q: What if I don't need to change some references?**  
A: Include identity mappings (old and new are the same) or omit from CSV (will remain unchanged).

**Q: Can I use wildcards in CSV?**  
A: No, but schema-level mappings (empty table column) act as wildcards for tables.

**Q: How do I map views?**  
A: Same as tables - use schema-level or table-level mappings.

### Permissions

**Q: What happens if a user doesn't exist in target?**  
A: Permission is skipped (best-effort). Create user first or manually set permissions later.

**Q: Are folder-level permissions migrated?**  
A: No, only dashboard-specific permissions are captured and restored.

**Q: Can I skip permissions entirely?**  
A: Yes, set `SKIP_PERMISSIONS = True` in Cell 1 of Notebook 3.

### Workflows

**Q: Can I run both manual and automated workflows?**  
A: Not needed - choose one. But you can run both if desired (just different dashboards).

**Q: Which workflow is better?**  
A: Automated for batch processing, manual for selective migration or review before import.

**Q: Can I pause and resume?**  
A: Yes! Volume artifacts persist. Re-run from any notebook as needed.

### Troubleshooting

**Q: Import failed with "already exists" error**  
A: Dashboard exists at target path. Delete/rename existing or change target path.

**Q: Queries fail after migration**  
A: Likely CSV mapping issue. Verify target catalog/schema/tables exist and mappings are correct.

**Q: Some dashboards imported but queries are empty**  
A: Transformation may have removed query content. Check CSV mappings and transformed JSON.

**Q: Permission restoration failed**  
A: Common if principals don't exist in target. Set `SKIP_PERMISSIONS = True` or create principals first.

---

## Appendix

### File Structure

```
/Volumes/.../dashboard_migration/
├── mappings/
│   └── catalog_schema_mapping.csv
├── exported/
│   ├── dashboard_abc123_Name.lvdash.json
│   ├── dashboard_abc123_Name_permissions.json
│   └── ...
├── transformed/
│   ├── dashboard_abc123_Name.lvdash.json
│   └── ...
└── logs/
    ├── manual_migration_report_TIMESTAMP.json
    ├── automated_migration_report_TIMESTAMP.json
    └── ...
```

### Notebook Cells Summary

#### Notebook 1: Setup & Configuration (8 cells)

1. Install libraries
2. Import libraries
3. Authentication configuration
4. Volume configuration
5. Create volume structure
6. Create CSV mapping template
7. Test workspace connectivity
8. Verify volume and CSV

#### Notebook 2: Export & Transform (6 cells)

1. Import configuration
2. Helper functions - Auth & Volume I/O
3. Dashboard export helpers
4. Transform helpers
5. **Export dashboards** (main execution)
6. **Transform dashboards** (main execution)

#### Notebook 3: Import & Migrate (9 cells)

1. Import configuration
2. Helper functions - Auth & Volume I/O
3. Import & permissions helpers
4. List transformed dashboards
5. **Manual: Import instructions**
6. **Manual: Apply ACLs**
7. **Manual: Generate report**
8. **Automated: Import dashboards**
9. **Automated: Generate report**

### Migration Report Schema

```json
{
  "timestamp": "20260128_153045",
  "workflow": "automated",
  "dry_run": false,
  "total": 5,
  "successful": 4,
  "failed": 1,
  "permissions_applied": 12,
  "permissions_skipped": 3,
  "dashboards": [
    {
      "dashboard_id": "abc123",
      "dashboard_name": "Sales Dashboard",
      "target_path": "/Workspace/Shared/Migrated_Dashboards/Sales Dashboard",
      "import_status": "success",
      "permissions_applied": 3,
      "permissions_skipped": 1,
      "error": ""
    }
  ]
}
```

---

## Support & Updates

For questions, issues, or feature requests:

1. Review this guide thoroughly
2. Check troubleshooting section
3. Review migration reports in logs folder
4. Test with dry run mode first

---

**Version**: 1.0  
**Last Updated**: January 2026  
**Compatible with**: Databricks Runtime 11.3 LTS+
