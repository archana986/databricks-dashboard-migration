# Dashboard Inventory Fields Reference

## Overview

The dashboard inventory captures **15 comprehensive fields** including lineage statistics, access patterns, and publication status to help you make informed migration decisions.

**NEW in Latest Version:**
- `catalog_count` - Number of unique catalogs referenced
- `table_count` - Number of unique tables referenced
- Workspace-filtered queries for accuracy
- Spark SQL optimization for 2-5x faster discovery
- `DASHBOARD_V3` entity type for AI/BI dashboards

---

## Core Identity Fields

| Field | Description | Source | Always Present |
|-------|-------------|--------|----------------|
| `dashboard_id` | Unique dashboard identifier | Lakeview SDK | ✅ Yes |
| `dashboard_name` | Display name of the dashboard | Lakeview SDK (`display_name`) | ✅ Yes |
| `path` | Workspace path where dashboard is located | Lakeview SDK | ✅ Yes |
| `parent_folder` | Parent folder extracted from path | Derived from `path` | ✅ Yes |

---

## Publication & Access Metadata

| Field | Description | Source | Always Present |
|-------|-------------|--------|----------------|
| `published` | Whether dashboard is published (Yes/No) | Lakeview SDK (`get_published`) | ✅ Yes* |
| `published_version` | Version number of published dashboard | Lakeview SDK | ⚠️ Only if published |
| `last_accessed` | Last time dashboard was viewed | `system.access.audit` logs | ✅ Yes** |
| `lifecycle_state` | Current state (ACTIVE, TRASHED, etc.) | Lakeview SDK | ✅ Yes |

\* *When `include_published_status=True`*  
\*\* *Shows "Never" if not accessed in last 90 days*

---

## Technical Metadata

| Field | Description | Source | Always Present |
|-------|-------------|--------|----------------|
| `warehouse_id` | SQL Warehouse used by dashboard | Lakeview SDK | ✅ Yes |
| `created_time` | When dashboard was created | Lakeview SDK (`create_time`) | ✅ Yes |
| `updated_time` | Last modification timestamp | Lakeview SDK (`update_time`) | ✅ Yes |
| `etag` | Entity tag for version control | Lakeview SDK | ✅ Yes |
| `link` | Direct URL to dashboard | Constructed | ✅ Yes |

---

## Data Lineage Metadata (NEW)

| Field | Description | Source | Always Present |
|-------|-------------|--------|----------------|
| `catalog_count` | Number of unique catalogs referenced | `system.access.table_lineage` | ✅ Yes* |
| `table_count` | Number of unique tables referenced | `system.access.table_lineage` | ✅ Yes* |

\* *When `include_metadata=True`; shows 0 if no lineage found*

---

## How Each Field is Captured

### 1. Core Dashboard Metadata (Lakeview SDK)

```python
full = client.lakeview.get(dashboard_id)

# Captured fields:
- dashboard_id
- dashboard_name (from full.display_name)
- path (from full.path)
- warehouse_id (from full.warehouse_id)
- created_time (from full.create_time)
- updated_time (from full.update_time)
- lifecycle_state (from full.lifecycle_state.value)
- etag (from full.etag)
```

### 2. Publication Status

```python
published = client.lakeview.get_published(dashboard_id)

# Captured fields:
- published (True/False → Yes/No)
- published_version (from published.version)
```

### 3. Last Accessed Date (Audit Logs)

```sql
SELECT 
    request_params.dashboard_id as dashboard_id,
    MAX(event_time) as last_accessed
FROM system.access.audit
WHERE action_name IN ('getDashboard', 'getPublishedDashboard', 'getDashboardSubscription')
  AND event_date >= CURRENT_DATE() - INTERVAL 90 DAYS
GROUP BY request_params.dashboard_id
```

**Note:** Last accessed date is queried for the last 90 days for performance. If a dashboard hasn't been accessed in 90 days, it will show as "Never".

### 4. Lineage Statistics (Per-Dashboard) - NEW

```sql
SELECT 
    COUNT(DISTINCT source_table_catalog) as catalog_count,
    COUNT(DISTINCT source_table_name) as table_count
FROM system.access.table_lineage
WHERE workspace_id = {workspace_id}
    AND entity_id = '{dashboard_id}'
    AND entity_type = 'DASHBOARD_V3'
```

**How it works:**
- Queries table lineage for each dashboard individually
- Counts unique catalogs and tables referenced
- Filtered by workspace_id to prevent cross-workspace pollution
- Uses `DASHBOARD_V3` entity type for AI/BI dashboards

**Use cases:**
- Identify dashboards with complex cross-catalog queries
- Find single-catalog dashboards (simpler to migrate)
- Measure dashboard data footprint

---

## Usage in Inventory Review

### Key Columns Displayed in Notebook

When you run `Bundle_01_Export_and_Transform.ipynb`, the inventory display shows:

1. **dashboard_name** - Easy identification
2. **published** - Migration priority (published = production)
3. **last_accessed** - Usage indicator
4. **lifecycle_state** - Active vs archived dashboards
5. **parent_folder** - Organizational context

### Full Inventory in CSV

The complete inventory with ALL fields is saved to:
```
/Volumes/{catalog}/{schema}/{volume_base}/dashboard_inventory/dashboard_inventory.csv
```

You can open this CSV to see all fields and use it for:
- Filtering dashboards by last access date
- Excluding archived/trashed dashboards
- Grouping by parent folder
- Tracking published versions

---

## Best Practices

### 1. Filter by Last Accessed
Exclude dashboards not accessed in 90 days:
```python
df = pd.read_csv(inventory_csv_path)
df_active = df[df['last_accessed'] != 'Never']
```

### 2. Prioritize Published Dashboards
Focus migration on published dashboards first:
```python
df_published = df[df['published'] == 'Yes']
```

### 3. Exclude Archived Dashboards
Filter out trashed dashboards:
```python
df_active = df[df['lifecycle_state'] == 'ACTIVE']
```

### 4. Group by Folder
Organize migration by workspace folders:
```python
df.groupby('parent_folder').size()
```

### 5. Filter by Data Complexity (NEW)
Prioritize simple single-catalog dashboards:
```python
# Simple dashboards (single catalog)
df_simple = df[df['catalog_count'] == 1]

# Complex dashboards (multiple catalogs)
df_complex = df[df['catalog_count'] > 1]

# Sort by table count to see data footprint
df.sort_values('table_count', ascending=False)
```

### 6. Identify Unused Dashboards (NEW)
Combine multiple signals to find candidates for exclusion:
```python
# Dashboards that are: not published, not accessed, and reference few tables
df_candidates = df[
    (df['published'] == 'No') &
    (df['last_accessed'] == 'Never') &
    (df['table_count'] <= 3)
]
```

---

## Performance Notes

### Query Optimization (NEW)

- **Spark SQL Auto-Detection**: Uses `spark.sql()` when available in notebooks (2-5x faster than SDK)
- **Workspace Filtering**: All queries now filter by `workspace_id` for accuracy
- **Entity Type Specificity**: Uses `DASHBOARD_V3` instead of generic `DASHBOARD` (faster indexing)

### Timing Expectations

- **Discovery Query**: 100-500ms (depends on catalog size and query method)
- **Last Accessed Query**: Limited to 90 days and first 100 dashboards for performance
- **Lineage Per Dashboard**: ~100-200ms per dashboard (parallelizable)
- **Audit Logs**: May take 5-10 seconds for large workspaces
- **Published Status**: Requires individual API call per dashboard
- **Total Time**: Expect ~1-2 seconds per dashboard for full metadata

### Performance Improvements

**Before Optimization:**
- SDK statement execution: ~500ms per query
- No workspace filtering
- Generic entity type matching

**After Optimization:**
- Spark SQL (when available): ~100-200ms per query (2-5x faster)
- Workspace-scoped queries (more accurate, potentially faster)
- Specific `DASHBOARD_V3` matching (better index usage)

---

## Troubleshooting

### "last_accessed" shows "Never" for all dashboards

**Cause**: Audit logs may not be available or dashboard IDs don't match audit format

**Solution**: This is non-critical; proceed with migration. Last accessed is informational only.

### "lifecycle_state" missing

**Cause**: Older Databricks SDK version

**Solution**: Update SDK: `%pip install -U databricks-sdk`

### "published_version" missing even for published dashboards

**Cause**: Some dashboards don't expose version info

**Solution**: This is normal; proceed with "published: Yes" status

---

## Future Enhancements

Potential additional fields for future versions:
- **owner** - Dashboard creator/owner (requires workspace API)
- **tags** - Custom tags if configured
- **schedules** - Subscription schedules (requires additional API calls)
- **query_count** - Number of queries in dashboard
- **table_count** - Number of source tables referenced

---

## Related Documentation

- **Main Testing Guide**: `TESTING_GUIDE.md`
- **Quick Start**: `QUICKSTART_MODULAR.md`
- **Bundle Workflow**: `Bundle/README.md`
