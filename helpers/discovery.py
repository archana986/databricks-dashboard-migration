"""
Dashboard discovery functions.
"""

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dashboards import DashboardView
from typing import List, Dict, Optional
from .config_loader import get_dashboard_selection

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
    """Fast discovery using system.access.table_lineage."""
    query = f"""
    SELECT DISTINCT dashboard_id, dashboard_name
    FROM system.access.table_lineage
    WHERE source_table_catalog = '{catalog}'
      AND dashboard_id IS NOT NULL
    """
    
    try:
        warehouses = list(client.warehouses.list())
        if not warehouses:
            raise Exception("No warehouses available")
        
        warehouse_id = warehouses[0].id
        
        statement = client.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=query,
            wait_timeout="30s"
        )
        
        dashboard_ids = set()
        if statement.result and statement.result.data_array:
            for row in statement.result.data_array:
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
        include_metadata: Include additional metadata (owner, tables, etc.)
    
    Returns:
        List of dashboard dictionaries with comprehensive metadata
    """
    from .config_loader import get_dashboard_selection
    
    config = get_dashboard_selection()
    method = config.get('method', 'catalog_filter')
    
    # Discover dashboards using configured method
    dashboards = discover_dashboards(client, method=method)
    
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
                try:
                    client.lakeview.get_published(dashboard_id)
                    published = True
                except:
                    pass
                enriched_dash['published'] = 'Yes' if published else 'No'
            
            # Add metadata if requested
            if include_metadata:
                enriched_dash['warehouse_id'] = full.warehouse_id or 'None'
                enriched_dash['created_time'] = str(full.create_time) if full.create_time else 'Unknown'
                enriched_dash['updated_time'] = str(full.update_time) if full.update_time else 'Unknown'
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
