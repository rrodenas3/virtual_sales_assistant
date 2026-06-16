from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from backend.governance.activation_evidence import build_evidence_manifest  # noqa: E402,F401
