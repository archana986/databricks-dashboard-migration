"""
IP ACL management and whitelisting checks.

This module provides functions to detect cluster IPs and verify IP whitelist
status on target workspaces, enabling pre-deployment validation.
"""

import requests
import json
import time
from typing import Dict, Optional, Tuple
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import DatabricksError
from .dbutils_helper import get_dbutils as _get_dbutils


def detect_cluster_ip() -> Optional[str]:
    """
    Detect the public egress IP of the current cluster.
    
    Tries multiple IP detection services in order:
    1. ipify.org (most reliable)
    2. icanhazip.com (backup)
    3. ipinfo.io (backup)
    
    Returns:
        str: Detected IP address (e.g., "35.155.15.56")
        None: If detection fails
    """
    methods = [
        ("ipify.org", "https://api.ipify.org?format=json", "json"),
        ("icanhazip.com", "https://icanhazip.com", "text"),
        ("ipinfo.io", "https://ipinfo.io/json", "json")
    ]
    
    for service_name, url, response_type in methods:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            if response_type == "json":
                data = response.json()
                cluster_ip = data.get('ip')
            else:  # text
                cluster_ip = response.text.strip()
            
            if cluster_ip and len(cluster_ip) > 0:
                # Basic validation: should look like an IP address
                parts = cluster_ip.split('.')
                if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
                    return cluster_ip
        
        except Exception:
            # Silently continue to next method
            continue
    
    return None


def get_stored_cluster_ip(volume_base: str) -> Optional[Dict]:
    """
    Retrieve previously stored cluster IP from UC volume.
    
    Args:
        volume_base: Base path to UC volume (e.g., /Volumes/catalog/schema/volume)
    
    Returns:
        dict: Metadata including 'cluster_ip', 'detected_at', etc.
        None: If no stored IP found
    """
    try:
        dbutils = _get_dbutils()
        metadata_path = f"{volume_base}/cluster_ip_metadata.json"
        
        # Read from volume
        content = dbutils.fs.head(metadata_path, 1048576)  # 1MB max
        metadata = json.loads(content)
        
        return metadata
    
    except Exception:
        return None


def save_cluster_ip(cluster_ip: str, volume_base: str) -> bool:
    """
    Save detected cluster IP to UC volume for later retrieval.
    
    Args:
        cluster_ip: Detected IP address
        volume_base: Base path to UC volume
    
    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        from datetime import datetime
        
        # Get Spark config for metadata
        try:
            from pyspark.sql import SparkSession
            spark = SparkSession.builder.getOrCreate()
            cluster_id = spark.conf.get("spark.databricks.clusterUsageTags.clusterId", "unknown")
            workspace_url = spark.conf.get("spark.databricks.workspaceUrl", "unknown")
            user = spark.conf.get("spark.databricks.clusterUsageTags.clusterOwnerEmail", "unknown")
        except:
            cluster_id = "unknown"
            workspace_url = "unknown"
            user = "unknown"
        
        # Create metadata
        metadata = {
            "cluster_ip": cluster_ip,
            "detected_at": datetime.now().isoformat(),
            "cluster_id": cluster_id,
            "workspace_url": workspace_url,
            "user": user,
            "suggested_ranges": {
                "single_ip": f"{cluster_ip}/32",
                "small_range": f"{'.'.join(cluster_ip.split('.')[:3])}.{int(cluster_ip.split('.')[3]) // 16 * 16}/28",
                "large_range": f"{'.'.join(cluster_ip.split('.')[:3])}.0/24"
            }
        }
        
        # Write to volume
        metadata_path = f"{volume_base}/cluster_ip_metadata.json"
        with open(metadata_path.replace("/Volumes", "/dbfs/Volumes"), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return True
    
    except Exception:
        return False


def check_ip_whitelist_status(
    target_client: WorkspaceClient,
    cluster_ip: Optional[str] = None,
    volume_base: Optional[str] = None
) -> Dict:
    """
    Check if the current cluster IP is whitelisted on target workspace.
    
    Args:
        target_client: Authenticated client for target workspace
        cluster_ip: Optional specific IP to check (auto-detects if not provided)
        volume_base: Optional volume path to check for stored IP
    
    Returns:
        dict: Status information with keys:
            - 'whitelisted': bool (True if IP is accessible)
            - 'cluster_ip': str (the IP being checked)
            - 'ip_acls_enabled': bool (True if IP ACLs are active)
            - 'error': str (error message if check failed)
            - 'needs_whitelist': bool (True if manual whitelisting needed)
    """
    result = {
        'whitelisted': False,
        'cluster_ip': None,
        'ip_acls_enabled': False,
        'error': None,
        'needs_whitelist': False
    }
    
    # Step 1: Get cluster IP
    if cluster_ip:
        result['cluster_ip'] = cluster_ip
    elif volume_base:
        # Try to load from volume first
        stored = get_stored_cluster_ip(volume_base)
        if stored:
            result['cluster_ip'] = stored.get('cluster_ip')
    
    # If still no IP, detect it
    if not result['cluster_ip']:
        result['cluster_ip'] = detect_cluster_ip()
    
    if not result['cluster_ip']:
        result['error'] = "Could not detect cluster IP"
        result['needs_whitelist'] = True
        return result
    
    # Step 2: Try to connect to target workspace
    try:
        # Simple API call to test connectivity
        user = target_client.current_user.me()
        result['whitelisted'] = True
        result['ip_acls_enabled'] = False  # If we connected, either no ACLs or we're whitelisted
        return result
    
    except DatabricksError as e:
        error_msg = str(e)
        
        # Check if it's an IP ACL error
        if "blocked by Databricks IP ACL" in error_msg or "Source IP address" in error_msg:
            result['ip_acls_enabled'] = True
            result['needs_whitelist'] = True
            result['error'] = f"IP {result['cluster_ip']} is blocked by IP ACL on target workspace"
            return result
        else:
            # Some other authentication or connectivity error
            result['error'] = f"Connection failed: {error_msg}"
            return result
    
    except Exception as e:
        result['error'] = f"Unexpected error: {str(e)}"
        return result


def suggest_whitelist_command(
    cluster_ip: str,
    target_profile: str = "target-workspace",
    script_name: str = "auto_setup_ip_acl.sh"
) -> str:
    """
    Generate CLI command for whitelisting the cluster IP.
    
    Args:
        cluster_ip: IP address to whitelist
        target_profile: Databricks CLI profile name for target workspace
        script_name: Name of the whitelisting script
    
    Returns:
        str: Command to run in terminal
    """
    return f"./scripts/{script_name} --target-profile {target_profile}"


def wait_for_whitelist_propagation(
    target_client: WorkspaceClient,
    max_wait_seconds: int = 300,
    check_interval: int = 10
) -> Tuple[bool, str]:
    """
    Wait for IP whitelist changes to propagate and become effective.
    
    Args:
        target_client: Authenticated client for target workspace
        max_wait_seconds: Maximum time to wait (default: 300 = 5 minutes)
        check_interval: Seconds between connectivity checks (default: 10)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    elapsed = 0
    last_error = None
    
    while elapsed < max_wait_seconds:
        try:
            # Test connectivity with a simple API call
            target_client.current_user.me()
            return True, f"IP whitelist active after {elapsed} seconds"
        
        except Exception as e:
            last_error = str(e)
            time.sleep(check_interval)
            elapsed += check_interval
    
    return False, f"IP whitelist not accessible after {max_wait_seconds} seconds. Last error: {last_error}"


def format_status_message(status: Dict) -> str:
    """
    Format the IP whitelist status into a user-friendly message.
    
    Args:
        status: Status dict from check_ip_whitelist_status()
    
    Returns:
        str: Formatted message for display
    """
    lines = []
    lines.append("="*70)
    lines.append("IP WHITELIST STATUS CHECK")
    lines.append("="*70)
    lines.append("")
    
    if status['cluster_ip']:
        lines.append(f"🔍 Cluster IP: {status['cluster_ip']}")
    else:
        lines.append("❌ Could not detect cluster IP")
    
    lines.append("")
    
    if status['whitelisted']:
        lines.append("✅ IP is whitelisted - deployment can proceed")
    elif status['needs_whitelist']:
        lines.append("⚠️  IP is NOT whitelisted on target workspace")
        lines.append("")
        lines.append("Required action:")
        lines.append("  1. Open a new terminal")
        lines.append(f"  2. Run: ./scripts/auto_setup_ip_acl.sh")
        lines.append("  3. Wait for completion (~5 minutes)")
        lines.append("  4. Re-run this notebook")
        lines.append("")
        if status.get('error'):
            lines.append(f"Error details: {status['error']}")
    elif status.get('error'):
        lines.append(f"❌ Status check failed: {status['error']}")
    
    lines.append("")
    lines.append("="*70)
    
    return "\n".join(lines)


def check_and_report_status(
    target_client: WorkspaceClient,
    volume_base: str,
    skip_check: bool = False
) -> bool:
    """
    Check IP whitelist status and print formatted report.
    
    Convenience function that combines check + format + print.
    
    Args:
        target_client: Authenticated client for target workspace
        volume_base: Base path to UC volume
        skip_check: If True, skip check and return True (for bypass scenarios)
    
    Returns:
        bool: True if whitelisted (or check skipped), False if needs whitelisting
    
    Raises:
        Exception: If IP is not whitelisted and skip_check is False
    """
    if skip_check:
        print("⚠️  IP whitelist check skipped (skip_check=True)")
        return True
    
    status = check_ip_whitelist_status(
        target_client=target_client,
        volume_base=volume_base
    )
    
    message = format_status_message(status)
    print(message)
    
    if not status['whitelisted']:
        if status['needs_whitelist']:
            raise Exception(
                f"IP {status['cluster_ip']} is not whitelisted on target workspace. "
                "Run ./scripts/auto_setup_ip_acl.sh to whitelist, then retry deployment."
            )
        elif status.get('error'):
            raise Exception(f"IP whitelist check failed: {status['error']}")
    
    return True
