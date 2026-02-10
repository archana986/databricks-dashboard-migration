# Setup Guide

How to set up and use this Databricks Dashboard Migration toolkit for your own projects.

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Databricks CLI** | v0.218.0+ ([install guide](https://docs.databricks.com/dev-tools/cli/install.html)) |
| **CLI profiles** | Two profiles in `~/.databrickscfg` -- one for source workspace, one for target |
| **Workspace access** | Admin or sufficient permissions on both source and target workspaces |
| **Unity Catalog volume** | A volume for migration artifacts (e.g. `/Volumes/<catalog>/<schema>/dashboard_migration`) |
| **SQL warehouse** | A warehouse in the target workspace (ID or name) |
| **Service Principal** (recommended) | For Step 4 cross-workspace deployment via SP OAuth |

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/archana-krishnamurthy_data/dashboard-migration.git
cd dashboard-migration
```

After cloning, verify the structure:

```
dashboard-migration/
  databricks.yml              # Bundle config: variables, targets (edit this)
  resources/migration_jobs.yml # Job definitions (no edits needed)
  src/notebooks/              # Migration notebooks (Steps 1-4)
  src/helpers/                # Python modules
  src/setup-guides/           # SP OAuth docs + secrets notebook
  SETUP.md                    # This file
  README.md                   # Project overview
```

---

## Step 2: Configure `databricks.yml`

Open `databricks.yml` and update the target you plan to use (e.g. `dev` or `azure-test`).

### Required variables to set

| Variable | What to enter | Example |
|---|---|---|
| `workspace.host` | Source workspace URL | `https://adb-123456.1.azuredatabricks.net` |
| `catalog` | Source catalog name | `my_catalog` |
| `volume_base` | UC volume path for artifacts | `/Volumes/my_catalog/my_schema/dashboard_migration` |
| `source_workspace_url` | Source workspace URL | `https://adb-123456.1.azuredatabricks.net` |
| `target_workspace_url` | Target workspace URL | `https://adb-789012.10.azuredatabricks.net` |
| `warehouse_id` or `warehouse_name` | Target SQL warehouse | `cb4a76f3c5e28557` or `My Warehouse` |
| `auth_method` | `"pat"` or `"sp_oauth"` | `"sp_oauth"` (recommended) |
| `node_type_id` | VM type for standard clusters | `Standard_DS3_v2` (Azure), `i3.xlarge` (AWS), `n1-standard-4` (GCP) |

> **Important:** The default `node_type_id` is `i3.xlarge` (AWS). You **must** override it for Azure or GCP workspaces, otherwise `bundle deploy` will fail.

### Example: updating the `dev` target (Azure)

```yaml
targets:
  dev:
    mode: development
    workspace:
      host: https://adb-123456.1.azuredatabricks.net
    variables:
      catalog: my_catalog
      volume_base: /Volumes/my_catalog/my_schema/dashboard_migration
      source_workspace_url: https://adb-123456.1.azuredatabricks.net
      target_workspace_url: https://adb-789012.10.azuredatabricks.net
      warehouse_id: "cb4a76f3c5e28557"
      auth_method: "sp_oauth"
      node_type_id: "Standard_DS3_v2"   # Azure -- required override
      dry_run_mode: "true"
```

> **Important:** Do NOT commit your real URLs, catalog names, or warehouse IDs. Keep these changes local only.

---

## Step 3: Upload Catalog/Schema Mapping CSV

Step 3 (Export & Transform) uses a mapping CSV to remap catalog, schema, and table references when transforming dashboards for the target workspace. You **must** upload this file before running Export & Transform.

### CSV location

```
<volume_base>/mappings/catalog_schema_mapping.csv
```

For example: `/Volumes/my_catalog/my_schema/dashboard_migration/mappings/catalog_schema_mapping.csv`

### CSV format

| Column | Required | Description |
|---|---|---|
| `old_catalog` | Yes | Source catalog name |
| `old_schema` | Yes | Source schema name |
| `old_table` | No | Source table name (leave blank for schema-level mapping) |
| `new_catalog` | Yes | Target catalog name |
| `new_schema` | Yes | Target schema name |
| `new_table` | No | Target table name (leave blank for schema-level mapping) |
| `old_volume` | No | Source volume path to remap |
| `new_volume` | No | Target volume path |

### Example: schema-level mapping (most common)

```csv
old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
my_source_catalog,my_source_schema,,my_target_catalog,my_target_schema,,,
```

### Example: table-level mapping

```csv
old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
prod_catalog,analytics,daily_sales,dev_catalog,analytics,daily_sales,,,
prod_catalog,analytics,customers,dev_catalog,analytics,customers,,,
```

### How to upload

```bash
# Create the mappings directory in the volume
databricks fs mkdir dbfs:<volume_base>/mappings --profile <source-profile>

# Upload your CSV
databricks fs cp ./catalog_schema_mapping.csv dbfs:<volume_base>/mappings/catalog_schema_mapping.csv --profile <source-profile>
```

> **Tip:** If source and target use the same catalog/schema (e.g. same-workspace test), create a single row with identical old/new values. The transformation will be a no-op but the file must still exist.

---

## Step 4: Service Principal OAuth Setup (Recommended)

SP OAuth is required when `auth_method: "sp_oauth"`. This is the recommended auth method for cross-workspace deployment in the Generate & Deploy step.

### 3a. Create a Service Principal

1. Go to **Databricks Account Console** > **User management** > **Service principals**.
2. Click **Add service principal** and give it a name (e.g. `migration-sp`).
3. Note the **Application (Client) ID**.

### 3b. Add SP to Both Workspaces

1. In Account Console, go to **Workspaces**.
2. For each workspace (source and target):
   - Click the workspace > **Permissions** > **Add** > select the SP.
   - Grant appropriate permissions (workspace access at minimum).

### 3c. Generate an OAuth Secret

1. In Account Console > **Service principals** > select your SP.
2. Go to **Secrets** > **Generate secret**.
3. Copy the **secret value** immediately (it is shown only once).

### 3d. Store Credentials in Databricks Secret Scope

Run these commands from your local machine:

```bash
# Create the secret scope on the source workspace
databricks secrets create-scope migration_secrets --profile <source-profile>

# Store the SP Application (Client) ID -- paste when prompted
databricks secrets put-secret migration_secrets sp_client_id --profile <source-profile>

# Store the SP OAuth secret -- paste when prompted
databricks secrets put-secret migration_secrets sp_client_secret --profile <source-profile>
```

### 3e. Verify (Optional)

After deploying the bundle (Step 4), open `src/setup-guides/Setup_Migration_Secrets.ipynb` in the Databricks workspace UI. Set the config cell and run the verification cells to confirm connectivity.

See `src/setup-guides/SP_OAUTH_SETUP.md` for the full detailed guide.

---

## Step 5: Deploy the Bundle

```bash
databricks bundle deploy -t <target> --profile <source-profile>
```

This syncs all notebooks, helpers, and setup guides to the workspace and creates the three migration jobs.

---

## Step 6: Run the Migration

### Step 1 -- Generate Inventory

```bash
databricks bundle run inventory_generation -t <target> --profile <source-profile>
```

### Step 2 -- Manual Review and Approval (UI)

Open `src/notebooks/Bundle_02_Review_and_Approve_Inventory.ipynb` in the Databricks workspace. Review dashboards, apply filters, type CONFIRM to save the approved inventory.

### Step 3 -- Export and Transform

```bash
databricks bundle run export_transform -t <target> --profile <source-profile>
```

### Step 4 -- Generate and Deploy

```bash
# Dry run first (safe default -- preview only, no resources created)
databricks bundle run generate_deploy -t <target> --profile <source-profile>

# Live deploy (when ready)
databricks bundle run generate_deploy -t <target> --profile <source-profile> \
  --var="dry_run_mode=false"
```

---

## Verification Checklist

After setup or any structural change, verify with:

1. `databricks bundle validate -t <target>` -- catches YAML/path errors
2. `databricks bundle deploy -t <target> --profile <source-profile>` -- syncs code to workspace
3. Run each job (inventory_generation, export_transform, generate_deploy) -- confirm no `ModuleNotFoundError`
4. Open `Bundle_02` in UI -- run path cell + cells that import helpers
5. Open `Setup_Migration_Secrets.ipynb` in UI -- run config, path, verify, test connection

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'helpers'` | `sys.path` missing `src/` | Run the path-resolution cell at the top of the notebook |
| `Missing secrets: ['sp_client_id', 'sp_client_secret']` | Secrets not stored in scope | Run `databricks secrets put-secret` for both keys via CLI |
| `Secret scope does not exist` | Scope not created | Run `databricks secrets create-scope migration_secrets --profile <source-profile>` |
| `401 Unauthorized` on target | SP OAuth secret invalid or expired | Regenerate in Account Console, re-store via CLI |
| `403 Forbidden` on target | SP lacks workspace permissions | Add SP to target workspace in Account Console |
| `Connection to wrong workspace` | Wrong URL in yml | Verify `target_workspace_url` matches the target |

---

## Git Guidelines

- **Never commit** real workspace URLs, catalog names, warehouse IDs, or secrets.
- The committed `databricks.yml` uses placeholders (e.g. `YOUR-SOURCE-WORKSPACE`). Update locally only.
- Keep `auth_method`, `sp_secret_scope`, and generic config names in the repo (e.g. `migration_secrets`).
- Secret scope values (`sp_client_id`, `sp_client_secret`) are stored via CLI, never in code.
