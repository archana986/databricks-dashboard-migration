# Configuration Guide - Option 1 Implementation

## ✅ What Changed

Your migration project now uses **databricks.yml as the single source of truth** for all configuration. This follows Databricks Asset Bundle best practices and eliminates configuration duplication.

---

## 📋 Quick Customization Checklist

When users download your repo from GitHub, they need to customize **ONE file**: `databricks.yml`

### Step 1: Update Core Variables (Lines 35-90)

```yaml
variables:
  catalog:
    default: YOUR_CATALOG_NAME  # ← CHANGE THIS
  
  volume_base:
    default: /Volumes/YOUR_CATALOG/YOUR_SCHEMA/YOUR_VOLUME  # ← CHANGE THIS
  
  source_workspace_url:
    default: https://YOUR-SOURCE.cloud.databricks.com  # ← CHANGE THIS
  
  target_workspace_url:
    default: https://YOUR-TARGET.cloud.databricks.com  # ← CHANGE THIS
  
  warehouse_name:
    default: YOUR_WAREHOUSE_NAME  # ← CHANGE THIS
```

### Step 2: Update Dev Target (Lines 170-180)

```yaml
targets:
  dev:
    workspace:
      host: https://YOUR-WORKSPACE.cloud.databricks.com  # ← CHANGE THIS
    
    variables:
      catalog: YOUR_CATALOG  # ← CHANGE THIS
      volume_base: /Volumes/YOUR_CATALOG/YOUR_SCHEMA/YOUR_VOLUME  # ← CHANGE THIS
      source_workspace_url: https://YOUR-SOURCE.cloud.databricks.com  # ← CHANGE THIS
      target_workspace_url: https://YOUR-TARGET.cloud.databricks.com  # ← CHANGE THIS
      warehouse_name: YOUR_WAREHOUSE  # ← CHANGE THIS
```

---

## 🚀 Usage After Configuration

### Command Line (Recommended)

```bash
# Deploy
databricks bundle deploy -t dev

# Run Step 1: Generate Inventory
databricks bundle run inventory_generation -t dev

# Run Step 2: Export & Transform
databricks bundle run export_transform -t dev

# Run Step 3: Generate & Deploy
databricks bundle run generate_deploy -t dev
```

### Databricks UI - Interactive Notebooks

**⚠️ IMPORTANT**: For interactive execution, you MUST run Cell 0.5 first!

1. Open `Bundle/Bundle_00_Inventory_Generation.ipynb`
2. **Run Cell 0.5** to create test widgets:
   ```python
   # Uncomment and customize:
   dbutils.widgets.text("catalog", "your_catalog")
   dbutils.widgets.text("volume_base", "/Volumes/your_catalog/your_schema/your_volume")
   # ... etc
   ```
3. Run remaining cells

---

## 🎯 What Users Need to Know

### For GitHub README or Documentation

**Key Points to Highlight:**

1. **Single Configuration File**: Everything is in `databricks.yml`
2. **No config.yaml**: The old config/config.yaml is no longer used
3. **Easy Customization**: Find all "CHANGE THIS" comments in databricks.yml
4. **Two Execution Methods**: 
   - CLI: Works immediately after deploy
   - UI Interactive: Requires Cell 0.5 setup first

### Sample GitHub README Section

```markdown
## 📝 Configuration

All configuration is in `databricks.yml`. Search for comments marked `# CHANGE THIS` to customize for your environment.

**Required Changes:**
1. Line 39: `catalog` - Your source catalog name
2. Line 42: `volume_base` - Your Unity Catalog volume path
3. Line 45: `source_workspace_url` - Your source workspace URL
4. Line 48: `target_workspace_url` - Your target workspace URL
5. Line 52: `warehouse_name` - Your SQL warehouse name
6. Lines 170-180: Update the `dev` target with the same values

**Optional Changes:**
- `audit_lookback_days` - Days to look back for usage data (default: 90)
- `transformation_enabled` - Enable/disable catalog transformations (default: true)
- `permissions_dry_run` - Test permissions without applying (default: true)
```

---

## 🔧 Technical Details

### How It Works

**Before (Option 2 - Two Config Files):**
```
User updates config.yaml → Also updates databricks.yml → Easy to get out of sync
```

**After (Option 1 - Single Config File):**
```
User updates databricks.yml → Values passed as parameters to notebooks → Single source of truth
```

### Parameter Flow

```
databricks.yml variables
    ↓
Job base_parameters
    ↓
dbutils.widgets.get() in notebooks
    ↓
Build config dict
    ↓
set_config() to cache for helpers
```

### Interactive Testing

For local/interactive notebook execution:
1. Cell 0.5 creates widgets with test values
2. Remaining cells read from widgets (same as job execution)
3. No code changes needed between job and interactive modes

---

## 📊 Status

### ✅ Completed
- [x] databricks.yml expanded with all variables
- [x] Bundle_00_Inventory_Generation.ipynb updated
- [x] README.md rewritten with comprehensive instructions
- [x] .gitignore updated
- [x] Committed and pushed to GitHub

### ⚠️ TODO
- [ ] Bundle_01_Export_and_Transform.ipynb needs similar update
- [ ] Bundle_02_Generate_and_Deploy.ipynb needs similar update
- [ ] Test full workflow end-to-end

**Note**: Bundle_01 and Bundle_02 currently still have config.yaml fallback logic. They will work with jobs (parameters passed) but interactive execution may fall back to config.yaml if Cell 0.5 isn't set up.

---

## 🎓 Benefits for Users

1. **Simpler Setup**: One file to customize
2. **No Duplication**: Can't have config mismatch
3. **Environment Support**: Easy dev/prod separation
4. **Standard Practice**: Follows Databricks recommendations
5. **Git Friendly**: Changes tracked in one file

---

## 📞 Support

If users have questions about configuration:
1. Check README.md for detailed instructions
2. Look for "CHANGE THIS" comments in databricks.yml
3. Refer to this CONFIGURATION_GUIDE.md
4. Check localplandoc.md for implementation details

---

**Last Updated**: 2026-01-30  
**Implementation**: Option 1 - databricks.yml Single Source of Truth
