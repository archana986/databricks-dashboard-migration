"""
Unity Catalog Volume file operations and archiving utilities.
"""

from .dbutils_helper import get_dbutils as _get_dbutils
from typing import List, Dict
from pathlib import Path
from datetime import datetime
import fnmatch
import time


# ============================================================================
# Basic Volume Operations
# ============================================================================

def read_volume_file(file_path: str) -> str:
    """
    Read file content from UC Volume.
    
    Args:
        file_path: Volume path to file
    
    Returns:
        File content as string
    """
    return _get_dbutils().fs.head(file_path, 10485760)  # 10MB limit


def write_volume_file(file_path: str, content: str, overwrite: bool = True) -> None:
    """
    Write content to UC Volume.
    
    Args:
        file_path: Volume path to write to
        content: Content to write
        overwrite: Whether to overwrite existing file
    """
    _get_dbutils().fs.put(file_path, content, overwrite=overwrite)


def list_volume_files(directory_path: str, pattern: str = "*") -> List[str]:
    """
    List files in UC Volume directory matching pattern.
    
    Args:
        directory_path: Volume directory path
        pattern: Glob pattern (e.g., "*.json", "*.csv")
    
    Returns:
        List of file paths
    """
    try:
        files = _get_dbutils().fs.ls(directory_path)
        matching_files = []
        
        for file_info in files:
            if not file_info.name.endswith('/'):  # Not a directory
                if fnmatch.fnmatch(file_info.name, pattern):
                    matching_files.append(file_info.path)
        
        return matching_files
    except Exception as e:
        print(f"Error listing files in {directory_path}: {e}")
        return []


def ensure_directory_exists(directory_path: str) -> bool:
    """
    Ensure directory exists in UC Volume, create if it doesn't.
    
    Args:
        directory_path: Volume directory path
    
    Returns:
        True if directory was created, False if already existed
    """
    try:
        _get_dbutils().fs.ls(directory_path)
        return False  # Already exists
    except:
        _get_dbutils().fs.mkdirs(directory_path)
        return True  # Created


def read_csv_from_volume(csv_path: str) -> List[Dict]:
    """
    Read CSV file from volume and return as list of dictionaries.
    
    Args:
        csv_path: Volume path to CSV file
    
    Returns:
        List of dictionaries (one per row)
    """
    import pandas as pd
    import io
    
    content = read_volume_file(csv_path)
    df = pd.read_csv(io.StringIO(content))
    return df.to_dict('records')


def write_csv_to_volume(csv_path: str, dataframe) -> None:
    """
    Write pandas DataFrame to volume as CSV.
    
    Args:
        csv_path: Volume path for CSV file
        dataframe: Pandas DataFrame to write
    """
    csv_content = dataframe.to_csv(index=False)
    write_volume_file(csv_path, csv_content, overwrite=True)
    print(f"✅ Wrote {len(dataframe)} rows to {csv_path}")


# ============================================================================
# Archiving Utilities (NEW)
# ============================================================================

def archive_old_files(
    source_folder: str,
    file_pattern: str = "*_transformed.json",
    archive_subfolder: str = "archive",
    min_age_minutes: int = 5
) -> Dict:
    """
    Archive old files from source folder to archive subfolder.
    
    This prevents mixing files from different export runs and ensures
    deployment only processes the current run's files.
    
    Args:
        source_folder: Path to folder containing files to archive
        file_pattern: Pattern for files to archive (e.g., "*_transformed.json", "*_permissions.json")
        archive_subfolder: Name of archive subfolder (default: "archive")
        min_age_minutes: Only archive files older than this many minutes (prevents archiving current run)
    
    Returns:
        Dict with stats: {
            'archived_count': int,
            'archive_path': str,
            'archived_files': List[str],
            'skipped_files': List[str]
        }
    """
    dbutils = _get_dbutils()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = f"{source_folder}/{archive_subfolder}/{timestamp}"
    
    archived_files = []
    skipped_files = []
    cutoff_time = time.time() - (min_age_minutes * 60)
    
    try:
        # Create archive directory
        dbutils.fs.mkdirs(archive_path)
        
        # List all files in source folder
        try:
            all_files = dbutils.fs.ls(source_folder)
        except Exception as e:
            # Folder might not exist yet
            return {
                'archived_count': 0,
                'archive_path': archive_path,
                'archived_files': [],
                'skipped_files': [],
                'error': f"Source folder not found: {str(e)}"
            }
        
        for file_info in all_files:
            # Skip if it's a directory
            if file_info.path.endswith('/'):
                continue
            
            # Check if file matches pattern
            file_matches = False
            if file_pattern == "*_transformed.json" and "_transformed.json" in file_info.name:
                file_matches = True
            elif file_pattern == "*_permissions.json" and "_permissions.json" in file_info.name:
                file_matches = True
            elif file_pattern == "*_schedules.json" and "_schedules.json" in file_info.name:
                file_matches = True
            elif file_pattern == "*.json" and file_info.name.endswith('.json'):
                file_matches = True
            
            if not file_matches:
                continue
            
            # Check file age (modification time in milliseconds)
            file_modification_time = file_info.modificationTime / 1000  # Convert to seconds
            
            if file_modification_time < cutoff_time:
                # File is old enough to archive
                try:
                    dest_path = f"{archive_path}/{file_info.name}"
                    dbutils.fs.mv(file_info.path, dest_path)
                    archived_files.append(file_info.name)
                except Exception as e:
                    skipped_files.append(f"{file_info.name} (error: {str(e)})")
            else:
                # File is too recent (likely from current run)
                age_minutes = (time.time() - file_modification_time) / 60
                skipped_files.append(f"{file_info.name} (age: {age_minutes:.1f} min, threshold: {min_age_minutes} min)")
    
    except Exception as e:
        return {
            'archived_count': 0,
            'archive_path': archive_path,
            'archived_files': [],
            'skipped_files': skipped_files,
            'error': f"Archive operation failed: {str(e)}"
        }
    
    return {
        'archived_count': len(archived_files),
        'archive_path': archive_path if len(archived_files) > 0 else None,
        'archived_files': archived_files,
        'skipped_files': skipped_files
    }


def cleanup_empty_archives(volume_base: str, archive_subfolder: str = "archive") -> Dict:
    """
    Remove empty archive folders to keep volume organized.
    
    Args:
        volume_base: Base volume path
        archive_subfolder: Name of archive subfolder
    
    Returns:
        Dict with cleanup stats
    """
    dbutils = _get_dbutils()
    removed_count = 0
    
    archive_root = f"{volume_base}/{archive_subfolder}"
    
    try:
        archive_folders = dbutils.fs.ls(archive_root)
        
        for folder in archive_folders:
            if folder.path.endswith('/'):
                # Check if folder is empty
                try:
                    contents = dbutils.fs.ls(folder.path)
                    if len(contents) == 0:
                        dbutils.fs.rm(folder.path, recurse=True)
                        removed_count += 1
                except:
                    pass
    
    except Exception as e:
        return {
            'removed_count': 0,
            'error': str(e)
        }
    
    return {
        'removed_count': removed_count
    }
