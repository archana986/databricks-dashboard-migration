# Sync Scripts - Upload to Databricks Workspace

## Overview

Two scripts to sync your migration notebooks from local directory to Databricks workspace:

1. **`sync_to_databricks.sh`** - Bash script (uses Databricks CLI)
2. **`sync_to_databricks.py`** - Python script (uses Databricks SDK)

Both scripts upload all notebooks and documentation to:
```
https://e2-demo-field-eng.cloud.databricks.com
/Workspace/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration
```

## Quick Start

### Option 1: Bash Script (Recommended)

```bash
# Run the sync
./sync_to_databricks.sh

# View help
./sync_to_databricks.sh --help
```

### Option 2: Python Script

```bash
# Run the sync
python sync_to_databricks.py

# Dry run (simulate without uploading)
python sync_to_databricks.py --dry-run

# Custom profile
python sync_to_databricks.py --profile my-profile
```

## Prerequisites

### 1. Configure Databricks Profile

Choose ONE of these methods:

#### Method A: Using Databricks CLI (Bash script)

```bash
# Install Databricks CLI
pip install databricks-cli

# Configure profile
databricks configure --token --profile e2-demo-field-eng

# When prompted, enter:
# Host: https://e2-demo-field-eng.cloud.databricks.com
# Token: [your PAT token]
```

#### Method B: Using Environment Variables (Python script)

```bash
export DATABRICKS_HOST="https://e2-demo-field-eng.cloud.databricks.com"
export DATABRICKS_TOKEN="your-pat-token"
```

### 2. Get Your PAT Token

1. Go to: https://e2-demo-field-eng.cloud.databricks.com
2. Click User Settings (top right)
3. Go to "Access Tokens" tab
4. Click "Generate New Token"
5. Copy the token (you won't see it again!)

## Files That Will Be Uploaded

- `00_Prerequisite_Generation.ipynb` - Discovery and analysis notebook
- `01_Setup_and_Configuration.ipynb` - Setup notebook
- `02_Export_and_Transform.ipynb` - Export and transform notebook
- `03_Import_and_Migrate.ipynb` - Import and migrate notebook
- `COMPLETE_MIGRATION_GUIDE.md` - Full documentation
- `README.md` - Quick reference
- `catalog_schema_mapping_template.csv` - CSV template

## Usage Examples

### Bash Script

```bash
# Basic sync
./sync_to_databricks.sh

# Show help
./sync_to_databricks.sh --help
```

### Python Script

```bash
# Basic sync
python sync_to_databricks.py

# Dry run (test without uploading)
python sync_to_databricks.py --dry-run

# Use different profile
python sync_to_databricks.py --profile my-other-profile

# Custom target path
python sync_to_databricks.py --target-path /Workspace/Shared/MyMigration

# Combine options
python sync_to_databricks.py --profile prod --dry-run
```

## Verification

After running the sync script:

1. Go to your workspace:
   ```
   https://e2-demo-field-eng.cloud.databricks.com
   ```

2. Navigate to:
   ```
   Workspace → Users → archana.krishnamurthy@databricks.com → 
   01-Customer-Projects → Vizient → Dashboard-Migration
   ```

3. You should see all 4 notebooks and documentation files

## Troubleshooting

### Error: "databricks not found" (Bash script)

Install Databricks CLI:
```bash
pip install databricks-cli
```

### Error: "databricks-sdk not installed" (Python script)

Install Databricks SDK:
```bash
pip install databricks-sdk
```

### Error: "Profile 'e2-demo-field-eng' not configured"

Configure the profile:
```bash
databricks configure --token --profile e2-demo-field-eng
```

### Error: "Authentication failed"

1. Check your PAT token is still valid
2. Generate a new token if expired
3. Reconfigure the profile with new token

### Error: "Permission denied"

1. Make scripts executable:
   ```bash
   chmod +x sync_to_databricks.sh
   chmod +x sync_to_databricks.py
   ```

2. Or run with explicit interpreter:
   ```bash
   bash sync_to_databricks.sh
   python sync_to_databricks.py
   ```

### Error: "Cannot create directory"

You may not have permissions to create directories in the target path. Contact your workspace admin.

## Script Details

### What the Scripts Do

1. **Validate connection** to Databricks workspace
2. **Create target directory** if it doesn't exist
3. **Upload each file** with appropriate format:
   - `.ipynb` files → JUPYTER format
   - `.py` files → SOURCE format
   - Other files → AUTO format
4. **Overwrite** existing files
5. **Report** success/failure for each file

### Files Synced

| File | Type | Purpose |
|------|------|---------|
| `00_Prerequisite_Generation.ipynb` | Notebook | Dashboard discovery and analysis |
| `01_Setup_and_Configuration.ipynb` | Notebook | Environment setup |
| `02_Export_and_Transform.ipynb` | Notebook | Export and transform |
| `03_Import_and_Migrate.ipynb` | Notebook | Import and migrate |
| `COMPLETE_MIGRATION_GUIDE.md` | Doc | Comprehensive guide |
| `README.md` | Doc | Quick reference |
| `catalog_schema_mapping_template.csv` | Data | CSV template |

## Advanced Usage

### Sync to Different Workspace

Edit the script and change:

**Bash script (`sync_to_databricks.sh`):**
```bash
PROFILE="your-profile-name"
WORKSPACE_URL="https://your-workspace.cloud.databricks.com"
TARGET_PATH="/Workspace/path/to/your/folder"
```

**Python script (`sync_to_databricks.py`):**
```python
DEFAULT_PROFILE = "your-profile-name"
WORKSPACE_URL = "https://your-workspace.cloud.databricks.com"
TARGET_PATH = "/Workspace/path/to/your/folder"
```

### Add More Files to Sync

Edit the `FILES_TO_SYNC` array/list in either script:

**Bash:**
```bash
FILES_TO_SYNC=(
    "00_Prerequisite_Generation.ipynb"
    "your_new_file.ipynb"
    # ... add more files
)
```

**Python:**
```python
FILES_TO_SYNC = [
    "00_Prerequisite_Generation.ipynb",
    "your_new_file.ipynb",
    # ... add more files
]
```

## Next Steps After Sync

1. Open Databricks workspace
2. Navigate to the uploaded notebooks
3. Start with `00_Prerequisite_Generation.ipynb`
4. Follow the notebook sequence: 00 → 01 → 02 → 03

## Support

For issues with:
- **Sync scripts**: Check this README
- **Migration notebooks**: See `COMPLETE_MIGRATION_GUIDE.md`
- **Databricks authentication**: See Databricks documentation

---

**Version**: 1.0  
**Profile**: e2-demo-field-eng  
**Target**: /Workspace/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration
