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
- **Cross-Workspace Auth**: Service Principal OAuth (recommended) or PAT Token
- **Runtime Overrides**: CLI parameters for dry_run, target_path, deployment_method
- **Multi-Environment**: Dev, staging, prod configurations

## Prerequisites

- Databricks CLI v0.218.0+ installed locally
- CLI profiles configured in `~/.databrickscfg`
- Workspace Admin access on source and target workspaces
- Unity Catalog volume for storing artifacts
- SQL warehouse in target workspace
- Cross-workspace authentication configured:
  - **Recommended**: Service Principal with OAuth M2M
  - **Alternative**: PAT Token (for quick dev/test)

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

When deploying dashboards from source to target workspace, the source cluster needs to authenticate with the target workspace API.

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

### Authentication Options Comparison

| Feature | Service Principal OAuth | PAT Token |
|---------|------------------------|-----------|
| **Recommendation** | **Recommended** | Fallback |
| Setup Complexity | Medium | Simple |
| Security | High (auto-rotating) | Lower (manual rotation) |
| Audit Trail | SP identity (clean) | User identity |
| Credential Lifetime | Configurable | Fixed expiry |
| Production Ready | Yes | Dev/Test only |
| IP Whitelisting | Required if ACL enabled | Required if ACL enabled |

### Authentication Flow

```mermaid
flowchart TD
    START[Choose Auth Method] --> DECIDE{Production Use?}
    
    DECIDE -->|Yes| SP[Service Principal OAuth]
    DECIDE -->|No/Quick Test| PAT[PAT Token]
    
    subgraph sp_flow [Recommended: Service Principal OAuth]
        S1[1. Create SP in Account Console] --> S2[2. Add SP to Both Workspaces]
        S2 --> S3[3. Generate OAuth Secret]
        S3 --> S4[4. Store in Secret Scope]
        S4 --> S5{Target has IP ACL?}
        S5 -->|Yes| S6[5. Whitelist Source IP]
        S5 -->|No| S7[Skip IP Setup]
        S6 --> S8[Ready to Migrate]
        S7 --> S8
    end
    
    subgraph pat_flow [Alternative: PAT Token]
        P1[1. Generate PAT in Target] --> P2[2. Store in Secret Scope]
        P2 --> P3{Target has IP ACL?}
        P3 -->|Yes| P4[3. Whitelist Source IP]
        P3 -->|No| P5[Skip IP Setup]
        P4 --> P6[Ready to Migrate]
        P5 --> P6
    end
    
    SP --> sp_flow
    PAT --> pat_flow
```

### Option 1: Service Principal OAuth M2M (Recommended)

**Best for:** Production, automation, compliance, secure credential management.

**Benefits:**
- Dedicated service identity (not tied to a user)
- Clean audit trail showing SP actions
- Credentials can be auto-rotated
- Follows Databricks security best practices

```bash
# Step 1: Create Service Principal in Account Console
# Account Console → User Management → Service Principals → Add

# Step 2: Add SP to BOTH workspaces
# Account Console → Workspaces → [workspace] → Permissions → Add SP
# Repeat for source AND target workspace

# Step 3: Generate OAuth Secret
# Account Console → Service Principals → [your SP] → Secrets → Generate
# IMPORTANT: Save the Client ID and Client Secret immediately

# Step 4: Create secret scope and store credentials
databricks secrets create-scope migration_secrets --profile source-workspace

databricks secrets put-secret migration_secrets sp_client_id --profile source-workspace
# (Enter Client ID when prompted)

databricks secrets put-secret migration_secrets sp_client_secret --profile source-workspace
# (Enter Client Secret when prompted)

# Step 5: Configure in databricks.yml
# Set these variables:
#   auth_method: "sp_oauth"
#   sp_secret_scope: "migration_secrets"
```

**If target workspace has IP Access Lists enabled:**
```bash
# Find source cluster's egress IP (run in notebook on source workspace)
import requests
print(requests.get('https://api.ipify.org').text)

# Add to target workspace IP allowlist
databricks ip-access-lists create \
  --label "source-workspace-migration" \
  --list-type ALLOW \
  --ip-addresses "YOUR.IP.HERE/32" \
  --profile target-workspace
```

See `checklater/SP_OAUTH_SETUP.md` for detailed Service Principal setup guide.

### Option 2: PAT Token (Alternative - Quick Setup)

**Best for:** Development, quick testing, when SP setup is not feasible.

**Note:** Use this only when Service Principal setup is not possible. PAT tokens are tied to a user account and require manual rotation.

```bash
# Step 1: Generate PAT in TARGET workspace
# User Settings → Developer → Access Tokens → Generate
# Set appropriate expiry (recommend 90 days max)

# Step 2: Create secret scope in SOURCE workspace
databricks secrets create-scope migration_secrets --profile source-workspace

# Step 3: Store the PAT token
databricks secrets put-secret migration_secrets target_workspace_token --profile source-workspace
# (Enter the PAT when prompted)

# Step 4: Configure in databricks.yml
# Set these variables:
#   auth_method: "pat"
#   target_workspace_secret_scope: "migration_secrets"
```

**If target workspace has IP Access Lists enabled:** Same IP whitelisting steps as SP OAuth above.

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
    
    subgraph auth [Step 3.5: Cross-Workspace Auth]
        K[Configure SP OAuth or PAT]
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
      
      # Authentication (choose one)
      auth_method: "sp_oauth"              # Recommended
      sp_secret_scope: "migration_secrets"
      
      # OR for quick dev/test:
      # auth_method: "pat"
      # target_workspace_secret_scope: "migration_secrets"
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

# Step 3.5: Configure cross-workspace auth (see section above)
# - Set up SP OAuth (recommended) or PAT token
# - Whitelist IP if target has IP ACLs

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

### Step 3.5: Configure Cross-Workspace Authentication

**CRITICAL: Before Step 4, ensure authentication is configured!**

Choose one:
- **Recommended**: Service Principal OAuth M2M (see [Option 1](#option-1-service-principal-oauth-m2m-recommended))
- **Alternative**: PAT Token (see [Option 2](#option-2-pat-token-alternative---quick-setup))

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
| `auth_method` | `sp_oauth` (recommended) or `pat` |
| `sp_secret_scope` | Secret scope for SP OAuth credentials |
| `target_workspace_secret_scope` | Secret scope for PAT token |
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
1. Verify credentials are stored correctly:
   ```bash
   databricks secrets list-secrets migration_secrets --profile source-workspace
   ```
2. For PAT: Verify token hasn't expired
3. For SP OAuth: Verify SP is added to target workspace with correct permissions

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

**Version**: 2.3.0  
**Last Updated**: February 2, 2026  
**Status**: Production Ready
