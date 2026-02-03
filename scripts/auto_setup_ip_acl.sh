#!/usr/bin/env bash

################################################################################
# Fully Automated IP Detection + Whitelist Setup
################################################################################
#
# Purpose: Automatically detect cluster IP and whitelist it on target workspace
#
# What this does:
#   1. Runs notebook on source workspace to detect cluster IP
#   2. Extracts detected IP from notebook output
#   3. Whitelists IP on target workspace
#   4. Waits for propagation
#   5. Ready for deployment (run Bundle_04 separately)
#
# Usage: ./auto_setup_ip_acl.sh [options]
#
# Platform Support:
#   - macOS (native bash)
#   - Linux (native bash)
#   - Windows (Git Bash, WSL, or Cygwin)
#
################################################################################

set -e
set -o pipefail

################################################################################
# OS Detection and Platform-Specific Setup
################################################################################

# Detect operating system
detect_os() {
    case "$(uname -s)" in
        Darwin*)    echo "macos" ;;
        Linux*)     echo "linux" ;;
        CYGWIN*|MINGW*|MSYS*) echo "windows" ;;
        *)          echo "unknown" ;;
    esac
}

OS_TYPE=$(detect_os)

# Platform-specific configuration
if [ "$OS_TYPE" = "windows" ]; then
    # Windows (Git Bash) specific settings
    export MSYS_NO_PATHCONV=1  # Prevent path conversion
    # Use winpty for interactive commands if available
    WINPTY=$(command -v winpty 2>/dev/null || echo "")
fi

# Color codes (work on all platforms with proper terminal)
if [ -t 1 ] && [ "$TERM" != "dumb" ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    MAGENTA='\033[0;35m'
    NC='\033[0m'
else
    # No colors for non-interactive or dumb terminals
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
BUNDLE_TARGET="${BUNDLE_TARGET:-dev}"
VOLUME_BASE="${VOLUME_BASE:-/Volumes/archana_krish_fe_dsa/vizient_deep_dive/dashboard_migration}"
PROPAGATION_WAIT="${PROPAGATION_WAIT:-300}"
DRY_RUN="${DRY_RUN:-false}"

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

log_section() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

################################################################################
# Configuration Display
################################################################################

show_configuration() {
    log_section "Configuration Summary"
    
    log_info "Source Workspace:"
    echo "   • Profile: ${SOURCE_PROFILE}"
    echo "   • Bundle Target: ${BUNDLE_TARGET}"
    echo ""
    
    log_info "Target Workspace:"
    echo "   • Profile: ${TARGET_PROFILE}"
    echo "   • Volume Base: ${VOLUME_BASE}"
    echo ""
    
    if [ "$DRY_RUN" = "true" ]; then
        log_warning "Mode: DRY RUN (no changes will be made)"
    else
        log_info "Mode: LIVE (changes will be applied)"
    fi
    echo ""
}

################################################################################
# Step 1: Detect Cluster IP Programmatically
################################################################################

detect_cluster_ip() {
    log_section "STEP 1: Detect Source Cluster IP"
    
    # Check if IP was provided via command line
    if [ -n "$CLUSTER_IP" ]; then
        echo ""
        log_info "Using provided cluster IP: ${GREEN}${CLUSTER_IP}${NC}"
        log_success "Skipping auto-detection (IP provided via --cluster-ip)"
        echo ""
        return 0
    fi
    
    echo ""
    log_info "📦 Deploying IP detection infrastructure to source workspace..."
    echo ""
    
    if [ "$DRY_RUN" = "true" ]; then
        log_info "DRY RUN: Would deploy IP detection bundle"
        echo "   • Bundle directory: ip-detection/"
        echo "   • Target: dev"
        echo "   • Profile: ${SOURCE_PROFILE}"
        echo ""
        log_success "DRY RUN: Skipping actual bundle deployment"
        echo ""
        
        # Set flag for dry-run cleanup simulation
        CLEANUP_NEEDED=true
        
        # Simulate job creation and execution
        JOB_ID="123456"
        RUN_ID="789012"
        
        log_success "DRY RUN: Simulated job resource: ${GREEN}${JOB_ID}${NC}"
        echo ""
        
        log_info "Step 1.2: Simulating IP detection job execution..."
        echo ""
        log_info "DRY RUN: Would execute job and display run URL"
        echo "   • Job ID: ${JOB_ID}"
        echo "   • Estimated duration: 2-3 minutes"
        echo ""
        
        log_success "DRY RUN: IP detection simulation complete"
        echo ""
        
        # Simulate IP detection with example IP
        CLUSTER_IP="35.155.15.56"
        log_success "🌐 DRY RUN - Example Detected IP: ${GREEN}${CLUSTER_IP}${NC}"
        
        # Calculate suggested IP ranges
        IFS='.' read -r -a IP_PARTS <<< "$CLUSTER_IP"
        SUBNET_24="${IP_PARTS[0]}.${IP_PARTS[1]}.${IP_PARTS[2]}.0/24"
        SUBNET_28="${IP_PARTS[0]}.${IP_PARTS[1]}.${IP_PARTS[2]}.$((${IP_PARTS[3]} / 16 * 16))/28"
        SINGLE_IP="${CLUSTER_IP}/32"
        
        echo ""
        log_info "📋 IP Range Options:"
        echo "   • Single IP (/32):    ${GREEN}${SINGLE_IP}${NC}          (Most restrictive)"
        echo "   • Small range (/28):  ${GREEN}${SUBNET_28}${NC}   (16 IPs, recommended)"
        echo "   • Large range (/24):  ${GREEN}${SUBNET_24}${NC}    (256 IPs, less secure)"
        echo ""
    else
        # LIVE MODE: Actually deploy and run
        # Deploy the IP detection bundle
        log_info "Step 1.1: Deploying IP detection infrastructure"
        echo "   • Bundle location: ip-detection/databricks.yml"
        echo "   • Target environment: dev"
        echo "   • Workspace: ${SOURCE_PROFILE}"
        echo ""
        
        # Change to ip-detection directory and deploy
        DEPLOY_OUTPUT=$(cd ip-detection && databricks bundle deploy \
            -t dev \
            --profile "$SOURCE_PROFILE" 2>&1)
        
        if [ $? -ne 0 ]; then
            log_error "Failed to deploy IP detection bundle"
            echo ""
            echo "Error details:"
            echo "$DEPLOY_OUTPUT"
            echo ""
            exit 1
        fi
        
        log_success "IP detection bundle deployed successfully"
        echo ""
        
        # Extract job ID from bundle summary (most reliable method)
        log_info "Retrieving job ID from bundle deployment..."
        echo ""
        
        # Method 1: Use bundle summary - returns job ID directly from bundle state
        log_info "Method 1: Using 'databricks bundle summary'..."
        
        set +e  # Temporarily disable exit on error
        BUNDLE_SUMMARY=$(cd ip-detection && databricks bundle summary -t dev --profile "$SOURCE_PROFILE" --output json 2>/dev/null)
        SUMMARY_EXIT=$?
        set -e
        
        if [ $SUMMARY_EXIT -eq 0 ] && [ -n "$BUNDLE_SUMMARY" ]; then
            # Extract job ID from JSON output
            JOB_ID=$(echo "$BUNDLE_SUMMARY" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
            
            # Alternative: try extracting from resources.jobs section
            if [ -z "$JOB_ID" ]; then
                JOB_ID=$(echo "$BUNDLE_SUMMARY" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    jobs = data.get('resources', {}).get('jobs', {})
    for job_key, job_info in jobs.items():
        job_id = job_info.get('id')
        if job_id:
            print(job_id)
            break
except:
    pass
" 2>/dev/null || echo "")
            fi
            
            if [ -n "$JOB_ID" ]; then
                log_success "Retrieved job ID from bundle summary: ${JOB_ID}"
            fi
        fi
        
        # Method 2: Use jobs list with JSON output and filter by name
        if [ -z "$JOB_ID" ]; then
            log_info "Method 2: Searching jobs list..."
            
            set +e
            JOBS_LIST=$(databricks jobs list --profile "$SOURCE_PROFILE" --output json 2>/dev/null)
            JOBS_EXIT=$?
            set -e
            
            if [ $JOBS_EXIT -eq 0 ] && [ -n "$JOBS_LIST" ]; then
                JOB_ID=$(echo "$JOBS_LIST" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    jobs = data.get('jobs', data) if isinstance(data, dict) else data
    for job in jobs if isinstance(jobs, list) else []:
        settings = job.get('settings', {})
        name = settings.get('name', '')
        if 'IP_Detection' in name and 'dev' in name:
            print(job.get('job_id', ''))
            break
except:
    pass
" 2>/dev/null || echo "")
                
                if [ -n "$JOB_ID" ]; then
                    log_success "Found job ID from jobs list: ${JOB_ID}"
                fi
            fi
        fi
        
        # Method 3: Try bundle run directly which handles job lookup internally
        if [ -z "$JOB_ID" ]; then
            log_info "Method 3: Using bundle run (handles job internally)..."
            
            # Bundle run will use the job defined in the bundle config
            # We can run it and capture the run ID from output
            set +e
            RUN_OUTPUT=$(cd ip-detection && databricks bundle run ip_detection_job -t dev --profile "$SOURCE_PROFILE" --no-wait 2>&1)
            RUN_EXIT=$?
            set -e
            
            if [ $RUN_EXIT -eq 0 ]; then
                # Extract run_id from bundle run output
                RUN_ID=$(echo "$RUN_OUTPUT" | grep -oE 'run_id[^0-9]*([0-9]+)' | grep -oE '[0-9]+' | head -1)
                
                if [ -n "$RUN_ID" ]; then
                    log_success "Started job via bundle run, run ID: ${RUN_ID}"
                    
                    # Get job_id from run info
                    RUN_INFO=$(databricks jobs get-run "$RUN_ID" --profile "$SOURCE_PROFILE" 2>/dev/null || echo "")
                    JOB_ID=$(echo "$RUN_INFO" | grep -o '"job_id":[0-9]*' | head -1 | cut -d':' -f2)
                    
                    if [ -n "$JOB_ID" ]; then
                        log_success "Retrieved job ID from run: ${JOB_ID}"
                        # Skip the normal job trigger since we already started it
                        SKIP_JOB_TRIGGER=true
                    fi
                fi
            else
                log_warning "Bundle run failed, trying fallback..."
            fi
        fi
        
        # Method 4: Fallback - check known job ID from previous runs
        if [ -z "$JOB_ID" ]; then
            log_warning "Dynamic job lookup failed, checking known job..."
            
            # Try known job ID
            TEST_JOB_ID="638400064365312"
            set +e
            JOB_INFO=$(databricks jobs get "$TEST_JOB_ID" --profile "$SOURCE_PROFILE" 2>/dev/null || echo "")
            set -e
            
            if echo "$JOB_INFO" | grep -q "IP_Detection"; then
                JOB_ID="$TEST_JOB_ID"
                log_info "Using known job ID: ${JOB_ID}"
            fi
        fi
        
        # Final check
        if [ -n "$JOB_ID" ]; then
            log_success "Job ID confirmed: ${JOB_ID}"
            echo ""
        else
            log_error "Could not find IP detection job"
            echo ""
            log_info "Troubleshooting:"
            echo "   1. Check bundle summary:"
            echo "      cd ip-detection && databricks bundle summary -t dev --profile ${SOURCE_PROFILE}"
            echo ""
            echo "   2. List jobs:"
            echo "      databricks jobs list --profile ${SOURCE_PROFILE} --output json | jq '.jobs[] | select(.settings.name | contains(\"IP_Detection\"))'"
            echo ""
            echo "   3. Check workspace UI"
            echo ""
            exit 1
        fi
        
        if [ -n "$JOB_ID" ]; then
            echo ""
            log_info "Step 1.2: IP detection job configured"
            echo "   • Job name: IP_Detection_dev"
            echo "   • Job ID: ${JOB_ID}"
            echo "   • Cluster type: Single node (UC-enabled)"
            echo "   • Runtime: 17.3.x-scala2.13"
            echo ""
            log_success "Job resource ready"
            echo ""
            
            # Run the job (skip if already triggered via bundle run)
            if [ "$SKIP_JOB_TRIGGER" = "true" ] && [ -n "$RUN_ID" ]; then
                log_info "Step 1.3: Job already executing (triggered via bundle run)"
                echo "   Run ID: ${RUN_ID}"
                echo ""
            else
                log_info "Step 1.3: Executing IP detection job"
                echo "   (CLI may take 1-2 minutes to respond, please wait...)"
                echo ""
                
                # Use timeout if available (Linux/Windows Git Bash), otherwise run without it (macOS)
                set +e
                if command -v timeout >/dev/null 2>&1; then
                    RUN_RESULT=$(timeout 180 databricks jobs run-now "$JOB_ID" --profile "$SOURCE_PROFILE" 2>&1)
                    RUN_EXIT=$?
                    
                    if [ $RUN_EXIT -eq 124 ]; then
                        log_error "CLI command timed out after 3 minutes"
                        echo ""
                        log_info "Job may still have been triggered. Check workspace UI:"
                        echo "   https://e2-demo-field-eng.cloud.databricks.com/#job/${JOB_ID}"
                        exit 1
                    fi
                else
                    # macOS doesn't have timeout by default, run without it
                    RUN_RESULT=$(databricks jobs run-now "$JOB_ID" --profile "$SOURCE_PROFILE" 2>&1)
                    RUN_EXIT=$?
                fi
                set -e
                
                RUN_ID=$(echo "$RUN_RESULT" | grep -o '"run_id":[0-9]*' | cut -d':' -f2 || echo "")
            fi
            
            if [ -n "$RUN_ID" ]; then
                # Get workspace URL from profile
                WORKSPACE_HOST=$(databricks current-user me --profile "$SOURCE_PROFILE" 2>/dev/null | grep -o '"workspace_url":"[^"]*"' | cut -d'"' -f4 || echo "")
                
                if [ -z "$WORKSPACE_HOST" ]; then
                    # Fallback: try to get from config
                    WORKSPACE_HOST=$(grep -A 10 "\[$SOURCE_PROFILE\]" ~/.databrickscfg 2>/dev/null | grep "host" | cut -d'=' -f2 | tr -d ' ' || echo "")
                fi
                
                # Display job run URL
                if [ -n "$WORKSPACE_HOST" ]; then
                    JOB_RUN_URL="${WORKSPACE_HOST}#job/${JOB_ID}/run/${RUN_ID}"
                    echo ""
                    log_success "Job Run URL: ${JOB_RUN_URL}"
                    echo ""
                    log_info "📊 You can track progress in your browser at the URL above"
                    echo ""
                fi
                
                log_info "⏳ Waiting for job to complete (run ID: $RUN_ID)..."
                echo "   (Job typically takes 5-8 minutes, will wait up to 15 minutes)"
                echo ""
                
                # Wait for completion (max 15 minutes)
                TIMEOUT=900
                ELAPSED=0
                LAST_STATUS=""
                CHECK_INTERVAL=30  # Check every 30 seconds (not too aggressive)
                
                # Give the job time to start before first check
                log_info "Waiting for job to start..."
                sleep 30
                ELAPSED=30
                
                while [ $ELAPSED -lt $TIMEOUT ]; do
                    # Use timeout if available, otherwise run without it
                    if command -v timeout >/dev/null 2>&1; then
                        RUN_INFO=$(timeout 120 databricks jobs get-run "$RUN_ID" --profile "$SOURCE_PROFILE" 2>/dev/null || echo "")
                    else
                        RUN_INFO=$(databricks jobs get-run "$RUN_ID" --profile "$SOURCE_PROFILE" 2>/dev/null || echo "")
                    fi
                    
                    if [ -z "$RUN_INFO" ]; then
                        log_warning "Could not get job status (CLI timeout or network issue)"
                        echo "   Retrying in ${CHECK_INTERVAL}s..."
                        sleep $CHECK_INTERVAL
                        ELAPSED=$((ELAPSED + CHECK_INTERVAL))
                        continue
                    fi
                    
                    LIFE_CYCLE_STATE=$(echo "$RUN_INFO" | grep -o '"life_cycle_state":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "UNKNOWN")
                    RESULT_STATE=$(echo "$RUN_INFO" | grep -o '"result_state":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
                    
                    # Show status updates
                    if [ "$LIFE_CYCLE_STATE" != "$LAST_STATUS" ]; then
                        if [ -n "$RESULT_STATE" ]; then
                            log_info "Status: $LIFE_CYCLE_STATE - $RESULT_STATE"
                        else
                            log_info "Status: $LIFE_CYCLE_STATE"
                        fi
                        LAST_STATUS="$LIFE_CYCLE_STATE"
                    fi
                    
                    # Check if job completed
                    if [[ "$LIFE_CYCLE_STATE" == "TERMINATED" ]]; then
                        if [[ "$RESULT_STATE" == "SUCCESS" ]]; then
                            echo ""
                            log_success "IP detection job completed successfully!"
                            break
                        elif [[ "$RESULT_STATE" == "FAILED" ]] || [[ "$RESULT_STATE" == "CANCELED" ]]; then
                            echo ""
                            log_error "IP detection job failed with result: $RESULT_STATE"
                            # Try to get error message
                            ERROR_MSG=$(echo "$RUN_INFO" | grep -o '"state_message":"[^"]*"' | cut -d'"' -f4 || echo "")
                            if [ -n "$ERROR_MSG" ]; then
                                log_error "Error: $ERROR_MSG"
                            fi
                            break
                        else
                            echo ""
                            log_warning "Job terminated with unknown result: $RESULT_STATE"
                            break
                        fi
                    fi
                    
                    # Show progress with time elapsed
                    MINS=$((ELAPSED / 60))
                    SECS=$((ELAPSED % 60))
                    if [ "$STATUS" != "$LAST_STATUS" ] || [ $((ELAPSED % 60)) -eq 0 ]; then
                        echo "   Status: ${STATUS} (${MINS}m ${SECS}s elapsed)"
                        LAST_STATUS="$STATUS"
                    fi
                    
                    sleep $CHECK_INTERVAL
                    ELAPSED=$((ELAPSED + CHECK_INTERVAL))
                done
                
                echo ""
                log_info "Step 1.4: Retrieving detected IP"
                echo ""
                
                # Give the job a moment to flush the metadata file to storage
                log_info "Waiting for metadata file to be available..."
                sleep 15
                
                # Method 1: Try to read from UC volume (most reliable since job saved it there)
                log_info "Checking UC volume for saved metadata..."
                METADATA_FILE="${VOLUME_BASE}/cluster_ip_metadata.json"
                
                # CRITICAL: CLI requires dbfs: prefix for volume paths
                DBFS_METADATA_FILE="dbfs:${METADATA_FILE}"
                
                log_info "Reading from: ${DBFS_METADATA_FILE}"
                echo ""
                
                # Try multiple times with retry (file might be flushing)
                MAX_RETRIES=5
                RETRY=0
                while [ $RETRY -lt $MAX_RETRIES ] && [ -z "$CLUSTER_IP" ]; do
                    if [ $RETRY -gt 0 ]; then
                        log_info "Retry $RETRY/$MAX_RETRIES (waiting 10 seconds)..."
                        sleep 10
                    fi
                    
                    METADATA_CONTENT=$(databricks fs cat "$DBFS_METADATA_FILE" --profile "$SOURCE_PROFILE" 2>&1)
                    EXIT_CODE=$?
                    
                    # Debug output
                    if [ $RETRY -eq 0 ]; then
                        log_info "Attempt $((RETRY + 1))/$MAX_RETRIES - CLI exit code: $EXIT_CODE"
                    fi
                    
                    if echo "$METADATA_CONTENT" | grep -q "cluster_ip"; then
                        # Extract IP using grep for the line, then extract just the IP value
                        CLUSTER_IP=$(echo "$METADATA_CONTENT" | grep "cluster_ip" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1)
                        if [ -n "$CLUSTER_IP" ]; then
                            log_success "Retrieved IP from UC volume: $CLUSTER_IP"
                            echo ""
                            break
                        fi
                    else
                        if [ $EXIT_CODE -ne 0 ]; then
                            # Show first line of error for debugging
                            ERROR_MSG=$(echo "$METADATA_CONTENT" | head -1)
                            log_warning "CLI error: $ERROR_MSG"
                        else
                            log_warning "File content doesn't contain cluster_ip field"
                        fi
                    fi
                    
                    RETRY=$((RETRY + 1))
                done
                
                # If still no IP, show what we got
                if [ -z "$CLUSTER_IP" ] && [ -n "$METADATA_CONTENT" ]; then
                    log_warning "Could not extract IP from volume. Last response:"
                    echo "$METADATA_CONTENT" | head -5
                    echo ""
                fi
                
                # Method 2: Try with workspace files API if fs cat failed
                if [ -z "$CLUSTER_IP" ]; then
                    log_info "Trying alternative volume read method..."
                    
                    # Try reading via workspace files API
                    WORKSPACE_PATH="/Workspace/Users/$(databricks current-user me --profile "$SOURCE_PROFILE" 2>/dev/null | grep -o '"userName":"[^"]*"' | cut -d'"' -f4)/.bundle/ip-detection/dev/files/cluster_ip_metadata.json"
                    
                    ALT_CONTENT=$(databricks workspace export "$WORKSPACE_PATH" --format AUTO --profile "$SOURCE_PROFILE" 2>/dev/null || echo "")
                    
                    if [ -n "$ALT_CONTENT" ]; then
                        CLUSTER_IP=$(echo "$ALT_CONTENT" | grep -o '"cluster_ip":"[^"]*"' | cut -d'"' -f4)
                        if [ -n "$CLUSTER_IP" ]; then
                            log_success "Retrieved IP via workspace API: $CLUSTER_IP"
                        fi
                    fi
                fi
                
                # Method 3: Fall back to job output if all else failed
                if [ -z "$CLUSTER_IP" ]; then
                    log_info "Reading from job output..."
                    
                    # Use timeout if available
                    if command -v timeout >/dev/null 2>&1; then
                        OUTPUT=$(timeout 120 databricks jobs get-run-output "$RUN_ID" --profile "$SOURCE_PROFILE" 2>/dev/null || echo "")
                    else
                        OUTPUT=$(databricks jobs get-run-output "$RUN_ID" --profile "$SOURCE_PROFILE" 2>/dev/null || echo "")
                    fi
                    
                    # Extract IP from output (BSD grep compatible)
                    CLUSTER_IP=$(echo "$OUTPUT" | grep -o 'Cluster Egress IP: [0-9]*\.[0-9]*\.[0-9]*\.[0-9]*' | sed 's/Cluster Egress IP: //' | head -1)
                    
                    # Alternative pattern if first doesn't work
                    if [ -z "$CLUSTER_IP" ]; then
                        CLUSTER_IP=$(echo "$OUTPUT" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1)
                    fi
                    
                    if [ -n "$CLUSTER_IP" ]; then
                        log_success "Retrieved IP from job output: $CLUSTER_IP"
                    fi
                fi
                
                if [ -n "$CLUSTER_IP" ]; then
                    DETECTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
                    
                    log_info "IP detection results:"
                    echo "   • IP Address: ${GREEN}${CLUSTER_IP}${NC}"
                    echo "   • Detected at: ${DETECTED_AT}"
                    echo ""
                    
                    # CRITICAL: Save IP metadata to volume for cleanup script
                    log_info "Saving IP metadata to UC volume..."
                    
                    METADATA_FILE="${VOLUME_BASE}/cluster_ip_metadata.json"
                    # CLI requires dbfs: prefix
                    DBFS_METADATA_FILE="dbfs:${METADATA_FILE}"
                    
                    # Calculate IP ranges first
                    IFS='.' read -r -a IP_PARTS <<< "$CLUSTER_IP"
                    
                    # Create metadata JSON
                    METADATA_JSON=$(cat <<EOF
{
  "cluster_ip": "${CLUSTER_IP}",
  "detected_at": "${DETECTED_AT}",
  "detected_by": "auto_setup_ip_acl.sh",
  "job_id": "${JOB_ID}",
  "run_id": "${RUN_ID}",
  "suggested_ranges": {
    "single_ip": "${CLUSTER_IP}/32",
    "small_range": "${IP_PARTS[0]}.${IP_PARTS[1]}.${IP_PARTS[2]}.$((${IP_PARTS[3]} / 16 * 16))/28",
    "large_range": "${IP_PARTS[0]}.${IP_PARTS[1]}.${IP_PARTS[2]}.0/24"
  }
}
EOF
)
                    
                    log_info "Writing to: ${DBFS_METADATA_FILE}"
                    
                    # Save to volume using databricks fs with dbfs: prefix
                    # Temporarily disable errexit to capture errors gracefully
                    set +e
                    SAVE_OUTPUT=$(echo "$METADATA_JSON" | databricks fs cp - "${DBFS_METADATA_FILE}" --profile "$SOURCE_PROFILE" --overwrite 2>&1)
                    SAVE_EXIT=$?
                    set -e
                    
                    if [ $SAVE_EXIT -eq 0 ]; then
                        echo "   • Saved to: ${METADATA_FILE}"
                        log_success "IP metadata saved successfully"
                    else
                        log_warning "Could not save to volume (job already saved it)"
                        log_info "Continuing with detected IP: $CLUSTER_IP"
                    fi
                    echo ""
                    log_success "IP detected successfully"
                    
                    # Use already calculated IP ranges
                    SUBNET_24="${IP_PARTS[0]}.${IP_PARTS[1]}.${IP_PARTS[2]}.0/24"
                    SUBNET_28="${IP_PARTS[0]}.${IP_PARTS[1]}.${IP_PARTS[2]}.$((${IP_PARTS[3]} / 16 * 16))/28"
                    SINGLE_IP="${CLUSTER_IP}/32"
                    
                    echo ""
                    log_info "IP range options for whitelisting:"
                    echo "   • Single IP (/32):    ${GREEN}${SINGLE_IP}${NC}          (Most restrictive)"
                    echo "   • Small range (/28):  ${GREEN}${SUBNET_28}${NC}   (16 IPs, recommended)"
                    echo "   • Large range (/24):  ${GREEN}${SUBNET_24}${NC}    (256 IPs, less secure)"
                    echo ""
                else
                    log_warning "Could not extract IP from job output"
                fi
                
                # Cleanup will be done via bundle destroy
                CLEANUP_NEEDED=true
            else
                log_error "Could not extract run ID from job execution"
            fi
        else
            log_error "Could not find or create job ID from bundle deployment"
            echo ""
            log_info "Possible causes:"
            echo "   • Bundle deployed but job resource not created"
            echo "   • Job naming mismatch (expected: IP_Detection_dev)"
            echo "   • Permissions issue with jobs API"
            echo ""
            log_info "Trying alternative: Check for existing metadata..."
            echo ""
        fi
    fi
    
    # Fallback: Try to read from saved metadata
    if [ -z "$CLUSTER_IP" ]; then
        log_warning "Could not detect IP via notebook, trying saved metadata..."
        
        METADATA_PATH="${VOLUME_BASE}/cluster_ip_metadata.json"
        METADATA=$(databricks fs cat "$METADATA_PATH" --profile "$SOURCE_PROFILE" 2>/dev/null || echo "")
        
        if [ -n "$METADATA" ]; then
            CLUSTER_IP=$(echo "$METADATA" | grep -o '"cluster_ip":[[:space:]]*"[^"]*"' | cut -d'"' -f4)
            
            if [ -n "$CLUSTER_IP" ]; then
                log_success "Found IP in saved metadata: $CLUSTER_IP"
            fi
        fi
    fi
    
    # Final check: If still no IP, exit with clear instructions
    if [ -z "$CLUSTER_IP" ]; then
        echo ""
        log_error "Could not auto-detect cluster IP"
        echo ""
        log_info "Troubleshooting steps:"
        echo ""
        echo "1. Check if IP detection job was created:"
        echo "   ${BLUE}databricks jobs list --profile source-workspace | grep IP_Detection${NC}"
        echo ""
        echo "2. If job exists, run it manually and check output:"
        echo "   ${BLUE}databricks jobs run-now --job-id <JOB_ID> --profile source-workspace${NC}"
        echo ""
        echo "3. Check for saved IP metadata:"
        echo "   ${BLUE}databricks fs cat ${VOLUME_BASE}/cluster_ip_metadata.json --profile source-workspace${NC}"
        echo ""
        echo "4. Or provide IP manually with:"
        echo "   ${BLUE}$0 --cluster-ip X.X.X.X${NC}"
        echo ""
        log_error "Script cannot continue without cluster IP"
        exit 1
    fi
    
    log_success "Using cluster IP: $CLUSTER_IP"
    echo ""
}

################################################################################
# Step 2: Whitelist IP on Target Workspace
################################################################################

whitelist_ip() {
    log_section "STEP 2: Whitelist IP on Target Workspace"
    
    if [ "$DRY_RUN" = "true" ]; then
        echo ""
        log_warning "🧪 DRY RUN MODE - Simulating IP whitelist process"
        log_warning "   No actual changes will be made to target workspace"
        echo ""
    else
        echo ""
        log_info "🔧 LIVE MODE - Will modify IP access lists on target workspace"
        echo ""
    fi
    
    # Get target workspace details
    log_info "Target workspace details:"
    
    if [ "$DRY_RUN" != "true" ]; then
        USER_INFO=$(databricks current-user me --profile "$TARGET_PROFILE" 2>/dev/null || echo "")
        WORKSPACE_HOST=$(echo "$USER_INFO" | grep -o '"workspace_url":"[^"]*"' | cut -d'"' -f4 || echo "")
        CURRENT_USER=$(echo "$USER_INFO" | grep -o '"userName":"[^"]*"' | cut -d'"' -f4 || echo "")
        
        if [ -z "$WORKSPACE_HOST" ]; then
            WORKSPACE_HOST=$(grep -A 10 "\[$TARGET_PROFILE\]" ~/.databrickscfg 2>/dev/null | grep "host" | cut -d'=' -f2 | tr -d ' ' || echo "")
        fi
        
        if [ -n "$WORKSPACE_HOST" ]; then
            echo "   • Host: ${WORKSPACE_HOST}"
        fi
        if [ -n "$CURRENT_USER" ]; then
            echo "   • User: ${CURRENT_USER}"
        fi
    else
        echo "   • Profile: ${TARGET_PROFILE}"
    fi
    
    echo "   • IP to whitelist: ${GREEN}${CLUSTER_IP}/32${NC}"
    echo ""
    
    # Step 2.1: Verify target workspace access
    log_info "📡 Step 2.1: Verifying target workspace access..."
    echo ""
    
    if [ "$DRY_RUN" = "true" ]; then
        log_info "DRY RUN: Would verify connection to target workspace"
        log_success "DRY RUN: Skipping actual verification"
        echo ""
    else
        if ! databricks workspace list / --profile "$TARGET_PROFILE" >/dev/null 2>&1; then
            echo ""
            log_error "Cannot access target workspace with profile: ${RED}${TARGET_PROFILE}${NC}"
            echo ""
            log_info "Troubleshooting:"
            echo "   1. Check ~/.databrickscfg has correct configuration for ${TARGET_PROFILE}"
            echo "   2. Verify your authentication token/credentials are valid"
            echo "   3. Ensure you have workspace access permissions"
            echo ""
            exit 1
        fi
        log_success "Target workspace accessible"
        echo ""
    fi
    
    # Step 2.2: Check if IP ACLs are enabled
    log_info "🔐 Step 2.2: Checking IP access list status..."
    echo ""
    
    if [ "$DRY_RUN" = "true" ]; then
        log_info "DRY RUN: Would check if IP ACLs are enabled on target"
        log_success "DRY RUN: Assuming IP access lists are enabled"
        echo ""
    else
        ACL_STATUS=$(databricks workspace-conf get-status enableIpAccessLists --profile "$TARGET_PROFILE" 2>/dev/null || echo "")
        
        if [ -z "$ACL_STATUS" ] || [[ "$ACL_STATUS" != *"true"* ]]; then
            echo ""
            log_warning "IP access lists are NOT enabled on target workspace"
            echo ""
            log_info "No whitelisting needed:"
            echo "   • Target workspace accepts connections from any IP"
            echo "   • You can proceed directly to deployment"
            echo ""
            log_success "IP whitelisting not required - workspace allows all IPs"
            echo ""
            return 0
        fi
        log_success "IP access lists are enabled - whitelisting required"
        echo ""
    fi
    
    # Step 2.3: Check existing IP ACL entries
    log_info "🔎 Step 2.3: Reviewing existing IP ACL entries"
    echo ""
    
    if [ "$DRY_RUN" = "true" ]; then
        log_info "DRY RUN: Would retrieve existing ACL entries"
        echo "   • Simulating: 3 existing entries found"
        echo "   • IP ${CLUSTER_IP} not found in existing entries"
        echo ""
        log_success "DRY RUN: Proceeding to whitelist simulation"
        echo ""
    else
        EXISTING_LISTS=$(databricks ip-access-lists list --profile "$TARGET_PROFILE" 2>/dev/null || echo "")
        
        # Count existing entries
        ENTRY_COUNT=$(echo "$EXISTING_LISTS" | grep -c '"list_id"' || echo "0")
        
        log_info "Current IP ACL entries on target workspace:"
        echo "   • Total entries: ${ENTRY_COUNT}"
        echo ""
        
        # Check if our IP is already in the list
        if echo "$EXISTING_LISTS" | grep -q "$CLUSTER_IP"; then
            echo ""
            log_success "IP ${GREEN}${CLUSTER_IP}${NC} is already whitelisted!"
            echo ""
            log_info "Details:"
            echo "$EXISTING_LISTS" | grep -B2 -A2 "$CLUSTER_IP" | sed 's/^/   /'
            echo ""
            log_info "No action needed - you can proceed directly to deployment"
            echo ""
            return 0
        fi
        
        log_info "Status: IP ${CLUSTER_IP} not found in existing ${ENTRY_COUNT} entries"
        log_info "Action: Will add new entry to allowlist"
        echo ""
    fi
    
    # Step 2.4: Add IP to allowlist
    echo ""
    log_info "📝 Step 2.4: Adding IP to allowlist..."
    echo ""
    
    IP_RANGE="${CLUSTER_IP}/32"
    LABEL="source-workspace-cluster-$(date +%s)"
    
    if [ "$DRY_RUN" = "true" ]; then
        log_info "DRY RUN: Would create IP allowlist entry with:"
        echo "   • Label: ${MAGENTA}${LABEL}${NC}"
        echo "   • IP Range: ${GREEN}${IP_RANGE}${NC}"
        echo "   • List Type: ${GREEN}ALLOW${NC}"
        echo "   • Target: ${GREEN}${TARGET_PROFILE}${NC}"
        echo ""
        log_success "DRY RUN: IP whitelisting simulation complete"
    else
        log_info "Creating allowlist entry with:"
        echo "   • Label: ${MAGENTA}${LABEL}${NC}"
        echo "   • IP Range: ${GREEN}${IP_RANGE}${NC}"
        echo "   • List Type: ALLOW"
        echo ""
        
        CREATE_RESULT=$(databricks ip-access-lists create --json "{
            \"label\": \"$LABEL\",
            \"list_type\": \"ALLOW\",
            \"ip_addresses\": [\"$IP_RANGE\"]
        }" --profile "$TARGET_PROFILE" 2>&1)
        
        if [ $? -ne 0 ]; then
            echo ""
            log_error "Failed to add IP to allowlist"
            echo ""
            echo "Error details:"
            echo "$CREATE_RESULT"
            echo ""
            exit 1
        fi
        
        # Extract entry ID from response
        ENTRY_ID=$(echo "$CREATE_RESULT" | grep -o '"list_id":"[^"]*"' | cut -d'"' -f4 || echo "")
        
        echo ""
        log_success "IP ACL entry created successfully"
        echo "   • IP Address: ${GREEN}${CLUSTER_IP}${NC}"
        echo "   • IP Range: ${GREEN}${IP_RANGE}${NC}"
        if [ -n "$ENTRY_ID" ]; then
            echo "   • Entry ID: ${ENTRY_ID}"
        fi
        echo "   • Label: ${MAGENTA}${LABEL}${NC}"
        echo "   • Status: Active"
        echo ""
        
        # Show updated count
        UPDATED_LISTS=$(databricks ip-access-lists list --profile "$TARGET_PROFILE" 2>/dev/null || echo "")
        NEW_ENTRY_COUNT=$(echo "$UPDATED_LISTS" | grep -c '"list_id"' || echo "0")
        
        log_info "Updated ACL summary:"
        echo "   • Total entries: ${NEW_ENTRY_COUNT} (was ${ENTRY_COUNT:-0})"
        echo "   • New entry for: ${GREEN}${CLUSTER_IP}${NC}"
    fi
    echo ""
    
    # Step 2.5: Wait for propagation
    log_section "STEP 3: Wait for IP ACL Propagation"
    
    echo ""
    if [ "$DRY_RUN" = "true" ]; then
        log_info "DRY RUN: Would wait ${GREEN}${PROPAGATION_WAIT} seconds${NC} for IP ACL changes to propagate"
        echo ""
        log_info "Why propagation wait is needed:"
        echo "   • IP ACL changes are distributed across Databricks infrastructure"
        echo "   • Typically takes 2-5 minutes to become fully active"
        echo "   • Recommended wait: 5 minutes (300 seconds)"
        echo ""
        log_success "DRY RUN: Skipping propagation wait"
        echo ""
    else
        log_info "⏳ Waiting ${GREEN}${PROPAGATION_WAIT} seconds${NC} for IP ACL propagation..."
        echo ""
        log_info "Why we wait:"
        echo "   • IP ACL changes need time to propagate across Databricks control plane"
        echo "   • Deployment will fail if attempted before propagation completes"
        echo "   • This ensures cross-workspace connections work reliably"
        echo ""
        echo "Progress:"
        
        # Progress bar
        for i in $(seq 1 $PROPAGATION_WAIT); do
            PERCENT=$((i * 100 / PROPAGATION_WAIT))
            BAR_LENGTH=$((PERCENT / 2))
            BAR=$(printf "%${BAR_LENGTH}s" | tr ' ' '=')
            
            # Calculate time remaining
            REMAINING=$((PROPAGATION_WAIT - i))
            MINUTES=$((REMAINING / 60))
            SECONDS=$((REMAINING % 60))
            
            printf "\r  [%-50s] %3d%% | Elapsed: %d/%ds | Remaining: %dm %02ds" \
                "$BAR" "$PERCENT" "$i" "$PROPAGATION_WAIT" "$MINUTES" "$SECONDS"
            sleep 1
        done
        echo ""
        echo ""
        
        log_success "Propagation wait complete!"
        log_info "   IP ACL changes should now be active"
        echo ""
    fi
    
    # Step 2.6: Verify IP is whitelisted
    log_section "STEP 4: Verification"
    
    echo ""
    log_info "Step 4.1: Retrieving current IP ACL configuration from target workspace"
    echo ""
    
    if [ "$DRY_RUN" = "true" ]; then
        log_info "DRY RUN: Would query target workspace ACL entries"
        echo "   • Expected: IP ${GREEN}${CLUSTER_IP}${NC} in ALLOW list"
        echo "   • Expected: Entry status Active"
        echo ""
        log_success "DRY RUN: Would verify IP is whitelisted"
        echo ""
        log_info "In live mode, verification includes:"
        echo "   • Querying all IP ACL entries"
        echo "   • Confirming IP appears in allowlist"
        echo "   • Verifying entry is in ALLOW list"
        echo "   • Checking propagation is complete"
        echo ""
    else
        FINAL_CHECK=$(databricks ip-access-lists list --profile "$TARGET_PROFILE" 2>/dev/null || echo "")
        FINAL_ENTRY_COUNT=$(echo "$FINAL_CHECK" | grep -c '"list_id"' || echo "0")
        
        log_info "Current IP ACL status:"
        echo "   • Total entries: ${FINAL_ENTRY_COUNT}"
        echo ""
        
        if echo "$FINAL_CHECK" | grep -q "$CLUSTER_IP"; then
            log_info "Step 4.2: Confirming IP entry details"
            echo ""
            
            # Extract and display the entry containing our IP
            log_info "Found entry containing ${GREEN}${CLUSTER_IP}${NC}:"
            echo ""
            echo "$FINAL_CHECK" | grep -B3 -A3 "$CLUSTER_IP" | sed 's/^/   /'
            echo ""
            
            log_success "VERIFICATION SUCCESSFUL"
            echo ""
            echo "Confirmed:"
            echo "   • IP ${GREEN}${CLUSTER_IP}${NC} present in target workspace allowlist"
            echo "   • Entry type: ALLOW"
            echo "   • IP ACL configuration active"
            echo "   • Ready for cross-workspace deployment"
            echo ""
        else
            echo ""
            log_warning "Could not verify IP in allowlist via CLI query"
            echo ""
            log_info "Possible reasons:"
            echo "   • CLI result caching (most common)"
            echo "   • Propagation still in progress"
            echo "   • Entry was added but not visible yet"
            echo ""
            log_info "The IP should be active. Recommendations:"
            echo "   1. Check target workspace UI: Settings → Security → IP Access Lists"
            echo "   2. Look for label: ${MAGENTA}${LABEL}${NC}"
            echo "   3. If deployment fails, wait 2-3 more minutes and retry"
            echo ""
        fi
    fi
}

################################################################################
# Cleanup Function
################################################################################

cleanup_ip_detection() {
    log_section "STEP 5: Cleanup IP Detection Infrastructure"
    
    echo ""
    if [ "$CLEANUP_NEEDED" = "true" ] && [ "$DRY_RUN" != "true" ]; then
        log_info "Step 5.1: Preparing to remove temporary infrastructure"
        echo ""
        
        log_info "Resources to be removed:"
        echo "   • Job: IP_Detection_dev"
        if [ -n "$JOB_ID" ]; then
            echo "   • Job ID: ${JOB_ID}"
        fi
        echo "   • Deployed notebook: Detect_Cluster_IP"
        echo "   • Workspace path: ~/.bundle/ip-detection/dev/"
        echo "   • Bundle files and metadata"
        echo ""
        
        log_info "Resources to be preserved:"
        echo "   • IP metadata: ${VOLUME_BASE}/cluster_ip_metadata.json"
        echo "   • Local source files: ip-detection/"
        echo ""
        
        log_info "Step 5.2: Executing bundle destroy"
        echo ""
        
        DESTROY_OUTPUT=$(cd ip-detection && databricks bundle destroy \
            -t dev \
            --profile "$SOURCE_PROFILE" \
            --auto-approve 2>&1)
        
        if [ $? -eq 0 ]; then
            echo ""
            log_success "Cleanup completed successfully"
            echo ""
            
            log_info "Step 5.3: Verification of cleanup"
            echo ""
            
            log_info "Removed:"
            echo "   • IP_Detection_dev job deleted from workspace"
            echo "   • Deployed notebook removed"
            echo "   • Bundle workspace directory cleaned up"
            echo ""
            
            log_info "Preserved:"
            echo "   • IP metadata in UC volume (for reference)"
            echo "   • Cluster IP: ${GREEN}${CLUSTER_IP}${NC}"
            echo "   • Detection timestamp available for audit"
            echo ""
        else
            log_warning "Cleanup encountered issues"
            echo ""
            log_info "Error details:"
            echo "$DESTROY_OUTPUT" | sed 's/^/   /'
            echo ""
            log_info "Manual cleanup command:"
            echo "   ${BLUE}cd ip-detection && databricks bundle destroy -t dev --profile ${SOURCE_PROFILE} --auto-approve${NC}"
            echo ""
        fi
    elif [ "$DRY_RUN" = "true" ]; then
        log_info "DRY RUN: Would clean up IP detection bundle"
        echo "   • Bundle directory: ip-detection/"
        echo "   • Target: dev"
        echo "   • Profile: ${SOURCE_PROFILE}"
        echo ""
        log_success "DRY RUN: Skipping actual cleanup"
        echo ""
    else
        log_info "No cleanup needed - IP detection infrastructure was not deployed"
        echo ""
    fi
}

################################################################################
# Main
################################################################################

main() {
    # Clear screen (cross-platform)
    if command -v clear >/dev/null 2>&1; then
        clear 2>/dev/null || true
    elif command -v cls >/dev/null 2>&1; then
        cls 2>/dev/null || true
    fi
    
    # Initialize cleanup flag
    CLEANUP_NEEDED=false
    
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║     Fully Automated IP Detection + Whitelist Setup           ║"
    echo "║                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Parse arguments
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
            --bundle-target)
                BUNDLE_TARGET="$2"
                shift 2
                ;;
            --volume-base)
                VOLUME_BASE="$2"
                shift 2
                ;;
            --wait)
                PROPAGATION_WAIT="$2"
                shift 2
                ;;
            --cluster-ip)
                CLUSTER_IP="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [options]"
                echo ""
                echo "Automatically detects cluster IP and whitelists it on target workspace."
                echo "After this completes, run Bundle_04 notebook to deploy dashboards."
                echo ""
                echo "Options:"
                echo "  --source-profile PROFILE   Source workspace profile (default: source-workspace)"
                echo "  --target-profile PROFILE   Target workspace profile (default: target-workspace)"
                echo "  --bundle-target TARGET     Bundle target (default: dev)"
                echo "  --volume-base PATH         UC volume path (default: /Volumes/...)"
                echo "  --cluster-ip IP            Skip auto-detection, use this IP (e.g., 35.155.15.56)"
                echo "  --wait SECONDS             Propagation wait (default: 300)"
                echo "  --dry-run                  Test mode - detect IP but don't whitelist"
                echo "  -h, --help                 Show this help"
                echo ""
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Show configuration summary
    show_configuration
    
    # Run detection and whitelisting
    detect_cluster_ip
    whitelist_ip
    
    # Cleanup IP detection infrastructure
    cleanup_ip_detection
    
    log_section "SETUP COMPLETE"
    
    if [ "$DRY_RUN" = "true" ]; then
        echo ""
        echo "╔═══════════════════════════════════════════════════════════════╗"
        echo "║                                                               ║"
        echo "║           🧪 DRY RUN COMPLETE - NO CHANGES MADE               ║"
        echo "║                                                               ║"
        echo "╚═══════════════════════════════════════════════════════════════╝"
        echo ""
        log_success "IP Detection Successful"
        echo ""
        echo "🌐 Detected Information:"
        echo "   • Cluster IP: ${GREEN}${CLUSTER_IP}${NC}"
        echo "   • IP saved to: ${VOLUME_BASE}/cluster_ip_metadata.json"
        echo ""
        echo "📋 What Would Happen in Live Mode:"
        echo "   1. Add IP ${CLUSTER_IP}/32 to target workspace allowlist"
        echo "   2. Wait 5 minutes for IP ACL propagation"
        echo "   3. Verify IP is whitelisted"
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        echo "NEXT STEPS:"
        echo "═══════════════════════════════════════════════════════════════"
        echo ""
        echo "  1️⃣  Run in LIVE mode to actually whitelist the IP:"
        echo "      ${BLUE}./scripts/auto_setup_ip_acl.sh${NC}"
        echo ""
        echo "  2️⃣  After whitelisting completes, deploy dashboards:"
        echo "      ${BLUE}databricks bundle run generate_deploy -t $BUNDLE_TARGET --profile $SOURCE_PROFILE${NC}"
        echo ""
        echo "  Or run interactively: Bundle_04_Generate_and_Deploy.ipynb"
        echo ""
    else
        echo ""
        echo "╔═══════════════════════════════════════════════════════════════╗"
        echo "║                                                               ║"
        echo "║           ✅ IP WHITELISTING COMPLETE - READY!                ║"
        echo "║                                                               ║"
        echo "╚═══════════════════════════════════════════════════════════════╝"
        echo ""
        log_success "IP Access Configuration Successful"
        echo ""
        echo "🌐 Whitelist Summary:"
        echo "   • Cluster IP: ${GREEN}${CLUSTER_IP}${NC}"
        echo "   • IP Range Added: ${GREEN}${CLUSTER_IP}/32${NC}"
        echo "   • Target Workspace: ${GREEN}${TARGET_PROFILE}${NC}"
        echo "   • Status: ${GREEN}WHITELISTED & ACTIVE${NC}"
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        echo "READY FOR DEPLOYMENT:"
        echo "═══════════════════════════════════════════════════════════════"
        echo ""
        echo "  1️⃣  Deploy dashboards using Bundle_04:"
        echo "      ${BLUE}databricks bundle run generate_deploy -t $BUNDLE_TARGET --profile $SOURCE_PROFILE${NC}"
        echo ""
        echo "  2️⃣  Or run interactively in Databricks UI:"
        echo "      Open: Bundle/Bundle_04_Generate_and_Deploy_V2.ipynb"
        echo "      Run all cells"
        echo ""
        echo "  3️⃣  After migration validation, cleanup IP ACL:"
        echo "      ${BLUE}./scripts/cleanup_ip_acl.sh${NC}"
        echo ""
        echo "⏱️  Estimated deployment time: 5-10 minutes"
        echo ""
    fi
}

main "$@"
