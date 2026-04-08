"""
Genie Space Export

Functions for exporting Genie Space configurations.
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from databricks.sdk import WorkspaceClient


def export_space(
    client: WorkspaceClient,
    space_id: str,
    include_serialized: bool = True
) -> dict:
    """
    Export a Genie Space configuration.

    Args:
        client: Databricks WorkspaceClient
        space_id: The Genie Space ID to export
        include_serialized: Whether to include serialized_space (requires CAN_EDIT)

    Returns:
        Dictionary with space configuration and metadata
    """
    space = client.genie.get_space(
        space_id=space_id,
        include_serialized_space=include_serialized
    )

    if include_serialized and not space.serialized_space:
        raise ValueError(
            f"Could not retrieve serialized_space for space {space_id}. "
            "Ensure you have CAN_EDIT permission on the Genie Space."
        )

    data_sources = extract_data_sources(space.serialized_space) if space.serialized_space else {}

    export_data = {
        "_metadata": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "source_space_id": space_id,
            "source_workspace": client.config.host,
            "export_version": "1.0"
        },
        "title": space.title,
        "description": space.description,
        "warehouse_id": getattr(space, "warehouse_id", None),
        "serialized_space": space.serialized_space,
        "data_sources": data_sources,
    }

    return export_data


def export_space_to_volume(
    client: WorkspaceClient,
    space_id: str,
    volume_path: str,
    filename: Optional[str] = None
) -> str:
    """
    Export a Genie Space and write to UC volume.

    Args:
        client: Databricks WorkspaceClient
        space_id: The Genie Space ID to export
        volume_path: Base path to the UC volume (e.g., /Volumes/catalog/schema/volume)
        filename: Optional filename (defaults to sanitized title)

    Returns:
        Path to the exported JSON file
    """
    export_data = export_space(client, space_id, include_serialized=True)

    if not filename:
        safe_title = re.sub(r'[^\w\-]', '_', export_data["title"].lower())
        filename = f"{safe_title}.json"

    export_dir = os.path.join(volume_path, "exported")
    os.makedirs(export_dir, exist_ok=True)

    output_path = os.path.join(export_dir, filename)

    json_content = json.dumps(export_data, indent=2, ensure_ascii=False)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(json_content)

    print(f"Exported space '{export_data['title']}' to {output_path}")
    return output_path


def extract_data_sources(serialized_space: str) -> Dict[str, Any]:
    """
    Extract data source references from serialized_space.

    Args:
        serialized_space: The serialized_space JSON string

    Returns:
        Dictionary with tables and other data source info
    """
    if not serialized_space:
        return {}

    try:
        data = json.loads(serialized_space)
    except json.JSONDecodeError:
        return {}

    result = {
        "tables": [],
        "catalogs": set(),
        "schemas": set(),
    }

    data_sources = data.get("data_sources", {})
    tables = data_sources.get("tables", [])

    for table in tables:
        identifier = table.get("identifier", "")
        if identifier:
            result["tables"].append(identifier)
            parts = identifier.split(".")
            if len(parts) >= 2:
                result["catalogs"].add(parts[0])
                result["schemas"].add(f"{parts[0]}.{parts[1]}")

    result["catalogs"] = list(result["catalogs"])
    result["schemas"] = list(result["schemas"])

    return result


def transform_data_sources(
    serialized_space: str,
    catalog_mapping: Dict[str, str],
    schema_mapping: Optional[Dict[str, str]] = None
) -> str:
    """
    Transform data source references in serialized_space.

    Args:
        serialized_space: The original serialized_space JSON string
        catalog_mapping: Dict mapping old catalog names to new ones
        schema_mapping: Optional dict mapping old schema names to new ones

    Returns:
        Transformed serialized_space JSON string
    """
    if not serialized_space:
        return serialized_space

    try:
        data = json.loads(serialized_space)
    except json.JSONDecodeError:
        return serialized_space

    data_sources = data.get("data_sources", {})
    tables = data_sources.get("tables", [])

    for table in tables:
        identifier = table.get("identifier", "")
        if identifier:
            parts = identifier.split(".")
            if len(parts) >= 3:
                old_catalog = parts[0]
                old_schema = parts[1]
                table_name = parts[2]

                new_catalog = catalog_mapping.get(old_catalog, old_catalog)
                new_schema = old_schema
                if schema_mapping:
                    old_full_schema = f"{old_catalog}.{old_schema}"
                    new_full_schema = schema_mapping.get(old_full_schema)
                    if new_full_schema:
                        new_schema = new_full_schema.split(".")[-1]

                table["identifier"] = f"{new_catalog}.{new_schema}.{table_name}"

    instructions = data.get("instructions", "")
    if instructions:
        for old_cat, new_cat in catalog_mapping.items():
            instructions = instructions.replace(old_cat, new_cat)
        data["instructions"] = instructions

    return json.dumps(data)


def write_export_manifest(
    volume_path: str,
    exported_spaces: List[dict]
) -> str:
    """
    Write a manifest of all exported spaces.

    Args:
        volume_path: Base path to the UC volume
        exported_spaces: List of export metadata dictionaries

    Returns:
        Path to the manifest file
    """
    manifest = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "total_spaces": len(exported_spaces),
        "spaces": [
            {
                "source_space_id": s["_metadata"]["source_space_id"],
                "title": s["title"],
                "benchmark_count": len(json.loads(s.get("serialized_space", "{}")).get("benchmarks", [])) if s.get("serialized_space") else 0,
            }
            for s in exported_spaces
        ]
    }

    manifest_path = os.path.join(volume_path, "export_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest_path
