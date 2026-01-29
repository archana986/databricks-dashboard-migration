#!/usr/bin/env python3
"""
Databricks Lakeview Dashboard Migration Script

This script migrates a Lakeview dashboard from one Databricks workspace to another.
Supports both PAT (Personal Access Token) and OAuth authentication methods.
Now supports configuration files for parameterized, environment-agnostic deployment.

Usage:
    # With config file (recommended for reusable deployments):
    python migrate_dashboard.py --config-file migration_config.json
    
    # With PAT tokens (CLI):
    python migrate_dashboard.py \
        --source-workspace https://workspace1.cloud.databricks.com \
        --source-dashboard-id 01abc123def456 \
        --source-pat-token dapi123... \
        --target-workspace https://workspace2.cloud.databricks.com \
        --target-pat-token dapi456... \
        --target-dashboard-name "My Dashboard" \
        --target-path "/Workspace/Users/user@example.com/Dashboards" \
        --target-warehouse-id abc123def456

    # With OAuth (Azure AD Service Principal):
    export ARM_CLIENT_ID="your-client-id"
    export ARM_TENANT_ID="your-tenant-id"
    export ARM_CLIENT_SECRET="your-client-secret"
    python migrate_dashboard.py \
        --config-file migration_config.json \
        --auth-method oauth

    # Config file + CLI overrides:
    python migrate_dashboard.py \
        --config-file migration_config.json \
        --target-dashboard-name "Override Name" \
        --publish

Author: Generated for Databricks Dashboard Migration
Date: 2026-01-26
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.dashboards import Dashboard
except ImportError:
    print("❌ Error: databricks-sdk not installed.")
    print("   Install with: pip install databricks-sdk")
    sys.exit(1)


class DashboardMigrator:
    """Handles migration of Databricks Lakeview dashboards between workspaces."""

    def __init__(
        self,
        source_workspace: str,
        target_workspace: str,
        auth_method: str = "pat",
        source_pat: Optional[str] = None,
        target_pat: Optional[str] = None,
    ):
        """
        Initialize the migrator.

        Args:
            source_workspace: Source workspace URL
            target_workspace: Target workspace URL
            auth_method: "pat" or "oauth"
            source_pat: Source workspace PAT token (required if auth_method="pat")
            target_pat: Target workspace PAT token (required if auth_method="pat")
        """
        self.source_workspace = source_workspace.rstrip("/")
        self.target_workspace = target_workspace.rstrip("/")
        self.auth_method = auth_method.lower()

        # Create workspace clients
        self.source_client = self._create_client(source_workspace, source_pat)
        self.target_client = self._create_client(target_workspace, target_pat)

    def _create_client(self, workspace_url: str, token: Optional[str] = None) -> WorkspaceClient:
        """Create a WorkspaceClient with appropriate authentication."""
        if self.auth_method == "pat":
            if not token:
                raise ValueError(
                    f"PAT token required for workspace {workspace_url} when auth_method='pat'"
                )
            return WorkspaceClient(host=workspace_url, token=token)
        else:  # oauth
            # OAuth uses environment variables: ARM_CLIENT_ID, ARM_TENANT_ID, ARM_CLIENT_SECRET
            # Or Azure CLI credentials (az login)
            return WorkspaceClient(host=workspace_url)

    def export_dashboard(self, dashboard_id: str) -> Dict:
        """
        Export dashboard from source workspace.

        Args:
            dashboard_id: Dashboard ID to export

        Returns:
            Dictionary containing dashboard metadata and serialized JSON
        """
        print(f"📤 Exporting dashboard {dashboard_id} from {self.source_workspace}...")

        try:
            dashboard = self.source_client.lakeview.get(dashboard_id=dashboard_id)

            serialized_dashboard = dashboard.serialized_dashboard
            dashboard_json = json.loads(serialized_dashboard)

            result = {
                "dashboard_id": dashboard_id,
                "display_name": dashboard.display_name,
                "etag": dashboard.etag,
                "warehouse_id": dashboard.warehouse_id,
                "serialized_dashboard": serialized_dashboard,
                "dashboard_json": dashboard_json,
                "path": getattr(dashboard, "path", None),
            }

            print(f"✅ Dashboard exported: {result['display_name']}")
            return result

        except Exception as e:
            print(f"❌ Error exporting dashboard: {e}")
            raise

    def discover_references(self, dashboard_json: Dict) -> List[Tuple[str, str, str]]:
        """
        Discover all catalog.schema.table references in dashboard queries.

        Args:
            dashboard_json: Dashboard JSON structure

        Returns:
            List of (catalog, schema, table) tuples
        """
        references = set()

        def extract_references(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str):
                        if key in ("query", "sql", "statement") or "query" in key.lower():
                            # Extract catalog.schema.table patterns
                            patterns = [
                                r"`?([a-zA-Z0-9_]+)`?\.`?([a-zA-Z0-9_]+)`?\.`?([a-zA-Z0-9_]+)`?",
                                r"\b([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\b",
                            ]
                            for pattern in patterns:
                                matches = re.findall(pattern, value)
                                for match in matches:
                                    if len(match) == 3:
                                        references.add((match[0], match[1], match[2]))
                    else:
                        extract_references(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_references(item)

        extract_references(dashboard_json)
        return sorted(references)

    def rewrite_references(
        self, dashboard_json: Dict, catalog_schema_map: Dict[Tuple[str, str], Tuple[str, str]]
    ) -> Dict:
        """
        Rewrite catalog/schema references in dashboard JSON.

        Args:
            dashboard_json: Dashboard JSON structure
            catalog_schema_map: Mapping of (old_catalog, old_schema) -> (new_catalog, new_schema)

        Returns:
            Rewritten dashboard JSON
        """
        if not catalog_schema_map:
            return dashboard_json

        def rewrite_sql(sql_string: str) -> str:
            rewritten = sql_string
            for (old_catalog, old_schema), (new_catalog, new_schema) in catalog_schema_map.items():
                # Pattern 1: Backtick-quoted identifiers
                pattern1 = rf"`{re.escape(old_catalog)}`\.`{re.escape(old_schema)}`\."
                replacement1 = f"`{new_catalog}`.`{new_schema}`."
                rewritten = re.sub(pattern1, replacement1, rewritten, flags=re.IGNORECASE)

                # Pattern 2: Bare identifiers
                pattern2 = rf"\b{re.escape(old_catalog)}\.{re.escape(old_schema)}\."
                replacement2 = f"{new_catalog}.{new_schema}."
                rewritten = re.sub(pattern2, replacement2, rewritten, flags=re.IGNORECASE)
            return rewritten

        def walk_and_rewrite(obj):
            if isinstance(obj, dict):
                result = {}
                for key, value in obj.items():
                    if isinstance(value, str) and (
                        key in ("query", "sql", "statement") or "query" in key.lower()
                    ):
                        result[key] = rewrite_sql(value)
                    else:
                        result[key] = walk_and_rewrite(value)
                return result
            elif isinstance(obj, list):
                return [walk_and_rewrite(item) for item in obj]
            else:
                return obj

        return walk_and_rewrite(dashboard_json)

    def validate_queries(
        self, dashboard_json: Dict, warehouse_id: str, catalog: Optional[str] = None, schema: Optional[str] = None
    ) -> List[Dict]:
        """
        Validate dataset queries against target workspace.

        Args:
            dashboard_json: Dashboard JSON structure
            warehouse_id: SQL Warehouse ID for validation
            catalog: Optional catalog name
            schema: Optional schema name

        Returns:
            List of validation results
        """
        queries = []
        if "datasets" in dashboard_json:
            for dataset in dashboard_json["datasets"]:
                if "query" in dataset:
                    queries.append(
                        {"name": dataset.get("name", "unknown"), "query": dataset["query"]}
                    )

        if not queries:
            return []

        print(f"✅ Validating {len(queries)} queries against target workspace...")

        results = []
        for query_info in queries:
            print(f"   Validating: {query_info['name']}...", end=" ")
            try:
                statement = self.target_client.statement_execution.execute_statement(
                    warehouse_id=warehouse_id,
                    statement=query_info["query"],
                    catalog=catalog,
                    schema=schema,
                )

                statement_id = statement.statement_id
                while True:
                    status = self.target_client.statement_execution.get_statement(statement_id)
                    state = status.status.state

                    if state in ("SUCCEEDED", "FAILED", "CANCELED"):
                        success = state == "SUCCEEDED"
                        result = {
                            "name": query_info["name"],
                            "success": success,
                            "state": state,
                            "message": getattr(status.status, "message", None),
                        }
                        results.append(result)
                        status_icon = "✅" if success else "❌"
                        print(f"{status_icon} {state}")
                        break

                    time.sleep(1)

            except Exception as e:
                result = {
                    "name": query_info["name"],
                    "success": False,
                    "state": "ERROR",
                    "message": str(e),
                }
                results.append(result)
                print(f"❌ ERROR: {e}")

        return results

    def import_dashboard(
        self,
        dashboard_name: str,
        dashboard_path: str,
        serialized_dashboard: str,
        warehouse_id: str,
    ) -> str:
        """
        Import dashboard to target workspace.

        Args:
            dashboard_name: Name for the dashboard
            dashboard_path: Workspace path for the dashboard
            serialized_dashboard: Serialized dashboard JSON string
            warehouse_id: SQL Warehouse ID

        Returns:
            New dashboard ID
        """
        print(f"📥 Importing dashboard to {self.target_workspace}...")
        print(f"   Name: {dashboard_name}")
        print(f"   Path: {dashboard_path}")
        print(f"   Warehouse: {warehouse_id}")

        try:
            dashboard = Dashboard.from_dict(
                {
                    "display_name": dashboard_name,
                    "parent_path": dashboard_path,
                    "warehouse_id": warehouse_id,
                    "serialized_dashboard": serialized_dashboard,
                }
            )

            created_dashboard = self.target_client.lakeview.create(dashboard=dashboard)

            dashboard_id = created_dashboard.dashboard_id
            print(f"✅ Dashboard imported successfully!")
            print(f"   Dashboard ID: {dashboard_id}")
            print(f"   URL: {self.target_workspace}/sql/dashboardsv3/{dashboard_id}")

            return dashboard_id

        except Exception as e:
            print(f"❌ Error importing dashboard: {e}")
            raise

    def publish_dashboard(self, dashboard_id: str, embed_credentials: bool = False) -> bool:
        """
        Publish dashboard.

        Args:
            dashboard_id: Dashboard ID to publish
            embed_credentials: Whether to embed credentials for viewers

        Returns:
            True if successful
        """
        print(f"📢 Publishing dashboard {dashboard_id}...")

        try:
            self.target_client.lakeview.publish(
                dashboard_id=dashboard_id, embed_credentials=embed_credentials
            )
            print(f"✅ Dashboard published successfully!")
            return True

        except Exception as e:
            print(f"❌ Error publishing dashboard: {e}")
            return False

    def save_backup(self, dashboard_json: Dict, dashboard_id: str) -> Path:
        """
        Save dashboard JSON as backup file.

        Args:
            dashboard_json: Dashboard JSON structure
            dashboard_id: Dashboard ID for filename

        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"dashboard_backup_{dashboard_id}_{timestamp}.json"
        backup_path = Path(backup_filename)

        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(dashboard_json, f, indent=2, ensure_ascii=False)

        print(f"💾 Backup saved to: {backup_path}")
        return backup_path


def load_config(config_file: str) -> Dict:
    """
    Load configuration from JSON file and resolve environment variable references.
    
    Supports environment variable references in the format ${VAR_NAME} or $VAR_NAME.
    
    Args:
        config_file: Path to JSON configuration file
        
    Returns:
        Dictionary with configuration values (with env vars resolved)
    """
    if not Path(config_file).exists():
        print(f"❌ Error: Config file not found: {config_file}")
        sys.exit(1)
        
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Helper function to resolve environment variables recursively
    def resolve_env_refs(value):
        if isinstance(value, str):
            # Pattern for ${VAR_NAME} or $VAR_NAME
            pattern = r'\$\{([^}]+)\}|\$([A-Z_][A-Z0-9_]*)'
            def replace_env(match):
                var_name = match.group(1) or match.group(2)
                env_value = os.getenv(var_name, '')
                if not env_value:
                    print(f"⚠️  Warning: Environment variable {var_name} not set")
                return env_value
            return re.sub(pattern, replace_env, value)
        elif isinstance(value, dict):
            return {k: resolve_env_refs(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [resolve_env_refs(item) for item in value]
        return value
    
    # Resolve environment variable references
    config = resolve_env_refs(config)
    
    return config


def main():
    """Main migration function with config file support."""
    parser = argparse.ArgumentParser(
        description="Migrate Databricks Lakeview dashboard between workspaces",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    # Config file argument (allows parameterizing most settings)
    parser.add_argument(
        "--config-file",
        help="Path to JSON configuration file (allows parameterizing most settings)",
    )
    
    # Source workspace
    parser.add_argument(
        "--source-workspace",
        help="Source workspace URL (e.g., https://workspace.cloud.databricks.com)",
    )
    parser.add_argument(
        "--source-dashboard-id",
        help="Source dashboard ID (from URL: /sql/dashboardsv3/{id})",
    )
    parser.add_argument(
        "--source-pat-token",
        help="Source workspace PAT token (required if --auth-method=pat). Can use env var ${SOURCE_PAT_TOKEN}",
    )
    
    # Target workspace
    parser.add_argument(
        "--target-workspace",
        help="Target workspace URL (e.g., https://workspace.cloud.databricks.com)",
    )
    parser.add_argument(
        "--target-dashboard-name",
        help="Name for dashboard in target workspace",
    )
    parser.add_argument(
        "--target-path",
        help="Workspace path for dashboard (e.g., /Workspace/Users/user@example.com/Dashboards)",
    )
    parser.add_argument(
        "--target-warehouse-id",
        help="SQL Warehouse ID in target workspace. Can use env var ${TARGET_WAREHOUSE_ID}",
    )
    parser.add_argument(
        "--target-pat-token",
        help="Target workspace PAT token (required if --auth-method=pat). Can use env var ${TARGET_PAT_TOKEN}",
    )
    
    # Authentication
    parser.add_argument(
        "--auth-method",
        choices=["pat", "oauth"],
        help="Authentication method: 'pat' (Personal Access Token) or 'oauth' (Azure AD)",
    )
    
    # Options
    parser.add_argument(
        "--catalog-schema-map",
        help="JSON mapping for catalog/schema rewrites: "
        '{"old_catalog.old_schema": "new_catalog.new_schema"}',
    )
    parser.add_argument(
        "--validate-queries",
        action="store_true",
        help="Validate queries against target workspace before import",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish dashboard after import",
    )
    parser.add_argument(
        "--embed-credentials",
        action="store_true",
        help="Embed credentials when publishing (requires service principal)",
    )
    parser.add_argument(
        "--create-backup",
        action="store_true",
        help="Create backup of exported dashboard JSON",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup file",
    )
    
    # Parse args first
    args = parser.parse_args()
    
    # Load config file if provided
    config = {}
    if args.config_file:
        print(f"📋 Loading configuration from: {args.config_file}")
        config = load_config(args.config_file)
    
    # Helper function to get value from config or args (args override config)
    def get_value(key, default=None):
        # Check CLI args first (they override config)
        if hasattr(args, key) and getattr(args, key) is not None:
            return getattr(args, key)
        # Then check config file (support both flat and nested structures)
        if key in config:
            return config[key]
        # Check nested config structures
        if 'source' in config and key.startswith('source_'):
            nested_key = key.replace('source_', '')
            if nested_key in config['source']:
                return config['source'][nested_key]
        if 'target' in config and key.startswith('target_'):
            nested_key = key.replace('target_', '')
            if nested_key in config['target']:
                return config['target'][nested_key]
        return default
    
    # Merge config and CLI args (CLI overrides config)
    # Support both flat config keys and nested source/target structure
    source_workspace = get_value('source_workspace') or config.get('source', {}).get('workspace')
    source_dashboard_id = get_value('source_dashboard_id') or config.get('source', {}).get('dashboard_id')
    source_pat_token = (
        get_value('source_pat_token') 
        or config.get('source', {}).get('pat_token') 
        or os.getenv('SOURCE_PAT_TOKEN')
    )
    
    target_workspace = get_value('target_workspace') or config.get('target', {}).get('workspace')
    target_dashboard_name = get_value('target_dashboard_name') or config.get('target', {}).get('dashboard_name')
    target_path = get_value('target_path') or config.get('target', {}).get('path')
    target_warehouse_id = (
        get_value('target_warehouse_id') 
        or config.get('target', {}).get('warehouse_id') 
        or os.getenv('TARGET_WAREHOUSE_ID')
    )
    target_pat_token = (
        get_value('target_pat_token') 
        or config.get('target', {}).get('pat_token') 
        or os.getenv('TARGET_PAT_TOKEN')
    )
    
    auth_method = get_value('auth_method') or config.get('auth_method', 'pat')
    
    # Validate required parameters
    required_params = {
        'source_workspace': source_workspace,
        'source_dashboard_id': source_dashboard_id,
        'target_workspace': target_workspace,
        'target_dashboard_name': target_dashboard_name,
        'target_path': target_path,
        'target_warehouse_id': target_warehouse_id,
    }
    
    missing = [k for k, v in required_params.items() if not v]
    if missing:
        print(f"❌ Error: Missing required parameters: {', '.join(missing)}")
        print("   Provide via --config-file or command-line arguments")
        sys.exit(1)
    
    # Validate authentication
    if auth_method == 'pat':
        if not source_pat_token or not target_pat_token:
            print("❌ Error: PAT tokens required when auth_method=pat")
            print("   Provide via --source-pat-token, --target-pat-token, config file, or environment variables")
            sys.exit(1)
    else:  # oauth
        required_env_vars = ["ARM_CLIENT_ID", "ARM_TENANT_ID", "ARM_CLIENT_SECRET"]
        missing = [var for var in required_env_vars if not os.getenv(var)]
        if missing:
            print(f"❌ Error: Missing OAuth environment variables: {', '.join(missing)}")
            print("   Set these before running: export ARM_CLIENT_ID=... ARM_TENANT_ID=... ARM_CLIENT_SECRET=...")
            sys.exit(1)
    
    # Parse catalog/schema mapping
    catalog_schema_map = {}
    catalog_map_config = get_value('catalog_schema_map') or config.get('catalog_schema_map')
    if catalog_map_config:
        try:
            if isinstance(catalog_map_config, str):
                mapping = json.loads(catalog_map_config)
            else:
                mapping = catalog_map_config
            for old_key, new_key in mapping.items():
                old_parts = old_key.split('.', 1)
                new_parts = new_key.split('.', 1)
                if len(old_parts) == 2 and len(new_parts) == 2:
                    catalog_schema_map[(old_parts[0], old_parts[1])] = (
                        new_parts[0],
                        new_parts[1],
                    )
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"❌ Error: Invalid catalog-schema-map format: {e}")
            sys.exit(1)
    
    # Get boolean flags (CLI overrides config)
    validate_queries = (
        get_value('validate_queries') is True 
        or args.validate_queries 
        or config.get('validate_queries', False)
    )
    publish = (
        get_value('publish') is True 
        or args.publish 
        or config.get('publish', False)
    )
    embed_credentials = (
        get_value('embed_credentials') is True 
        or args.embed_credentials 
        or config.get('embed_credentials', False)
    )
    create_backup = (
        not args.no_backup 
        and (
            get_value('create_backup') is True 
            or args.create_backup 
            or config.get('create_backup', True)
        )
    )
    
    # Create migrator
    try:
        migrator = DashboardMigrator(
            source_workspace=source_workspace,
            target_workspace=target_workspace,
            auth_method=auth_method,
            source_pat=source_pat_token,
            target_pat=target_pat_token,
        )
    except Exception as e:
        print(f"❌ Error initializing migrator: {e}")
        sys.exit(1)
    
    # Export dashboard
    try:
        exported = migrator.export_dashboard(source_dashboard_id)
    except Exception as e:
        print(f"❌ Migration failed at export step: {e}")
        sys.exit(1)
    
    # Discover references
    references = migrator.discover_references(exported["dashboard_json"])
    if references:
        print(f"\n🔍 Found {len(references)} catalog.schema.table references:")
        for catalog, schema, table in references:
            print(f"   {catalog}.{schema}.{table}")
    
    # Rewrite references if mapping provided
    if catalog_schema_map:
        print(f"\n🔄 Rewriting catalog/schema references...")
        exported["dashboard_json"] = migrator.rewrite_references(
            exported["dashboard_json"], catalog_schema_map
        )
        exported["serialized_dashboard"] = json.dumps(
            exported["dashboard_json"], separators=(",", ":"), ensure_ascii=False
        )
        
        new_references = migrator.discover_references(exported["dashboard_json"])
        if new_references:
            print(f"   New references:")
            for catalog, schema, table in new_references:
                print(f"   {catalog}.{schema}.{table}")
    
    # Create backup
    if create_backup:
        migrator.save_backup(exported["dashboard_json"], source_dashboard_id)
    
    # Validate queries
    if validate_queries:
        validation_results = migrator.validate_queries(
            exported["dashboard_json"], target_warehouse_id
        )
        if validation_results:
            successful = sum(1 for r in validation_results if r["success"])
            total = len(validation_results)
            print(f"\n📊 Validation Summary: {successful}/{total} queries passed")
            if successful < total:
                print("⚠️  Some queries failed validation. Review errors above.")
    
    # Import dashboard
    try:
        target_dashboard_id = migrator.import_dashboard(
            dashboard_name=target_dashboard_name,
            dashboard_path=target_path,
            serialized_dashboard=exported["serialized_dashboard"],
            warehouse_id=target_warehouse_id,
        )
    except Exception as e:
        print(f"❌ Migration failed at import step: {e}")
        sys.exit(1)
    
    # Publish dashboard
    if publish:
        migrator.publish_dashboard(target_dashboard_id, embed_credentials=embed_credentials)
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 MIGRATION SUMMARY")
    print("=" * 80)
    print(f"\n✅ Source Dashboard:")
    print(f"   Workspace: {source_workspace}")
    print(f"   Dashboard ID: {source_dashboard_id}")
    print(f"   Name: {exported['display_name']}")
    print(f"\n✅ Target Dashboard:")
    print(f"   Workspace: {target_workspace}")
    print(f"   Dashboard ID: {target_dashboard_id}")
    print(f"   Name: {target_dashboard_name}")
    print(f"   URL: {target_workspace}/sql/dashboardsv3/{target_dashboard_id}")
    print(f"\n🎉 Migration completed successfully!")


if __name__ == "__main__":
    main()
