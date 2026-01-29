# Sync Script - Quick Upload to Databricks

## What This Does

Uploads your migration solution (all folders and files) to Databricks workspace in one command.

**Use this if:**
- ✅ You want quick upload without Git
- ✅ You're testing and iterating quickly
- ✅ You don't need version control yet

**Use Databricks Repos if:**
- ✅ You want auto-sync (recommended)
- ✅ You want version control
- ✅ You're working with a team

---

## Quick Start (3 Steps)

### Step 1: Configure Databricks CLI (One-Time)

```bash
# Install Databricks CLI
pip install databricks-cli

# Configure your profile
databricks configure --token --profile e2-demo-field-eng
```

**When prompted, enter:**
- **Databricks Host:** `https://e2-demo-field-eng.cloud.databricks.com`
- **Token:** Your PAT token (from User Settings → Access Tokens)

### Step 2: Run Sync Script

```bash
# Navigate to migration folder
cd "/Users/archana.krishnamurthy/Downloads/Career & Growth/Cursor/Customer-Work/Catalog Migration"

# Run Python sync script (recommended)
python sync_to_databricks.py

# OR run Bash sync script
./sync_to_databricks.sh
```

### Step 3: Verify in Databricks

1. Go to: https://e2-demo-field-eng.cloud.databricks.com
2. Navigate to:
   ```
   Workspace → Users → archana.krishnamurthy@databricks.com → 
   01-Customer-Projects → Vizient → Dashboard-Migration
   ```
3. You should see all folders:
   - `config/`
   - `helpers/`
   - `Bundle/`
   - `notebooks/`

**Done! All files are synced!** ✅

---

## What Gets Uploaded

The script uploads **32 files** in **4 folders**:

```
Dashboard-Migration/
├── config/
│   ├── config.yaml
│   └── config_example.yaml
├── helpers/
│   ├── __init__.py
│   ├── auth.py
│   ├── bundle_generator.py
│   ├── config_loader.py
│   ├── discovery.py
│   ├── export.py
│   ├── permissions.py
│   ├── transform.py
│   └── volume_utils.py
├── Bundle/
│   ├── Bundle_01_Export_and_Transform.ipynb
│   ├── Bundle_02_Generate_and_Deploy.ipynb
│   └── README.md
├── notebooks/
│   ├── 01_Export_and_Transform.ipynb
│   └── 02_Apply_Permissions.ipynb
├── TESTING_GUIDE.md
├── START_HERE.md
├── README.md
└── [other docs...]
```

---

## Options

### Dry Run (Preview Without Uploading)

```bash
# See what would be uploaded without actually uploading
python sync_to_databricks.py --dry-run
```

### Custom Profile

```bash
# Use different Databricks profile
python sync_to_databricks.py --profile my-other-profile
```

### Custom Target Path

```bash
# Upload to different workspace location
python sync_to_databricks.py --target-path /Workspace/Shared/MyFolder
```

### Combine Options

```bash
python sync_to_databricks.py --profile prod --dry-run
```

---

## Script Details

### Python Script (`sync_to_databricks.py`)

**Uses:** Databricks SDK (databricks-sdk)

**Install:**
```bash
pip install databricks-sdk
```

**Run:**
```bash
python sync_to_databricks.py
```

**Advantages:**
- More detailed output
- Better error handling
- Supports custom options

### Bash Script (`sync_to_databricks.sh`)

**Uses:** Databricks CLI (databricks-cli)

**Install:**
```bash
pip install databricks-cli
```

**Run:**
```bash
chmod +x sync_to_databricks.sh
./sync_to_databricks.sh
```

**Advantages:**
- Simpler, fewer dependencies
- Works in any shell environment

---

## Troubleshooting

### Error: "databricks-cli not installed"

**Fix:**
```bash
pip install databricks-cli
```

### Error: "databricks-sdk not installed"

**Fix:**
```bash
pip install databricks-sdk
```

### Error: "Profile 'e2-demo-field-eng' not configured"

**Fix:**
```bash
databricks configure --token --profile e2-demo-field-eng
# Enter your workspace URL and PAT token
```

### Error: "Authentication failed"

**Fix:**
1. Generate new PAT token in Databricks
2. Reconfigure profile:
   ```bash
   databricks configure --token --profile e2-demo-field-eng
   ```

### Error: "Permission denied"

**Fix:**
```bash
# Make script executable
chmod +x sync_to_databricks.py
chmod +x sync_to_databricks.sh

# Or run with explicit interpreter
python sync_to_databricks.py
bash sync_to_databricks.sh
```

### Error: "Module not found: helpers"

**This error happens in notebooks, not during sync.**

**Fix in notebook:**
```python
# Add this at top of notebook
import sys
sys.path.insert(0, '../helpers')

# Then import
from helpers import load_config
```

---

## After Syncing

### To Run Your Notebooks:

1. **Go to workspace**
2. **Navigate to:**
   ```
   Workspace → Users → archana.krishnamurthy@databricks.com → 
   01-Customer-Projects → Vizient → Dashboard-Migration
   ```
3. **Open Bundle approach:**
   - Click `Bundle/Bundle_01_Export_and_Transform.ipynb`
   - Run all cells
   - Then run `Bundle/Bundle_02_Generate_and_Deploy.ipynb`

### To Update After Changes:

**If you make changes locally:**
```bash
# Just re-run the sync script
python sync_to_databricks.py
```

Files are **overwritten**, so latest version is always uploaded.

---

## Comparison: Sync Script vs Databricks Repos

| Feature | Sync Script | Databricks Repos |
|---------|-------------|------------------|
| **Setup time** | 2 minutes | 10 minutes |
| **One-time upload** | ✅ Perfect | Overkill |
| **Repeated updates** | Manual re-run | Auto-sync |
| **Version control** | None | Built-in Git |
| **Team sharing** | Manual | Easy |
| **Industry standard** | No | Yes |
| **Best for** | Testing/quick start | Production use |

---

## When to Upgrade to Repos

Consider switching to Databricks Repos when:
- ✅ You're happy with the migration solution
- ✅ You want to track changes over time
- ✅ You need to collaborate with others
- ✅ You want automatic syncing
- ✅ You're ready for production

**See:** `DATABRICKS_REPOS_SETUP.md` for step-by-step Repos setup

---

## Quick Command Reference

```bash
# Configure Databricks (one-time)
databricks configure --token --profile e2-demo-field-eng

# Sync all files
python sync_to_databricks.py

# Preview without uploading
python sync_to_databricks.py --dry-run

# Check what's configured
databricks workspace ls /Workspace/Users/archana.krishnamurthy@databricks.com
```

---

## Summary

**Sync script is perfect for:**
- 🚀 Getting started quickly
- 🧪 Testing changes
- 📦 One-time uploads

**Just run:**
```bash
python sync_to_databricks.py
```

**All 32 files upload to Databricks in ~30 seconds!**

**Ready to test?** Follow `TESTING_GUIDE.md` after syncing!
