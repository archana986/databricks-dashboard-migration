# Single-workspace migration test (optional)

> **Standard topology:** [REQUIREMENTS.md](../REQUIREMENTS.md) assumes **different** source and target **workspaces** on a shared metastore. Use this page only for **local or lab testing** when both bundles run against **one** workspace—for example two catalogs (or two volumes) in the same workspace.

## When this applies

- You deploy **source** and **target** bundles with the **same** `workspace.host` and CLI profile.
- You use a **source catalog** (export volume) and a **target catalog** (import volume) that both attach to the **same** Unity Catalog metastore as that workspace.

## Workspace folder paths (browse URLs)

Databricks **browse** links (`/browse/folders/<id>`) are not the same as **`target_parent_path`**. Resolve the folder in the UI and copy the **absolute path** (e.g. `/Shared/...` or `/Workspace/Users/you@company.com/...`).

| Role | Use in config |
|------|----------------|
| Folder for extra assets (notebooks, dashboard JSON uploads) | `WORKSPACE_PATH` in your sync script, or `PARENT_PATH` in a deploy notebook |
| Folder where migrated dashboards should appear | `target_parent_path` in `target/databricks.yml` or `target/databricks.local.yml` |

## 1. Create volumes (example SQL)

Replace catalog, schema, and volume names with yours:

```sql
CREATE VOLUME IF NOT EXISTS <source_catalog>.<schema>.<export_volume_name>;
CREATE VOLUME IF NOT EXISTS <target_catalog>.<schema>.<import_volume_name>;
```

## 2. Local bundle overrides

```bash
cd source
cp databricks.local.yml.example databricks.local.yml

cd ../target
cp databricks.local.yml.example databricks.local.yml
```

## 3. Catalog mapping (optional)

If `transformation_enabled` is `true`, place `mappings/catalog_schema_mapping.csv` on the export volume (see `catalog_schema_mapping_template.csv` in the repo).

## 4. Run order

Use the **same** profile for both bundles when hosts match:

```bash
cd source
databricks bundle deploy --profile YOUR_PROFILE
databricks bundle run src_dashboard_inventory --profile YOUR_PROFILE
# Bundle_02 in UI → CONFIRM
databricks bundle run src_dashboard_export_transform --profile YOUR_PROFILE

cd ../target
databricks bundle deploy --profile YOUR_PROFILE
databricks bundle run tgt_dashboard_register --profile YOUR_PROFILE
```

## 5. Metastore

Both catalogs must be in the **same** metastore as the workspace so the transfer task can copy between volumes.
