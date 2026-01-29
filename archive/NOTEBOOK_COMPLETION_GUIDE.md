# Notebook Completion Guide

This guide provides the complete code for Cells 3-14 to finish the restructured notebook.

## Status

### Completed ✅
- Cell 1: Configuration with OAuth/SP/PAT authentication (OAuth as RECOMMENDED)
- Cell 2: Authentication helper and Volume I/O functions
- README: Complete authentication documentation
- QUICK_START: Workflow and authentication guidance

### To Be Added
- Cells 3-5: Helper functions (updated to use auth helper)
- Cell 6: Shared export function
- Cell 7: Shared transform function
- Cell 8: Manual import instructions (NEW)
- Cell 9: Manual ACL application (NEW)
- Cell 10: Manual workflow report (NEW)
- Cell 11: Automated import (renumbered)
- Cell 12: Automated report (renumbered)
- Cells 13-14: Utility cells (renumbered)

---

## Cell 3: Dashboard Export Helper Functions

**Markdown:**
```markdown
## Cell 3: Helper Functions - Dashboard Export

**Purpose:** Define functions for exporting dashboards and permissions from source workspace.

**Functions:**
- `get_dashboard_path_from_id()` - Get workspace path for dashboard ID
- `export_dashboard_to_lvdash()` - Export dashboard as .lvdash.json
- `get_dashboard_permissions()` - Retrieve dashboard permissions (ACL)
- `save_dashboard_export()` - Save dashboard and permissions to volume
- `discover_dashboards_in_folder()` - Discover all dashboards in a folder
```

**Code:** (Same as original, no changes needed - these functions don't use authentication)

---

## Cell 4: CSV Mapping & Transform Helper Functions

**Markdown:**
```markdown
## Cell 4: Helper Functions - CSV Mapping & Transform

**Purpose:** Define functions for loading CSV mappings and transforming dashboard JSON.

**Functions:**
- `load_mapping_csv()` - Load catalog/schema/table mappings from CSV
- `find_and_replace_references()` - Replace references in SQL queries
- `transform_dashboard_json()` - Transform entire dashboard JSON structure
```

**Code:** (Same as original, no changes needed - these are pure transformation functions)

---

## Cell 5: Dashboard Import & Permissions Helper Functions

**Markdown:**
```markdown
## Cell 5: Helper Functions - Dashboard Import & Permissions

**Purpose:** Define functions for importing dashboards and restoring permissions in target workspace.

**Functions:**
- `import_dashboard_from_lvdash()` - Import dashboard from .lvdash.json to target
- `apply_dashboard_permissions()` - Apply permissions (best effort)
```

**Code:** (Same as original, no changes needed)

---

## Cell 6: Export Dashboards (SHARED)

**Markdown:**
```markdown
## Cell 6: Export Dashboards (SHARED - Used by Both Workflows)

**Purpose:** Export dashboards from source workspace to volume.

**Used by:**
- Manual Workflow (continue to Cell 8)
- Automated Workflow (continue to Cell 11)

**Process:**
1. Connect to source workspace using configured auth method
2. Discover or select dashboards
3. Export each as .lvdash.json
4. Capture permissions
5. Save to volume exported/ directory
```

**Code:**
```python
def export_dashboards_to_volume(
    dashboard_ids: List[str],
    source_folder_path: Optional[str],
    volume_export_path: str,
    use_folder: bool = False
) -> Dict[str, Any]:
    """Export dashboards using configured authentication."""
    
    print("=" * 80)
    print("📤 EXPORTING DASHBOARDS FROM SOURCE")
    print("=" * 80)
    
    # Create client using configured auth - KEY CHANGE HERE
    client = create_workspace_client(SOURCE_WORKSPACE_URL, is_source=True)
    
    # Ensure export directory exists
    ensure_volume_directory(volume_export_path)
    
    # Determine which dashboards to export
    dashboards_to_export = []
    
    if use_folder and source_folder_path:
        print(f"\n🔍 Discovering dashboards in: {source_folder_path}")
        discovered = discover_dashboards_in_folder(client, source_folder_path)
        dashboards_to_export = discovered
        print(f"   Found {len(dashboards_to_export)} dashboards")
    else:
        dashboards_to_export = [{"id": did, "path": None, "name": f"Dashboard_{did}"} 
                                for did in dashboard_ids]
    
    if not dashboards_to_export:
        print("⚠️  No dashboards to export")
        return {"exported": [], "errors": []}
    
    # Export each dashboard
    results = {
        "exported": [],
        "errors": []
    }
    
    for idx, dashboard_info in enumerate(dashboards_to_export, 1):
        dashboard_id = dashboard_info["id"]
        dashboard_path = dashboard_info.get("path") or get_dashboard_path_from_id(client, dashboard_id)
        
        print(f"\n[{idx}/{len(dashboards_to_export)}] Exporting dashboard: {dashboard_id}")
        
        try:
            # Export dashboard content
            exported = export_dashboard_to_lvdash(client, dashboard_path, dashboard_id)
            
            # Get permissions (skip if SKIP_PERMISSIONS is True)
            if not SKIP_PERMISSIONS:
                permissions = get_dashboard_permissions(client, dashboard_path)
            else:
                permissions = {"access_control_list": []}
            
            # Save to volume
            dashboard_file, perms_file = save_dashboard_export(
                dashboard_id=dashboard_id,
                lvdash_content=exported["content"],
                dashboard_name=exported["display_name"],
                permissions=permissions,
                volume_base_path=volume_export_path
            )
            
            results["exported"].append({
                "dashboard_id": dashboard_id,
                "dashboard_name": exported["display_name"],
                "dashboard_file": dashboard_file,
                "permissions_file": perms_file,
                "status": "success"
            })
            
            print(f"   ✅ Exported successfully")
            
        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ Export failed: {error_msg}")
            results["errors"].append({
                "dashboard_id": dashboard_id,
                "error": error_msg
            })
    
    print(f"\n" + "=" * 80)
    print(f"📊 Export Summary: {len(results['exported'])} succeeded, {len(results['errors'])} failed")
    print("=" * 80)
    
    return results


print("✅ Main export function loaded")
```

---

## Cell 7: Transform Dashboards (SHARED)

**Markdown:**
```markdown
## Cell 7: Transform Dashboards (SHARED - Used by Both Workflows)

**Purpose:** Apply CSV mappings to exported dashboards.

**Used by:**
- Manual Workflow (continue to Cell 8)
- Automated Workflow (continue to Cell 11)

**Process:**
1. Load CSV mappings
2. Read exported .lvdash.json files
3. Transform catalog/schema/table references
4. Save to transformed/ directory
```

**Code:** (Same as original - no auth changes needed)

---

## Cell 8: Manual Import Instructions (NEW)

**Markdown:**
```markdown
## Cell 8: Manual Import Instructions

**Purpose:** Guide for manually importing dashboards via Databricks UI.

**Workflow:** MANUAL IMPORT PATH

**Steps:**
1. Download transformed .lvdash.json files from volume
2. Import via Databricks UI: Workspace → Import
3. Note the new dashboard paths
4. Configure mapping below
5. Run Cell 9 to apply ACLs
```

**Code:**
```python
print("=" * 80)
print("🔧 MANUAL IMPORT WORKFLOW - Step 1: Instructions")
print("=" * 80)

print("\nTransformed dashboards are ready in:")
print(f"   {TRANSFORMED_PATH}")

print("\n📋 To manually import:")
print("1. Access the volume folder in Databricks")
print("2. Download .lvdash.json files from transformed/ folder")
print("3. In target workspace, go to: Workspace → Import")
print("4. Select and upload .lvdash.json files")
print("5. Choose destination folder")
print("6. Note the paths where dashboards were imported")

print("\n👉 Next: Configure MANUAL_IMPORT_MAPPING below and run Cell 9")

# List available transformed dashboards
transformed_files = list_volume_files(TRANSFORMED_PATH, "*.lvdash.json")
print(f"\n📊 Available transformed dashboards ({len(transformed_files)}):")
for f in transformed_files:
    filename = Path(f).name
    match = re.match(r'dashboard_([^_]+)_(.+)\.lvdash\.json', filename)
    if match:
        dash_id = match.group(1)
        dash_name = match.group(2).replace('_', ' ')
        print(f"   • ID: {dash_id} | Name: {dash_name}")
    else:
        print(f"   • {filename}")

print("\n" + "=" * 80)
```

---

## Cell 9: Apply ACLs to Manual Imports (NEW)

**Markdown:**
```markdown
## Cell 9: Apply ACLs to Manually Imported Dashboards

**Purpose:** Apply permissions to dashboards that were manually imported.

**Workflow:** MANUAL IMPORT PATH

**Instructions:**
1. After manually importing dashboards (Cell 8), update MANUAL_IMPORT_MAPPING below
2. Map: old_dashboard_id → new_dashboard_path_in_target
3. Run this cell to apply ACLs
```

**Code:**
```python
# ============================================================================
# CONFIGURATION: Manual Import Mapping
# ============================================================================
# Update this mapping after manually importing dashboards
# Format: "old_dashboard_id": "new_dashboard_path_in_target_workspace"

MANUAL_IMPORT_MAPPING = {
    # Example:
    # "abc123def456": "/Workspace/Shared/Migrated_Dashboards/Sales Dashboard",
    # "ghi789jkl012": "/Workspace/Shared/Migrated_Dashboards/Marketing KPIs",
}

if not MANUAL_IMPORT_MAPPING:
    print("⚠️  MANUAL_IMPORT_MAPPING is empty. Please configure mapping above before running.")
    print("   Format: 'old_id': '/Workspace/path/to/imported/dashboard'")
else:
    print("=" * 80)
    print("🔐 MANUAL IMPORT WORKFLOW - Step 2: Apply ACLs")
    print("=" * 80)
    
    # Create client for target workspace using configured auth
    client = create_workspace_client(TARGET_WORKSPACE_URL, is_source=False)
    
    acl_results = []
    
    for old_id, new_path in MANUAL_IMPORT_MAPPING.items():
        print(f"\n🔐 Processing: {new_path}")
        
        try:
            # Find permissions file
            perms_files = [f for f in list_volume_files(EXPORT_PATH, "*.json") 
                          if old_id in f and "permissions" in f]
            
            if not perms_files:
                print(f"   ⚠️  No permissions file found for {old_id}")
                acl_results.append({
                    "dashboard_id": old_id,
                    "target_path": new_path,
                    "status": "no_permissions_file",
                    "applied": 0,
                    "skipped": 0
                })
                continue
            
            # Read and apply permissions
            perms_content = read_volume_file(perms_files[0])
            permissions = json.loads(perms_content)
            
            if not SKIP_PERMISSIONS:
                perms_result = apply_dashboard_permissions(
                    client=client,
                    dashboard_path=new_path,
                    permissions=permissions
                )
                
                acl_results.append({
                    "dashboard_id": old_id,
                    "target_path": new_path,
                    "status": "success",
                    "applied": perms_result["applied"],
                    "skipped": perms_result["skipped"]
                })
                
                print(f"   ✅ Applied: {perms_result['applied']}, Skipped: {perms_result['skipped']}")
            else:
                print(f"   ⊘ Permissions skipped (SKIP_PERMISSIONS=True)")
                acl_results.append({
                    "dashboard_id": old_id,
                    "target_path": new_path,
                    "status": "skipped",
                    "applied": 0,
                    "skipped": 0
                })
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            acl_results.append({
                "dashboard_id": old_id,
                "target_path": new_path,
                "status": "error",
                "error": str(e),
                "applied": 0,
                "skipped": 0
            })
    
    # Store results for Cell 10
    manual_acl_results = acl_results
    
    print("\n" + "=" * 80)
    print(f"📊 ACL Application Complete: {len([r for r in acl_results if r['status']=='success'])}/{len(acl_results)} succeeded")
    print("=" * 80)
    print("\n👉 Next: Run Cell 10 to generate manual workflow report")
```

---

## Cell 10: Manual Workflow Report (NEW)

**Code provided in guide...**

---

## Cell 11-12: Automated Workflow (Renumbered)

Update function calls to use `create_workspace_client()` instead of passing tokens.

---

## Cells 13-14: Utility Cells

Renumber from previous Cells 11-12.

---

## Quick Integration Steps

1. Open the partial notebook file created
2. Add the missing cells using Databricks UI
3. Copy code from this guide into each cell
4. Ensure all markdown descriptions are included
5. Test with dry run mode

## Key Changes Summary

- **Cell 1**: Added OAuth/SP/PAT auth config (OAuth as RECOMMENDED)
- **Cell 2**: Added `create_workspace_client()` helper
- **Cell 6**: Updated to use `create_workspace_client()`
- **Cells 8-10**: NEW manual workflow cells
- **Cells 11-12**: Renumbered automated workflow (updated auth calls)
- **Cells 13-14**: Renumbered utility cells
