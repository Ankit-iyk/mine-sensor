"""
Pytest conftest — backend

Ensures the backend package is importable from the tests directory.
The backend is run from the backend/ directory, so sys.path needs
the app root.
"""
import sys
import os

# Add backend/ to sys.path so 'from app.xxx import ...' works in tests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.logging_config import configure_logging
configure_logging()
