# Service Principal OAuth M2M Setup Guide

Complete setup guide for cross-workspace authentication using Service Principal OAuth Machine-to-Machine (M2M).

## Overview

OAuth M2M with Service Principal is the **recommended approach** for cross-workspace authentication. It provides:

- Credential-based security (not IP-based)
- Full audit trail (SP identity logged)
- Works with dynamic IPs
- Follows Databricks best practices
- Compatible with serverless compute

## Prerequisites

Before starting, ensure you have:

- [ ] Service Principal created in Databricks Account Console
- [ ] Account Console UI access
- [ ] Workspace Admin access on **both** source and target workspaces
- [ ] Databricks CLI installed and configured

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ACCOUNT CONSOLE                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    Service Principal                                 │ │
│  │     ┌──────────────────┐    ┌──────────────────┐                    │ │
│  │     │   Client ID      │    │   OAuth Secret   │                    │ │
│  │     │   (Application)  │    │   (Credential)   │                    │ │
│  │     └────────┬─────────┘    └────────┬─────────┘                    │ │
│  └──────────────┼───────────────────────┼──────────────────────────────┘ │
└─────────────────┼───────────────────────┼───────────────────────────────┘
                  │                       │
       ┌──────────┴──────────┐   ┌────────┴────────┐
       ▼                     ▼   ▼                 ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ SOURCE WORKSPACE │   │ TARGET WORKSPACE │   │   SECRET SCOPE   │
│                  │   │                  │   │                  │
│  SP has access   │   │  SP has access   │   │  sp_client_id    │
│                  │   │                  │   │  sp_client_secret│
└──────────────────┘   └──────────────────┘   └──────────────────┘
         │                     ▲                      │
         │                     │                      │
         │    ┌────────────────┴──────────────────────┘
         │    │  Notebook reads credentials
         │    ▼  from secret scope
         │  ┌──────────────────┐
         │  │   NOTEBOOK       │
         │  │                  │
         │  │  get_target_     │──────────────▶ Connects to TARGET
         │  │  client_sp()     │               with SP credentials
         │  └──────────────────┘
         │
         └───────── Runs on SOURCE workspace
```

---

## Phase 1: Account Console Setup

### Step 1.1: Verify Service Principal Exists

1. Go to **Account Console**: https://accounts.cloud.databricks.com
2. Click **User management** in the left sidebar
3. Click **Service principals** tab
4. Verify your SP is listed
   - If not, click **Add service principal** to create one

### Step 1.2: Add SP to Source Workspace

1. In Account Console, click **Workspaces** in left sidebar
2. Click on your **Source Workspace** name
3. Go to **Permissions** tab
4. Click **Add permissions**
5. Search for your Service Principal name
6. Select it and set permission level: **User**
7. Click **Save**

### Step 1.3: Add SP to Target Workspace

1. Still in Account Console > Workspaces
2. Click on your **Target Workspace** name
3. Go to **Permissions** tab
4. Click **Add permissions**
5. Search for your Service Principal name
6. Select it and set permission level: **User**
7. Click **Save**

### Step 1.4: Create OAuth Secret

1. In Account Console, go to **User management**
2. Click **Service principals** tab
3. Click on your Service Principal name
4. Go to **Secrets** tab (or **OAuth secrets**)
5. Click **Generate secret**
6. Set lifetime: **365 days** (recommended for automation)
7. **CRITICAL**: Copy and save the displayed secret immediately!
   - It is shown **only once**
   - Store securely (password manager, etc.)
8. Note the **Client ID** (same as Application ID)

---

## Phase 2: Store Credentials in Secret Scope

Run these commands from your **local machine** with Databricks CLI configured.

### Step 2.1: Create Secret Scope

```bash
# Create the secret scope on SOURCE workspace
databricks secrets create-scope migration_secrets --profile source-workspace
```

If the scope already exists, this command will fail (that's OK).

### Step 2.2: Store SP Client ID

```bash
databricks secrets put-secret migration_secrets sp_client_id --profile source-workspace
```

When prompted, paste your **Service Principal Application ID** (Client ID).

### Step 2.3: Store SP Client Secret

```bash
databricks secrets put-secret migration_secrets sp_client_secret --profile source-workspace
```

When prompted, paste the **OAuth Secret** you saved in Step 1.4.

### Step 2.4: Verify Secrets

```bash
databricks secrets list-secrets migration_secrets --profile source-workspace
```

Expected output:
```
Key                   Last Updated Timestamp
--------------------  -------------------------
sp_client_id          2026-01-28T10:30:00.000Z
sp_client_secret      2026-01-28T10:30:00.000Z
```

---

## Phase 3: Configure Bundle

### Step 3.1: Update databricks.yml

Add or update these variables in your `databricks.yml`:

```yaml
variables:
  # Cross-Workspace Authentication
  auth_method:
    description: "Authentication method for target workspace: pat, sp_oauth"
    default: "sp_oauth"  # Changed from "pat" to "sp_oauth"
  
  sp_secret_scope:
    description: "Secret scope containing SP credentials"
    default: "migration_secrets"
```

### Step 3.2: Verify Variables in Job Parameters

Ensure your job's `base_parameters` include:

```yaml
base_parameters:
  # ... existing parameters ...
  auth_method: ${var.auth_method}
  sp_secret_scope: ${var.sp_secret_scope}
```

---

## Phase 4: Test Connection

### Option A: Test in Notebook

Run this in a notebook on the **SOURCE** workspace:

```python
from helpers.sp_oauth_auth import test_sp_connection

result = test_sp_connection(
    target_url="https://YOUR-TARGET-WORKSPACE.cloud.databricks.com",
    secret_scope="migration_secrets"
)

if result['success']:
    print(f"SUCCESS!")
    print(f"Connected to: {result['workspace_host']}")
    print(f"Service Principal: {result['user_info']}")
else:
    print(f"FAILED: {result['error']}")
    print(f"Error type: {result['error_type']}")
```

### Option B: Validate Credentials Only

```python
from helpers.sp_oauth_auth import validate_sp_credentials

result = validate_sp_credentials("migration_secrets")

if result['valid']:
    print("Credentials configured correctly")
else:
    for error in result['errors']:
        print(f"Error: {error}")
```

### Option C: Get Full Instructions

```python
from helpers.sp_oauth_auth import print_setup_instructions

print_setup_instructions("migration_secrets")
```

---

## Phase 5: Run Migration with SP Authentication

After deploying both bundles, run the migration jobs. The notebooks automatically use SP OAuth M2M authentication when `auth_method: "sp_oauth"` is configured.

```bash
# Source workspace: inventory, then export/transform
cd source
databricks bundle run src_dashboard_inventory --profile <source-profile>
# (Step 2: manual review in UI)
databricks bundle run src_dashboard_export_transform --profile <source-profile>

# Target workspace: transfer and deploy
cd ../target
databricks bundle run tgt_dashboard_register --profile <target-profile>
```

---

## Troubleshooting

### Error: "Secret scope does not exist"

**Cause**: Secret scope not created.

**Fix**:
```bash
databricks secrets create-scope migration_secrets --profile source-workspace
```

### Error: "sp_client_id not found"

**Cause**: Client ID not stored in secret scope.

**Fix**:
```bash
databricks secrets put-secret migration_secrets sp_client_id --profile source-workspace
# Paste your Service Principal Application ID when prompted
```

### Error: "401 Unauthorized"

**Cause**: OAuth secret is invalid or expired.

**Fix**:
1. Go to Account Console > User management > Service principals
2. Click your SP > Secrets tab
3. Generate a **new** secret
4. Update the secret scope:
   ```bash
   databricks secrets put-secret migration_secrets sp_client_secret --profile source-workspace
   # Paste the new secret
   ```

### Error: "403 Forbidden"

**Cause**: SP authenticated but lacks workspace permissions.

**Fix**:
1. Go to Account Console > Workspaces
2. Click target workspace > Permissions
3. Add your Service Principal with **User** or **Admin** role

### Error: "IP blocked by Databricks IP ACL"

**Cause**: Target workspace has IP Access Lists enabled, blocking your cluster IP.

**Fix** (choose one):
1. Manually add your cluster's egress IP to the target workspace's IP Access Lists
2. Or use the IP ACL setup notebook at `src/notebooks/Bundle_IP_ACL_Setup.ipynb` if available

### Error: "Connected to wrong workspace"

**Cause**: Client connected to a different workspace than expected.

**Fix**:
1. Verify `target_workspace_url` in databricks.yml is correct
2. Check that the URL matches exactly (including protocol and no trailing slash)

---

## Security Best Practices

1. **Secret Scope Access**: Limit who can read the secret scope
   ```bash
   databricks secrets put-acl migration_secrets <principal> READ
   ```

2. **Secret Rotation**: Rotate OAuth secrets periodically (recommended: every 90-180 days)

3. **Minimal Permissions**: Grant SP only the permissions needed:
   - **User** role is sufficient for dashboard migration
   - Avoid **Admin** unless required

4. **Audit Logging**: SP actions are logged in Databricks audit logs with the SP identity

5. **Separate SPs**: Consider separate SPs for different environments (dev, staging, prod)

---

## Comparison: SP OAuth vs PAT vs IP Whitelisting

| Aspect | SP OAuth M2M | PAT Token | IP Whitelisting |
|--------|--------------|-----------|-----------------|
| Security | High | Medium | Medium |
| Audit Trail | Full (SP identity) | User identity | Limited (IP only) |
| Secret Management | OAuth secrets | PAT rotation | None |
| Dynamic IPs | Works | Works | Requires detection |
| Serverless | Works | Works | Requires detection |
| Best Practice | Yes | Acceptable | Workaround |
| Setup Complexity | Medium | Simple | Medium |

---

## Quick Reference

### CLI Commands

```bash
# Create scope
databricks secrets create-scope migration_secrets --profile source-workspace

# Store credentials
databricks secrets put-secret migration_secrets sp_client_id --profile source-workspace
databricks secrets put-secret migration_secrets sp_client_secret --profile source-workspace

# Verify
databricks secrets list-secrets migration_secrets --profile source-workspace

# Test authentication (replace with your target workspace URL)
databricks auth login --host https://YOUR-TARGET-WORKSPACE.cloud.databricks.com --client-id <sp-client-id> --client-secret <sp-client-secret>
```

### Python Functions

```python
from helpers.sp_oauth_auth import (
    get_target_client_sp,      # Get authenticated client
    validate_sp_credentials,   # Check credentials exist
    test_sp_connection,        # Test full connection
    print_setup_instructions   # Print help
)
```

### databricks.yml Configuration

```yaml
variables:
  auth_method: "sp_oauth"
  sp_secret_scope: "migration_secrets"
```

---

## Related Documentation

- [README.md](../../README.md) - Main project documentation
- [docs/TARGET_JOB_RUN_AS_SP.md](../../docs/TARGET_JOB_RUN_AS_SP.md) - UC grants and run-as configuration
