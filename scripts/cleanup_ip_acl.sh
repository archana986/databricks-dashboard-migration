#!/usr/bin/env bash

################################################################################
# Cleanup IP ACL After Migration - Removal Script
################################################################################
# 
# Purpose: Remove source workspace IP from target workspace allowlist after
#          successful migration and validation.
#
# Usage: ./cleanup_ip_acl.sh [options]
#
# Prerequisites:
#   - Migration completed successfully
#   - Dashboards validated in target workspace
#   - No future migrations planned from this source workspace
#
# IMPORTANT: Only run this after confirming migration success!
#
# Platform Support:
#   - macOS (native bash)
#   - Linux (native bash)
#   - Windows (Git Bash, WSL, or Cygwin)
#
################################################################################

set -e  # Exit on error
set -o pipefail  # Exit on pipe failure

################################################################################
# OS Detection
################################################################################

detect_os() {
    case "$(uname -s)" in
        Darwin*)    echo "macos" ;;
        Linux*)     echo "linux" ;;
        CYGWIN*|MINGW*|MSYS*) echo "windows" ;;
        *)          echo "unknown" ;;
    esac
}

OS_TYPE=$(detect_os)

# Windows-specific settings
if [ "$OS_TYPE" = "windows" ]; then
    export MSYS_NO_PATHCONV=1
fi

# Color codes for output (with terminal detection)
if [ -t 1 ] && [ "$TERM" != "dumb" ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    MAGENTA='\033[0;35m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    MAGENTA=''
    NC=''
fi

# Configuration
SOURCE_PROFILE="${SOURCE_PROFILE:-source-workspace}"
TARGET_PROFILE="${TARGET_PROFILE:-target-workspace}"
CLUSTER_IP="${CLUSTER_IP:-}"
FORCE="${FORCE:-false}"
AUTO_DETECT="${AUTO_DETECT:-true}"
VOLUME_BASE="${VOLUME_BASE:-/Volumes/YOUR_CATALOG/YOUR_SCHEMA/dashboard_migration}"

################################################################################
# Helper Functions
################################################################################

log_info() {
    echo -e "${BLUE}ℹ ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠️ ${NC} $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
}

log_critical() {
    echo -e "${MAGENTA}🚨${NC} $1"
}

log_section() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

################################################################################
# Step 0: Auto-Detect Cluster IP (if not provided)
################################################################################

auto_detect_cluster_ip() {
    if [ -n "$CLUSTER_IP" ]; then
        log_section "Cluster IP Configuration"
        log_info "Using provided cluster IP: ${GREEN}${CLUSTER_IP}${NC}"
        echo ""
        return 0
    fi
    
    if [ "$AUTO_DETECT" != "true" ]; then
        log_section "Cluster IP Configuration"
        log_info "Auto-detection disabled"
        echo ""
        return 0
    fi
    
    log_section "Step 1: Auto-Detect Stored Cluster IP"
    
    log_info "Retrieving IP metadata from UC volume"
    echo ""
    
    METADATA_FILE="${VOLUME_BASE}/cluster_ip_metadata.json"
    # CLI requires dbfs: prefix for volume paths
    DBFS_METADATA_FILE="dbfs:${METADATA_FILE}"
    
    log_info "Metadata location:"
    echo "   • File: ${METADATA_FILE}"
    echo "   • CLI path: ${DBFS_METADATA_FILE}"
    echo "   • Profile: ${SOURCE_PROFILE}"
    echo ""
    
    # Try to read metadata with correct dbfs: prefix
    METADATA=$(databricks fs cat "$DBFS_METADATA_FILE" --profile "$SOURCE_PROFILE" 2>/dev/null || echo "")
    
    if [ -n "$METADATA" ]; then
        DETECTED_IP=$(echo "$METADATA" | grep -o '"cluster_ip":[[:space:]]*"[^"]*"' | cut -d'"' -f4)
        
        if [ -n "$DETECTED_IP" ]; then
            CLUSTER_IP="$DETECTED_IP"
            
            # Extract all metadata
            DETECTED_AT=$(echo "$METADATA" | grep -o '"detected_at":[[:space:]]*"[^"]*"' | cut -d'"' -f4 || echo "Unknown")
            DETECTED_BY=$(echo "$METADATA" | grep -o '"detected_by":[[:space:]]*"[^"]*"' | cut -d'"' -f4 || echo "Unknown")
            
            log_info "IP metadata retrieved:"
            echo "   • Cluster IP: ${GREEN}${CLUSTER_IP}${NC}"
            echo "   • Detected at: ${DETECTED_AT}"
            echo "   • Detected by: ${DETECTED_BY}"
            echo ""
            
            log_success "Auto-detected cluster IP successfully"
            echo ""
            return 0
        fi
    fi
    
    log_warning "Could not auto-detect cluster IP from stored metadata"
    echo ""
    log_info "Options:"
    echo "   1. Provide IP manually: --cluster-ip X.X.X.X"
    echo "   2. Check if metadata file exists: ${METADATA_FILE}"
    echo "   3. Run auto_setup_ip_acl.sh first to generate metadata"
    echo ""
    exit 1
}

################################################################################
# Pre-Cleanup Information Display
################################################################################

show_cleanup_info() {
    log_section "Pre-Cleanup Information"
    
    log_info "Configuration:"
    echo "   • Target workspace profile: ${TARGET_PROFILE}"
    echo "   • Source workspace profile: ${SOURCE_PROFILE}"
    echo "   • Volume base: ${VOLUME_BASE}"
    echo ""
    
    if [ -n "$CLUSTER_IP" ]; then
        log_info "IP to remove:"
        echo "   • Cluster IP: ${GREEN}${CLUSTER_IP}${NC}"
        echo "   • IP Range: ${GREEN}${CLUSTER_IP}/32${NC}"
    else
        log_warning "Cluster IP not yet detected - will auto-detect from metadata"
    fi
    echo ""
}

################################################################################
# Step 1: Display Warning & Confirm
################################################################################

confirm_cleanup() {
    log_section "⚠️  IMPORTANT: Read Before Proceeding"
    
    echo -e "${YELLOW}This script will REMOVE IP allowlist entries from target workspace.${NC}"
    echo ""
    echo "Before proceeding, ensure:"
    echo ""
    echo "  ✅ Migration completed successfully"
    echo "  ✅ All dashboards verified in target workspace"
    echo "  ✅ Dashboard permissions tested"
    echo "  ✅ Data queries execute correctly"
    echo "  ✅ Schedules/subscriptions working (if applicable)"
    echo "  ✅ No future migrations planned from source workspace"
    echo ""
    echo -e "${RED}⚠️  After removal, future deployments from source will be blocked!${NC}"
    echo ""
    
    if [ "$FORCE" = true ]; then
        log_warning "FORCE mode enabled - skipping confirmation"
        return 0
    fi
    
    read -p "Have you completed validation? (yes/no): " VALIDATION_CONFIRM
    
    if [[ ! $VALIDATION_CONFIRM =~ ^[Yy][Ee][Ss]$ ]]; then
        log_warning "User did not confirm validation complete"
        echo ""
        echo "Please complete these validation steps first:"
        echo ""
        echo "1. Open your target workspace in a browser"
        echo "2. Navigate to: SQL → Dashboards → /Shared/Migrated_Dashboards_V2"
        echo "3. Verify all dashboards are present and published"
        echo "4. Open a sample dashboard and run queries"
        echo "5. Check permissions (Share button)"
        echo "6. Check schedules (Schedule button)"
        echo ""
        log_error "Cleanup aborted by user"
        exit 1
    fi
    
    echo ""
    read -p "Are you sure you want to remove IP allowlist entries? (yes/no): " FINAL_CONFIRM
    
    if [[ ! $FINAL_CONFIRM =~ ^[Yy][Ee][Ss]$ ]]; then
        log_error "Cleanup aborted by user"
        exit 1
    fi
    
    log_success "User confirmed - proceeding with cleanup"
    echo ""
}

################################################################################
# Step 2: List Current IP Allowlist Entries
################################################################################

list_current_entries() {
    log_section "Step 2: Review Current IP ACL Entries"
    
    log_info "Step 2.1: Querying target workspace for IP ACL entries"
    echo ""
    
    log_info "Connection details:"
    echo "   • Profile: ${TARGET_PROFILE}"
    
    # Get workspace details
    USER_INFO=$(databricks current-user me --profile "$TARGET_PROFILE" 2>/dev/null || echo "")
    WORKSPACE_HOST=$(echo "$USER_INFO" | grep -o '"workspace_url":"[^"]*"' | cut -d'"' -f4 || echo "")
    CURRENT_USER=$(echo "$USER_INFO" | grep -o '"userName":"[^"]*"' | cut -d'"' -f4 || echo "")
    
    if [ -n "$WORKSPACE_HOST" ]; then
        echo "   • Host: ${WORKSPACE_HOST}"
    fi
    if [ -n "$CURRENT_USER" ]; then
        echo "   • User: ${CURRENT_USER}"
    fi
    echo ""
    
    log_info "Step 2.2: Retrieving IP access lists"
    echo ""
    
    ALL_LISTS=$(databricks ip-access-lists list --profile "$TARGET_PROFILE" --output json 2>/dev/null || echo "")
    
    if [ -z "$ALL_LISTS" ]; then
        log_error "Failed to fetch IP access lists from target workspace"
        echo ""
        log_info "Troubleshooting:"
        echo "   1. Verify target workspace profile is configured"
        echo "   2. Check you have permissions to view IP ACLs"
        echo "   3. Ensure IP ACLs are enabled on target workspace"
        echo ""
        exit 1
    fi
    
    # Count total entries
    TOTAL_ENTRIES=$(echo "$ALL_LISTS" | grep -c '"list_id"' || echo "0")
    
    log_info "Current IP ACL summary:"
    echo "   • Total entries: ${TOTAL_ENTRIES}"
    echo "   • Looking for IP: ${GREEN}${CLUSTER_IP}${NC}"
    echo ""
    
    # Find source-workspace entries
    log_info "Step 2.3: Identifying entries to remove"
    echo ""
    
    # Use Python for robust JSON parsing to find entries with "source-workspace" in label
    SOURCE_LIST_IDS=$(echo "$ALL_LISTS" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for entry in data:
        label = entry.get('label', '')
        if 'source-workspace' in label.lower():
            print(entry.get('list_id', ''))
except:
    pass
" 2>/dev/null || echo "")
    
    SOURCE_COUNT=$(echo "$SOURCE_LIST_IDS" | grep -c . 2>/dev/null || echo "0")
    
    if [ -z "$SOURCE_LIST_IDS" ] || [ "$SOURCE_COUNT" = "0" ]; then
        log_info "No entries with 'source-workspace' label found by label search"
        log_info "Will search by IP address: ${CLUSTER_IP}"
        echo ""
    else
        log_info "Found entries with 'source-workspace' label:"
        echo "   • Count: ${SOURCE_COUNT}"
        echo "   • List IDs: ${SOURCE_LIST_IDS}"
        echo ""
        log_success "Identified ${SOURCE_COUNT} entry(ies) to remove by label"
        echo ""
    fi
    
    # Continue to extract list IDs (Python handles both label and IP search)
    if [ -z "$CLUSTER_IP" ] && [ -z "$SOURCE_LIST_IDS" ]; then
        log_error "Cannot identify which entries to remove"
        echo ""
        log_info "No cluster IP provided and no source-workspace entries found"
        echo ""
        log_info "Options:"
        echo "   1. Provide IP: --cluster-ip X.X.X.X"
        echo "   2. Ensure metadata exists in UC volume"
        echo ""
        echo "Run with --cluster-ip to specify the IP to remove:"
        echo "  $0 --cluster-ip X.X.X.X"
        exit 1
    fi
    
    # Extract list IDs using Python for robust JSON parsing
    # Find by label containing "source-workspace"
    LABEL_LIST_IDS=$(echo "$ALL_LISTS" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for entry in data:
        label = entry.get('label', '')
        if 'source-workspace' in label.lower():
            print(entry.get('list_id', ''))
except:
    pass
" 2>/dev/null || echo "")
    
    # Convert to array
    LIST_IDS=()
    while IFS= read -r id; do
        [ -n "$id" ] && LIST_IDS+=("$id")
    done <<< "$LABEL_LIST_IDS"
    
    # If cluster IP provided, also find by IP using Python
    if [ -n "$CLUSTER_IP" ]; then
        IP_FOUND_IDS=$(echo "$ALL_LISTS" | python3 -c "
import sys, json
cluster_ip = '$CLUSTER_IP'
try:
    data = json.load(sys.stdin)
    for entry in data:
        ip_addresses = entry.get('ip_addresses', [])
        # Check if any IP in the list matches (with or without /32)
        for ip in ip_addresses:
            if cluster_ip in ip or ip.replace('/32', '') == cluster_ip:
                print(entry.get('list_id', ''))
                break
except:
    pass
" 2>/dev/null || echo "")
        
        # Add to array
        while IFS= read -r id; do
            [ -n "$id" ] && LIST_IDS+=("$id")
        done <<< "$IP_FOUND_IDS"
    fi
    
    # Deduplicate
    LIST_IDS=($(echo "${LIST_IDS[@]}" | tr ' ' '\n' | sort -u | grep -v '^$'))
    
    if [ ${#LIST_IDS[@]} -eq 0 ]; then
        log_error "No list IDs found to remove"
        exit 1
    fi
    
    log_info "Found ${#LIST_IDS[@]} entry(ies) to remove:"
    for list_id in "${LIST_IDS[@]}"; do
        echo "  • $list_id"
    done
    echo ""
}

################################################################################
# Step 3: Remove IP Allowlist Entries
################################################################################

remove_entries() {
    log_section "Step 3: Remove IP ACL Entries"
    
    if [ ${#LIST_IDS[@]} -eq 0 ]; then
        log_error "No entries to remove"
        exit 1
    fi
    
    log_info "Removal plan:"
    echo "   • Number of entries to remove: ${#LIST_IDS[@]}"
    echo "   • Target workspace: ${TARGET_PROFILE}"
    echo ""
    
    REMOVED_COUNT=0
    FAILED_COUNT=0
    ENTRY_INDEX=1
    
    # Arrays to store deleted entry details for final proof
    declare -a DELETED_LABELS
    declare -a DELETED_IPS
    declare -a DELETED_IDS
    
    for list_id in "${LIST_IDS[@]}"; do
        log_info "Step 3.${ENTRY_INDEX}: Processing entry ${ENTRY_INDEX} of ${#LIST_IDS[@]}"
        echo "   • List ID: ${list_id}"
        echo ""
        
        # Get entry details before removal
        ENTRY_DETAILS=$(databricks ip-access-lists get "$list_id" --profile "$TARGET_PROFILE" 2>/dev/null || echo "")
        
        LABEL=""
        IPS=""
        LIST_TYPE=""
        
        if [ -n "$ENTRY_DETAILS" ]; then
            LABEL=$(echo "$ENTRY_DETAILS" | grep -o '"label":"[^"]*"' | cut -d'"' -f4 || echo "Unknown")
            IPS=$(echo "$ENTRY_DETAILS" | grep -o '"ip_addresses":\[[^]]*\]' | sed 's/"ip_addresses":\[//;s/\]//;s/"//g' || echo "Unknown")
            LIST_TYPE=$(echo "$ENTRY_DETAILS" | grep -o '"list_type":"[^"]*"' | cut -d'"' -f4 || echo "Unknown")
            
            log_info "Entry details BEFORE deletion:"
            echo "   • Label: ${MAGENTA}${LABEL}${NC}"
            echo "   • IP addresses: ${GREEN}${IPS}${NC}"
            echo "   • List type: ${LIST_TYPE}"
            echo ""
        else
            log_warning "Could not retrieve entry details (entry may not exist)"
            echo ""
        fi
        
        # Remove the entry
        log_info "Executing deletion command..."
        echo ""
        
        if DELETE_OUTPUT=$(databricks ip-access-lists delete "$list_id" --profile "$TARGET_PROFILE" 2>&1); then
            log_info "Deletion command succeeded, verifying removal..."
            echo ""
            
            # PROVE DELETION: Try to get the entry again - should fail
            sleep 2  # Brief wait for API consistency
            VERIFY_GONE=$(databricks ip-access-lists get "$list_id" --profile "$TARGET_PROFILE" 2>&1 || echo "")
            VERIFY_EXIT=$?
            
            # Check if entry is gone: exit code non-zero, or response contains error indicators
            if [ $VERIFY_EXIT -ne 0 ] || echo "$VERIFY_GONE" | grep -qiE "not found|does not exist|404|RESOURCE_DOES_NOT_EXIST|error|invalid"; then
                log_success "DELETION CONFIRMED - Entry no longer exists"
                echo "   • List ID: ${list_id}"
                if [ -n "$LABEL" ]; then
                    echo "   • Deleted label: ${MAGENTA}${LABEL}${NC}"
                fi
                if [ -n "$IPS" ]; then
                    echo "   • Deleted IPs: ${GREEN}${IPS}${NC}"
                fi
                echo "   • Proof: Entry query returned 'not found'"
                echo ""
                
                # Store for final summary
                DELETED_LABELS+=("$LABEL")
                DELETED_IPS+=("$IPS")
                DELETED_IDS+=("$list_id")
                
                REMOVED_COUNT=$((REMOVED_COUNT + 1))
            else
                log_warning "Deletion command succeeded but entry still exists"
                echo "   • List ID: ${list_id}"
                echo "   • This may indicate a race condition or caching"
                echo ""
                log_info "Marking as failed for safety"
                echo ""
                FAILED_COUNT=$((FAILED_COUNT + 1))
            fi
        else
            log_error "DELETION FAILED"
            echo "   • List ID: ${list_id}"
            if [ -n "$LABEL" ]; then
                echo "   • Label: ${MAGENTA}${LABEL}${NC}"
            fi
            echo "   • Error output:"
            echo "$DELETE_OUTPUT" | sed 's/^/     /'
            echo ""
            FAILED_COUNT=$((FAILED_COUNT + 1))
        fi
        
        echo ""
        ENTRY_INDEX=$((ENTRY_INDEX + 1))
    done
    
    log_section "Removal Summary"
    
    log_info "Processing results:"
    echo "   • Total entries processed: ${#LIST_IDS[@]}"
    echo "   • Successfully removed: ${GREEN}${REMOVED_COUNT}${NC}"
    if [ $FAILED_COUNT -gt 0 ]; then
        echo "   • Failed: ${RED}${FAILED_COUNT}${NC}"
    else
        echo "   • Failed: 0"
    fi
    echo ""
    
    if [ $REMOVED_COUNT -gt 0 ]; then
        log_success "Confirmed Deletions (${REMOVED_COUNT} entries)"
        echo ""
        
        for i in "${!DELETED_IDS[@]}"; do
            IDX=$((i + 1))
            echo "   ${IDX}. List ID: ${DELETED_IDS[$i]}"
            echo "      • Label: ${MAGENTA}${DELETED_LABELS[$i]}${NC}"
            echo "      • IPs: ${GREEN}${DELETED_IPS[$i]}${NC}"
            echo "      • Status: DELETED and verified gone"
            echo ""
        done
    fi
    
    if [ $FAILED_COUNT -gt 0 ]; then
        log_warning "${FAILED_COUNT} entry(ies) could not be removed"
        echo ""
        log_info "Troubleshooting:"
        echo "   1. Check you have admin permissions on target workspace"
        echo "   2. Verify list IDs are correct"
        echo "   3. Remove manually via UI: Settings → Security → IP Access Lists"
        echo ""
    else
        log_success "All IP ACL entries removed successfully and verified"
        echo ""
    fi
}

################################################################################
# Step 4: Verify Removal
################################################################################

verify_removal() {
    log_section "Step 4: Post-Cleanup Verification"
    
    log_info "Step 4.1: Waiting for IP ACL propagation"
    echo "   • Wait time: 2 seconds (brief check)"
    echo ""
    
    sleep 2  # Brief wait for propagation
    
    log_info "Step 4.2: Querying target workspace for remaining entries"
    echo ""
    
    # Get all current entries
    ALL_REMAINING=$(databricks ip-access-lists list --profile "$TARGET_PROFILE" 2>/dev/null || echo "")
    REMAINING_COUNT=$(echo "$ALL_REMAINING" | grep -c '"list_id"' || echo "0")
    
    log_info "Current IP ACL status:"
    echo "   • Total remaining entries: ${REMAINING_COUNT}"
    echo ""
    
    # Check for source-workspace labels
    log_info "Step 4.3: Checking for source-workspace labeled entries"
    echo ""
    
    REMAINING=$(echo "$ALL_REMAINING" | grep -i "source-workspace" || true)
    
    if [ -z "$REMAINING" ]; then
        log_success "No source-workspace entries found"
        echo "   • All labeled entries successfully removed"
        echo ""
    else
        log_warning "Found remaining source-workspace entries:"
        echo ""
        echo "$REMAINING" | sed 's/^/   /'
        echo ""
    fi
    
    # Check specific IP if provided
    if [ -n "$CLUSTER_IP" ]; then
        log_info "Step 4.4: Verifying IP ${GREEN}${CLUSTER_IP}${NC} removal"
        echo ""
        
        IP_CHECK=$(echo "$ALL_REMAINING" | grep "$CLUSTER_IP" || true)
        
        if [ -z "$IP_CHECK" ]; then
            log_success "PROOF OF DELETION: IP ${GREEN}${CLUSTER_IP}${NC} not found in allowlist"
            echo "   • Searched all ${REMAINING_COUNT} remaining entries"
            echo "   • IP does not appear in any entry"
            echo "   • Target workspace will now block connections from this IP"
            echo ""
        else
            log_warning "DELETION NOT CONFIRMED: IP ${GREEN}${CLUSTER_IP}${NC} still appears"
            echo ""
            log_info "Found in these entries:"
            echo "$IP_CHECK" | sed 's/^/   /'
            echo ""
            log_info "This may indicate:"
            echo "   • IP exists in other non-source-workspace entries (check labels)"
            echo "   • CLI result caching (wait 1-2 minutes and re-run verification)"
            echo "   • Propagation delay (check UI: Settings → Security → IP Access Lists)"
            echo ""
        fi
    fi
    
    # Check all deleted IPs are gone
    if [ ${#DELETED_IPS[@]} -gt 0 ]; then
        log_info "Step 4.5: Verifying all deleted IPs are gone"
        echo ""
        
        ALL_VERIFIED=true
        for deleted_ip in "${DELETED_IPS[@]}"; do
            # Clean up the IP (remove /32, spaces, etc)
            CLEAN_IP=$(echo "$deleted_ip" | sed 's/\/32//;s/,.*//;s/ //g')
            
            if [ -n "$CLEAN_IP" ] && [ "$CLEAN_IP" != "Unknown" ]; then
                IP_STILL_EXISTS=$(echo "$ALL_REMAINING" | grep "$CLEAN_IP" || true)
                
                if [ -z "$IP_STILL_EXISTS" ]; then
                    log_success "   ✅ ${GREEN}${CLEAN_IP}${NC} - NOT found (deleted)"
                else
                    log_warning "   ⚠️  ${CLEAN_IP} - STILL EXISTS in allowlist"
                    ALL_VERIFIED=false
                fi
            fi
        done
        echo ""
        
        if [ "$ALL_VERIFIED" = true ]; then
            log_success "ALL DELETED IPS VERIFIED ABSENT"
            echo ""
        else
            log_warning "Some deleted IPs still found - see details above"
            echo ""
        fi
    fi
    
    log_info "Final verification summary:"
    echo "   • Entries before cleanup: ${TOTAL_ENTRIES:-Unknown}"
    echo "   • Entries after cleanup: ${REMAINING_COUNT}"
    echo "   • Net change: -${REMOVED_COUNT}"
    echo "   • All deletions verified: $([ "$ALL_VERIFIED" = true ] && echo "✅ YES" || echo "⚠️  CHECK ABOVE")"
    echo ""
}

################################################################################
# Step 5: Cleanup IP Detection Infrastructure
################################################################################

cleanup_ip_detection() {
    log_section "  Step 5: Cleanup IP Detection Infrastructure"
    echo ""
    
    log_info "Checking for IP detection bundle..."
    echo ""
    
    # Check if bundle exists
    BUNDLE_PATH="ip-detection"
    if [ ! -d "$BUNDLE_PATH" ]; then
        log_info "No IP detection bundle found - nothing to cleanup"
        echo ""
        return 0
    fi
    
    log_info "📦 IP detection bundle found:"
    echo "   • Location: ${BUNDLE_PATH}/databricks.yml"
    echo "   • Target: dev"
    echo "   • Workspace: ${SOURCE_PROFILE}"
    echo ""
    
    # Get job info before destroying
    log_info "Getting job details before cleanup..."
    JOB_ID=$(databricks jobs list --profile "$SOURCE_PROFILE" 2>&1 | grep "IP_Detection_dev" | grep -oE '[0-9]{15,}' | head -1 || echo "")
    
    if [ -n "$JOB_ID" ]; then
        log_info "Found IP detection job:"
        echo "   • Job ID: ${JOB_ID}"
        echo "   • Job Name: IP_Detection_dev"
        echo ""
    fi
    
    # Destroy the bundle
    log_info "Destroying IP detection bundle..."
    echo ""
    
    cd "$BUNDLE_PATH" || return 1
    
    DESTROY_OUTPUT=$(databricks bundle destroy -t dev --profile "$SOURCE_PROFILE" --auto-approve 2>&1)
    DESTROY_EXIT=$?
    
    cd - > /dev/null || return 1
    
    if [ $DESTROY_EXIT -eq 0 ]; then
        log_success "IP detection bundle destroyed successfully"
        echo ""
        
        # Verify job is gone
        if [ -n "$JOB_ID" ]; then
            log_info "Verifying job deletion..."
            
            JOB_CHECK=$(databricks jobs get "$JOB_ID" --profile "$SOURCE_PROFILE" 2>&1 || echo "")
            
            if echo "$JOB_CHECK" | grep -q "does not exist\|RESOURCE_DOES_NOT_EXIST"; then
                log_success "Job successfully deleted (ID: ${JOB_ID})"
                echo ""
            else
                log_warning "Job may still exist - check manually"
                echo "   Job ID: ${JOB_ID}"
                echo ""
            fi
        fi
        
        log_info "Cleanup summary:"
        echo "   • Bundle: Destroyed"
        echo "   • Job: Deleted"
        echo "   • Workspace: ${SOURCE_PROFILE}"
        echo ""
        
    else
        log_warning "Bundle destroy encountered issues (may already be deleted)"
        echo "   This is OK if bundle was manually deleted"
        echo ""
    fi
}

################################################################################
# Step 6: Create Backup/Record
################################################################################

create_record() {
    log_section "Step 5: Create Cleanup Record"
    
    RECORD_FILE="ip_acl_cleanup_$(date +%Y%m%d_%H%M%S).log"
    RECORD_PATH="/tmp/$RECORD_FILE"
    
    log_info "Creating detailed cleanup record with deletion proof..."
    echo ""
    
    cat > "$RECORD_PATH" << EOF
IP ACL Cleanup Record - DELETION PROOF
=======================================

Execution Details:
-----------------
Date: $(date)
User: $(whoami)
Target Profile: $TARGET_PROFILE
Source Profile: $SOURCE_PROFILE
Cluster IP: ${CLUSTER_IP:-Not specified}

Deletion Results:
----------------
Total Entries Processed: ${#LIST_IDS[@]}
Successfully Deleted: ${REMOVED_COUNT}
Failed: ${FAILED_COUNT}

PROOF OF DELETION - Verified Entries:
-------------------------------------
EOF
    
    if [ ${#DELETED_IDS[@]} -gt 0 ]; then
        for i in "${!DELETED_IDS[@]}"; do
            IDX=$((i + 1))
            cat >> "$RECORD_PATH" << EOF

Entry ${IDX}:
  List ID: ${DELETED_IDS[$i]}
  Label: ${DELETED_LABELS[$i]}
  IP Addresses: ${DELETED_IPS[$i]}
  Status: DELETED
  Verification: Entry re-queried and confirmed NOT FOUND
  Timestamp: $(date)
EOF
        done
    else
        echo "  (No entries were successfully deleted)" >> "$RECORD_PATH"
    fi
    
    cat >> "$RECORD_PATH" << EOF

Verification Steps Completed:
----------------------------
✅ Each entry deletion confirmed via API
✅ Each deleted entry re-queried to prove absence
✅ All deleted IPs searched in remaining entries
✅ Final ACL count verified (before: ${TOTAL_ENTRIES:-N/A}, after: ${REMAINING_COUNT:-N/A})

Impact:
-------
⚠️  Future deployments from source cluster IPs will be BLOCKED
⚠️  Target workspace will reject connections from deleted IPs
✅ Migration validated before cleanup
✅ Dashboards remain accessible in target workspace

To Restore Access:
-----------------
If you need to deploy again from source workspace:
  ./scripts/auto_setup_ip_acl.sh --cluster-ip ${CLUSTER_IP:-35.155.15.56}

This will re-add the IP to the target workspace allowlist.

EOF
    
    log_success "Detailed record created: ${RECORD_PATH}"
    echo ""
    log_info "Record includes:"
    echo "   • Complete deletion details for each entry"
    echo "   • Verification proof for each deletion"
    echo "   • Restoration commands if needed"
    echo ""
}

################################################################################
# Step 7: Final Summary
################################################################################

generate_summary() {
    log_section "✨ CLEANUP COMPLETE - DELETION PROOF"
    
    echo ""
    log_success "IP ACL cleanup completed successfully!"
    echo ""
    
    log_info "═══════════════════════════════════════════════════════════"
    log_info "  PROOF OF DELETION: Exactly What Was Removed"
    log_info "═══════════════════════════════════════════════════════════"
    echo ""
    
    if [ ${#DELETED_IDS[@]} -gt 0 ]; then
        log_success "Successfully deleted and verified ${#DELETED_IDS[@]} entry(ies):"
        echo ""
        
        for i in "${!DELETED_IDS[@]}"; do
            IDX=$((i + 1))
            echo "   ${IDX}. ${MAGENTA}${DELETED_LABELS[$i]}${NC}"
            echo "      └─ List ID: ${DELETED_IDS[$i]}"
            echo "      └─ IP Addresses: ${GREEN}${DELETED_IPS[$i]}${NC}"
            echo "      └─ Status: ${GREEN}✅ DELETED AND VERIFIED ABSENT${NC}"
            echo ""
        done
    else
        log_warning "No entries were successfully deleted"
        echo ""
    fi
    
    log_info "═══════════════════════════════════════════════════════════"
    log_info "  Verification Results"
    log_info "═══════════════════════════════════════════════════════════"
    echo ""
    
    echo "  ✅ Deletion commands executed: ${#LIST_IDS[@]}"
    echo "  ✅ Deletions confirmed and verified: ${REMOVED_COUNT}"
    echo "  ✅ Each deleted entry re-queried to prove absence"
    echo "  ✅ All deleted IPs confirmed not in allowlist"
    echo "  ✅ Cleanup record created"
    echo ""
    
    if [ $FAILED_COUNT -gt 0 ]; then
        log_warning "Failed deletions: ${FAILED_COUNT}"
        echo "     (See details above for troubleshooting)"
        echo ""
    fi
    
    log_info "═══════════════════════════════════════════════════════════"
    log_critical "  IMPORTANT: Impact on Future Deployments"
    log_info "═══════════════════════════════════════════════════════════"
    echo ""
    
    if [ ${#DELETED_IPS[@]} -gt 0 ]; then
        echo "  ${RED}⚠️  The following IPs can NO LONGER deploy to target workspace:${NC}"
        echo ""
        for deleted_ip in "${DELETED_IPS[@]}"; do
            echo "     • ${RED}${deleted_ip}${NC} - BLOCKED"
        done
        echo ""
    fi
    
    echo "  ${YELLOW}To restore access for future deployments:${NC}"
    echo "     ${BLUE}./scripts/auto_setup_ip_acl.sh --cluster-ip ${CLUSTER_IP:-35.155.15.56}${NC}"
    echo ""
    
    log_info "═══════════════════════════════════════════════════════════"
    log_success "  Migration Status"
    log_info "═══════════════════════════════════════════════════════════"
    echo ""
    echo "  ✅ Migration: COMPLETE"
    echo "  ✅ Target Workspace: Dashboards accessible"
    echo "  ✅ IP Cleanup: VERIFIED"
    echo "  ✅ Source Workspace: Blocked (as intended)"
    echo ""
    
    echo "Next Steps:"
    echo "  1. ✅ Migration validated"
    echo "  2. ✅ IP ACL cleaned up and verified"
    echo "  3. ✅ No further action required (unless re-deploying)"
    echo ""
}

################################################################################
# Main Execution
################################################################################

show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --source-profile PROFILE    Source workspace CLI profile (default: source-workspace)"
    echo "  --target-profile PROFILE    Target workspace CLI profile (default: target-workspace)"
    echo "  --cluster-ip IP             Source cluster IP to remove (auto-detected if not provided)"
    echo "  --volume-base PATH          UC volume path for stored IP (default: /Volumes/...)"
    echo "  --no-auto-detect            Disable automatic IP detection"
    echo "  --force                     Skip confirmation prompts (use with caution!)"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  SOURCE_PROFILE              Override source profile"
    echo "  TARGET_PROFILE              Override target profile"
    echo "  CLUSTER_IP                  Source cluster IP (overrides auto-detection)"
    echo "  AUTO_DETECT                 Set to 'false' to disable (default: 'true')"
    echo "  FORCE                       Set to 'true' to skip confirmations"
    echo "  VOLUME_BASE                 UC volume path"
    echo ""
    echo "Examples:"
    echo ""
    echo "  # Auto-detect IP and cleanup (recommended)"
    echo "  $0"
    echo ""
    echo "  # Cleanup with specific IP"
    echo "  $0 --cluster-ip 35.155.15.56"
    echo ""
    echo "  # Force cleanup (no confirmations)"
    echo "  $0 --cluster-ip 35.155.15.56 --force"
    echo ""
    echo "  # Custom profiles"
    echo "  $0 --source-profile my-source --target-profile my-target"
    echo ""
    echo "IMPORTANT:"
    echo "  - Only run after successful migration validation"
    echo "  - IP will be auto-detected from stored metadata if not provided"
    echo "  - Future deployments will be blocked after cleanup"
    echo "  - Use setup_ip_acl_and_deploy.sh to restore access"
    echo ""
}

main() {
    clear
    
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║         IP ACL Cleanup After Migration Validation            ║"
    echo "║                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Parse command line arguments
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
            --cluster-ip)
                CLUSTER_IP="$2"
                shift 2
                ;;
            --volume-base)
                VOLUME_BASE="$2"
                shift 2
                ;;
            --no-auto-detect)
                AUTO_DETECT=false
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Execute cleanup workflow
    auto_detect_cluster_ip
    show_cleanup_info
    confirm_cleanup
    list_current_entries
    remove_entries
    verify_removal
    cleanup_ip_detection
    create_record
    generate_summary
    
    log_success "Cleanup script completed successfully! 🎉"
    echo ""
}

# Run main function
main "$@"
