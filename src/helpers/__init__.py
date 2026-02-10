"""
Databricks Dashboard Migration Helper Functions

This package provides reusable functions for dashboard migration workflow.
"""

__version__ = "1.0.0"

# Import commonly used functions for convenience
from .config_loader import load_config, set_config, get_config, get_path
from .auth import create_workspace_client, create_target_workspace_client
from .discovery import discover_dashboards, generate_inventory, save_inventory_to_csv, load_inventory_from_csv
from .export import export_dashboard
from .transform import transform_dashboard_json, load_mapping_csv
from .permissions import get_dashboard_permissions, apply_dashboard_permissions
from .schedules import get_dashboard_schedules, apply_dashboard_schedules
from .volume_utils import (
    read_volume_file, write_volume_file, list_volume_files, 
    ensure_directory_exists, read_csv_from_volume, write_csv_to_volume,
    archive_old_files, cleanup_empty_archives
)
from .bundle_generator import (
    generate_bundle_structure,
    validate_bundle,
    deploy_bundle,
    convert_permissions_for_bundle
)
from .deployment_package import (
    DashboardDeploymentPackage,
    PermissionDefinition,
    ScheduleDefinition,
    SubscriptionDefinition,
    build_deployment_packages,
    load_permissions_from_csv,
    load_schedules_from_csv
)
from .sdk_deployer import (
    deploy_via_sdk,
    apply_permissions_sdk,
    apply_schedules_sdk,
    resolve_warehouse
)
from .ip_acl_manager import (
    detect_cluster_ip,
    check_ip_whitelist_status,
    suggest_whitelist_command,
    wait_for_whitelist_propagation,
    format_status_message,
    check_and_report_status,
    get_stored_cluster_ip,
    save_cluster_ip
)
from .config_validator import (
    validate_configuration,
    validate_and_raise,
    validate_workspace_connectivity,
    validate_volume_paths,
    validate_warehouse_config,
    validate_mapping_csv,
    validate_permissions
)

# SP OAuth M2M Authentication (optional module - can be detached)
# This module provides Service Principal OAuth M2M authentication for cross-workspace access
# If the module is not present, SP auth will not be available but other auth methods will work
try:
    from .sp_oauth_auth import (
        get_target_client_sp,
        validate_sp_credentials,
        test_sp_connection,
        print_setup_instructions as print_sp_setup_instructions
    )
    _SP_OAUTH_AVAILABLE = True
except ImportError:
    _SP_OAUTH_AVAILABLE = False
    # Define stub functions so code doesn't break if module is removed
    def get_target_client_sp(*args, **kwargs):
        raise ImportError("SP OAuth module not available. Install helpers/sp_oauth_auth.py")
    def validate_sp_credentials(*args, **kwargs):
        raise ImportError("SP OAuth module not available. Install helpers/sp_oauth_auth.py")
    def test_sp_connection(*args, **kwargs):
        raise ImportError("SP OAuth module not available. Install helpers/sp_oauth_auth.py")
    def print_sp_setup_instructions(*args, **kwargs):
        raise ImportError("SP OAuth module not available. Install helpers/sp_oauth_auth.py")

__all__ = [
    # Config
    'load_config',
    'set_config',
    'get_config',
    'get_path',
    # Auth
    'create_workspace_client',
    'create_target_workspace_client',
    # Discovery
    'discover_dashboards',
    'generate_inventory',
    'save_inventory_to_csv',
    'load_inventory_from_csv',
    # Export/Transform
    'export_dashboard',
    'transform_dashboard_json',
    'load_mapping_csv',
    # Permissions
    'get_dashboard_permissions',
    'apply_dashboard_permissions',
    'load_permissions_from_csv',
    # Schedules
    'get_dashboard_schedules',
    'apply_dashboard_schedules',
    'load_schedules_from_csv',
    # Volume Utils
    'read_volume_file',
    'write_volume_file',
    'list_volume_files',
    'ensure_directory_exists',
    'read_csv_from_volume',
    'write_csv_to_volume',
    'archive_old_files',
    'cleanup_empty_archives',
    # Bundle Generator
    'generate_bundle_structure',
    'validate_bundle',
    'deploy_bundle',
    'convert_permissions_for_bundle',
    # Deployment Package
    'DashboardDeploymentPackage',
    'PermissionDefinition',
    'ScheduleDefinition',
    'SubscriptionDefinition',
    'build_deployment_packages',
    # SDK Deployer
    'deploy_via_sdk',
    'apply_permissions_sdk',
    'apply_schedules_sdk',
    'resolve_warehouse',
    # IP ACL Manager
    'detect_cluster_ip',
    'check_ip_whitelist_status',
    'suggest_whitelist_command',
    'wait_for_whitelist_propagation',
    'format_status_message',
    'check_and_report_status',
    'get_stored_cluster_ip',
    'save_cluster_ip',
    # Config Validator
    'validate_configuration',
    'validate_and_raise',
    'validate_workspace_connectivity',
    'validate_volume_paths',
    'validate_warehouse_config',
    'validate_mapping_csv',
    'validate_permissions',
    # SP OAuth M2M (optional - may not be available if module detached)
    'get_target_client_sp',
    'validate_sp_credentials',
    'test_sp_connection',
    'print_sp_setup_instructions',
    '_SP_OAUTH_AVAILABLE'
]
