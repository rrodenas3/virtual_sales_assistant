"""Mock-backed MCP tool function modules for the VSA MVP."""

from pathlib import Path
import sys

BACKEND_PATH = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))
