"""
SDK-based direct deployment for dashboards with all metadata.

This module provides functions to deploy dashboards directly via Databricks SDK,
including permissions and schedules, without using asset bundles.
"""

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dashboards import (
    Dashboard, Schedule, CronSchedule, Subscription,
    Subscriber, SubscriptionSubscriberUser, SubscriptionSubscriberDestination
)
from databricks.sdk.service.iam import AccessControlRequest, PermissionLevel
from typing import Dict, List, Optional
from .deployment_package import DashboardDeploymentPackage, PermissionDefinition, ScheduleDefinition, SubscriptionDefinition


def deploy_via_sdk(
    client: WorkspaceClient,
    packages: List[DashboardDeploymentPackage],
    target_parent_path: str,
    warehouse_id: str = None,
    warehouse_name: str = None,
    apply_permissions: bool = True,
    apply_schedules: bool = True,
    embed_credentials: bool = True,
    skip_duplicate_check: bool = False,
    dry_run: bool = False
) -> Dict:
    """
    Deploy dashboards via SDK with all metadata (permissions, schedules).
    
    Args:
        client: Authenticated WorkspaceClient for target workspace
        packages: List of DashboardDeploymentPackage to deploy
        target_parent_path: Parent folder path in target workspace
        warehouse_id: Warehouse ID for dashboard execution (preferred)
        warehouse_name: Warehouse name for resolution (fallback if warehouse_id not provided)
        apply_permissions: Whether to apply permissions
        apply_schedules: Whether to apply schedules/subscriptions
        embed_credentials: Whether to embed credentials when publishing dashboards
        skip_duplicate_check: If True, skip checking for existing dashboards (faster but may error on duplicates)
        dry_run: If True, preview changes without creating resources
    
    Returns:
        Dict with deployment results and statistics
    """
    # DEBUG: Log entry parameters
    print(f"\n🔍 DEBUG deploy_via_sdk() Entry:")
    print(f"   dry_run parameter: {dry_run} (type: {type(dry_run)})")
    print(f"   packages count: {len(packages)}")
    print(f"   warehouse_id: {warehouse_id}")
    print(f"   apply_permissions: {apply_permissions}")
    print(f"   apply_schedules: {apply_schedules}")
    
    # CRITICAL: Verify client workspace
    print(f"\n🔍 CRITICAL - Verifying client workspace:")
    print(f"   Client is connected to: {client.config.host}")
    print(f"   Dashboards will be created in: {client.config.host} (NOT source!)")
    
    # Resolve warehouse ID if not provided directly
    if not warehouse_id:
        if not warehouse_name:
            raise ValueError("Either warehouse_id or warehouse_name must be provided")
        warehouse_id = resolve_warehouse(client, warehouse_name)
    
    # PERFORMANCE FIX: Cache existing dashboards (list once instead of 50 times!)
    existing_dashboards_cache = {}
    if not skip_duplicate_check:
        print(f"\n🚀 PERFORMANCE: Caching existing dashboards (list once for all packages)...")
        cache_start = __import__('time').time()
        try:
            dashboard_count = 0
            for dash in client.lakeview.list():
                dashboard_count += 1
                # Cache only dashboards in our target folder
                if dash.parent_path and dash.parent_path.startswith(target_parent_path):
                    existing_dashboards_cache[dash.display_name] = dash
                
                # Show progress every 200 dashboards
                if dashboard_count % 200 == 0:
                    print(f"   ... scanned {dashboard_count} dashboards, {len(existing_dashboards_cache)} in target folder")
            
            cache_duration = __import__('time').time() - cache_start
            print(f"   ✅ Cached {len(existing_dashboards_cache)} dashboards in target folder (scanned {dashboard_count} total)")
            print(f"   ⏱️  Time: {cache_duration:.2f}s (saved ~{len(packages) * cache_duration:.0f}s by caching!)")
        except Exception as e:
            print(f"   ⚠️  Could not cache dashboards: {e}")
            print(f"   Will skip duplicate checks for all packages")
            skip_duplicate_check = True
    
    results = []
    
    for package in packages:
        result = {
            'dashboard_name': package.dashboard_name,
            'dashboard_id': package.dashboard_id,
            'status': 'pending',
            'steps': {},
            'errors': []
        }
        
        try:
            # DEBUG: Show which path we're taking
            print(f"🔍 DEBUG Processing: {package.dashboard_name}")
            print(f"   dry_run={dry_run}, taking {'DRY RUN' if dry_run else 'LIVE'} path")
            
            if dry_run:
                result['status'] = 'dry_run'
                result['steps']['dashboard'] = 'Would create dashboard'
                result['steps']['permissions'] = len(package.permissions) if apply_permissions else 0
                result['steps']['schedules'] = len(package.schedules) if apply_schedules else 0
                result['steps']['subscriptions'] = sum(len(s.subscriptions) for s in package.schedules) if apply_schedules else 0
                print(f"   ✅ DRY RUN - Would create dashboard")
            else:
                # Step 1: Create dashboard
                dashboard_json = package.dashboard_json
                
                print(f"   🔧 LIVE MODE - Attempting to create dashboard")
                print(f"      Display name: {package.dashboard_name}")
                print(f"      Parent path: {target_parent_path}")
                print(f"      Warehouse ID: {warehouse_id}")
                print(f"      Has serialized_dashboard: {bool(dashboard_json.get('serialized_dashboard'))}")
                print(f"      Serialized dashboard length: {len(dashboard_json.get('serialized_dashboard', ''))}")
                
                # Check if dashboard with same name already exists (unless skipped for performance)
                existing_dashboard = None
                
                if skip_duplicate_check:
                    print(f"      ⚡ Skipping duplicate check (skip_duplicate_check=true)")
                    print(f"      ⚠️  If dashboard exists, creation will fail - errors will be caught")
                else:
                    # PERFORMANCE FIX: Use cached dashboards (instant lookup!)
                    print(f"      🚀 Checking cache for existing dashboard (instant)...")
                    existing_dashboard = existing_dashboards_cache.get(package.dashboard_name)
                    if existing_dashboard:
                        print(f"      ⚠️  Dashboard already exists in cache: {existing_dashboard.dashboard_id}")
                    else:
                        print(f"      ✅ No existing dashboard found in cache")
                
                if existing_dashboard:
                    # Dashboard exists - update it
                    print(f"      ♻️  Updating existing dashboard...")
                    try:
                        # Create Dashboard object with updated content
                        dashboard_obj = Dashboard(
                            display_name=package.dashboard_name,
                            parent_path=target_parent_path,
                            warehouse_id=warehouse_id,
                            serialized_dashboard=dashboard_json.get('serialized_dashboard', '')
                        )
                        
                        updated_dashboard = client.lakeview.update(
                            dashboard_id=existing_dashboard.dashboard_id,
                            dashboard=dashboard_obj
                        )
                        print(f"      ✅ Dashboard updated: {existing_dashboard.dashboard_id}")
                        new_dashboard_id = existing_dashboard.dashboard_id
                    except Exception as update_err:
                        print(f"      ❌ Update failed: {update_err}")
                        raise
                else:
                    # Create new dashboard
                    print(f"      🔍 DEBUG - Creating Dashboard object with:")
                    print(f"         display_name: '{package.dashboard_name}' (length: {len(package.dashboard_name)})")
                    print(f"         parent_path: '{target_parent_path}'")
                    print(f"         warehouse_id: '{warehouse_id}'")
                    print(f"         serialized_dashboard length: {len(dashboard_json.get('serialized_dashboard', ''))}")
                    
                    # Check if dashboard_name has file extension
                    if '.json' in package.dashboard_name or '.lvdash' in package.dashboard_name:
                        print(f"      ⚠️  WARNING: dashboard_name contains file extension!")
                        clean_name = package.dashboard_name.replace('.lvdash.json', '').replace('_transformed.json', '')
                        print(f"      🔧 Cleaning to: '{clean_name}'")
                    else:
                        clean_name = package.dashboard_name
                    
                    dashboard_obj = Dashboard(
                        display_name=clean_name,
                        parent_path=target_parent_path,
                        warehouse_id=warehouse_id,
                        serialized_dashboard=dashboard_json.get('serialized_dashboard', '')
                    )
                    
                    print(f"      Dashboard object created with display_name='{clean_name}', calling API...")
                    dashboard_created = False
                    new_dashboard_id = None
                    try:
                        created_dashboard = client.lakeview.create(dashboard=dashboard_obj)
                        print(f"      ✅ Dashboard created (DRAFT): {created_dashboard.dashboard_id}")
                        new_dashboard_id = created_dashboard.dashboard_id
                        dashboard_created = True
                    except Exception as create_err:
                        # If creation fails due to duplicate (when skip_duplicate_check=true)
                        if "already exists" in str(create_err).lower():
                            print(f"      ⚠️  Dashboard already exists - SKIPPED (no update performed)")
                            print(f"      📝 Note: Existing dashboard not modified")
                            print(f"      💡 Options:")
                            print(f"         1. Set skip_duplicate_check=false to update existing (slower)")
                            print(f"         2. Manually delete dashboards in {target_parent_path} first")
                            # Mark as skipped, don't fail the deployment
                            result['status'] = 'skipped'
                            result['errors'].append(f"Already exists - skipped")
                            dashboard_created = False
                            # Don't try to find existing - just move on
                        else:
                            raise
                
                # Only publish if dashboard was created/updated
                if dashboard_created:
                    # Publish dashboard to make it visible in UI
                    print(f"      📤 Publishing dashboard...")
                    print(f"         Dashboard ID: {new_dashboard_id}")
                    print(f"         embed_credentials: {embed_credentials}")
                    print(f"         warehouse_id: {warehouse_id}")
                    
                    try:
                        published = client.lakeview.publish(
                            dashboard_id=new_dashboard_id,
                            embed_credentials=embed_credentials,
                            warehouse_id=warehouse_id
                        )
                        print(f"      ✅ Publish API call completed")
                        print(f"         Response type: {type(published)}")
                        print(f"         Has revision_create_time: {hasattr(published, 'revision_create_time')}")
                        
                        # Verify dashboard is actually published
                        print(f"      🔍 Verifying published state...")
                        try:
                            pub_dashboard = client.lakeview.get_published(new_dashboard_id)
                            print(f"      ✅ Dashboard IS published! Display name: {pub_dashboard.display_name}")
                        except Exception as verify_err:
                            print(f"      ❌ Dashboard NOT published! Error: {verify_err}")
                            print(f"      ⚠️  Dashboard created but remains as DRAFT")
                            
                    except Exception as pub_err:
                        print(f"      ❌ Publish failed: {pub_err}")
                        print(f"      Dashboard created as DRAFT only - NOT visible in UI")
                        print(f"      Try manual publish: databricks lakeview publish {new_dashboard_id} --profile target-workspace")
                    
                    result['steps']['dashboard'] = new_dashboard_id
                    
                    # Step 2: Apply permissions
                    if apply_permissions and package.permissions:
                        try:
                            apply_permissions_sdk(client, new_dashboard_id, package.permissions)
                            result['steps']['permissions'] = len(package.permissions)
                        except Exception as perm_err:
                            result['errors'].append(f"Permissions error: {str(perm_err)}")
                            result['steps']['permissions'] = 0
                    
                    # Step 3: Apply schedules
                    if apply_schedules and package.schedules:
                        try:
                            scheds_created, subs_created = apply_schedules_sdk(
                                client, new_dashboard_id, package.schedules
                            )
                            result['steps']['schedules'] = scheds_created
                            result['steps']['subscriptions'] = subs_created
                        except Exception as sched_err:
                            result['errors'].append(f"Schedules error: {str(sched_err)}")
                            result['steps']['schedules'] = 0
                            result['steps']['subscriptions'] = 0
                    
                    result['status'] = 'success'
                # If dashboard was skipped, status is already set to 'skipped'
        
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(str(e))
        
        results.append(result)
    
    # Calculate summary statistics
    summary = {
        'total': len(packages),
        'successful': len([r for r in results if r['status'] == 'success']),
        'failed': len([r for r in results if r['status'] == 'error']),
        'skipped': len([r for r in results if r['status'] == 'skipped']),
        'dry_run': dry_run,
        'results': results
    }
    
    return summary


def apply_permissions_sdk(
    client: WorkspaceClient,
    dashboard_id: str,
    permissions: List[PermissionDefinition]
):
    """
    Apply permissions to a dashboard using SDK.
    
    Args:
        client: WorkspaceClient for target workspace
        dashboard_id: ID of the dashboard
        permissions: List of PermissionDefinition objects
    """
    acl_list = []
    
    for perm in permissions:
        acr = AccessControlRequest()
        
        if perm.principal_type == "user":
            acr.user_name = perm.principal
        elif perm.principal_type == "group":
            acr.group_name = perm.principal
        elif perm.principal_type == "service_principal":
            acr.service_principal_name = perm.principal
        
        # Map permission level
        if perm.level == "CAN_VIEW":
            acr.permission_level = PermissionLevel.CAN_VIEW
        elif perm.level == "CAN_RUN":
            acr.permission_level = PermissionLevel.CAN_RUN
        elif perm.level == "CAN_MANAGE":
            acr.permission_level = PermissionLevel.CAN_MANAGE
        else:
            acr.permission_level = PermissionLevel.CAN_VIEW  # Default fallback
        
        acl_list.append(acr)
    
    # Update permissions
    client.permissions.update(
        request_object_type="dashboards",
        request_object_id=dashboard_id,
        access_control_list=acl_list
    )


def apply_schedules_sdk(
    client: WorkspaceClient,
    dashboard_id: str,
    schedules: List[ScheduleDefinition]
) -> tuple:
    """
    Apply schedules and subscriptions to a dashboard using SDK.
    
    Args:
        client: WorkspaceClient for target workspace
        dashboard_id: ID of the dashboard
        schedules: List of ScheduleDefinition objects
    
    Returns:
        Tuple of (schedules_created, subscriptions_created)
    """
    schedules_created = 0
    subscriptions_created = 0
    
    for schedule_def in schedules:
        # Create schedule
        schedule = client.lakeview.create_schedule(
            dashboard_id=dashboard_id,
            schedule=Schedule(
                display_name=schedule_def.display_name,
                cron_schedule=CronSchedule(
                    quartz_cron_expression=schedule_def.quartz_cron_expression,
                    timezone_id=schedule_def.timezone_id
                ),
                pause_status=schedule_def.pause_status
            )
        )
        schedules_created += 1
        
        # Create subscriptions for this schedule
        for sub_def in schedule_def.subscriptions:
            try:
                # Build subscription based on subscriber type
                subscriber = None
                if sub_def.user_id:
                    subscriber = Subscriber(
                        user_subscriber=SubscriptionSubscriberUser(
                            user_id=sub_def.user_id
                        )
                    )
                elif sub_def.destination_id:
                    subscriber = Subscriber(
                        destination_subscriber=SubscriptionSubscriberDestination(
                            destination_id=sub_def.destination_id
                        )
                    )
                
                if subscriber:
                    client.lakeview.create_subscription(
                        dashboard_id=dashboard_id,
                        schedule_id=schedule.schedule_id,
                        subscription=Subscription(
                            subscriber=subscriber
                        )
                    )
                    subscriptions_created += 1
                else:
                    print(f"⚠️  Skipping subscription - no user_id or destination_id provided")
            
            except Exception as sub_err:
                print(f"⚠️  Warning: Failed to create subscription: {sub_err}")
    
    return schedules_created, subscriptions_created


def resolve_warehouse(client: WorkspaceClient, warehouse_name: str) -> str:
    """
    Resolve warehouse name to warehouse ID.
    
    Args:
        client: WorkspaceClient
        warehouse_name: Name of the warehouse
    
    Returns:
        Warehouse ID
    
    Raises:
        ValueError: If warehouse not found
    """
    for wh in client.warehouses.list():
        if wh.name == warehouse_name:
            return wh.id
    
    raise ValueError(f"Warehouse not found: {warehouse_name}")
