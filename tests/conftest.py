"""
Pytest configuration for trading system tests.
"""

import sys
import os

# Add the workspace root to sys.path so we can import modules
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)
