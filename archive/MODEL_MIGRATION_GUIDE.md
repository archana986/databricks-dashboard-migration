# MLflow Model Deep Clone Migration Guide

## Overview

This guide addresses the challenge of migrating MLflow models while preserving **all** metadata, including:
- Metrics from training runs
- Parameters from training runs
- Dataset lineage
- Source notebook references
- Tags and other metadata

## The Problem

When using `client.copy_model_version()` followed by simple re-logging, the destination model only gets:
- ✅ Model artifacts (weights, code)
- ✅ Model signature
- ❌ Training metrics
- ❌ Training parameters
- ❌ Source notebook reference
- ❌ Dataset lineage

For the EDA team migrating 200+ models, this loss of metadata is unacceptable for:
- Model governance and compliance
- Understanding model performance
- Debugging and troubleshooting
- Lineage tracking

## The Solution

The enhanced deep clone approach uses the following workflow:

```
1. Get Source Model Version → Extract Run ID
2. Fetch Run Details → Get all metrics, params, tags, datasets
3. Copy Model Artifacts → Use copy_model_version()
4. Create New Run in Destination → With proper experiment
5. Re-log All Metadata → Metrics, params, tags
6. Re-log Model → With signature and input example
7. Verify → Confirm all metadata preserved
```

## Key Functions

### 1. `get_source_run_metadata(model_name, model_version)`

Retrieves all metadata from the source model's training run:

```python
# Returns a dict with:
{
    'run_id': 'abc123...',
    'metrics': {'accuracy': 0.95, 'f1': 0.93, ...},
    'params': {'n_estimators': 100, 'max_depth': 10, ...},
    'tags': {'mlflow.databricks.notebookPath': '/path/to/notebook', ...},
    'run_info': <RunInfo object>,
    'dataset_inputs': <DatasetInputs object>,
    'model_version_details': <ModelVersion object>
}
```

**Critical:** This function extracts the original run ID from the model version, then fetches the complete run data.

### 2. Deep Clone with Metadata Preservation

The core process:

```python
# 1. Load copied model
model = mlflow.sklearn.load_model(model_uri)

# 2. Re-log all parameters
for key, value in source_metadata['params'].items():
    mlflow.log_param(key, value)

# 3. Re-log all metrics
for key, value in source_metadata['metrics'].items():
    mlflow.log_metric(key, value)

# 4. Preserve source notebook tags
mlflow.set_tag('mlflow.databricks.notebookPath', source_notebook_path)
mlflow.set_tag('mlflow.databricks.notebookID', source_notebook_id)

# 5. Add migration lineage
mlflow.set_tag('migration.source_run_id', source_run_id)

# 6. Re-log model with signature
mlflow.sklearn.log_model(model, "model", signature=signature, ...)
```

### 3. `migrate_model_with_full_metadata()`

Batch migration function that handles the complete process for a single model. Designed to be called in a loop for 200+ models.

## Critical Tags for Source Notebook Preservation

These Databricks-specific tags must be preserved:

| Tag | Purpose |
|-----|---------|
| `mlflow.databricks.notebookPath` | Full path to source notebook |
| `mlflow.databricks.notebookID` | Unique notebook identifier |
| `mlflow.databricks.notebookRevisionID` | Specific notebook version used |
| `mlflow.source.name` | Original source name |
| `mlflow.source.type` | Source type (NOTEBOOK, JOB, etc.) |
| `mlflow.user` | User who created the original run |

**Important:** When you view the migrated model in Databricks UI, clicking the source notebook link will work because these tags are preserved!

## Migration Lineage Tags

To maintain traceability, the solution adds:

| Tag/Param | Purpose |
|-----------|---------|
| `migration.source_model` | Original model name |
| `migration.source_version` | Original model version |
| `migration.source_run_id` | Original training run ID |
| `migration.type` | Migration method used |
| `migration.timestamp` | When migration occurred |

These create a clear audit trail from destination back to source.

## Dataset Lineage (MLflow 2.0+)

If the source model has dataset tracking:

```python
# Retrieve dataset inputs from source
dataset_inputs = source_run.inputs

# Re-log in destination
for dataset_input in dataset_inputs.dataset_inputs:
    mlflow.log_input(dataset_input.dataset, context="training")
```

This preserves:
- Dataset names and paths
- Dataset versions/snapshots
- Data profile information

## Batch Migration Strategy for 200+ Models

### Step 1: Prepare Model Inventory

Create a CSV file: `models_to_migrate.csv`

```csv
source_model,source_version,dest_schema,priority
catalog1.schema1.model_a,5,target_schema,high
catalog1.schema1.model_b,3,target_schema,high
catalog1.schema2.model_c,10,target_schema,medium
...
```

### Step 2: Test on Sample Models

```python
# Test with 2-3 models first
test_models = [
    {"source": "catalog1.schema1.model_a", "version": "5"},
    {"source": "catalog1.schema1.model_b", "version": "3"}
]

for model in test_models:
    result = migrate_model_with_full_metadata(
        source_model_name=model['source'],
        source_model_version=model['version'],
        dest_model_name=f"target_catalog.target_schema.{model['source'].split('.')[-1]}",
        dest_experiment_name='/Users/your.email/test_migration',
        dest_artifact_location='dbfs:/Volumes/target/test'
    )
    print(result)
```

### Step 3: Full Batch Execution

```python
import pandas as pd

# Load model inventory
models_df = pd.read_csv('models_to_migrate.csv')

# Track results
migration_results = []

for idx, row in models_df.iterrows():
    print(f"\n{'='*80}")
    print(f"Processing {idx+1}/{len(models_df)}: {row['source_model']}")
    print(f"{'='*80}")
    
    result = migrate_model_with_full_metadata(
        source_model_name=row['source_model'],
        source_model_version=row['source_version'],
        dest_model_name=f"target_catalog.{row['dest_schema']}.{row['source_model'].split('.')[-1]}",
        dest_experiment_name='/Users/your.email/batch_migration',
        dest_artifact_location=f"dbfs:/Volumes/target/{row['dest_schema']}/models"
    )
    
    migration_results.append(result)
    
    # Save progress every 10 models
    if (idx + 1) % 10 == 0:
        pd.DataFrame(migration_results).to_csv(f'migration_progress_{idx+1}.csv')

# Save final results
results_df = pd.DataFrame(migration_results)
results_df.to_csv('final_migration_results.csv')

# Summary
print(f"\nSuccessful: {results_df['success'].sum()}")
print(f"Failed: {(~results_df['success']).sum()}")
```

### Step 4: Handle Failures

```python
# Load results and retry failures
results_df = pd.read_csv('final_migration_results.csv')
failed_models = results_df[results_df['success'] == False]

retry_results = []
for idx, row in failed_models.iterrows():
    print(f"Retrying: {row['source_model']} v{row['source_version']}")
    print(f"Previous error: {row['error']}")
    
    # Retry with adjusted settings or custom signature
    result = migrate_model_with_full_metadata(
        source_model_name=row['source_model'],
        source_model_version=row['source_version'],
        # ... same params as before
    )
    retry_results.append(result)
```

## Verification Checklist

After migration, verify each model has:

### In Databricks UI:

1. **Model Registry Page:**
   - [ ] Model version appears
   - [ ] Description preserved
   - [ ] Tags visible

2. **Model Version Page:**
   - [ ] Metrics section shows all training metrics
   - [ ] Parameters section shows all hyperparameters
   - [ ] Source notebook link works
   - [ ] Artifacts present

3. **Run Details Page:**
   - [ ] All metrics logged
   - [ ] All parameters logged
   - [ ] Tags include `mlflow.databricks.notebookPath`
   - [ ] Migration tags present

### Programmatic Verification:

```python
# Get destination model
dest_model = client.get_model_version(dest_model_name, version)
dest_run = client.get_run(dest_model.run_id)

# Check metrics
assert len(dest_run.data.metrics) > 0, "No metrics found"

# Check parameters
assert len(dest_run.data.params) > 0, "No parameters found"

# Check source notebook
assert 'mlflow.databricks.notebookPath' in dest_run.data.tags, "Source notebook not preserved"

# Check migration lineage
assert 'migration.source_run_id' in dest_run.data.tags, "Migration lineage not recorded"
```

## Troubleshooting

### Issue: Source notebook reference not preserved

**Symptoms:**
- "Source" link in UI shows generic path or current notebook
- `mlflow.databricks.notebookPath` tag missing or wrong

**Solutions:**

1. Check if source model has the tag:
```python
source_model = client.get_model_version(SOURCE_MODEL_NAME, SOURCE_VERSION)
source_run = client.get_run(source_model.run_id)
print(source_run.data.tags.get('mlflow.databricks.notebookPath'))
```

2. If missing in source, manually add:
```python
mlflow.set_tag('mlflow.databricks.notebookPath', '/Users/original.user/TrainingNotebook')
mlflow.set_tag('mlflow.databricks.notebookID', '1234567890')
```

3. Verify tag was set:
```python
dest_run = client.get_run(dest_run_id)
assert 'mlflow.databricks.notebookPath' in dest_run.data.tags
```

### Issue: Metrics/parameters not appearing

**Symptoms:**
- Empty metrics/parameters section in UI
- Verification shows no data

**Solutions:**

1. Check source run has data:
```python
source_run = client.get_run(source_run_id)
print(f"Metrics: {len(source_run.data.metrics)}")
print(f"Params: {len(source_run.data.params)}")
```

2. Verify logging in destination:
```python
# Add debug prints
for key, value in source_metadata['metrics'].items():
    print(f"Logging metric: {key} = {value}")
    mlflow.log_metric(key, value)
```

3. Check for MLflow API version compatibility

### Issue: Dataset lineage not preserved

**Symptoms:**
- "Datasets" section empty in UI
- No dataset inputs logged

**Solutions:**

1. Check MLflow version (requires 2.0+):
```python
print(mlflow.__version__)  # Should be >= 2.0.0
```

2. Check if source has dataset tracking:
```python
source_run = client.get_run(source_run_id)
try:
    print(source_run.inputs)
except AttributeError:
    print("Dataset tracking not available")
```

3. Dataset logging is optional - model will work without it

### Issue: Signature mismatch

**Symptoms:**
- Error during model re-logging about signature
- Inference fails with schema errors

**Solutions:**

1. Inspect source model signature:
```python
source_model_uri = f"models:/{SOURCE_MODEL_NAME}/{SOURCE_VERSION}"
source_model = mlflow.sklearn.load_model(source_model_uri)
print(mlflow.models.get_model_info(source_model_uri).signature)
```

2. Create matching signature:
```python
from mlflow.types.schema import Schema, ColSpec

input_schema = Schema([
    ColSpec("type", "name"),
    # ... match source columns
])

signature = mlflow.models.ModelSignature(inputs=input_schema, outputs=output_schema)
```

3. Pass custom signature to migration function:
```python
result = migrate_model_with_full_metadata(
    ...,
    custom_signature=signature
)
```

## Performance Considerations

For 200+ models:

### Parallelization

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def migrate_single_model(model_config):
    return migrate_model_with_full_metadata(**model_config)

# Prepare configs
model_configs = [
    {
        'source_model_name': row['source_model'],
        'source_model_version': row['source_version'],
        # ...
    }
    for _, row in models_df.iterrows()
]

# Parallel execution (careful with rate limits)
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(migrate_single_model, cfg): cfg for cfg in model_configs}
    
    for future in as_completed(futures):
        cfg = futures[future]
        try:
            result = future.result()
            print(f"✅ {cfg['source_model_name']}")
        except Exception as e:
            print(f"❌ {cfg['source_model_name']}: {e}")
```

**Warning:** Be mindful of:
- Databricks API rate limits
- Workspace resource limits
- Storage quotas

### Chunking

Process in batches:

```python
BATCH_SIZE = 20

for i in range(0, len(models_df), BATCH_SIZE):
    batch = models_df.iloc[i:i+BATCH_SIZE]
    print(f"\nProcessing batch {i//BATCH_SIZE + 1}")
    
    batch_results = []
    for _, row in batch.iterrows():
        result = migrate_model_with_full_metadata(...)
        batch_results.append(result)
    
    # Save batch results
    pd.DataFrame(batch_results).to_csv(f'batch_{i//BATCH_SIZE + 1}_results.csv')
    
    # Small delay between batches
    time.sleep(5)
```

## Alternative: MLflow Export-Import Tool

The notebook mentions that MLflow export-import works well. For comparison:

### Export-Import Approach

**Pros:**
- Built-in tool designed for migration
- Automatically handles all metadata
- Works across workspaces

**Cons:**
- May not work for Unity Catalog to Unity Catalog
- Requires export/import files (storage overhead)
- Less flexible for transformations

### Deep Clone Approach (This Solution)

**Pros:**
- Works with Unity Catalog
- Programmatic control over process
- Can transform/customize during migration
- Can add migration tracking tags
- No intermediate files needed

**Cons:**
- More code to write/maintain
- Must manually preserve all metadata

**Recommendation:** Use deep clone approach for UC-to-UC migrations in Databricks Runtime 16.

## Best Practices

### 1. Test First
Always test on 2-3 models before full migration

### 2. Version Control
Save your model inventory and results:
```bash
git add models_to_migrate.csv
git add migration_results.csv
git commit -m "Model migration batch 1 - completed"
```

### 3. Documentation
Document any custom signatures or special handling:
```python
# models_with_custom_handling.yaml
special_models:
  - name: "catalog.schema.special_model"
    version: "5"
    reason: "Requires TensorFlow signature"
    custom_signature: "See notebook cell 42"
```

### 4. Monitoring
Track migration status:
```python
# Create dashboard of migration status
results_df = pd.read_csv('migration_results.csv')
print(f"Total: {len(results_df)}")
print(f"Success: {results_df['success'].sum()}")
print(f"Failed: {(~results_df['success']).sum()}")
print(f"Success rate: {results_df['success'].mean()*100:.1f}%")

# Check for patterns in failures
failed_df = results_df[~results_df['success']]
print(failed_df.groupby('error').size())
```

### 5. Communication
Keep stakeholders informed:
- Share progress updates
- Document known issues
- Provide access to migrated models

## FAQ

**Q: Will the source notebook link work in the migrated model?**  
A: Yes! By preserving the `mlflow.databricks.notebookPath` and related tags, the UI will show and link to the original training notebook.

**Q: Can I migrate models across workspaces?**  
A: Yes, but you need access to both workspaces and proper permissions. The source metadata retrieval requires read access to the source workspace.

**Q: What if the source run no longer exists?**  
A: The model version still stores the run_id, and as long as the run data hasn't been deleted, you can retrieve it. If deleted, you'll need to reconstruct metadata manually.

**Q: How do I handle different model types (PyTorch, TensorFlow, etc.)?**  
A: Change the loading/logging method:
```python
# PyTorch
model = mlflow.pytorch.load_model(model_uri)
mlflow.pytorch.log_model(model, "model", ...)

# TensorFlow
model = mlflow.tensorflow.load_model(model_uri)
mlflow.tensorflow.log_model(model, "model", ...)
```

**Q: Can I rename models during migration?**  
A: Yes! The `dest_model_name` parameter can be different from the source. Just ensure you track the mapping.

**Q: How long does it take to migrate 200 models?**  
A: Approximately 2-5 minutes per model (depending on size), so 200 models could take 6-17 hours. Consider parallelization and running overnight.

## Summary

This deep clone solution provides a comprehensive way to migrate MLflow models while preserving **all** metadata including:

✅ Training metrics  
✅ Training parameters  
✅ Source notebook references  
✅ Dataset lineage  
✅ Tags and metadata  
✅ Migration tracking

The approach is production-ready for Databricks Runtime 16 with Unity Catalog and designed specifically for large-scale migrations (200+ models).

## Support & Resources

- Enhanced notebook: `MLModel_DeepClone_Enhanced.ipynb`
- MLflow documentation: https://mlflow.org/docs/latest/
- Databricks Model Registry: https://docs.databricks.com/mlflow/model-registry.html
- Unity Catalog: https://docs.databricks.com/unity-catalog/

---

**Note:** This guide and notebook were created to address the specific requirements of the EDA team's model migration project.




