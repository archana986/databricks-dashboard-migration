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
    # Read CSV with all columns as strings to avoid float conversion
    df = pd.read_csv(io.StringIO(content), dtype=str, keep_default_na=False)
    # Convert NaN to empty string and ensure all values are strings
    df = df.fillna('')
    return df.to_dict('records')

def transform_dashboard_json(
    dashboard_json: str,
    mappings: List[Dict]
) -> str:
    """
    Apply catalog/schema/table transformations to dashboard JSON.
    
    Uses regex with word boundaries for accurate replacements.
    
    Args:
        dashboard_json: Dashboard JSON string
        mappings: List of mapping dictionaries from CSV
    
    Returns:
        Transformed JSON string
    """
    # Parse and re-serialize for consistency
    data = json.loads(dashboard_json)
    json_str = json.dumps(data, indent=2)
    
    # Apply transformations
    result = _find_and_replace_references(json_str, mappings)
    
    # Validate result
    json.loads(result)  # Raises error if invalid
    
    return result

def _find_and_replace_references(text: str, mappings: List[Dict]) -> str:
    """
    Replace catalog.schema.table references with proper boundary handling.
    
    Handles:
    - Fully-qualified references: catalog.schema.table
    - Schema references: catalog.schema
    - Catalog-only references in JSON fields
    - Volume paths
    """
    if not isinstance(text, str):
        return text
    
    result = text
    
    for mapping in mappings:
        # Get values and convert to strings, handle None/NaN
        old_cat = str(mapping.get('old_catalog', '') or '')
        old_schema = str(mapping.get('old_schema', '') or '')
        old_table = str(mapping.get('old_table', '') or '')
        new_cat = str(mapping.get('new_catalog', '') or '')
        new_schema = str(mapping.get('new_schema', '') or '')
        new_table = str(mapping.get('new_table', '') or '')
        
        # Replace fully-qualified table references: catalog.schema.table
        if old_cat and old_schema and old_table and new_cat and new_schema and new_table:
            old_ref = f"{old_cat}.{old_schema}.{old_table}"
            new_ref = f"{new_cat}.{new_schema}.{new_table}"
            # Use word boundaries to avoid partial matches
            result = re.sub(rf'\b{re.escape(old_ref)}\b', new_ref, result)
        
        # Replace schema references: catalog.schema
        if old_cat and old_schema and not old_table and new_cat and new_schema:
            old_ref = f"{old_cat}.{old_schema}"
            new_ref = f"{new_cat}.{new_schema}"
            # Negative lookahead: don't replace if followed by a dot (already handled above)
            result = re.sub(rf'\b{re.escape(old_ref)}(?!\.)', new_ref, result)
        
        # Replace catalog-only references
        if old_cat and new_cat:
            # Match catalog in quoted JSON fields: "catalog": "old_catalog"
            result = re.sub(
                rf'("catalog"\s*:\s*")({re.escape(old_cat)})(")',
                rf'\1{new_cat}\3',
                result
            )
            # Match catalog followed by dot (in qualified names)
            result = re.sub(rf'\b{re.escape(old_cat)}\.', f'{new_cat}.', result)
        
        # Replace volume paths
        old_vol = str(mapping.get('old_volume', '') or '')
        new_vol = str(mapping.get('new_volume', '') or '')
        if old_vol and new_vol:
            result = result.replace(f"/Volumes/{old_vol}/", f"/Volumes/{new_vol}/")
            result = result.replace(old_vol, new_vol)
    
    return result
