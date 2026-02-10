# Databricks Dashboard Migration Toolkit

Migrate Databricks Lakeview dashboards across workspaces with catalog/schema transformations, permission and schedule migration, and cross-workspace authentication via Service Principal OAuth or PAT tokens. Fully deployable with Databricks Asset Bundles (DABs).

**Why this toolkit instead of Terraform?** Terraform's Databricks provider doesn't support Lakeview dashboard migration, cross-workspace catalog remapping, or automatic permissions/schedule preservation. See [WHY_THIS_TOOLKIT.md](WHY_THIS_TOOLKIT.md) for a full comparison and decision guide.

## Prerequisites Checklist

Before you begin, verify all items below. See [SETUP.md](SETUP.md) for detailed instructions on each.

| # | Requirement | How to verify |
|---|---|---|
| 1 | **Databricks CLI v0.218.0+** | `databricks version` |
| 2 | **Source workspace CLI profile** | `databricks auth profiles` -- must show **Valid: YES** for your source profile |
| 3 | **Target workspace CLI profile** | Same command -- must show **Valid: YES** for your target profile |
| 4 | **Unity Catalog + schema** | `databricks catalogs list --profile <source>` and `databricks schemas list <catalog> --profile <source>` |
| 5 | **UC volume for artifacts** | `databricks volumes list <catalog> <schema> --profile <source>` -- must contain a `dashboard_migration` volume |
| 6 | **SQL warehouse on target** | `databricks warehouses list --profile <target>` -- note the warehouse ID or name |
| 7 | **Secret scope** (if using SP OAuth) | `databricks secrets list-scopes --profile <source>` -- must contain `migration_secrets` |
| 8 | **SP credentials stored** (if using SP OAuth) | `databricks secrets list-secrets migration_secrets --profile <source>` -- must contain `sp_client_id` and `sp_client_secret` |
| 9 | **Node type configured** | Set `node_type_id` in your target's variables -- see table below |
| 10 | **Catalog/schema mapping CSV** | Upload `catalog_schema_mapping.csv` to `<volume_base>/mappings/` -- see [SETUP.md](SETUP.md) for format |
| 11 | **Bundle validates** | `databricks bundle validate -t <target> --profile <source>` -- must show `Validation OK!` |

### Cloud-specific node types

Step 4 (Generate & Deploy) uses a standard cluster for cross-workspace access. Set the `node_type_id` variable in your target:

| Cloud | `node_type_id` value | Notes |
|---|---|---|
| **AWS** | `i3.xlarge` | Default -- no change needed |
| **Azure** | `Standard_DS3_v2` | Must override in your target |
| **GCP** | `n1-standard-4` | Must override in your target |

Example for Azure in `databricks.yml`:

```yaml
targets:
  azure-test:
    variables:
      node_type_id: "Standard_DS3_v2"
```

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
| **4** | Generate and deploy | `databricks bundle run generate_deploy -t <target>` |

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
