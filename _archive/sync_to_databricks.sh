#!/bin/bash

# ============================================================================
# Databricks Workspace Sync Script
# ============================================================================
# Purpose: Sync local notebooks to Databricks workspace
# Profile: e2-demo-field-eng
# Target: /Workspace/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# CONFIGURATION
# ============================================================================

# Databricks profile (from ~/.databrickscfg)
PROFILE="e2-demo-field-eng"

# Workspace details
WORKSPACE_URL="https://e2-demo-field-eng.cloud.databricks.com"
TARGET_PATH="/Workspace/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration"

# Local directory (where this script is located)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Files to sync (notebooks and docs)
FILES_TO_SYNC=(
    "00_Prerequisite_Generation.ipynb"
    "01_Setup_and_Configuration.ipynb"
    "02_Export_and_Transform.ipynb"
    "03_Import_and_Migrate.ipynb"
    "COMPLETE_MIGRATION_GUIDE.md"
    "README.md"
    "catalog_schema_mapping_template.csv"
)

# ============================================================================
# FUNCTIONS
# ============================================================================

print_header() {
    echo -e "${BLUE}============================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if databricks CLI is installed
check_cli() {
    if ! command -v databricks &> /dev/null; then
        print_error "Databricks CLI not found"
        echo ""
        echo "Install it with:"
        echo "  pip install databricks-cli"
        echo ""
        echo "Or:"
        echo "  brew tap databricks/tap"
        echo "  brew install databricks"
        exit 1
    fi
    print_success "Databricks CLI found: $(databricks --version)"
}

# Check if profile exists
check_profile() {
    if ! databricks --profile "$PROFILE" workspace ls / &> /dev/null; then
        print_error "Profile '$PROFILE' not configured or authentication failed"
        echo ""
        echo "Configure profile with:"
        echo "  databricks configure --token --profile $PROFILE"
        echo ""
        echo "You'll be prompted for:"
        echo "  Host: $WORKSPACE_URL"
        echo "  Token: Your PAT token"
        exit 1
    fi
    print_success "Profile '$PROFILE' is valid"
}

# Create target directory in workspace
create_target_dir() {
    print_info "Creating target directory: $TARGET_PATH"
    
    if databricks --profile "$PROFILE" workspace mkdirs "$TARGET_PATH" &> /dev/null; then
        print_success "Target directory ready"
    else
        print_warning "Directory may already exist or couldn't be created"
    fi
}

# Upload a single file
upload_file() {
    local file=$1
    local local_path="$SCRIPT_DIR/$file"
    local remote_path="$TARGET_PATH/$file"
    
    if [ ! -f "$local_path" ]; then
        print_warning "File not found: $file (skipping)"
        return 1
    fi
    
    print_info "Uploading: $file"
    
    # Determine format based on file extension
    local format="AUTO"
    if [[ $file == *.ipynb ]]; then
        format="JUPYTER"
    elif [[ $file == *.py ]]; then
        format="SOURCE"
    fi
    
    # Upload file
    if databricks --profile "$PROFILE" workspace import \
        "$local_path" \
        "$remote_path" \
        --format "$format" \
        --language PYTHON \
        --overwrite &> /dev/null; then
        print_success "✓ $file"
        return 0
    else
        print_error "✗ $file (upload failed)"
        return 1
    fi
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    print_header "DATABRICKS WORKSPACE SYNC"
    
    echo ""
    echo "Configuration:"
    echo "  Profile:     $PROFILE"
    echo "  Workspace:   $WORKSPACE_URL"
    echo "  Target Path: $TARGET_PATH"
    echo "  Local Dir:   $SCRIPT_DIR"
    echo ""
    
    # Pre-flight checks
    print_header "PRE-FLIGHT CHECKS"
    check_cli
    check_profile
    echo ""
    
    # Create target directory
    print_header "PREPARING TARGET DIRECTORY"
    create_target_dir
    echo ""
    
    # Upload files
    print_header "UPLOADING FILES"
    
    local success_count=0
    local fail_count=0
    local skip_count=0
    
    for file in "${FILES_TO_SYNC[@]}"; do
        if upload_file "$file"; then
            ((success_count++))
        elif [ -f "$SCRIPT_DIR/$file" ]; then
            ((fail_count++))
        else
            ((skip_count++))
        fi
    done
    
    echo ""
    print_header "SYNC SUMMARY"
    echo ""
    echo "Results:"
    echo "  ✅ Uploaded:  $success_count files"
    echo "  ❌ Failed:    $fail_count files"
    echo "  ⊘ Skipped:   $skip_count files (not found)"
    echo ""
    
    if [ $success_count -gt 0 ]; then
        print_success "Sync completed!"
        echo ""
        echo "View files at:"
        echo "  $WORKSPACE_URL#workspace$TARGET_PATH"
    fi
    
    if [ $fail_count -gt 0 ]; then
        echo ""
        print_error "Some files failed to upload. Check errors above."
        exit 1
    fi
}

# ============================================================================
# RUN
# ============================================================================

# Show usage if help requested
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    echo "Usage: $0"
    echo ""
    echo "Syncs migration notebooks to Databricks workspace"
    echo ""
    echo "Configuration:"
    echo "  Profile:     $PROFILE"
    echo "  Workspace:   $WORKSPACE_URL"
    echo "  Target Path: $TARGET_PATH"
    echo ""
    echo "Files synced:"
    for file in "${FILES_TO_SYNC[@]}"; do
        echo "  - $file"
    done
    echo ""
    exit 0
fi

# Run main function
main
