# UC Model Migration — Requirements

## Goal

Migrate MLflow registered models from a source Unity Catalog catalog to a target catalog on the same metastore. Source models are **never modified or deleted**. All configuration is passed via DAB variables and notebook widget parameters — no hardcoded values in code.

## Architecture: Separate Bundles, 4 Workflows

Two independent Databricks Asset Bundles, each deployed to its own workspace. Each bundle contains two workflows (jobs) — one for cleanup, one for migration.

### Source bundle (`source/`)

Deployed to the **source workspace**. Reads source models (never modifies them) and writes artifacts to the source export volume.

| Workflow | Job key | Run command | Tasks |
|---|---|---|---|
| **src_model_migration_cleanup** | `src_model_migration_cleanup` | `cd source && databricks bundle run src_model_migration_cleanup` | `cleanup_export_volume` |
| **src_model_export** | `src_model_export` | `cd source && databricks bundle run src_model_export` | `export` |

### Target bundle (`target/`)

Deployed to the **target workspace**. Cleans target state, transfers from source export volume, imports into target catalog, validates.

| Workflow | Job key | Run command | Tasks |
|---|---|---|---|
| **tgt_model_migration_cleanup** | `tgt_model_migration_cleanup` | `cd target && databricks bundle run tgt_model_migration_cleanup` | `cleanup_volume` → `cleanup_models` |
| **tgt_model_migration_register** | `tgt_model_migration_register` | `cd target && databricks bundle run tgt_model_migration_register` | `transfer` → `import_register` → `validate` → `reconciliation` |

## Run Order

```bash
cd source && databricks bundle run src_model_migration_cleanup       # 1. Clean source export volume
cd source && databricks bundle run src_model_export                  # 2. Export models to volume
cd ../target && databricks bundle run tgt_model_migration_cleanup    # 3. Clean target volume + models
cd target && databricks bundle run tgt_model_migration_register      # 4. Transfer + import + validate
```

## Safety Rules

- **Source models are read-only.** No workflow or notebook may modify, delete, or overwrite registered models in the source catalog. Source interactions: read model versions, download artifacts, read/write the export volume only.
- **Target cleanup is destructive.** `tgt_cleanup` deletes all model versions, aliases, registered model entries, migration experiments, and import volume files for the specified model names.

## No Hardcoding

Every configurable value is a DAB variable in each bundle's `databricks.yml`:

| Variable | Source bundle | Target bundle | Description |
|---|---|---|---|
| `source_catalog` | yes | yes | Source UC catalog name |
| `target_catalog` | yes | yes | Target UC catalog name |
| `schema` | yes | yes | Schema name |
| `model_names` | yes | yes | Comma-separated model short names |
| `export_volume` | yes | yes | Export volume name in source catalog |
| `import_volume` | — | yes | Import volume name in target catalog |

Job YAMLs reference these as `${var.source_catalog}`, `${var.model_names}`, etc. Notebooks receive values as widget parameters.

## Compute

Each workflow defines both serverless and classic cluster compute:
- **Default**: Serverless via `environment_key: migration_env`
- **Classic**: Switch each task to `job_cluster_key: migration_cluster`

Notebooks are compatible with both: Python variables for config, no `spark.conf.set()`.

## Notebooks

| # | Notebook | Bundle | Workflow | Purpose |
|---|---|---|---|---|
| 02 | `02_cleanup_export.ipynb` | source | `src_model_migration_cleanup` | Delete all files in source export volume |
| 03 | `03_export.ipynb` | source | `src_model_export` | Export model artifacts + metadata to export volume |
| 04 | `04_transfer.ipynb` | target | `tgt_model_migration_register` | Copy export volume to target import volume |
| 05 | `05_import.ipynb` | target | `tgt_model_migration_register` | Load from import volume, register in target catalog |
| 06 | `06_validate.ipynb` | target | `tgt_model_migration_register` | Compare versions, metrics, params, aliases; inference test |
| 09 | `09_reconciliation.ipynb` | target | `tgt_model_migration_register` | Read-only summary: version counts and aliases, source vs target |
| 07 | `07_cleanup_target_volume.ipynb` | target | `tgt_model_migration_cleanup` | Delete all files in target import volume |
| 08 | `08_cleanup_target_models.ipynb` | target | `tgt_model_migration_cleanup` | Delete aliases, all versions, registered models, experiments |

## File Structure

```
uc-model-migration-customer/
  source/                                 # Source bundle (deploy to source workspace)
    databricks.yml
    resources/
      src_cleanup_job.yml
      src_migration_job.yml
    src/
      notebooks/
        02_cleanup_export.ipynb
        03_export.ipynb
  target/                                 # Target bundle (deploy to target workspace)
    databricks.yml
    resources/
      tgt_cleanup_job.yml
      tgt_migration_job.yml
    src/
      notebooks/
        04_transfer.ipynb
        05_import.ipynb
        06_validate.ipynb
        09_reconciliation.ipynb
        07_cleanup_target_volume.ipynb
        08_cleanup_target_models.ipynb
  README.md
  SETUP.md
  REQUIREMENTS.md
  .gitignore
```
