"""
ACL and permissions management.
"""

from .dbutils_helper import get_dbutils as _get_dbutils
from databricks.sdk import WorkspaceClient
from typing import Dict, List
import json

def get_dashboard_permissions(client: WorkspaceClient, dashboard_id: str) -> Dict:
    """
    Get dashboard permissions from source workspace.
    
    Args:
        client: Workspace client
        dashboard_id: Dashboard ID
    
    Returns:
        Dictionary with access_control_list
    """
    try:
        perms = client.permissions.get("dashboards", dashboard_id)
        
        return {
            "dashboard_id": dashboard_id,
            "access_control_list": [
                {
                    "user_name": acl.user_name,
                    "group_name": acl.group_name,
                    "service_principal_name": acl.service_principal_name,
                    "all_permissions": [
                        str(p.permission_level.value) if hasattr(p.permission_level, 'value')
                        else str(p.permission_level)
                        for p in (acl.all_permissions or [])
                    ]
                }
                for acl in (perms.access_control_list or [])
            ]
        }
    except Exception as e:
        print(f"Could not retrieve permissions: {e}")
        return {"dashboard_id": dashboard_id, "access_control_list": []}

def apply_dashboard_permissions(
    client: WorkspaceClient,
    dashboard_id: str,
    permissions_data: Dict,
    dry_run: bool = True
) -> Dict:
    """
    Apply permissions to a dashboard in target workspace.
    
    Args:
        client: Workspace client
        dashboard_id: Dashboard ID
        permissions_data: Permissions dictionary from get_dashboard_permissions
        dry_run: If True, only preview without applying
    
    Returns:
        Dictionary with status and details
    """
    acl_list = permissions_data.get('access_control_list', [])
    
    if not acl_list:
        return {'status': 'skipped', 'reason': 'No permissions to apply'}
    
    if dry_run:
        return {
            'status': 'dry_run',
            'would_apply': len(acl_list),
            'permissions': acl_list
        }
    
    try:
        from databricks.sdk.service.iam import AccessControlRequest, PermissionLevel
        
        access_control_list = []
        for acl in acl_list:
            acr = AccessControlRequest()
            
            # Set principal
            if acl.get('user_name'):
                acr.user_name = acl['user_name']
            elif acl.get('group_name'):
                acr.group_name = acl['group_name']
            elif acl.get('service_principal_name'):
                acr.service_principal_name = acl['service_principal_name']
            else:
                continue
            
            # Set permission level
            if acl.get('all_permissions') and len(acl['all_permissions']) > 0:
                perm_str = acl['all_permissions'][0]
                try:
                    acr.permission_level = PermissionLevel[perm_str] if hasattr(PermissionLevel, perm_str) else perm_str
                except:
                    acr.permission_level = perm_str
            else:
                continue
            
            access_control_list.append(acr)
        
        # Apply permissions
        client.permissions.update(
            request_object_type="dashboards",
            request_object_id=dashboard_id,
            access_control_list=access_control_list
        )
        
        return {
            'status': 'success',
            'applied': len(access_control_list)
        }
        
    except Exception as e:
        return {
            'status': 'failed',
            'error': str(e)
        }

def load_permissions_from_volume(export_path: str) -> Dict[str, Dict]:
    """Load all permissions JSON files from volume."""
    permissions_map = {}
    
    try:
        files = _get_dbutils().fs.ls(export_path)
        perm_files = [f for f in files if '_permissions.json' in f.path]
        
        for perm_file in perm_files:
            content = _get_dbutils().fs.head(perm_file.path, 10485760)
            perm_data = json.loads(content)
            
            dashboard_id = perm_data.get('dashboard_id')
            dashboard_name = perm_data.get('display_name')
            
            # Store by both ID and name for flexible matching
            if dashboard_id:
                permissions_map[dashboard_id] = perm_data
            if dashboard_name:
                permissions_map[dashboard_name] = perm_data
        
        return permissions_map
    except Exception as e:
        print(f"Error loading permissions: {e}")
        return {}

def list_target_dashboards(client: WorkspaceClient, parent_path: str) -> List[Dict]:
    """List dashboards in target workspace location."""
    dashboards = []
    
    for dash in client.lakeview.list():
        if dash.parent_path and dash.parent_path.startswith(parent_path):
            dashboards.append({
                'id': dash.dashboard_id,
                'name': dash.display_name,
                'path': dash.parent_path
            })
    
    return dashboards
