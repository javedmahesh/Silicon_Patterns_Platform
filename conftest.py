"""Pytest bootstrap: put the platform root on sys.path so tests can import the
top-level packages (``config``, ``integration``, ``master_db``) without an
install step. Keeps P0 runnable with a bare ``pytest`` from this folder.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
