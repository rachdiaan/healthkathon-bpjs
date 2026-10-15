"""Versi aplikasi dan git SHA (dipakai /api/health dan engine_version batch, FR-25)."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

VERSION = "2.0.0-dev"
ROOT = Path(__file__).resolve().parent.parent


def _git_sha() -> str:
    sha = os.environ.get("GIT_SHA") or os.environ.get("RENDER_GIT_COMMIT")
    if sha:
        return sha[:12]
    try:
        out = subprocess.run(  # nosec B603 B607
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, timeout=2, check=True,
        )
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


GIT_SHA = _git_sha()
