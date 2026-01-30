# Databricks Lakeview Dashboard Migration

Migrate Databricks Lakeview dashboards between workspaces with catalog/schema transformations, preserving permissions and metadata.

> **📦 Asset Bundle Implementation**: This migration uses Databricks Asset Bundles for deployment. All configuration is in `databricks.yml` (single source of truth).

---

## 🚀 Quick Start

### Prerequisites

1. **Databricks CLI** installed and configured
   ```bash
   # Install Databricks CLI
   curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
   
   # Verify installation
   databricks version
   ```

2. **Unity Catalog Volume** created in your workspace
   ```sql
   -- Run in Databricks SQL Editor
   CREATE SCHEMA IF NOT EXISTS <your_catalog>.<your_schema>;
   CREATE VOLUME IF NOT EXISTS <your_catalog>.<your_schema>.dashboard_migration;
   ```

3. **Databricks authentication** configured
   ```bash
   # Configure authentication for your workspace
   databricks auth login --host https://your-workspace.cloud.databricks.com
   ```

---

## 📥 Installation

### Step 1: Clone Repository
```bash
git clone https://github.com/your-org/dashboard-migration.git
cd dashboard-migration
```

### Step 2: Customize Configuration

**IMPORTANT**: All configuration is in `databricks.yml`. Update the following sections:

#### A. Update Variables (lines 35-90)
```yaml
variables:
  # UPDATE THESE FOR YOUR ENVIRONMENT
  catalog:
    default: your_catalog_name  # Source catalog
  
  volume_base:
    default: /Volumes/your_catalog/your_schema/dashboard_migration  # Your volume path
  
  source_workspace_url:
    default: https://your-source-workspace.cloud.databricks.com  # Source workspace
  
  target_workspace_url:
    default: https://your-target-workspace.cloud.databricks.com  # Target workspace
  
  warehouse_name:
    default: your_warehouse_name  # SQL warehouse in target
```

#### B. Update Deployment Target (lines 170-180)
```yaml
targets:
  dev:
    workspace:
      host: https://your-workspace.cloud.databricks.com  # CHANGE THIS
    
    variables:
      catalog: your_catalog_name  # CHANGE THIS
      volume_base: /Volumes/your_catalog/your_schema/dashboard_migration  # CHANGE THIS
      source_workspace_url: https://your-workspace.cloud.databricks.com  # CHANGE THIS
      target_workspace_url: https://your-target.cloud.databricks.com  # CHANGE THIS
      warehouse_name: your_warehouse  # CHANGE THIS
```

---

## 🎯 Usage

### Method 1: Command Line (Recommended)

#### Deploy the Bundle
```bash
# Deploy to dev environment
databricks bundle deploy -t dev

# Verify deployment
databricks bundle validate -t dev
```

#### Run Migration Steps

**Step 1: Generate Inventory**
```bash
# Discover dashboards and create inventory CSV
# Also creates volume and both directories if they don't exist
databricks bundle run inventory_generation -t dev

# View job status
databricks jobs list-runs --limit 1
```

**Output:**
- Volume created (if not exists)
- `dashboard_inventory/` directory created with `inventory.csv`
- `dashboard_inventory_approved/` directory created (empty, ready for manual upload)

---

**Step 1a: Review & Approve** (MANUAL STEP - Choose One Option)

## Option A: Manual CSV Editing

1. **Download** the inventory CSV from the volume:
   - Via UI: Navigate to Catalog Explorer → Your Volume → `dashboard_inventory/inventory.csv`
   - Via code: Use `dbutils.fs.head()` or download via API

2. **Edit** the file:
   - Open in Excel or text editor
   - Delete rows for dashboards you don't want to migrate
   - Save your changes

3. **Upload** to approved location:
   - Via UI: Navigate to `dashboard_inventory_approved/` and upload as `inventory.csv`
   - Via code:
     ```python
     # Upload edited CSV
     volume_base = "/Volumes/your_catalog/your_schema/dashboard_migration"
     approved_path = f"{volume_base}/dashboard_inventory_approved/inventory.csv"
     
     # Read your edited CSV content
     with open('path/to/edited/inventory.csv', 'r') as f:
         csv_content = f.read()
     
     dbutils.fs.put(approved_path, csv_content, overwrite=True)
     print(f"✅ Uploaded to: {approved_path}")
     ```

4. **Verify** upload succeeded:
   ```python
   df = spark.read.csv(approved_path, header=True, inferSchema=True)
   print(f"✅ Approved: {df.count()} dashboards")
   display(df)
   ```

## Option B: Interactive Helper Notebook

1. **Open** the helper notebook in Databricks UI:
   `Bundle/Bundle_00a_Review_and_Approve_Inventory.ipynb`

2. **Run cells** to review and filter:
   - Cell 1: Configuration (auto-detects UI/CLI mode)
   - Cells 2-4: View stats and identify issues
   - Cell 5: Customize filters (remove failed lookups, inactive dashboards, etc.)
   - Cell 6: Review approved list

3. **Upload** with confirmation:
   - Cell 7: Type `CONFIRM` to upload approved inventory
   - Cell 8: Verify upload succeeded

**Benefits:**
- Interactive filtering with live dashboard counts
- Built-in issue detection (failed lookups, inactive dashboards, zero tables)
- Automatic upload with confirmation
- Immediate verification

See [`QC_WORKFLOW.md`](QC_WORKFLOW.md) for detailed step-by-step instructions for both options.

---

**Step 2: Export & Transform**

**Prerequisites:**
- ✅ Step 1 completed
- ✅ Approved CSV uploaded to `dashboard_inventory_approved/inventory.csv`

**Run:**
```bash
# Export dashboards and apply transformations
databricks bundle run export_transform -t dev
```

**What Step 2 does:**
- Verifies approved inventory exists and checks file age
- Fails with clear error if approved CSV is missing
- Exports only the approved dashboards
- Applies transformations (if enabled)
- Captures permissions

**Step 3: Generate & Deploy** (Final step)
```bash
# Generate asset bundle and deploy to target
databricks bundle run generate_deploy -t dev
```

---

### Method 2: Databricks UI

#### Option A: Run as Workflows

1. Navigate to **Workflows** in Databricks UI
2. Find jobs named:
   - `[Migration] 01 - Inventory Generation`
   - `[Migration] 02 - Export & Transform`
   - `[Migration] 03 - Generate & Deploy`
3. Click **Run Now** on each job sequentially

#### Option B: Run Notebooks Interactively

**⚠️ IMPORTANT**: For interactive execution, you must set up test widgets first!

1. **Open notebook** in Databricks: `Bundle/Bundle_00_Inventory_Generation.ipynb`

2. **Run Cell 0.5** (Interactive Testing Setup) to create widgets:
   ```python
   # Uncomment and customize these values:
   dbutils.widgets.text("catalog", "your_catalog_name")
   dbutils.widgets.text("volume_base", "/Volumes/your_catalog/your_schema/dashboard_migration")
   dbutils.widgets.text("source_workspace_url", "https://your-workspace.cloud.databricks.com")
   dbutils.widgets.text("inventory_path", "dashboard_inventory")
   dbutils.widgets.text("audit_lookback_days", "90")
   ```

3. **Run remaining cells** sequentially

4. Repeat for `Bundle_01` and `Bundle_02` notebooks

---

## 📂 Project Structure

```
dashboard-migration/
├── databricks.yml              # SINGLE SOURCE OF TRUTH - All configuration here
├── Bundle/
│   ├── Bundle_00_Inventory_Generation.ipynb  # Step 1: Discover dashboards
│   ├── Bundle_01_Export_and_Transform.ipynb  # Step 2: Export & transform
│   └── Bundle_02_Generate_and_Deploy.ipynb   # Step 3: Deploy to target
├── helpers/                     # Python helper functions
│   ├── __init__.py
│   ├── auth.py                 # Authentication
│   ├── discovery.py            # Dashboard discovery
│   ├── export.py               # Dashboard export
│   ├── transform.py            # Catalog/schema transformations
│   ├── permissions.py          # Permission management
│   ├── volume_utils.py         # Volume operations
│   └── bundle_generator.py     # Asset bundle generation
└── README.md                   # This file
```

---

## ⚙️ Configuration Reference

### Core Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `catalog` | Source catalog to scan | `production_data` |
| `volume_base` | Base volume path | `/Volumes/main/migration/dashboard_migration` |
| `source_workspace_url` | Source workspace URL | `https://source.cloud.databricks.com` |
| `target_workspace_url` | Target workspace URL | `https://target.cloud.databricks.com` |
| `warehouse_name` | SQL warehouse name | `migration_warehouse` |

### Path Variables (Relative to volume_base)

| Variable | Default | Description |
|----------|---------|-------------|
| `inventory_path` | `dashboard_inventory` | Inventory CSV location |
| `exported_path` | `exported` | Exported JSONs location |
| `transformed_path` | `transformed` | Transformed JSONs location |
| `mappings_path` | `mappings` | Mapping CSV location |
| `bundles_path` | `bundles` | Generated bundles location |

### Options

| Variable | Default | Description |
|----------|---------|-------------|
| `audit_lookback_days` | `90` | Days to look back for audit data |
| `transformation_enabled` | `true` | Apply catalog/schema transformations |
| `capture_permissions` | `true` | Export dashboard permissions |
| `apply_permissions` | `true` | Apply permissions to target |
| `permissions_dry_run` | `true` | Simulate permission application |
| `embed_credentials` | `true` | Embed credentials in dashboards |

---

## 🔄 Workflow

### Step 1: Inventory Generation

**What it does:**
- Discovers dashboards using system tables
- Fetches metadata (names, lineage, audit logs)
- Generates comprehensive inventory CSV

**Output:**
- `<volume_base>/dashboard_inventory/inventory.csv`

**Fields in inventory:**
- dashboard_id, dashboard_name, reference_count
- catalog_count, table_count, unique_tables
- last_accessed, first_accessed, unique_users
- complexity (High/Medium/Low)
- activity_level (Very Active/Active/Moderate/Inactive)

### Step 2: Export & Transform

**What it does:**
- Exports dashboard JSONs from inventory
- Applies catalog/schema/table transformations
- Exports permissions

**Inputs:**
- `inventory.csv` from Step 1
- `mappings/catalog_schema_mapping.csv` (create this file)

**Outputs:**
- `<volume_base>/exported/*.lvdash.json`
- `<volume_base>/transformed/*.lvdash.json`
- `<volume_base>/exported/*_permissions.json`

**Mapping CSV format:**
```csv
old_catalog,old_schema,old_table,new_catalog,new_schema,new_table
prod_data,sales,orders,dev_data,sales_test,orders
```

### Step 3: Generate & Deploy

**What it does:**
- Generates Databricks Asset Bundle structure
- Deploys dashboards to target workspace
- Applies permissions

**Output:**
- `<volume_base>/bundles/` with deployment bundle
- Dashboards created in target workspace

---

## 🛠️ Advanced Configuration

### Multiple Environments

Define multiple targets for different environments:

```yaml
targets:
  dev:
    mode: development
    workspace:
      host: https://dev-workspace.cloud.databricks.com
    variables:
      catalog: dev_catalog
      permissions_dry_run: "true"
  
  prod:
    mode: production
    workspace:
      host: https://prod-workspace.cloud.databricks.com
    variables:
      catalog: prod_catalog
      permissions_dry_run: "false"  # Actually apply in prod
```

Deploy to specific environment:
```bash
databricks bundle deploy -t dev
databricks bundle deploy -t prod
```

### Custom Cluster Configuration

By default, **Job 1 uses serverless compute** (fastest, recommended).

To use a standard cluster instead, uncomment in `databricks.yml`:

```yaml
inventory_generation:
  tasks:
    - task_key: generate_inventory
      # Uncomment for standard cluster:
      new_cluster:
        spark_version: "17.3.x-scala2.12"
        node_type_id: "i3.xlarge"
        num_workers: 2
        runtime_engine: PHOTON
```

---

## 📊 Monitoring & Troubleshooting

### View Job Logs

**CLI:**
```bash
# List recent runs
databricks jobs list-runs --limit 5

# Get specific run details
databricks runs get --run-id <run_id>

# View run output
databricks runs get-output --run-id <run_id>
```

**UI:**
1. Navigate to **Workflows**
2. Click on job name
3. View **Runs** tab
4. Click on specific run for detailed logs

### Common Issues

#### 1. `SCHEMA_NOT_FOUND` Error
**Solution**: Create the Unity Catalog schema and volume:
```sql
CREATE SCHEMA IF NOT EXISTS <catalog>.<schema>;
CREATE VOLUME IF NOT EXISTS <catalog>.<schema>.dashboard_migration;
```

#### 2. `ModuleNotFoundError: No module named 'helpers'`
**Solution**: Redeploy bundle to sync helper files:
```bash
databricks bundle deploy -t dev --force
```

#### 3. Dashboards Not Found in Inventory
**Possible causes:**
- Dashboards were deleted but lineage persists
- Incorrect catalog name in configuration
- Dashboards don't query the specified catalog

**Check audit logs** in notebook output for deletion events.

#### 4. Permission Application Fails
**Solution**: Ensure `permissions_dry_run: "true"` for testing, then set to `"false"` for actual application.

---

## 🔒 Security & Permissions

### Required Permissions

**Source Workspace:**
- READ access to dashboards
- READ access to system tables (`system.access.table_lineage`, `system.access.audit`)

**Target Workspace:**
- CREATE dashboard permissions
- WRITE access to Unity Catalog volume
- SQL warehouse USAGE permissions

### Authentication Methods

**OAuth (Recommended):**
- Uses notebook's built-in authentication
- No token management required
- Inherits your permissions

**Personal Access Token (Alternative):**
```yaml
variables:
  source_auth_method: pat
  source_pat_scope: migration_secrets
  source_pat_key: source_token
```

---

## 📝 Best Practices

1. **Test in Dev First**: Always test migration in dev environment
2. **Review Inventory**: Inspect `inventory.csv` before proceeding
3. **Dry Run Permissions**: Keep `permissions_dry_run: "true"` initially
4. **Backup Dashboards**: Export originals before transformation
5. **Version Control**: Commit `databricks.yml` changes to git
6. **Monitor Jobs**: Check logs for warnings/errors
7. **Incremental Migration**: Migrate in batches, not all at once

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## 📄 License

[Your License Here]

---

## 💬 Support

For issues or questions:
- GitHub Issues: [link]
- Documentation: [link]
- Contact: [email]

---

## 🎓 Additional Resources

- [Databricks Asset Bundles Documentation](https://docs.databricks.com/en/dev-tools/bundles/index.html)
- [Lakeview Dashboard API Reference](https://docs.databricks.com/api/workspace/lakeview)
- [Unity Catalog Volumes](https://docs.databricks.com/en/connect/unity-catalog/volumes.html)
- [System Tables Reference](https://docs.databricks.com/en/administration-guide/system-tables/index.html)

---

**Last Updated**: 2026-01-30  
**Version**: 2.0 (Asset Bundle Implementation)
