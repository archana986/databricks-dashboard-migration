"""
Unity Catalog Volume file operations.
"""

from typing import List, Dict
from pathlib import Path
import fnmatch

# Initialize dbutils for module scope (Databricks-specific)
try:
    dbutils
except NameError:
    import IPython
    dbutils = IPython.get_ipython().user_ns.get("dbutils")

def read_volume_file(file_path: str) -> str:
    """
    Read file content from UC Volume.
    
    Args:
        file_path: Volume path to file
    
    Returns:
        File content as string
    """
    return dbutils.fs.head(file_path, 10485760)  # 10MB limit

def write_volume_file(file_path: str, content: str, overwrite: bool = True) -> None:
    """
    Write content to UC Volume.
    
    Args:
        file_path: Volume path to write to
        content: Content to write
        overwrite: Whether to overwrite existing file
    """
    dbutils.fs.put(file_path, content, overwrite=overwrite)

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
        files = dbutils.fs.ls(directory_path)
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
        dbutils.fs.ls(directory_path)
        return False  # Already exists
    except:
        dbutils.fs.mkdirs(directory_path)
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
