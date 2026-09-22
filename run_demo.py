"""
JA Assure AI Marketing Agent — Unified Demo Launcher
Runs the FastAPI backend and Streamlit review dashboard simultaneously for local hackathon judging.
Operates on the isolated demo database (data/demo/ja_assure_demo.db) to protect production data.

Usage:
  python run_demo.py            # Runs both backend & dashboard in DEMO_MODE
  python run_demo.py --seed     # Re-seeds demo database first, then runs both
  python run_demo.py --backend  # Runs only the FastAPI backend (port 8000)
  python run_demo.py --dashboard # Runs only the Streamlit dashboard (port 8501)
"""

import os
import sys
import time
import subprocess
import argparse
from pathlib import Path

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent
from backend.database import DEMO_DB_PATH, init_db, get_connection


def run_init_and_seed(force_seed: bool = False):
    """Ensure demo database exists and is populated with demo review benchmarks."""
    demo_db_str = str(DEMO_DB_PATH)
    init_db(demo_db_str)

    conn = get_connection(demo_db_str)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM content_queue")
    count = cursor.fetchone()[0]
    conn.close()

    if count == 0 or force_seed:
        print(f"[Launcher] Seeding isolated demo database ({demo_db_str}) with 4 cycles of InsurTech review data...")
        from scripts.seed_demo import seed_data
        seed_data(db_path=demo_db_str)
    else:
        print(f"[Launcher] Demo database contains {count} content items. Ready.")


def main():
    parser = argparse.ArgumentParser(description="JA Assure AI Marketing Agent Launcher")
    parser.add_argument("--seed", action="store_true", help="Force re-seeding of demo data")
    parser.add_argument("--backend", action="store_true", help="Run only FastAPI backend")
    parser.add_argument("--dashboard", action="store_true", help="Run only Streamlit dashboard")
    args = parser.parse_args()

    run_init_and_seed(force_seed=args.seed)

    processes = []

    try:
        sub_env = os.environ.copy()
        sub_env["PYTHONUTF8"] = "1"
        sub_env["PYTHONIOENCODING"] = "utf-8"
        sub_env["DEMO_MODE"] = "true"
        sub_env["JA_ASSURE_DB_PATH"] = str(DEMO_DB_PATH)

        # Launch Backend
        if not args.dashboard:
            print("\n[Launcher] 🚀 Starting FastAPI Backend on http://127.0.0.1:8000 ...")
            backend_cmd = [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
                "--log-level",
                "info",
            ]
            p_backend = subprocess.Popen(backend_cmd, cwd=str(PROJECT_ROOT), env=sub_env)
            processes.append(p_backend)

        # Launch Streamlit Dashboard
        if not args.backend:
            # Short sleep to give backend a head start
            time.sleep(1.0)
            print("\n[Launcher] 🎨 Starting Streamlit Review Dashboard on http://localhost:8501 ...")
            dashboard_cmd = [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "dashboard/app.py",
                "--server.port",
                "8501",
                "--server.headless",
                "true",
            ]
            p_dashboard = subprocess.Popen(dashboard_cmd, cwd=str(PROJECT_ROOT), env=sub_env)
            processes.append(p_dashboard)

        print("\n" + "=" * 65)
        print("  JA ASSURE AI MARKETING AGENT RUNNING (DEMO WORKSPACE)")
        print(f"  - Database: {DEMO_DB_PATH}")
        print("  - Streamlit Dashboard: http://localhost:8501")
        print("  - FastAPI Docs (Swagger): http://127.0.0.1:8000/docs")
        print("  Press Ctrl+C to stop all services.")
        print("=" * 65 + "\n")

        # Keep parent alive while children run
        while True:
            time.sleep(1)
            for p in processes:
                if p.poll() is not None:
                    print(f"[Launcher] Process {p.pid} terminated unexpectedly.")
                    return

    except KeyboardInterrupt:
        print("\n[Launcher] Shutting down services...")
        for p in processes:
            p.terminate()
            p.wait()
        print("[Launcher] Services stopped cleanly. Goodbye!")


if __name__ == "__main__":
    main()
