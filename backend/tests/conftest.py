"""
Root conftest file for pytest.

This file is automatically loaded by pytest and contains setup
for making imports work correctly in tests.
"""
import os
import sys
from pathlib import Path

# Add the backend directory to the Python path for imports
backend_dir = str(Path(__file__).parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root) 