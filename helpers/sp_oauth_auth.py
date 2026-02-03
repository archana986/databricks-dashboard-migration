"""
Service Principal OAuth M2M Authentication Module.

Standalone module for cross-workspace authentication using Service Principal.
Can be attached/detached from bundle without affecting existing auth.py.

This module provides OAuth Machine-to-Machine (M2M) authentication for 
cross-workspace operations using a Service Principal. It reads credentials
from a Databricks Secret Scope.

Prerequisites:
    1. Service Principal created in Account Console
    2. SP added to both source and target workspaces
    3. OAuth secret created for SP
    4. Credentials stored in Databricks secret scope:
       - sp_client_id: Service Principal Application ID
       - sp_client_secret: OAuth Secret

Usage:
    from helpers.sp_oauth_auth import get_target_client_sp
    
    client = get_target_client_sp(
        target_url="https://target.cloud.databricks.com",
        secret_scope="migration_secrets"
    )
    
    # Use client for cross-workspace operations
    user = client.current_user.me()
    dashboards = client.lakeview.list()

Setup Commands:
    # Create secret scope (if not exists)
    databricks secrets create-scope migration_secrets --profile source-workspace
    
    # Store SP credentials
    databricks secrets put-secret migration_secrets sp_client_id --profile source-workspace
    databricks secrets put-secret migration_secrets sp_client_secret --profile source-workspace

See docs/SP_OAUTH_SETUP.md for complete setup instructions.
"""

from databricks.sdk import WorkspaceClient
from typing import Dict, Any, Optional

# Required secret keys
REQUIRED_SECRETS = {
    'client_id': 'sp_client_id',
    'client_secret': 'sp_client_secret'
}


def _get_dbutils():
    """Get dbutils instance (works in Databricks notebooks)."""
    try:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.getOrCreate()
        return spark._jvm.dbutils
    except:
        pass
    
    try:
        # Try IPython/Databricks notebook context
        from IPython import get_ipython
        ip = get_ipython()
        if ip and hasattr(ip, 'user_ns') and 'dbutils' in ip.user_ns:
            return ip.user_ns['dbutils']
    except:
        pass
    
    try:
        # Last resort: try importing directly
        import dbutils
        return dbutils
    except:
        pass
    
    raise RuntimeError(
        "dbutils not available. This module requires Databricks notebook context."
    )


def validate_sp_credentials(secret_scope: str) -> Dict[str, Any]:
    """
    Validate that SP credentials exist in the secret scope.
    
    Args:
        secret_scope: Name of the Databricks secret scope containing SP credentials
    
    Returns:
        Dict with validation status:
        {
            'valid': bool,
            'client_id_exists': bool,
            'client_secret_exists': bool,
            'errors': List[str],
            'secret_scope': str
        }
    
    Example:
        >>> result = validate_sp_credentials("migration_secrets")
        >>> if result['valid']:
        ...     print("Credentials are configured")
        >>> else:
        ...     for error in result['errors']:
        ...         print(f"Error: {error}")
    """
    result = {
        'valid': False,
        'client_id_exists': False,
        'client_secret_exists': False,
        'errors': [],
        'secret_scope': secret_scope
    }
    
    try:
        dbutils = _get_dbutils()
    except Exception as e:
        result['errors'].append(f"Cannot access dbutils: {str(e)}")
        return result
    
    # Check client_id
    try:
        client_id = dbutils.secrets.get(secret_scope, REQUIRED_SECRETS['client_id'])
        if client_id and len(client_id.strip()) > 0:
            result['client_id_exists'] = True
        else:
            result['errors'].append(
                f"Secret '{REQUIRED_SECRETS['client_id']}' exists but is empty"
            )
    except Exception as e:
        error_msg = str(e).lower()
        if 'does not exist' in error_msg or 'not found' in error_msg:
            result['errors'].append(
                f"Secret '{REQUIRED_SECRETS['client_id']}' not found in scope '{secret_scope}'. "
                f"Run: databricks secrets put-secret {secret_scope} {REQUIRED_SECRETS['client_id']}"
            )
        elif 'scope' in error_msg and 'not found' in error_msg:
            result['errors'].append(
                f"Secret scope '{secret_scope}' does not exist. "
                f"Run: databricks secrets create-scope {secret_scope}"
            )
        else:
            result['errors'].append(f"Error reading client_id: {str(e)}")
    
    # Check client_secret
    try:
        client_secret = dbutils.secrets.get(secret_scope, REQUIRED_SECRETS['client_secret'])
        if client_secret and len(client_secret.strip()) > 0:
            result['client_secret_exists'] = True
        else:
            result['errors'].append(
                f"Secret '{REQUIRED_SECRETS['client_secret']}' exists but is empty"
            )
    except Exception as e:
        error_msg = str(e).lower()
        if 'does not exist' in error_msg or 'not found' in error_msg:
            result['errors'].append(
                f"Secret '{REQUIRED_SECRETS['client_secret']}' not found in scope '{secret_scope}'. "
                f"Run: databricks secrets put-secret {secret_scope} {REQUIRED_SECRETS['client_secret']}"
            )
        else:
            result['errors'].append(f"Error reading client_secret: {str(e)}")
    
    # Set overall validity
    result['valid'] = result['client_id_exists'] and result['client_secret_exists']
    
    return result


def get_target_client_sp(
    target_url: str,
    secret_scope: str,
    validate_connection: bool = True
) -> WorkspaceClient:
    """
    Get target workspace client using SP OAuth M2M from secret scope.
    
    This is the main function for authenticating to a target workspace
    using Service Principal OAuth M2M credentials stored in a secret scope.
    
    Args:
        target_url: Target workspace URL (e.g., "https://target.cloud.databricks.com")
        secret_scope: Name of the Databricks secret scope containing SP credentials
        validate_connection: If True, test the connection before returning
    
    Returns:
        WorkspaceClient authenticated to the target workspace
    
    Raises:
        RuntimeError: If credentials are missing or connection fails
    
    Example:
        >>> client = get_target_client_sp(
        ...     target_url="https://target.cloud.databricks.com",
        ...     secret_scope="migration_secrets"
        ... )
        >>> user = client.current_user.me()
        >>> print(f"Connected as: {user.user_name}")
    """
    # Validate credentials first
    validation = validate_sp_credentials(secret_scope)
    
    if not validation['valid']:
        error_lines = [
            "SP OAuth credentials not properly configured.",
            "",
            "Missing credentials:",
        ]
        for error in validation['errors']:
            error_lines.append(f"  - {error}")
        
        error_lines.extend([
            "",
            "Setup Instructions:",
            f"  1. Create secret scope (if not exists):",
            f"     databricks secrets create-scope {secret_scope} --profile source-workspace",
            "",
            f"  2. Store SP client ID:",
            f"     databricks secrets put-secret {secret_scope} sp_client_id --profile source-workspace",
            "",
            f"  3. Store SP client secret:",
            f"     databricks secrets put-secret {secret_scope} sp_client_secret --profile source-workspace",
            "",
            "See docs/SP_OAUTH_SETUP.md for complete setup instructions."
        ])
        
        raise RuntimeError("\n".join(error_lines))
    
    # Get credentials from secret scope
    dbutils = _get_dbutils()
    client_id = dbutils.secrets.get(secret_scope, REQUIRED_SECRETS['client_id'])
    client_secret = dbutils.secrets.get(secret_scope, REQUIRED_SECRETS['client_secret'])
    
    # Normalize target URL
    target_url = target_url.rstrip('/')
    if not target_url.startswith('https://'):
        target_url = f"https://{target_url}"
    
    # Create workspace client with SP OAuth M2M
    try:
        client = WorkspaceClient(
            host=target_url,
            client_id=client_id,
            client_secret=client_secret
        )
    except Exception as e:
        raise RuntimeError(
            f"Failed to create WorkspaceClient for {target_url}: {str(e)}\n\n"
            "Possible causes:\n"
            "  - Invalid client_id or client_secret\n"
            "  - Service Principal not added to target workspace\n"
            "  - OAuth secret expired\n\n"
            "See docs/SP_OAUTH_SETUP.md for troubleshooting."
        )
    
    # Validate connection if requested
    if validate_connection:
        try:
            user = client.current_user.me()
            
            # Verify connected to correct workspace
            client_host = client.config.host.rstrip('/')
            expected_host = target_url.rstrip('/')
            
            # Check if hosts match (handle case where one has port, etc.)
            if expected_host not in client_host and client_host != expected_host:
                raise RuntimeError(
                    f"Connected to wrong workspace!\n"
                    f"  Expected: {expected_host}\n"
                    f"  Got: {client_host}"
                )
            
            print(f"🔐 SP OAuth M2M Authentication Successful")
            print(f"   Connected to: {client.config.host}")
            print(f"   Service Principal: {user.user_name}")
            
        except Exception as e:
            error_msg = str(e)
            
            # Check for common errors
            if "blocked by Databricks IP ACL" in error_msg:
                raise RuntimeError(
                    f"SP OAuth authentication failed - IP blocked.\n\n"
                    f"Your cluster IP is blocked by IP Access Lists on {target_url}.\n\n"
                    f"Solutions:\n"
                    f"  1. Whitelist your cluster IP on the target workspace\n"
                    f"  2. Run: ./scripts/auto_setup_ip_acl.sh\n\n"
                    f"See docs/SP_OAUTH_SETUP.md for details."
                )
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                raise RuntimeError(
                    f"SP OAuth authentication failed - Unauthorized.\n\n"
                    f"Possible causes:\n"
                    f"  - Invalid client_id or client_secret\n"
                    f"  - OAuth secret expired (recreate in Account Console)\n"
                    f"  - Service Principal not added to workspace {target_url}\n\n"
                    f"See docs/SP_OAUTH_SETUP.md for troubleshooting."
                )
            elif "403" in error_msg or "forbidden" in error_msg.lower():
                raise RuntimeError(
                    f"SP OAuth authentication failed - Forbidden.\n\n"
                    f"Service Principal authenticated but lacks permissions.\n\n"
                    f"Ensure SP has adequate permissions in target workspace:\n"
                    f"  - Account Console > Workspaces > {target_url} > Permissions\n"
                    f"  - Add Service Principal with 'User' or 'Admin' role\n\n"
                    f"See docs/SP_OAUTH_SETUP.md for details."
                )
            else:
                raise RuntimeError(
                    f"SP OAuth authentication failed: {error_msg}\n\n"
                    f"See docs/SP_OAUTH_SETUP.md for troubleshooting."
                )
    
    return client


def test_sp_connection(
    target_url: str,
    secret_scope: str
) -> Dict[str, Any]:
    """
    Test SP connection and return diagnostic info.
    
    Use this function to diagnose connection issues without raising exceptions.
    
    Args:
        target_url: Target workspace URL
        secret_scope: Name of the secret scope with SP credentials
    
    Returns:
        Dict with connection test results:
        {
            'success': bool,
            'target_url': str,
            'secret_scope': str,
            'credentials_valid': bool,
            'connection_successful': bool,
            'user_info': Optional[str],
            'workspace_host': Optional[str],
            'error': Optional[str],
            'error_type': Optional[str]  # 'credentials', 'ip_blocked', 'auth', 'connection'
        }
    
    Example:
        >>> result = test_sp_connection(
        ...     "https://target.cloud.databricks.com",
        ...     "migration_secrets"
        ... )
        >>> if result['success']:
        ...     print(f"Connected as: {result['user_info']}")
        >>> else:
        ...     print(f"Failed: {result['error']}")
        ...     print(f"Error type: {result['error_type']}")
    """
    result = {
        'success': False,
        'target_url': target_url,
        'secret_scope': secret_scope,
        'credentials_valid': False,
        'connection_successful': False,
        'user_info': None,
        'workspace_host': None,
        'error': None,
        'error_type': None
    }
    
    # Step 1: Validate credentials
    validation = validate_sp_credentials(secret_scope)
    result['credentials_valid'] = validation['valid']
    
    if not validation['valid']:
        result['error'] = "; ".join(validation['errors'])
        result['error_type'] = 'credentials'
        return result
    
    # Step 2: Try to connect
    try:
        client = get_target_client_sp(
            target_url=target_url,
            secret_scope=secret_scope,
            validate_connection=False  # We'll validate manually
        )
        
        # Step 3: Test connection
        user = client.current_user.me()
        
        result['connection_successful'] = True
        result['user_info'] = user.user_name
        result['workspace_host'] = client.config.host
        result['success'] = True
        
    except Exception as e:
        error_msg = str(e)
        result['error'] = error_msg
        
        # Categorize error
        if "blocked by Databricks IP ACL" in error_msg:
            result['error_type'] = 'ip_blocked'
        elif "401" in error_msg or "unauthorized" in error_msg.lower():
            result['error_type'] = 'auth'
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            result['error_type'] = 'permissions'
        elif "credentials" in error_msg.lower():
            result['error_type'] = 'credentials'
        else:
            result['error_type'] = 'connection'
    
    return result


def print_setup_instructions(secret_scope: str = "migration_secrets") -> None:
    """
    Print setup instructions for SP OAuth M2M authentication.
    
    Useful for helping users configure their environment.
    
    Args:
        secret_scope: Name of the secret scope to use in examples
    """
    instructions = f"""
================================================================================
SERVICE PRINCIPAL OAUTH M2M SETUP INSTRUCTIONS
================================================================================

This guide helps you configure Service Principal authentication for 
cross-workspace dashboard migration.

PREREQUISITES:
- Service Principal created in Databricks Account Console
- Account Console UI access
- Workspace Admin access on both source and target workspaces

================================================================================
STEP 1: ADD SERVICE PRINCIPAL TO WORKSPACES (Account Console UI)
================================================================================

1. Log in to Account Console: https://accounts.cloud.databricks.com
2. Navigate to: Workspaces (left sidebar)
3. Click on your SOURCE workspace name
4. Go to "Permissions" tab
5. Click "Add permissions"
6. Search for your Service Principal
7. Select it and set permission level to "User"
8. Click "Save"
9. REPEAT steps 3-8 for your TARGET workspace

================================================================================
STEP 2: CREATE OAUTH SECRET (Account Console UI)
================================================================================

1. In Account Console, go to: User management (left sidebar)
2. Click "Service principals" tab
3. Click on your Service Principal name
4. Go to "Secrets" or "OAuth secrets" tab
5. Click "Generate secret"
6. Set lifetime (recommend: 365 days)
7. IMPORTANT: Copy and save the secret immediately!
   (It's shown only once)
8. Note the Client ID (same as Application ID)

================================================================================
STEP 3: STORE CREDENTIALS IN SECRET SCOPE
================================================================================

Run these commands from your local machine (with Databricks CLI):

# Create secret scope (if it doesn't exist)
databricks secrets create-scope {secret_scope} --profile source-workspace

# Store the SP Client ID
databricks secrets put-secret {secret_scope} sp_client_id --profile source-workspace
# When prompted, paste your Service Principal Application ID

# Store the SP Client Secret
databricks secrets put-secret {secret_scope} sp_client_secret --profile source-workspace
# When prompted, paste the OAuth secret you saved in Step 2

# Verify secrets are stored
databricks secrets list-secrets {secret_scope} --profile source-workspace

================================================================================
STEP 4: TEST CONNECTION
================================================================================

In a Databricks notebook on the SOURCE workspace:

```python
from helpers.sp_oauth_auth import test_sp_connection

result = test_sp_connection(
    target_url="https://YOUR-TARGET-WORKSPACE.cloud.databricks.com",
    secret_scope="{secret_scope}"
)

if result['success']:
    print(f"SUCCESS! Connected as: {{result['user_info']}}")
else:
    print(f"FAILED: {{result['error']}}")
    print(f"Error type: {{result['error_type']}}")
```

================================================================================
STEP 5: ENABLE IN DATABRICKS.YML
================================================================================

Set these variables in your databricks.yml:

variables:
  auth_method: "sp_oauth"  # Change from "pat" to "sp_oauth"
  sp_secret_scope: "{secret_scope}"

================================================================================
TROUBLESHOOTING
================================================================================

ERROR: "SP not found in scope"
  -> Run: databricks secrets put-secret {secret_scope} sp_client_id

ERROR: "401 Unauthorized"
  -> OAuth secret may have expired. Generate a new one in Account Console.

ERROR: "403 Forbidden"
  -> SP not added to target workspace. Add via Account Console > Workspaces.

ERROR: "IP blocked"
  -> Run ./scripts/auto_setup_ip_acl.sh to whitelist your cluster IP.

================================================================================
"""
    print(instructions)


# Convenience exports
__all__ = [
    'get_target_client_sp',
    'validate_sp_credentials',
    'test_sp_connection',
    'print_setup_instructions',
    'REQUIRED_SECRETS'
]
