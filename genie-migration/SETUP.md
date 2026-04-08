# Genie space migration — setup guide

Use this checklist to run the toolkit in your own Databricks account. The layout matches the other folders in [this repository](https://github.com/archana986/databricks-dashboard-migration): **source** bundle (source workspace), **target** bundle (target workspace), optional **setup** bundle (demo data).

## Prerequisites

| Item | Notes |
|------|--------|
| Databricks CLI | v0.278+ recommended |
| Two workspaces | Same Unity Catalog metastore (shared volumes) |
| UC volumes | Export path (source catalog) and import path (target catalog) |
| SQL warehouse | In the **target** workspace (for Genie deployment) |
| Permissions | Service principal or user with Genie + UC volume access in both workspaces |

## Step 1 — CLI profiles

```bash
databricks auth login -p source-profile --host https://YOUR-SOURCE-WORKSPACE.cloud.databricks.com
databricks auth login -p target-profile --host https://YOUR-TARGET-WORKSPACE.cloud.databricks.com
```

Use the same profile for both if you are doing single-workspace testing with two catalogs.

## Step 2 — Local configuration (recommended)

In **each** of `source/`, `target/`, and (if used) `setup/`:

```bash
cp databricks.local.yml.example databricks.local.yml
# Edit databricks.local.yml: profile, host, catalog/schema/volume, warehouse_id (target only)
```

`databricks.local.yml` is listed in `.gitignore` and is merged via `include` in `databricks.yml`.

## Step 3 — Create volumes (if needed)

```sql
-- Source catalog (export)
CREATE VOLUME IF NOT EXISTS <source_catalog>.<schema>.<export_volume>;

-- Target catalog (import) — or let the transfer job create it, depending on your permissions
CREATE VOLUME IF NOT EXISTS <target_catalog>.<schema>.<import_volume>;
```

Grant your migration principal `READ_VOLUME`, `WRITE_VOLUME` (and Genie permissions) as described in [README.md](README.md).

## Step 4 — Deploy and run (source)

```bash
cd source
databricks bundle deploy -p <source-profile>
databricks bundle run src_genie_inventory -p <source-profile>
```

Open `Src_02_Review_and_Approve` in the workspace, set approved rows, then:

```bash
databricks bundle run src_genie_export -p <source-profile>
```

## Step 5 — Deploy and run (target)

```bash
cd ../target
databricks bundle deploy -p <target-profile>
databricks bundle run tgt_genie_deploy -p <target-profile>
```

If source and target catalogs differ, edit `catalog_mapping.csv` on the volume as described in [README.md](README.md).

## Optional — demo data and spaces

```bash
cd ../setup
cp databricks.local.yml.example databricks.local.yml   # if not already
databricks bundle deploy -p <profile>
databricks bundle run setup_sample_genie_spaces -p <profile>
```

## Troubleshooting

- **`databricks.local.yml` missing:** `bundle validate` fails if the included file is absent. Copy from `*.example` first.
- **Wrong workspace:** Confirm `host` and `-p` profile point to the same workspace for each bundle.
- **Warehouse errors:** Set `warehouse_id` in the target bundle to a warehouse in the **target** workspace.
