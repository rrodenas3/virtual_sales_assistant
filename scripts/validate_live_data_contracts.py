from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from backend.clients.sql import DatabricksSQLClient, SnowflakeSQLClient  # noqa: E402
from backend.config import settings  # noqa: E402
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
    return {"valid": all(result["valid"] for result in results), "results": results}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate PHANTOM live data view contracts.")
    parser.add_argument("--manifest-only", action="store_true", help="Print required contract manifests and exit.")
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
        print(json.dumps({"contracts": contract_manifest()}, indent=2, sort_keys=True))
        return
    output = asyncio.run(_run_live(args))
    print(json.dumps(output, indent=2, sort_keys=True))
    if not output["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
