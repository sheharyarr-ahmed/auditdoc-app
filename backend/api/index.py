"""Vercel Python serverless entry point.

Vercel discovers `app` here; the `vercel.json` rewrites all paths to /api,
which routes through this module. The actual FastAPI app and routes live in
`main.py` at the backend root — we just put the parent directory on
sys.path and re-export the app instance.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app  # noqa: E402  (sys.path mutation must precede import)

__all__ = ["app"]
