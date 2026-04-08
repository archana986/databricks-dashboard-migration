"""
Genie Space Reconciliation

Functions for validating and reconciling deployed Genie Spaces.
"""

import csv
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from databricks.sdk import WorkspaceClient


@dataclass
class ValidationResult:
    """Result of validating a single aspect of a Genie Space."""
    check_name: str
    status: str  # PASS, FAIL, WARN
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class ReconciliationEntry:
    """Reconciliation result for a single Genie Space."""
    source_space_id: str
    source_title: str
    target_space_id: Optional[str]
    deployment_status: str
    benchmarks_source: int
    benchmarks_target: int
    benchmarks_match: bool
    permissions_source: int
    permissions_target: int
    permissions_match: bool
    data_sources_valid: bool
    overall_status: str  # SUCCESS, PARTIAL, FAILED
    notes: str

    def to_dict(self) -> dict:
        return asdict(self)


def count_benchmarks_in_space(
    client: WorkspaceClient,
    space_id: str
) -> int:
    """
    Count benchmarks in a deployed Genie Space.

    Args:
        client: Databricks WorkspaceClient
        space_id: The Genie Space ID

    Returns:
        Number of benchmarks
    """
    try:
        space = client.genie.get_space(
            space_id=space_id,
            include_serialized_space=True
        )

        if not space.serialized_space:
            return 0

        data = json.loads(space.serialized_space)
        return len(data.get("benchmarks", []))

    except Exception as e:
        print(f"Warning: Could not count benchmarks for {space_id}: {e}")
        return -1


def count_permissions_in_space(
    client: WorkspaceClient,
    space_id: str
) -> int:
    """
    Count permission entries for a Genie Space.

    Args:
        client: Databricks WorkspaceClient
        space_id: The Genie Space ID

    Returns:
        Number of ACL entries
    """
    try:
        response = client.api_client.do(
            "GET",
            f"/api/2.0/permissions/genie-spaces/{space_id}",
            headers={"Accept": "application/json"}
        )

        if response and "access_control_list" in response:
            return len(response["access_control_list"])

        return 0

    except Exception as e:
        print(f"Warning: Could not count permissions for {space_id}: {e}")
        return -1


def validate_data_sources(
    client: WorkspaceClient,
    space_config: dict
) -> List[ValidationResult]:
    """
    Check if all data source tables exist in the target catalog.

    Args:
        client: Databricks WorkspaceClient
        space_config: Exported space configuration dictionary

    Returns:
        List of ValidationResult objects
    """
    results = []

    data_sources = space_config.get("data_sources", {})
    tables = data_sources.get("tables", [])

    if not tables:
        results.append(ValidationResult(
            check_name="data_sources",
            status="WARN",
            message="No data sources found in space configuration"
        ))
        return results

    for table_ref in tables:
        parts = table_ref.split(".")
        if len(parts) != 3:
            results.append(ValidationResult(
                check_name=f"table:{table_ref}",
                status="WARN",
                message=f"Invalid table reference format: {table_ref}"
            ))
            continue

        catalog, schema, table = parts

        try:
            client.api_client.do(
                "GET",
                f"/api/2.1/unity-catalog/tables/{catalog}.{schema}.{table}",
                headers={"Accept": "application/json"}
            )
            results.append(ValidationResult(
                check_name=f"table:{table_ref}",
                status="PASS",
                message=f"Table exists: {table_ref}"
            ))
        except Exception as e:
            results.append(ValidationResult(
                check_name=f"table:{table_ref}",
                status="FAIL",
                message=f"Table not found or inaccessible: {table_ref}",
                details={"error": str(e)}
            ))

    return results


def generate_reconciliation_report(
    client: WorkspaceClient,
    deployment_results: List[dict],
    import_path: str
) -> List[ReconciliationEntry]:
    """
    Compare source and target state for all deployed spaces.

    Args:
        client: Databricks WorkspaceClient
        deployment_results: List of deployment result dictionaries
        import_path: Path to the import volume

    Returns:
        List of ReconciliationEntry objects
    """
    entries = []

    for result in deployment_results:
        source_id = result.get("source_space_id", "")
        title = result.get("source_title", "")
        target_id = result.get("target_space_id")
        deployment_status = result.get("status", "UNKNOWN")

        source_benchmarks = 0
        source_permissions = 0
        target_benchmarks = 0
        target_permissions = 0
        data_sources_valid = True
        notes = []

        safe_title = title.lower().replace(" ", "_")[:50]
        exported_file = os.path.join(import_path, "exported", f"{safe_title}.json")

        if os.path.exists(exported_file):
            try:
                with open(exported_file, "r", encoding="utf-8") as f:
                    config = json.load(f)

                if config.get("serialized_space"):
                    data = json.loads(config["serialized_space"])
                    source_benchmarks = len(data.get("benchmarks", []))
            except Exception:
                pass

        perms_file = os.path.join(import_path, "permissions", f"{safe_title}_permissions.json")
        if os.path.exists(perms_file):
            try:
                with open(perms_file, "r", encoding="utf-8") as f:
                    perms = json.load(f)
                source_permissions = len(perms)
            except Exception:
                pass

        if deployment_status == "SUCCESS" and target_id:
            target_benchmarks = count_benchmarks_in_space(client, target_id)
            target_permissions = count_permissions_in_space(client, target_id)

            if os.path.exists(exported_file):
                try:
                    with open(exported_file, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    validations = validate_data_sources(client, config)
                    failed = [v for v in validations if v.status == "FAIL"]
                    if failed:
                        data_sources_valid = False
                        notes.append(f"{len(failed)} data source(s) invalid")
                except Exception:
                    pass

        benchmarks_match = (source_benchmarks == target_benchmarks) or target_benchmarks == -1
        permissions_match = (source_permissions <= target_permissions) or target_permissions == -1

        if deployment_status == "FAILED":
            overall_status = "FAILED"
        elif not benchmarks_match or not data_sources_valid:
            overall_status = "PARTIAL"
        else:
            overall_status = "SUCCESS"

        entries.append(ReconciliationEntry(
            source_space_id=source_id,
            source_title=title,
            target_space_id=target_id,
            deployment_status=deployment_status,
            benchmarks_source=source_benchmarks,
            benchmarks_target=target_benchmarks if target_benchmarks >= 0 else 0,
            benchmarks_match=benchmarks_match,
            permissions_source=source_permissions,
            permissions_target=target_permissions if target_permissions >= 0 else 0,
            permissions_match=permissions_match,
            data_sources_valid=data_sources_valid,
            overall_status=overall_status,
            notes="; ".join(notes) if notes else ""
        ))

    return entries


def write_reconciliation_report(
    entries: List[ReconciliationEntry],
    output_path: str
) -> str:
    """
    Write reconciliation report to CSV.

    Args:
        entries: List of ReconciliationEntry objects
        output_path: Path to write the CSV file

    Returns:
        Path to the written file
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fieldnames = [
        "source_space_id", "source_title", "target_space_id",
        "deployment_status", "benchmarks_source", "benchmarks_target",
        "benchmarks_match", "permissions_source", "permissions_target",
        "permissions_match", "data_sources_valid", "overall_status", "notes"
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for entry in entries:
            writer.writerow(entry.to_dict())

    return output_path


def generate_reconciliation_summary(entries: List[ReconciliationEntry]) -> dict:
    """
    Generate a summary of the reconciliation results.

    Args:
        entries: List of ReconciliationEntry objects

    Returns:
        Summary dictionary
    """
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_spaces": len(entries),
        "successful": sum(1 for e in entries if e.overall_status == "SUCCESS"),
        "partial": sum(1 for e in entries if e.overall_status == "PARTIAL"),
        "failed": sum(1 for e in entries if e.overall_status == "FAILED"),
        "total_source_benchmarks": sum(e.benchmarks_source for e in entries),
        "total_target_benchmarks": sum(e.benchmarks_target for e in entries),
        "benchmarks_preserved": all(e.benchmarks_match for e in entries),
        "data_sources_valid": all(e.data_sources_valid for e in entries),
    }
