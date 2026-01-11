"""Shared cache utility functions"""

import hashlib
from typing import Tuple, Dict, Any
import numpy as np


def create_cache_key(func_name: str, args: Tuple, kwargs: Dict[str, Any]) -> str:
    """Create a cache key from function name and arguments
    
    Args:
        func_name: Name of the function being cached
        args: Positional arguments
        kwargs: Keyword arguments
    
    Returns:
        A unique cache key string
    """
    # Convert arguments to strings for hashing
    arg_strs = []
    
    # Handle positional args (skip 'self' if present)
    for i, arg in enumerate(args):
        if i == 0 and hasattr(arg, '__class__'):
            # Skip 'self' parameter
            continue
            
        if isinstance(arg, (list, tuple)):
            # For lists/tuples, create hash of content
            arg_str = hashlib.sha256(str(tuple(str(x) for x in arg)).encode()).hexdigest()
        elif isinstance(arg, np.ndarray):
            # For numpy arrays, use shape and data hash
            arg_str = f"array_{arg.shape}_{hashlib.sha256(arg.data.tobytes()).hexdigest()}"
        else:
            arg_str = str(arg)
            
        arg_strs.append(arg_str)
    
    # Handle keyword args
    for key, value in sorted(kwargs.items()):
        if isinstance(value, (list, tuple)):
            value_str = str(hash(tuple(str(x) for x in value)))
        elif isinstance(value, np.ndarray):
            value_str = f"array_{value.shape}_{hash(value.data.tobytes())}"
        else:
            value_str = str(value)
        
        arg_strs.append(f"{key}={value_str}")
    
    # Create final cache key
    key_content = f"{func_name}({','.join(arg_strs)})"
    
    # Hash for consistent length and characters
    key_hash = hashlib.sha256(key_content.encode()).hexdigest()
    
    return f"mbed:embedding:{key_hash}"