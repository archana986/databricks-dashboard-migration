# Lakeview Dashboard Migration - Volume-Based Approach

A complete file-based migration solution for Databricks Lakeview dashboards using Databricks volumes for storage and CSV-based catalog/schema/table remapping.

## Overview

This solution enables you to:
- Export Lakeview dashboards as `.lvdash.json` files to Databricks volumes
- Transform catalog/schema/table/volume references using CSV mappings
- Capture and restore dashboard permissions (best effort)
- Import transformed dashboards to a target workspace
- Generate detailed migration reports

## Architecture

```
Source Workspace → Export → Volume → Transform → Volume → Import → Target Workspace
                    ↓                    ↓                   ↓
              Permissions.json    CSV Mappings      Restore Permissions
```

## Prerequisites

1. **Databricks Workspaces**: Access to both source and target workspaces
2. **Authentication**: One of the following:
   - **OAuth/Azure AD** (RECOMMENDED) - Azure CLI or environment variables
   - **Service Principal** - For production/automation
   - **PAT Tokens** - For quick tests
3. **Databricks Volume**: A volume accessible from both source and target (or separate volumes)
4. **Python Libraries**: `databricks-sdk`, `pandas`

## Setup Instructions

### Step 1: Create Databricks Volume

Create a volume in Unity Catalog to store migration artifacts:

```sql
CREATE VOLUME IF NOT EXISTS migration_cat.migration_schema.migration_vol;
```

### Step 2: Set Up Volume Directory Structure

The notebook will automatically create these directories, but you can pre-create them:

```
/Volumes/migration_cat/migration_schema/migration_vol/dashboard_migration/
├── mappings/              # CSV mapping files
├── exported/              # Exported .lvdash.json files
├── transformed/           # Transformed .lvdash.json files
└── logs/                  # Migration reports
```

### Step 3: Create Mapping CSV File

1. Copy `catalog_schema_mapping_template.csv` to your volume:
   ```
   /Volumes/migration_cat/migration_schema/migration_vol/dashboard_migration/mappings/catalog_schema_mapping.csv
   ```

2. Edit the CSV file with your actual mappings:
   ```csv
   old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
   dev_catalog,bronze_layer,customers,prod_catalog,gold_layer,customers,dev_files,prod_files
   dev_catalog,bronze_layer,orders,prod_catalog,gold_layer,orders,dev_files,prod_files
   ```

   **CSV Column Definitions:**
   - `old_catalog`: Source catalog name
   - `old_schema`: Source schema name
   - `old_table`: Source table name (can be empty for schema-level mapping)
   - `new_catalog`: Target catalog name
   - `new_schema`: Target schema name
   - `new_table`: Target table name (can be empty for schema-level mapping)
   - `old_volume`: Source volume name (optional, for volume path replacements)
   - `new_volume`: Target volume name (optional, for volume path replacements)

### Step 4: Choose and Configure Authentication Method

The notebook supports three authentication methods. **OAuth is recommended for most use cases.**

#### OAuth (Azure AD) - RECOMMENDED

**Best for:** Most scenarios - Interactive use, development, temporary migrations, general use

**Advantages:**
- Easy setup with Azure CLI
- Secure with Azure-managed tokens
- No credential management needed
- Good for interactive development
- Recommended by Databricks

**Setup:**
1. Install Azure CLI and login: `az login`
2. Or set environment variables:
   ```bash
   export ARM_CLIENT_ID="your-client-id"
   export ARM_TENANT_ID="your-tenant-id"
   export ARM_CLIENT_SECRET="your-client-secret"
   ```
3. In Cell 1, set: `AUTH_METHOD = "oauth"` (this is the default)

#### Service Principal

**Best for:** Production, automated pipelines, CI/CD, long-running jobs

**Advantages:**
- No token expiration concerns
- Better audit trail with service principal identity
- Fine-grained permissions via Azure AD
- Suitable for automated workflows

**Setup:**
1. Create service principals in Azure AD for source and target workspaces
2. Grant appropriate permissions in Databricks workspaces
3. Store credentials in Databricks secrets:
   ```bash
   # Create secret scope (one-time setup)
   databricks secrets create-scope migration
   
   # Store service principal credentials
   databricks secrets put --scope migration --key source-sp-client-id
   databricks secrets put --scope migration --key source-sp-secret
   databricks secrets put --scope migration --key source-sp-tenant
   databricks secrets put --scope migration --key target-sp-client-id
   databricks secrets put --scope migration --key target-sp-secret
   databricks secrets put --scope migration --key target-sp-tenant
   ```
4. In Cell 1, set: `AUTH_METHOD = "service_principal"`

#### PAT Tokens

**Best for:** Quick tests, development environments, legacy systems

**Considerations:**
- Tokens expire and require rotation
- Simpler setup for testing
- Works across all Databricks deployments

**Setup:**
1. Generate PAT tokens in both workspaces (User Settings → Access Tokens)
2. Store in Databricks secrets:
   ```bash
   databricks secrets put --scope migration --key source-token
   databricks secrets put --scope migration --key target-token
   ```
3. In Cell 1, set: `AUTH_METHOD = "pat"`

**Alternative for testing only:**
You can hardcode tokens directly in the notebook (Cell 1), but this is not recommended for production.

#### Comparison Table

| Method | Setup Complexity | Security | Best Use Case | Token Expiration | Recommended? |
|--------|-----------------|----------|---------------|------------------|--------------|
| **OAuth** | Low | High | Most scenarios, Interactive, Development | Managed by Azure | **YES** |
| Service Principal | Medium | High | Production, Automation | No expiration | For automation |
| PAT Token | Low | Medium | Quick Tests | Yes (needs rotation) | No |

### Step 5: Configure the Notebook

Import `lakeview_migration_volume_based.ipynb` to Databricks and update Cell 1 configuration:

```python
# Authentication Method (RECOMMENDED: oauth)
AUTH_METHOD = "oauth"  # Options: "oauth", "service_principal", "pat"

# Workspace URLs
SOURCE_WORKSPACE_URL = "https://your-source-workspace.cloud.databricks.com"
TARGET_WORKSPACE_URL = "https://your-target-workspace.cloud.databricks.com"

# Volume Paths
VOLUME_BASE_PATH = "/Volumes/migration_cat/migration_schema/migration_vol/dashboard_migration"
MAPPING_CSV_PATH = f"{VOLUME_BASE_PATH}/mappings/catalog_schema_mapping.csv"

# Dashboard Selection - Choose one approach:

# Option 1: Explicit list of dashboard IDs
DASHBOARD_IDS = [
    "abc123def456",
    "ghi789jkl012",
]
USE_FOLDER_PATH = False

# Option 2: Export all dashboards from a folder
SOURCE_FOLDER_PATH = "/Workspace/Shared/Dashboards"
USE_FOLDER_PATH = True

# Target Configuration
TARGET_FOLDER_PATH = "/Workspace/Shared/Migrated_Dashboards"
```

## Usage

The notebook supports two migration workflows:

### Workflow 1: Manual Import (Cells 8-10)

Best for: Users who want to review dashboards before importing, or have specific import requirements.

1. **Cells 1-7**: Configure, export, and transform dashboards (shared steps)
2. **Cell 8**: View manual import instructions and download transformed files
3. Manually import dashboards via Databricks UI
4. **Cell 9**: Apply ACLs to manually imported dashboards
5. **Cell 10**: Generate manual workflow report

### Workflow 2: Automated Import (Cells 11-12)

Best for: Automated migrations, batch processing, CI/CD pipelines.

1. **Cells 1-7**: Configure, export, and transform dashboards (shared steps)
2. **Cell 11**: Automatically import dashboards to target workspace
3. **Cell 12**: Generate automated workflow report

### Shared Steps (Both Workflows)

Execute these cells first:

1. **Cell 1**: Configuration - Set auth method, workspace URLs, dashboard selection
2. **Cells 2-5**: Load helper functions
3. **Cell 6**: Export dashboards from source workspace
4. **Cell 7**: Transform dashboards using CSV mappings

Then choose either Manual Workflow (Cells 8-10) or Automated Workflow (Cells 11-12)

### Option C: Dry Run Mode

Test the migration without actually importing:

```python
# In Cell 1, set:
DRY_RUN = True
```

This will execute all steps except the actual import to the target workspace.

## Configuration Options

### Cell 1 Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `SOURCE_WORKSPACE_URL` | Source workspace URL | Required |
| `SOURCE_PAT_TOKEN` | Source PAT token | Required |
| `TARGET_WORKSPACE_URL` | Target workspace URL | Required |
| `TARGET_PAT_TOKEN` | Target PAT token | Required |
| `VOLUME_BASE_PATH` | Volume base path for migration | Required |
| `DASHBOARD_IDS` | List of dashboard IDs to migrate | `[]` |
| `SOURCE_FOLDER_PATH` | Folder path to discover dashboards | `None` |
| `USE_FOLDER_PATH` | Use folder discovery vs explicit IDs | `False` |
| `TARGET_FOLDER_PATH` | Target folder for imported dashboards | Required |
| `VALIDATE_QUERIES` | Validate queries before import | `False` |
| `SKIP_PERMISSIONS` | Skip permissions migration | `False` |
| `DRY_RUN` | Test mode without actual import | `False` |

## Understanding the Migration Workflow

### Phase 1: Export

**What happens:**
- Connects to source workspace using PAT token
- Exports each dashboard as `.lvdash.json` file
- Captures dashboard permissions as separate JSON file
- Saves both to volume `exported/` directory

**Output files:**
```
exported/
├── dashboard_abc123_Sales_Dashboard.lvdash.json
├── dashboard_abc123_Sales_Dashboard_permissions.json
├── dashboard_def456_Marketing_KPIs.lvdash.json
└── dashboard_def456_Marketing_KPIs_permissions.json
```

### Phase 2: Transform

**What happens:**
- Loads CSV mapping file
- Reads each exported `.lvdash.json` file
- Recursively walks JSON structure to find:
  - SQL queries with `catalog.schema.table` references
  - Volume paths like `/Volumes/cat/schema/vol/`
- Replaces old references with new ones using regex patterns
- Saves transformed files to volume `transformed/` directory

**Transformation Examples:**

Input SQL:
```sql
SELECT * FROM dev_catalog.bronze_layer.customers
```

With mapping: `dev_catalog.bronze_layer → prod_catalog.gold_layer`

Output SQL:
```sql
SELECT * FROM prod_catalog.gold_layer.customers
```

### Phase 3: Import

**What happens:**
- Connects to target workspace using PAT token
- Reads each transformed `.lvdash.json` file
- Imports to target workspace at specified folder path
- Loads corresponding permissions file
- Attempts to apply permissions (best effort)
- Records results

**Permission Handling:**
- Tries to apply each permission from the source
- If a principal (user/group) doesn't exist in target, skips it with a warning
- Tracks applied vs skipped permissions

### Phase 4: Reporting

**What happens:**
- Combines results from all phases
- Creates summary DataFrame with:
  - Export, transform, and import status for each dashboard
  - Permissions applied/skipped counts
  - Error messages if any
- Saves detailed JSON report to volume `logs/` directory
- Displays summary table

## Migration Report

After migration, you'll see a summary table:

| source_dashboard_id | dashboard_name | export | transform | import | target_path | perms_ok | perms_skip | error |
|---------------------|----------------|--------|-----------|--------|-------------|----------|------------|-------|
| abc123def456 | Sales Dashboard | ✅ | ✅ | ✅ | /Workspace/.../Sales_Dashboard | 3 | 1 | |
| ghi789jkl012 | Marketing KPIs | ✅ | ✅ | ✅ | /Workspace/.../Marketing_KPIs | 5 | 0 | |

**Column Definitions:**
- **export**: Export status (✅ success, ❌ failed, ⊘ skipped)
- **transform**: Transform status
- **import**: Import status
- **target_path**: Path in target workspace
- **perms_ok**: Number of permissions successfully applied
- **perms_skip**: Number of permissions skipped (e.g., principal doesn't exist)
- **error**: Error message if any step failed

## Troubleshooting

### Common Issues

#### 1. "databricks-sdk not installed"

**Solution:**
```python
%pip install databricks-sdk
dbutils.library.restartPython()
```

#### 2. "Failed to read volume file"

**Possible causes:**
- Volume path is incorrect
- Volume doesn't exist
- Insufficient permissions to access volume

**Solution:**
- Verify volume exists: `dbutils.fs.ls("/Volumes/catalog/schema/volume/")`
- Check permissions in Unity Catalog
- Ensure volume path in configuration matches actual volume

#### 3. "No dashboards to export"

**Possible causes:**
- `DASHBOARD_IDS` list is empty and `USE_FOLDER_PATH` is False
- Folder path doesn't contain dashboards
- Dashboard IDs are incorrect

**Solution:**
- Verify dashboard IDs or folder path
- Check that dashboards exist in source workspace
- Enable logging to see discovery process

#### 4. "Could not retrieve permissions"

**Possible causes:**
- PAT token lacks permission to read ACLs
- Dashboard path format is incorrect
- Permissions API not available for dashboard type

**Solution:**
- Verify PAT token has appropriate permissions
- Set `SKIP_PERMISSIONS = True` to proceed without permissions
- Check Databricks workspace admin settings

#### 5. "Import failed: Dashboard already exists"

**Solution:**
- Change `TARGET_FOLDER_PATH` to a different location
- Manually delete existing dashboards in target
- Modify dashboard names in transformation step

#### 6. "CSV mapping not applied"

**Possible causes:**
- CSV file path is incorrect
- CSV format doesn't match expected schema
- Catalog/schema names don't match exactly (case-sensitive)

**Solution:**
- Verify CSV file exists at specified path
- Check CSV format matches template
- Ensure exact case match for catalog/schema names
- Review transformation output for applied replacements

### Debug Mode

To see detailed logs during execution, add print statements or enable verbose logging:

```python
# In any cell, add:
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Advanced Usage

### Custom Transformation Logic

To add custom transformation logic beyond CSV mappings, modify Cell 4 `transform_dashboard_json` function:

```python
def custom_transform(dashboard_json: Dict[str, Any]) -> Dict[str, Any]:
    # Add your custom logic here
    # Example: Replace warehouse IDs
    if "warehouse_id" in dashboard_json:
        dashboard_json["warehouse_id"] = "new_warehouse_id"
    return dashboard_json
```

### Partial Migration

To migrate only specific dashboards from a folder:

```python
# In Cell 1:
SOURCE_FOLDER_PATH = "/Workspace/Shared/Dashboards"
USE_FOLDER_PATH = True

# In Cell 6, after discovering dashboards, filter the list:
dashboards_to_export = [d for d in discovered if d["name"] in ["Dashboard1", "Dashboard2"]]
```

### Principal Mapping

To map principals (users/groups) between workspaces, modify Cell 5 `apply_dashboard_permissions`:

```python
PRINCIPAL_MAPPING = {
    "old_user@company.com": "new_user@company.com",
    "old_group": "new_group"
}

# In apply_dashboard_permissions, before applying:
if principal_id in PRINCIPAL_MAPPING:
    principal_id = PRINCIPAL_MAPPING[principal_id]
```

## Security Best Practices

1. **Never hardcode PAT tokens** in notebooks committed to version control
2. **Use Databricks Secrets** for token storage
3. **Limit PAT token permissions** to minimum required:
   - Source: Read dashboards, read permissions
   - Target: Create dashboards, manage permissions
4. **Restrict volume access** to authorized users only
5. **Review permissions** before applying in target workspace
6. **Use service principal tokens** instead of user PAT tokens for production

## File Structure

```
Customer-Work/Catalog Migration/
├── lakeview_migration_volume_based.ipynb   # Main Databricks notebook
├── catalog_schema_mapping_template.csv     # CSV template
├── README_Volume_Migration.md              # This file
└── Lakeview Dashboard Migration Playbook.txt  # Original playbook reference
```

## Limitations

1. **Dashboard Types**: Designed for Lakeview dashboards; may not work with legacy dashboards
2. **Permissions**: Best-effort restoration; inherited permissions may not transfer
3. **Principals**: Assumes principals exist in both workspaces; skips non-existent ones
4. **Workspace Objects**: Does not migrate linked notebooks, queries, or alerts
5. **Dashboard Schedules**: Does not migrate dashboard schedules or subscriptions
6. **Custom Widgets**: May require manual adjustment if using custom visualizations

## Support & Contribution

For issues or questions:
1. Review this README and troubleshooting section
2. Check Databricks documentation for API changes
3. Verify configuration and prerequisites
4. Review notebook cell outputs for specific error messages

## Version History

- **v1.0** (2026-01-28): Initial release with volume-based migration

## References

- [Databricks SDK for Python](https://docs.databricks.com/dev-tools/sdk-python.html)
- [Databricks Volumes](https://docs.databricks.com/sql/language-manual/sql-ref-volumes.html)
- [Lakeview Dashboard API](https://docs.databricks.com/api/workspace/lakeview)
- [Databricks Secrets](https://docs.databricks.com/security/secrets/index.html)
