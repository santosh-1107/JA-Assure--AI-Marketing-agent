"""
Database Initialization Script for JA Assure AI Marketing Agent.
Sets up SQLite schema in data/ja_assure.db.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import init_db, get_db_path

if __name__ == "__main__":
    db_file = get_db_path()
    print(f"Initializing SQLite database at: {db_file}")
    init_db()
    print("Database schema successfully created!")
