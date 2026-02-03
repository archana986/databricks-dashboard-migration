# Databricks Dashboard Migration Toolkit

**Created by Archana Krishnamurthy, Sr Delivery Solutions Architect, Databricks**

Complete solution for migrating Databricks Lakeview dashboards across workspaces with catalog/schema transformations.

## Features

- **Automated Discovery**: System table queries for dashboard inventory
- **Manual Approval**: Review and approve dashboards before migration
- **Catalog Transformation**: Remap catalog.schema.table references via CSV
- **Permission Migration**: Capture and apply ACLs
- **Schedule Migration**: Capture and apply schedules/subscriptions
- **Dual Deployment**: SDK Direct or Asset Bundle methods
- **Cross-Workspace Auth**: PAT or Service Principal OAuth M2M
- **Runtime Overrides**: CLI parameters for dry_run, target_path, deployment_method
- **Multi-Environment**: Dev, staging, prod configurations

## Prerequisites

- Databricks CLI v0.218.0+ installed locally
- CLI profiles configured in `~/.databrickscfg`
- Workspace Admin access on source and target workspaces
- Unity Catalog volume for storing artifacts
- SQL warehouse in target workspace
- Cross-workspace authentication configured (PAT or Service Principal)

## Getting Started - Two Options

### Option 1: CLI Execution (Recommended for Automation)

Clone the repository and run from your local machine:

```bash
# Clone the repository
git clone https://github.com/your-org/dashboard-migration.git

# Navigate to the migration folder
cd dashboard-migration/Customer-Folder/Catalog\ Migration

# Configure databricks.yml with your workspace details
# Then deploy and run (see Quick Start section below)
```

**Folder placement:** Place the cloned folder anywhere on your machine. All paths are relative to `databricks.yml`.

### Option 2: Interactive Notebook Execution

For interactive execution in the Databricks UI:

1. Clone the repo to your Databricks Workspace (Repos → Add Repo)
2. Open each notebook in sequence (Bundle_01 → 02 → 03 → 04)
3. Configure widgets/parameters in each notebook
4. Run cells interactively

**Best for:** First-time users, debugging, understanding the workflow.

## Quick CLI Setup

```bash
# Install CLI
pip install databricks-cli --upgrade
databricks --version  # Must be >= 0.218.0

# Configure profiles
databricks configure --profile source-workspace
databricks configure --profile target-workspace

# Test profiles
databricks workspace list --profile source-workspace
databricks workspace list --profile target-workspace
```

## Cross-Workspace Authentication

When deploying dashboards from source to target workspace, the source cluster needs to authenticate with the target workspace API. You have **two authentication options**:

### Why Cross-Workspace Auth is Required

```mermaid
flowchart LR
    subgraph source [Source Workspace]
        A[Migration Job] -->|API Call| B[Cluster/Serverless]
    end
    
    subgraph target [Target Workspace]
        C[Dashboards API]
        D[Permissions API]
    end
    
    B -->|Needs Auth| C
    B -->|Needs Auth| D
    
    style source fill:#e1f5ff
    style target fill:#e7f5e1
```

The source workspace cluster must authenticate to the target workspace to:
- Create dashboards via API
- Apply permissions
- Create schedules and subscriptions

### Authentication Flow Diagram

```mermaid
flowchart TD
    subgraph auth_options [Choose Authentication Method]
        PAT[PAT Token]
        SP[Service Principal OAuth]
    end
    
    subgraph pat_flow [PAT Token Flow]
        P1[Generate PAT in Target] --> P2[Store in Secret Scope]
        P2 --> P3[Job reads secret]
        P3 --> P4{Target has IP ACL?}
        P4 -->|Yes| P5[Whitelist Source IP]
        P4 -->|No| P6[Direct Access]
        P5 --> P7[API Access Granted]
        P6 --> P7
    end
    
    subgraph sp_flow [SP OAuth Flow]
        S1[Create Service Principal] --> S2[Add SP to Both Workspaces]
        S2 --> S3[Generate OAuth Secret]
        S3 --> S4[Store Client ID/Secret]
        S4 --> S5{Target has IP ACL?}
        S5 -->|Yes| S6[Whitelist Source IP]
        S5 -->|No| S7[Direct Access]
        S6 --> S8[API Access Granted]
        S7 --> S8
    end
    
    PAT --> pat_flow
    SP --> sp_flow
```

### Option A: PAT Token (Quick Setup)

Best for: Development, quick testing, simple migrations.

```bash
# 1. Generate PAT in TARGET workspace
#    User Settings → Developer → Access Tokens → Generate

# 2. Create secret scope in SOURCE workspace
databricks secrets create-scope migration_secrets --profile source-workspace

# 3. Store the PAT token
databricks secrets put-secret migration_secrets target_workspace_token --profile source-workspace
# (Enter the PAT when prompted)

# 4. Configure in databricks.yml
#    auth_method: "pat"
#    target_workspace_secret_scope: "migration_secrets"
```

**If target workspace has IP Access Lists enabled:**
```bash
# Find your source cluster's egress IP
# Run in a notebook on source workspace:
import requests
print(requests.get('https://api.ipify.org').text)

# Add to target workspace IP allowlist
databricks ip-access-lists create \
  --label "source-workspace-migration" \
  --list-type ALLOW \
  --ip-addresses "YOUR.IP.HERE/32" \
  --profile target-workspace
```

### Option B: Service Principal OAuth M2M (Production)

Best for: Production, automation, audit compliance, credential rotation.

```bash
# 1. Create Service Principal in Account Console
#    Account Console → User Management → Service Principals → Add

# 2. Add SP to BOTH workspaces
#    Account Console → Workspaces → [workspace] → Permissions → Add SP

# 3. Generate OAuth Secret
#    Account Console → Service Principals → [your SP] → Secrets → Generate
#    Save the Client ID and Client Secret

# 4. Create secret scope and store credentials
databricks secrets create-scope migration_secrets --profile source-workspace
databricks secrets put-secret migration_secrets sp_client_id --profile source-workspace
# (Enter Client ID when prompted)
databricks secrets put-secret migration_secrets sp_client_secret --profile source-workspace
# (Enter Client Secret when prompted)

# 5. Configure in databricks.yml
#    auth_method: "sp_oauth"
#    sp_secret_scope: "migration_secrets"
```

**If target workspace has IP Access Lists enabled:** Same IP whitelisting steps as PAT.

See `checklater/SP_OAUTH_SETUP.md` for detailed Service Principal setup guide.

### Comparison

| Feature | PAT Token | Service Principal OAuth |
|---------|-----------|------------------------|
| Setup Complexity | Simple | Medium |
| Security | Rotating required | Auto-rotating available |
| Audit Trail | User identity | SP identity (cleaner) |
| Best For | Dev/Test | Production |
| IP Whitelisting | Required if ACL enabled | Required if ACL enabled |

## Migration Flow

```mermaid
flowchart TD
    subgraph step1 [Step 1: Inventory]
        A[Source Workspace] -->|Query System Tables| B[Dashboard List]
        B -->|Save| C[inventory.csv]
    end
    
    subgraph step2 [Step 2: Manual Approval]
        C -->|Review in UI| D{Approve?}
        D -->|Yes| E[approved_inventory.csv]
        D -->|No| F[Excluded]
    end
    
    subgraph step3 [Step 3: Export and Transform]
        E -->|Export JSONs| G[Dashboard JSONs]
        G -->|Apply CSV Mappings| H[Transformed JSONs]
        H -->|Generate| I[Permissions CSV]
        H -->|Generate| J[Schedules CSV]
    end
    
    subgraph auth [Cross-Workspace Auth Required]
        K[Configure PAT or SP OAuth]
        L[Whitelist IP if needed]
    end
    
    subgraph step4 [Step 4: Deploy]
        H --> M{Method?}
        M -->|SDK Direct| N[API Deployment]
        M -->|Asset Bundle| O[Bundle Deployment]
        N --> P[Target Workspace]
        O --> P
    end
    
    step3 --> auth
    auth --> step4
```

## Quick Start

### 1. Configure Environment

```bash
cd "Customer-Folder/Catalog Migration"
```

Edit `databricks.yml` target variables:

```yaml
targets:
  dev:
    workspace:
      host: https://your-source-workspace.cloud.databricks.com
    variables:
      catalog: your_source_catalog
      volume_base: /Volumes/catalog/schema/migration_volume
      source_workspace_url: https://source-workspace.cloud.databricks.com
      target_workspace_url: https://target-workspace.cloud.databricks.com
      warehouse_id: "your_warehouse_id"  # 16-char hex ID
      auth_method: "pat"  # or "sp_oauth"
```

### 2. Create Catalog Mapping CSV

Upload to `/Volumes/catalog/schema/volume/mappings/catalog_schema_mapping.csv`:

```csv
old_catalog,old_schema,old_table,new_catalog,new_schema,new_table,old_volume,new_volume
dev_catalog,bronze,customers,prod_catalog,gold,customers,,
dev_catalog,bronze,,prod_catalog,gold,,,
```

### 3. Run Migration

```bash
# Deploy bundle (one-time setup)
databricks bundle deploy -t dev --profile source-workspace

# Step 1: Generate inventory
databricks bundle run inventory_generation -t dev --profile source-workspace

# Step 2: Manual approval (open Bundle_02 in Databricks UI)
# Review and approve dashboards interactively

# Step 3: Export & transform
databricks bundle run export_transform -t dev --profile source-workspace

# ⚠️  BEFORE STEP 4: Ensure cross-workspace auth is configured!
# - PAT token stored in secret scope, OR
# - SP OAuth credentials stored in secret scope
# - IP whitelisted if target has IP ACLs enabled

# Step 4: Deploy (dry run first - safe)
databricks bundle run generate_deploy -t dev --profile source-workspace

# Step 4: Deploy (live - creates resources)
databricks bundle run generate_deploy -t dev --params "dry_run_mode=false" --profile source-workspace
```

## Workflow Steps Detail

### Step 1: Inventory Generation

**Notebook**: `Bundle/Bundle_01_Inventory_Generation.ipynb`

Discovers all dashboards and generates inventory CSV.

```bash
databricks bundle run inventory_generation -t dev --profile source-workspace
```

### Step 2: Manual Review and Approval

**Notebook**: `Bundle/Bundle_02_Review_and_Approve_Inventory.ipynb`

**This step requires manual intervention in the Databricks UI:**
1. Open the notebook in your source workspace
2. Review the inventory table
3. Select/deselect dashboards to migrate
4. Run the approval cell to save `approved_inventory.csv`

### Step 3: Export and Transform

**Notebook**: `Bundle/Bundle_03_Export_and_Transform.ipynb`

Exports approved dashboards and applies catalog transformations.

```bash
databricks bundle run export_transform -t dev --profile source-workspace
```

**What it does:**
- Exports dashboard JSONs from source
- Captures permissions to `all_permissions.csv`
- Captures schedules to `all_schedules.csv`
- Applies CSV mappings to transform catalog references
- Saves to `exported/` and `transformed/` directories

### Step 3.5: Configure Cross-Workspace Authentication

**CRITICAL: Before Step 4, ensure authentication is configured!**

See [Cross-Workspace Authentication](#cross-workspace-authentication) section above for:
- PAT Token setup, OR
- Service Principal OAuth setup
- IP whitelisting (if target has IP ACLs)

### Step 4: Generate and Deploy

**Notebook**: `Bundle/Bundle_04_Generate_and_Deploy.ipynb`

Deploys dashboards to target workspace.

## Runtime Parameter Overrides

Step 4 supports runtime parameter overrides via `--params`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `dry_run_mode` | `true` | Preview only (no resources created) |
| `deployment_method` | `sdk_direct` | `sdk_direct` or `asset_bundle` |
| `target_parent_path` | `/Shared/Migrated_Dashboards_V2` | Target folder path |

### CLI Examples

```bash
# Dry run (default - safe preview)
databricks bundle run generate_deploy -t dev --profile source-workspace

# Live deployment
databricks bundle run generate_deploy -t dev \
  --params "dry_run_mode=false" \
  --profile source-workspace

# SDK deployment to custom path
databricks bundle run generate_deploy -t dev \
  --params "dry_run_mode=false,target_parent_path=/Shared/Production/Dashboards" \
  --profile source-workspace

# Asset Bundle deployment
databricks bundle run generate_deploy -t dev \
  --params "dry_run_mode=false,deployment_method=asset_bundle" \
  --profile source-workspace
```

## Deployment Methods

| Feature | SDK Direct (Default) | Asset Bundle |
|---------|---------------------|--------------|
| Dashboards | API calls | Bundle deploy |
| Permissions | Immediate | Bundle deploy |
| Schedules | Immediate | SDK post-deploy |
| Complexity | Simple | Medium |
| Best For | General migrations | IaC workflows |

## Project Structure

```
Catalog Migration/
├── databricks.yml                    # Bundle configuration
├── README.md                         # This file
├── catalog_schema_mapping_template.csv
├── Bundle/
│   ├── Bundle_01_Inventory_Generation.ipynb
│   ├── Bundle_02_Review_and_Approve_Inventory.ipynb
│   ├── Bundle_03_Export_and_Transform.ipynb
│   └── Bundle_04_Generate_and_Deploy.ipynb
├── helpers/
│   ├── __init__.py
│   ├── auth.py                       # Workspace authentication
│   ├── bundle_generator.py           # Asset bundle generation
│   ├── config_loader.py              # Configuration utilities
│   ├── config_validator.py           # Pre-flight validation
│   ├── dbutils_helper.py             # dbutils wrapper
│   ├── deployment_package.py         # Deployment data structures
│   ├── discovery.py                  # Dashboard discovery
│   ├── export.py                     # Dashboard export
│   ├── ip_acl_manager.py             # IP whitelist management
│   ├── permissions.py                # ACL management
│   ├── schedules.py                  # Schedule management
│   ├── sdk_deployer.py               # SDK deployment
│   ├── sp_oauth_auth.py              # Service Principal auth
│   ├── transform.py                  # Catalog transformation
│   └── volume_utils.py               # UC volume operations
└── checklater/                       # Deferred testing items
    ├── Setup_Migration_Secrets.ipynb
    └── SP_OAUTH_SETUP.md
```

## Configuration Reference

### Key Variables in databricks.yml

| Variable | Description |
|----------|-------------|
| `catalog` | Source catalog to scan |
| `volume_base` | Base path for artifacts (e.g., `/Volumes/cat/schema/vol`) |
| `source_workspace_url` | Source workspace URL |
| `target_workspace_url` | Target workspace URL |
| `warehouse_id` | Target warehouse ID (16-char hex) |
| `auth_method` | `pat` or `sp_oauth` |
| `target_workspace_secret_scope` | Secret scope for PAT |
| `sp_secret_scope` | Secret scope for SP OAuth |
| `transformation_enabled` | Enable catalog mapping (`true`/`false`) |
| `mapping_csv_path` | Path to mapping CSV |
| `apply_permissions` | Apply ACLs to target (`true`/`false`) |
| `apply_schedules` | Apply schedules to target (`true`/`false`) |
| `deployment_method` | `sdk_direct` or `asset_bundle` |
| `dry_run_mode` | Preview without deploying (`true`/`false`) |

## Troubleshooting

### Cross-Workspace Authentication Errors

**Error**: `403 Invalid access token` or `401 Unauthorized`

**Solution**:
1. Verify PAT/SP credentials are stored correctly:
   ```bash
   databricks secrets list-secrets migration_secrets --profile source-workspace
   ```
2. Verify PAT hasn't expired
3. For SP OAuth, verify SP is added to target workspace

### IP Whitelist Errors

**Error**: `403 IP not allowed` or connection timeout

**Solution**:
1. Get source cluster IP:
   ```python
   import requests
   print(requests.get('https://api.ipify.org').text)
   ```
2. Add to target workspace IP allowlist

### Bundle Deploy Errors

```bash
# Validate bundle
databricks bundle validate -t dev --profile source-workspace

# Force redeploy
databricks bundle deploy -t dev --profile source-workspace
```

## What Gets Migrated

**Included:**
- Dashboard structure and layout
- Datasets and queries
- Visualizations and filters
- Catalog/schema/table references (transformed)
- Permissions (ACLs)
- Scheduled refreshes
- Subscriptions

**Not Included:**
- Dashboard history/versions
- Comments and annotations

---

**Version**: 2.2.0  
**Last Updated**: February 2, 2026  
**Status**: Production Ready
