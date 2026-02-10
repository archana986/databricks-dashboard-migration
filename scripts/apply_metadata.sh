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

if [ "$APPLY_PERMISSIONS" = "true" ]; then
    PERMISSIONS_CSV_PATH="dbfs:${VOLUME_BASE}/exported/all_permissions.csv"
    log_info "Downloading permissions: ${PERMISSIONS_CSV_PATH}"
    
    if ! databricks fs cp "${PERMISSIONS_CSV_PATH}" "${TEMP_DIR}/all_permissions.csv" --profile "$SOURCE_PROFILE" --overwrite 2>&1; then
        log_error "Failed to download permissions CSV"
        log_warning "Skipping permissions application"
        APPLY_PERMISSIONS=false
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
from databricks.sdk.service.dashboards import Schedule, CronSchedule, Subscription
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
        if dash.parent_path and dash.parent_path.startswith(args.target_path):
            deployed_dashboards[dash.display_name] = dash.dashboard_id
    
    print(f"   Found {len(deployed_dashboards)} dashboard(s)")
    
    # Apply permissions
    if args.permissions_csv:
        print(f"\n🔐 Applying permissions...")
        perms_applied = 0
        
        with open(args.permissions_csv, 'r') as f:
            reader = csv.DictReader(f)
            dashboard_perms = {}
            
            for row in reader:
                dash_name = row['dashboard_name']
                if dash_name not in dashboard_perms:
                    dashboard_perms[dash_name] = []
                
                principal_type = row['principal_type']
                principal = row['principal']
                level = row['permission_level']
                
                # Map permission level
                if 'MANAGE' in level.upper():
                    perm_level = PermissionLevel.CAN_MANAGE
                elif 'RUN' in level.upper():
                    perm_level = PermissionLevel.CAN_RUN
                elif 'EDIT' in level.upper():
                    perm_level = PermissionLevel.CAN_EDIT
                else:
                    perm_level = PermissionLevel.CAN_VIEW
                
                dashboard_perms[dash_name].append({
                    'principal_type': principal_type,
                    'principal': principal,
                    'level': perm_level
                })
        
        for dash_name, perms in dashboard_perms.items():
            if dash_name in deployed_dashboards:
                dashboard_id = deployed_dashboards[dash_name]
                
                if args.dry_run:
                    print(f"   [DRY RUN] Would apply {len(perms)} permission(s) to: {dash_name}")
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
                        perms_applied += len(perms)
                        print(f"   ✅ Applied {len(perms)} permission(s) to: {dash_name}")
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
                dash_name = row['dashboard_name'] if 'dashboard_name' in row else None
                dash_id_from_csv = row['dashboard_id']
                
                # Find dashboard name from ID if not in CSV
                if not dash_name:
                    # Map old ID to new name (best effort)
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
                
                if args.dry_run:
                    print(f"   [DRY RUN] Would create schedule for: {dash_name}")
                else:
                    try:
                        # Create schedule
                        schedule = target_client.lakeview.create_schedule(
                            dashboard_id=new_dashboard_id,
                            schedule=Schedule(
                                display_name=f"{dash_name} Schedule",
                                cron_schedule=CronSchedule(
                                    quartz_cron_expression=cron_expr,
                                    timezone_id=timezone
                                ),
                                pause_status="PAUSED" if paused else "UNPAUSED"
                            )
                        )
                        
                        scheds_applied += 1
                        print(f"   ✅ Created schedule for: {dash_name}")
                        
                        # Create subscriptions
                        if subscriptions_json and subscriptions_json != '[]':
                            try:
                                subs_list = json.loads(subscriptions_json)
                                for sub in subs_list:
                                    user_id = sub.get('subscriber', {}).get('user_id')
                                    if user_id:
                                        target_client.lakeview.create_subscription(
                                            dashboard_id=new_dashboard_id,
                                            schedule_id=schedule.schedule_id,
                                            subscription=Subscription(
                                                subscriber={'user_id': user_id}
                                            )
                                        )
                                        subs_applied += 1
                            except json.JSONDecodeError:
                                pass
                    
                    except Exception as e:
                        print(f"   ❌ Failed to create schedule for {dash_name}: {e}")
        
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

if [ "$APPLY_PERMISSIONS" = "true" ]; then
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
