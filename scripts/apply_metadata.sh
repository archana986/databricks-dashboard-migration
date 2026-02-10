#!/usr/bin/env bash

################################################################################
# Apply Permissions and Schedules to Deployed Dashboards
################################################################################
#
# This script applies permissions and schedules to dashboards that were
# deployed via Asset Bundle. Asset Bundles don't support schedules, and
# permissions may need post-deployment application.
#
# Prerequisites:
#   - Databricks CLI v0.218.0+ installed
#   - CLI profiles configured for source and target workspaces
#   - Dashboards already deployed to target workspace
#   - Permissions and schedules CSVs exist in UC Volume
#
# Usage:
#   ./apply_metadata.sh [options]
#
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default configuration
SOURCE_PROFILE="${SOURCE_PROFILE:-source-workspace}"
TARGET_PROFILE="${TARGET_PROFILE:-target-workspace}"
VOLUME_BASE="${VOLUME_BASE:-/Volumes/YOUR_CATALOG/YOUR_SCHEMA/dashboard_migration}"
TARGET_PARENT_PATH="${TARGET_PARENT_PATH:-/Shared/Migrated_Dashboards_V2}"
APPLY_PERMISSIONS="${APPLY_PERMISSIONS:-true}"
APPLY_SCHEDULES="${APPLY_SCHEDULES:-true}"
DRY_RUN="${DRY_RUN:-false}"

log_info() { echo -e "${BLUE}ℹ ${NC} $1"; }
log_success() { echo -e "${GREEN}✅${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠️ ${NC} $1"; }
log_error() { echo -e "${RED}❌${NC} $1"; }

show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Applies permissions and schedules to deployed dashboards."
    echo ""
    echo "Options:"
    echo "  --source-profile PROFILE   Source workspace CLI profile (default: source-workspace)"
    echo "  --target-profile PROFILE   Target workspace CLI profile (default: target-workspace)"
    echo "  --volume-base PATH         UC Volume base path (required)"
    echo "  --target-path PATH         Target dashboard parent path (default: /Shared/Migrated_Dashboards_V2)"
    echo "  --apply-permissions        Apply permissions (default: true)"
    echo "  --apply-schedules          Apply schedules (default: true)"
    echo "  --skip-permissions         Skip permissions application"
    echo "  --skip-schedules           Skip schedules application"
    echo "  --dry-run                  Show what would be applied without actually applying"
    echo "  -h, --help                 Show this help"
    echo ""
    echo "Example:"
    echo "  $0 --source-profile source-workspace \\"
    echo "     --target-profile target-workspace \\"
    echo "     --volume-base /Volumes/my_catalog/my_schema/dashboard_migration"
    echo ""
}

################################################################################
# Parse Arguments
################################################################################

while [[ $# -gt 0 ]]; do
    case $1 in
        --source-profile)
            SOURCE_PROFILE="$2"
            shift 2
            ;;
        --target-profile)
            TARGET_PROFILE="$2"
            shift 2
            ;;
        --volume-base)
            VOLUME_BASE="$2"
            shift 2
            ;;
        --target-path)
            TARGET_PARENT_PATH="$2"
            shift 2
            ;;
        --apply-permissions)
            APPLY_PERMISSIONS=true
            shift
            ;;
        --apply-schedules)
            APPLY_SCHEDULES=true
            shift
            ;;
        --skip-permissions)
            APPLY_PERMISSIONS=false
            shift
            ;;
        --skip-schedules)
            APPLY_SCHEDULES=false
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

################################################################################
# Validate Configuration
################################################################################

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Apply Permissions & Schedules to Deployed Dashboards        ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check for placeholder values
if [[ "$VOLUME_BASE" == *"YOUR_CATALOG"* ]] || [[ "$VOLUME_BASE" == *"YOUR_SCHEMA"* ]]; then
    log_error "Please provide --volume-base with your actual volume path"
    echo ""
    echo "Example:"
    echo "  $0 --volume-base /Volumes/my_catalog/my_schema/dashboard_migration"
    echo ""
    exit 1
fi

log_info "Configuration:"
echo "   • Source Profile: ${SOURCE_PROFILE}"
echo "   • Target Profile: ${TARGET_PROFILE}"
echo "   • Volume Base: ${VOLUME_BASE}"
echo "   • Target Path: ${TARGET_PARENT_PATH}"
echo "   • Apply Permissions: ${APPLY_PERMISSIONS}"
echo "   • Apply Schedules: ${APPLY_SCHEDULES}"
echo "   • Dry Run: ${DRY_RUN}"
echo ""

################################################################################
# Step 1: Verify Prerequisites
################################################################################

log_info "Step 1: Verifying prerequisites..."
echo ""

# Check CLI version
CLI_VERSION=$(databricks --version 2>/dev/null || echo "not found")
if [[ "$CLI_VERSION" == "not found" ]]; then
    log_error "Databricks CLI not found. Install with: pip install databricks-cli"
    exit 1
fi
log_success "CLI version: $CLI_VERSION"

# Test source profile
if ! databricks workspace list / --profile "$SOURCE_PROFILE" >/dev/null 2>&1; then
    log_error "Cannot access source workspace with profile: ${SOURCE_PROFILE}"
    exit 1
fi
log_success "Source profile verified: ${SOURCE_PROFILE}"

# Test target profile
if ! databricks workspace list / --profile "$TARGET_PROFILE" >/dev/null 2>&1; then
    log_error "Cannot access target workspace with profile: ${TARGET_PROFILE}"
    exit 1
fi
log_success "Target profile verified: ${TARGET_PROFILE}"
echo ""

################################################################################
# Step 2: Download Permissions and Schedules CSVs
################################################################################

log_info "Step 2: Downloading permissions and schedules metadata..."
echo ""

TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Always download permissions CSV if either permissions or schedules are being applied
# (schedules need it for dashboard name mapping)
if [ "$APPLY_PERMISSIONS" = "true" ] || [ "$APPLY_SCHEDULES" = "true" ]; then
    PERMISSIONS_CSV_PATH="dbfs:${VOLUME_BASE}/exported/all_permissions.csv"
    log_info "Downloading permissions: ${PERMISSIONS_CSV_PATH}"
    
    if ! databricks fs cp "${PERMISSIONS_CSV_PATH}" "${TEMP_DIR}/all_permissions.csv" --profile "$SOURCE_PROFILE" --overwrite 2>&1; then
        log_error "Failed to download permissions CSV"
        if [ "$APPLY_PERMISSIONS" = "true" ]; then
            log_warning "Skipping permissions application"
            APPLY_PERMISSIONS=false
        fi
        # Note: Schedules may still work if they have dashboard_name in the CSV
    else
        PERM_COUNT=$(tail -n +2 "${TEMP_DIR}/all_permissions.csv" | wc -l | tr -d ' ')
        log_success "Downloaded permissions (${PERM_COUNT} entries)"
    fi
fi

if [ "$APPLY_SCHEDULES" = "true" ]; then
    SCHEDULES_CSV_PATH="dbfs:${VOLUME_BASE}/exported/all_schedules.csv"
    log_info "Downloading schedules: ${SCHEDULES_CSV_PATH}"
    
    if ! databricks fs cp "${SCHEDULES_CSV_PATH}" "${TEMP_DIR}/all_schedules.csv" --profile "$SOURCE_PROFILE" --overwrite 2>&1; then
        log_error "Failed to download schedules CSV"
        log_warning "Skipping schedules application"
        APPLY_SCHEDULES=false
    else
        SCHED_COUNT=$(tail -n +2 "${TEMP_DIR}/all_schedules.csv" | wc -l | tr -d ' ')
        log_success "Downloaded schedules (${SCHED_COUNT} entries)"
    fi
fi

echo ""

################################################################################
# Step 3: Generate Python Script to Apply Metadata
################################################################################

log_info "Step 3: Generating metadata application script..."
echo ""

# Create Python script
cat > "${TEMP_DIR}/apply_metadata.py" << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""
Apply permissions and schedules to deployed dashboards.
"""
import sys
import json
import csv
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dashboards import (
    Schedule, CronSchedule, Subscription, SchedulePauseStatus,
    Subscriber, SubscriptionSubscriberUser
)
from databricks.sdk.service.iam import AccessControlRequest, PermissionLevel

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--target-profile', required=True)
    parser.add_argument('--target-path', required=True)
    parser.add_argument('--permissions-csv', required=False)
    parser.add_argument('--schedules-csv', required=False)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    
    # Initialize target workspace client
    target_client = WorkspaceClient(profile=args.target_profile)
    
    # Get deployed dashboards
    print(f"\n📋 Finding deployed dashboards in {args.target_path}...")
    deployed_dashboards = {}
    for dash in target_client.lakeview.list():
        # Get full dashboard details to check parent_path (list() doesn't include it)
        try:
            full_dash = target_client.lakeview.get(dash.dashboard_id)
            if full_dash.parent_path and full_dash.parent_path.startswith(args.target_path):
                deployed_dashboards[dash.display_name] = dash.dashboard_id
        except Exception as e:
            # Skip dashboards we can't access
            pass
    
    print(f"   Found {len(deployed_dashboards)} dashboard(s)")
    
    def normalize_name(name):
        """Normalize dashboard names by replacing underscores with spaces."""
        return name.replace('_', ' ')
    
    # Build mapping from old dashboard IDs to normalized names (from permissions CSV)
    old_id_to_name = {}
    if args.permissions_csv:
        with open(args.permissions_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_id = row['dashboard_id']
                dash_name = normalize_name(row['dashboard_name'])
                old_id_to_name[old_id] = dash_name
    
    # Apply permissions
    if args.permissions_csv:
        print(f"\n🔐 Applying permissions...")
        perms_applied = 0
        
        with open(args.permissions_csv, 'r') as f:
            reader = csv.DictReader(f)
            dashboard_perms = {}
            
            for row in reader:
                dash_name = normalize_name(row['dashboard_name'])
                if dash_name not in dashboard_perms:
                    dashboard_perms[dash_name] = []
                
                principal_type = row['principal_type']
                principal = row['principal']
                level = row['permission_level'].upper()
                
                # Skip admin group - cannot be modified via API
                if principal_type == 'group' and principal.lower() == 'admins':
                    continue
                
                # Map permission level for Lakeview dashboards
                # Valid levels: CAN_EDIT, CAN_MANAGE, CAN_READ, CAN_RUN
                if 'MANAGE' in level:
                    perm_level = PermissionLevel.CAN_MANAGE
                elif 'RUN' in level:
                    perm_level = PermissionLevel.CAN_RUN
                elif 'EDIT' in level:
                    perm_level = PermissionLevel.CAN_EDIT
                elif 'READ' in level or 'VIEW' in level:
                    perm_level = PermissionLevel.CAN_READ
                else:
                    # Unknown level, skip
                    print(f"   ⚠️  Skipping unknown permission level '{level}' for {principal}")
                    continue
                
                dashboard_perms[dash_name].append({
                    'principal_type': principal_type,
                    'principal': principal,
                    'level': perm_level
                })
        
        for dash_name, perms in dashboard_perms.items():
            if dash_name in deployed_dashboards:
                dashboard_id = deployed_dashboards[dash_name]
                
                # Check existing permissions
                new_perms_count = 0
                try:
                    existing_perms = target_client.permissions.get("dashboards", dashboard_id)
                    existing_principals = set()
                    if hasattr(existing_perms, 'access_control_list') and existing_perms.access_control_list:
                        for acl in existing_perms.access_control_list:
                            if hasattr(acl, 'user_name') and acl.user_name:
                                existing_principals.add(('user', acl.user_name))
                            elif hasattr(acl, 'group_name') and acl.group_name:
                                existing_principals.add(('group', acl.group_name))
                            elif hasattr(acl, 'service_principal_name') and acl.service_principal_name:
                                existing_principals.add(('service_principal', acl.service_principal_name))
                    
                    # Count only new permissions
                    for p in perms:
                        if (p['principal_type'], p['principal']) not in existing_principals:
                            new_perms_count += 1
                    
                    if new_perms_count == 0:
                        print(f"   ⏭️  Permissions already set for: {dash_name}")
                        continue
                except Exception:
                    new_perms_count = len(perms)  # If can't read existing, treat all as new
                
                if args.dry_run:
                    print(f"   [DRY RUN] Would apply {new_perms_count} new permission(s) to: {dash_name}")
                else:
                    acrs = []
                    for perm in perms:
                        acr = AccessControlRequest(permission_level=perm['level'])
                        if perm['principal_type'] == 'user':
                            acr.user_name = perm['principal']
                        elif perm['principal_type'] == 'group':
                            acr.group_name = perm['principal']
                        elif perm['principal_type'] == 'service_principal':
                            acr.service_principal_name = perm['principal']
                        acrs.append(acr)
                    
                    try:
                        target_client.permissions.update("dashboards", dashboard_id, access_control_list=acrs)
                        perms_applied += new_perms_count
                        print(f"   ✅ Applied {new_perms_count} new permission(s) to: {dash_name}")
                    except Exception as e:
                        print(f"   ❌ Failed to apply permissions to {dash_name}: {e}")
        
        print(f"\n✅ Total permissions applied: {perms_applied}")
    
    # Apply schedules
    if args.schedules_csv:
        print(f"\n📅 Applying schedules...")
        scheds_applied = 0
        subs_applied = 0
        
        with open(args.schedules_csv, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                dash_id_from_csv = row['dashboard_id']
                
                # Get dashboard name - from CSV or from mapping
                if 'dashboard_name' in row and row['dashboard_name']:
                    dash_name = normalize_name(row['dashboard_name'])
                elif dash_id_from_csv in old_id_to_name:
                    dash_name = old_id_to_name[dash_id_from_csv]
                else:
                    # No name available, skip
                    continue
                
                if dash_name not in deployed_dashboards:
                    continue
                
                new_dashboard_id = deployed_dashboards[dash_name]
                
                # Parse schedule data
                cron_expr = row.get('cron_expression', '').strip()
                timezone = row.get('timezone', 'UTC').strip()
                paused = row.get('paused', 'False').strip().lower() == 'true'
                subscriptions_json = row.get('subscriptions_json', '[]').strip()
                
                if not cron_expr:
                    # Skip schedules without cron expression
                    continue
                
                # Check if schedule already exists
                existing_schedule = None
                try:
                    schedules_list = list(target_client.lakeview.list_schedules(dashboard_id=new_dashboard_id))
                    if schedules_list:
                        existing_schedule = schedules_list[0]
                        print(f"   ⏭️  Schedule already exists for: {dash_name}")
                except Exception:
                    pass
                
                if args.dry_run:
                    if existing_schedule:
                        print(f"   [DRY RUN] Schedule exists, would check subscriptions for: {dash_name}")
                    else:
                        print(f"   [DRY RUN] Would create schedule for: {dash_name}")
                else:
                    if not existing_schedule:
                        try:
                            # Create schedule
                            pause_status_enum = SchedulePauseStatus.PAUSED if paused else SchedulePauseStatus.UNPAUSED
                            
                            schedule = target_client.lakeview.create_schedule(
                                dashboard_id=new_dashboard_id,
                                schedule=Schedule(
                                    display_name=f"{dash_name} Schedule",
                                    cron_schedule=CronSchedule(
                                        quartz_cron_expression=cron_expr,
                                        timezone_id=timezone
                                    ),
                                    pause_status=pause_status_enum
                                )
                            )
                            
                            scheds_applied += 1
                            print(f"   ✅ Created schedule for: {dash_name}")
                            existing_schedule = schedule
                        except Exception as e:
                            print(f"   ❌ Failed to create schedule for {dash_name}: {e}")
                            continue
                    
                    # Handle subscriptions (for both new and existing schedules)
                    if existing_schedule and subscriptions_json and subscriptions_json != '[]':
                        try:
                            # Get existing subscriptions
                            existing_subs = list(target_client.lakeview.list_subscriptions(
                                dashboard_id=new_dashboard_id,
                                schedule_id=existing_schedule.schedule_id
                            ))
                            existing_user_ids = {s.subscriber.user_subscriber.user_id 
                                               for s in existing_subs 
                                               if s.subscriber and s.subscriber.user_subscriber}
                            
                            # Add missing subscriptions
                            subs_list = json.loads(subscriptions_json)
                            for sub in subs_list:
                                user_id = sub.get('subscriber', {}).get('user_id')
                                if user_id and user_id not in existing_user_ids:
                                    target_client.lakeview.create_subscription(
                                        dashboard_id=new_dashboard_id,
                                        schedule_id=existing_schedule.schedule_id,
                                        subscription=Subscription(
                                            subscriber=Subscriber(
                                                user_subscriber=SubscriptionSubscriberUser(user_id=user_id)
                                            )
                                        )
                                    )
                                    subs_applied += 1
                        except (json.JSONDecodeError, Exception) as e:
                            pass
        
        print(f"\n✅ Total schedules created: {scheds_applied}")
        print(f"✅ Total subscriptions created: {subs_applied}")
    
    print("\n" + "="*80)
    print("METADATA APPLICATION COMPLETE")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
PYTHON_SCRIPT

log_success "Script generated"
echo ""

################################################################################
# Step 4: Execute Metadata Application
################################################################################

log_info "Step 4: Applying metadata to deployed dashboards..."
echo ""

PYTHON_ARGS="--target-profile $TARGET_PROFILE --target-path $TARGET_PARENT_PATH"

# Always pass permissions CSV if it exists (needed for schedule name mapping)
if [ -f "${TEMP_DIR}/all_permissions.csv" ]; then
    PYTHON_ARGS="$PYTHON_ARGS --permissions-csv ${TEMP_DIR}/all_permissions.csv"
fi

if [ "$APPLY_SCHEDULES" = "true" ]; then
    PYTHON_ARGS="$PYTHON_ARGS --schedules-csv ${TEMP_DIR}/all_schedules.csv"
fi

if [ "$DRY_RUN" = "true" ]; then
    PYTHON_ARGS="$PYTHON_ARGS --dry-run"
fi

python3 "${TEMP_DIR}/apply_metadata.py" $PYTHON_ARGS

################################################################################
# Summary
################################################################################

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║            METADATA APPLICATION COMPLETE                      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

if [ "$DRY_RUN" = "true" ]; then
    log_info "Dry run completed. No changes were made."
else
    log_success "Permissions and schedules applied to deployed dashboards!"
    echo ""
    echo "Next steps:"
    echo "   1. Verify dashboards in target workspace UI"
    echo "   2. Check permissions (click Share button on each dashboard)"
    echo "   3. Check schedules (click Schedule button on each dashboard)"
fi
echo ""
