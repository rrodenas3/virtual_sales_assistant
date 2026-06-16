from __future__ import annotations

from typing import Any, Literal

from scripts.ai_demo_eval_evidence import evidence_env_manifest
from scripts.pilot_env_handoff import ALLOWED_ENV_KEYS
from scripts.validate_live_data_contracts import readiness_env_manifest

Target = Literal["local", "ai-demo", "pilot"]


def build_evidence_manifest(target: Target) -> dict[str, Any]:
    """Return the public-safe evidence files and env keys required for a target."""
    sections: list[dict[str, Any]] = [
        {
            "name": "local_scaffold",
            "required_for": ["local", "ai-demo", "pilot"],
            "artifacts": [
                "local-handoff/local_handoff.json",
                "local-handoff/spec-decision-guard/spec_decision_guard.json",
                "local-handoff/readiness-bundle/readiness_bundle.json",
            ],
            "env_keys": {},
            "notes": "Local scaffold proof must stay green for every target.",
        }
    ]
    if target in {"ai-demo", "pilot"}:
        sections.append(
            {
                "name": "ai_demo_eval",
                "required_for": ["ai-demo", "pilot"],
                "artifacts": [
                    "eval-ai/osa_eval_results.json",
                    "eval-ai/mlflow_handoff.json",
                    "eval-ai/ai_demo_eval_evidence.json",
                    "eval-ai/ai_demo_eval_env.json",
                    "load/summary/load_test_report.json",
                ],
                "env_keys": evidence_env_manifest(),
                "notes": "Generated only after the approved Anthropic provider eval and summary load test pass.",
            }
        )
    if target == "pilot":
        sections.extend(
            [
                {
                    "name": "live_data_contracts",
                    "required_for": ["pilot"],
                    "artifacts": [
                        "contracts/live/live_data_contract_report.json",
                        "contracts/live/readiness_env.json",
                    ],
                    "env_keys": readiness_env_manifest(),
                    "notes": "Generated only in an approved credentialed environment.",
                },
                {
                    "name": "provider_dry_runs",
                    "required_for": ["pilot"],
                    "artifacts": [
                        "unity-audit-smoke/unity_audit_smoke.json",
                        "action-provider-smoke/action_provider_smoke.json",
                        "guardrail-classifier-smoke/guardrail_classifier_smoke.json",
                        "memory-provider-smoke/memory_provider_smoke.json",
                    ],
                    "env_keys": {},
                    "notes": "Dry-run proof for live write, audit, guardrail, and memory contracts before credentialed smoke.",
                },
                {
                    "name": "pilot_env_handoff",
                    "required_for": ["pilot"],
                    "artifacts": [
                        "pilot-env/pilot_env_handoff.json",
                        "pilot-env/pilot_validation.env.snippet",
                    ],
                    "env_keys": {key: "public-safe pilot validation evidence" for key in sorted(ALLOWED_ENV_KEYS)},
                    "notes": "Merges non-secret AI-demo and live-data validation values for approved runtime configuration.",
                },
            ]
        )

    required_env_keys = sorted({key for section in sections for key in section["env_keys"]})
    required_artifacts = [artifact for section in sections for artifact in section["artifacts"]]
    return {
        "target": target,
        "sections": sections,
        "required_env_keys": required_env_keys,
        "required_artifacts": required_artifacts,
    }
