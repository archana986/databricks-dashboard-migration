"""
Genie Space Permissions

Functions for exporting and managing Genie Space permissions.
"""

import csv
import json
import os
from dataclasses import dataclass, asdict
from typing import List, Optional
from databricks.sdk import WorkspaceClient


@dataclass
class PermissionEntry:
    """A single permission entry for a Genie Space."""
    space_id: str
    space_title: str
    principal_type: str  # user, group, service_principal
    principal_name: str
    permission_level: str  # CAN_MANAGE, CAN_EDIT, CAN_RUN, CAN_VIEW

    def to_dict(self) -> dict:
        return asdict(self)


def get_space_permissions(
    client: WorkspaceClient,
    space_id: str,
    space_title: str = ""
) -> List[PermissionEntry]:
    """
    Get ACL entries for a Genie Space.

    Args:
        client: Databricks WorkspaceClient
        space_id: The Genie Space ID
        space_title: Optional title for the space (for display purposes)

    Returns:
        List of PermissionEntry objects
    """
    permissions = []

    try:
        response = client.api_client.do(
            "GET",
            f"/api/2.0/permissions/genie-spaces/{space_id}",
            headers={"Accept": "application/json"}
        )

        if response and "access_control_list" in response:
            for acl in response["access_control_list"]:
                principal_type = None
                principal_name = None

                if "user_name" in acl:
                    principal_type = "user"
                    principal_name = acl["user_name"]
                elif "group_name" in acl:
                    principal_type = "group"
                    principal_name = acl["group_name"]
                elif "service_principal_name" in acl:
                    principal_type = "service_principal"
                    principal_name = acl["service_principal_name"]

                if principal_type and principal_name:
                    for perm in acl.get("all_permissions", []):
                        permissions.append(PermissionEntry(
                            space_id=space_id,
                            space_title=space_title,
                            principal_type=principal_type,
                            principal_name=principal_name,
                            permission_level=perm.get("permission_level", "UNKNOWN")
                        ))

    except Exception as e:
        print(f"Warning: Could not get permissions for space {space_id}: {e}")
        try:
            object_permissions = client.permissions.get(
                object_type="genie-spaces",
                object_id=space_id
            )
            if object_permissions and object_permissions.access_control_list:
                for acl in object_permissions.access_control_list:
                    principal_type = None
                    principal_name = None

                    if acl.user_name:
                        principal_type = "user"
                        principal_name = acl.user_name
                    elif acl.group_name:
                        principal_type = "group"
                        principal_name = acl.group_name
                    elif acl.service_principal_name:
                        principal_type = "service_principal"
                        principal_name = acl.service_principal_name

                    if principal_type and principal_name:
                        for perm in acl.all_permissions or []:
                            permissions.append(PermissionEntry(
                                space_id=space_id,
                                space_title=space_title,
                                principal_type=principal_type,
                                principal_name=principal_name,
                                permission_level=perm.permission_level.value if perm.permission_level else "UNKNOWN"
                            ))
        except Exception as e2:
            print(f"Warning: Fallback permissions fetch also failed: {e2}")

    return permissions


def export_permissions_json(
    permissions: List[PermissionEntry],
    output_path: str
) -> None:
    """
    Write permissions to a JSON file.

    Args:
        permissions: List of PermissionEntry objects
        output_path: Path to write the JSON file
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    data = [p.to_dict() for p in permissions]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def export_permissions_csv(
    permissions: List[PermissionEntry],
    output_path: str
) -> None:
    """
    Write permissions to a CSV file.

    Args:
        permissions: List of PermissionEntry objects
        output_path: Path to write the CSV file
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fieldnames = ["space_id", "space_title", "principal_type", "principal_name", "permission_level"]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in permissions:
            writer.writerow(p.to_dict())


def export_all_permissions(
    client: WorkspaceClient,
    spaces: List[dict],
    volume_path: str
) -> str:
    """
    Export permissions for all spaces to the volume.

    Args:
        client: Databricks WorkspaceClient
        spaces: List of space info dictionaries with space_id and title
        volume_path: Base path to the UC volume

    Returns:
        Path to the consolidated permissions CSV
    """
    all_permissions = []
    permissions_dir = os.path.join(volume_path, "permissions")
    os.makedirs(permissions_dir, exist_ok=True)

    for space in spaces:
        space_id = space.get("space_id") or space.get("_metadata", {}).get("source_space_id")
        title = space.get("title", "")

        if not space_id:
            continue

        perms = get_space_permissions(client, space_id, title)
        all_permissions.extend(perms)

        if perms:
            safe_title = title.lower().replace(" ", "_")[:50]
            json_path = os.path.join(permissions_dir, f"{safe_title}_permissions.json")
            export_permissions_json(perms, json_path)

    csv_path = os.path.join(permissions_dir, "all_permissions.csv")
    export_permissions_csv(all_permissions, csv_path)

    print(f"Exported {len(all_permissions)} permission entries to {csv_path}")
    return csv_path
