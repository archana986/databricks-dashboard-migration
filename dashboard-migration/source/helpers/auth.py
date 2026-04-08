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
    
    if auth_method == 'service_principal':
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
        if auth_method == 'pat':
            raise ValueError("PAT is not supported; use service_principal or oauth in config.")
        raise ValueError(f"Unsupported auth method: {auth_method}")


def create_target_workspace_client(
    target_url: str,
    secret_scope: str = "migration_secrets"
) -> WorkspaceClient:
    """
    Create client for target workspace using stored credentials.
    
    SIMPLIFIED: Single consistent auth method (no OAuth fallback complexity).
    
    Supported auth: Service Principal only (no PAT). Store sp_client_id and sp_secret in the secret scope.
    
    OAuth is NOT supported for cross-workspace (tokens are workspace-scoped).
    
    Args:
        target_url: Target workspace URL
        secret_scope: Databricks secret scope containing credentials
    
    Returns:
        Authenticated WorkspaceClient for target workspace
    
    Raises:
        RuntimeError: If authentication fails
    """
    dbutils = _get_dbutils()
    
    # Method 1: Try Service Principal (RECOMMENDED)
    try:
        client_id = dbutils.secrets.get(secret_scope, "sp_client_id")
        client_secret = dbutils.secrets.get(secret_scope, "sp_secret")
        
        client = WorkspaceClient(
            host=target_url,
            client_id=client_id,
            client_secret=client_secret
        )
        
        # Test connection and verify workspace
        user = client.current_user.me()
        client_host = client.config.host.rstrip('/')
        expected_host = target_url.rstrip('/')
        
        if expected_host in client_host or client_host == expected_host:
            print(f"🔐 AUTH: Service Principal")
            print(f"   Connected to: {client.config.host}")
            print(f"   Service Principal ID: {user.user_name}")
            return client
        else:
            raise RuntimeError(f"SP connected to wrong workspace: {client_host}")
            
    except Exception as e:
        raise RuntimeError(
            f"Failed to authenticate to target workspace: {target_url}\n\n"
            f"Error: {str(e)}\n\n"
            f"SETUP: Store Service Principal credentials in '{secret_scope}' secret scope (no PAT):\n"
            f"  1. Create SP in Account Console and assign to both source and target workspaces\n"
            f"  2. Store credentials:\n"
            f"     databricks secrets put-secret {secret_scope} sp_client_id --profile source-workspace\n"
            f"     databricks secrets put-secret {secret_scope} sp_secret --profile source-workspace\n\n"
            f"NOTE: OAuth is not supported for cross-workspace; use Service Principal only.\n"
        )
