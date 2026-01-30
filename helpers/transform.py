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
    """Load catalog/schema/table mappings from CSV."""
    content = _get_dbutils().fs.head(csv_path, 10485760)
    df = pd.read_csv(io.StringIO(content))
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
        old_cat = mapping.get('old_catalog', '')
        old_schema = mapping.get('old_schema', '')
        old_table = mapping.get('old_table', '')
        new_cat = mapping.get('new_catalog', '')
        new_schema = mapping.get('new_schema', '')
        new_table = mapping.get('new_table', '')
        
        # Replace fully-qualified table references: catalog.schema.table
        if old_cat and old_schema and old_table:
            old_ref = f"{old_cat}.{old_schema}.{old_table}"
            new_ref = f"{new_cat}.{new_schema}.{new_table}"
            # Use word boundaries to avoid partial matches
            result = re.sub(rf'\b{re.escape(old_ref)}\b', new_ref, result)
        
        # Replace schema references: catalog.schema
        if old_cat and old_schema and not old_table:
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
        old_vol = mapping.get('old_volume', '')
        new_vol = mapping.get('new_volume', '')
        if old_vol and new_vol:
            result = result.replace(f"/Volumes/{old_vol}/", f"/Volumes/{new_vol}/")
            result = result.replace(old_vol, new_vol)
    
    return result
