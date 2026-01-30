"""
Authentication and workspace client creation.
"""

from .dbutils_helper import get_dbutils as _get_dbutils
from databricks.sdk import WorkspaceClient
from typing import Optional
from .config_loader import get_config

def create_workspace_client(
    workspace: str = 'source',
    custom_config: Optional[dict] = None
) -> WorkspaceClient:
    """
    Create authenticated Databricks workspace client.
    
    Args:
        workspace: 'source' or 'target'
        custom_config: Optional custom configuration override
    
    Returns:
        WorkspaceClient instance
    """
    if custom_config:
        config = custom_config
    else:
        full_config = get_config()
        config = full_config[workspace]
    
    workspace_url = config['workspace_url']
    auth_config = config['auth']
    auth_method = auth_config['method']
    
    if auth_method == 'pat':
        # PAT authentication
        scope = auth_config['pat']['secret_scope']
        key = auth_config['pat']['secret_key']
        token = _get_dbutils().secrets.get(scope=scope, key=key)
        
        return WorkspaceClient(host=workspace_url, token=token)
    
    elif auth_method == 'service_principal':
        # Service Principal authentication
        sp_config = auth_config['service_principal']
        
        client_id = _get_dbutils().secrets.get(
            scope=sp_config['client_id_scope'],
            key=sp_config['client_id_key']
        )
        client_secret = _get_dbutils().secrets.get(
            scope=sp_config['client_secret_scope'],
            key=sp_config['client_secret_key']
        )
        
        return WorkspaceClient(
            host=workspace_url,
            client_id=client_id,
            client_secret=client_secret
        )
    
    elif auth_method == 'oauth':
        # OAuth (notebook-native authentication)
        return WorkspaceClient(host=workspace_url)
    
    else:
        raise ValueError(f"Unsupported auth method: {auth_method}")
