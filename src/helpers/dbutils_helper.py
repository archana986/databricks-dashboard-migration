"""
Shared dbutils helper for lazy initialization.
"""

_dbutils_instance = None

def get_dbutils():
    """
    Lazy initialization of dbutils.
    
    Returns dbutils object if available, None otherwise.
    """
    global _dbutils_instance
    
    if _dbutils_instance is None:
        try:
            # Try to get from notebook globals (injected by Databricks)
            import builtins
            if hasattr(builtins, 'dbutils'):
                _dbutils_instance = builtins.dbutils
                return _dbutils_instance
        except:
            pass
        
        try:
            # Try IPython approach
            import IPython
            ipython = IPython.get_ipython()
            if ipython:
                _dbutils_instance = ipython.user_ns.get("dbutils")
                if _dbutils_instance:
                    return _dbutils_instance
        except:
            pass
    
    return _dbutils_instance
