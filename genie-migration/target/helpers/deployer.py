"""
Genie Space Deployer

Functions for deploying Genie Spaces to the target workspace.
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import List, Optional
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ObjectType


@dataclass
class DeploymentResult:
    """Result of a Genie Space deployment."""
    source_space_id: str
    source_title: str
    target_space_id: Optional[str]
    status: str  # SUCCESS, FAILED, SKIPPED
    action: str  # CREATED, UPDATED, NONE
    error: Optional[str]

    def to_dict(self) -> dict:
        return asdict(self)


def find_existing_space(
    client: WorkspaceClient,
    parent_path: str,
    title: str
) -> Optional[str]:
    """
    Find an existing Genie Space by title in the given workspace path.

    Args:
        client: Databricks WorkspaceClient
        parent_path: Workspace folder path to search
        title: Title of the Genie Space to find

    Returns:
        The space_id if found, None otherwise
    """
    try:
        items = list(client.workspace.list(parent_path))

        for item in items:
            if item.object_type and "DASHBOARD" in str(item.object_type):
                try:
                    potential_id = item.path.split("/")[-1] if item.path else None
                    if potential_id and len(potential_id) == 32:
                        space = client.genie.get_space(space_id=potential_id)
                        if space.title == title:
                            return potential_id
                except Exception:
                    continue
    except Exception as e:
        print(f"Warning: Could not search {parent_path}: {e}")

    return None


def deploy_space(
    client: WorkspaceClient,
    config: dict,
    warehouse_id: str,
    parent_path: str,
    target_space_id: Optional[str] = None
) -> DeploymentResult:
    """
    Create or update a Genie Space from exported config.

    Args:
        client: Databricks WorkspaceClient
        config: Exported space configuration dictionary
        warehouse_id: SQL Warehouse ID in target workspace
        parent_path: Workspace folder path for new spaces
        target_space_id: Existing space ID to update (optional)

    Returns:
        DeploymentResult with deployment status
    """
    source_space_id = config.get("_metadata", {}).get("source_space_id", "")
    title = config.get("title", "Untitled")
    description = config.get("description")
    serialized_space = config.get("serialized_space")

    if not serialized_space:
        return DeploymentResult(
            source_space_id=source_space_id,
            source_title=title,
            target_space_id=None,
            status="FAILED",
            action="NONE",
            error="Missing serialized_space in config"
        )

    try:
        existing_space_id = target_space_id

        if not existing_space_id:
            existing_space_id = find_existing_space(client, parent_path, title)

        if existing_space_id:
            print(f"  Updating existing space: {existing_space_id}")
            client.genie.update_space(
                space_id=existing_space_id,
                title=title,
                description=description,
                serialized_space=serialized_space,
                warehouse_id=warehouse_id
            )
            return DeploymentResult(
                source_space_id=source_space_id,
                source_title=title,
                target_space_id=existing_space_id,
                status="SUCCESS",
                action="UPDATED",
                error=None
            )
        else:
            print(f"  Creating new space: {title}")
            result = client.genie.create_space(
                warehouse_id=warehouse_id,
                serialized_space=serialized_space,
                title=title,
                description=description,
                parent_path=parent_path
            )
            return DeploymentResult(
                source_space_id=source_space_id,
                source_title=title,
                target_space_id=result.space_id,
                status="SUCCESS",
                action="CREATED",
                error=None
            )

    except Exception as e:
        return DeploymentResult(
            source_space_id=source_space_id,
            source_title=title,
            target_space_id=None,
            status="FAILED",
            action="NONE",
            error=str(e)
        )


def deploy_all_spaces(
    client: WorkspaceClient,
    import_path: str,
    warehouse_id: str,
    parent_path: str
) -> List[DeploymentResult]:
    """
    Deploy all spaces from import volume.

    Args:
        client: Databricks WorkspaceClient
        import_path: Path to the import volume
        warehouse_id: SQL Warehouse ID in target workspace
        parent_path: Workspace folder path for new spaces

    Returns:
        List of DeploymentResult objects
    """
    results = []
    exported_dir = os.path.join(import_path, "exported")

    if not os.path.exists(exported_dir):
        print(f"Warning: Exported directory not found: {exported_dir}")
        return results

    json_files = [f for f in os.listdir(exported_dir) if f.endswith(".json")]

    for filename in json_files:
        filepath = os.path.join(exported_dir, filename)
        print(f"\nDeploying: {filename}")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                config = json.load(f)

            result = deploy_space(client, config, warehouse_id, parent_path)
            results.append(result)

            if result.status == "SUCCESS":
                print(f"  ✓ {result.action}: {result.target_space_id}")
            else:
                print(f"  ✗ Failed: {result.error}")

        except Exception as e:
            results.append(DeploymentResult(
                source_space_id="",
                source_title=filename,
                target_space_id=None,
                status="FAILED",
                action="NONE",
                error=str(e)
            ))
            print(f"  ✗ Error loading config: {e}")

    return results


def write_deployment_manifest(
    import_path: str,
    results: List[DeploymentResult]
) -> str:
    """
    Write deployment manifest with source→target mappings.

    Args:
        import_path: Path to the import volume
        results: List of DeploymentResult objects

    Returns:
        Path to the manifest file
    """
    import csv
    from datetime import datetime, timezone

    manifest_path = os.path.join(import_path, "deployment_manifest.csv")

    fieldnames = ["source_space_id", "source_title", "target_space_id", "status", "action", "error"]

    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r.to_dict())

    summary_path = os.path.join(import_path, "deployment_summary.json")
    summary = {
        "deployed_at": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "success": sum(1 for r in results if r.status == "SUCCESS"),
        "failed": sum(1 for r in results if r.status == "FAILED"),
        "created": sum(1 for r in results if r.action == "CREATED"),
        "updated": sum(1 for r in results if r.action == "UPDATED"),
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return manifest_path
