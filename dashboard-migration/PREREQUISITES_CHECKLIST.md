# Prerequisites Checklist

Complete this checklist before running the dashboard migration.

## ✅ Infrastructure Prerequisites

### Databricks CLI
- [ ] Databricks CLI v0.218.0+ installed
  ```bash
  databricks --version
  ```
- [ ] Two CLI profiles configured in `~/.databrickscfg`:
  - [ ] Source workspace profile
  - [ ] Target workspace profile

### Unity Catalog Setup
- [ ] Source catalog and schema exist and are accessible
- [ ] Target catalog and schema exist and are accessible
- [ ] **Export volume** created in the source catalog (required before running Inventory):
  ```sql
  CREATE VOLUME IF NOT EXISTS <source_catalog>.<source_schema>.<export_volume>;
  -- e.g. CREATE VOLUME IF NOT EXISTS my_catalog.migration.dashboard_export;
  ```
- [ ] **Import volume** — **no action needed**; the Transfer & Deploy job creates it automatically via `CREATE VOLUME IF NOT EXISTS`. Optionally pre-create:
  ```sql
  -- Optional:
  CREATE VOLUME IF NOT EXISTS <target_catalog>.<target_schema>.<import_volume>;
  ```
- [ ] **Mapping CSV** uploaded to the export volume (required if `transformation_enabled` is `"true"`):
  ```bash
  databricks fs cp catalog_schema_mapping.csv \
    dbfs:/Volumes/<source_catalog>/<source_schema>/<export_volume>/mappings/catalog_schema_mapping.csv \
    --profile <source-profile>
  ```
  Create the CSV from `catalog_schema_mapping_template.csv` in the repo root. See [SETUP.md](SETUP.md) for column reference.
- [ ] **Target tables exist** in target catalog/schema (dashboards will fail if referencing non-existent tables)
- [ ] Source and target catalogs are on the **same UC metastore** (required for volume transfer)

### Warehouse Configuration
- [ ] SQL Warehouse exists in target workspace
- [ ] Warehouse ID or name noted for configuration

### Workspace Permissions
- [ ] Admin or sufficient permissions on source workspace
- [ ] Admin or sufficient permissions on target workspace
- [ ] **Target workspace folder** exists or will be created
  ```bash
  # Example: /Shared/Migrated_Dashboards_V2
  # Create if needed:
  databricks workspace mkdirs /Shared/Migrated_Dashboards_V2 --profile target-profile
  ```

---

## ✅ Authentication Setup (OAuth Recommended)

### Service Principal (for OAuth - Recommended)
- [ ] Service Principal created in Account Console
- [ ] Application (Client) ID noted
- [ ] OAuth secret generated and securely stored
- [ ] SP added to both source and target workspaces
- [ ] SP has appropriate workspace permissions

### Secret Scope
- [ ] Secret scope created on source workspace:
  ```bash
  databricks secrets create-scope migration_secrets --profile source-profile
  ```
- [ ] SP Client ID stored in secret scope:
  ```bash
  databricks secrets put-secret migration_secrets sp_client_id --profile source-profile
  ```
- [ ] SP Client Secret stored in secret scope:
  ```bash
  databricks secrets put-secret migration_secrets sp_client_secret --profile source-profile
  ```

---

## ✅ Configuration Files

### databricks.yml
- [ ] Workspace URLs configured (source and target)
- [ ] Catalog and schema names set
- [ ] Volume base path configured
- [ ] Warehouse ID or name set
- [ ] Authentication method selected (OAuth recommended)
- [ ] **DO NOT commit** real values to git (keep local only)

### Catalog/Schema Mapping CSV (required if `transformation_enabled` is `"true"`)
- [ ] `catalog_schema_mapping.csv` file created using the template (`catalog_schema_mapping_template.csv` in repo root)
- [ ] File uploaded to the **export volume** at: `/Volumes/<source_catalog>/<source_schema>/<export_volume>/mappings/catalog_schema_mapping.csv`
  ```bash
  # Upload from local machine:
  databricks fs cp catalog_schema_mapping.csv \
    dbfs:/Volumes/<source_catalog>/<source_schema>/<export_volume>/mappings/catalog_schema_mapping.csv \
    --profile source-profile
  ```
- [ ] CSV columns: `old_catalog`, `old_schema`, `old_table`, `new_catalog`, `new_schema`, `new_table`, `old_volume`, `new_volume`
- [ ] Leave `old_table`/`new_table` empty to remap all tables in a schema:
  ```csv
  old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
  my_source_catalog,my_schema,,my_target_catalog,my_target_schema,,,
  ```
  See `catalog_schema_mapping_template.csv` in the repo root and [SETUP.md](SETUP.md) for a full column reference.
- [ ] If you do **not** need SQL rewriting, set `transformation_enabled: "false"` in your local config and skip this step

---

## ✅ Pre-Flight Verification

### CLI Connectivity
- [ ] Source profile connection verified:
  ```bash
  databricks workspace list / --profile source-profile
  ```
- [ ] Target profile connection verified:
  ```bash
  databricks workspace list / --profile target-profile
  ```

### Volume Access
- [ ] Can access the **export volume** (source):
  ```bash
  databricks fs ls dbfs:/Volumes/<source_catalog>/<source_schema>/<export_volume> --profile source-profile
  ```
- [ ] Can access the **import volume** (target):
  ```bash
  databricks fs ls dbfs:/Volumes/<target_catalog>/<target_schema>/<import_volume> --profile target-profile
  ```

### Warehouse Access
- [ ] Warehouse is accessible and running (or can start):
  ```bash
  databricks warehouses get <warehouse-id> --profile target-profile
  ```

---

## ✅ Pre-Deployment Steps

### Bundle deployment
- [ ] **Source** bundle deployed:
  ```bash
  cd source && databricks bundle deploy --profile source-profile
  ```
- [ ] **Target** bundle deployed:
  ```bash
  cd target && databricks bundle deploy --profile target-profile
  ```
- [ ] In the **source** workspace Jobs UI, verify **two** jobs: `[Src] Dashboard Inventory`, `[Src] Dashboard Export & Transform`
- [ ] In the **target** workspace Jobs UI, verify **one** job: `[Tgt] Dashboard Transfer & Deploy`

---

## ✅ Migration-Ready Checklist

### Source Data
- [ ] Dashboards to migrate are identified
- [ ] Source dashboards are accessible and functional
- [ ] Source tables exist and contain data

### Target Environment
- [ ] Target catalog and schema exist
- [ ] **Target tables exist** (matching source table references after transformation)
- [ ] Target workspace folder exists (or will be created by script)
- [ ] Target warehouse is available

---

## 📋 Quick Reference

### Minimum required configuration (two bundles)

**Source — `source/databricks.yml`**

```yaml
targets:
  default:
    workspace:
      host: https://your-source.azuredatabricks.net
    variables:
      source_workspace_url: https://your-source.azuredatabricks.net
      catalog: your_source_catalog
      volume_base: /Volumes/your_source_catalog/your_schema/your_export_volume
```

**Target — `target/databricks.yml`**

```yaml
targets:
  default:
    workspace:
      host: https://your-target.azuredatabricks.net
    variables:
      source_catalog: your_source_catalog
      target_catalog: your_target_catalog
      source_schema: your_source_schema
      target_schema: your_target_schema
      export_volume: your_export_volume
      import_volume: your_import_volume
      volume_base: /Volumes/your_target_catalog/your_target_schema/your_import_volume
      warehouse_id: "your-warehouse-id"
      target_parent_path: /Shared/Migrated_Dashboards
```

### Typical files on the export volume (after Steps 1–3)

```
/Volumes/<source_catalog>/<schema>/<export_volume>/
├── mappings/
│   └── catalog_schema_mapping.csv   ← needed if transformation_enabled is true
├── dashboard_inventory/
│   └── inventory.csv                  ← generated by Inventory job
├── dashboard_inventory_approved/
│   └── inventory_approved.csv         ← written by Src_02 (review & approve)
├── exported/
│   └── (generated by Step 3)
└── transformed/
    └── (generated by Step 3)
```

After the target **transfer** task, the same structure should appear under your **import** volume path.

---

## ⚠️ Common Pitfalls to Avoid

1. **Missing catalog_schema_mapping.csv** → Step 3 fails if **transformation_enabled** is true and a mapping file is required
2. **Target tables don't exist** → Dashboards will have broken references
3. **Target folder doesn't exist** → Create it manually or script will fail
5. **Secrets not configured** → OAuth authentication will fail
6. **Wrong CLI profile** → Operations will target wrong workspace

---

## 🎯 Ready to Migrate?

If all items above are checked, you're ready to run the migration! 

See [SETUP.md](SETUP.md) for detailed step-by-step instructions.
