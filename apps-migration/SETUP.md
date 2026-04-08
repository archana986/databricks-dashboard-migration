# Databricks Apps migration — setup guide

This toolkit follows the same pattern as the other folders in [this repository](https://github.com/archana986/databricks-dashboard-migration): a **source** Databricks Asset Bundle that inventories apps, lets you approve them, and exports each app as files under a Unity Catalog volume. You then download a bundle folder, optionally rewrite catalog names, and deploy with the DAB inside that folder.

## Prerequisites

| Item | Notes |
|------|--------|
| Databricks CLI | Recent v0.2xx+ |
| Apps enabled | Source and target workspaces |
| UC volume | For `apps_inventory`, exported bundle trees, and optional prereq data copy |
| Target workspace URL | Set as `target_host` for generated bundle metadata |

## Step 1 — Local configuration

```bash
cd source
cp databricks.local.yml.example databricks.local.yml
```

Edit `databricks.local.yml`:

- `workspace.profile` — CLI profile in `~/.databrickscfg`
- `workspace.host` — workspace where you run inventory/export jobs
- `variables.catalog`, `schema`, `volume` — artifact location (`/Volumes/.../bundles/<app>/`)
- `variables.target_catalog` — used by the optional prereq notebook
- `variables.target_host` — URL of the workspace where apps will eventually run (embedded in exports)

This file is **gitignored**; placeholders remain in `databricks.yml` for a clean clone.

## Step 2 — Deploy bundle

```bash
databricks bundle deploy -p <your-profile>
```

## Step 3 — Optional prereq and sample apps

If you use the prereq job to clone demo tables into a target catalog:

```bash
databricks bundle run prereq_setup_target_catalog -p <your-profile>
```

Optional sample apps for testing:

```bash
databricks bundle run setup_deploy_sample_apps -p <your-profile>
```

## Step 4 — Inventory and export

```bash
databricks bundle run src_apps_inventory -p <your-profile>
databricks bundle run src_apps_export -p <your-profile>
```

Complete any approval steps in the workspace notebooks if your process requires them.

## Step 5 — Download, transform, deploy

```bash
databricks fs cp -r "dbfs:/Volumes/<catalog>/<schema>/<volume>/bundles/<app-name>" ./<app-name> -p <your-profile>
python scripts/transform_catalogs.py ./<app-name>   # if you use catalog_mapping.csv
cd <app-name>
databricks bundle deploy -t target -p <target-profile>
```

Use `--var app_name=...` when deploying a second copy in the **same** workspace.

## Target-only notebook

`target/notebooks/Tgt_04_Reconciliation.ipynb` is optional helper content for validation; there is no separate target bundle in this release. Run it from a workspace if you attach it to your own job or notebook workflow.

## Troubleshooting

- **`databricks.local.yml` missing:** Copy from `databricks.local.yml.example` before `bundle validate` or `deploy`.
- **Wrong volume path:** `catalog` / `schema` / `volume` must match a volume your principal can write.
- **Secrets and Lakebase:** Customer-specific; configure secrets and database endpoints in the target workspace before starting exported apps.
