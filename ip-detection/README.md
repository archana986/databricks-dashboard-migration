# IP Detection Bundle

This is a standalone Databricks Asset Bundle for detecting the source cluster's egress IP address.

## Purpose

This bundle deploys a temporary job that runs the `Detect_Cluster_IP` notebook to identify your source cluster's egress IP. This IP is needed for whitelisting on the target workspace to enable cross-workspace deployment.

## Structure

```
ip-detection/
├── databricks.yml              # Bundle configuration
├── notebooks/
│   └── Detect_Cluster_IP.ipynb # IP detection notebook
└── README.md                   # This file
```

## Lifecycle

This bundle follows a **deploy → use → destroy** lifecycle:

1. **Deploy**: Creates the IP detection job in the workspace
2. **Use**: Runs the job once to detect the IP
3. **Destroy**: Removes the job and deployed resources

## Usage

### Manual Deployment

```bash
# From the project root, navigate to this directory
cd ip-detection

# Deploy the bundle
databricks bundle deploy -t dev --profile source-workspace

# Run the job to detect IP
databricks bundle run detect_cluster_ip -t dev --profile source-workspace

# Clean up after use
databricks bundle destroy -t dev --profile source-workspace --auto-approve
```

### Automated Deployment (Recommended)

Use the automated script from the project root:

```bash
# Dry-run mode (test without making changes)
./scripts/auto_setup_ip_acl.sh --dry-run

# Live mode (detect IP and whitelist)
./scripts/auto_setup_ip_acl.sh
```

The script automatically:
- Deploys this bundle
- Runs the IP detection job
- Captures the detected IP
- Whitelists it on the target workspace
- Cleans up the bundle resources

## What Gets Deployed

- **Job**: `IP_Detection_dev` - Temporary job for IP detection
- **Notebook**: Deployed to `/Workspace/.bundle/ip-detection/dev/notebooks/`
- **Cluster**: Single-node cluster (auto-terminates after job)

## What Gets Cleaned Up

When you run `databricks bundle destroy`:

### Removed
- ✅ IP Detection job
- ✅ Deployed notebook in workspace
- ✅ Bundle workspace directory (`.bundle/ip-detection/`)

### Preserved
- ✅ IP metadata in UC volume (`cluster_ip_metadata.json`)
- ✅ Local source files (this directory)
- ✅ Main dashboard migration bundle (unaffected)

## Testing

Test the bundle configuration:

```bash
# From project root
./scripts/test_ip_detection.sh --validate-only

# Full test with dry-run
./scripts/test_ip_detection.sh
```

## Integration with Main Workflow

This bundle is **independent** of the main dashboard migration bundle:

| Bundle | Purpose | Lifecycle |
|--------|---------|-----------|
| `ip-detection/` | Detect cluster IP | Temporary (deploy → destroy) |
| Main bundle | Deploy dashboards | Permanent (deploy → keep) |

Both bundles can coexist and operate independently.

## Troubleshooting

### Bundle validation fails

```bash
cd ip-detection
databricks bundle validate -t dev --profile source-workspace
```

Check for:
- Valid `databricks.yml` syntax
- Notebook exists at `notebooks/Detect_Cluster_IP.ipynb`
- Valid CLI profile configuration

### Job fails to run

Check the job run logs in the workspace UI at:
```
Workspace → Workflows → Jobs → IP_Detection_dev
```

Common issues:
- Cluster startup failure (check quota/permissions)
- Notebook execution errors (check notebook logic)
- Network restrictions (check workspace networking)

### Cleanup fails

Manual cleanup:
```bash
cd ip-detection
databricks bundle destroy -t dev --profile source-workspace --auto-approve
```

If the bundle was already destroyed, this command will safely indicate no resources to clean up.

## Notes

- This bundle uses **development mode** (`mode: development`)
- Deploys to workspace path: `/Workspace/.bundle/ip-detection/dev/`
- Job name: `IP_Detection_dev`
- Default profile: `source-workspace` (configurable via variables)
- Single-node cluster with Databricks Runtime 17.3.x

## Related Documentation

- [IP_DETECTION_BUNDLE_IMPROVEMENTS.md](../IP_DETECTION_BUNDLE_IMPROVEMENTS.md) - Detailed technical documentation
- [SUMMARY_IP_DETECTION_IMPROVEMENTS.md](../SUMMARY_IP_DETECTION_IMPROVEMENTS.md) - Quick reference guide
- [IP_ACL_AUTOMATION_GUIDE.md](../IP_ACL_AUTOMATION_GUIDE.md) - Complete IP whitelisting workflow
