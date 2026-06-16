from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from backend.adapters.osa import AlertSeed, MockOSAAdapter, StoreSeed  # noqa: E402


def build_demo_seed() -> dict[str, Any]:
    adapter = MockOSAAdapter()
    stores = [_serialize_seed(row) for row in adapter.stores]
    alerts = [_serialize_seed(row) for row in adapter.alerts]
    reps = sorted({str(store["rep_id"]) for store in stores})
    territories = sorted({str(store["territory_code"]) for store in stores})
    manifest = {
        "territories": territories,
        "reps": reps,
        "store_count": len(stores),
        "alert_count": len(alerts),
        "stores_per_rep": {
            rep_id: len([store for store in stores if store["rep_id"] == rep_id])
            for rep_id in reps
        },
        "alerts_per_store_min": min(_alert_count_for_store(alerts, store["store_id"]) for store in stores),
        "alerts_per_store_max": max(_alert_count_for_store(alerts, store["store_id"]) for store in stores),
        "stable_alert_id_format": "{store_id}:{sku_id}:{prediction_date}",
        "source": "backend.adapters.osa.MockOSAAdapter",
        "public_safe": True,
    }
    return {
        "manifest": manifest,
        "stores": stores,
        "alerts": alerts,
    }


def write_artifacts(seed: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "demo_seed_manifest.json").write_text(
        json.dumps(seed["manifest"], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "store_master_seed.json").write_text(
        json.dumps(seed["stores"], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "oos_alert_seed.json").write_text(
        json.dumps(seed["alerts"], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "demo_seed_manifest.md").write_text(_manifest_markdown(seed["manifest"]), encoding="utf-8")


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if manifest["territories"] != ["WEST-01"]:
        failures.append("Expected exactly territory WEST-01")
    if len(manifest["reps"]) < 3 or len(manifest["reps"]) > 5:
        failures.append("Expected 3 to 5 demo reps")
    if manifest["store_count"] < 15 or manifest["store_count"] > 25:
        failures.append("Expected 15 to 25 demo stores")
    if manifest["alert_count"] < 100:
        failures.append("Expected at least 100 OOS alert rows")
    if manifest["alerts_per_store_min"] < 1:
        failures.append("Expected every seeded store to have at least one alert")
    return failures


def _serialize_seed(row: StoreSeed | AlertSeed) -> dict[str, Any]:
    if not is_dataclass(row):
        raise TypeError(f"Unsupported seed row: {type(row).__name__}")
    payload = asdict(row)
    if isinstance(row, AlertSeed):
        payload["alert_id"] = row.alert_id
    return {key: _serialize_value(value) for key, value in payload.items()}


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def _alert_count_for_store(alerts: list[dict[str, Any]], store_id: str) -> int:
    return len([alert for alert in alerts if alert["store_id"] == store_id])


def _manifest_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Demo Seed Manifest",
        "",
        f"- Source: `{manifest['source']}`",
        f"- Public safe: `{manifest['public_safe']}`",
        f"- Territories: `{', '.join(manifest['territories'])}`",
        f"- Reps: `{', '.join(manifest['reps'])}`",
        f"- Stores: `{manifest['store_count']}`",
        f"- Alerts: `{manifest['alert_count']}`",
        f"- Stable alert ID: `{manifest['stable_alert_id_format']}`",
        "",
        "## Stores Per Rep",
        "",
        "| Rep | Stores |",
        "|---|---:|",
    ]
    for rep_id, count in manifest["stores_per_rep"].items():
        lines.append(f"| {rep_id} | {count} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export deterministic public-safe PHANTOM demo seed artifacts.")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/demo-data"))
    args = parser.parse_args()

    seed = build_demo_seed()
    write_artifacts(seed, args.output_dir)
    failures = validate_manifest(seed["manifest"])
    print(json.dumps(seed["manifest"], indent=2, sort_keys=True))
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
