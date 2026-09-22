"""
Database management for JA Assure AI Marketing Agent.
Handles SQLite connection, schema creation, migrations, and database isolation.
Supports production/local database (data/ja_assure.db) and isolated demo database (data/demo/ja_assure_demo.db).
"""

import os
import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default database paths relative to project root
DEFAULT_DB_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "ja_assure.db"
DEMO_DB_DIR = DEFAULT_DB_DIR / "demo"
DEMO_DB_PATH = DEMO_DB_DIR / "ja_assure_demo.db"


def is_demo_mode() -> bool:
    """Check if the system is running in isolated DEMO_MODE."""
    return os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")


def get_db_path(custom_path: Optional[str] = None) -> Path:
    """
    Resolve database path, ensuring the parent directory exists.
    Priority:
      1. Explicit custom_path argument
      2. DEMO_MODE=true -> data/demo/ja_assure_demo.db (or JA_ASSURE_DEMO_DB_PATH)
      3. JA_ASSURE_DB_PATH environment variable
      4. Default production/local path -> data/ja_assure.db
    """
    if custom_path:
        path = Path(custom_path)
    elif is_demo_mode():
        env_demo_path = os.getenv("JA_ASSURE_DEMO_DB_PATH")
        path = Path(env_demo_path) if env_demo_path else DEMO_DB_PATH
    else:
        env_path = os.getenv("JA_ASSURE_DB_PATH")
        path = Path(env_path) if env_path else DEFAULT_DB_PATH

    # Ensure directory exists safely
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Get a configured SQLite database connection.
    Enables row factory for dict-like access, foreign keys, and WAL mode.
    """
    resolved_path = get_db_path(db_path)
    conn = sqlite3.connect(str(resolved_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def _run_migrations(cursor: sqlite3.Cursor) -> None:
    """
    Execute safe SQLite migrations without deleting or modifying existing rows.
    Checks existing columns with PRAGMA table_info before adding new columns.
    """
    # 1. content_queue column migrations
    cursor.execute("PRAGMA table_info(content_queue);")
    existing_cq_cols = {row["name"] for row in cursor.fetchall()}

    cq_migrations = [
        ("topic", "TEXT"),
        ("product", "TEXT"),
        ("generation_mode", "TEXT DEFAULT 'offline'"),
        ("provider", "TEXT DEFAULT 'offline'"),
        ("model", "TEXT DEFAULT 'offline-engine'"),
        ("prompt_version", "TEXT DEFAULT '1.0'"),
        ("knowledge_source_ids", "TEXT"),
        ("feedback_ids", "TEXT"),
        ("generation_metadata", "TEXT"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("sources", "TEXT"),
        ("risk_level", "TEXT DEFAULT 'LOW'"),
        ("risk_score", "REAL DEFAULT 0.0"),
    ]

    for col_name, col_def in cq_migrations:
        if col_name not in existing_cq_cols:
            try:
                cursor.execute(f"ALTER TABLE content_queue ADD COLUMN {col_name} {col_def};")
                logger.info(f"Migrated content_queue: added column '{col_name}'")
            except sqlite3.OperationalError as e:
                logger.debug(f"Column {col_name} could not be added: {e}")

    # 2. feedback column migrations (structured semantic learning)
    cursor.execute("PRAGMA table_info(feedback);")
    existing_fb_cols = {row["name"] for row in cursor.fetchall()}

    fb_migrations = [
        ("original_content", "TEXT"),
        ("corrected_content", "TEXT"),
        ("issue_type", "TEXT"),
        ("product", "TEXT"),
        ("platform", "TEXT"),
        ("risk_score", "REAL DEFAULT 0.0"),
        ("compliance_rule", "TEXT"),
    ]

    for col_name, col_def in fb_migrations:
        if col_name not in existing_fb_cols:
            try:
                cursor.execute(f"ALTER TABLE feedback ADD COLUMN {col_name} {col_def};")
                logger.info(f"Migrated feedback: added column '{col_name}'")
            except sqlite3.OperationalError as e:
                logger.debug(f"Column {col_name} could not be added: {e}")

    # 3. leads column migrations
    cursor.execute("PRAGMA table_info(leads);")
    existing_lead_cols = {row["name"] for row in cursor.fetchall()}

    lead_migrations = [
        ("region", "TEXT DEFAULT 'Singapore'"),
        ("source", "TEXT"),
        ("source_url", "TEXT"),
        ("scoring_breakdown", "TEXT"),
    ]

    for col_name, col_def in lead_migrations:
        if col_name not in existing_lead_cols:
            try:
                cursor.execute(f"ALTER TABLE leads ADD COLUMN {col_name} {col_def};")
                logger.info(f"Migrated leads: added column '{col_name}'")
            except sqlite3.OperationalError as e:
                logger.debug(f"Column {col_name} could not be added: {e}")


def init_db(db_path: Optional[str] = None) -> None:
    """
    Initialize SQLite database schema and run non-destructive migrations.
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
        topic TEXT,                              -- Original campaign brief / topic
        content TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | rejected | scheduled
        compliance_result TEXT,                  -- JSON string: {"status": "pass"|"fail", "reasons": [...]}
        cycle INTEGER DEFAULT 1,                 -- Generation/review cycle (1, 2, 3...)
        parent_id INTEGER,                       -- Linked original content if regenerated
        fixed_issue TEXT,                        -- Specific correction applied in this variant
        sources TEXT,                            -- JSON array of official JA Assure grounding sources
        generation_mode TEXT DEFAULT 'offline',  -- gemini | offline
        model TEXT DEFAULT 'offline-engine',     -- Model name or offline-engine
        prompt_version TEXT DEFAULT '1.0',       -- Version of brand prompt YAML
        knowledge_source_ids TEXT,               -- Comma-separated or JSON list of knowledge article IDs
        feedback_ids TEXT,                       -- Comma-separated or JSON list of feedback IDs applied
        generation_metadata TEXT,                -- JSON blob of extra execution telemetry
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_id) REFERENCES content_queue(id) ON DELETE SET NULL
    );
    """)

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

    # 3. Leads Table (Prospect pipeline)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact TEXT,
        vertical TEXT NOT NULL,                  -- Jewellers | Clinics | SMEs | Couriers
        region TEXT DEFAULT 'Singapore',         -- Target operating region
        fit_score INTEGER DEFAULT 50,            -- 0-100 score
        outreach_draft TEXT,
        source TEXT,                             -- e.g. 'official_directory', 'live_research'
        source_url TEXT,
        scoring_breakdown TEXT,                  -- JSON breakdown of scoring criteria
        status TEXT DEFAULT 'new',               -- new | contacted | qualified
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Run safe column additions on existing tables
    _run_migrations(cursor)

    # Indices for performance and query optimization
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_status ON content_queue(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_brand ON content_queue(brand);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_cycle ON content_queue(cycle);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_parent_id ON content_queue(parent_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_content_id ON feedback(content_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_brand ON feedback(brand);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_vertical ON leads(vertical);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_fit_score ON leads(fit_score);")

    conn.commit()
    conn.close()
