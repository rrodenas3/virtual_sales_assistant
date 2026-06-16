from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.governance.discovery_packet import build_discovery_packet  # noqa: E402

Target = Literal["local", "ai-demo", "pilot"]


def build_report(target: Target) -> dict[str, Any]:
    return build_discovery_packet(target)


def write_artifacts(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "discovery_packet.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "discovery_packet.md").write_text(_markdown(report), encoding="utf-8")


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Discovery Packet",
        "",
        f"- Target: `{report['target']}`",
        f"- Selected live modes: `{', '.join(report['selected_live_modes']) or 'none'}`",
        f"- Missing gates: `{report['missing_count']}`",
        f"- Defaulted gates: `{report['defaulted_count']}`",
        "",
        "## Owner Groups",
        "",
        "| Owner | Gates | Missing | Defaulted |",
        "|---|---:|---:|---:|",
    ]
    for group in report["owner_groups"]:
        lines.append(
            f"| {group['owner']} | {group['gate_count']} | {group['missing_count']} | {group['defaulted_count']} |"
        )
    lines.extend(["", "## Gate Detail", "", "| Owner | Setting | Status | Required for | Notes |", "|---|---|---|---|---|"])
    for group in report["owner_groups"]:
        for gate in group["gates"]:
            required_for = ", ".join(gate["required_for"])
            notes = str(gate["notes"]).replace("|", "\\|")
            lines.append(
                f"| {group['owner']} | `{gate['setting_name']}` | {gate['status']} | {required_for} | {notes} |"
            )
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {action}" for action in report["next_actions"])
    lines.extend(["", "## Public Safety", ""])
    lines.extend(f"- {note}" for note in report["public_safety_notes"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a public-safe client discovery packet.")
    parser.add_argument("--target", choices=["local", "ai-demo", "pilot"], default="pilot")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/discovery-packet"))
    args = parser.parse_args()

    report = build_report(args.target)  # type: ignore[arg-type]
    write_artifacts(report, args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
