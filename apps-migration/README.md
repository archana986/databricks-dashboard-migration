# Databricks Apps Migration Toolkit

Migrate Databricks Apps between workspaces using the **bundle-based deployment pattern**.

## Overview

Apps are **code, not workspace objects**. The migration approach:

1. **Export** app source code from source workspace
2. **Transform** catalog references (if catalogs differ)
3. **Deploy** to target workspace via Databricks Asset Bundles

## Configure your workspace

Copy `source/databricks.local.yml.example` to `source/databricks.local.yml` (gitignored) and set `profile`, `host`, `catalog`, `schema`, `volume`, and `target_host`. Alternatively edit `source/databricks.yml` under `targets.default`. See [SETUP.md](SETUP.md).

## Quick Start

### Step 0: Setup Target Catalog (Prerequisite)

```bash
cd source
databricks bundle deploy -p <source_profile>

# Creates schema, volume, and copies tables from source to target catalog
databricks bundle run prereq_setup_target_catalog -p <source_profile>
```

### Step 1: Export Apps (Source Workspace)

```bash
cd source
databricks bundle deploy -p <source_profile>

# Generate inventory
databricks bundle run src_apps_inventory -p <source_profile>

# Export apps to bundles (scans for catalog references)
databricks bundle run src_apps_export -p <source_profile>
```

### Step 2: Download and Transform

```bash
# Download a bundle
databricks fs cp -r "dbfs:/Volumes/<catalog>/<schema>/<volume>/bundles/<app-name>" ./<app-name> -p <source_profile>

# Edit catalog_mapping.csv - fill in target catalog names
cat <app-name>/catalog_mapping.csv
# source_catalog,target_catalog,notes
# prod_catalog,,# Fill in target catalog

# Apply catalog transformations
python source/scripts/transform_catalogs.py ./<app-name>
```

### Step 3: Deploy to Target

```bash
cd <app-name>

# Cross-workspace (different workspace, same app name)
databricks bundle deploy -t target -p <target_profile>

# Same-workspace testing (must use different app name)
databricks bundle deploy -t target -p <target_profile> --var app_name=<new-name>

# Start the app
databricks bundle run <app_resource> -t target -p <target_profile>
```

## Catalog Transformation

When source and target workspaces use different Unity Catalog catalogs:

| Source | Target | Action |
|--------|--------|--------|
| `prod_catalog.sales.orders` | `dev_catalog.sales.orders` | Fill in `catalog_mapping.csv` |

### How It Works

1. **Export notebook scans** all `.py`, `.sql`, `.yaml` files for patterns like:
   - `spark.table("catalog.schema.table")`
   - `FROM catalog.schema.table`
   - `USE CATALOG catalog_name`

2. **Generates `catalog_mapping.csv`** per app:
   ```csv
   source_catalog,target_catalog,notes
   prod_catalog,,# Fill in target catalog
   analytics,,# Fill in target catalog
   ```

3. **Transform script applies** find-and-replace:
   ```bash
   python source/scripts/transform_catalogs.py ./my-app
   # prod_catalog -> dev_catalog (3 replacements)
   ```

## File Structure

```
AppsMigration/
├── README.md
├── source/
│   ├── databricks.yml
│   ├── notebooks/
│   │   ├── Setup_Deploy_Sample_Apps.ipynb  # Test setup (optional)
│   │   ├── Src_01_Inventory_Generation.ipynb
│   │   ├── Src_02_Create_Approved.ipynb
│   │   ├── Src_02_Review_and_Approve.ipynb
│   │   └── Src_03_Export_Apps.ipynb
│   ├── resources/
│   │   └── src_apps_jobs.yml
│   └── scripts/
│       └── transform_catalogs.py           # Catalog replacement script
└── archive/                                 # Old planning docs
```

## Exported Bundle Structure

Each app exports to `/Volumes/<catalog>/<schema>/<volume>/bundles/<app-name>/`:

```
<app-name>/
├── databricks.yml        # Bundle config (source + target hosts)
├── resources/
│   └── app.yml           # App resource definition
├── app.py                # Application code
├── app.yaml              # App config (command, env vars)
├── requirements.txt      # Dependencies
└── catalog_mapping.csv   # Detected catalog references (if any)
```

## Jobs Reference

| Job | Purpose |
|-----|---------|
| `prereq_setup_target_catalog` | Creates schema/volume in target catalog, copies tables |
| `setup_deploy_sample_apps` | Creates sample apps for testing |
| `src_apps_inventory` | Lists all apps, generates `apps_inventory.csv` |
| `src_apps_export` | Exports code + generates bundles + scans catalogs |

## Deployment Options

### Cross-Workspace Migration (Production)

Source and target are different workspaces. App name stays the same.

```bash
# Update databricks.yml target host if needed
databricks bundle deploy -t target -p <target_profile>
```

### Same-Workspace Testing (Demo)

Both source and target are the same workspace. Must use different app name.

```bash
databricks bundle deploy -t target -p <profile> --var app_name=myapp-migrated
```

## Target Workspace Preparation

Before deploying to target:

- [ ] Apps feature enabled
- [ ] Serverless compute available
- [ ] Network allows `*.databricksapps.com`
- [ ] Unity Catalog configured (create target catalogs/schemas)
- [ ] Secrets configured (if app uses secrets)
- [ ] SQL warehouses available (if app queries data)
- [ ] Lakebase migrated (if app uses OLTP - see below)

## Lakebase Migration

If your app uses Lakebase (OLTP databases):

```bash
# Export from source
pg_dump -h <source-lakebase-host> -U <user> -d <db> > backup.sql

# Import to target (after creating new Lakebase instance)
psql -h <target-lakebase-host> -U <user> -d <db> < backup.sql
```

Update the app's database connection config to point to the new Lakebase host.

## Example end-to-end commands

Replace `<profile>`, catalog/schema/volume paths, and app names with yours:

```bash
cd source
databricks bundle deploy -p <profile>

databricks bundle run prereq_setup_target_catalog -p <profile>
# Optional: databricks bundle run setup_deploy_sample_apps -p <profile>

databricks bundle run src_apps_inventory -p <profile>
databricks bundle run src_apps_export -p <profile>

databricks fs cp -r "dbfs:/Volumes/<catalog>/<schema>/<volume>/bundles/<app-name>" ./<app-name> -p <profile>

python source/scripts/transform_catalogs.py ./<app-name>

cd <app-name>
databricks bundle deploy -t target -p <profile> --var app_name=<unique-app-name>
databricks bundle run <app_resource_name> -t target -p <profile>
```

## Related Resources

- [Databricks Apps Documentation](https://docs.databricks.com/en/apps/index.html)
- [Databricks Asset Bundles](https://docs.databricks.com/en/dev-tools/bundles/index.html)
