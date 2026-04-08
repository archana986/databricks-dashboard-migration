"""
Databricks Dashboard Migration — Source Helpers

Modules for inventory generation, export, transform, permissions, and schedules.
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
    'load_config', 'set_config', 'get_config', 'get_path',
    'create_workspace_client', 'create_target_workspace_client',
    'discover_dashboards', 'generate_inventory', 'save_inventory_to_csv', 'load_inventory_from_csv',
    'export_dashboard', 'transform_dashboard_json', 'load_mapping_csv',
    'get_dashboard_permissions', 'apply_dashboard_permissions',
    'get_dashboard_schedules', 'apply_dashboard_schedules',
    'read_volume_file', 'write_volume_file', 'list_volume_files',
    'ensure_directory_exists', 'read_csv_from_volume', 'write_csv_to_volume',
    'archive_old_files', 'cleanup_empty_archives',
    'validate_configuration', 'validate_and_raise', 'validate_workspace_connectivity',
    'validate_volume_paths', 'validate_warehouse_config', 'validate_mapping_csv',
    'validate_permissions',
]
