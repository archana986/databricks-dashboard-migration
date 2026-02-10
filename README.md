# Databricks Dashboard Migration Toolkit

Migrate Databricks Lakeview dashboards across workspaces with catalog/schema transformations, permission and schedule migration, and cross-workspace authentication via Service Principal OAuth or PAT tokens. Fully deployable with Databricks Asset Bundles (DABs).

**Why this toolkit instead of Terraform?** Terraform's Databricks provider doesn't support Lakeview dashboard migration, cross-workspace catalog remapping, or automatic permissions/schedule preservation. See [WHY_THIS_TOOLKIT.md](WHY_THIS_TOOLKIT.md) for a full comparison and decision guide.

## Project Structure

```
databricks.yml                  # Bundle config: variables, targets, include
resources/
  migration_jobs.yml            # DAB job definitions (3 migration jobs)
src/
  notebooks/                    # Migration notebooks (Steps 1-4)
    Bundle_01_Inventory_Generation.ipynb
    Bundle_02_Review_and_Approve_Inventory.ipynb
    Bundle_03_Export_and_Transform.ipynb
    Bundle_04_Generate_and_Deploy.ipynb
    Bundle_04_Generate_and_Deploy_V2.ipynb
    Bundle_IP_ACL_Setup.ipynb
  helpers/                      # Python modules (auth, export, transform, deploy)
  setup-guides/                 # SP OAuth setup doc + secrets verification notebook
    Setup_Migration_Secrets.ipynb
    SP_OAUTH_SETUP.md
scripts/                        # Shell scripts (IP ACL, asset bundle deploy)
ip-detection/                   # Sub-bundle for cluster IP detection
SETUP.md                        # Full setup and usage guide
```

## Quick Start

```bash
# 1. Clone
git clone https://github.com/archana-krishnamurthy_data/dashboard-migration.git
cd dashboard-migration

# 2. Configure -- edit databricks.yml with your workspace URLs, catalog, volume, warehouse
#    (keep changes local, do not commit real values)

# 3. Deploy
databricks bundle deploy -t <target> --profile <source-profile>

# 4. Run migration steps 1-4
databricks bundle run inventory_generation -t <target> --profile <source-profile>
# ... (Step 2 is manual review in UI) ...
databricks bundle run export_transform -t <target> --profile <source-profile>
databricks bundle run generate_deploy -t <target> --profile <source-profile>
```

**For full setup instructions including SP OAuth, see [SETUP.md](SETUP.md).**

## Migration Workflow

| Step | What | How |
|---|---|---|
| **1** | Generate inventory | `databricks bundle run inventory_generation -t <target>` |
| **2** | Review and approve (UI) | Open `Bundle_02` notebook in workspace |
| **3** | Export and transform | `databricks bundle run export_transform -t <target>` |
| **4a** | Generate bundles | `databricks bundle run generate_deploy -t <target> --var="dry_run_mode=false"` |
| **4b** | Deploy to target + apply metadata | `./scripts/deploy_asset_bundle.sh --source-profile <src> --target-profile <tgt> --volume-base <path>` |

> **Note:** Step 4b automatically applies permissions and schedules after deploying dashboards. See [SETUP.md](SETUP.md) for details.

## Key Design Decisions

- **Structure**: All code in `src/`, DAB resource definitions in `resources/`, config + targets in root `databricks.yml`
- **Single source of truth**: All configuration variables and target overrides in `databricks.yml`
- **No secrets in repo**: Workspace URLs, catalogs, and credentials stay local or in Databricks secret scopes
- **`include:` pattern**: Root yml includes `resources/*.yml` for clean separation of config vs. job definitions

## Resources

- [SETUP.md](SETUP.md) -- Full setup, SP OAuth, deploy, run, troubleshoot
- [WHY_THIS_TOOLKIT.md](WHY_THIS_TOOLKIT.md) -- Why this toolkit vs Terraform (comparison, decision guide, scenarios)
- `src/setup-guides/SP_OAUTH_SETUP.md` -- Detailed SP OAuth guide
- `src/setup-guides/Setup_Migration_Secrets.ipynb` -- Verify secrets and test connection
- `ip-detection/` -- Sub-bundle for detecting cluster IPs (for IP ACL whitelisting)
