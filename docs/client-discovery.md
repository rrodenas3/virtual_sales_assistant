# Client Discovery Gate

These items must be answered before Phase 2 production write-back.

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
| Rep device | `DISCOVERY_REP_DEVICE` | Defaulted to `PWA` | Offline runtime decisions |
| SSO provider | `DISCOVERY_SSO_PROVIDER` | TBD | External JWT |
| Data residency | `DISCOVERY_DATA_RESIDENCY` | TBD | Databricks, Snowflake, Unity Catalog |
| Offline sync policy | `DISCOVERY_OFFLINE_SYNC_POLICY` | Defaulted to browser feedback queue | Offline write expansion |

Live-mode selectors currently gated:

- `AUTH_PROVIDER=external_jwt`
- `OSA_ADAPTER=databricks`
- `RGM_ADAPTER=databricks`
- `STORE_MASTER_ADAPTER=snowflake`
- `AUDIT_SINK=unity_catalog`
