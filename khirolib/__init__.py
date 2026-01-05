"""
KHI Robot Library - Python 3 only module
"""

import sys

# Check Python version
if sys.version_info[0] == 3:
    # Python 3 - import the Python 3 specific module
    from .core_py3 import KHIRoLibLite

    __all__ = ["KHIRoLibLite"]


__version__ = "1.0.0"
__description__ = "Kawasaki Robot Library for Python 3"
