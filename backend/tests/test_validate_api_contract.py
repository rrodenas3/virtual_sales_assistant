import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate_api_contract import REQUIRED_ROUTES, _contract_from_routes, write_artifacts  # noqa: E402
from scripts.validate_api_contract import build_local_contract  # noqa: E402


def test_api_index_and_validator_share_pilot_route_contract() -> None:
    from backend.api.contract import PILOT_ROUTE_SIGNATURES  # noqa: PLC0415

    assert REQUIRED_ROUTES == set(PILOT_ROUTE_SIGNATURES)


def test_local_api_contract_contains_pilot_routes() -> None:
    contract = build_local_contract()

    assert contract["valid"] is True
    assert contract["missing_required_routes"] == []
    assert contract["missing_required_query_params"] == []
    assert contract["missing_required_response_fields"] == []
    assert "GET /api/v1/integrations/readiness" in contract["available_routes"]
    assert "GET /api/v1/integrations/readiness" in contract["required_routes"]
    assert "GET /api/v1/integrations/pilot-gap-report?target=local" in contract["required_routes"]
    assert "GET /api/v1/integrations/activation-runbook?target=pilot" in contract["required_routes"]
    assert "GET /api/v1/manager/approval-queue?territory_code=WEST-01" in REQUIRED_ROUTES
    assert "GET /api/v1/manager/my-tasks?status=OPEN" in REQUIRED_ROUTES
    assert "GET /api/v1/admin/audit-events?event_type=&rep_id=&resource_type=&limit=&cursor=" in REQUIRED_ROUTES
    assert "GET /api/v1/stores/{store_id}/alerts?limit=50&cursor=&min_risk_score=0.7" in REQUIRED_ROUTES
    assert "POST /api/v1/orders/drafts/{draft_id}/submit-sandbox" in REQUIRED_ROUTES
    assert len(REQUIRED_ROUTES) >= 35
    assert "activation_evidence_manifests" in contract["required_response_fields"]["IntegrationReadinessResponse"]
    assert "blocking_gaps" in contract["required_response_fields"]["PilotGapReportResponse"]
    assert "phases" in contract["required_response_fields"]["ActivationRunbookResponse"]


def test_api_contract_writes_handoff_artifacts(tmp_path: Path) -> None:
    contract = build_local_contract()

    write_artifacts(contract, tmp_path)

    assert json.loads((tmp_path / "api_contract_report.json").read_text(encoding="utf-8"))["valid"] is True
    markdown = (tmp_path / "api_contract_report.md").read_text(encoding="utf-8")
    assert markdown.startswith("# API Contract Report")
    assert "GET /api/v1/integrations/readiness" in markdown
    assert "GET /api/v1/integrations/pilot-gap-report?target" in markdown
    assert "GET /api/v1/integrations/activation-runbook?target" in markdown
    assert "Missing required query params: `none`" in markdown
    assert "Missing required response fields: `none`" in markdown
    assert "## Available Routes" in markdown
    assert "GET /api/v1/manager/tasks?status&territory_code" in markdown
    assert "GET /api/v1/admin/audit-events?cursor&event_type&limit&rep_id&resource_type" in markdown


def test_api_contract_failure_artifact_lists_missing_detail(tmp_path: Path) -> None:
    contract = _contract_from_routes(["GET /api/v1/health"], source="test_source")

    write_artifacts(contract, tmp_path)

    assert contract["valid"] is False
    markdown = (tmp_path / "api_contract_report.md").read_text(encoding="utf-8")
    assert "## Failure Detail" in markdown
    assert "### Missing Routes" in markdown
    assert "POST /api/v1/agent/run" in markdown
    assert "GET /api/v1/stores/{store_id}/alerts?limit=50&cursor=&min_risk_score=0.7" in markdown
    assert "### Missing Response Fields" in markdown
    assert "IntegrationReadinessResponse.activation_evidence_manifests" in markdown
    assert "## Available Routes" in markdown


def test_api_contract_detects_missing_required_response_fields() -> None:
    schema = {
        "components": {
            "schemas": {
                "IntegrationReadinessResponse": {"properties": {"summary_provider": {"type": "string"}}},
                "ActivationEvidenceManifestOut": {"properties": {"target": {"type": "string"}}},
                "ActivationEvidenceSectionOut": {"properties": {"name": {"type": "string"}}},
                "PilotGapReportResponse": {"properties": {"target": {"type": "string"}}},
                "ActivationRunbookResponse": {"properties": {"current_target": {"type": "string"}}},
            }
        }
    }

    contract = _contract_from_routes(sorted(REQUIRED_ROUTES), source="test_source", schema=schema)

    assert contract["valid"] is False
    assert "IntegrationReadinessResponse.activation_evidence_manifests" in contract["missing_required_response_fields"]
    assert "ActivationEvidenceManifestOut.sections" in contract["missing_required_response_fields"]
    assert "ActivationEvidenceSectionOut.artifacts" in contract["missing_required_response_fields"]
    assert "PilotGapReportResponse.blocking_gaps" in contract["missing_required_response_fields"]
    assert "ActivationRunbookResponse.phases" in contract["missing_required_response_fields"]
