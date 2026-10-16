"""
SAKSHI Criminal Network Intelligence Workbench - Backend Package.
"""
import os
import sys

# Ensure backend directory is in sys.path so sibling imports work universally
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

_sakshi_dir = os.path.dirname(_backend_dir)
if _sakshi_dir not in sys.path:
    sys.path.insert(0, _sakshi_dir)
