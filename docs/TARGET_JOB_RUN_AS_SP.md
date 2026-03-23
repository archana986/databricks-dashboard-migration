# Run the target migration job as a Service Principal (SP)

Use this when you want **`tgt_dashboard_register`** (transfer + deploy notebooks) to execute as an SP instead of your user. That makes audits and ownership show the SP, and matches how many customers run automation.

**Note:** `Deploy_Dashboards_Target` uses `WorkspaceClient()` with **no explicit credentials** — it uses the **job run identity**. So if the job **runs as** the SP, API calls (Lakeview create, permissions, schedules) are performed **as that SP**.

This is separate from **SP OAuth** in `SP_OAUTH_SETUP.md`, which is for **cross-workspace** M2M clients. For a single workspace, **job run-as SP** is usually enough.

---

## 1. Create or pick a Service Principal

1. Open **Databricks Account Console** → **User management** → **Service principals**.
2. **Add service principal** (or reuse an existing automation SP).
3. Copy the SP **Application (client) ID** — a UUID like `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`. You will use this in the bundle as `service_principal_name` (see section 5).

Optional: under the SP → **Secrets** → **Generate secret** if you also use this SP for OAuth elsewhere. **Not required** for job run-as identity.

---

## 2. Add the SP to the workspace

1. Account Console → **Workspaces** → your workspace.
2. **Permissions** → **Add permissions** → select the SP.
3. Grant at least **User** (workspace access). Without this, the job cannot run as the SP in that workspace.

Repeat for **source** workspace too if it differs; for **one workspace** for both sides, one add is enough.

---

## 3. Workspace admin: allow jobs to run as SP

Depending on your account/workspace policy:

- Some workspaces require an admin to allow **running jobs as a service principal** (wording varies: e.g. entitlement or admin setting under **Jobs** / **Advanced**).
- If job creation or first run fails with an error about **run as** / **service principal** not allowed, a **workspace admin** must enable the relevant option for that workspace.

If you are workspace admin, check **Settings** → areas related to **Jobs** and **Service principals** for restrictions.

---

## 4. Access the SP needs (Unity Catalog + warehouse + folders)

Grant these to the SP’s identity in **Unity Catalog** (as **principal** = the service principal), not only to your user.

### 4.1 SQL warehouse

- **Can use** (or equivalent) on the SQL warehouse whose ID you pass as `warehouse_id` in the target bundle.  
- Without this, dashboard publish/query steps can fail.

### 4.2 Catalogs and volumes (transfer + deploy)

The **transfer** task reads the **export** volume and writes the **import** volume. The **deploy** task reads from the **import** volume and creates Lakeview dashboards.

Minimum to aim for (adjust names to your catalogs/schemas/volumes):

| Resource | Typical privilege | Why |
|----------|-------------------|-----|
| Source catalog | `USE CATALOG` | Resolve export volume |
| Source schema | `USE SCHEMA` | Volume lives under schema |
| Export volume | `READ VOLUME` | `Transfer_Volume_Dashboard` reads files |
| Target catalog | `USE CATALOG` | Resolve import volume |
| Target schema | `USE SCHEMA` | Import volume |
| Import volume | `READ VOLUME`, `WRITE VOLUME` | Clear/copy in transfer; deploy reads JSON/CSVs |

Example (illustrative — replace identifiers):

```sql
-- Unity Catalog: run as a user who can grant (e.g. metastore admin / catalog owner)

GRANT USE CATALOG ON CATALOG <source_catalog> TO `<sp_application_id>`;
GRANT USE SCHEMA ON SCHEMA <source_catalog>.<schema> TO `<sp_application_id>`;
GRANT READ VOLUME ON VOLUME <source_catalog>.<schema>.<export_volume> TO `<sp_application_id>`;

GRANT USE CATALOG ON CATALOG <your_target_catalog> TO `<sp_application_id>`;
GRANT USE SCHEMA ON SCHEMA <your_target_catalog>.default TO `<sp_application_id>`;
GRANT READ VOLUME, WRITE VOLUME ON VOLUME <your_target_catalog>.default.dashboard_migration_import TO `<sp_application_id>`;
```

If grants fail, a catalog owner or metastore admin must apply them.

### 4.3 Workspace folder for migrated dashboards (`target_parent_path`)

- The SP must be able to **create** Lakeview dashboards under `target_parent_path`. That usually means the SP is granted **CAN MANAGE** (or at least **CAN EDIT** / **CAN VIEW** as required by your workspace model) on that **folder** via workspace ACLs or by being in a group that owns the folder.
- If deploy fails with **403** or **permission denied** on `lakeview.create` / workspace path, extend folder permissions to the SP (or a group containing the SP).

### 4.4 Applying permissions and schedules (`apply_permissions` / `apply_schedules`)

- Updating dashboard ACLs and creating schedules/subscriptions often requires **stronger** rights than only creating a dashboard. If these steps fail for the SP, try:
  - Granting the SP **CAN MANAGE** on the target folder or dashboards, or
  - Temporarily setting `apply_permissions` / `apply_schedules` to `false` in the bundle to validate deploy-only, then tightening grants.

### 4.5 Notebooks used by the job

- The job tasks reference notebooks synced by the bundle (e.g. under a shared user path or `/Shared/...`). The SP must have **permission to read/execute** those notebook paths (typically **CAN VIEW** on the folder containing the notebooks).  
- After `bundle deploy`, confirm the SP can see the job’s `notebook_path` in the workspace.

---

## 5. Configure the job to run as the SP (Databricks Asset Bundle)

In **`target/resources/tgt_dashboard_jobs.yml`**, on the job `tgt_dashboard_register`, add **`run_as`** with the SP’s **application UUID**:

```yaml
resources:
  jobs:
    tgt_dashboard_register:
      name: "[Tgt] Dashboard Transfer & Deploy"
      run_as:
        service_principal_name: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
      description: "Transfer export volume to import volume, then deploy dashboards in this workspace."
      tags:
        ...
```

Use the same UUID as in Account Console for the SP (client / application ID).

Alternatively, some teams set `run_as` under a **bundle target** in `databricks.yml` / `databricks.local.yml` so only certain environments use the SP (see Databricks docs: [Specify a run identity for a Databricks Asset Bundles workflow](https://docs.databricks.com/aws/en/dev-tools/bundles/run-as)).

Redeploy after changing YAML:

```bash
cd "Customer-Work/Catalog Migration/target"
databricks bundle deploy --profile <profile-matching-workspace-host>
```

---

## 6. Verify

1. Run **`tgt_dashboard_register`** once.
2. In the job run UI, confirm **Run as** shows the **service principal**.
3. Confirm dashboards appear under `target_parent_path` and queries run with the configured warehouse.

---

## 7. Quick checklist

| Step | Done |
|------|------|
| SP exists in Account Console | ☐ |
| SP added to workspace with User access | ☐ |
| Workspace allows jobs to run as SP (if required) | ☐ |
| Warehouse: SP can use warehouse | ☐ |
| UC: READ export volume, READ+WRITE import volume (+ USE catalog/schema) | ☐ |
| Workspace: SP can access job notebooks and `target_parent_path` | ☐ |
| `run_as.service_principal_name` set in bundle + redeployed | ☐ |

---

## Related

- Cross-workspace OAuth client credentials: [src/setup-guides/SP_OAUTH_SETUP.md](../src/setup-guides/SP_OAUTH_SETUP.md)
- Optional single-workspace test: [SINGLE_WORKSPACE_OPTIONAL.md](SINGLE_WORKSPACE_OPTIONAL.md)
