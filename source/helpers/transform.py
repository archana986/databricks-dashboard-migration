"""
Dashboard transformation functions.
"""

from .dbutils_helper import get_dbutils as _get_dbutils
import json
import re
from typing import List, Dict
import pandas as pd
import io

def load_mapping_csv(csv_path: str) -> List[Dict]:
    """
    Load catalog/schema/table mappings from CSV.
    Converts all values to strings and handles NaN/empty cells.
    """
    content = _get_dbutils().fs.head(csv_path, 10485760)
    # Prevent NaN conversion entirely
    df = pd.read_csv(
        io.StringIO(content), 
        dtype=str, 
        keep_default_na=False,
        na_values=None,
        na_filter=False
    )
    # Convert all values to strings and handle any remaining NaN
    df = df.fillna('').astype(str)
    # Replace string "nan" with empty string
    df = df.replace('nan', '')
    return df.to_dict('records')

def transform_dashboard_json(
    dashboard_json: str,
    mappings: List[Dict],
    debug: bool = False,
    clean_display_name: str = None
) -> str:
    """
    Apply catalog/schema/table transformations to dashboard JSON.
    
    Uses regex with word boundaries for accurate replacements.
    
    Args:
        dashboard_json: Dashboard JSON string
        mappings: List of mapping dictionaries from CSV
        debug: Enable debug logging (default: False)
        clean_display_name: Optional clean display name (removes ID prefix)
    
    Returns:
        Transformed JSON string
    """
    # Parse JSON
    data = json.loads(dashboard_json)
    
    # Fix display_name if it has dashboard ID prefix
    if clean_display_name:
        data['display_name'] = clean_display_name
    elif 'display_name' in data:
        # Remove dashboard_{id}_ prefix pattern if present
        import re
        display_name = data['display_name']
        # Pattern: dashboard_{hex_id}_{name} -> {name}
        match = re.match(r'dashboard_[a-f0-9]+_(.*)', display_name)
        if match:
            data['display_name'] = match.group(1).replace('_', ' ')
    
    # Serialize for transformation
    json_str = json.dumps(data, indent=2)
    
    # Apply transformations
    result = _find_and_replace_references(json_str, mappings, debug=debug)
    
    # Validate result
    transformed_data = json.loads(result)  # Raises error if invalid
    
    return json.dumps(transformed_data, indent=2)

def _validate_string_value(value) -> str:
    """
    Validate and clean a string value from CSV mapping.
    
    Args:
        value: Value from CSV mapping dictionary
    
    Returns:
        Clean string value, or empty string if invalid
    """
    if value is None:
        return ''
    # Convert to string
    str_value = str(value).strip()
    # Check for invalid values
    if str_value in ('', 'nan', 'None', 'NaN', 'null', 'NULL'):
        return ''
    return str_value

def _find_and_replace_references(text: str, mappings: List[Dict], debug: bool = False) -> str:
    """
    Replace catalog.schema.table references with proper boundary handling.
    
    Handles:
    - Fully-qualified references: catalog.schema.table
    - Schema references: catalog.schema
    - Catalog-only references in JSON fields
    - Volume paths
    
    Args:
        text: Text to transform
        mappings: List of mapping dictionaries
        debug: Enable debug logging
    """
    if not isinstance(text, str):
        return text
    
    result = text
    
    for i, mapping in enumerate(mappings, 1):
        if debug:
            print(f"   [Mapping {i}/{len(mappings)}] Processing: {mapping}")
        
        # Get values and validate/clean them
        old_cat = _validate_string_value(mapping.get('old_catalog'))
        old_schema = _validate_string_value(mapping.get('old_schema'))
        old_table = _validate_string_value(mapping.get('old_table'))
        new_cat = _validate_string_value(mapping.get('new_catalog'))
        new_schema = _validate_string_value(mapping.get('new_schema'))
        new_table = _validate_string_value(mapping.get('new_table'))
        
        # Replace fully-qualified table references: catalog.schema.table
        if old_cat and old_schema and old_table and new_cat and new_schema and new_table:
            old_ref = f"{old_cat}.{old_schema}.{old_table}"
            new_ref = f"{new_cat}.{new_schema}.{new_table}"
            if debug:
                print(f"      Table: '{old_ref}' → '{new_ref}'")
            # Use word boundaries to avoid partial matches
            result = re.sub(rf'\b{re.escape(old_ref)}\b', new_ref, result)
        
        # Replace schema references: catalog.schema (including when followed by .table)
        if old_cat and old_schema and not old_table and new_cat and new_schema:
            old_ref = f"{old_cat}.{old_schema}"
            new_ref = f"{new_cat}.{new_schema}"
            if debug:
                print(f"      Schema: '{old_ref}' → '{new_ref}'")
            # Replace all occurrences of catalog.schema (whether or not followed by .table)
            result = re.sub(rf'\b{re.escape(old_ref)}\b', new_ref, result)
        
        # Replace catalog-only references
        if old_cat and new_cat:
            if debug:
                print(f"      Catalog: '{old_cat}' → '{new_cat}'")
            # Match catalog in quoted JSON fields: "catalog": "old_catalog"
            result = re.sub(
                rf'("catalog"\s*:\s*")({re.escape(old_cat)})(")',
                rf'\1{new_cat}\3',
                result
            )
            # Match catalog followed by dot (in qualified names)
            result = re.sub(rf'\b{re.escape(old_cat)}\.', f'{new_cat}.', result)
        
        # Replace volume paths
        old_vol = _validate_string_value(mapping.get('old_volume'))
        new_vol = _validate_string_value(mapping.get('new_volume'))
        if old_vol and new_vol:
            if debug:
                print(f"      Volume: '{old_vol}' → '{new_vol}'")
            result = result.replace(f"/Volumes/{old_vol}/", f"/Volumes/{new_vol}/")
            result = result.replace(old_vol, new_vol)
    
    return result
