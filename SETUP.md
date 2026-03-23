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
  source/databricks.yml       # Source bundle (edit for source workspace)
  source/resources/           # Source job definitions
  target/databricks.yml       # Target bundle (edit for target workspace)
  target/resources/           # Target job definitions (transfer + deploy)
  src/notebooks/              # Migration notebooks (Steps 1-4, transfer, deploy)
  src/helpers/                # Python modules
  src/setup-guides/           # SP OAuth docs + secrets notebook
  REQUIREMENTS.md             # Migration need, two-bundle design, assumptions
  SETUP.md                    # This file
  README.md                   # Project overview
```

---

## Step 2: Configure `databricks.yml`

Open `databricks.yml` and update the target you plan to use (e.g. `dev` or `azure-test`).

### Local overrides (recommended)

To avoid committing workspace URLs and catalog names, copy the examples and edit the generated `databricks.local.yml` files (gitignored):

- `source/databricks.local.yml.example` → `source/databricks.local.yml`
- `target/databricks.local.yml.example` → `target/databricks.local.yml`

**Default topology:** **different** source and target workspaces on a **shared Unity Catalog metastore** (see [REQUIREMENTS.md](REQUIREMENTS.md)). Optional single-workspace test notes: [docs/SINGLE_WORKSPACE_OPTIONAL.md](docs/SINGLE_WORKSPACE_OPTIONAL.md).

Add the same **service principal** to **both** workspaces for automation; grant UC access on export and import volumes. See [docs/TARGET_JOB_RUN_AS_SP.md](docs/TARGET_JOB_RUN_AS_SP.md) for `run_as` and grants.

### Source bundle (`source/databricks.yml`)

| Variable | What to enter | Example |
|---|---|---|
| `workspace.host` | Source workspace URL | `https://adb-123456.1.azuredatabricks.net` |
| `catalog` | Source catalog name | `my_catalog` |
| `volume_base` | UC **export** volume path for artifacts | `/Volumes/my_catalog/my_schema/dashboard_migration` |
| `source_workspace_url` | Source workspace URL (display / parameters) | `https://adb-123456.1.azuredatabricks.net` |

### Target bundle (`target/databricks.yml`)

| Variable | What to enter | Example |
|---|---|---|
| `workspace.host` | Target workspace URL | `https://adb-789012.10.azuredatabricks.net` |
| `source_catalog` | Catalog that holds the **export** volume | `source_catalog` |
| `target_catalog` | Catalog that holds the **import** volume | `target_catalog` |
| `schema` | Schema containing both volumes | `default` |
| `export_volume` / `import_volume` | Volume **names** (transfer task) | e.g. `dashboard_migration` or distinct export/import names |
| `volume_base` | Full import volume path | `/Volumes/<target_catalog>/<schema>/<import_volume>` |
| `target_parent_path` | Workspace folder for new dashboards | `/Shared/Migrated_Dashboards` |
| `warehouse_id` or `warehouse_name` | Target SQL warehouse | ID or display name |

### Example: source `targets.default` snippet

```yaml
targets:
  default:
    workspace:
      host: https://adb-123456.1.azuredatabricks.net
    variables:
      source_workspace_url: https://adb-123456.1.azuredatabricks.net
      catalog: my_catalog
      volume_base: /Volumes/my_catalog/my_schema/dashboard_migration_export
```

> **Important:** Do NOT commit your real URLs, catalog names, or warehouse IDs. Keep these changes local only.

---

## Step 3: Service principal (both workspaces) and optional OAuth secrets

Add the **same service principal** to **source and target** workspaces for automation. Grant **Unity Catalog** access to export/import volumes and the target warehouse (see [docs/TARGET_JOB_RUN_AS_SP.md](docs/TARGET_JOB_RUN_AS_SP.md)).

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

This syncs notebooks and helpers into the **source** workspace and registers **two** jobs: `src_dashboard_inventory` and `src_dashboard_export_transform`.

---

## Step 5: Run the migration (source, then target)

### 5a. Source workspace — Steps 1–3

**Step 1 — Generate inventory**

```bash
cd source
databricks bundle run src_dashboard_inventory --profile <source-profile>
```

**Step 2 — Review and approve (UI)**  
Open [Bundle_02_Review_and_Approve_Inventory.ipynb](src/notebooks/Bundle_02_Review_and_Approve_Inventory.ipynb) in the **source** workspace. Review dashboards, apply filters, type **CONFIRM** to save the approved inventory.

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

---

## Git Guidelines

- **Never commit** real workspace URLs, catalog names, warehouse IDs, or secrets.
- The committed `databricks.yml` uses placeholders (e.g. `YOUR-SOURCE-WORKSPACE`). Update locally only.
- Keep `auth_method`, `sp_secret_scope`, and generic config names in the repo (e.g. `migration_secrets`).
- Secret scope values (`sp_client_id`, `sp_client_secret`) are stored via CLI, never in code.
