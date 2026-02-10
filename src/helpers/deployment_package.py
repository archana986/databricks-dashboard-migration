"""
Deployment package data structures and builders.

This module provides unified data structures for dashboard deployment
that include dashboard definitions, permissions, and schedules.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json


@dataclass
class PermissionDefinition:
    """Permission/ACL definition for a dashboard."""
    principal: str
    principal_type: str  # "user", "group", "service_principal"
    level: str  # "CAN_VIEW", "CAN_RUN", "CAN_MANAGE"


@dataclass
class SubscriptionDefinition:
    """Subscription definition for a schedule."""
    # Either user_id (for user subscriptions) or destination_id (for destination subscriptions)
    user_id: Optional[int] = None  # For user subscribers
    destination_id: Optional[str] = None  # For destination subscribers (webhooks, etc.)
    subject: Optional[str] = None


@dataclass
class ScheduleDefinition:
    """Schedule definition for a dashboard."""
    display_name: str
    quartz_cron_expression: str
    timezone_id: str
    pause_status: str  # "PAUSED" or "UNPAUSED"
    subscriptions: List[SubscriptionDefinition] = field(default_factory=list)


@dataclass
class DashboardDeploymentPackage:
    """
    Complete deployment package for a single dashboard.
    
    Includes dashboard definition, permissions, and schedules.
    Used by both asset bundle and SDK direct deployment paths.
    """
    # Dashboard metadata
    dashboard_id: str
    dashboard_name: str
    
    # Dashboard definition
    dashboard_json: Dict
    
    # Permissions
    permissions: List[PermissionDefinition] = field(default_factory=list)
    
    # Schedules (with subscriptions)
    schedules: List[ScheduleDefinition] = field(default_factory=list)
    
    # Deployment metadata
    source_path: Optional[str] = None
    target_path: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'dashboard_id': self.dashboard_id,
            'dashboard_name': self.dashboard_name,
            'dashboard_json': self.dashboard_json,
            'permissions': [
                {'principal': p.principal, 'principal_type': p.principal_type, 'level': p.level}
                for p in self.permissions
            ],
            'schedules': [
                {
                    'display_name': s.display_name,
                    'quartz_cron_expression': s.quartz_cron_expression,
                    'timezone_id': s.timezone_id,
                    'pause_status': s.pause_status,
                    'subscriptions': [
                        {'destination_type': sub.destination_type, 'destination_id': sub.destination_id, 'subject': sub.subject}
                        for sub in s.subscriptions
                    ]
                }
                for s in self.schedules
            ],
            'source_path': self.source_path,
            'target_path': self.target_path
        }


def build_deployment_packages(
    transformed_path: str,
    permissions_map: Optional[Dict[str, Dict]] = None,
    schedules_map: Optional[Dict[str, Dict]] = None
) -> List[DashboardDeploymentPackage]:
    """
    Build deployment packages from transformed JSONs and metadata.
    
    Args:
        transformed_path: Path to transformed dashboard JSONs in UC volume
        permissions_map: Dict mapping dashboard_id -> permissions data
        schedules_map: Dict mapping dashboard_id -> schedules data
    
    Returns:
        List of DashboardDeploymentPackage objects ready for deployment
    """
    from .dbutils_helper import get_dbutils
    import time
    
    dbutils = get_dbutils()
    packages = []
    
    # List all transformed dashboard JSON files
    list_start = time.time()
    files = dbutils.fs.ls(transformed_path)
    dashboard_files = [f for f in files if f.name.endswith('.json') and f.name.startswith('dashboard_')]
    list_duration = time.time() - list_start
    
    print(f"   📁 Found {len(dashboard_files)} dashboard files (took {list_duration:.2f}s)")
    
    # Process files with progress indicator
    for idx, file_info in enumerate(dashboard_files, 1):
        file_start = time.time()
        
        # Progress indicator (every 10 files or first/last)
        if idx == 1 or idx == len(dashboard_files) or idx % 10 == 0:
            print(f"   📊 Processing file {idx}/{len(dashboard_files)}: {file_info.name[:50]}...")
        
        # Read dashboard JSON (optimized: only read what we need)
        file_content = dbutils.fs.head(file_info.path, 10485760)  # 10MB limit
        
        # IMPORTANT: The file content IS the serialized_dashboard string
        dashboard_json = {
            'serialized_dashboard': file_content
        }
        
        # Extract dashboard ID and name from filename
        # Format: dashboard_{id}_{name}.lvdash.json or dashboard_{id}_{name}_transformed.json
        filename = file_info.name
        filename_clean = filename.replace('.lvdash.json', '').replace('_transformed.json', '').replace('.json', '')
        
        parts = filename_clean.split('_', 2)
        
        if len(parts) >= 3:
            dashboard_id = parts[1]
            dashboard_name = parts[2]
        else:
            # Fallback: parse JSON to get display_name (only if filename parsing fails)
            try:
                parsed = json.loads(file_content)
                dashboard_id = parsed.get('dashboard_id', 'unknown')
                dashboard_name = parsed.get('display_name', 'unknown')
            except:
                dashboard_id = 'unknown'
                dashboard_name = filename_clean
        
        # Build package
        package = DashboardDeploymentPackage(
            dashboard_id=dashboard_id,
            dashboard_name=dashboard_name,
            dashboard_json=dashboard_json,  # Now has 'serialized_dashboard' key
            source_path=file_info.path
        )
        
        # Add permissions if available
        if permissions_map and dashboard_id in permissions_map:
            perms_data = permissions_map[dashboard_id]
            
            # Handle both formats: 'permissions' (from CSV) and 'access_control_list' (from JSON)
            if 'permissions' in perms_data:
                # CSV format with 'permissions' list
                for perm in perms_data.get('permissions', []):
                    package.permissions.append(PermissionDefinition(
                        principal=perm['principal'],
                        principal_type=perm['principal_type'],
                        level=perm['level']
                    ))
            elif 'access_control_list' in perms_data:
                # JSON format with 'access_control_list'
                for acl in perms_data.get('access_control_list', []):
                    # Extract principal
                    principal = acl.get('user_name') or acl.get('group_name') or acl.get('service_principal_name', '')
                    
                    # Determine principal type
                    if acl.get('user_name'):
                        principal_type = 'user'
                    elif acl.get('group_name'):
                        principal_type = 'group'
                    elif acl.get('service_principal_name'):
                        principal_type = 'service_principal'
                    else:
                        continue
                    
                    # Get permission level (first one)
                    all_perms = acl.get('all_permissions', [])
                    if all_perms:
                        level = all_perms[0]  # Use first permission
                        package.permissions.append(PermissionDefinition(
                            principal=principal,
                            principal_type=principal_type,
                            level=level
                        ))
        
        # Add schedules if available
        if schedules_map and dashboard_id in schedules_map:
            scheds_data = schedules_map[dashboard_id]
            for sched in scheds_data.get('schedules', []):
                subs = []
                for sub in sched.get('subscriptions', []):
                    subscriber_data = sub.get('subscriber', {})
                    subs.append(SubscriptionDefinition(
                        user_id=subscriber_data.get('user_id'),
                        destination_id=subscriber_data.get('destination_id'),
                        subject=sub.get('subject')
                    ))
                
                cron_data = sched.get('cron_schedule', {})
                package.schedules.append(ScheduleDefinition(
                    display_name=sched.get('display_name', 'Migrated Schedule'),
                    quartz_cron_expression=cron_data.get('quartz_cron_expression', '0 0 8 * * ?'),
                    timezone_id=cron_data.get('timezone_id', 'UTC'),
                    pause_status=sched.get('pause_status', 'UNPAUSED'),
                    subscriptions=subs
                ))
        
        packages.append(package)
        
        # Show timing for first and last file (debugging)
        file_duration = time.time() - file_start
        if idx == 1 or idx == len(dashboard_files):
            print(f"      ⏱️  File processing time: {file_duration:.2f}s")
    
    print(f"   ✅ Built {len(packages)} packages successfully")
    return packages


def load_permissions_from_csv(export_path: str) -> Dict[str, Dict]:
    """
    Load permissions from consolidated CSV file.
    
    Args:
        export_path: Path to exported files in UC volume
    
    Returns:
        Dict mapping dashboard_id -> permissions data
    
    Raises:
        FileNotFoundError: If all_permissions.csv doesn't exist (run Step 3 first)
    """
    from .dbutils_helper import get_dbutils
    import time
    import pandas as pd
    import io
    
    dbutils = get_dbutils()
    permissions_map = {}
    
    start_time = time.time()
    csv_path = f"{export_path}/all_permissions.csv"
    
    print(f"      📄 Loading permissions CSV: {csv_path}")
    
    try:
        csv_content = dbutils.fs.head(csv_path, 100*1024*1024)  # 100MB limit
    except Exception as e:
        raise FileNotFoundError(
            f"all_permissions.csv not found at {csv_path}. "
            f"Run Step 3 (Export & Transform) first to generate CSV files. Error: {e}"
        )
    
    df = pd.read_csv(io.StringIO(csv_content))
    
    # Convert to dict structure matching expected format for build_deployment_packages
    for dashboard_id, group in df.groupby('dashboard_id'):
        permissions_list = []
        for _, row in group.iterrows():
            permissions_list.append({
                'principal': row['principal'],
                'principal_type': row['principal_type'],
                'level': row['permission_level']
            })
        
        permissions_map[dashboard_id] = {
            'dashboard_id': dashboard_id,
            'display_name': group.iloc[0]['dashboard_name'] if 'dashboard_name' in group.columns else dashboard_id,
            'permissions': permissions_list
        }
    
    duration = time.time() - start_time
    print(f"      ✅ Loaded {len(permissions_map)} permission sets ({duration:.2f}s)")
    
    return permissions_map


def load_schedules_from_csv(export_path: str) -> Dict[str, Dict]:
    """
    Load schedules from consolidated CSV file.
    
    Args:
        export_path: Path to exported files in UC volume
    
    Returns:
        Dict mapping dashboard_id -> schedules data
    
    Raises:
        FileNotFoundError: If all_schedules.csv doesn't exist (run Step 3 first)
    """
    from .dbutils_helper import get_dbutils
    import time
    import pandas as pd
    import io
    
    dbutils = get_dbutils()
    schedules_map = {}
    
    start_time = time.time()
    csv_path = f"{export_path}/all_schedules.csv"
    
    print(f"      📄 Loading schedules CSV: {csv_path}")
    
    try:
        csv_content = dbutils.fs.head(csv_path, 100*1024*1024)  # 100MB limit
    except Exception as e:
        raise FileNotFoundError(
            f"all_schedules.csv not found at {csv_path}. "
            f"Run Step 3 (Export & Transform) first to generate CSV files. Error: {e}"
        )
    
    df = pd.read_csv(io.StringIO(csv_content))
    
    # CSV columns: dashboard_id, schedule_id, cron_expression, timezone, paused, subscriptions_count, subscriptions_json
    for dashboard_id, group in df.groupby('dashboard_id'):
        schedules_list = []
        
        for _, row in group.iterrows():
            # Parse subscriptions from JSON string
            subscriptions = []
            subs_json = row.get('subscriptions_json', '[]')
            if pd.notna(subs_json) and subs_json != '[]':
                try:
                    subs_data = json.loads(subs_json) if isinstance(subs_json, str) else subs_json
                    for sub in subs_data:
                        subscriber = sub.get('subscriber', {})
                        subscriptions.append({
                            'subscriber': {
                                'user_id': subscriber.get('user_id'),
                                'destination_id': subscriber.get('destination_id')
                            },
                            'subject': sub.get('subject', 'Dashboard Update')
                        })
                except (json.JSONDecodeError, TypeError):
                    pass  # Skip malformed subscription JSON
            
            # Build schedule object
            schedule_id = row.get('schedule_id', '')
            cron_expr = row.get('cron_expression', '')
            timezone = row.get('timezone', 'UTC')
            paused = row.get('paused', False)
            
            # Only add if there's a valid cron expression
            if pd.notna(cron_expr) and cron_expr:
                schedules_list.append({
                    'display_name': f"Schedule_{schedule_id[:8]}" if schedule_id else 'Migrated Schedule',
                    'schedule_id': schedule_id,
                    'cron_schedule': {
                        'quartz_cron_expression': cron_expr,
                        'timezone_id': timezone
                    },
                    'pause_status': 'PAUSED' if paused else 'UNPAUSED',
                    'subscriptions': subscriptions
                })
        
        if schedules_list:
            schedules_map[dashboard_id] = {
                'dashboard_id': dashboard_id,
                'schedules': schedules_list
            }
    
    duration = time.time() - start_time
    print(f"      ✅ Loaded {len(schedules_map)} schedule sets ({duration:.2f}s)")
    
    return schedules_map
