# Databricks Dashboard Migration Toolkit

Migrate Databricks Lakeview dashboards across workspaces with catalog/schema transformations, permission and schedule migration, and cross-workspace authentication via Service Principal OAuth or PAT tokens. Fully deployable with Databricks Asset Bundles (DABs).

## Project Structure

```
Catalog Migration/
  databricks.yml              # Bundle definition: jobs, variables, targets
  src/
    notebooks/                # Migration notebooks (Steps 1-4)
      Bundle_01_Inventory_Generation.ipynb
      Bundle_02_Review_and_Approve_Inventory.ipynb
      Bundle_03_Export_and_Transform.ipynb
      Bundle_04_Generate_and_Deploy.ipynb
      Bundle_04_Generate_and_Deploy_V2.ipynb
      Bundle_IP_ACL_Setup.ipynb
    helpers/                  # Python modules (auth, export, transform, deploy)
    setup-guides/             # SP OAuth setup doc + secrets verification notebook
      Setup_Migration_Secrets.ipynb
      SP_OAUTH_SETUP.md
  resources/                  # Reserved for additional DAB resource definitions
  scripts/                    # Shell scripts (IP ACL, asset bundle deploy)
  ip-detection/               # Sub-bundle for cluster IP detection
```

## Prerequisites

- Databricks CLI v0.218.0+ installed
- Two CLI profiles configured in `~/.databrickscfg` (one per workspace)
- Workspace admin (or sufficient permissions) on source and target workspaces
- Unity Catalog volume for migration artifacts
- SQL warehouse in target workspace
- For Step 4: Service Principal with OAuth (recommended) or a PAT token

## Setup

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd <repo-root>/Customer-Work/Catalog\ Migration
```

### 2. Configure databricks.yml

Edit `databricks.yml` and set these for your target (e.g. `dev` or `azure-test`):

| Variable | Example |
|----------|---------|
| `catalog` | `my_catalog` |
| `volume_base` | `/Volumes/my_catalog/my_schema/dashboard_migration` |
| `source_workspace_url` | `https://source.cloud.databricks.com` |
| `target_workspace_url` | `https://target.cloud.databricks.com` |
| `warehouse_id` or `warehouse_name` | Target SQL warehouse |
| `auth_method` | `"sp_oauth"` (recommended) or `"pat"` |
| `sp_secret_scope` | `"migration_secrets"` |

Also set the target `workspace.host` to your source workspace URL.

### 3. Service Principal OAuth (recommended for Step 4)

SP OAuth is required when `auth_method: "sp_oauth"`. Create the SP and store credentials before running Step 4.

**Account Console setup:**

1. Create a Service Principal in Account Console (User management > Service principals).
2. Add the SP to both source and target workspaces (Workspaces > Permissions > Add).
3. Generate an OAuth secret for the SP (Service principals > your SP > Secrets > Generate).
4. Save the Client ID and OAuth secret securely.

**Store credentials via CLI (run from your machine):**

```bash
# Create secret scope on source workspace
databricks secrets create-scope migration_secrets --profile <source-profile>

# Store SP Application (Client) ID -- paste when prompted
databricks secrets put-secret migration_secrets sp_client_id --profile <source-profile>

# Store SP OAuth secret -- paste when prompted
databricks secrets put-secret migration_secrets sp_client_secret --profile <source-profile>
```

See `src/setup-guides/SP_OAUTH_SETUP.md` for the full guide.

### 4. Deploy the bundle (one-time)

```bash
databricks bundle deploy -t <target> --profile <source-profile>
```

### 5. (Optional) Verify secrets in the workspace

After deploy, open `src/setup-guides/Setup_Migration_Secrets.ipynb` in the workspace. Set the config cell (target URL, scope, profile), run the path and verify cells to confirm connectivity.

## Running the Migration (Steps 1-4)

### Step 1: Generate Inventory

```bash
databricks bundle run inventory_generation -t <target> --profile <source-profile>
```

### Step 2: Manual Review and Approval (UI)

Open `src/notebooks/Bundle_02_Review_and_Approve_Inventory.ipynb` in the Databricks workspace. Review dashboards, apply filters, type CONFIRM to save the approved inventory.

### Step 3: Export and Transform

```bash
databricks bundle run export_transform -t <target> --profile <source-profile>
```

### Step 4: Generate and Deploy

```bash
# Dry run (safe default -- preview only, no resources created)
databricks bundle run generate_deploy -t <target> --profile <source-profile>

# Live deploy (when ready)
databricks bundle run generate_deploy -t <target> --profile <source-profile> \
  --var="dry_run_mode=false"
```

Step 4 uses `auth_method` and `sp_secret_scope` from `databricks.yml` to connect to the target workspace. When `auth_method: "sp_oauth"`, it reads `sp_client_id` and `sp_client_secret` from the secret scope.

## Verification Checklist

After any structural or config change, verify with:

1. `databricks bundle validate -t <target>` -- catches YAML/path errors
2. `databricks bundle deploy -t <target> --profile <source-profile>` -- syncs code to workspace
3. Run each job (inventory_generation, export_transform, generate_deploy) -- confirm no `ModuleNotFoundError`
4. Open `Bundle_02` in UI -- run path cell + cells that import helpers
5. Open `Setup_Migration_Secrets.ipynb` in UI -- run config, path, verify, test connection

## Git Guidelines

- Never commit real workspace URLs, catalog names, warehouse IDs, or secrets.
- The committed `databricks.yml` uses placeholders (e.g. `YOUR-SOURCE-WORKSPACE`). Update locally only.
- Keep `auth_method`, `sp_secret_scope`, and generic config names in the repo (e.g. `migration_secrets`).
- Secret scope values (`sp_client_id`, `sp_client_secret`) are stored via CLI, never in code.

## New User Flow

1. **Pull** the repo.
2. **Create** a Service Principal in Account Console; add to both workspaces; generate an OAuth secret.
3. **Update** `databricks.yml` locally (catalog, volume_base, source/target URLs, warehouse, auth_method).
4. **Store** SP credentials via CLI (`create-scope`, `put-secret sp_client_id`, `put-secret sp_client_secret`).
5. **Deploy** once: `databricks bundle deploy -t <target> --profile <source-profile>`.
6. **Run** Steps 1-4 in order.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'helpers'` | `sys.path` missing `src/` | Run the path-resolution cell at the top of the notebook |
| `Missing secrets: ['sp_client_id', 'sp_client_secret']` | Secrets not stored in scope | Run `databricks secrets put-secret` for both keys via CLI |
| `Secret scope does not exist` | Scope not created | Run `databricks secrets create-scope migration_secrets --profile <source-profile>` |
| `401 Unauthorized` on target | SP OAuth secret invalid or expired | Regenerate in Account Console, re-store via CLI |
| `403 Forbidden` on target | SP lacks workspace permissions | Add SP to target workspace in Account Console |
| `Connection to wrong workspace` | Wrong URL in yml | Verify `target_workspace_url` matches the target |

## Resources

- `src/setup-guides/SP_OAUTH_SETUP.md` -- Full SP OAuth setup guide
- `src/setup-guides/Setup_Migration_Secrets.ipynb` -- Verify secrets and test connection
- `ip-detection/` -- Sub-bundle for detecting cluster IPs (for IP ACL whitelisting)
- `scripts/` -- Shell scripts for IP ACL setup and asset bundle deployment
