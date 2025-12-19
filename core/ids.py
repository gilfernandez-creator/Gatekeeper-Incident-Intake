# core/ids.py
from __future__ import annotations

import secrets
from datetime import datetime, timezone


def new_run_id(prefix: str = "gk") -> str:
    # Example: gk_20251218T013045Z_8f2c1a9b
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rnd = secrets.token_hex(4)
    return f"{prefix}_{ts}_{rnd}"
