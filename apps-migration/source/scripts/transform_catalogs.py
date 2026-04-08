#!/usr/bin/env python3
"""
Catalog Transform Script for Apps Migration

Reads catalog_mapping.csv and applies find-and-replace to all code files
in the bundle directory.

Usage:
    python transform_catalogs.py <bundle_path>
    
Example:
    python transform_catalogs.py ./sample-gradio-app
    
The script expects catalog_mapping.csv in the bundle directory with format:
    source_catalog,target_catalog,notes
    prod_catalog,dev_catalog,# Used by: sample-app
"""

import os
import sys
import csv
import re
from pathlib import Path


def load_catalog_mapping(mapping_file: Path) -> dict:
    """Load catalog mapping from CSV file."""
    mapping = {}
    
    if not mapping_file.exists():
        print(f"No catalog_mapping.csv found at {mapping_file}")
        return mapping
    
    with open(mapping_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            source = row.get('source_catalog', '').strip()
            target = row.get('target_catalog', '').strip()
            if source and target:
                mapping[source] = target
            elif source and not target:
                print(f"  Warning: No target specified for '{source}' - skipping")
    
    return mapping


def transform_file(file_path: Path, mapping: dict) -> tuple[int, list]:
    """
    Transform a single file, replacing catalog references.
    Returns (replacement_count, list of changes made).
    """
    if not file_path.suffix in ['.py', '.sql', '.yaml', '.yml', '.json', '.txt']:
        return 0, []
    
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  Error reading {file_path}: {e}")
        return 0, []
    
    original_content = content
    changes = []
    total_replacements = 0
    
    for source_catalog, target_catalog in mapping.items():
        # Pattern matches catalog.schema.table or catalog.schema references
        # Handles: "catalog.schema.table", FROM catalog.schema.table, spark.table("catalog...")
        
        # Count occurrences first
        pattern = rf'\b{re.escape(source_catalog)}\.'
        matches = re.findall(pattern, content)
        
        if matches:
            # Replace all occurrences
            content = re.sub(pattern, f'{target_catalog}.', content)
            count = len(matches)
            total_replacements += count
            changes.append(f"{source_catalog} -> {target_catalog} ({count} replacements)")
    
    if content != original_content:
        file_path.write_text(content, encoding='utf-8')
    
    return total_replacements, changes


def transform_bundle(bundle_path: Path) -> dict:
    """Transform all files in a bundle directory."""
    
    results = {
        "bundle": str(bundle_path),
        "mapping_loaded": False,
        "files_transformed": 0,
        "total_replacements": 0,
        "changes": []
    }
    
    mapping_file = bundle_path / "catalog_mapping.csv"
    mapping = load_catalog_mapping(mapping_file)
    
    if not mapping:
        print("No catalog mappings to apply (either no file or no target catalogs specified)")
        return results
    
    results["mapping_loaded"] = True
    print(f"Loaded {len(mapping)} catalog mapping(s):")
    for src, tgt in mapping.items():
        print(f"  {src} -> {tgt}")
    print()
    
    # Process all files in bundle (excluding resources/ which has DAB configs)
    code_files = []
    for ext in ['*.py', '*.sql', '*.yaml', '*.yml', '*.json']:
        code_files.extend(bundle_path.glob(ext))
    
    print(f"Processing {len(code_files)} file(s)...")
    
    for file_path in code_files:
        # Skip DAB config files
        if file_path.name in ['databricks.yml'] or 'resources' in str(file_path):
            continue
            
        replacements, changes = transform_file(file_path, mapping)
        
        if replacements > 0:
            results["files_transformed"] += 1
            results["total_replacements"] += replacements
            results["changes"].append({
                "file": file_path.name,
                "changes": changes
            })
            print(f"  {file_path.name}: {replacements} replacement(s)")
            for change in changes:
                print(f"    - {change}")
    
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python transform_catalogs.py <bundle_path>")
        print("Example: python transform_catalogs.py ./sample-gradio-app")
        sys.exit(1)
    
    bundle_path = Path(sys.argv[1])
    
    if not bundle_path.exists():
        print(f"Error: Bundle path does not exist: {bundle_path}")
        sys.exit(1)
    
    if not (bundle_path / "databricks.yml").exists():
        print(f"Error: Not a valid bundle (no databricks.yml found): {bundle_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("CATALOG TRANSFORM")
    print("=" * 60)
    print(f"Bundle: {bundle_path}")
    print()
    
    results = transform_bundle(bundle_path)
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Files transformed: {results['files_transformed']}")
    print(f"Total replacements: {results['total_replacements']}")
    
    if results['total_replacements'] > 0:
        print("\nNext step: Deploy to target workspace")
        print("  databricks bundle deploy -t target")
    elif not results['mapping_loaded']:
        print("\nAction required: Fill in target catalogs in catalog_mapping.csv")
    else:
        print("\nNo changes needed - no catalog references matched the mapping")


if __name__ == "__main__":
    main()
