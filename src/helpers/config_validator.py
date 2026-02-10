"""
Configuration validation for dashboard migration.

This module provides pre-flight validation to catch configuration errors
before migration starts, improving user experience and debugging.
"""

from typing import Dict, List, Tuple
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import DatabricksError
from .dbutils_helper import get_dbutils as _get_dbutils
import re


def validate_workspace_connectivity(config: Dict) -> Tuple[bool, List[str]]:
    """
    Validate connectivity to source workspace.
    
    Note: Target workspace connectivity is checked separately during deployment
    due to cross-workspace authentication complexity.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        tuple: (success: bool, errors: List[str])
    """
    errors = []
    
    try:
        source_url = config.get('source', {}).get('workspace_url')
        if not source_url:
            errors.append("Source workspace URL not configured")
            return False, errors
        
        # Validate URL format (AWS: .cloud.databricks.com, Azure: .azuredatabricks.net, GCP: .gcp.databricks.com)
        if not re.match(r'https://[a-z0-9-]+(\.[0-9]+)?\.(cloud\.databricks\.com|azuredatabricks\.net|gcp\.databricks\.com)', source_url):
            errors.append(f"Invalid source workspace URL format: {source_url}")
        
        # Try to connect (this should always work since we're running in source workspace)
        from .auth import create_workspace_client
        try:
            client = create_workspace_client(workspace='source', custom_config=config.get('source'))
            user = client.current_user.me()
            # Success - no errors
        except Exception as e:
            errors.append(f"Cannot connect to source workspace: {str(e)}")
    
    except Exception as e:
        errors.append(f"Workspace connectivity check failed: {str(e)}")
    
    return len(errors) == 0, errors


def validate_volume_paths(config: Dict) -> Tuple[bool, List[str]]:
    """
    Validate that UC volume paths exist and are accessible.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        tuple: (success: bool, errors: List[str])
    """
    errors = []
    dbutils = _get_dbutils()
    
    try:
        # Fix: volume_base is under config['paths']['volume_base'], not config['volume']['base_path']
        volume_base = config.get('paths', {}).get('volume_base')
        if not volume_base:
            errors.append("Volume base path not configured")
            return False, errors
        
        # Validate volume path format
        if not volume_base.startswith('/Volumes/'):
            errors.append(f"Volume path must start with /Volumes/ (got: {volume_base})")
            return False, errors
        
        # Check if volume path is accessible
        try:
            dbutils.fs.ls(volume_base)
        except Exception as e:
            errors.append(f"Cannot access volume path {volume_base}: {str(e)}")
            return False, errors
        
        # Check required subdirectories (if they exist in config)
        # Fix: paths are under config['paths'], not config['volume']
        paths_config = config.get('paths', {})
        required_dirs_map = {
            'exported': 'exported',
            'transformed': 'transformed',
            'bundles': 'bundles'
        }
        
        for config_key, dir_name in required_dirs_map.items():
            dir_path = paths_config.get(config_key)
            if dir_path:
                full_path = f"{volume_base}/{dir_path}"
                # Try to list (will auto-create if needed in actual workflow)
                # Just check parent exists
                try:
                    dbutils.fs.ls(volume_base)
                except Exception as e:
                    errors.append(f"Volume directory {dir_name} parent not accessible: {str(e)}")
    
    except Exception as e:
        errors.append(f"Volume path validation failed: {str(e)}")
    
    return len(errors) == 0, errors


def validate_warehouse_config(config: Dict) -> Tuple[bool, List[str]]:
    """
    Validate warehouse configuration (ID or name).
    
    Args:
        config: Configuration dictionary
    
    Returns:
        tuple: (success: bool, errors: List[str])
    """
    errors = []
    warnings = []
    
    try:
        # Fix: warehouse config is under config['warehouse'], not config['target']
        warehouse_id = config.get('warehouse', {}).get('warehouse_id')
        warehouse_name = config.get('warehouse', {}).get('warehouse_name')
        
        if not warehouse_id and not warehouse_name:
            # Warehouse is optional for export-only workflows (Step 3)
            # Only required for deployment (Step 4)
            warnings.append("No warehouse configured (optional for export, required for deploy)")
            return True, warnings  # Warning only, not an error
        
        if warehouse_id:
            # Warehouse ID provided (preferred)
            if not re.match(r'^[a-f0-9]{16}$', warehouse_id):
                warnings.append(f"Warehouse ID format looks unusual: {warehouse_id} (expected 16 hex chars)")
        else:
            # Only warehouse name provided - will need to resolve at deployment time
            warnings.append(f"Using warehouse name '{warehouse_name}' - will resolve to ID at deployment time")
    
    except Exception as e:
        errors.append(f"Warehouse config validation failed: {str(e)}")
    
    # Warnings don't fail validation
    return len(errors) == 0, errors + warnings


def validate_mapping_csv(config: Dict) -> Tuple[bool, List[str]]:
    """
    Validate mapping CSV file structure and accessibility.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        tuple: (success: bool, errors: List[str])
    """
    errors = []
    warnings = []
    dbutils = _get_dbutils()
    
    try:
        # Fix: transformation config doesn't exist in current config structure
        # This validation is for optional transformation mappings, so skip if not configured
        transformation_enabled = config.get('transformation', {}).get('enabled', False)
        if isinstance(transformation_enabled, str):
            transformation_enabled = transformation_enabled.lower() == 'true'
        
        if not transformation_enabled:
            warnings.append("Transformation mapping CSV not configured - using direct export/import")
            return True, warnings
        
        # Fix: volume_base is under config['paths']['volume_base']
        volume_base = config.get('paths', {}).get('volume_base')
        mapping_csv = config.get('transformation', {}).get('mapping_csv_path')
        
        if not mapping_csv:
            warnings.append("Transformation enabled but mapping_csv_path not configured - using direct mapping")
            return True, warnings
        
        # Construct full path
        csv_path = f"{volume_base}/{mapping_csv}"
        
        # Check if file exists
        try:
            content = dbutils.fs.head(csv_path, 1024)  # Read first 1KB
            
            # Basic CSV structure validation
            lines = content.split('\n')
            if len(lines) < 2:
                errors.append(f"Mapping CSV appears empty: {csv_path}")
                return False, errors
            
            header = lines[0].lower()
            required_columns = ['source_catalog', 'source_schema', 'target_catalog', 'target_schema']
            
            missing_columns = [col for col in required_columns if col not in header]
            if missing_columns:
                errors.append(f"Mapping CSV missing required columns: {', '.join(missing_columns)}")
            
        except Exception as e:
            errors.append(f"Cannot access mapping CSV {csv_path}: {str(e)}")
            return False, errors
    
    except Exception as e:
        errors.append(f"Mapping CSV validation failed: {str(e)}")
    
    return len(errors) == 0, errors + warnings


def validate_permissions(config: Dict) -> Tuple[bool, List[str]]:
    """
    Validate that user has required permissions by checking ONE dashboard
    from the approved inventory (fast and targeted).
    
    Args:
        config: Configuration dictionary
    
    Returns:
        tuple: (success: bool, errors: List[str])
    """
    errors = []
    warnings = []
    dbutils = _get_dbutils()
    
    try:
        from .auth import create_workspace_client
        client = create_workspace_client(workspace='source', custom_config=config.get('source'))
        
        # Get paths from config
        volume_base = config.get('paths', {}).get('volume_base', '')
        inventory_approved = config.get('paths', {}).get('inventory_approved', 'dashboard_inventory_approved')
        
        # Try to load first dashboard ID from approved inventory
        inventory_path = f"{volume_base}/{inventory_approved}"
        dashboard_id = None
        
        try:
            # Find CSV file in inventory path
            files = dbutils.fs.ls(inventory_path)
            csv_files = [f for f in files if f.name.endswith('.csv')]
            
            if csv_files:
                # Read first few lines to get a dashboard ID
                csv_content = dbutils.fs.head(csv_files[0].path, 4096)
                lines = csv_content.strip().split('\n')
                
                if len(lines) > 1:
                    # Parse header to find dashboard_id column
                    header = lines[0].lower().split(',')
                    if 'dashboard_id' in header:
                        id_idx = header.index('dashboard_id')
                        first_row = lines[1].split(',')
                        if len(first_row) > id_idx:
                            dashboard_id = first_row[id_idx].strip().strip('"')
        except Exception as e:
            warnings.append(f"Could not load inventory for permission check: {e}")
        
        # Validate permission access using ONE dashboard
        if dashboard_id:
            try:
                # Try to get permissions for this specific dashboard
                perms = client.permissions.get("dashboards", dashboard_id)
                # Success - user has permission access
            except Exception as e:
                errors.append(f"Cannot read dashboard permissions: {str(e)}")
        else:
            # No inventory yet - just verify basic Lakeview API access with single item
            try:
                # Use iterator to get just first item (not full list)
                next(iter(client.lakeview.list()), None)
            except Exception as e:
                errors.append(f"Cannot access Lakeview API: {str(e)}")
    
    except Exception as e:
        errors.append(f"Permission validation failed: {str(e)}")
    
    return len(errors) == 0, errors + warnings


def validate_configuration(config: Dict, verbose: bool = True) -> Dict:
    """
    Run all configuration validations.
    
    Args:
        config: Configuration dictionary from config_loader
        verbose: Print detailed validation results
    
    Returns:
        dict: Validation results with keys:
            - 'valid': bool (True if all checks passed)
            - 'errors': List[str] (blocking errors)
            - 'warnings': List[str] (non-blocking warnings)
            - 'checks': Dict[str, Tuple[bool, List[str]]] (individual check results)
    """
    if verbose:
        print("="*80)
        print("CONFIGURATION VALIDATION")
        print("="*80)
        print()
    
    checks = {}
    all_errors = []
    all_warnings = []
    
    # Run all validations
    validations = [
        ('Workspace Connectivity', validate_workspace_connectivity),
        ('Volume Paths', validate_volume_paths),
        ('Warehouse Config', validate_warehouse_config),
        ('Mapping CSV', validate_mapping_csv),
        ('Permissions', validate_permissions)
    ]
    
    for check_name, validator_func in validations:
        if verbose:
            print(f"🔍 {check_name}...", end=" ")
        
        try:
            success, messages = validator_func(config)
            checks[check_name] = (success, messages)
            
            # Separate errors from warnings
            # Warnings typically contain "warning" in lowercase
            errors = [m for m in messages if 'warning' not in m.lower()]
            warnings = [m for m in messages if 'warning' in m.lower()]
            
            if success:
                if verbose:
                    print("✅")
                    if warnings:
                        for warning in warnings:
                            print(f"   ⚠️  {warning}")
            else:
                if verbose:
                    print("❌")
                    for error in errors:
                        print(f"   ❌ {error}")
                all_errors.extend(errors)
            
            all_warnings.extend(warnings)
        
        except Exception as e:
            checks[check_name] = (False, [f"Validation check crashed: {str(e)}"])
            all_errors.append(f"{check_name} check failed: {str(e)}")
            if verbose:
                print(f"❌ {str(e)}")
    
    if verbose:
        print()
        print("="*80)
        if all_errors:
            print(f"❌ VALIDATION FAILED - {len(all_errors)} error(s)")
            print("="*80)
            print()
            print("Errors that must be fixed:")
            for i, error in enumerate(all_errors, 1):
                print(f"  {i}. {error}")
        else:
            print("✅ VALIDATION PASSED")
            if all_warnings:
                print(f"⚠️  {len(all_warnings)} warning(s)")
            print("="*80)
            if all_warnings:
                print()
                print("Warnings (non-blocking):")
                for i, warning in enumerate(all_warnings, 1):
                    print(f"  {i}. {warning}")
        print()
    
    return {
        'valid': len(all_errors) == 0,
        'errors': all_errors,
        'warnings': all_warnings,
        'checks': checks
    }


def validate_and_raise(config: Dict, verbose: bool = True) -> bool:
    """
    Validate configuration and raise exception if invalid.
    
    Convenience function for notebook cells.
    
    Args:
        config: Configuration dictionary
        verbose: Print validation details
    
    Returns:
        bool: True if valid
    
    Raises:
        Exception: If configuration is invalid
    """
    results = validate_configuration(config, verbose=verbose)
    
    if not results['valid']:
        error_summary = '\n  - '.join(results['errors'])
        raise Exception(
            f"Configuration validation failed:\n  - {error_summary}\n\n"
            "Fix these errors before proceeding."
        )
    
    return True
