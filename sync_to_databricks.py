#!/usr/bin/env python3
"""
Databricks Workspace Sync Script (Python Version)

Purpose: Sync local notebooks and files to Databricks workspace
Profile: e2-demo-field-eng
Target: /Workspace/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration

Usage:
    python sync_to_databricks.py
    
    # Or with custom options:
    python sync_to_databricks.py --profile e2-demo-field-eng --dry-run
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple
import argparse
import base64

try:
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.workspace import ImportFormat
except ImportError:
    print("❌ Error: databricks-sdk not installed")
    print("\nInstall it with:")
    print("  pip install databricks-sdk")
    sys.exit(1)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Default Databricks profile
DEFAULT_PROFILE = "e2-demo-field-eng"

# Workspace details
WORKSPACE_URL = "https://e2-demo-field-eng.cloud.databricks.com"
TARGET_PATH = "/Workspace/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration"

# Files to sync (modular structure)
FILES_TO_SYNC = [
    # Configuration files
    "config/config.yaml",
    "config/config_example.yaml",
    
    # Helper modules (reusable Python functions)
    "helpers/__init__.py",
    "helpers/auth.py",
    "helpers/bundle_generator.py",
    "helpers/config_loader.py",
    "helpers/discovery.py",
    "helpers/export.py",
    "helpers/permissions.py",
    "helpers/transform.py",
    "helpers/volume_utils.py",
    
    # Bundle approach notebooks (recommended)
    "Bundle/Bundle_01_Export_and_Transform.ipynb",
    "Bundle/Bundle_02_Generate_and_Deploy.ipynb",
    "Bundle/README.md",
    
    # Manual approach notebooks (alternative)
    "notebooks/01_Export_and_Transform.ipynb",
    "notebooks/02_Apply_Permissions.ipynb",
    
    # Documentation
    "TESTING_GUIDE.md",
    "START_HERE.md",
    "README.md",
    "README_MODULAR.md",
    "QUICKSTART_MODULAR.md",
    
    # CSV templates
    "catalog_schema_mapping_template.csv",
    "catalog_schema_mapping.csv",
    
    # Setup guides
    "DATABRICKS_REPOS_SETUP.md",
    "SYNC_LIMITATION.md",
    "SYNC_COMPARISON.md",
    "EXECUTE_NOW.md",
    "FIRST_STEPS.md",
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def print_header(text: str):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)

def print_success(text: str):
    """Print success message"""
    print(f"✅ {text}")

def print_error(text: str):
    """Print error message"""
    print(f"❌ {text}")

def print_warning(text: str):
    """Print warning message"""
    print(f"⚠️  {text}")

def print_info(text: str):
    """Print info message"""
    print(f"ℹ️  {text}")

def get_format(filename: str) -> ImportFormat:
    """Determine import format based on file extension"""
    if filename.endswith('.ipynb'):
        return ImportFormat.JUPYTER
    elif filename.endswith('.py'):
        return ImportFormat.SOURCE
    else:
        return ImportFormat.AUTO

def ensure_parent_directory(client: WorkspaceClient, file_path: str, dry_run: bool = False) -> bool:
    """Ensure parent directory exists for a file path"""
    parent_dir = "/".join(file_path.split("/")[:-1])
    if not parent_dir:
        return True
    
    try:
        if not dry_run:
            client.workspace.mkdirs(parent_dir)
        return True
    except Exception as e:
        # Directory might already exist, which is fine
        return True

def delete_if_exists(client: WorkspaceClient, path: str) -> bool:
    """Delete a file or folder if it exists"""
    try:
        client.workspace.delete(path, recursive=True)
        return True
    except Exception:
        # Path doesn't exist, which is fine
        return False

def upload_file(
    client: WorkspaceClient,
    local_path: Path,
    remote_path: str,
    dry_run: bool = False
) -> bool:
    """
    Upload a single file to Databricks workspace
    
    Args:
        client: Databricks WorkspaceClient
        local_path: Path to local file
        remote_path: Target path in workspace
        dry_run: If True, only simulate upload
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not local_path.exists():
            print_warning(f"File not found: {local_path} (skipping)")
            return False
        
        # Show relative path for clarity
        relative_path = str(local_path).split("Catalog Migration/")[-1] if "Catalog Migration/" in str(local_path) else local_path.name
        print_info(f"Uploading: {relative_path}")
        
        if dry_run:
            print_success(f"[DRY RUN] Would upload to: {remote_path}")
            return True
        
        # Ensure parent directory exists
        ensure_parent_directory(client, remote_path, dry_run)
        
        # Read file content
        with open(local_path, 'rb') as f:
            content = f.read()
        
        # Base64 encode content for Databricks API
        content_b64 = base64.b64encode(content).decode('utf-8')
        
        # Determine format
        format_type = get_format(local_path.name)
        
        # For Python files in folders (helpers/, etc.), delete first then upload
        # This avoids the "Overwrite cannot be used for source format when importing a folder" error
        is_python_in_folder = local_path.suffix == '.py' and '/' in relative_path
        
        if is_python_in_folder:
            delete_if_exists(client, remote_path)
            # Upload without overwrite flag for Python files in folders
            client.workspace.import_(
                path=remote_path,
                format=format_type,
                content=content_b64
            )
        else:
            # Upload with overwrite for other files
            client.workspace.import_(
                path=remote_path,
                format=format_type,
                content=content_b64,
                overwrite=True
            )
        
        print_success(f"✓ {relative_path}")
        return True
        
    except Exception as e:
        print_error(f"✗ {relative_path}: {e}")
        return False

def create_target_directory(
    client: WorkspaceClient,
    target_path: str,
    dry_run: bool = False
) -> bool:
    """Create target directory in workspace"""
    try:
        if dry_run:
            print_info(f"[DRY RUN] Would create directory: {target_path}")
            return True
        
        # Try to create directory (will succeed if already exists)
        client.workspace.mkdirs(target_path)
        print_success("Target directory ready")
        return True
        
    except Exception as e:
        print_warning(f"Could not create directory: {e}")
        return False

def validate_connection(profile: str) -> Tuple[bool, WorkspaceClient]:
    """
    Validate connection to Databricks workspace
    
    Returns:
        Tuple of (success, client)
    """
    try:
        # Initialize client with profile
        client = WorkspaceClient(profile=profile)
        
        # Test connection
        user = client.current_user.me()
        
        print_success(f"Connected to workspace")
        print(f"   User: {user.user_name}")
        print(f"   Workspace: {client.config.host}")
        
        return True, client
        
    except Exception as e:
        print_error(f"Connection failed: {e}")
        print("")
        print("Make sure you have configured the profile:")
        print(f"  databricks configure --token --profile {profile}")
        print("")
        print("Or set environment variables:")
        print("  export DATABRICKS_HOST=https://e2-demo-field-eng.cloud.databricks.com")
        print("  export DATABRICKS_TOKEN=your-pat-token")
        
        return False, None

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main sync function"""
    parser = argparse.ArgumentParser(
        description="Sync notebooks to Databricks workspace"
    )
    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE,
        help=f"Databricks profile to use (default: {DEFAULT_PROFILE})"
    )
    parser.add_argument(
        "--target-path",
        default=TARGET_PATH,
        help=f"Target path in workspace (default: {TARGET_PATH})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate upload without actually uploading"
    )
    
    args = parser.parse_args()
    
    # Get script directory
    script_dir = Path(__file__).parent
    
    # Print configuration
    print_header("DATABRICKS WORKSPACE SYNC")
    print("")
    print("Configuration:")
    print(f"  Profile:     {args.profile}")
    print(f"  Workspace:   {WORKSPACE_URL}")
    print(f"  Target Path: {args.target_path}")
    print(f"  Local Dir:   {script_dir}")
    print(f"  Dry Run:     {args.dry_run}")
    
    # Validate connection
    print_header("VALIDATING CONNECTION")
    success, client = validate_connection(args.profile)
    
    if not success:
        sys.exit(1)
    
    # Create target directory
    print("")
    print_header("PREPARING TARGET DIRECTORY")
    create_target_directory(client, args.target_path, args.dry_run)
    
    # Upload files
    print("")
    print_header("UPLOADING FILES")
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for filename in FILES_TO_SYNC:
        local_path = script_dir / filename
        remote_path = f"{args.target_path}/{filename}"
        
        if not local_path.exists():
            skip_count += 1
            continue
        
        if upload_file(client, local_path, remote_path, args.dry_run):
            success_count += 1
        else:
            fail_count += 1
    
    # Print summary
    print("")
    print_header("SYNC SUMMARY")
    print("")
    print("Results:")
    print(f"  ✅ Uploaded:  {success_count} files")
    print(f"  ❌ Failed:    {fail_count} files")
    print(f"  ⊘ Skipped:   {skip_count} files (not found)")
    
    if success_count > 0:
        print("")
        print_success("Sync completed!")
        print("")
        print("View files at:")
        print(f"  {WORKSPACE_URL}#workspace{args.target_path}")
        
        if args.dry_run:
            print("")
            print_info("This was a DRY RUN. No files were actually uploaded.")
            print_info("Remove --dry-run flag to perform actual upload.")
    
    if fail_count > 0:
        print("")
        print_error("Some files failed to upload. Check errors above.")
        sys.exit(1)

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Sync interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
