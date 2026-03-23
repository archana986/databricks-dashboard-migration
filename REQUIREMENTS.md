# Dashboard Migration: Requirements and Design

This document states the **migration need**, the **two-bundle design** (source and target), and the **assumptions** under which the toolkit operates.

---

## 1. Migration Need

Organizations need to **migrate Databricks Lakeview (AI/BI) dashboards** from a source workspace to a target workspace while:

- Preserving **permissions**, **schedules**, and **subscriptions**
- Applying **catalog/schema remapping** (e.g., source catalog/schema → target catalog/schema)
- Avoiding manual, error-prone copy-paste and one-off scripts

Terraform does not support Lakeview dashboard migration. This toolkit fills that gap with an automated, bundle-based workflow.

---

## 2. Two-Bundle Design

The migration is split into **two Databricks Asset Bundles**:

| Bundle | Deploy where | Purpose |
|--------|----------------|--------|
| **Source bundle** | Source workspace | Run **inventory** (Step 1), **review/approve** (Step 2), and **export & transform** (Step 3). Writes all artifacts to a **Unity Catalog volume** (export volume). No direct calls to the target workspace. |
| **Target bundle** | Target workspace | **Transfer** dashboard artifacts from the source export volume to the target (same metastore), then **install** dashboards in the target workspace (deploy from volume using local `WorkspaceClient()`). |

**Why two bundles?**

- **Source** and **target** run in different workspaces. Each bundle is deployed and run in its own workspace.
- **Authentication** stays simple: OAuth in each workspace (no cross-workspace PAT or IP allowlisting).
- **Artifacts** move via a **shared Unity Catalog volume** that both workspaces can access (see assumption below).

---

## 3. Assumptions

### 3.1 Catalog (and export volume) available from source workspace

- The **source workspace** has a Unity Catalog **catalog** (and schema) to which it can write.
- The **export volume** used for migration artifacts (inventory CSVs, exported/transformed dashboard JSONs) is **bound to that catalog** and writable by the source workspace.
- All **copy and transfer of files** for the migration (inventory, export, transform outputs) happens **from and to this catalog/volume** while running jobs **on the source workspace**.

So: **the catalog (and the export volume) is bound to the source workspace** for the purpose of producing migration artifacts. No target credentials are required on the source.

### 3.2 Same metastore for source and target (for volume copy)

- For the **target** bundle, we assume **source and target workspaces share the same Unity Catalog metastore** (or that the export volume is otherwise accessible from the target, e.g., via volume replication or a shared location).
- The **target** job **transfers** files from the **source export volume** to an **import volume** in the target catalog (or the same volume if naming allows), then runs **installation** (deploy dashboards, apply permissions/schedules) **in the target workspace**.

### 3.3 Installation runs in the target workspace

- **Installation** (creating/updating dashboards, applying permissions and schedules) runs **only in the target workspace**, using the **target** bundle and **local OAuth** (`WorkspaceClient()` with no cross-workspace auth).
- No IP allowlisting or PAT for cross-workspace access is required for the deploy path.

### 3.4 Service principal access (automation)

- For **automation**, use a **service principal** registered in the **Databricks account** and added to **both** the source and the target **workspaces** (workspace-level access as required by your organization).
- Grant that principal **Unity Catalog** privileges appropriate for reading the **export volume** (source catalog) and reading/writing the **import volume** (target catalog), and for using the target **SQL warehouse** and workspace objects (notebooks, dashboard parent folder) used by the jobs.
- Optionally set the **target** job to **run as** that service principal so Lakeview and volume operations execute under the SP identity. See `docs/TARGET_JOB_RUN_AS_SP.md` in this repo.

---

## 4. Flow in Short

1. **Source workspace (source bundle):** Run inventory → review/approve → export & transform. All outputs go to the **export volume** in the catalog bound to the source.
2. **Target workspace (target bundle):** Run the **transfer** task (copy from source export volume to target import volume), then the **deploy** task (read from import volume and install dashboards in the target workspace).

See **README.md** and **SETUP.md** for step-by-step usage, variables, and prerequisites.
