# PHANTOM Spec Corrections

These corrections permanently override the original internal MVP brief for implementation.

1. `store_master` must include `promo_compliance_rate` and `revenue_opportunity_score`, because the priority formula depends on them.
2. `oos_risk` must include `territory_code` and `rep_id`, because OSA reads are territory- and identity-scoped.
3. SQL must not be built through string interpolation. All future Databricks/Snowflake adapters must use parameterized statements or validated typed query builders.
4. The OSA agent pseudocode that iterates `response.content` as if it contains executed tool messages is invalid. Phase 1 keeps deterministic data retrieval outside the LLM path.
5. The Phase 1 UX is workbench-first. Copilot-style chat can be secondary after the operational route and alert workflow works.
6. Audit data is append-only. Approval decisions live in separate append-only rows.
7. Read paths set `requires_approval=false`. Approval is only for write actions introduced in Phase 2+.
8. There is no `backend/mcp_servers/` directory. Standalone servers live under `mcp/`; backend adapters and clients live under `backend/adapters/` and `backend/clients/`.
