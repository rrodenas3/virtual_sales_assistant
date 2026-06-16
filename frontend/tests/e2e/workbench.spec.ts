import { expect, test, type Route } from "@playwright/test";

const alertId = "ST-001:SKU-4001:2026-06-15";
const managerTaskId = "work_001";
const adminAuditEvent = {
  event_id: "audit-admin-1",
  session_id: "session-admin",
  rep_id: "REP-001",
  event_type: "osa_summary_created",
  resource_type: "agent_summary",
  resource_id: "ST-001",
  payload_json: { summary_provider: "template" },
  source_system: "mock",
  data_freshness_ts: "2026-06-15T00:00:00Z",
  created_at: "2026-06-15T00:00:00Z"
};

test.use({ serviceWorkers: "block" });

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    window.localStorage.setItem("phantom.demoRole", "rep");
  });

  await page.route("**/api/v1/metrics/pilot", async (route) => {
    await route.fulfill({
      json: {
        feedback_count: 2,
        confirmed_count: 1,
        false_positive_count: 0,
        alert_precision: 0.9,
        summary_count: 1,
        avg_estimated_cost_eur: 0.001,
        trace_event_counts: { visit_priority_read: 1 },
        metrics: []
      }
    });
  });

  await page.route("**/api/v1/visits/today**", async (route) => {
    await route.fulfill({
      json: [
        {
          store_id: "ST-001",
          store_name: "West Market 01",
          address: "101 Commerce Ave",
          priority_score: 0.873,
          rank: 1,
          reasons: ["5 high-risk OOS SKUs", "Promo compliance below target"],
          components: { oos_risk: 0.91, promo_gap: 0.23, revenue_opportunity: 0.75, visit_recency: 0.4 },
          oos_sku_count: 5,
          data_freshness_ts: "2026-06-15T00:00:00Z",
          audit_event_ids: ["audit-route-1"]
        }
      ]
    });
  });

  const fulfillStoreDetail = async (route: Route) => {
    await route.fulfill({
      json: {
        store_id: "ST-001",
        store_name: "West Market 01",
        retailer_name: "Northstar Retail",
        address: "101 Commerce Ave",
        store_tier: "A",
        territory_code: "WEST-01",
        rep_id: "REP-001",
        last_visit_date: "2026-06-01",
        next_visit_date: "2026-06-20",
        units_sold_30d: 1200,
        revenue_30d: 24000,
        promo_compliance_rate: 0.77,
        revenue_opportunity_score: 0.75,
        oos_sku_count: 5,
        data_freshness_ts: "2026-06-15T00:00:00Z",
        audit_event_id: "audit-store-1"
      }
    });
  };

  await page.route("**/api/v1/stores/ST-001", fulfillStoreDetail);
  await page.route("**/api/v1/stores/ST-001?*", fulfillStoreDetail);

  await page.route("**/api/v1/stores/ST-001/alerts**", async (route) => {
    await route.fulfill({
      json: {
        alerts: [
          {
            alert_id: alertId,
            prediction_row_id: "PRED-00001",
            store_id: "ST-001",
            sku_id: "SKU-4001",
            sku_name: "Core SKU 4001",
            category: "Beverages",
            risk_score: 0.92,
            is_phantom_inventory: true,
            predicted_stockout_date: "2026-06-16",
            root_cause_label: "phantom",
            recommended_action: "Verify backroom inventory; escalate phantom signal",
            confidence_label: "high",
            data_freshness_ts: "2026-06-15T00:00:00Z",
            model_version: "mock-v1",
            source_system: "mock",
            audit_event_id: "audit-alert-1"
          }
        ],
        page: { limit: 50, next_cursor: null }
      }
    });
  });

  await page.route("**/api/v1/stores/ST-001/rgm-recommendations**", async (route) => {
    await route.fulfill({
      json: {
        store_id: "ST-001",
        promos: [
          {
            recommendation_id: "promo-1",
            store_id: "ST-001",
            sku_id: "SKU-4001",
            promo_name: "Cooler endcap",
            expected_lift: 0.12,
            margin_impact: 0.04,
            reason: "High OOS risk with promotion gap",
            confidence_label: "medium"
          }
        ],
        assortment_gaps: [
          {
            gap_id: "gap-1",
            store_id: "ST-001",
            sku_id: "SKU-4002",
            sku_name: "Core SKU 4002",
            category: "Beverages",
            estimated_revenue_opportunity: 4200,
            reason: "Velocity above peer stores",
            confidence_label: "medium"
          }
        ],
        upsell_opportunities: [],
        source_system: "mock",
        model_version: "mock-rgm-v1",
        audit_event_id: "audit-rgm-1"
      }
    });
  });

  await page.route("**/api/v1/agent/osa-summary", async (route) => {
    await route.fulfill({
      json: {
        summary: "Core SKU 4001 has high grounded OOS risk. Verify backroom inventory before replenishment.",
        grounded_alert_ids: [alertId],
        session_id: "REP-001:2026-06-15:workbench",
        model_id: "grounded-template-v1",
        audit_event_id: "audit-summary-1"
      }
    });
  });

  await page.route("**/api/v1/manager/my-tasks**", async (route) => {
    await route.fulfill({ json: { assigned_rep_id: "REP-001", tasks: [] } });
  });

  await page.route("**/api/v1/manager/territory-summary**", async (route) => {
    await route.fulfill({
      json: {
        territory_code: "WEST-01",
        store_count: 1,
        total_oos_alerts: 5,
        confirmed_feedback_count: 1,
        false_positive_count: 0,
        open_draft_count: 0,
        stores: [
          {
            store_id: "ST-001",
            store_name: "West Market 01",
            rep_id: "REP-001",
            priority_score: 0.873,
            oos_sku_count: 5,
            confirmed_feedback_count: 1,
            false_positive_count: 0,
            open_draft_count: 0,
            data_freshness_ts: "2026-06-15T00:00:00Z"
          }
        ]
      }
    });
  });

  let managerTasks: unknown[] = [];
  await page.route("**/api/v1/manager/tasks?**", async (route) => {
    await route.fulfill({ json: { territory_code: "WEST-01", tasks: managerTasks } });
  });

  await page.route("**/api/v1/manager/tasks", async (route) => {
    managerTasks = [
      {
        task_id: managerTaskId,
        territory_code: "WEST-01",
        store_id: "ST-001",
        store_name: "West Market 01",
        assigned_rep_id: "REP-001",
        created_by: "MGR-001",
        session_id: "MGR-001:2026-06-15:manager_work",
        title: "Verify shelf at West Market 01",
        task_type: "shelf_check",
        priority: "medium",
        due_date: null,
        status: "OPEN",
        payload_json: { notes: "Confirm top OOS risks before the next replenishment decision.", linked_alert_ids: [] },
        created_at: "2026-06-15T00:00:00Z",
        audit_event_id: "audit_work_1"
      }
    ];
    await route.fulfill({ json: managerTasks[0] });
  });

  await page.route(`**/api/v1/manager/tasks/${managerTaskId}/status`, async (route) => {
    const task = { ...(managerTasks[0] as Record<string, unknown>), status: "CANCELLED" };
    managerTasks = [task];
    await route.fulfill({ json: task });
  });

  await page.route("**/api/v1/manager/approval-queue**", async (route) => {
    await route.fulfill({ json: { territory_code: "WEST-01", pending_count: 0, items: [] } });
  });

  await page.route("**/api/v1/integrations/readiness", async (route) => {
    await route.fulfill({
      json: {
        ready: true,
        selected_live_modes: [],
        blockers: [],
        provider_blockers: [],
        provider_readiness: {
          auth: { provider: "mock", ready: true },
          data_platform: { ready: true },
          action_providers: { ready: true },
          shelf_image: { provider: "mock", ready: true },
          memory: { provider: "none", ready: true },
          audit: { primary_sink: "postgres", ready: true },
          guardrails: { provider: "pattern", ready: true },
          offline_agent: { provider: "none", enabled: false, ready: false },
          observability: { provider: "structured", ready: true }
        },
        gates: [],
        view_contract_validated: false,
        last_validation_at: null,
        validation_summary: null,
        summary_provider: "template",
        summary_model_id: "grounded-template-v1",
        ai_demo_ready: false,
        ai_demo_provider_ready: false,
        ai_demo_eval_validated: false,
        ai_demo_eval_last_validation_at: null,
        ai_demo_eval_validation_summary: null,
        ai_demo_stage: "template_scaffold",
        ai_demo_blockers: [
          "SUMMARY_PROVIDER must be anthropic for AI-demo readiness",
          "AI-demo eval must pass with provider=anthropic before AI-demo readiness"
        ],
        ai_demo_next_actions: ["Set SUMMARY_PROVIDER=anthropic in the approved AI-demo runtime"],
        ai_demo_validation_command: "python scripts/run_eval.py --require-provider anthropic --output-dir artifacts/eval-ai",
        activation_targets: [
          {
            target: "local",
            ready: true,
            description: "Local scaffold with mock/default providers",
            blockers: []
          },
          {
            target: "ai-demo",
            ready: false,
            description: "Real summary provider validation with the SSE assistant enabled",
            blockers: ["SUMMARY_PROVIDER must be anthropic for AI-demo readiness"]
          },
          {
            target: "pilot",
            ready: false,
            description: "Credentialed pilot with live contracts, live modes, and audit mirror",
            blockers: ["Live data contracts must be validated for pilot readiness"]
          }
        ],
        runtime_validation_commands: {
          local: [
            {
              name: "public_safety_scan",
              command: "bash ./scripts/public_safety_scan.sh",
              notes: "Required before sharing or publishing artifacts."
            },
            {
              name: "local_dev_smoke",
              command: "python scripts/local_dev_smoke.py --output-dir artifacts/local-dev-smoke",
              notes: "Verifies the running Vite workbench and backend health/route data loop."
            },
            {
              name: "local_verification",
              command: "python scripts/verify_local.py --include-frontend-e2e --output-dir artifacts/local-verification",
              notes: "Repo-root pre-push gate covering lint, tests, eval, readiness, MCP smoke, frontend build, Playwright smoke, and public safety."
            },
            {
              name: "pilot_status_snapshot",
              command: "python scripts/pilot_status_snapshot.py --target local --output-dir artifacts/pilot-status/local",
              notes: "Writes a public-safe readiness/API/evidence snapshot for operator handoff."
            },
            {
              name: "pilot_gap_report",
              command: "python scripts/pilot_gap_report.py --target local --output-dir artifacts/pilot-gap-report/local",
              notes: "Writes a public-safe blocker, owner, and next-command report for pilot activation."
            },
            {
              name: "pilot_activation_runbook",
              command: "python scripts/pilot_activation_runbook.py --target local --output-dir artifacts/pilot-activation-runbook/local",
              notes: "Writes the public-safe phase plan from current scaffold to final VSA pilot outcome."
            },
            {
              name: "validation_suite",
              command: "python scripts/validation_suite.py --target local --output-dir artifacts/validation-suite/local --include-local-dev-smoke",
              notes: "Runs the consolidated operator handoff bundle."
            }
          ],
          "ai-demo": [
            {
              name: "ai_summary_eval",
              command: "python scripts/run_eval.py --require-provider anthropic --output-dir artifacts/eval-ai",
              notes: "Must pass with the configured approved provider before claiming AI-assistant behavior."
            },
            {
              name: "mlflow_handoff_dry_run",
              command: "python scripts/log_eval_to_mlflow.py --artifact-dir artifacts/eval-ai --experiment-name phantom-vsa-evals --dry-run --output-dir artifacts/eval-ai",
              notes: "Validates eval artifacts and produces local handoff manifests without a tracking server."
            },
            {
              name: "ai_demo_eval_evidence",
              command: "python scripts/ai_demo_eval_evidence.py --artifact-dir artifacts/eval-ai --output-dir artifacts/eval-ai",
              notes: "Writes the exact AI_DEMO_EVAL_* values to record after the approved eval passes."
            },
            {
              name: "summary_load_test",
              command: "python scripts/load_test.py --base-url http://localhost:8000 --requests 50 --concurrency 10 --threshold-p95-ms 5000 --output-dir artifacts/load/summary",
              notes: "Set LOAD_TEST_BEARER_TOKEN only in the approved runtime environment when validating external identity."
            },
            {
              name: "pilot_gap_report",
              command: "python scripts/pilot_gap_report.py --target ai-demo --output-dir artifacts/pilot-gap-report/ai-demo",
              notes: "Writes a public-safe blocker, owner, and next-command report for pilot activation."
            },
            {
              name: "pilot_activation_runbook",
              command: "python scripts/pilot_activation_runbook.py --target ai-demo --output-dir artifacts/pilot-activation-runbook/ai-demo",
              notes: "Writes the public-safe phase plan from current scaffold to final VSA pilot outcome."
            },
            {
              name: "validation_suite",
              command: "python scripts/validation_suite.py --target ai-demo --output-dir artifacts/validation-suite/ai-demo",
              notes: "Runs the consolidated AI-demo handoff bundle."
            }
          ],
          pilot: [
            {
              name: "pilot_readiness",
              command: "python scripts/pilot_readiness_report.py --target pilot --output-dir artifacts/readiness/pilot",
              notes: "Final gate after approved decisions."
            },
            {
              name: "pilot_gap_report",
              command: "python scripts/pilot_gap_report.py --target pilot --output-dir artifacts/pilot-gap-report/pilot",
              notes: "Writes a public-safe blocker, owner, and next-command report for pilot activation."
            },
            {
              name: "pilot_activation_runbook",
              command: "python scripts/pilot_activation_runbook.py --target pilot --output-dir artifacts/pilot-activation-runbook/pilot",
              notes: "Writes the public-safe phase plan from current scaffold to final VSA pilot outcome."
            },
            {
              name: "validation_suite",
              command: "python scripts/validation_suite.py --target pilot --output-dir artifacts/validation-suite/pilot",
              notes: "Runs the consolidated pilot handoff bundle."
            }
          ]
        },
        activation_evidence_manifests: {
          local: {
            target: "local",
            sections: [
              {
                name: "local_scaffold",
                required_for: ["local", "ai-demo", "pilot"],
                artifacts: [
                  "local-handoff/local_handoff.json",
                  "local-handoff/spec-decision-guard/spec_decision_guard.json",
                  "local-handoff/readiness-bundle/readiness_bundle.json"
                ],
                env_keys: {},
                notes: "Local scaffold proof must stay green for every target."
              }
            ],
            required_env_keys: [],
            required_artifacts: [
              "local-handoff/local_handoff.json",
              "local-handoff/spec-decision-guard/spec_decision_guard.json",
              "local-handoff/readiness-bundle/readiness_bundle.json"
            ]
          },
          "ai-demo": {
            target: "ai-demo",
            sections: [
              {
                name: "local_scaffold",
                required_for: ["local", "ai-demo", "pilot"],
                artifacts: ["local-handoff/local_handoff.json"],
                env_keys: {},
                notes: "Local scaffold proof must stay green for every target."
              },
              {
                name: "ai_demo_eval",
                required_for: ["ai-demo", "pilot"],
                artifacts: [
                  "eval-ai/osa_eval_results.json",
                  "eval-ai/mlflow_handoff.json",
                  "eval-ai/ai_demo_eval_evidence.json",
                  "eval-ai/ai_demo_eval_env.json",
                  "load/summary/load_test_report.json"
                ],
                env_keys: {
                  AI_DEMO_EVAL_VALIDATED: "true only after the approved provider eval passes",
                  AI_DEMO_EVAL_LAST_VALIDATION_AT: "UTC timestamp from the approved provider eval run",
                  AI_DEMO_EVAL_VALIDATION_SUMMARY: "short eval summary copied from ai_demo_eval_env.json"
                },
                notes: "Generated only after the approved Anthropic provider eval and summary load test pass."
              }
            ],
            required_env_keys: [
              "AI_DEMO_EVAL_LAST_VALIDATION_AT",
              "AI_DEMO_EVAL_VALIDATED",
              "AI_DEMO_EVAL_VALIDATION_SUMMARY"
            ],
            required_artifacts: [
              "local-handoff/local_handoff.json",
              "eval-ai/osa_eval_results.json",
              "eval-ai/mlflow_handoff.json",
              "eval-ai/ai_demo_eval_evidence.json",
              "eval-ai/ai_demo_eval_env.json",
              "load/summary/load_test_report.json"
            ]
          },
          pilot: {
            target: "pilot",
            sections: [
              {
                name: "local_scaffold",
                required_for: ["local", "ai-demo", "pilot"],
                artifacts: ["local-handoff/local_handoff.json"],
                env_keys: {},
                notes: "Local scaffold proof must stay green for every target."
              },
              {
                name: "ai_demo_eval",
                required_for: ["ai-demo", "pilot"],
                artifacts: ["eval-ai/osa_eval_results.json"],
                env_keys: { AI_DEMO_EVAL_VALIDATED: "true only after the approved provider eval passes" },
                notes: "Generated only after the approved Anthropic provider eval and summary load test pass."
              },
              {
                name: "live_data_contracts",
                required_for: ["pilot"],
                artifacts: [
                  "contracts/live/live_data_contract_report.json",
                  "contracts/live/readiness_env.json"
                ],
                env_keys: {
                  LIVE_DATA_CONTRACT_VALIDATED: "true only after all selected live data contracts validate",
                  LIVE_DATA_CONTRACT_LAST_VALIDATION_AT: "UTC timestamp from the credentialed validation run",
                  LIVE_DATA_CONTRACT_VALIDATION_SUMMARY: "short validation summary copied from readiness_env.json"
                },
                notes: "Generated only in an approved credentialed environment."
              },
              {
                name: "provider_dry_runs",
                required_for: ["pilot"],
                artifacts: ["unity-audit-smoke/unity_audit_smoke.json"],
                env_keys: {},
                notes: "Dry-run proof for live write, audit, guardrail, and memory contracts before credentialed smoke."
              },
              {
                name: "pilot_env_handoff",
                required_for: ["pilot"],
                artifacts: ["pilot-env/pilot_validation.env.snippet"],
                env_keys: {
                  AI_DEMO_EVAL_VALIDATED: "public-safe pilot validation evidence",
                  LIVE_DATA_CONTRACT_VALIDATED: "public-safe pilot validation evidence"
                },
                notes: "Merges non-secret AI-demo and live-data validation values for approved runtime configuration."
              }
            ],
            required_env_keys: [
              "AI_DEMO_EVAL_VALIDATED",
              "LIVE_DATA_CONTRACT_VALIDATED",
              "LIVE_DATA_CONTRACT_LAST_VALIDATION_AT",
              "LIVE_DATA_CONTRACT_VALIDATION_SUMMARY"
            ],
            required_artifacts: [
              "local-handoff/local_handoff.json",
              "eval-ai/osa_eval_results.json",
              "contracts/live/readiness_env.json",
              "pilot-env/pilot_validation.env.snippet"
            ]
          }
        }
      }
    });
  });

  await page.route("**/api/v1/integrations/pilot-gap-report**", async (route) => {
    await route.fulfill({
      json: {
        generated_at: "2026-06-15T00:00:00Z",
        target: "pilot",
        ready_for_requested_target: false,
        requested_target_blocker_count: 3,
        gap_count: 3,
        activation_targets: [
          { target: "local", ready: true, blocker_count: 0, blockers: [] },
          { target: "ai-demo", ready: false, blocker_count: 1, blockers: ["SUMMARY_PROVIDER must be anthropic for AI-demo readiness"] },
          { target: "pilot", ready: false, blocker_count: 2, blockers: ["Live data contracts must be validated for pilot readiness", "Unity Catalog audit sink or mirror must be selected for pilot readiness"] }
        ],
        blocking_gaps: [
          {
            target: "ai-demo",
            blocker: "SUMMARY_PROVIDER must be anthropic for AI-demo readiness",
            owner: "engineering",
            recommended_command_names: ["ai_summary_eval"]
          },
          {
            target: "pilot",
            blocker: "Live data contracts must be validated for pilot readiness",
            owner: "delivery+engineering",
            recommended_command_names: ["live_data_contracts"]
          },
          {
            target: "pilot",
            blocker: "Unity Catalog audit sink or mirror must be selected for pilot readiness",
            owner: "delivery+engineering",
            recommended_command_names: ["unity_audit_smoke"]
          }
        ],
        recommended_commands: [
          {
            name: "ai_summary_eval",
            command: "python scripts/run_eval.py --require-provider anthropic --output-dir artifacts/eval-ai",
            notes: "Must pass with the configured approved provider."
          },
          {
            name: "live_data_contracts",
            command: "python scripts/validate_live_data_contracts.py --output-dir artifacts/contracts/live",
            notes: "Run only in an approved credentialed environment."
          },
          {
            name: "unity_audit_smoke",
            command: "python scripts/unity_audit_smoke.py --output-dir artifacts/unity-audit-smoke",
            notes: "Dry-run parameterized audit insert."
          }
        ],
        roadmap_items: [
          {
            area: "live_data",
            owner: "delivery+engineering",
            status: "blocked_by_credentials",
            next_gate: "live_data_contracts"
          }
        ],
        public_safety_notes: ["No secrets, token values, local user paths, or client-confidential identifiers are included."]
      }
    });
  });

  await page.route("**/api/v1/integrations/ai-demo-activation-pack", async (route) => {
    await route.fulfill({
      json: {
        generated_at: "2026-06-15T00:00:00Z",
        target: "ai-demo",
        ready: false,
        stage: "template_scaffold",
        summary_provider: "template",
        summary_model_id: "grounded-template-v1",
        provider_ready: false,
        eval_validated: false,
        last_validation_at: null,
        validation_summary: null,
        blockers: [
          "SUMMARY_PROVIDER must be anthropic for AI-demo readiness",
          "AI-demo eval must pass with provider=anthropic before AI-demo readiness"
        ],
        next_actions: ["Set SUMMARY_PROVIDER=anthropic in the approved AI-demo runtime"],
        config_checks: [
          {
            name: "summary_provider",
            ready: false,
            public_value: "template",
            required_value: "anthropic",
            value_present: null,
            notes: "Template mode proves scaffold safety only."
          },
          {
            name: "anthropic_token_ref",
            ready: false,
            public_value: null,
            required_value: null,
            value_present: false,
            notes: "Presence only; value is never exposed."
          },
          {
            name: "agent_run_enabled",
            ready: true,
            public_value: "true",
            required_value: "true",
            value_present: null,
            notes: "AI-demo validates the SSE assistant path."
          }
        ],
        required_commands: [
          {
            name: "ai_summary_eval",
            command: "python scripts/run_eval.py --require-provider anthropic --output-dir artifacts/eval-ai",
            notes: "Must pass with provider=anthropic."
          },
          {
            name: "ai_demo_eval_evidence",
            command: "python scripts/ai_demo_eval_evidence.py --artifact-dir artifacts/eval-ai --output-dir artifacts/eval-ai",
            notes: "Writes AI_DEMO_EVAL_* evidence."
          }
        ],
        required_artifacts: ["eval-ai/osa_eval_results.json", "eval-ai/ai_demo_eval_env.json"],
        required_env_keys: ["AI_DEMO_EVAL_VALIDATED", "AI_DEMO_EVAL_LAST_VALIDATION_AT"],
        public_safety_notes: ["Token references are reported only as value_present booleans."]
      }
    });
  });

  await page.route("**/api/v1/integrations/activation-runbook**", async (route) => {
    await route.fulfill({
      json: {
        generated_at: "2026-06-15T00:00:00Z",
        current_target: "pilot",
        final_outcome: "A governed VSA pilot where reps prioritize stores, inspect grounded recommendations, run the SSE assistant, submit feedback, and create HITL-gated drafts.",
        phase_count: 8,
        ready_phase_count: 1,
        blocked_phase_count: 4,
        phases: [
          {
            phase_id: "phase-0-local-scaffold",
            title: "Local Scaffold Readiness",
            target: "local",
            owner: "engineering",
            estimated_effort: "same day after each implementation chunk",
            goal: "Prove the mock-backed workbench still works.",
            status: "ready",
            required_command_names: ["local_readiness", "api_contract", "final_api_smoke"],
            required_configuration_keys: [],
            exit_gate_summary: ["Local readiness report passes."],
            blockers: []
          },
          {
            phase_id: "phase-1-ai-demo",
            title: "Real AI Demo Readiness",
            target: "ai-demo",
            owner: "delivery+engineering",
            estimated_effort: "1-2 engineering days",
            goal: "Prove the assistant is more than a deterministic template.",
            status: "blocked",
            required_command_names: ["ai_summary_eval", "mlflow_handoff_dry_run", "summary_load_test"],
            required_configuration_keys: ["SUMMARY_PROVIDER", "ANTHROPIC_TOKEN_REF", "AI_DEMO_EVAL_VALIDATED"],
            exit_gate_summary: ["Approved-provider eval passes."],
            blockers: ["SUMMARY_PROVIDER must be anthropic for AI-demo readiness"]
          },
          {
            phase_id: "phase-2-live-data-contracts",
            title: "Live Data Contract Readiness",
            target: "pilot",
            owner: "delivery+engineering",
            estimated_effort: "2-5 engineering days",
            goal: "Prove selected Databricks and Snowflake views match the ontology.",
            status: "blocked",
            required_command_names: ["live_data_contracts"],
            required_configuration_keys: ["LIVE_DATA_CONTRACT_VALIDATED"],
            exit_gate_summary: ["Live data contract validation passes."],
            blockers: ["Live data contracts must be validated for pilot readiness"]
          },
          {
            phase_id: "phase-3-identity-governance",
            title: "Identity And Governance Readiness",
            target: "pilot",
            owner: "delivery+engineering",
            estimated_effort: "2-4 engineering days",
            goal: "Move from mock identity and local audit to governed identity and mirror audit.",
            status: "blocked",
            required_command_names: ["unity_audit_smoke", "guardrail_classifier_smoke"],
            required_configuration_keys: ["AUTH_PROVIDER", "AUDIT_UNITY_CATALOG_TABLE"],
            exit_gate_summary: ["Unauthorized store access still returns 404."],
            blockers: ["Unity Catalog audit sink or mirror must be selected for pilot readiness"]
          },
          {
            phase_id: "phase-4-crm-erp-hitl",
            title: "CRM, ERP, And HITL Write-Back",
            target: "pilot",
            owner: "delivery+engineering",
            estimated_effort: "3-7 engineering days",
            goal: "Preserve HITL while enabling write-back integrations.",
            status: "scaffolded",
            required_command_names: ["action_provider_smoke"],
            required_configuration_keys: ["CRM_ADAPTER", "ERP_ADAPTER"],
            exit_gate_summary: ["Agents can draft but cannot submit."],
            blockers: []
          },
          {
            phase_id: "phase-6-final-pilot",
            title: "Final VSA Pilot Gate",
            target: "pilot",
            owner: "delivery+engineering",
            estimated_effort: "1-2 days",
            goal: "Joint signoff before pilot traffic.",
            status: "blocked",
            required_command_names: ["pilot_readiness", "pilot_env_handoff"],
            required_configuration_keys: [],
            exit_gate_summary: ["Every AI summary and write intent is grounded and audited."],
            blockers: ["Live data contracts must be validated for pilot readiness"]
          }
        ],
        public_safety_notes: ["No secrets, token values, local user paths, or client-confidential identifiers are included."]
      }
    });
  });

  await page.route("**/api/v1/integrations/discovery-packet**", async (route) => {
    await route.fulfill({
      json: {
        generated_at: "2026-06-15T00:00:00Z",
        target: "pilot",
        selected_live_modes: [],
        gate_count: 6,
        missing_count: 4,
        defaulted_count: 2,
        owner_groups: [
          {
            owner: "delivery",
            gate_count: 4,
            missing_count: 3,
            defaulted_count: 1,
            gates: [
              {
                topic: "Data sharing model",
                setting_name: "discovery_data_sharing_model",
                status: "missing",
                value_present: false,
                required_for: ["databricks", "snowflake", "unity_catalog"],
                notes: "Required before live data or audit integrations.",
                owner: "delivery"
              },
              {
                topic: "SSO provider",
                setting_name: "discovery_sso_provider",
                status: "missing",
                value_present: false,
                required_for: ["external_jwt"],
                notes: "Required before external JWT validation.",
                owner: "delivery"
              },
              {
                topic: "ERP sandbox endpoint",
                setting_name: "discovery_erp_sandbox",
                status: "missing",
                value_present: false,
                required_for: ["erp_submit"],
                notes: "Required before real order submission.",
                owner: "delivery"
              },
              {
                topic: "Rep device",
                setting_name: "discovery_rep_device",
                status: "defaulted",
                value_present: true,
                required_for: ["offline", "offline_agent"],
                notes: "Required before native/offline runtime decisions.",
                owner: "delivery"
              }
            ]
          },
          {
            owner: "shared",
            gate_count: 2,
            missing_count: 1,
            defaulted_count: 1,
            gates: [
              {
                topic: "Guardrail classifier endpoint",
                setting_name: "guardrail_classifier_endpoint",
                status: "missing",
                value_present: false,
                required_for: ["guardrail_classifier"],
                notes: "Required before external classifier guardrails.",
                owner: "shared"
              },
              {
                topic: "Offline sync policy",
                setting_name: "discovery_offline_sync_policy",
                status: "defaulted",
                value_present: true,
                required_for: ["offline", "offline_agent"],
                notes: "Required before broader offline write queues.",
                owner: "shared"
              }
            ]
          }
        ],
        next_actions: ["delivery: answer discovery_data_sharing_model, discovery_sso_provider, discovery_erp_sandbox"],
        public_safety_notes: ["Actual values, endpoint URLs, tokens, local paths, and client-confidential identifiers are not included."]
      }
    });
  });

  await page.route("**/api/v1/admin/audit-events?**", async (route) => {
    await route.fulfill({
      json: {
        events: [adminAuditEvent],
        limit: 75,
        next_cursor: null
      }
    });
  });

  await page.route("**/api/v1/admin/audit-events/audit-admin-1", async (route) => {
    await route.fulfill({
      json: { event: adminAuditEvent }
    });
  });

  await page.route("**/api/v1/agent/run", async (route) => {
    const body = route.request().postDataJSON() as { intent?: string };
    if (body.intent === "order_draft") {
      await route.fulfill({
        contentType: "text/event-stream",
        body: [
          `event: run_started\ndata: {"run_id":"run-order","session_id":"REP-001:2026-06-15:workbench","intent":"order_draft"}`,
          `event: supervisor_decision\ndata: {"run_id":"run-order","intent":"order_draft","agent":"action_agent","requires_human_approval":true}`,
          `event: action_result\ndata: {"run_id":"run-order","type":"order_draft","draft":{"draft_id":"draft-agent-1","store_id":"ST-001","rep_id":"REP-001","session_id":"REP-001:2026-06-15:workbench","payload_json":{"items":[{"sku_id":"SKU-4001","sku_name":"Core SKU 4001","quantity":12,"reason":"Confirm on-shelf availability"}],"notes":"Agent drafted from alert ${alertId}; human approval required."},"payload_hash":"hash-agent-order-1","status":"DRAFT","created_at":"2026-06-15T00:00:00Z","audit_event_id":"audit-order-agent-1"}}`,
          `event: hitl_required\ndata: {"run_id":"run-order","required":true,"reason":"order_submit_requires_human_approval","resume_token":"REP-001:2026-06-15:workbench:hitl:order:draft-agent-1"}`,
          `event: audit\ndata: {"run_id":"run-order","audit_event_id":"audit-order-agent-1","model_id":null}`,
          `event: run_completed\ndata: {"run_id":"run-order","session_id":"REP-001:2026-06-15:workbench"}`
        ].join("\n\n") + "\n\n"
      });
      return;
    }
    if (body.intent === "visit_log_draft") {
      await route.fulfill({
        contentType: "text/event-stream",
        body: [
          `event: run_started\ndata: {"run_id":"run-visit","session_id":"REP-001:2026-06-15:workbench","intent":"visit_log_draft"}`,
          `event: supervisor_decision\ndata: {"run_id":"run-visit","intent":"visit_log_draft","agent":"action_agent","requires_human_approval":false}`,
          `event: action_result\ndata: {"run_id":"run-visit","type":"visit_log_draft","visit_log":{"id":"visit-agent-1","store_id":"ST-001","rep_id":"REP-001","session_id":"REP-001:2026-06-15:workbench","payload_json":{"notes":"Agent drafted visit log from grounded OOS alerts for rep review.","outcome":"needs_follow_up"},"status":"DRAFT","created_at":"2026-06-15T00:00:00Z","audit_event_id":"audit-visit-agent-1"}}`,
          `event: audit\ndata: {"run_id":"run-visit","audit_event_id":"audit-visit-agent-1","model_id":null}`,
          `event: run_completed\ndata: {"run_id":"run-visit","session_id":"REP-001:2026-06-15:workbench"}`
        ].join("\n\n") + "\n\n"
      });
      return;
    }
    await route.fulfill({
      contentType: "text/event-stream",
      body: [
        `event: run_started\ndata: {"run_id":"run-1","session_id":"REP-001:2026-06-15:workbench","intent":"osa_summary"}`,
        `event: supervisor_decision\ndata: {"run_id":"run-1","intent":"osa_summary","agent":"osa_agent","requires_human_approval":false}`,
        `event: message\ndata: {"run_id":"run-1","role":"assistant","content":"Core SKU 4001 has high grounded OOS risk from the agent stream.","grounded_alert_ids":["${alertId}"]}`,
        `event: audit\ndata: {"run_id":"run-1","audit_event_id":"audit-agent-1","model_id":"grounded-template-v1"}`,
        `event: run_completed\ndata: {"run_id":"run-1","session_id":"REP-001:2026-06-15:workbench"}`
      ].join("\n\n") + "\n\n"
    });
  });

  await page.route(`**/api/v1/alerts/${encodeURIComponent(alertId)}/feedback`, async (route) => {
    await route.fulfill({
      json: {
        id: "feedback-1",
        alert_id: alertId,
        store_id: "ST-001",
        sku_id: "SKU-4001",
        rep_id: "REP-001",
        feedback: "confirmed",
        notes: null,
        session_id: "REP-001:2026-06-15:workbench",
        created_at: "2026-06-15T00:00:00Z",
        audit_event_id: "audit-feedback-1"
      }
    });
  });
});

test("rep can review route, generate summary, and submit alert feedback", async ({ page }) => {
  const requestFailures: string[] = [];
  page.on("requestfailed", (request) => {
    requestFailures.push(`${request.url()} :: ${request.failure()?.errorText ?? "unknown"}`);
  });
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Today's field workbench" })).toBeVisible();
  await expect(page.getByTestId("visit-ST-001")).toContainText("West Market 01");
  await expect(page.getByRole("heading", { name: "West Market 01" })).toBeVisible().catch((error: Error) => {
    throw new Error(`${error.message}\nRequest failures:\n${requestFailures.join("\n") || "none"}`);
  });
  await expect(page.getByTestId("alert-count")).toContainText("1 grounded shelf risks");

  await page.getByTestId("generate-summary").click();
  await expect(page.getByTestId("summary-box")).toContainText("Core SKU 4001 has high grounded OOS risk");

  await page.getByTestId("run-agent").click();
  await expect(page.getByTestId("agent-panel")).toContainText("message");
  await expect(page.getByTestId("agent-panel")).toContainText("audit");
  await expect(page.getByTestId("summary-box")).toContainText("agent stream");

  await page.getByTestId("agent-draft-order").click();
  await expect(page.getByTestId("agent-panel")).toContainText("hitl required");
  await expect(page.getByTestId("agent-panel")).toContainText("order submit requires human approval");
  await expect(page.getByText("Draft DRAFT")).toBeVisible();

  await page.getByTestId("agent-visit-log").click();
  await expect(page.getByTestId("agent-panel")).toContainText("visit log draft created");
  await expect(page.getByText(/Visit log draft draft/)).toBeVisible();

  await page.getByTestId(`feedback-${alertId}-confirmed`).click();
  await expect(page.getByTestId(`feedback-${alertId}-confirmed`)).toHaveClass(/feedbackButton--active/);
});

test("rep assigned work hides completed and cancelled task history", async ({ page }) => {
  await page.unroute("**/api/v1/manager/my-tasks**");
  await page.route("**/api/v1/manager/my-tasks**", async (route) => {
    expect(new URL(route.request().url()).searchParams.get("status")).toBe("OPEN");
    await route.fulfill({
      json: {
        assigned_rep_id: "REP-001",
        tasks: [
          {
            task_id: "work_open",
            territory_code: "WEST-01",
            store_id: "ST-001",
            store_name: "West Market 01",
            assigned_rep_id: "REP-001",
            created_by: "MGR-001",
            session_id: "MGR-001:2026-06-15:manager_work",
            title: "Verify shelf before noon",
            task_type: "shelf_check",
            priority: "high",
            due_date: null,
            status: "OPEN",
            payload_json: { notes: "Confirm top OOS risks.", linked_alert_ids: [] },
            created_at: "2026-06-15T00:00:00Z",
            audit_event_id: "audit_work_open"
          },
          {
            task_id: "work_done",
            territory_code: "WEST-01",
            store_id: "ST-001",
            store_name: "West Market 01",
            assigned_rep_id: "REP-001",
            created_by: "MGR-001",
            session_id: "MGR-001:2026-06-15:manager_work",
            title: "Readiness shelf check",
            task_type: "shelf_check",
            priority: "medium",
            due_date: null,
            status: "COMPLETED",
            payload_json: { notes: "Already handled.", linked_alert_ids: [] },
            created_at: "2026-06-15T00:00:00Z",
            audit_event_id: "audit_work_done"
          },
          {
            task_id: "work_open_duplicate",
            territory_code: "WEST-01",
            store_id: "ST-001",
            store_name: "West Market 01",
            assigned_rep_id: "REP-001",
            created_by: "MGR-001",
            session_id: "MGR-001:2026-06-15:manager_work",
            title: "Verify shelf before noon",
            task_type: "shelf_check",
            priority: "high",
            due_date: null,
            status: "OPEN",
            payload_json: { notes: "Duplicate open task.", linked_alert_ids: [] },
            created_at: "2026-06-15T00:00:00Z",
            audit_event_id: "audit_work_open_duplicate"
          },
          {
            task_id: "work_cancelled",
            territory_code: "WEST-01",
            store_id: "ST-001",
            store_name: "West Market 01",
            assigned_rep_id: "REP-001",
            created_by: "MGR-001",
            session_id: "MGR-001:2026-06-15:manager_work",
            title: "Cancel this duplicate task",
            task_type: "shelf_check",
            priority: "medium",
            due_date: null,
            status: "CANCELLED",
            payload_json: { notes: "Cancelled by manager.", linked_alert_ids: [] },
            created_at: "2026-06-15T00:00:00Z",
            audit_event_id: "audit_work_cancelled"
          }
        ]
      }
    });
  });

  await page.goto("/");

  await expect(page.getByTestId("my-tasks")).toContainText("1 open tasks");
  await expect(page.getByTestId("my-tasks").getByText("Verify shelf before noon")).toHaveCount(1);
  await expect(page.getByTestId("my-tasks")).not.toContainText("Readiness shelf check");
  await expect(page.getByTestId("my-tasks")).not.toContainText("Cancel this duplicate task");
});

test("app exposes PWA manifest and registers service worker", async ({ browser }) => {
  const context = await browser.newContext({ baseURL: "http://127.0.0.1:4173", serviceWorkers: "allow" });
  const page = await context.newPage();
  await page.goto("/");

  const manifestHref = await page.locator('link[rel="manifest"]').getAttribute("href");
  expect(manifestHref).toBe("/manifest.webmanifest");
  const manifestResponse = await page.request.get("/manifest.webmanifest");
  expect(manifestResponse.ok()).toBeTruthy();
  const manifest = await manifestResponse.json();
  expect(manifest.display).toBe("standalone");
  expect(manifest.icons[0].src).toBe("/pwa-icon.svg");
  const policyResponse = await page.request.get("/offline-cache-policy.json");
  expect(policyResponse.ok()).toBeTruthy();
  const policy = await policyResponse.json();
  const apiPolicy = policy.policies.find((row: { scope: string }) => row.scope === "api");
  expect(apiPolicy.strategy).toBe("network-only");
  expect(apiPolicy.writes_cached).toBe(false);

  const registrationState = await page.evaluate(async () => {
    if (!("serviceWorker" in navigator)) return "unsupported";
    const registration = await navigator.serviceWorker.ready;
    return registration.active?.scriptURL.endsWith("/sw.js") ? "registered" : "missing";
  });
  expect(registrationState).toBe("registered");
  const runtimePolicy = await page.evaluate(async () => {
    const registration = await navigator.serviceWorker.ready;
    return await new Promise<Record<string, unknown>>((resolve, reject) => {
      const timeout = window.setTimeout(() => reject(new Error("Timed out waiting for cache policy")), 2000);
      navigator.serviceWorker.addEventListener("message", function onMessage(event) {
        if (event.data?.type !== "PHANTOM_CACHE_POLICY") return;
        window.clearTimeout(timeout);
        navigator.serviceWorker.removeEventListener("message", onMessage);
        resolve(event.data.policy);
      });
      registration.active?.postMessage({ type: "PHANTOM_CACHE_POLICY" });
    });
  });
  expect(runtimePolicy.api).toBe("network-only");
  expect(runtimePolicy.writes_cached).toBe(false);
  await context.close();
});

test("manager can assign a shelf-check task from the command view", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "manager" }).click();
  await expect(page.getByRole("heading", { name: "Territory command view" })).toBeVisible();
  await expect(page.getByTestId("readiness-panel")).toContainText("Local scaffold ready");
  await expect(page.getByTestId("readiness-panel")).toContainText("mock/local modes");
  await expect(page.getByTestId("readiness-panel")).toContainText("ai-demo");
  await expect(page.getByTestId("readiness-panel")).toContainText("pilot");
  await expect(page.getByTestId("readiness-panel")).toContainText("SUMMARY_PROVIDER must be anthropic");
  await expect(page.getByTestId("readiness-panel")).toContainText("AI eval pending");
  await expect(page.getByTestId("readiness-panel")).toContainText("stage template_scaffold");
  await expect(page.getByTestId("readiness-panel")).toContainText("Set SUMMARY_PROVIDER=anthropic");
  await expect(page.getByTestId("readiness-panel")).toContainText("ai_summary_eval");
  await expect(page.getByTestId("readiness-panel")).toContainText("ai_demo_eval_evidence");
  await expect(page.getByTestId("readiness-panel")).toContainText("summary_load_test");
  await expect(page.getByTestId("ai-demo-activation-pack")).toContainText("AI demo activation");
  await expect(page.getByTestId("ai-demo-activation-pack")).toContainText("summary_provider");
  await expect(page.getByTestId("ai-demo-activation-pack")).toContainText("anthropic_token_ref");
  await expect(page.getByTestId("runtime-commands")).toContainText("local_dev_smoke");
  await expect(page.getByTestId("runtime-commands")).toContainText("local_verification");
  await expect(page.getByTestId("runtime-commands")).toContainText("pilot_status_snapshot");
  await expect(page.getByTestId("runtime-commands")).toContainText("pilot_gap_report");
  await expect(page.getByTestId("runtime-commands")).toContainText("validation_suite");
  await expect(page.getByTestId("runtime-commands")).toContainText("7 commands");
  await expect(page.getByTestId("pilot-gap-summary")).toContainText("pilot gap report");
  await expect(page.getByTestId("pilot-gap-summary")).toContainText("3 gaps");
  await expect(page.getByTestId("pilot-gap-summary")).toContainText("delivery+engineering");
  await expect(page.getByTestId("pilot-gap-summary")).toContainText("live_data_contracts");
  await expect(page.getByTestId("activation-runbook")).toContainText("Final VSA runbook");
  await expect(page.getByTestId("activation-runbook")).toContainText("1/8 ready");
  await expect(page.getByTestId("activation-runbook")).toContainText("Real AI Demo Readiness");
  await expect(page.getByTestId("activation-runbook")).toContainText("ai_summary_eval");
  await expect(page.getByTestId("activation-runbook")).toContainText("Final VSA Pilot Gate");
  await expect(page.getByTestId("discovery-packet")).toContainText("pilot discovery packet");
  await expect(page.getByTestId("discovery-packet")).toContainText("4 missing");
  await expect(page.getByTestId("discovery-packet")).toContainText("delivery");
  await expect(page.getByTestId("discovery-packet")).toContainText("discovery_sso_provider");
  await expect(page.getByTestId("activation-evidence")).toContainText("local evidence");
  await expect(page.getByTestId("activation-evidence")).toContainText("ai_demo_eval");
  await expect(page.getByTestId("activation-evidence")).toContainText("pilot_env_handoff");
  await expect(page.getByTestId("activation-evidence")).toContainText("local-handoff/local_handoff.json");
  await expect(page.getByLabel("ai-demo required env keys")).toContainText("AI_DEMO_EVAL_VALIDATED");
  await expect(page.getByLabel("local next validation command")).toContainText("bash ./scripts/public_safety_scan.sh");
  await expect(page.getByLabel("ai-demo next validation command")).toContainText("python scripts/run_eval.py");
  await expect(page.getByText("0 assigned tasks")).toBeVisible();

  await page.getByRole("button", { name: "Assign shelf check" }).click();
  await expect(page.getByText("Assigned Verify shelf at West Market 01")).toBeVisible();
  await expect(page.locator(".taskRow").filter({ hasText: "Verify shelf at West Market 01" })).toBeVisible();

  await page.getByTestId(`cancel-work-${managerTaskId}`).click();
  await expect(page.getByText("marked cancelled")).toBeVisible();
});

test("admin can review readiness and audit detail", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "admin" }).click();
  await expect(page.getByRole("heading", { name: "Governance audit view" })).toBeVisible();
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("Provider gates clear");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("mock contracts");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("AI provider blocked");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("AI eval pending");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("AI demo activation");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("ai_summary_eval");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("stage template_scaffold");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("local");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("pilot");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("Live data contracts must be validated");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("pilot_readiness");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("pilot gap report");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("unity_audit_smoke");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("Final VSA runbook");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("Live Data Contract Readiness");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("pilot_env_handoff");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("pilot discovery packet");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("guardrail_classifier_endpoint");
  await expect(page.getByTestId("activation-evidence")).toContainText("live_data_contracts");
  await expect(page.getByTestId("activation-evidence")).toContainText("4 artifacts");
  await expect(page.getByLabel("pilot required artifacts")).toContainText("pilot-env/pilot_validation.env.snippet");
  await expect(page.getByLabel("pilot required env keys")).toContainText("LIVE_DATA_CONTRACT_VALIDATED");
  await expect(page.getByLabel("pilot next validation command")).toContainText("python scripts/pilot_readiness_report.py");
  await expect(page.getByText("1 recent events")).toBeVisible();

  await page.getByRole("button", { name: /osa_summary_created/ }).click();
  await expect(page.locator(".auditDetail")).toContainText("audit-admin-1");
});
