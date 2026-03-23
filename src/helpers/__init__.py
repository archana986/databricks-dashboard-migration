"""
Databricks Dashboard Migration Helper Functions

This package provides reusable functions for dashboard migration workflow.
"""

__version__ = "1.0.0"

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
from .config_validator import (
    validate_configuration,
    validate_and_raise,
    validate_workspace_connectivity,
    validate_volume_paths,
    validate_warehouse_config,
    validate_mapping_csv,
    validate_permissions
)

__all__ = [
    # Config
    'load_config', 'set_config', 'get_config', 'get_path',
    # Auth
    'create_workspace_client', 'create_target_workspace_client',
    # Discovery
    'discover_dashboards', 'generate_inventory', 'save_inventory_to_csv', 'load_inventory_from_csv',
    # Export / Transform
    'export_dashboard', 'transform_dashboard_json', 'load_mapping_csv',
    # Permissions
    'get_dashboard_permissions', 'apply_dashboard_permissions', 'load_permissions_from_csv',
    # Schedules
    'get_dashboard_schedules', 'apply_dashboard_schedules', 'load_schedules_from_csv',
    # Volume Utils
    'read_volume_file', 'write_volume_file', 'list_volume_files',
    'ensure_directory_exists', 'read_csv_from_volume', 'write_csv_to_volume',
    'archive_old_files', 'cleanup_empty_archives',
    # Deployment Package
    'DashboardDeploymentPackage', 'PermissionDefinition', 'ScheduleDefinition',
    'SubscriptionDefinition', 'build_deployment_packages',
    # SDK Deployer
    'deploy_via_sdk', 'apply_permissions_sdk', 'apply_schedules_sdk', 'resolve_warehouse',
    # Config Validator
    'validate_configuration', 'validate_and_raise', 'validate_workspace_connectivity',
    'validate_volume_paths', 'validate_warehouse_config', 'validate_mapping_csv',
    'validate_permissions',
]
