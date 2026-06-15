from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from backend.clients.sql import QueryStatement  # noqa: E402
from backend.db.models import AuditEvent  # noqa: E402
from backend.services.audit_sinks import (  # noqa: E402
    UNITY_AUDIT_AGENT_ACTION_COLUMNS,
    UNITY_AUDIT_APPROVAL_DECISION_COLUMNS,
    validate_unity_table_name,
    write_unity_catalog_event,
)


class CaptureSQLClient:
    def __init__(self) -> None:
        self.queries: list[QueryStatement] = []

    async def execute(self, query: QueryStatement) -> list[dict]:
        self.queries.append(query)
        return []


async def build_smoke(table_name: str) -> dict[str, Any]:
    table_name = validate_unity_table_name(table_name)
    client = CaptureSQLClient()
    event = AuditEvent(
        event_id="audit-smoke-1",
        session_id="unity-smoke-session",
        rep_id="REP-001",
        event_type="osa_summary_created",
        resource_type="agent_summary",
        resource_id="ST-001",
        payload_json={
            "tool_name": "osa_summary",
            "territory_code": "WEST-01",
            "model_id": "grounded-template-v1",
            "model_version": "mock-v1",
            "reasoning_trace": "dry-run",
        },
        source_system="mock",
        data_freshness_ts=datetime(2026, 6, 15, tzinfo=UTC),
        created_at=datetime(2026, 6, 15, tzinfo=UTC),
    )
    await write_unity_catalog_event(client, table_name=table_name, event=event, payload_json=event.payload_json)
    query = client.queries[0]
    ddl_status = _ddl_status(table_name)
    parameter_names = [parameter.name for parameter in query.parameters]
    missing_parameters = sorted(set(UNITY_AUDIT_AGENT_ACTION_COLUMNS) - set(parameter_names))
    return {
        "valid": not missing_parameters and ddl_status["valid"],
        "table_name": table_name,
        "statement_preview": query.statement,
        "parameter_names": parameter_names,
        "missing_parameters": missing_parameters,
        "ddl": ddl_status,
        "dry_run_only": True,
    }


def write_artifacts(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "unity_audit_smoke.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Unity Audit Smoke",
        "",
        f"- Table: `{report['table_name']}`",
        f"- Valid: `{report['valid']}`",
        f"- Dry run only: `{report['dry_run_only']}`",
        f"- Missing parameters: `{', '.join(report['missing_parameters']) or 'none'}`",
        f"- DDL valid: `{report['ddl']['valid']}`",
        "",
        "## Parameter Names",
        "",
    ]
    lines.extend(f"- `{name}`" for name in report["parameter_names"])
    (output_dir / "unity_audit_smoke.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _ddl_status(table_name: str) -> dict[str, Any]:
    ddl_path = ROOT / "infra" / "databricks" / "audit_table_ddl.sql"
    ddl = ddl_path.read_text(encoding="utf-8")
    agent_columns = _ddl_columns(ddl, table_name)
    approval_table = table_name.rsplit(".", 1)[0] + ".approval_decisions"
    approval_columns = _ddl_columns(ddl, approval_table)
    return {
        "valid": agent_columns == list(UNITY_AUDIT_AGENT_ACTION_COLUMNS)
        and approval_columns == list(UNITY_AUDIT_APPROVAL_DECISION_COLUMNS)
        and "delta.appendOnly = true" in ddl,
        "agent_columns": agent_columns,
        "approval_columns": approval_columns,
        "append_only": "delta.appendOnly = true" in ddl,
    }


def _ddl_columns(ddl: str, table_name: str) -> list[str]:
    start = ddl.index(f"CREATE TABLE IF NOT EXISTS {table_name} (")
    body = ddl[start:].split(")", 1)[0].split("(", 1)[1]
    columns = []
    for line in body.splitlines():
        stripped = line.strip().rstrip(",")
        if stripped:
            columns.append(stripped.split()[0])
    return columns


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a dry-run Unity Catalog audit smoke artifact.")
    parser.add_argument("--table-name", default="phantom.audit.agent_actions")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/unity-audit-smoke"))
    args = parser.parse_args()

    report = asyncio.run(build_smoke(args.table_name))
    write_artifacts(report, args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
