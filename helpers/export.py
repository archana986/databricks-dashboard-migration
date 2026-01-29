"""
Dashboard export functions.
"""

from databricks.sdk import WorkspaceClient
from typing import Tuple
import re

def export_dashboard(
    client: WorkspaceClient,
    dashboard_id: str
) -> Tuple[str, str, str]:
    """
    Export dashboard JSON and metadata.
    
    Args:
        client: Workspace client
        dashboard_id: Dashboard ID
    
    Returns:
        Tuple of (dashboard_json, display_name, clean_name)
    """
    # Get dashboard
    dash = client.lakeview.get(dashboard_id)
    published = client.lakeview.get_published(dashboard_id)
    
    # Get JSON content
    json_content = published.serialized_dashboard
    display_name = dash.display_name or "unnamed"
    
    # Clean name for file naming
    clean_name = display_name.replace(" ", "_").replace("/", "_")
    clean_name = re.sub(r'[^a-zA-Z0-9_-]', '', clean_name)
    
    return json_content, display_name, clean_name
