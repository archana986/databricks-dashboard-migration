"""
Dashboard discovery functions.
"""

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dashboards import DashboardView
from typing import List, Dict, Optional
from .config_loader import get_dashboard_selection

# Initialize dbutils for module scope (Databricks-specific)
try:
    dbutils
except NameError:
    import IPython
    dbutils = IPython.get_ipython().user_ns.get("dbutils")

def _get_workspace_id(client: WorkspaceClient) -> int:
    """
    Extract workspace ID from client host URL or notebook context.
    
    Args:
        client: Workspace client
    
    Returns:
        Workspace ID as integer
    """
    import re
    
    # Method 1: Extract from host URL (e.g., https://xxx-12345678-abc.cloud.databricks.com)
    host = client.config.host
    match = re.search(r'-(\d+)-', host)
    if match:
        return int(match.group(1))
    
    # Method 2: Try to get from notebook context
    try:
        workspace_id = dbutils.notebook.entry_point.getDbutils().notebook().getContext().tags().get("orgId").get()
        return int(workspace_id)
    except:
        pass
    
    # Method 3: Last resort - parse from different URL format
    match = re.search(r'//([a-z0-9-]+)\.cloud\.databricks\.com', host)
    if match:
        # Some workspaces have ID embedded differently
        parts = match.group(1).split('-')
        for part in parts:
            if part.isdigit() and len(part) >= 8:
                return int(part)
    
    raise ValueError(f"Could not determine workspace_id from host: {host}")

def _execute_query(client: WorkspaceClient, query: str) -> List[List]:
    """
    Execute SQL query using spark.sql if available (faster), otherwise SDK.
    
    Args:
        client: Workspace client
        query: SQL query string
    
    Returns:
        List of rows (each row is a list of values)
    """
    # Try spark first (faster in Databricks notebooks)
    try:
        from pyspark.sql import SparkSession
        spark = SparkSession.getActiveSession()
        if spark:
            result = spark.sql(query).collect()
            # Convert rows to list of lists
            return [[getattr(row, field) for field in row.__fields__] for row in result]
    except Exception:
        pass
    
    # Fall back to SDK statement execution
    warehouses = list(client.warehouses.list())
    if not warehouses:
        raise Exception("No warehouses available")
    
    statement = client.statement_execution.execute_statement(
        warehouse_id=warehouses[0].id,
        statement=query,
        wait_timeout="30s"
    )
    
    if statement.result and statement.result.data_array:
        return statement.result.data_array
    return []

def discover_dashboards(
    client: WorkspaceClient,
    method: Optional[str] = None,
    **kwargs
) -> List[Dict]:
    """
    Discover dashboards using configured method.
    
    Args:
        client: Workspace client
        method: Discovery method override
        **kwargs: Additional method-specific parameters
    
    Returns:
        List of dashboard dictionaries with id, name, path
    """
    if method is None:
        selection_config = get_dashboard_selection()
        method = selection_config.get('method', 'catalog_filter')
    
    if method == 'catalog_filter':
        return _discover_by_catalog(client, **kwargs)
    elif method == 'folder_path':
        return _discover_by_folder(client, **kwargs)
    elif method == 'explicit_ids':
        return _discover_by_ids(client, **kwargs)
    elif method == 'inventory_csv':
        return _discover_from_inventory(**kwargs)
    else:
        raise ValueError(f"Unknown discovery method: {method}")

def _discover_by_catalog(
    client: WorkspaceClient,
    catalog: Optional[str] = None,
    use_system_tables: bool = True
) -> List[Dict]:
    """Discover dashboards using a specific catalog."""
    from .config_loader import get_dashboard_selection
    
    if catalog is None:
        config = get_dashboard_selection()
        catalog = config['catalog_filter']['catalog']
        use_system_tables = config['catalog_filter'].get('use_system_tables', True)
    
    if use_system_tables:
        return _discover_via_system_tables(client, catalog)
    else:
        return _discover_via_sdk_list(client, catalog)

def _discover_via_system_tables(client: WorkspaceClient, catalog: str) -> List[Dict]:
    """Fast discovery using system.access.table_lineage with workspace filtering."""
    try:
        # Get workspace ID for accurate filtering
        workspace_id = _get_workspace_id(client)
        
        query = f"""
        SELECT DISTINCT entity_id
        FROM system.access.table_lineage
        WHERE workspace_id = {workspace_id}
          AND source_table_catalog = '{catalog}'
          AND entity_type = 'DASHBOARD_V3'
          AND entity_id IS NOT NULL
        """
        
        # Execute query using optimized method (spark.sql if available)
        result_rows = _execute_query(client, query)
        
        dashboard_ids = set()
        for row in result_rows:
            dashboard_ids.add(row[0])
        
        # Get full dashboard objects
        dashboards = []
        for dash_id in dashboard_ids:
            try:
                dash = client.lakeview.get(dash_id)
                dashboards.append({
                    'id': dash.dashboard_id,
                    'name': dash.display_name,
                    'path': dash.path
                })
            except:
                pass
        
        return dashboards
        
    except Exception as e:
        print(f"System tables query failed: {e}. Falling back to SDK list.")
        return _discover_via_sdk_list(client, catalog)

def _discover_via_sdk_list(client: WorkspaceClient, catalog: Optional[str] = None) -> List[Dict]:
    """Slower but more reliable SDK list method."""
    dashboards = []
    
    for dash in client.lakeview.list(
        page_size=100,
        view=DashboardView.DASHBOARD_VIEW_BASIC,
        show_trashed=False
    ):
        try:
            full = client.lakeview.get(dash.dashboard_id)
            
            if catalog:
                # Filter by catalog
                try:
                    published = client.lakeview.get_published(dash.dashboard_id)
                    if catalog in (published.serialized_dashboard or ""):
                        dashboards.append({
                            'id': full.dashboard_id,
                            'name': full.display_name,
                            'path': full.path
                        })
                except:
                    pass
            else:
                dashboards.append({
                    'id': full.dashboard_id,
                    'name': full.display_name,
                    'path': full.path
                })
        except:
            pass
    
    return dashboards

def _discover_by_folder(client: WorkspaceClient, folder_path: Optional[str] = None) -> List[Dict]:
    """Discover dashboards in a folder."""
    from .config_loader import get_dashboard_selection
    
    if folder_path is None:
        config = get_dashboard_selection()
        folder_path = config['folder_path']['path']
    
    dashboards = []
    
    for dash in client.lakeview.list(
        page_size=100,
        view=DashboardView.DASHBOARD_VIEW_BASIC,
        show_trashed=False
    ):
        full = client.lakeview.get(dash.dashboard_id)
        if full.path and full.path.startswith(folder_path):
            dashboards.append({
                'id': full.dashboard_id,
                'name': full.display_name,
                'path': full.path
            })
    
    return dashboards

def _discover_by_ids(client: WorkspaceClient, dashboard_ids: Optional[List[str]] = None) -> List[Dict]:
    """Discover dashboards by explicit IDs."""
    from .config_loader import get_dashboard_selection
    
    if dashboard_ids is None:
        config = get_dashboard_selection()
        dashboard_ids = config['explicit_ids']['dashboard_ids']
    
    dashboards = []
    
    for dash_id in dashboard_ids:
        try:
            dash = client.lakeview.get(dash_id)
            dashboards.append({
                'id': dash.dashboard_id,
                'name': dash.display_name,
                'path': dash.path
            })
        except Exception as e:
            print(f"Failed to get dashboard {dash_id}: {e}")
    
    return dashboards

def _get_last_accessed_dates(client: WorkspaceClient, dashboard_ids: List[str]) -> Dict[str, str]:
    """
    Get last accessed dates for dashboards from audit logs.
    
    Args:
        client: Workspace client
        dashboard_ids: List of dashboard IDs to query
    
    Returns:
        Map of dashboard_id -> last_accessed_date string
    """
    if not dashboard_ids:
        return {}
    
    # Build query for audit logs (last 90 days for performance)
    ids_list = "', '".join(dashboard_ids[:100])  # Limit to first 100 for performance
    query = f"""
    SELECT 
        request_params.dashboard_id as dashboard_id,
        MAX(event_time) as last_accessed
    FROM system.access.audit
    WHERE action_name IN ('getDashboard', 'getPublishedDashboard', 'getDashboardSubscription')
      AND request_params.dashboard_id IN ('{ids_list}')
      AND event_date >= CURRENT_DATE() - INTERVAL 90 DAYS
    GROUP BY request_params.dashboard_id
    """
    
    try:
        # Use optimized query execution (spark.sql if available)
        result_rows = _execute_query(client, query)
        
        last_accessed_map = {}
        for row in result_rows:
            dash_id = row[0]
            last_accessed = row[1]
            if dash_id and last_accessed:
                # Convert timestamp to readable date
                last_accessed_map[dash_id] = str(last_accessed).split('T')[0]  # Just date part
        
        return last_accessed_map
        
    except Exception as e:
        print(f"Could not fetch last accessed dates: {e}")
        return {}

def _discover_from_inventory(csv_path: Optional[str] = None) -> List[Dict]:
    """Load dashboards from inventory CSV."""
    import pandas as pd
    import io
    from .config_loader import get_path
    
    if csv_path is None:
        csv_path = get_path('inventory')
        csv_path = f"{csv_path}/dashboard_inventory.csv"
    
    content = dbutils.fs.head(csv_path, 10485760)
    df = pd.read_csv(io.StringIO(content))
    
    return df.to_dict('records')

def generate_inventory(
    client: WorkspaceClient,
    include_published_status: bool = True,
    include_metadata: bool = True
) -> List[Dict]:
    """
    Generate comprehensive inventory with metadata.
    
    Args:
        client: Workspace client
        include_published_status: Include whether dashboard is published
        include_metadata: Include additional metadata (owner, tables, last accessed, etc.)
    
    Returns:
        List of dashboard dictionaries with comprehensive metadata
    """
    from .config_loader import get_dashboard_selection
    
    config = get_dashboard_selection()
    method = config.get('method', 'catalog_filter')
    
    # Discover dashboards using configured method
    dashboards = discover_dashboards(client, method=method)
    
    # Get last accessed dates from audit logs if metadata requested
    last_accessed_map = {}
    if include_metadata:
        try:
            last_accessed_map = _get_last_accessed_dates(client, [d['id'] for d in dashboards])
        except Exception as e:
            print(f"Warning: Could not fetch last accessed dates: {e}")
    
    # Enrich with additional metadata
    enriched = []
    
    for dash in dashboards:
        dashboard_id = dash['id']
        
        try:
            # Get full details
            full = client.lakeview.get(dashboard_id)
            
            enriched_dash = {
                'dashboard_id': dashboard_id,
                'dashboard_name': full.display_name,
                'path': full.path,
            }
            
            # Add published status if requested
            if include_published_status:
                published = False
                published_version = None
                try:
                    pub = client.lakeview.get_published(dashboard_id)
                    published = True
                    published_version = pub.version if hasattr(pub, 'version') else None
                except:
                    pass
                enriched_dash['published'] = 'Yes' if published else 'No'
                if published_version:
                    enriched_dash['published_version'] = published_version
            
            # Add comprehensive metadata if requested
            if include_metadata:
                enriched_dash['warehouse_id'] = full.warehouse_id or 'None'
                enriched_dash['created_time'] = str(full.create_time) if full.create_time else 'Unknown'
                enriched_dash['updated_time'] = str(full.update_time) if full.update_time else 'Unknown'
                enriched_dash['lifecycle_state'] = full.lifecycle_state.value if hasattr(full, 'lifecycle_state') and full.lifecycle_state else 'ACTIVE'
                enriched_dash['etag'] = full.etag if hasattr(full, 'etag') and full.etag else 'None'
                
                # Extract parent folder from path
                if full.path:
                    parent_path = '/'.join(full.path.rsplit('/', 1)[:-1]) if '/' in full.path else '/'
                    enriched_dash['parent_folder'] = parent_path
                else:
                    enriched_dash['parent_folder'] = 'Unknown'
                
                # Add last accessed date if available
                enriched_dash['last_accessed'] = last_accessed_map.get(dashboard_id, 'Never')
                
                # Add lineage statistics (catalog and table counts)
                try:
                    workspace_id = _get_workspace_id(client)
                    lineage_query = f"""
                        SELECT 
                            COUNT(DISTINCT source_table_catalog) as catalog_count,
                            COUNT(DISTINCT source_table_name) as table_count
                        FROM system.access.table_lineage
                        WHERE workspace_id = {workspace_id}
                            AND entity_id = '{dashboard_id}'
                            AND entity_type = 'DASHBOARD_V3'
                    """
                    lineage_result = _execute_query(client, lineage_query)
                    if lineage_result and len(lineage_result) > 0:
                        enriched_dash['catalog_count'] = lineage_result[0][0] if lineage_result[0][0] is not None else 0
                        enriched_dash['table_count'] = lineage_result[0][1] if lineage_result[0][1] is not None else 0
                    else:
                        enriched_dash['catalog_count'] = 0
                        enriched_dash['table_count'] = 0
                except Exception:
                    enriched_dash['catalog_count'] = 0
                    enriched_dash['table_count'] = 0
                
                # Add workspace link
                enriched_dash['link'] = f"/sql/dashboards/{dashboard_id}"
            
            enriched.append(enriched_dash)
            
        except Exception as e:
            print(f"Warning: Could not enrich {dashboard_id}: {e}")
            enriched.append(dash)
    
    return enriched

def save_inventory_to_csv(dashboards: List[Dict], csv_path: str) -> None:
    """
    Save dashboard inventory to CSV in volume.
    
    Args:
        dashboards: List of dashboard dictionaries
        csv_path: Full volume path to save CSV (e.g., /Volumes/.../inventory.csv)
    """
    import pandas as pd
    from .volume_utils import write_volume_file, ensure_directory_exists
    
    # Ensure parent directory exists
    parent_dir = "/".join(csv_path.rsplit("/", 1)[:-1])
    ensure_directory_exists(parent_dir)
    
    # Convert to DataFrame and CSV
    df = pd.DataFrame(dashboards)
    csv_content = df.to_csv(index=False)
    
    # Save to volume
    write_volume_file(csv_path, csv_content)
    
    print(f"✅ Saved inventory to: {csv_path}")
    print(f"   Total dashboards: {len(dashboards)}")

def load_inventory_from_csv(csv_path: str) -> List[Dict]:
    """
    Load validated inventory from CSV in volume.
    
    Args:
        csv_path: Full volume path to CSV
    
    Returns:
        List of dashboard dictionaries from CSV
    """
    import pandas as pd
    import io
    from .volume_utils import read_volume_file
    
    content = read_volume_file(csv_path)
    df = pd.read_csv(io.StringIO(content))
    
    print(f"✅ Loaded inventory from: {csv_path}")
    print(f"   Total dashboards: {len(df)}")
    
    return df.to_dict('records')
