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
            }
          ],
          pilot: [
            {
              name: "pilot_readiness",
              command: "python scripts/pilot_readiness_report.py --target pilot --output-dir artifacts/readiness/pilot",
              notes: "Final gate after approved decisions."
            }
          ]
        }
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
    await route.fulfill({
      contentType: "text/event-stream",
      body: [
        `event: run_started\ndata: {"run_id":"run-1","session_id":"REP-001:2026-06-15:workbench","intent":"osa_summary"}`,
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
  await expect(page.getByTestId("runtime-commands")).toContainText("local_dev_smoke");
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
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("stage template_scaffold");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("local");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("pilot");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("Live data contracts must be validated");
  await expect(page.getByTestId("admin-readiness-panel")).toContainText("pilot_readiness");
  await expect(page.getByLabel("pilot next validation command")).toContainText("python scripts/pilot_readiness_report.py");
  await expect(page.getByText("1 recent events")).toBeVisible();

  await page.getByRole("button", { name: /osa_summary_created/ }).click();
  await expect(page.locator(".auditDetail")).toContainText("audit-admin-1");
});
