from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tests.eval.run_eval import main  # noqa: E402


if __name__ == "__main__":
    main()
