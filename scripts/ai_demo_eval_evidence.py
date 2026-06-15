from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


REQUIRED_PROVIDER = "anthropic"


def evidence_env_manifest() -> dict[str, str]:
    return {
        "AI_DEMO_EVAL_VALIDATED": "true only after the approved provider eval passes",
        "AI_DEMO_EVAL_LAST_VALIDATION_AT": "UTC timestamp from the approved provider eval run",
        "AI_DEMO_EVAL_VALIDATION_SUMMARY": "short eval summary copied from ai_demo_eval_env.json",
    }


def evidence_from_eval_result(eval_result: dict[str, Any], validated_at: str | None = None) -> dict[str, Any]:
    summary = eval_result.get("summary", {})
    if not isinstance(summary, dict):
        raise SystemExit("osa_eval_results.json must contain a summary object.")

    providers = [str(provider) for provider in summary.get("providers", [])]
    models = [str(model) for model in summary.get("models", [])]
    passed = bool(eval_result.get("passed"))
    provider_present = REQUIRED_PROVIDER in providers
    generated_at = validated_at or datetime.now(UTC).isoformat()
    validation_summary = (
        f"provider={REQUIRED_PROVIDER}; models={','.join(models) or 'unknown'}; "
        f"p95_ms={summary.get('p95_latency_ms', 'unknown')}; "
        f"trace={summary.get('trace_completeness', 'unknown')}; "
        f"cost_eur={summary.get('max_estimated_cost_eur', 'unknown')}"
    )
    blockers = []
    if not passed:
        blockers.append("eval did not pass")
    if not provider_present:
        blockers.append(f"provider={REQUIRED_PROVIDER} not present")

    return {
        "valid": passed and provider_present,
        "generated_at": generated_at,
        "required_provider": REQUIRED_PROVIDER,
        "providers": providers,
        "models": models,
        "blockers": blockers,
        "env": {
            "AI_DEMO_EVAL_VALIDATED": passed and provider_present,
            "AI_DEMO_EVAL_LAST_VALIDATION_AT": generated_at,
            "AI_DEMO_EVAL_VALIDATION_SUMMARY": validation_summary,
        },
    }


def build_evidence(artifact_dir: Path, validated_at: str | None = None) -> dict[str, Any]:
    eval_path = artifact_dir / "osa_eval_results.json"
    if not eval_path.exists():
        raise SystemExit(f"Missing {eval_path.name}. Run scripts/run_eval.py first.")
    eval_result = json.loads(eval_path.read_text(encoding="utf-8"))
    if not isinstance(eval_result, dict):
        raise SystemExit(f"{eval_path.name} must contain a JSON object.")
    return evidence_from_eval_result(eval_result, validated_at=validated_at)


def write_artifacts(evidence: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "ai_demo_eval_evidence.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "ai_demo_eval_env.json").write_text(
        json.dumps(evidence["env"], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    env_lines = [
        f"{key}={str(value).lower() if isinstance(value, bool) else value}"
        for key, value in evidence["env"].items()
    ]
    (output_dir / "ai_demo_eval.env.snippet").write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    lines = [
        "# AI Demo Eval Evidence",
        "",
        f"- Generated at: `{evidence['generated_at']}`",
        f"- Valid: `{evidence['valid']}`",
        f"- Required provider: `{evidence['required_provider']}`",
        f"- Providers: `{', '.join(evidence['providers']) or 'none'}`",
        f"- Models: `{', '.join(evidence['models']) or 'none'}`",
        f"- Blockers: `{', '.join(evidence['blockers']) or 'none'}`",
        "",
        "## Environment Values",
        "",
    ]
    lines.extend(f"- `{key}`: `{value}`" for key, value in evidence["env"].items())
    (output_dir / "ai_demo_eval_evidence.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PHANTOM AI-demo eval readiness evidence.")
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--validated-at", default=None, help="Optional UTC timestamp override for repeatable artifacts.")
    args = parser.parse_args()

    evidence = build_evidence(args.artifact_dir, validated_at=args.validated_at)
    if args.output_dir:
        write_artifacts(evidence, args.output_dir)
    print(json.dumps(evidence, indent=2, sort_keys=True))
    if not evidence["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
