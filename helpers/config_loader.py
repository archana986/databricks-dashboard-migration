"""
Configuration loader for migration workflow.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

# Initialize dbutils for module scope (Databricks-specific)
try:
    dbutils
except NameError:
    import IPython
    dbutils = IPython.get_ipython().user_ns.get("dbutils")

_config_cache: Optional[Dict[str, Any]] = None

def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config.yaml file. 
                    If None, looks in standard locations.
    
    Returns:
        Dictionary with configuration
    
    Raises:
        FileNotFoundError: If config file not found
        yaml.YAMLError: If config file invalid
    """
    global _config_cache
    
    if config_path is None:
        # Dynamically locate config directory
        try:
            # In Databricks workspace/job context
            try:
                notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
                bundle_parent = os.path.dirname(os.path.dirname(notebook_path))
                config_path = f"/Workspace{bundle_parent}/config/config.yaml"
            except:
                # Fallback: try relative paths for local execution
                possible_paths = [
                    "../config/config.yaml",
                    "./config/config.yaml",
                    "config/config.yaml"
                ]
                for path in possible_paths:
                    if Path(path).exists():
                        config_path = path
                        break
        except Exception as e:
            pass
        
        if config_path is None:
            raise FileNotFoundError(
                "config.yaml not found. Ensure config directory is synced in databricks.yml"
            )
    
    # Read config file
    try:
        if config_path.startswith('/Workspace'):
            # Workspace file - use standard Python open
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        elif config_path.startswith('/Volumes') or config_path.startswith('dbfs:'):
            # Volume or DBFS path - use dbutils
            content = dbutils.fs.head(config_path, 10485760)
            config = yaml.safe_load(content)
        else:
            # Local file path
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
    except Exception as e:
        raise yaml.YAMLError(f"Failed to load config from {config_path}: {e}")
    
    # Cache config
    _config_cache = config
    
    # Validate required fields
    _validate_config(config)
    
    return config

def get_config() -> Dict[str, Any]:
    """
    Get cached configuration.
    
    Returns:
        Cached configuration dictionary
    
    Raises:
        RuntimeError: If config not loaded yet
    """
    if _config_cache is None:
        raise RuntimeError("Config not loaded. Call load_config() first.")
    
    return _config_cache

def _validate_config(config: Dict[str, Any]) -> None:
    """Validate required configuration fields."""
    required_fields = [
        'source.workspace_url',
        'target.workspace_url',
        'paths.volume_base'
    ]
    
    for field in required_fields:
        keys = field.split('.')
        value = config
        for key in keys:
            if key not in value:
                raise ValueError(f"Required config field missing: {field}")
            value = value[key]

def get_path(path_key: str, absolute: bool = True) -> str:
    """
    Get path from configuration.
    
    Args:
        path_key: Path key (e.g., 'exported', 'transformed')
        absolute: If True, returns absolute path with volume_base prefix
    
    Returns:
        Path string
    """
    config = get_config()
    volume_base = config['paths']['volume_base']
    
    if path_key == 'volume_base':
        return volume_base
    
    relative_path = config['paths'].get(path_key, path_key)
    
    if absolute:
        return f"{volume_base}/{relative_path}"
    else:
        return relative_path

def get_dashboard_selection() -> Dict[str, Any]:
    """Get dashboard selection configuration."""
    config = get_config()
    return config.get('dashboard_selection', {})

def get_auth_config(workspace: str = 'source') -> Dict[str, Any]:
    """
    Get authentication configuration for a workspace.
    
    Args:
        workspace: 'source' or 'target'
    
    Returns:
        Authentication configuration
    """
    config = get_config()
    return config[workspace]['auth']
