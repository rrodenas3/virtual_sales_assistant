import json
from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.config import settings  # noqa: E402
from backend.governance.ai_demo_activation import build_ai_demo_activation_pack  # noqa: E402
from backend.main import app  # noqa: E402
from scripts.ai_demo_activation_pack import write_ai_demo_activation_pack_artifacts  # noqa: E402


REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."
MANAGER = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJNR1ItMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6Im1hbmFnZXIifQ."


def test_ai_demo_activation_pack_is_public_safe_by_default() -> None:
    pack = build_ai_demo_activation_pack()

    assert pack["target"] == "ai-demo"
    assert pack["ready"] is False
    assert pack["stage"] == "template_scaffold"
    assert "SUMMARY_PROVIDER must be anthropic for AI-demo readiness" in pack["blockers"]
    token_check = next(check for check in pack["config_checks"] if check["name"] == "anthropic_token_ref")
    assert token_check["value_present"] is False
    assert "public_value" not in token_check
    assert any(command["name"] == "ai_summary_eval" for command in pack["required_commands"])
    assert "eval-ai/ai_demo_eval_env.json" in pack["required_artifacts"]
    assert "AI_DEMO_EVAL_VALIDATED" in pack["required_env_keys"]


def test_ai_demo_activation_pack_marks_ready_when_provider_and_evidence_are_ready(monkeypatch) -> None:
    import backend.services.summary_providers as summary_providers

    monkeypatch.setattr(summary_providers, "find_spec", lambda name: object())
    monkeypatch.setattr(settings, "summary_provider", "anthropic")
    monkeypatch.setattr(settings, "anthropic_token_ref", "approved-token-ref")
    monkeypatch.setattr(settings, "summary_fail_open", False)
    monkeypatch.setattr(settings, "agent_run_enabled", True)
    monkeypatch.setattr(settings, "ai_demo_eval_validated", True)
    monkeypatch.setattr(settings, "ai_demo_eval_last_validation_at", "2026-06-16T12:00:00Z")
    monkeypatch.setattr(settings, "ai_demo_eval_validation_summary", "provider=anthropic; p95_ms=900")

    pack = build_ai_demo_activation_pack()

    assert pack["ready"] is True
    assert pack["stage"] == "validated"
    assert pack["blockers"] == []
    token_check = next(check for check in pack["config_checks"] if check["name"] == "anthropic_token_ref")
    assert token_check["value_present"] is True
    assert "approved-token-ref" not in json.dumps(pack)


def test_ai_demo_activation_pack_endpoint_requires_manager() -> None:
    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/integrations/ai-demo-activation-pack")
    assert response.status_code == 403


def test_ai_demo_activation_pack_endpoint_returns_pack() -> None:
    with TestClient(app, headers={"Authorization": f"Bearer {MANAGER}"}) as client:
        response = client.get("/api/v1/integrations/ai-demo-activation-pack")
    assert response.status_code == 200
    body = response.json()
    assert body["target"] == "ai-demo"
    assert body["summary_provider"] == "template"
    assert any(check["name"] == "anthropic_token_ref" for check in body["config_checks"])
    assert "value" not in next(check for check in body["config_checks"] if check["name"] == "anthropic_token_ref")


def test_ai_demo_activation_pack_writes_artifacts(tmp_path: Path) -> None:
    pack = build_ai_demo_activation_pack()

    write_ai_demo_activation_pack_artifacts(pack, tmp_path)

    report = json.loads((tmp_path / "ai_demo_activation_pack.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "ai_demo_activation_pack.md").read_text(encoding="utf-8")
    assert report["target"] == "ai-demo"
    assert markdown.startswith("# AI Demo Activation Pack")
    assert "AI_DEMO_EVAL_VALIDATED" in markdown
    assert "api_key" not in markdown.lower()
