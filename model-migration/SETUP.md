# UC Model Migration — Setup and Run

## Prerequisites

1. **Databricks CLI** (v0.278.0 or higher).
2. **Authentication**: Authenticate to **both** workspaces:
   ```bash
   databricks auth login -p <src-profile> --host <source-workspace-url>
   databricks auth login -p <tgt-profile> --host <target-workspace-url>
   ```
   OAuth or Azure CLI preferred; no PAT required.
3. **Same metastore**: Source and target catalogs must be on the same Unity Catalog metastore.
4. **Permissions**: Your user must be able to:
   - Read models and experiments in the source catalog.
   - Create and use the target catalog, schema, and volume (or use existing ones).
   - Run jobs in both workspaces.
5. **Python packages**: `scikit-learn`, `mlflow[databricks]` (provided by the job environment on serverless, or pre-installed on DBR 17.3 LTS+ classic clusters).

## Customization

Each bundle has its own `databricks.yml`. Edit the variables in both:

| Variable | Description | Default |
|---|---|---|
| `source_catalog` | UC catalog containing models to migrate | — |
| `target_catalog` | UC catalog to migrate models into | — |
| `schema` | Schema name | `default` |
| `model_names` | Comma-separated list of model short names | — |
| `export_volume` | Export volume name in source catalog | `model_exports` |
| `import_volume` | Import volume name in target catalog (target bundle only) | `model_imports` |

Set `workspace.profile` and `workspace.host` in each bundle's `databricks.yml` to match your `~/.databrickscfg`.

## Compute: Serverless vs Classic

Jobs default to **serverless** compute (`environment_key: migration_env`). Both options are defined in each job YAML.

**To switch to a classic cluster**, change each task from:

```yaml
environment_key: migration_env
```

to:

```yaml
job_cluster_key: migration_cluster
```

Then update the `job_clusters` section to set `spark_version`, `node_type_id`, and other cluster settings. Notebooks are compatible with both serverless and classic.

## Deploy

Deploy each bundle to its workspace:

```bash
# Source bundle
cd source
databricks bundle validate
databricks bundle deploy

# Target bundle
cd ../target
databricks bundle validate
databricks bundle deploy
```

## Run

**Step 1 — Source cleanup**:

```bash
cd source && databricks bundle run src_model_migration_cleanup
```

**Step 2 — Source export**:

```bash
cd source && databricks bundle run src_model_export
```

**Step 3 — Target cleanup**:

```bash
cd target && databricks bundle run tgt_model_migration_cleanup
```

**Step 4 — Target import + validate + reconciliation**:

```bash
cd target && databricks bundle run tgt_model_migration_register
```

Always run source workflows before target workflows.

## Workflows

**`src_model_migration_cleanup`** — Clears all contents of the source export volume.

**`src_model_export`** — Exports all model versions, metadata, and artifacts to the export volume.

**`tgt_model_migration_cleanup`** — `cleanup_volume` → `cleanup_models`. Clears target import volume and deletes all aliases, model versions, registered models, and migration experiments.

**`tgt_model_migration_register`** — `transfer` → `import_register` → `validate` → `reconciliation`. Copies export volume, imports into target catalog, validates, and produces a reconciliation report comparing version counts and aliases between source and target.

## One-Time Setup

If the catalogs, schemas, or volumes do not exist yet, create them via SQL. The export and transfer notebooks also create volumes inline (`CREATE VOLUME IF NOT EXISTS`).

## Known Limitations

- **Same metastore only**: Does not support cross-metastore or cross-cloud migration.
- **Source models are read-only**: No step modifies or deletes models in the source catalog.
- **UC grants/ACLs not migrated**: Permissions on models must be reapplied on the target catalog.
- **sklearn models**: The import notebook uses `mlflow.sklearn`; extend for other flavors as needed.
- **Run order**: Run source bundle before target bundle. Export must complete before transfer.
- **Volume paths only**: Uses `/Volumes/<catalog>/<schema>/<volume>/` paths.
- **No source experiment migration**: Source experiments are not copied. New migration experiments are created in the target to house re-logged model versions.
- **Target cleanup is destructive**: Deletes all model versions and entries for specified model names in the target.
