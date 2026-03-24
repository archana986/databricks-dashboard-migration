# Setup Guide

How to set up and use this Databricks Dashboard Migration toolkit for your own projects.

**Design:** This toolkit uses **two bundles**—a **source** bundle (run in the source workspace for inventory, export, and transform) and a **target** bundle (run in the target workspace for transfer and install). The catalog (and export volume) is bound to the source workspace for copy/transfer of files; installation runs in the target workspace. See [REQUIREMENTS.md](REQUIREMENTS.md) for the full requirements and assumptions.

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Databricks CLI** | v0.218.0+ ([install guide](https://docs.databricks.com/dev-tools/cli/install.html)) |
| **CLI profiles** | Two profiles in `~/.databrickscfg` -- one for source workspace, one for target |
| **Workspace access** | Admin or sufficient permissions on both source and target workspaces |
| **Same UC metastore** | Source and target catalogs must be on the same Unity Catalog metastore |
| **Export volume** | A UC volume in the **source** catalog for export artifacts |
| **Import volume** | A UC volume in the **target** catalog for import artifacts |
| **SQL warehouse** | A warehouse in the target workspace (ID or name) |
| **Mapping CSV** | Required if `transformation_enabled` is `"true"` (see Step 2b below) |
| **Service Principal** (recommended) | For cross-workspace deployment via SP OAuth |

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_ORG/dashboard-migration.git
cd dashboard-migration
```

After cloning, verify the structure and symlinks:

```
dashboard-migration/
  source/databricks.yml       # Source bundle (edit for source workspace)
  source/resources/           # Source job definitions
  source/src -> ../src        # Symlink to shared code (required)
  target/databricks.yml       # Target bundle (edit for target workspace)
  target/resources/           # Target job definitions (transfer + deploy)
  target/src -> ../src        # Symlink to shared code (required)
  src/notebooks/              # Migration notebooks (Steps 1-4, transfer, deploy)
  src/helpers/                # Python modules
  src/setup-guides/           # SP OAuth docs + secrets notebook
  REQUIREMENTS.md             # Migration need, two-bundle design, assumptions
  SETUP.md                    # This file
  README.md                   # Project overview
```

**Verify symlinks exist** (required for bundle deploy):

```bash
ls -la source/src target/src
# Both should be symlinks to ../src
# If missing, recreate: cd source && ln -sfn ../src src && cd ../target && ln -sfn ../src src
```

---

## Step 1b: Create Unity Catalog volumes and mapping CSV

### Export volume (required — create before running Inventory)

Run in the **source** workspace (SQL editor or notebook):

```sql
CREATE VOLUME IF NOT EXISTS <source_catalog>.<source_schema>.<export_volume>;
-- Example: CREATE VOLUME IF NOT EXISTS my_catalog.migration.dashboard_export;
```

All migration artifacts (inventory, exported JSONs, transformed JSONs, mapping CSV) are written here.

### Import volume (automatic — no action needed)

The **Transfer & Deploy** job creates this volume automatically via `CREATE VOLUME IF NOT EXISTS`. You do **not** need to create it manually. If you prefer to pre-create it:

```sql
-- Optional — run in the target workspace
CREATE VOLUME IF NOT EXISTS <target_catalog>.<target_schema>.<import_volume>;
-- Example: CREATE VOLUME IF NOT EXISTS my_target_catalog.migration_tgt.dashboard_import;
```

### Mapping CSV (required if `transformation_enabled` is `"true"`)

Create a CSV from the template (`catalog_schema_mapping_template.csv` in the repo root) and upload it to the export volume **before** running Export & Transform:

```bash
databricks fs cp catalog_schema_mapping.csv \
  dbfs:/Volumes/<source_catalog>/<source_schema>/<export_volume>/mappings/catalog_schema_mapping.csv \
  --profile <source-profile>
```

See Step 2b below for column reference and examples.

Both catalogs must be on the **same Unity Catalog metastore** for the transfer step to work.

---

## Step 2: Configure `databricks.yml`

Edit the `databricks.yml` file in each bundle folder directly. Each file has a clearly marked **EDIT HERE** section at the bottom where you replace placeholder values with your environment details.

**Default topology:** **different** source and target workspaces on a **shared Unity Catalog metastore** (see [REQUIREMENTS.md](REQUIREMENTS.md)).

Add the same **service principal** to **both** workspaces for automation; grant UC access on export and import volumes. See the **Service principal** section in [README.md](README.md) for grant SQL and `run_as` configuration.

### Source bundle (`source/databricks.yml`)

Open `source/databricks.yml` and edit the **EDIT HERE** section:

| Variable | What to enter | Example |
|---|---|---|
| `workspace.profile` | CLI profile name (from `databricks auth login`) | `my-source-profile` |
| `workspace.host` | Source workspace URL | `https://adb-123456.1.azuredatabricks.net` |
| `source_workspace_url` | Same as host (used by job parameters) | `https://adb-123456.1.azuredatabricks.net` |
| `catalog` | Source catalog name | `my_catalog` |
| `volume_base` | Export volume path: `/Volumes/<catalog>/<schema>/<volume>` | `/Volumes/my_catalog/my_schema/dashboard_export` |

### Target bundle (`target/databricks.yml`)

Open `target/databricks.yml` and edit the **EDIT HERE** section:

| Variable | What to enter | Example |
|---|---|---|
| `workspace.profile` | CLI profile name for target workspace | `my-target-profile` |
| `workspace.host` | Target workspace URL | `https://adb-789012.10.azuredatabricks.net` |
| `source_catalog` | Catalog that holds the **export** volume | `source_catalog` |
| `target_catalog` | Catalog that holds the **import** volume | `target_catalog` |
| `source_schema` | Schema in source catalog (export volume) | `default` |
| `target_schema` | Schema in target catalog (import volume) | `default` |
| `export_volume` | Export volume **name** in source catalog | `dashboard_export` |
| `import_volume` | Import volume **name** in target catalog | `dashboard_import` |
| `volume_base` | Full import volume path: `/Volumes/<target_catalog>/<target_schema>/<import_volume>` | `/Volumes/target_catalog/default/dashboard_import` |
| `warehouse_id` | SQL warehouse ID (find in SQL Warehouses > Connection details) | `"abc123def456"` |
| `target_parent_path` | Workspace folder for new dashboards | `/Shared/Migrated_Dashboards` |

---

## Step 3: Service principal (both workspaces) and optional OAuth secrets

Add the **same service principal** to **source and target** workspaces for automation. Grant **Unity Catalog** access to export/import volumes and the target warehouse (see the **Service principal** section in [README.md](README.md)).

**OAuth client ID + secret** in a secret scope are for notebooks or tools that use **machine-to-machine** auth (see [src/setup-guides/SP_OAUTH_SETUP.md](src/setup-guides/SP_OAUTH_SETUP.md)). The default **transfer + deploy** job path uses the **job run identity** in the target workspace, not cross-workspace OAuth.

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

After deploying the **source** bundle, open [Setup_Migration_Secrets.ipynb](src/setup-guides/Setup_Migration_Secrets.ipynb) in the Databricks workspace UI if you use SP OAuth from notebooks. Set the config cell and run the verification cells to confirm connectivity.

See [SP_OAUTH_SETUP.md](src/setup-guides/SP_OAUTH_SETUP.md) for the full detailed guide.

---

## Step 4: Deploy the source bundle (source workspace)

From the repo root:

```bash
cd source
databricks bundle validate
databricks bundle deploy --profile <source-profile>
```

This syncs notebooks and helpers into the **source** workspace and registers **two** jobs: `[Src] Dashboard Inventory` and `[Src] Dashboard Export & Transform`.

---

## Step 5: Run the migration (source, then target)

### 5a. Source workspace — Steps 1–3

**Step 1 — Generate inventory**

```bash
cd source
databricks bundle run src_dashboard_inventory --profile <source-profile>
```

**Step 2 — Review and approve (UI)**  
Open [Bundle_02_Review_and_Approve_Inventory.ipynb](src/notebooks/Bundle_02_Review_and_Approve_Inventory.ipynb) in the **source** workspace UI. Review the dashboard list, filter out any you don't want to migrate, and type **CONFIRM** when prompted. The notebook saves the approved list as:

```
<volume_base>/dashboard_inventory_approved/inventory_approved.csv
```

The Export & Transform job reads this exact file. Do not rename it.

**Step 2b — Upload mapping CSV** (required if `transformation_enabled` is `"true"`)

Create a mapping CSV from the template (`catalog_schema_mapping_template.csv` in the repo root) with your old and new catalog/schema names. Upload it to the export volume:

```bash
databricks fs cp catalog_schema_mapping.csv \
  dbfs:/Volumes/<source_catalog>/<source_schema>/<export_volume>/mappings/catalog_schema_mapping.csv \
  --profile <source-profile>
```

A template is included in the repo root: `catalog_schema_mapping_template.csv`.

**Column reference:**

| Column | Required | Description |
|--------|----------|-------------|
| `old_catalog` | Yes | Source catalog name to find in dashboard SQL |
| `old_schema` | Yes | Source schema name to find |
| `old_table` | No | Specific table name (leave empty to match all tables in the schema) |
| `new_catalog` | Yes | Target catalog name to replace with |
| `new_schema` | Yes | Target schema name to replace with |
| `new_table` | No | New table name (leave empty to keep original table name) |
| `old_volume` | No | Source volume name to replace (if dashboard SQL references volumes) |
| `new_volume` | No | Target volume name to replace with |

**Example 1 — Remap all tables from one catalog/schema to another:**

```csv
old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
my_source_catalog,my_schema,,my_target_catalog,my_target_schema,,,
```

**Example 2 — Multiple schemas with specific table renames:**

```csv
old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
dev_catalog,bronze_layer,,prod_catalog,gold_layer,,,
staging_cat,raw_data,events,prod_catalog,curated_data,events,,
staging_cat,raw_data,clicks,prod_catalog,analytics,click_events,,
```

If you do **not** need catalog/schema rewriting in dashboard SQL, set `transformation_enabled: "false"` in your local config and skip this step.

**Step 3 — Export and transform**

```bash
databricks bundle run src_dashboard_export_transform --profile <source-profile>
```

Artifacts are written under your configured **export volume** (for example `exported/`, `transformed/`, `dashboard_inventory_approved/`, and consolidated CSVs where applicable).

### 5b. Target workspace — transfer and deploy

**Deploy the target bundle** (separate host and profile):

```bash
cd ../target
databricks bundle validate
databricks bundle deploy --profile <target-profile>
```

**Run transfer + deploy** (one job, two tasks):

```bash
databricks bundle run tgt_dashboard_register --profile <target-profile>
```

This copies data from the **source export volume** to the **target import volume** (same metastore), then creates dashboards under `target_parent_path` and applies permissions/schedules per job parameters.

> **Optional / alternate flows:** Some forks include `Bundle_04_*` notebooks or shell scripts for asset-bundle-based publish paths. This repository’s **default** Databricks Asset Bundle definitions are the jobs above.

---

## Verification Checklist

After setup or any structural change:

1. `cd source && databricks bundle validate` and `cd target && databricks bundle validate`
2. Deploy each bundle with the correct profile (`<source-profile>` vs `<target-profile>`)
3. Run `src_dashboard_inventory`, then `src_dashboard_export_transform` on the source side — confirm no `ModuleNotFoundError`
4. Run `tgt_dashboard_register` on the target side — confirm transfer and deploy tasks succeed
5. Open [Bundle_02](src/notebooks/Bundle_02_Review_and_Approve_Inventory.ipynb) in the source UI — run path cell and helper imports if you run it ad hoc
6. If using SP OAuth from notebooks, open [Setup_Migration_Secrets.ipynb](src/setup-guides/Setup_Migration_Secrets.ipynb) and run verify / connection cells

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

