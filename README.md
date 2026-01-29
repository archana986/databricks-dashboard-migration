# Lakeview Dashboard Migration Solution

Complete solution for migrating Databricks Lakeview dashboards between workspaces with automated catalog/schema/table transformations.

## Quick Start

### 1. Import Notebooks to Databricks

Upload these three notebooks to your Databricks workspace:

1. **`01_Setup_and_Configuration.ipynb`** - Environment setup
2. **`02_Export_and_Transform.ipynb`** - Export and transform dashboards
3. **`03_Import_and_Migrate.ipynb`** - Import to target workspace

### 2. Read the Guide

📖 **[COMPLETE_MIGRATION_GUIDE.md](./COMPLETE_MIGRATION_GUIDE.md)** - Comprehensive documentation covering:
- Prerequisites and setup
- Authentication configuration (OAuth, Service Principal, PAT)
- Step-by-step instructions for all 3 notebooks
- CSV mapping reference
- Troubleshooting guide
- Best practices and FAQ

### 3. Prepare CSV Mappings

Edit **`catalog_schema_mapping_template.csv`** with your catalog/schema/table mappings.

## File Structure

### Core Files (Use These)

| File | Description |
|------|-------------|
| `01_Setup_and_Configuration.ipynb` | Notebook 1: Install libraries, configure auth, create volume |
| `02_Export_and_Transform.ipynb` | Notebook 2: Export dashboards and apply transformations |
| `03_Import_and_Migrate.ipynb` | Notebook 3: Import to target and restore permissions |
| `COMPLETE_MIGRATION_GUIDE.md` | Comprehensive documentation (READ THIS FIRST) |
| `catalog_schema_mapping_template.csv` | CSV template for mappings |

### Archive Folder

The `archive/` folder contains:
- Old versions of notebooks
- Previous documentation versions
- Reference materials
- Working documents

## Features

✅ **Three-Notebook Workflow**: Modular setup → export & transform → import & migrate  
✅ **Multiple Authentication**: OAuth (recommended), Service Principal, or PAT  
✅ **Dual Import Workflows**: Manual (UI-based) or Automated (programmatic)  
✅ **CSV-Based Mappings**: Simple catalog/schema/table transformations  
✅ **Permissions Migration**: Best-effort ACL restoration  
✅ **Volume Storage**: All artifacts stored in Databricks volumes  
✅ **Comprehensive Reporting**: Detailed migration logs  
✅ **Dry Run Mode**: Test migrations without actual imports  

## Workflow Overview

```
┌─────────────────────────────────────┐
│ Notebook 1: Setup & Configuration  │
├─────────────────────────────────────┤
│ • Install libraries                 │
│ • Configure authentication         │
│ • Create volume structure          │
│ • Prepare CSV mappings             │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Notebook 2: Export & Transform      │
├─────────────────────────────────────┤
│ • Export dashboards from source    │
│ • Capture permissions              │
│ • Apply CSV transformations        │
│ • Save transformed dashboards      │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Notebook 3: Import & Migrate        │
├─────────────────────────────────────┤
│ Choose workflow:                    │
│ • Manual: Import via UI, apply ACLs│
│ • Automated: Full automation       │
│ • Generate migration report        │
└─────────────────────────────────────┘
```

## Prerequisites

- Access to source and target Databricks workspaces
- Permissions to create volumes in Unity Catalog
- One of: Azure CLI (`az login`), Service Principal credentials, or PAT tokens
- Databricks Runtime 11.3 LTS or higher

## Authentication (Choose One)

### OAuth - RECOMMENDED ✅

```bash
az login
```

**Best for**: Most scenarios, interactive use, development

### Service Principal

```bash
# Store credentials in Databricks secrets
databricks secrets create-scope migration
databricks secrets put --scope migration --key source-sp-client-id
# ... (see guide for details)
```

**Best for**: Production, CI/CD, automation

### PAT Tokens

```bash
# Store tokens in Databricks secrets
databricks secrets put --scope migration --key source-token
databricks secrets put --scope migration --key target-token
```

**Best for**: Quick tests, development

## Support

- 📖 Full documentation: [COMPLETE_MIGRATION_GUIDE.md](./COMPLETE_MIGRATION_GUIDE.md)
- 🐛 Troubleshooting: See guide Section 9
- 💡 Best practices: See guide Section 10
- ❓ FAQ: See guide Section 11

## Quick Links

- [Prerequisites](./COMPLETE_MIGRATION_GUIDE.md#prerequisites)
- [Quick Start Guide](./COMPLETE_MIGRATION_GUIDE.md#quick-start)
- [Authentication Setup](./COMPLETE_MIGRATION_GUIDE.md#authentication-guide)
- [CSV Mapping Reference](./COMPLETE_MIGRATION_GUIDE.md#csv-mapping-reference)
- [Troubleshooting](./COMPLETE_MIGRATION_GUIDE.md#troubleshooting)
- [FAQ](./COMPLETE_MIGRATION_GUIDE.md#faq)

---

**Version**: 1.0  
**Last Updated**: January 2026  
**Compatible with**: Databricks Runtime 11.3 LTS+
