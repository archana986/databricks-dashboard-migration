# Genie Space Migration Toolkit

Migrate **Databricks Genie Spaces** between **two different Databricks workspaces** using workflows and Databricks Asset Bundles.

This toolkit exports Genie Space configurations (including benchmarks and permissions) from a source workspace and deploys them to a target workspace. A **Service Principal with access to both workspaces** is used to run the migration jobs.

## What You Get

| Output | Description |
|--------|-------------|
| **Inventory** | List of Genie Spaces to migrate (you review and approve) |
| **Export** | Space configs with serialized_space, benchmarks, and permissions |
| **Deploy** | Create/update spaces in target workspace |
| **Reconciliation** | Validation report comparing source and target |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                SOURCE WORKSPACE (Workspace A)               │
│  source/                                                    │
│    Src_01_Inventory_Generation → Discover spaces + catalogs │
│    Src_02_Review_and_Approve   → Select spaces to migrate   │
│    Src_03_Export_Genie_Spaces  → Export configs + ACLs      │
│                           ↓                                 │
│              UC Export Volume                               │
└─────────────────────────────────────────────────────────────┘
                           ↓
              Service Principal (SP) with access to both
              - Runs jobs in both workspaces
              - UC metastore shared between workspaces
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                TARGET WORKSPACE (Workspace B)               │
│  target/                                                    │
│    Tgt_01_Transfer_Volume      → Copy to import volume      │
│    Tgt_00_Transform_Catalogs   → Map source→target catalogs │
│    Tgt_02_Deploy_Genie_Spaces  → Create/update spaces       │
│    Tgt_03_Apply_Permissions    → Set ACLs                   │
│    Tgt_04_Reconciliation       → Validate migration         │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

1. **Databricks CLI** v0.278.0+
2. **Two Databricks workspaces** (source and target) sharing the same Unity Catalog metastore
3. **Service Principal (SP)** with:
   - Access to **both workspaces** (source and target)
   - Permissions to run jobs and access Genie Spaces in both workspaces
   - Access to the shared Unity Catalog volumes for artifact transfer
4. **CLI profiles** configured for each workspace (can use SP credentials or user OAuth)

### 1. Set Up Service Principal

Create a Service Principal (SP) with access to both workspaces:

```bash
# Option A: Use existing SP
# Ensure the SP has workspace access and is added to both workspaces

# Option B: Create new SP via Account Console
# 1. Go to Account Console → User Management → Service Principals
# 2. Create SP and note the Application ID
# 3. Add SP to both source and target workspaces
# 4. Grant SP permissions:
#    - Source workspace: CAN_MANAGE on Genie Spaces, access to export volume
#    - Target workspace: CAN_MANAGE on target folder, access to import volume
```

Configure CLI profiles for each workspace (using SP or user credentials):

```bash
# Profile for source workspace
databricks auth login --host https://<source-workspace>.cloud.databricks.com -p source-profile

# Profile for target workspace  
databricks auth login --host https://<target-workspace>.cloud.databricks.com -p target-profile
```

### 2. Configure variables

**Recommended:** After you clone or fork [this repo](https://github.com/archana986/databricks-dashboard-migration), each bundle includes an empty `{}` `databricks.local.yml` so `bundle validate` works. Replace those contents with your real CLI profile, workspace host, catalogs, and warehouse ID (or copy from each `databricks.local.yml.example` and edit). **Do not commit** workspace-specific secrets back to a public fork; use a private branch or keep overrides local. See [SETUP.md](SETUP.md).

Alternatively, edit `targets.default` in each `databricks.yml` directly:

**Source bundle** (`source/databricks.yml`):
- `workspace.host` — source workspace URL
- `catalog`, `schema`, `volume` — export artifact location in Unity Catalog

**Target bundle** (`target/databricks.yml`):
- `workspace.host` — target workspace URL
- `source_catalog`, `source_schema`, `export_volume` — where the export volume lives on the shared metastore
- `target_catalog`, `target_schema`, `import_volume` — import volume in the target catalog
- `warehouse_id` — target SQL warehouse
- `target_parent_path` — folder for new Genie Spaces

### 3. Deploy and Run (Source Workspace)

```bash
cd source
databricks bundle validate --profile <source-profile>
databricks bundle deploy --profile <source-profile>

# Generate inventory
databricks bundle run src_genie_inventory --profile <source-profile>

# (Manual) Open Src_02_Review_and_Approve in the source workspace UI
# Review spaces, set confirmation=CONFIRM

# Export approved spaces
databricks bundle run src_genie_export --profile <source-profile>
```

### 4. Deploy and Run (Target Workspace)

```bash
cd ../target
databricks bundle validate --profile <target-profile>
databricks bundle deploy --profile <target-profile>

# Transfer, deploy, permissions, reconciliation (all in one)
databricks bundle run tgt_genie_deploy --profile <target-profile>
```

## Jobs Reference

| Bundle | Job | Description |
|--------|-----|-------------|
| Source | `src_genie_inventory` | Discover Genie Spaces + catalogs, generate inventory |
| Source | `src_genie_export` | Export approved spaces with benchmarks + permissions |
| Target | `tgt_genie_deploy` | Transfer → Transform Catalogs → Deploy → Permissions → Reconciliation |

### Deploy Job Task Flow

```
transfer → transform_catalogs → deploy → permissions → reconciliation
```

The `transform_catalogs` task applies `catalog_mapping.csv` automatically if `source_catalog` and `target_catalog` variables differ.

## What Migrates

| Component | Migrated? | Notes |
|-----------|-----------|-------|
| Space config | ✓ | Title, description, serialized_space |
| Benchmarks | ✓ | Embedded in serialized_space |
| Permissions | ✓ | Applied via Permissions API |
| Catalog references | ✓ | Transformed via catalog_mapping.csv |
| Conversation history | ✗ | Workspace-specific |
| UC function definitions | ✗ | Only references; functions must exist |

## Catalog Transformation

When source and target workspaces use different Unity Catalog catalogs, the toolkit automatically:

1. **Detects catalogs** in source spaces during inventory generation
2. **Generates `catalog_mapping.csv`** with all discovered catalogs
3. **Transforms references** in `serialized_space` before deployment

### How to Use

1. Run inventory: catalogs are detected and listed in `genie_inventory/catalog_summary.csv`
2. Export spaces: catalog references are preserved in JSON
3. On target, edit `catalog_mapping.csv`:
   ```csv
   source_catalog,target_catalog,notes
   prod_catalog,dev_catalog,# Used by: Sales Dashboard
   ```
4. Run deploy: catalogs are transformed automatically

## Service Principal Requirements

For cross-workspace migration, the Service Principal needs:

| Workspace | Required Permissions |
|-----------|---------------------|
| **Source** | `CAN_MANAGE` on Genie Spaces to export, access to UC export volume |
| **Target** | `CAN_MANAGE` on target workspace folder, access to UC import volume, access to SQL warehouse |
| **Unity Catalog** | Read/write on source and target volumes (both workspaces share same metastore) |

### Setting Up SP Permissions

```sql
-- Grant SP access to volumes (run in either workspace - shared metastore)
GRANT READ_VOLUME, WRITE_VOLUME ON VOLUME <catalog>.<schema>.<volume> TO `<sp-application-id>`;

-- Grant SP access to target catalog/schema for Genie data sources
GRANT USE CATALOG ON CATALOG <target_catalog> TO `<sp-application-id>`;
GRANT USE SCHEMA ON SCHEMA <target_catalog>.<target_schema> TO `<sp-application-id>`;
GRANT SELECT ON SCHEMA <target_catalog>.<target_schema> TO `<sp-application-id>`;
```

## Demo mode (single workspace)

For testing, you can run both bundles in the **same workspace**:

1. Point both `databricks.yml` (or `databricks.local.yml`) targets at the same workspace `host` and `profile`.
2. Use two different Unity Catalog names for export vs import (for example `demo_src` and `demo_tgt`) via `catalog` / `target_catalog` variables.

This validates the migration flow without two separate workspaces.

## Documentation

- [REQUIREMENTS.md](REQUIREMENTS.md) — Full requirements document
- [PLAN.md](PLAN.md) — Implementation plan

## References

- [Genie API Documentation](https://docs.databricks.com/api/workspace/genie)
- [DABs Genie Support PR](https://github.com/databricks/cli/pull/4191)
- [Benchmarks Documentation](https://docs.databricks.com/en/genie/benchmarks.html)
- [Service Principals](https://docs.databricks.com/administration-guide/users-groups/service-principals.html)
