"""
Database management for JA Assure AI Marketing Agent.
Handles SQLite connection, schema creation, and transaction safety.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional

# Default database path relative to project root
DEFAULT_DB_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "ja_assure.db"


def get_db_path(custom_path: Optional[str] = None) -> Path:
    """Resolve database path, ensuring the parent directory exists."""
    if custom_path:
        path = Path(custom_path)
    else:
        env_path = os.getenv("JA_ASSURE_DB_PATH")
        path = Path(env_path) if env_path else DEFAULT_DB_PATH
    
    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Get a configured SQLite database connection.
    Enables row factory for dict-like access and enforces foreign keys.
    """
    resolved_path = get_db_path(db_path)
    conn = sqlite3.connect(str(resolved_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """
    Initialize SQLite database schema according to JA Assure specifications.
    Creates content_queue, feedback, and leads tables with appropriate indices.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. Content Queue Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS content_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand TEXT NOT NULL,                     -- Jade | DoctorShield
        platform TEXT NOT NULL,                  -- LinkedIn | Instagram | X
        content_type TEXT NOT NULL,              -- post | carousel | tweet | video_script
        content TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | rejected | scheduled
        compliance_result TEXT,                  -- JSON string: {"status": "pass"|"fail", "reasons": [...]}
        cycle INTEGER DEFAULT 1,                 -- Generation/review cycle (1, 2, 3...)
        parent_id INTEGER,                       -- Linked original content if regenerated
        fixed_issue TEXT,                        -- Specific correction applied in this variant
        sources TEXT,                            -- JSON array of official JA Assure grounding sources
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_id) REFERENCES content_queue(id) ON DELETE SET NULL
    );
    """)

    # Automatic migration: ensure 'sources' column exists in existing tables
    try:
        cursor.execute("ALTER TABLE content_queue ADD COLUMN sources TEXT;")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # 2. Feedback Table (Immutable audit trail)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content_id INTEGER NOT NULL,
        brand TEXT NOT NULL,
        tag TEXT NOT NULL,                       -- too_salesy | inaccurate_claim | off_brand_tone | wrong_cta | other
        note TEXT NOT NULL,                      -- Reviewer explanation / instructions
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (content_id) REFERENCES content_queue(id) ON DELETE CASCADE
    );
    """)

    # 3. Leads Table (P1 prospect pipeline)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact TEXT NOT NULL,
        vertical TEXT NOT NULL,                  -- Jewellers | Clinics | SMEs | Couriers
        fit_score INTEGER DEFAULT 50,            -- 0-100 score
        outreach_draft TEXT,
        status TEXT DEFAULT 'new',               -- new | contacted | qualified
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Indices for performance and query optimization
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_status ON content_queue(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_brand ON content_queue(brand);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_cycle ON content_queue(cycle);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_content_id ON feedback(content_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_brand ON feedback(brand);")

    conn.commit()
    conn.close()
