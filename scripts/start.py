#!/usr/bin/env python3
"""Start AI Career Helper with one command, on Windows, macOS, or Linux.

    python scripts/start.py            # mock mode, no LLM calls
    python scripts/start.py --llm      # enable real LLM integration
    python scripts/start.py --rebuild  # force a fresh frontend build

The script installs any missing backend/frontend dependencies, builds the Vite
frontend if needed, then runs the FastAPI server. FastAPI serves *both* the
`/v1` API and the built frontend, so the whole app is one process at
http://127.0.0.1:8000/.

Because that is a single foreground process, stopping is just Ctrl-C -- there is
no separate stop script and nothing is left running in the background.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from shutil import which

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
HOST = "127.0.0.1"
PORT = "8000"
# npm ships as npm.cmd on Windows; the bare name works on macOS/Linux.
NPM = "npm.cmd" if os.name == "nt" else "npm"

# Let `import app.*` work when this file is run as `python scripts/start.py`.
sys.path.insert(0, str(ROOT))


def run(cmd: list[str], **kwargs) -> None:
    """Run a command, streaming its output, and abort the script if it fails."""
    printable = " ".join(str(c) for c in cmd)
    print(f"\n> {printable}", flush=True)
    if subprocess.run(cmd, **kwargs).returncode != 0:
        sys.exit(f"Command failed: {printable}")


def ensure_backend_deps(with_llm: bool) -> None:
    """Install runtime deps if uvicorn is missing, plus AI deps when requested."""
    try:
        import uvicorn  # noqa: F401
    except ModuleNotFoundError:
        run([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])
    if with_llm:
        run([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements-ai.txt")])


def ensure_frontend_build(rebuild: bool) -> None:
    """Install node deps if absent and build the frontend if dist/ is missing."""
    if which(NPM) is None:
        sys.exit("npm was not found on PATH. Install Node.js 20+ and re-run.")
    if not (FRONTEND / "node_modules").exists():
        run([NPM, "ci"], cwd=FRONTEND)
    if rebuild or not (FRONTEND / "dist" / "index.html").exists():
        run([NPM, "run", "build"], cwd=FRONTEND)


def check_llm_connectivity() -> None:
    """Make one real model call so a bad key/URL/network aborts before startup."""
    from app.core.config import settings

    if not settings.llm_api_key:
        sys.exit("--llm requires CAREER_LLM_API_KEY. Set it in .env and re-run.")

    from app.llm.models import Purpose, get_llm

    print(f"Checking LLM connectivity (model={settings.llm_cv_model})...", flush=True)
    try:
        response = get_llm(Purpose.CV).invoke("Reply with exactly the word: pong")
    except Exception as exc:  # noqa: BLE001 - any failure here means we must not start
        sys.exit(f"LLM connectivity check failed: {exc}\nStartup aborted.")

    text = getattr(response, "content", response)
    if not isinstance(text, str) or not text.strip():
        sys.exit("LLM connectivity check failed: empty response. Startup aborted.")
    print(f"LLM connectivity OK (reply: {text.strip()!r}).", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Start AI Career Helper (API + built frontend).")
    parser.add_argument(
        "--llm", action="store_true", help="Enable real LLM integration (needs CAREER_LLM_API_KEY)."
    )
    parser.add_argument(
        "--rebuild", action="store_true", help="Rebuild the frontend even if dist/ exists."
    )
    args = parser.parse_args()

    # Force the mode for this run so a stray shell variable can't flip it.
    os.environ["CAREER_ENABLE_REAL_AI"] = "true" if args.llm else "false"

    ensure_backend_deps(args.llm)
    if args.llm:
        check_llm_connectivity()
    ensure_frontend_build(args.rebuild)

    print(
        f"\nAI Career Helper: http://{HOST}:{PORT}/   (docs at /docs, Ctrl-C to stop)\n", flush=True
    )
    try:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", HOST, "--port", PORT],
            cwd=ROOT,
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
