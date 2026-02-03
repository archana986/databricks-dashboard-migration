"""
Databricks Asset Bundle generation helpers.
"""

from .dbutils_helper import get_dbutils as _get_dbutils
import json
import yaml
from typing import Dict, List, Any
from pathlib import Path

def create_databricks_yml(
    bundle_name: str,
    target_workspace_url: str,
    warehouse_id: str = None,
    warehouse_name: str = None
) -> str:
    """
    Generate databricks.yml content.
    
    Args:
        bundle_name: Name of the bundle
        target_workspace_url: Target workspace URL
        warehouse_id: Direct warehouse ID (optional)
        warehouse_name: Warehouse name for lookup (optional)
    
    Returns:
        YAML content as string
    """
    config = {
        'bundle': {
            'name': bundle_name
        },
        'workspace': {
            'host': target_workspace_url
        },
        'include': [
            'resources/*.yml'
        ]
    }
    
    # Add warehouse variable
    if warehouse_name:
        config['variables'] = {
            'warehouse_id': {
                'description': 'SQL Warehouse for dashboards',
                'lookup': {
                    'warehouse': warehouse_name
                }
            }
        }
    elif warehouse_id:
        config['variables'] = {
            'warehouse_id': {
                'description': 'SQL Warehouse for dashboards',
                'default': warehouse_id
            }
        }
    
    return yaml.dump(config, default_flow_style=False, sort_keys=False)

def create_dashboard_resource(
    dashboard_id: str,
    display_name: str,
    file_path: str,
    permissions: List[Dict],
    parent_path: str = None,
    embed_credentials: bool = True
) -> Dict:
    """
    Create a single dashboard resource definition.
    
    Args:
        dashboard_id: Dashboard ID (used as resource key)
        display_name: Dashboard display name
        file_path: Path to .lvdash.json file (relative to bundle root)
        permissions: List of permission dictionaries
        parent_path: Parent folder path
        embed_credentials: Whether to embed credentials
    
    Returns:
        Dashboard resource dictionary
    """
    resource = {
        'display_name': display_name,
        'warehouse_id': '${var.warehouse_id}',
        'file_path': file_path,
        'embed_credentials': embed_credentials
    }
    
    if parent_path:
        resource['parent_path'] = parent_path
    
    # Add permissions if provided
    if permissions:
        resource['permissions'] = []
        for perm in permissions:
            perm_entry = {
                'level': perm.get('level', 'CAN_VIEW')
            }
            
            if perm.get('user_name'):
                perm_entry['user_name'] = perm['user_name']
            elif perm.get('group_name'):
                perm_entry['group_name'] = perm['group_name']
            elif perm.get('service_principal_name'):
                perm_entry['service_principal_name'] = perm['service_principal_name']
            
            resource['permissions'].append(perm_entry)
    
    return resource

def create_dashboards_yml(dashboard_resources: Dict[str, Dict]) -> str:
    """
    Generate resources/dashboards.yml content.
    
    Args:
        dashboard_resources: Dictionary of dashboard resources
                           {resource_key: resource_definition}
    
    Returns:
        YAML content as string
    """
    config = {
        'resources': {
            'dashboards': dashboard_resources
        }
    }
    
    return yaml.dump(config, default_flow_style=False, sort_keys=False, width=1000)

def convert_permissions_for_bundle(permissions_data: Dict) -> List[Dict]:
    """
    Convert exported permissions JSON to bundle format.
    
    Args:
        permissions_data: Permissions from get_dashboard_permissions
    
    Returns:
        List of permission dictionaries in bundle format
    """
    bundle_permissions = []
    
    acl_list = permissions_data.get('access_control_list', [])
    
    for acl in acl_list:
        # Get permission level (use first/highest)
        level = 'CAN_VIEW'  # Default
        if acl.get('all_permissions') and len(acl['all_permissions']) > 0:
            perm_str = acl['all_permissions'][0]
            # Map to bundle permission levels
            if 'MANAGE' in perm_str.upper():
                level = 'CAN_MANAGE'
            elif 'EDIT' in perm_str.upper():
                level = 'CAN_EDIT'
            elif 'RUN' in perm_str.upper():
                level = 'CAN_RUN'
            else:
                level = 'CAN_VIEW'
        
        perm = {'level': level}
        
        if acl.get('user_name'):
            perm['user_name'] = acl['user_name']
        elif acl.get('group_name'):
            perm['group_name'] = acl['group_name']
        elif acl.get('service_principal_name'):
            perm['service_principal_name'] = acl['service_principal_name']
        else:
            continue
        
        bundle_permissions.append(perm)
    
    return bundle_permissions

def generate_bundle_structure(
    bundle_name: str,
    target_workspace_url: str,
    transformed_dashboards: Dict[str, Dict],  # Dict with dashboard_id as key
    permissions_map: Dict[str, Dict],
    bundle_output_path: str,
    warehouse_id: str = None,
    warehouse_name: str = None,
    parent_path: str = "/Shared/Migrated_Dashboards",
    embed_credentials: bool = True
) -> str:
    """
    Generate complete bundle structure.
    
    Args:
        bundle_name: Name of the bundle
        target_workspace_url: Target workspace URL
        transformed_dashboards: Dict mapping dashboard_id -> {'display_name', 'json', 'source_path'}
        permissions_map: Map of dashboard_id/name to permissions
        bundle_output_path: Where to create bundle
        warehouse_id: Direct warehouse ID
        warehouse_name: Warehouse name for lookup
        parent_path: Parent folder path
        embed_credentials: Whether to embed credentials
    
    Returns:
        Path to generated bundle
    """
    import os
    
    # Create bundle directory structure
    bundle_path = f"{bundle_output_path}/{bundle_name}"
    
    # Use dbutils if available
    try:
        _get_dbutils().fs.mkdirs(bundle_path)
        _get_dbutils().fs.mkdirs(f"{bundle_path}/resources")
        _get_dbutils().fs.mkdirs(f"{bundle_path}/src/dashboards")
    except:
        os.makedirs(f"{bundle_path}/resources", exist_ok=True)
        os.makedirs(f"{bundle_path}/src/dashboards", exist_ok=True)
    
    # Generate databricks.yml
    databricks_yml = create_databricks_yml(
        bundle_name,
        target_workspace_url,
        warehouse_id,
        warehouse_name
    )
    
    # Write databricks.yml
    try:
        _get_dbutils().fs.put(f"{bundle_path}/databricks.yml", databricks_yml, overwrite=True)
    except:
        with open(f"{bundle_path}/databricks.yml", 'w') as f:
            f.write(databricks_yml)
    
    # Generate dashboard resources
    dashboard_resources = {}
    
    dashboard_items = list(transformed_dashboards.items())
    
    for dashboard_id, dash_data in dashboard_items:
        display_name = dash_data['display_name']
        
        # Copy transformed JSON to bundle
        src_json_path = dash_data['source_path']
        dest_json_path = f"{bundle_path}/src/dashboards/{Path(src_json_path).name}"
        
        try:
            # Copy using dbutils
            content = _get_dbutils().fs.head(src_json_path, 10485760)
            _get_dbutils().fs.put(dest_json_path, content, overwrite=True)
        except:
            # Copy using standard file ops
            with open(src_json_path, 'r') as f:
                content = f.read()
            with open(dest_json_path, 'w') as f:
                f.write(content)
        
        # Get permissions
        permissions_data = permissions_map.get(dashboard_id) or permissions_map.get(display_name)
        bundle_permissions = []
        if permissions_data:
            bundle_permissions = convert_permissions_for_bundle(permissions_data)
        
        # Create resource
        resource_key = f"dashboard_{dashboard_id}"
        file_path_relative = f"src/dashboards/{Path(src_json_path).name}"
        
        dashboard_resources[resource_key] = create_dashboard_resource(
            dashboard_id,
            display_name,
            file_path_relative,
            bundle_permissions,
            parent_path,
            embed_credentials
        )
    
    # Generate resources/dashboards.yml
    dashboards_yml = create_dashboards_yml(dashboard_resources)
    
    try:
        _get_dbutils().fs.put(f"{bundle_path}/resources/dashboards.yml", dashboards_yml, overwrite=True)
    except:
        with open(f"{bundle_path}/resources/dashboards.yml", 'w') as f:
            f.write(dashboards_yml)
    
    return bundle_path

def validate_bundle(bundle_path: str) -> Dict[str, Any]:
    """
    Validate bundle using Databricks CLI.
    
    NOTE: This function is designed to be run from local CLI, not within Databricks notebooks.
    When run from a notebook, it will skip validation gracefully.
    
    Args:
        bundle_path: Path to bundle directory
    
    Returns:
        Validation result dictionary
    """
    import subprocess
    
    try:
        # Check if 'databricks bundle' command is available
        check_result = subprocess.run(
            ['databricks', 'bundle', '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if check_result.returncode != 0 or 'No such command' in check_result.stderr:
            # CLI doesn't support bundle command - skip validation
            return {
                'success': True,
                'skipped': True,
                'stdout': 'Bundle validation skipped - CLI version does not support bundle command.\n'
                         'Validation should be done from local machine using: databricks bundle validate'
            }
        
        # Run validation
        result = subprocess.run(
            ['databricks', 'bundle', 'validate'],
            cwd=bundle_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except FileNotFoundError:
        # databricks CLI not found
        return {
            'success': True,
            'skipped': True,
            'stdout': 'Bundle validation skipped - Databricks CLI not available in this environment.\n'
                     'Validation should be done from local machine using: databricks bundle validate'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def deploy_bundle(bundle_path: str, target: str = None) -> Dict[str, Any]:
    """
    Deploy bundle using Databricks CLI.
    
    NOTE: This function is designed to be run from local CLI, not within Databricks notebooks.
    When run from a notebook, it will skip deployment gracefully.
    
    Args:
        bundle_path: Path to bundle directory
        target: Optional target name
    
    Returns:
        Deployment result dictionary
    """
    import subprocess
    
    cmd = ['databricks', 'bundle', 'deploy']
    if target:
        cmd.extend(['--target', target])
    
    try:
        # Check if 'databricks bundle' command is available
        check_result = subprocess.run(
            ['databricks', 'bundle', '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if check_result.returncode != 0 or 'No such command' in check_result.stderr:
            # CLI doesn't support bundle command - skip deployment
            return {
                'success': True,
                'skipped': True,
                'stdout': f'Bundle deployment skipped - CLI version does not support bundle command.\n'
                         f'Deploy from local machine using: databricks bundle deploy -t {target or "dev"}\n'
                         f'Bundle location: {bundle_path}'
            }
        
        # Run deployment
        result = subprocess.run(
            cmd,
            cwd=bundle_path,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes
        )
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except FileNotFoundError:
        # databricks CLI not found
        return {
            'success': True,
            'skipped': True,
            'stdout': f'Bundle deployment skipped - Databricks CLI not available in this environment.\n'
                     f'Deploy from local machine using: databricks bundle deploy -t {target or "dev"}\n'
                     f'Bundle location: {bundle_path}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
