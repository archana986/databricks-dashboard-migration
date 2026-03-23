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
- [ ] UC Volume created for migration artifacts
  ```bash
  # Example path: /Volumes/<catalog>/<schema>/dashboard_migration
  databricks fs ls dbfs:/Volumes/<catalog>/<schema>/dashboard_migration --profile source-profile
  ```
- [ ] **Target tables exist** in target catalog/schema (dashboards will fail if referencing non-existent tables)

### Warehouse Configuration
- [ ] SQL Warehouse exists in target workspace
- [ ] Warehouse ID or name noted for configuration
- [ ] Node type ID configured for your cloud (AWS/Azure/GCP)
  - AWS: e.g., `i3.xlarge`
  - Azure: e.g., `Standard_DS3_v2`
  - GCP: e.g., `n1-standard-4`

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
- [ ] Authentication method selected (`sp_oauth` or `pat`)
- [ ] Node type ID set for your cloud provider
- [ ] **DO NOT commit** real values to git (keep local only)

### Catalog/Schema Mapping CSV
- [ ] `catalog_schema_mapping.csv` file created
- [ ] File uploaded to UC Volume at: `/Volumes/<catalog>/<schema>/dashboard_migration/mappings/catalog_schema_mapping.csv`
- [ ] CSV format:
  ```csv
  source_catalog,source_schema,target_catalog,target_schema
  source_cat,source_schema,target_cat,target_schema
  ```

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
- [ ] Can read from source volume:
  ```bash
  databricks fs ls dbfs:/Volumes/<catalog>/<schema>/dashboard_migration --profile source-profile
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
- [ ] In the **source** workspace Jobs UI, verify **two** jobs: `src_dashboard_inventory`, `src_dashboard_export_transform`
- [ ] In the **target** workspace Jobs UI, verify **one** job: `tgt_dashboard_register`

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
      schema: your_schema
      export_volume: your_export_volume
      import_volume: your_import_volume
      volume_base: /Volumes/your_target_catalog/your_schema/your_import_volume
      warehouse_id: "your-warehouse-id"
      target_parent_path: /Shared/Migrated_Dashboards
```

### Typical files on the export volume (after Steps 1–3)

```
/Volumes/<source_catalog>/<schema>/<export_volume>/
├── mappings/
│   └── catalog_schema_mapping.csv   ← needed if transformation_enabled is true
├── dashboard_inventory/
│   └── (generated by Step 1)
├── dashboard_inventory_approved/
│   └── (written by Step 2)
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
3. **Wrong node_type_id for cloud** → Jobs will fail with "instance type not supported"
4. **Target folder doesn't exist** → Create it manually or script will fail
5. **Secrets not configured** → OAuth authentication will fail
6. **Wrong CLI profile** → Operations will target wrong workspace

---

## 🎯 Ready to Migrate?

If all items above are checked, you're ready to run the migration! 

See [SETUP.md](SETUP.md) for detailed step-by-step instructions.
