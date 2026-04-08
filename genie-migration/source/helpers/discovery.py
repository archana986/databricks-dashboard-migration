"""
Genie Space Discovery

Functions for discovering and listing Genie Spaces in a workspace.
"""

import json
from dataclasses import dataclass, asdict
from typing import List, Optional
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ObjectType


@dataclass
class GenieSpaceInfo:
    """Metadata about a Genie Space."""
    space_id: str
    title: str
    description: Optional[str]
    parent_path: str
    warehouse_id: Optional[str]
    benchmark_count: int
    created_by: Optional[str]
    created_at: Optional[str]

    def to_dict(self) -> dict:
        return asdict(self)


def list_genie_spaces(
    client: WorkspaceClient,
    parent_path: str = "/Workspace",
    recursive: bool = True
) -> List[GenieSpaceInfo]:
    """
    Discover all Genie Spaces in the workspace.

    Args:
        client: Databricks WorkspaceClient
        parent_path: Root path to search from
        recursive: Whether to search subdirectories

    Returns:
        List of GenieSpaceInfo objects
    """
    spaces = []

    def search_path(path: str):
        try:
            items = list(client.workspace.list(path))
            for item in items:
                if item.object_type == ObjectType.DIRECTORY:
                    if recursive:
                        search_path(item.path)
                elif item.object_type and "DASHBOARD" in str(item.object_type):
                    try:
                        space_id = item.path.split("/")[-1] if item.path else None
                        if space_id and len(space_id) == 32:
                            space_info = get_space_details(client, space_id, item.path)
                            if space_info:
                                spaces.append(space_info)
                    except Exception:
                        pass
        except Exception as e:
            print(f"Warning: Could not list {path}: {e}")

    search_path(parent_path)
    return spaces


def discover_genie_spaces_via_api(client: WorkspaceClient) -> List[GenieSpaceInfo]:
    """
    Discover Genie Spaces using the Genie API directly.

    This is the preferred method as it doesn't rely on workspace listing.

    Args:
        client: Databricks WorkspaceClient

    Returns:
        List of GenieSpaceInfo objects
    """
    spaces = []

    try:
        response = client.api_client.do(
            "GET",
            "/api/2.0/genie/spaces",
            headers={"Accept": "application/json"}
        )
        if response and "spaces" in response:
            for space_data in response["spaces"]:
                space_id = space_data.get("space_id")
                if space_id:
                    space_info = get_space_details(client, space_id)
                    if space_info:
                        spaces.append(space_info)
    except Exception as e:
        print(f"Warning: Could not list spaces via API: {e}")
        print("Falling back to workspace listing...")

    return spaces


def get_space_details(
    client: WorkspaceClient,
    space_id: str,
    parent_path: Optional[str] = None
) -> Optional[GenieSpaceInfo]:
    """
    Get full details for a Genie Space.

    Args:
        client: Databricks WorkspaceClient
        space_id: The Genie Space ID
        parent_path: Optional parent path (if known from workspace listing)

    Returns:
        GenieSpaceInfo or None if not found
    """
    try:
        space = client.genie.get_space(
            space_id=space_id,
            include_serialized_space=True
        )

        benchmark_count = 0
        if space.serialized_space:
            try:
                serialized = json.loads(space.serialized_space)
                benchmarks = serialized.get("benchmarks", [])
                benchmark_count = len(benchmarks)
            except (json.JSONDecodeError, TypeError):
                pass

        actual_parent_path = parent_path
        if not actual_parent_path and hasattr(space, "parent_path"):
            actual_parent_path = space.parent_path
        if not actual_parent_path:
            actual_parent_path = "/Workspace/Shared"

        return GenieSpaceInfo(
            space_id=space_id,
            title=space.title or "Untitled",
            description=space.description,
            parent_path=actual_parent_path,
            warehouse_id=getattr(space, "warehouse_id", None),
            benchmark_count=benchmark_count,
            created_by=getattr(space, "created_by", None),
            created_at=getattr(space, "created_at", None),
        )
    except Exception as e:
        print(f"Warning: Could not get details for space {space_id}: {e}")
        return None


def filter_spaces_by_path(
    spaces: List[GenieSpaceInfo],
    path_prefix: str
) -> List[GenieSpaceInfo]:
    """
    Filter spaces by parent path prefix.

    Args:
        spaces: List of GenieSpaceInfo objects
        path_prefix: Path prefix to filter by

    Returns:
        Filtered list of spaces
    """
    return [s for s in spaces if s.parent_path.startswith(path_prefix)]
