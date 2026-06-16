from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from backend.governance.ai_demo_activation import build_ai_demo_activation_pack  # noqa: E402


def write_ai_demo_activation_pack_artifacts(pack: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "ai_demo_activation_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# AI Demo Activation Pack",
        "",
        f"- Generated at: `{pack['generated_at']}`",
        f"- Ready: `{pack['ready']}`",
        f"- Stage: `{pack['stage']}`",
        f"- Summary provider: `{pack['summary_provider']}`",
        f"- Summary model: `{pack['summary_model_id']}`",
        f"- Provider ready: `{pack['provider_ready']}`",
        f"- Eval validated: `{pack['eval_validated']}`",
        "",
        "## Blockers",
        "",
    ]
    blockers = pack["blockers"] or ["none"]
    lines.extend(f"- `{blocker}`" for blocker in blockers)
    lines.extend(["", "## Configuration Checks", ""])
    for check in pack["config_checks"]:
        value = check.get("public_value")
        if check.get("value_present") is not None:
            value = f"value_present={str(check['value_present']).lower()}"
        lines.append(f"- `{check['name']}`: ready=`{check['ready']}`; {value or 'no public value'}")
    lines.extend(["", "## Required Commands", ""])
    for command in pack["required_commands"]:
        lines.append(f"- `{command['name']}`: `{command['command']}`")
    lines.extend(["", "## Required Artifacts", ""])
    lines.extend(f"- `{artifact}`" for artifact in pack["required_artifacts"])
    lines.extend(["", "## Required Env Evidence Keys", ""])
    lines.extend(f"- `{key}`" for key in pack["required_env_keys"])
    lines.extend(["", "## Public Safety", ""])
    lines.extend(f"- {note}" for note in pack["public_safety_notes"])
    (output_dir / "ai_demo_activation_pack.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the public-safe PHANTOM AI-demo activation pack.")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/ai-demo-activation-pack"))
    args = parser.parse_args()

    pack = build_ai_demo_activation_pack()
    write_ai_demo_activation_pack_artifacts(pack, args.output_dir)
    print(json.dumps(pack, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
