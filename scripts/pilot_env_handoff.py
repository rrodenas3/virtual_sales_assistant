from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from backend.governance.activation_evidence import PILOT_VALIDATION_ENV_KEYS  # noqa: E402


ALLOWED_ENV_KEYS = set(PILOT_VALIDATION_ENV_KEYS)


def build_handoff(ai_demo_env_path: Path | None, live_data_env_path: Path | None) -> dict[str, Any]:
    sources = []
    env: dict[str, Any] = {}
    missing_sources = []
    for label, path in (("ai_demo", ai_demo_env_path), ("live_data", live_data_env_path)):
        if path is None or not path.exists():
            missing_sources.append(label)
            continue
        payload = _read_env_json(path)
        unknown_keys = sorted(set(payload) - ALLOWED_ENV_KEYS)
        if unknown_keys:
            raise SystemExit(f"{path.name} contains unsupported public handoff keys: {unknown_keys}")
        env.update(payload)
        sources.append({"name": label, "path": path.as_posix(), "keys": sorted(payload)})

    missing_keys = sorted(ALLOWED_ENV_KEYS - set(env))
    return {
        "ready": not missing_sources and not missing_keys,
        "env": env,
        "sources": sources,
        "missing_sources": missing_sources,
        "missing_keys": missing_keys,
    }


def write_artifacts(handoff: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "pilot_env_handoff.json").write_text(
        json.dumps(handoff, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    env_lines = [f"{key}={_format_env_value(value)}" for key, value in sorted(handoff["env"].items())]
    (output_dir / "pilot_validation.env.snippet").write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    lines = [
        "# Pilot Validation Env Handoff",
        "",
        f"- Ready: `{handoff['ready']}`",
        f"- Missing sources: `{', '.join(handoff['missing_sources']) or 'none'}`",
        f"- Missing keys: `{', '.join(handoff['missing_keys']) or 'none'}`",
        "",
        "## Environment Values",
        "",
    ]
    lines.extend(f"- `{key}`: `{value}`" for key, value in sorted(handoff["env"].items()))
    (output_dir / "pilot_env_handoff.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_env_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path.name} must contain a JSON object.")
    return payload


def _format_env_value(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge PHANTOM public-safe pilot validation env evidence.")
    parser.add_argument("--ai-demo-env", type=Path, default=Path("artifacts/eval-ai/ai_demo_eval_env.json"))
    parser.add_argument("--live-data-env", type=Path, default=Path("artifacts/contracts/live/readiness_env.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/pilot-env"))
    args = parser.parse_args()

    handoff = build_handoff(args.ai_demo_env, args.live_data_env)
    write_artifacts(handoff, args.output_dir)
    print(json.dumps(handoff, indent=2, sort_keys=True))
    if not handoff["ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
