# Lakeview dashboard migration toolkit

Move **Databricks Lakeview (AI/BI) dashboards** from a **source workspace** to a **target workspace** while keeping **permissions**, **schedules**, and **subscriptions** aligned with your new **catalog and schema** names.

This toolkit uses **two Databricks Asset Bundles**: you deploy and run the **source** bundle only in the source workspace, and the **target** bundle only in the target workspace. A **shared Unity Catalog metastore** (and volumes under it) carries the files between workspaces—no cross-workspace passwords in the notebooks for the main path.

**Who this is for:** Teams doing workspace consolidation, environment promotion (e.g. non-prod → prod), or catalog changes where dashboards must be recreated in a new workspace with updated table references.

---

## What you get

| Output | Description |
|--------|-------------|
| **Inventory** | List of dashboards to migrate (you review and approve in the UI). |
| **Export + transform** | Dashboard definitions plus metadata written to a Unity Catalog **export volume**. |
| **Transfer + install** | In the target workspace, files are copied to an **import volume**, then dashboards are created under your chosen **workspace folder**. |
| **Optional mapping** | Catalog/schema/table rewrites driven by a mapping file on the volume when transformation is enabled. |

**Out of scope for Terraform:** Lakeview objects, cross-workspace dashboard install, and rich schedule/subscription metadata are not covered by the Databricks Terraform provider the same way—this toolkit is built for that gap. See [WHY_THIS_TOOLKIT.md](WHY_THIS_TOOLKIT.md) for a comparison.

---

## How it fits together (two workspaces)

```mermaid
flowchart TB
  subgraph acct [Databricks account]
    SP[Service principal]
  end
  subgraph src_ws [Source workspace]
    SJOBS[Source bundle jobs]
    SVOL[(Export volume in source catalog)]
    SJOBS --> SVOL
  end
  subgraph metastore [Shared Unity Catalog metastore]
    SVOL -.->|same metastore| TVOL
  end
  subgraph tgt_ws [Target workspace]
    TJOBS[Target bundle job]
    TVOL[(Import volume in target catalog)]
    DASH[Dashboards in target folder]
    TJOBS --> TVOL
    TJOBS --> DASH
  end
  SP -->|access| src_ws
  SP -->|access| tgt_ws
```

**Typical roles**

- **Humans** use **two CLI profiles** (or OAuth logins)—one for source, one for target.
- **Automation** uses a **service principal** that is added to **both** workspaces and granted Unity Catalog rights on the export volume (source catalog) and import volume (target catalog), plus use of the target **SQL warehouse** and permissions on the **target folder** for dashboards.

---

## End-to-end workflow

```mermaid
sequenceDiagram
  participant You
  participant Src as Source workspace
  participant Vol as UC volumes
  participant Tgt as Target workspace
  You->>Src: Deploy source bundle
  You->>Src: Run inventory job
  You->>Src: Review and approve in Src_02
  You->>Src: Run export and transform job
  Src->>Vol: Write inventory, export, transform, CSVs
  You->>Tgt: Deploy target bundle
  You->>Tgt: Run transfer and deploy job
  Tgt->>Vol: Read export path, write import path
  Tgt->>Tgt: Create dashboards, apply metadata
```

---

## Quick start (two workspaces)

**Prerequisites (short):**

1. Databricks CLI v0.218+ with **two profiles** (source and target)
2. Source and target catalogs on the **same UC metastore**
3. Target **SQL warehouse** and target **tables** matching transformed references
4. Admin or sufficient rights on both workspaces

**Volumes and files to create:**

| What | When to create | How |
|------|----------------|-----|
| **Export volume** (source catalog) | Before running the Inventory job | `CREATE VOLUME IF NOT EXISTS <source_catalog>.<source_schema>.<export_volume>;` in the **source** workspace |
| **Import volume** (target catalog) | **Automatic** — the Transfer & Deploy job creates it | No action needed; the Transfer notebook runs `CREATE VOLUME IF NOT EXISTS` |
| **Mapping CSV** | Before running Export & Transform, if `transformation_enabled` is `"true"` | Create from the template (`catalog_schema_mapping_template.csv`), then upload: `databricks fs cp catalog_schema_mapping.csv dbfs:/Volumes/<source_catalog>/<source_schema>/<export_volume>/mappings/catalog_schema_mapping.csv --profile <source-profile>` |

See [PREREQUISITES_CHECKLIST.md](PREREQUISITES_CHECKLIST.md) for the full checklist with SQL and CLI commands.

### 1. Clone and configure locally

```bash
git clone https://github.com/archana986/databricks-dashboard-migration.git
cd databricks-dashboard-migration/dashboard-migration
```

Edit the `databricks.yml` in each bundle folder with your values. Each file has a clearly marked **EDIT HERE** section at the bottom — replace the placeholder values with your workspace URL, CLI profile, catalog, schema, volume, and warehouse details.

```bash
# Edit these two files:
source/databricks.yml   # Source workspace: host, profile, catalog, volume_base
target/databricks.yml   # Target workspace: host, profile, catalogs, schemas, volumes, warehouse_id, target folder
```

See [SETUP.md](SETUP.md) for the full variable reference.

### 2. Service principal in both workspaces (recommended)

**Create or pick an SP:**

1. Open **Account Console** → **User management** → **Service principals**.
2. **Add service principal** (or reuse an existing one). Copy its **Application (client) ID** (a UUID).

**Add the SP to both workspaces:**

3. Account Console → **Workspaces** → select workspace → **Permissions** → **Add** → select the SP → grant at least **User** access.
4. Repeat for both source and target workspaces.

**Grant Unity Catalog privileges** (run as a catalog owner or metastore admin):

```sql
-- Source catalog: read export volume
GRANT USE CATALOG ON CATALOG <source_catalog> TO `<sp_application_id>`;
GRANT USE SCHEMA  ON SCHEMA  <source_catalog>.<schema> TO `<sp_application_id>`;
GRANT READ VOLUME ON VOLUME  <source_catalog>.<schema>.<export_volume> TO `<sp_application_id>`;

-- Target catalog: read + write import volume
GRANT USE CATALOG  ON CATALOG <target_catalog> TO `<sp_application_id>`;
GRANT USE SCHEMA   ON SCHEMA  <target_catalog>.<schema> TO `<sp_application_id>`;
GRANT READ VOLUME, WRITE VOLUME ON VOLUME <target_catalog>.<schema>.<import_volume> TO `<sp_application_id>`;
```

**Grant warehouse and folder access:**

| Resource | Permission | Why |
|----------|-----------|-----|
| Target SQL warehouse | **Can use** | Dashboard queries run on this warehouse |
| Target workspace folder (`target_parent_path`) | **CAN MANAGE** | SP creates dashboards here |
| Job notebook paths (synced by bundle) | **CAN VIEW** | SP must read notebooks to execute tasks |

**Configure run-as in the target bundle** (so the job executes as the SP):

Add `run_as` to the job in `target/resources/tgt_dashboard_jobs.yml`:

```yaml
resources:
  jobs:
    tgt_dashboard_register:
      name: "[Tgt] Dashboard Transfer & Deploy"
      run_as:
        service_principal_name: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

Redeploy after this change: `databricks bundle deploy --profile YOUR_TARGET_PROFILE`

**OAuth client credentials (optional):** If any notebook needs to call another workspace directly (M2M), store client ID and secret in a secret scope — see [source/setup-guides/SP_OAUTH_SETUP.md](source/setup-guides/SP_OAUTH_SETUP.md). The default transfer + deploy path does **not** need this.

### 3. Deploy and run (source)

```bash
cd source
databricks bundle deploy --profile YOUR_SOURCE_PROFILE
databricks bundle run src_dashboard_inventory --profile YOUR_SOURCE_PROFILE
```

Open **`Src_02_Review_and_Approve_Inventory.ipynb`** in the **source** workspace UI. Review the dashboard list, filter out any you don't want to migrate, and type **CONFIRM** when prompted. The notebook saves the approved list as `inventory_approved.csv` under `dashboard_inventory_approved/` in your export volume. The Export & Transform job reads this exact file.

```bash
databricks bundle run src_dashboard_export_transform --profile YOUR_SOURCE_PROFILE
```

### 4. Deploy and run (target)

The target bundle deploys to a **separate workspace**. Before deploying, ensure the following are in place on the **target** workspace:

| Requirement | Details |
|-------------|---------|
| **CLI profile** | A separate profile in `~/.databrickscfg` pointing to the target workspace host |
| **Target catalog + schema** | Must exist and be accessible; must be on the **same UC metastore** as the source catalog |
| **Target tables** | Tables referenced by transformed dashboards must already exist in the target catalog |
| **SQL warehouse** | A warehouse the deploying user (or SP) can use; its ID goes in `warehouse_id` |
| **Target folder** | A workspace folder (e.g. `/Shared/Migrated_Dashboards`) where dashboards will be created; the user or SP must have `CAN_MANAGE` on it |
| **UC permissions** | The deploying user or SP needs `USE CATALOG`, `USE SCHEMA` on the target catalog/schema, and `READ VOLUME`/`WRITE VOLUME` on the import volume (if pre-created) |

```bash
cd ../target
databricks bundle deploy --profile YOUR_TARGET_PROFILE
databricks bundle run tgt_dashboard_register --profile YOUR_TARGET_PROFILE
```

The target job runs **transfer** (copy artifacts from the source export volume into the target import volume — both visible via the shared metastore) then **deploy** (create dashboards under `target_parent_path` and apply permissions/schedules when enabled).

---

## Jobs reference

| Bundle | Job name | CLI key | What it does |
|--------|----------|---------|--------------|
| Source | `[Src] Dashboard Inventory` | `src_dashboard_inventory` | Scans source dashboards and generates inventory CSV |
| Source | `[Src] Dashboard Export & Transform` | `src_dashboard_export_transform` | Exports and transforms approved dashboards |
| Target | `[Tgt] Dashboard Transfer & Deploy` | `tgt_dashboard_register` | Copies volume data and creates dashboards in target |

Between **Inventory** and **Export & Transform**, review and approve in **`Src_02_Review_and_Approve_Inventory.ipynb`** (manual, no scheduled job).

---

## Repository layout

Each bundle is **completely self-contained** with its own notebooks and helpers. No symlinks, no shared directories, no cross-dependencies.

```
dashboard-migration/
├── source/                          # Source bundle (deploy to source workspace)
│   ├── databricks.yml               #   EDIT HERE: source host, profile, catalog, volume
│   ├── resources/
│   │   └── src_dashboard_jobs.yml   #   Job definitions: Inventory + Export & Transform
│   ├── notebooks/
│   │   ├── Src_01_Inventory_Generation.ipynb
│   │   ├── Src_02_Review_and_Approve_Inventory.ipynb
│   │   └── Src_03_Export_and_Transform.ipynb
│   ├── helpers/                     #   Python modules (discovery, export, transform, etc.)
│   └── setup-guides/                #   SP OAuth setup doc + secrets notebook
│
├── target/                          # Target bundle (deploy to target workspace)
│   ├── databricks.yml               #   EDIT HERE: target host, profile, catalogs, warehouse
│   ├── resources/
│   │   └── tgt_dashboard_jobs.yml   #   Job definition: Transfer & Deploy
│   ├── notebooks/
│   │   ├── Tgt_01_Transfer_Volume.ipynb
│   │   └── Tgt_02_Deploy_Dashboards.ipynb
│   └── helpers/                     #   Python modules (deployment_package, sdk_deployer)
│
├── catalog_schema_mapping_template.csv   # Template for catalog/schema remapping
├── SETUP.md                         # Detailed setup and variable reference
├── PREREQUISITES_CHECKLIST.md       # Pre-flight checklist with SQL and CLI
└── WHY_THIS_TOOLKIT.md              # Comparison with Terraform
```

**Why two bundles?** Each bundle targets a different workspace (`workspace.host`). You run `databricks bundle deploy` from `source/` against the source workspace, and from `target/` against the target workspace. They never cross-reference each other at deploy time.

**Why separate code in each bundle?** The source bundle only needs inventory, export, and transform logic. The target bundle only needs transfer and deployment logic. Keeping them independent means you can hand off just the `target/` folder to a target workspace team without dragging in source-specific code.

---

## FAQ

**Why two bundles instead of one?**  
Source and target are **different workspaces**. Each bundle sets `workspace.host` for where notebooks run and contains only the notebooks and helpers it needs. That keeps auth simple and means each bundle is fully independent -- no symlinks, no shared directories.

**Why must source and target share a metastore?**  
The **transfer** step copies files between UC volume locations. Both catalogs must be visible to the **target** workspace’s compute for that copy to succeed. If your metastores differ, use **Delta Sharing**, **volume replication**, or another approved copy path—then adjust your process (not covered in the default notebooks).

**Where do files live?**  
Under the **export** volume path you set in the source bundle (subfolders such as `dashboard_inventory`, `exported`, `transformed`, etc.), then under the **import** volume after transfer.

**What is Step 2 for?**  
You narrow the dashboard list and **approve** what should be exported so large workspaces are not migrated by accident.

**Do I need a mapping CSV?**  
Only if **`transformation_enabled`** is `true` and you rely on catalog/schema/table rewrites. If transformation is off, you do not need the mapping file for that path (confirm your parameter defaults in the source bundle).

**Which profile do I use where?**  
Always use **`YOUR_SOURCE_PROFILE`** when running `databricks bundle` from **`source/`**, and **`YOUR_TARGET_PROFILE`** from **`target/`**, so the CLI talks to the correct host.

**Does the SP replace my user for everything?**  
No. You still deploy bundles and can run jobs as yourself. If you set **run as** on the target job to the SP, **only that job’s** notebook execution uses the SP for `WorkspaceClient()` and volume access **as configured**.

**What does the SP need on the target warehouse?**  
Ability to **run queries** on the warehouse you pass as `warehouse_id` / `warehouse_name` (e.g. “Can use” on the warehouse).

**Can I migrate without an SP?**  
Yes. Use your user identity for jobs and ensure **you** have UC and workspace permissions. SP is recommended for **automation and auditing**.

**What if transfer says there is no source data?**  
Confirm Step 3 finished successfully and paths match: **export volume** name in the source bundle equals the **`export_volume`** parameter expected by the target job’s transfer task (and catalogs/schemas are correct).

**What if dashboards show broken data?**  
Tables in the **target** catalog must exist and match **transformed** names. Validate mapping rules and run a few dashboards manually before a full cutover.

**Are schedules and permissions always applied?**  
They run when **`apply_permissions`** and **`apply_schedules`** are true in the target bundle and the SP or user has sufficient rights. Failures there may still leave dashboards created—check job logs.

**Is this idempotent?**  
Re-running may recreate or update objects depending on notebook logic and duplicate checks (`skip_duplicate_check`). Treat the first successful run as your template; read logs before repeating on production.

**Where do I get Lakeview / bundle help?**  
Use [Databricks documentation for Lakeview dashboards](https://docs.databricks.com/dashboards/index.html) and [Databricks Asset Bundles](https://docs.databricks.com/dev-tools/bundles/index.html).

**Can I test from one machine without committing secrets?**  
Yes. Auth is handled by your CLI profile (OAuth or Azure CLI) — no tokens are stored in `databricks.yml`. Edit the `host` and `profile` fields and run `databricks auth login` to authenticate.

---

## More documentation

| Document | Use |
|----------|-----|
| [SETUP.md](SETUP.md) | Full setup, secrets, troubleshooting |
| [PREREQUISITES_CHECKLIST.md](PREREQUISITES_CHECKLIST.md) | Pre-flight checklist |
| [WHY_THIS_TOOLKIT.md](WHY_THIS_TOOLKIT.md) | vs Terraform and decision guide |
| [source/setup-guides/SP_OAUTH_SETUP.md](source/setup-guides/SP_OAUTH_SETUP.md) | OAuth M2M and secret scope |

