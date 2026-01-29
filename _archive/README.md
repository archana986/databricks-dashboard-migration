# Archived Notebooks

This folder contains the original notebooks that have been replaced by the modular architecture.

## Why These Were Archived

The original notebooks had several issues:

1. **Configuration duplication** - Same config edited in multiple notebooks
2. **Code duplication** - Helper functions copied across notebooks
3. **Maintenance difficulty** - Changes needed in multiple places
4. **Timeout issues** - Automated SDK import (NB03) had 5-minute timeouts
5. **Transformation bugs** - Simple string replace didn't handle all JSON formats

## What Replaced Them

### New Modular Structure

```
Customer-Work/Catalog Migration/
├── config/
│   ├── config.yaml              # Single configuration file
│   └── config_example.yaml      # Template
├── helpers/
│   ├── __init__.py
│   ├── config_loader.py         # Configuration management
│   ├── auth.py                  # Authentication
│   ├── discovery.py             # Dashboard discovery
│   ├── export.py                # Export functions
│   ├── transform.py             # Transformation logic
│   ├── permissions.py           # ACL management
│   └── volume_utils.py          # Volume operations
└── notebooks/
    ├── 01_Export_and_Transform.ipynb    # Replaces NB00, NB01, NB02
    └── 02_Apply_Permissions.ipynb       # Replaces NB03
```

### Mapping of Old to New

| Old Notebooks | New Notebooks | Status |
|--------------|---------------|--------|
| 00_Prerequisite_Generation.ipynb | notebooks/01_Export_and_Transform.ipynb | ✅ Consolidated |
| 01_Setup_and_Configuration.ipynb | config/config.yaml | ✅ Replaced by config file |
| 02_Export_and_Transform.ipynb | notebooks/01_Export_and_Transform.ipynb | ✅ Improved & consolidated |
| 03_Import_and_Migrate.ipynb | **Deprecated** (use Bundle approach or manual + 03A) | ⚠️ Removed due to timeouts |
| 03A_Apply_Permissions.ipynb | notebooks/02_Apply_Permissions.ipynb | ✅ Improved with config |

## Key Improvements

### 1. Single Configuration File

**Before:**
```python
# Had to edit in each notebook:
SOURCE_WORKSPACE_URL = "https://..."
TARGET_WORKSPACE_URL = "https://..."
VOLUME_BASE = "/Volumes/..."
# ... repeated in NB00, NB01, NB02, NB03
```

**After:**
```yaml
# Edit once in config/config.yaml:
source:
  workspace_url: "https://..."
target:
  workspace_url: "https://..."
paths:
  volume_base: "/Volumes/..."
```

### 2. Reusable Helper Modules

**Before:**
- Discovery functions copied in NB00, NB02
- Export functions copied in NB02
- Transform functions only in NB02
- Permission functions copied in NB03

**After:**
- All functions in `helpers/` module
- Import only what you need
- Testable, maintainable, documented

### 3. Fixed Transformation Logic

**Before (broken):**
```python
result = result.replace(old_ref, new_ref)  # Simple replace - misses many cases
```

**After (fixed):**
```python
result = re.sub(rf'\b{re.escape(old_ref)}\b', new_ref, result)  # Regex with boundaries
```

### 4. Simplified Workflow

**Before:** 5 notebooks (00 → 01 → 02 → 03/04)
**After:** 2 notebooks (01 → Manual Import → 02)

## Can I Still Use These Old Notebooks?

**Yes, but not recommended:**

- The old notebooks will still run
- They contain the same bugs (transformation issues, timeouts)
- Configuration is duplicated and harder to maintain

**Recommendation:** Use the new modular notebooks in the `notebooks/` folder.

## Migration Path

If you were mid-migration using old notebooks:

1. **Complete current run** with old notebooks if in progress
2. **Update configuration** in `config/config.yaml` for new runs
3. **Use new notebooks** for future migrations:
   - `notebooks/01_Export_and_Transform.ipynb`
   - Manual import (Bundle or UI)
   - `notebooks/02_Apply_Permissions.ipynb`

## Archived Files

- `00_Prerequisite_Generation.ipynb` - Dashboard discovery (now in NB01)
- `01_Setup_and_Configuration.ipynb` - Configuration (now in config.yaml)
- `02_Export_and_Transform.ipynb` - Export/transform (improved version in NB01)
- `03_Import_and_Migrate_DEPRECATED.ipynb` - Automated SDK import (deprecated due to timeouts)
- `03A_Apply_Permissions.ipynb` - Permissions (improved version in NB02)

## Questions?

See the main `README.md` in the parent directory for complete documentation of the new modular architecture.
