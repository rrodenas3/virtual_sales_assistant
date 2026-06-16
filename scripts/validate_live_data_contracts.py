from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from backend.clients.sql import DatabricksSQLClient, SnowflakeSQLClient  # noqa: E402
from backend.config import settings  # noqa: E402
from backend.governance.activation_evidence import LIVE_DATA_READINESS_ENV_MANIFEST  # noqa: E402
from backend.governance.live_contracts import (  # noqa: E402
    contract_manifest,
    live_data_contracts,
    validate_contract_with_client,
)


async def _run_live(args: argparse.Namespace) -> dict[str, object]:
    contracts = live_data_contracts(
        territory_code=args.territory_code,
        rep_id=args.rep_id,
        store_id=args.store_id,
    )
    results = []
    clients = {
        "databricks": DatabricksSQLClient(settings),
        "snowflake": SnowflakeSQLClient(settings),
    }
    for name in args.contract:
        contract = contracts[name]
        try:
            result = await validate_contract_with_client(
                contract,
                clients[contract.source_system],
                expected_territory_code=args.territory_code,
                expected_rep_id=args.rep_id,
            )
            results.append(result.__dict__)
        except Exception as exc:  # noqa: BLE001 - script must report all contract failures.
            results.append(
                {
                    "name": name,
                    "valid": False,
                    "row_count": 0,
                    "missing_columns": [],
                    "violations": [f"{type(exc).__name__}: {exc}"],
                }
            )
    return {
        "valid": all(result["valid"] for result in results),
        "generated_at": datetime.now(UTC).isoformat(),
        "territory_code": args.territory_code,
        "rep_id": args.rep_id,
        "store_id": args.store_id,
        "results": results,
    }


def _validation_summary(report: dict[str, object]) -> str:
    results = list(report.get("results", []))
    valid_count = sum(1 for result in results if isinstance(result, dict) and result.get("valid"))
    row_count = sum(int(result.get("row_count", 0)) for result in results if isinstance(result, dict))
    return f"{valid_count}/{len(results)} contracts valid; rows={row_count}"


def readiness_env_from_report(report: dict[str, object]) -> dict[str, object]:
    summary = _validation_summary(report)
    generated_at = str(report.get("generated_at", datetime.now(UTC).isoformat()))
    return {
        "LIVE_DATA_CONTRACT_VALIDATED": bool(report.get("valid")),
        "LIVE_DATA_CONTRACT_LAST_VALIDATION_AT": generated_at,
        "LIVE_DATA_CONTRACT_VALIDATION_SUMMARY": summary,
    }


def readiness_env_manifest() -> dict[str, str]:
    return dict(LIVE_DATA_READINESS_ENV_MANIFEST)


def failure_examples() -> dict[str, str]:
    return {
        "missing_columns": "A required column such as territory_code, rep_id, data_freshness_ts, or risk_score is absent.",
        "empty_sample": "The parameterized sample query returns no rows for the pilot territory/rep/store.",
        "filter_leakage": "Rows cross the requested territory_code or rep_id filter.",
        "score_range": "Normalized score columns are not numeric values between 0 and 1.",
        "alert_business_key": "OSA alert rows cannot build the stable store_id:sku_id:prediction_date alert ID.",
    }


def build_manifest_payload() -> dict[str, object]:
    return {
        "contracts": contract_manifest(),
        "readiness_env_manifest": readiness_env_manifest(),
        "failure_examples": failure_examples(),
        "operator_notes": [
            "Run manifest-only mode in public/local environments.",
            "Run credentialed validation only in an approved client environment.",
            "Supply live credentials through the approved runtime secret channel, not through repository files.",
            "Record readiness_env.json values only after all selected contracts validate.",
        ],
    }


def write_manifest_artifacts(manifest: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "live_data_contract_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Live Data Contract Manifest",
        "",
        "This manifest is public-safe. It describes expected columns and validation rules without live credentials.",
        "",
        "## Contracts",
        "",
        "| Contract | Source | Required Columns | Normalized Scores | Non-null Columns |",
        "|---|---|---:|---|---|",
    ]
    contracts = manifest.get("contracts", {})
    if isinstance(contracts, dict):
        for name, contract in contracts.items():
            if not isinstance(contract, dict):
                continue
            normalized = ", ".join(str(item) for item in contract.get("normalized_score_columns", [])) or "none"
            non_null = ", ".join(str(item) for item in contract.get("non_null_columns", [])) or "none"
            lines.append(
                f"| {name} | {contract.get('source_system')} | {len(contract.get('required_columns', []))} | "
                f"{normalized} | {non_null} |"
            )
            required = ", ".join(str(item) for item in contract.get("required_columns", []))
            lines.append(f"|  | required columns |  | {required} |  |")
    lines.extend(["", "## Readiness Environment Keys", ""])
    readiness_manifest = manifest.get("readiness_env_manifest", {})
    if isinstance(readiness_manifest, dict):
        lines.extend(f"- `{key}`: {value}" for key, value in readiness_manifest.items())
    lines.extend(["", "## Common Failure Examples", ""])
    examples = manifest.get("failure_examples", {})
    if isinstance(examples, dict):
        lines.extend(f"- `{key}`: {value}" for key, value in examples.items())
    lines.extend(["", "## Operator Notes", ""])
    notes = manifest.get("operator_notes", [])
    if isinstance(notes, list):
        lines.extend(f"- {note}" for note in notes)
    (output_dir / "live_data_contract_manifest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_artifacts(report: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    readiness_env = readiness_env_from_report(report)
    summary = str(readiness_env["LIVE_DATA_CONTRACT_VALIDATION_SUMMARY"])
    generated_at = str(readiness_env["LIVE_DATA_CONTRACT_LAST_VALIDATION_AT"])
    (output_dir / "live_data_contract_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "readiness_env.json").write_text(
        json.dumps(readiness_env, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Live Data Contract Report",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Valid: `{bool(report.get('valid'))}`",
        f"- Summary: `{summary}`",
        "",
        "| Contract | Valid | Rows | Missing Columns | Violations |",
        "|---|---:|---:|---|---|",
    ]
    for result in report.get("results", []):
        if not isinstance(result, dict):
            continue
        missing = ", ".join(str(item) for item in result.get("missing_columns", [])) or "none"
        violations = "; ".join(str(item) for item in result.get("violations", [])) or "none"
        escaped_missing = missing.replace("|", "\\|")
        escaped_violations = violations.replace("|", "\\|")
        lines.append(
            f"| {result.get('name')} | {bool(result.get('valid'))} | {int(result.get('row_count', 0))} | "
            f"{escaped_missing} | {escaped_violations} |"
        )
    (output_dir / "live_data_contract_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate PHANTOM live data view contracts.")
    parser.add_argument("--manifest-only", action="store_true", help="Print required contract manifests and exit.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Optional directory for validation artifacts.")
    parser.add_argument("--territory-code", default="WEST-01")
    parser.add_argument("--rep-id", default="REP-001")
    parser.add_argument("--store-id", default="ST-001")
    parser.add_argument(
        "--contract",
        action="append",
        choices=sorted(live_data_contracts().keys()),
        default=[],
        help="Contract to validate. Repeat to validate multiple. Defaults to all contracts.",
    )
    return parser


def main() -> None:
    parser = _parser()
    args = parser.parse_args()
    if not args.contract:
        args.contract = sorted(live_data_contracts().keys())
    if args.manifest_only:
        manifest = build_manifest_payload()
        if args.output_dir:
            write_manifest_artifacts(manifest, args.output_dir)
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return
    output = asyncio.run(_run_live(args))
    if args.output_dir:
        write_artifacts(output, args.output_dir)
    print(json.dumps(output, indent=2, sort_keys=True))
    if not output["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
