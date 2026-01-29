# Authentication Guide for Dashboard Migration

## Overview

This guide explains **why you need OAuth or PAT authentication** even when doing manual dashboard imports, and what each authentication is used for.

---

## TL;DR - What Do You Need?

### Required for ALL migration workflows:
- ✅ **Source Workspace Authentication** (OAuth or PAT)
- ✅ **Target Workspace Authentication** (OAuth or PAT)

### Why?
Even with manual dashboard import, the notebook needs to:
1. Read dashboard JSON from source volume
2. Write updated JSON to target volume
3. Migrate permissions programmatically

---

## What Authentication Is Used For

### Source Workspace (SOURCE_PAT_TOKEN or OAuth)

| Operation | Required | Why |
|-----------|----------|-----|
| **Read dashboard JSON from volume** | ✅ Yes | Access Unity Catalog volume files |
| **Get permissions from dashboard** | ✅ Yes | Export ACLs for migration |
| **Validate source exists** | ✅ Yes | Check file exists and is valid |

### Target Workspace (TARGET_PAT_TOKEN or OAuth)

| Operation | Required | Why |
|-----------|----------|-----|
| **Write updated JSON to volume** | ✅ Yes | Save rewritten dashboard to volume |
| **Set permissions on dashboard** | ✅ Yes | Apply ACLs after import |
| **Validate queries** | ⚠️  Optional | Test SQL queries before import |
| **Import dashboard programmatically** | ⚠️  Optional | Only if IMPORT_METHOD = "programmatic" |
| **Publish dashboard** | ⚠️  Optional | Only if programmatic import + PUBLISH_DASHBOARD=True |

---

## Migration Workflow with Manual Import

Here's what happens step-by-step:

### Steps 1-5: Preparation (REQUIRES AUTH)

1. **Connect to source workspace** 🔐 *Uses SOURCE_PAT_TOKEN*
   - Read dashboard JSON from source volume
   - Validate file exists and is .lvdash.json format

2. **Extract references**
   - Parse JSON (no auth needed)
   - Find catalog.schema.table references

3. **Load lookup file**
   - Read CSV from local file (no auth needed)
   - Cross-reference with discovered tables

4. **Rewrite references**
   - Update SQL queries (no auth needed)
   - Apply catalog/schema mappings

5. **Save to target volume** 🔐 *Uses TARGET_PAT_TOKEN*
   - Write updated JSON to target workspace volume

### Step 6: Validate Queries (OPTIONAL - requires auth if enabled)

6. **Validate queries** 🔐 *Uses TARGET_PAT_TOKEN*
   - Test SQL statements against target warehouse
   - Confirm tables exist and are accessible

### Step 7: Import Dashboard (MANUAL - no auth needed for UI)

7. **Manual import via UI** 👤 *Uses your browser session*
   - You log into target workspace UI
   - Upload .lvdash.json from target volume
   - Dashboard created with new ID

**OR** (if IMPORT_METHOD = "programmatic"):

7. **Programmatic import** 🔐 *Uses TARGET_PAT_TOKEN*
   - Automated API call to create dashboard
   - Returns dashboard ID automatically

### Step 7.5: Permissions Migration (REQUIRED - requires auth)

7.5. **Migrate permissions** 🔐 *Uses BOTH tokens*
   - **Source**: Get ACLs from source dashboard
   - **Target**: Set ACLs on target dashboard
   - Save backup to JSON file

### Step 8: Publish (OPTIONAL)

8. **Publish dashboard**
   - Manual: Click "Publish" in UI 👤 *Uses your browser*
   - Programmatic: API call 🔐 *Uses TARGET_PAT_TOKEN*

---

## Authentication Methods

### Option 1: Personal Access Tokens (PAT) - Simplest

**When to use:**
- Quick migrations
- Testing
- Personal workspaces
- One-time migrations

**Setup:**

```python
# Configuration in notebook
AUTH_METHOD = "PAT"

# Source workspace token
SOURCE_PAT_TOKEN = "dapi..."  # Or use dbutils.secrets.get()

# Target workspace token  
TARGET_PAT_TOKEN = "dapi..."  # Or use dbutils.secrets.get()
```

**How to create PAT tokens:**

1. Log into workspace
2. Click your profile → Settings
3. Developer → Access tokens
4. Generate new token
5. Copy and save securely

**Permissions needed:**
- Source: Read access to volumes, dashboards
- Target: Write access to volumes, dashboards, permissions

---

### Option 2: OAuth (Azure AD Service Principal) - Production

**When to use:**
- Production environments
- Automated/scheduled migrations
- Multiple dashboard migrations
- Enterprise deployments

**Setup:**

```python
# Configuration in notebook
AUTH_METHOD = "OAUTH"

# Set environment variables (or use Databricks secrets):
# export ARM_CLIENT_ID="..."
# export ARM_TENANT_ID="..."
# export ARM_CLIENT_SECRET="..."

# Tokens not needed - SDK uses OAuth automatically
SOURCE_PAT_TOKEN = None
TARGET_PAT_TOKEN = None
```

**Prerequisites:**
- Azure AD service principal created
- Service principal added to both workspaces
- Appropriate permissions granted

---

## What If I Only Do Manual Import?

### You STILL need authentication for:

1. ✅ **Reading source volume** (SOURCE_PAT_TOKEN)
   ```
   /Volumes/{SOURCE_CATALOG}/{SOURCE_SCHEMA}/{SOURCE_VOLUME}/dashboard.lvdash.json
   ```

2. ✅ **Writing target volume** (TARGET_PAT_TOKEN)
   ```
   /Volumes/{TARGET_CATALOG}/{TARGET_SCHEMA}/{TARGET_VOLUME}/dashboard_updated.lvdash.json
   ```

3. ✅ **Permissions migration** (BOTH tokens)
   - Get permissions from source dashboard
   - Set permissions on target dashboard

### You DON'T need authentication for:

1. ❌ Manual dashboard import (uses UI login)
2. ❌ Manual publish (uses UI login)

---

## Common Scenarios

### Scenario 1: Full Automation

```python
IMPORT_METHOD = "programmatic"
PUBLISH_DASHBOARD = True
AUTH_METHOD = "PAT"  # or "OAUTH"
```

**Authentication used for:**
- ✅ Read source volume
- ✅ Write target volume
- ✅ Import dashboard via API
- ✅ Migrate permissions
- ✅ Publish dashboard via API

---

### Scenario 2: Manual Import + Auto Permissions (RECOMMENDED)

```python
IMPORT_METHOD = "manual"
AUTH_METHOD = "PAT"  # or "OAUTH"
```

**Authentication used for:**
- ✅ Read source volume
- ✅ Write target volume
- ✅ Migrate permissions
- ❌ Import (done in UI)
- ❌ Publish (done in UI)

**Why this works:**
- You import via UI (uses your browser login)
- Permissions migrate automatically (uses PAT/OAuth)
- Best of both worlds!

---

### Scenario 3: Manual Import + Manual Permissions

```python
IMPORT_METHOD = "manual"
# Skip permissions migration by not setting SOURCE_DASHBOARD_ID
SOURCE_DASHBOARD_ID = None
```

**Authentication used for:**
- ✅ Read source volume
- ✅ Write target volume
- ❌ Permissions (set manually in UI)
- ❌ Import (done in UI)
- ❌ Publish (done in UI)

**Note:** This defeats the purpose - might as well not use the notebook!

---

## Security Best Practices

### 1. Use Databricks Secrets (NOT plain text)

**Good:**
```python
SOURCE_PAT_TOKEN = dbutils.secrets.get(scope="my-scope", key="source-pat")
TARGET_PAT_TOKEN = dbutils.secrets.get(scope="my-scope", key="target-pat")
```

**Bad:**
```python
SOURCE_PAT_TOKEN = "dapi1234567890abcdef..."  # DON'T DO THIS!
```

### 2. Use Service Principals for Production

```python
AUTH_METHOD = "OAUTH"
# Uses service principal, not personal account
```

### 3. Limit Token Scope

- Create separate tokens for migrations only
- Set expiration dates
- Use least-privilege principle

### 4. Rotate Tokens Regularly

- Change PAT tokens quarterly
- Update secrets in Databricks
- Audit token usage

---

## Troubleshooting

### Error: "Permission denied reading volume"

**Problem:** SOURCE_PAT_TOKEN lacks volume access

**Solution:**
```sql
-- Grant access to source volume
GRANT READ FILES ON VOLUME source_catalog.source_schema.source_volume 
  TO `your.service.principal@databricks.com`;
```

---

### Error: "Permission denied writing volume"

**Problem:** TARGET_PAT_TOKEN lacks volume access

**Solution:**
```sql
-- Grant access to target volume
GRANT WRITE FILES ON VOLUME target_catalog.target_schema.target_volume 
  TO `your.service.principal@databricks.com`;
```

---

### Error: "Could not retrieve permissions: 403"

**Problem:** SOURCE_PAT_TOKEN lacks dashboard permissions

**Solution:**
- Ensure PAT user has CAN_MANAGE on source dashboard
- Or use admin credentials for source workspace

---

### Error: "Could not set permissions: 403"

**Problem:** TARGET_PAT_TOKEN lacks permissions API access

**Solution:**
- Ensure PAT user has workspace admin role
- Or grant CAN_MANAGE on target dashboard

---

## Summary

### Always Need Authentication For:
1. ✅ Volume operations (read source, write target)
2. ✅ Permissions migration (read source ACLs, write target ACLs)

### Sometimes Need Authentication For:
3. ⚠️  Query validation (target workspace - optional)
4. ⚠️  Programmatic import (target workspace - if enabled)
5. ⚠️  Programmatic publish (target workspace - if enabled)

### Never Need Authentication For (uses UI login):
6. ❌ Manual dashboard import via UI
7. ❌ Manual publish via UI

---

## Quick Reference

| Task | Source Auth | Target Auth | Manual Alternative |
|------|-------------|-------------|-------------------|
| Read dashboard JSON from volume | ✅ Required | - | ❌ No |
| Write updated JSON to volume | - | ✅ Required | ❌ No |
| Get source permissions | ✅ Required | - | ⚠️  Manual copy/paste |
| Set target permissions | - | ✅ Required | ⚠️  Manual via UI |
| Import dashboard | - | ⚠️  Optional | ✅ Yes (UI) |
| Publish dashboard | - | ⚠️  Optional | ✅ Yes (UI) |
| Validate queries | - | ⚠️  Optional | ✅ Yes (manual test) |

**Legend:**
- ✅ = Can be done manually
- ⚠️  = Can be done manually but tedious
- ❌ = Cannot be done manually (must use auth)

---

## Configuration Template

```python
# ============================================================================
# AUTHENTICATION CONFIGURATION
# ============================================================================

# Choose authentication method
AUTH_METHOD = "PAT"  # or "OAUTH"

# For PAT authentication
SOURCE_PAT_TOKEN = dbutils.secrets.get(scope="migration", key="source-pat")
TARGET_PAT_TOKEN = dbutils.secrets.get(scope="migration", key="target-pat")

# For OAuth authentication (set environment variables)
# export ARM_CLIENT_ID="your-client-id"
# export ARM_TENANT_ID="your-tenant-id"
# export ARM_CLIENT_SECRET="your-client-secret"

# ============================================================================
# IMPORT CONFIGURATION
# ============================================================================

# Choose import method
IMPORT_METHOD = "manual"  # "programmatic" or "manual"

# If programmatic, set warehouse ID
TARGET_WAREHOUSE_ID = None  # Set if using programmatic import

# ============================================================================
# PERMISSIONS CONFIGURATION (REQUIRED)
# ============================================================================

# Source dashboard ID (REQUIRED for permissions migration)
SOURCE_DASHBOARD_ID = "01f0fb1aabc91dc88f09650d5c307b00"

# User/group mapping (if names differ between workspaces)
USER_GROUP_MAPPING = {
    # "source_user@company.com": "target_user@company.com"
}
```

---

**Ready to migrate?** Follow the setup in `02_Migrate_Dashboard.ipynb` with proper authentication configured!
