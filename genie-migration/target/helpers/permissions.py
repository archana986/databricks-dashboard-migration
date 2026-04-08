"""
Genie Space Permissions - Target

Functions for applying permissions to deployed Genie Spaces.
"""

import json
import os
from dataclasses import dataclass
from typing import List, Dict, Optional
from databricks.sdk import WorkspaceClient


@dataclass
class PermissionEntry:
    """A single permission entry for a Genie Space."""
    space_id: str
    space_title: str
    principal_type: str
    principal_name: str
    permission_level: str


def load_permissions_from_json(filepath: str) -> List[PermissionEntry]:
    """
    Load permissions from a JSON file.

    Args:
        filepath: Path to the permissions JSON file

    Returns:
        List of PermissionEntry objects
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [
        PermissionEntry(
            space_id=p.get("space_id", ""),
            space_title=p.get("space_title", ""),
            principal_type=p.get("principal_type", ""),
            principal_name=p.get("principal_name", ""),
            permission_level=p.get("permission_level", "")
        )
        for p in data
    ]


def apply_space_permissions(
    client: WorkspaceClient,
    space_id: str,
    permissions: List[PermissionEntry],
    principal_mapping: Optional[Dict[str, str]] = None
) -> Dict[str, any]:
    """
    Apply ACL entries to a deployed Genie Space.

    Args:
        client: Databricks WorkspaceClient
        space_id: The target Genie Space ID
        permissions: List of PermissionEntry objects to apply
        principal_mapping: Optional dict mapping source principal names to target

    Returns:
        Dictionary with results (applied, skipped, errors)
    """
    results = {
        "applied": [],
        "skipped": [],
        "errors": []
    }

    acl_entries = []

    for perm in permissions:
        principal_name = perm.principal_name

        if principal_mapping and principal_name in principal_mapping:
            principal_name = principal_mapping[principal_name]

        entry = {
            "permission_level": perm.permission_level
        }

        if perm.principal_type == "user":
            entry["user_name"] = principal_name
        elif perm.principal_type == "group":
            entry["group_name"] = principal_name
        elif perm.principal_type == "service_principal":
            entry["service_principal_name"] = principal_name
        else:
            results["skipped"].append({
                "principal": principal_name,
                "reason": f"Unknown principal type: {perm.principal_type}"
            })
            continue

        acl_entries.append(entry)

    if not acl_entries:
        return results

    try:
        client.api_client.do(
            "PATCH",
            f"/api/2.0/permissions/genie-spaces/{space_id}",
            body={"access_control_list": acl_entries},
            headers={"Content-Type": "application/json"}
        )

        for entry in acl_entries:
            principal = entry.get("user_name") or entry.get("group_name") or entry.get("service_principal_name")
            results["applied"].append({
                "principal": principal,
                "level": entry["permission_level"]
            })

    except Exception as e:
        results["errors"].append({
            "space_id": space_id,
            "error": str(e)
        })

    return results


def apply_all_permissions(
    client: WorkspaceClient,
    deployment_results: List[dict],
    import_path: str,
    principal_mapping: Optional[Dict[str, str]] = None
) -> Dict[str, any]:
    """
    Apply permissions to all deployed spaces.

    Args:
        client: Databricks WorkspaceClient
        deployment_results: List of deployment result dictionaries
        import_path: Path to the import volume
        principal_mapping: Optional dict mapping source principals to target

    Returns:
        Summary of all permission applications
    """
    summary = {
        "total_spaces": 0,
        "spaces_with_permissions": 0,
        "total_applied": 0,
        "total_skipped": 0,
        "total_errors": 0,
        "details": []
    }

    permissions_dir = os.path.join(import_path, "permissions")

    if not os.path.exists(permissions_dir):
        print(f"Warning: Permissions directory not found: {permissions_dir}")
        return summary

    for result in deployment_results:
        if result.get("status") != "SUCCESS":
            continue

        source_id = result.get("source_space_id")
        target_id = result.get("target_space_id")
        title = result.get("source_title", "")

        if not target_id:
            continue

        summary["total_spaces"] += 1

        safe_title = title.lower().replace(" ", "_")[:50]
        perms_file = os.path.join(permissions_dir, f"{safe_title}_permissions.json")

        if not os.path.exists(perms_file):
            continue

        try:
            perms = load_permissions_from_json(perms_file)

            if not perms:
                continue

            summary["spaces_with_permissions"] += 1

            result = apply_space_permissions(client, target_id, perms, principal_mapping)

            summary["total_applied"] += len(result["applied"])
            summary["total_skipped"] += len(result["skipped"])
            summary["total_errors"] += len(result["errors"])

            summary["details"].append({
                "space_id": target_id,
                "title": title,
                "applied": len(result["applied"]),
                "skipped": len(result["skipped"]),
                "errors": result["errors"]
            })

        except Exception as e:
            summary["total_errors"] += 1
            summary["details"].append({
                "space_id": target_id,
                "title": title,
                "error": str(e)
            })

    return summary
