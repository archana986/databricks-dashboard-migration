"""
Databricks Dashboard Migration Helper Functions

This package provides reusable functions for dashboard migration workflow.
"""

__version__ = "1.0.0"

# Import commonly used functions for convenience
from .config_loader import load_config, get_config, get_path
from .auth import create_workspace_client
from .discovery import discover_dashboards, generate_inventory, save_inventory_to_csv, load_inventory_from_csv
from .export import export_dashboard
from .transform import transform_dashboard_json, load_mapping_csv
from .permissions import get_dashboard_permissions, apply_dashboard_permissions, load_permissions_from_volume
from .volume_utils import read_volume_file, write_volume_file, list_volume_files, ensure_directory_exists
from .bundle_generator import (
    generate_bundle_structure,
    validate_bundle,
    deploy_bundle,
    convert_permissions_for_bundle
)

__all__ = [
    'load_config',
    'get_config',
    'get_path',
    'create_workspace_client',
    'discover_dashboards',
    'generate_inventory',
    'save_inventory_to_csv',
    'load_inventory_from_csv',
    'export_dashboard',
    'transform_dashboard_json',
    'load_mapping_csv',
    'get_dashboard_permissions',
    'apply_dashboard_permissions',
    'load_permissions_from_volume',
    'read_volume_file',
    'write_volume_file',
    'list_volume_files',
    'ensure_directory_exists',
    'generate_bundle_structure',
    'validate_bundle',
    'deploy_bundle',
    'convert_permissions_for_bundle'
]
