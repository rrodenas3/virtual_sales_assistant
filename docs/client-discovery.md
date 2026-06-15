# Client Discovery Gate

These items must be answered before Phase 2 production write-back.

Owner model:

- Client delivery owner: supplies platform answers, credentials through approved secret channels, view names, OAuth details, and pilot territory scope.
- Engineering owner: maintains readiness gates, validation scripts, redacted diagnostics, and adapter implementations.

The backend exposes the current gate state at:

```text
GET /api/v1/integrations/readiness
```

The endpoint is manager/admin-only. Local mock mode can remain ready with several unanswered gates because no live integration is selected. When a live mode is selected, the relevant gates become blockers before provider setup or query execution.

| Topic | Setting | Status | Blocks |
|---|---|---|---|
| Data sharing model | `DISCOVERY_DATA_SHARING_MODEL` | TBD | Databricks, Snowflake, Unity Catalog |
| CRM platform + OAuth | `DISCOVERY_CRM_PLATFORM` | TBD | CRM write-back |
| ERP sandbox endpoint | `DISCOVERY_ERP_SANDBOX` | TBD | Real ERP submit |
| Pilot territory | `DISCOVERY_PILOT_TERRITORY` | Defaulted to `WEST-01` | All live modes |
| Rep device | `DISCOVERY_REP_DEVICE` | Defaulted to `PWA` | Offline runtime decisions, shelf-image capture/runtime |
| SSO provider | `DISCOVERY_SSO_PROVIDER` | TBD | External JWT |
| Data residency | `DISCOVERY_DATA_RESIDENCY` | TBD | Databricks, Snowflake, Unity Catalog, external shelf-image analysis |
| Offline sync policy | `DISCOVERY_OFFLINE_SYNC_POLICY` | Defaulted to browser feedback queue | Offline write expansion |
| Memory retention policy | `DISCOVERY_MEMORY_RETENTION_POLICY` | TBD | Mem0 |
| Memory scopes | `DISCOVERY_MEMORY_SCOPES` | TBD | Mem0 |

Live-mode selectors currently gated:

- `AUTH_PROVIDER=external_jwt`
- `OSA_ADAPTER=databricks`
- `RGM_ADAPTER=databricks`
- `STORE_MASTER_ADAPTER=snowflake`
- `AUDIT_SINK=unity_catalog`
- `MEMORY_PROVIDER=mem0`
- `SHELF_IMAGE_ADAPTER=external`

Live data contract validation:

```powershell
python scripts/validate_live_data_contracts.py --manifest-only
python scripts/validate_live_data_contracts.py --territory-code WEST-01 --rep-id REP-001 --store-id ST-001 --output-dir artifacts/contracts/live
```

The manifest command is safe for CI and public review. The live command must only run in a client-approved environment with credentials supplied outside the repository. It writes `live_data_contract_report.json`, `live_data_contract_report.md`, and `readiness_env.json`. Results can be summarized in:

- `LIVE_DATA_CONTRACT_VALIDATED`
- `LIVE_DATA_CONTRACT_LAST_VALIDATION_AT`
- `LIVE_DATA_CONTRACT_VALIDATION_SUMMARY`
