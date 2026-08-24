from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent / "backend"
if BACKEND.exists() and str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
