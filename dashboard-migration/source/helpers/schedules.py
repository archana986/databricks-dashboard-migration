"""
Schedule and subscription management for dashboard migration.
"""

from .dbutils_helper import get_dbutils as _get_dbutils
from databricks.sdk import WorkspaceClient
from typing import Dict, List
import json


def get_dashboard_schedules(client: WorkspaceClient, dashboard_id: str) -> Dict:
    """
    Get dashboard schedules and their subscriptions from source workspace.
    
    Args:
        client: Workspace client
        dashboard_id: Dashboard ID
    
    Returns:
        Dictionary with dashboard_id and list of schedules with subscriptions
    """
    try:
        schedules_list = []
        
        # List all schedules for this dashboard
        schedules = client.lakeview.list_schedules(dashboard_id=dashboard_id)
        
        for schedule in schedules:
            schedule_data = {
                'schedule_id': schedule.schedule_id,
                'display_name': schedule.display_name,
                'pause_status': str(schedule.pause_status) if schedule.pause_status else None,
                'cron_schedule': {}
            }
            
            # Extract cron schedule details
            if schedule.cron_schedule:
                schedule_data['cron_schedule'] = {
                    'quartz_cron_expression': schedule.cron_schedule.quartz_cron_expression,
                    'timezone_id': schedule.cron_schedule.timezone_id
                }
            
            # Get subscriptions for this schedule
            subscriptions_list = []
            try:
                subscriptions = client.lakeview.list_subscriptions(
                    dashboard_id=dashboard_id,
                    schedule_id=schedule.schedule_id
                )
                
                for sub in subscriptions:
                    sub_data = {
                        'subscription_id': sub.subscription_id,
                        'subscriber': {}
                    }
                    
                    # Extract subscriber details
                    if sub.subscriber:
                        if sub.subscriber.user_subscriber:
                            sub_data['subscriber']['user_id'] = sub.subscriber.user_subscriber.user_id
                        elif sub.subscriber.destination_subscriber:
                            sub_data['subscriber']['destination_id'] = sub.subscriber.destination_subscriber.destination_id
                    
                    subscriptions_list.append(sub_data)
                    
            except Exception as e:
                print(f"    Warning: Could not retrieve subscriptions for schedule {schedule.schedule_id}: {e}")
            
            schedule_data['subscriptions'] = subscriptions_list
            schedules_list.append(schedule_data)
        
        return {
            'dashboard_id': dashboard_id,
            'schedules': schedules_list
        }
        
    except Exception as e:
        print(f"Could not retrieve schedules: {e}")
        return {
            'dashboard_id': dashboard_id,
            'schedules': []
        }


def apply_dashboard_schedules(
    client: WorkspaceClient,
    dashboard_id: str,
    schedules_data: Dict,
    dry_run: bool = True
) -> Dict:
    """
    Apply schedules and subscriptions to a dashboard in target workspace.
    
    Args:
        client: Workspace client
        dashboard_id: Dashboard ID in target workspace
        schedules_data: Schedules dictionary from get_dashboard_schedules
        dry_run: If True, only preview without applying
    
    Returns:
        Dictionary with status and details
    """
    schedules_list = schedules_data.get('schedules', [])
    
    if not schedules_list:
        return {'status': 'skipped', 'reason': 'No schedules to apply'}
    
    if dry_run:
        total_subs = sum(len(s.get('subscriptions', [])) for s in schedules_list)
        return {
            'status': 'dry_run',
            'would_create_schedules': len(schedules_list),
            'would_create_subscriptions': total_subs,
            'schedules': schedules_list
        }
    
    try:
        from databricks.sdk.service.dashboards import (
            Schedule,
            CronSchedule,
            Subscription,
            Subscriber,
            SubscriptionSubscriberUser,
            SubscriptionSubscriberDestination
        )
        
        schedules_created = 0
        subscriptions_created = 0
        errors = []
        
        for schedule_data in schedules_list:
            try:
                # Create CronSchedule object
                cron_schedule = None
                if schedule_data.get('cron_schedule'):
                    cron_data = schedule_data['cron_schedule']
                    if cron_data.get('quartz_cron_expression'):
                        cron_schedule = CronSchedule(
                            quartz_cron_expression=cron_data['quartz_cron_expression'],
                            timezone_id=cron_data.get('timezone_id', 'UTC')
                        )
                
                if not cron_schedule:
                    errors.append({
                        'schedule': schedule_data.get('display_name', 'unknown'),
                        'error': 'No valid cron expression'
                    })
                    continue
                
                # Create Schedule object
                schedule = Schedule(
                    display_name=schedule_data.get('display_name', 'Migrated Schedule'),
                    cron_schedule=cron_schedule,
                    pause_status=schedule_data.get('pause_status', 'UNPAUSED')
                )
                
                # Create schedule in target workspace
                created_schedule = client.lakeview.create_schedule(
                    dashboard_id=dashboard_id,
                    schedule=schedule
                )
                
                schedules_created += 1
                new_schedule_id = created_schedule.schedule_id
                
                # Create subscriptions for this schedule
                subscriptions = schedule_data.get('subscriptions', [])
                for sub_data in subscriptions:
                    try:
                        subscriber_data = sub_data.get('subscriber', {})
                        
                        # Create subscriber object
                        subscriber = None
                        if subscriber_data.get('user_id'):
                            subscriber = Subscriber(
                                user_subscriber=SubscriptionSubscriberUser(
                                    user_id=int(subscriber_data['user_id'])
                                )
                            )
                        elif subscriber_data.get('destination_id'):
                            subscriber = Subscriber(
                                destination_subscriber=SubscriptionSubscriberDestination(
                                    destination_id=subscriber_data['destination_id']
                                )
                            )
                        
                        if subscriber:
                            # Create subscription
                            client.lakeview.create_subscription(
                                dashboard_id=dashboard_id,
                                schedule_id=new_schedule_id,
                                subscription=Subscription(
                                    subscriber=subscriber
                                )
                            )
                            subscriptions_created += 1
                        else:
                            errors.append({
                                'schedule': schedule_data.get('display_name'),
                                'subscription': 'unknown',
                                'error': 'No valid subscriber information (user_id or destination_id required)'
                            })
                            
                    except Exception as e:
                        errors.append({
                            'schedule': schedule_data.get('display_name'),
                            'subscription': sub_data.get('subscription_id', 'unknown'),
                            'error': str(e)
                        })
                
            except Exception as e:
                errors.append({
                    'schedule': schedule_data.get('display_name', 'unknown'),
                    'error': str(e)
                })
        
        return {
            'status': 'success' if schedules_created > 0 else 'failed',
            'schedules_created': schedules_created,
            'subscriptions_created': subscriptions_created,
            'errors': errors
        }
        
    except Exception as e:
        return {
            'status': 'failed',
            'error': str(e),
            'schedules_created': 0,
            'subscriptions_created': 0
        }


def load_schedules_from_volume(export_path: str) -> Dict[str, Dict]:
    """
    Load all schedule JSON files from volume.
    
    Args:
        export_path: Path to exported files directory
    
    Returns:
        Dictionary mapping dashboard_id/name to schedules data
    """
    schedules_map = {}
    
    try:
        files = _get_dbutils().fs.ls(export_path)
        schedule_files = [f for f in files if '_schedules.json' in f.path]
        
        for sched_file in schedule_files:
            content = _get_dbutils().fs.head(sched_file.path, 10485760)
            sched_data = json.loads(content)
            
            dashboard_id = sched_data.get('dashboard_id')
            dashboard_name = sched_data.get('display_name')
            
            # Store by both ID and name for flexible matching
            if dashboard_id:
                schedules_map[dashboard_id] = sched_data
            if dashboard_name:
                schedules_map[dashboard_name] = sched_data
        
        return schedules_map
    except Exception as e:
        print(f"Error loading schedules: {e}")
        return {}
