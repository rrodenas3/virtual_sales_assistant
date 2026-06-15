import { expect, test } from "@playwright/test";

const alertId = "ST-001:SKU-4001:2026-06-15";

test.beforeEach(async ({ page }) => {
  await page.route("http://localhost:8000/api/v1/metrics/pilot", async (route) => {
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

  await page.route("http://localhost:8000/api/v1/visits/today**", async (route) => {
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

  await page.route("http://localhost:8000/api/v1/stores/ST-001", async (route) => {
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
  });

  await page.route("http://localhost:8000/api/v1/stores/ST-001/alerts**", async (route) => {
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

  await page.route("http://localhost:8000/api/v1/stores/ST-001/rgm-recommendations", async (route) => {
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

  await page.route("http://localhost:8000/api/v1/agent/osa-summary", async (route) => {
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

  await page.route("http://localhost:8000/api/v1/agent/run", async (route) => {
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

  await page.route(`http://localhost:8000/api/v1/alerts/${encodeURIComponent(alertId)}/feedback`, async (route) => {
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
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Today's field workbench" })).toBeVisible();
  await expect(page.getByTestId("visit-ST-001")).toContainText("West Market 01");
  await expect(page.getByRole("heading", { name: "West Market 01" })).toBeVisible();
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

test("app exposes PWA manifest and registers service worker", async ({ page }) => {
  await page.goto("/");

  const manifestHref = await page.locator('link[rel="manifest"]').getAttribute("href");
  expect(manifestHref).toBe("/manifest.webmanifest");
  const manifestResponse = await page.request.get("/manifest.webmanifest");
  expect(manifestResponse.ok()).toBeTruthy();
  const manifest = await manifestResponse.json();
  expect(manifest.display).toBe("standalone");
  expect(manifest.icons[0].src).toBe("/pwa-icon.svg");

  const registrationState = await page.evaluate(async () => {
    if (!("serviceWorker" in navigator)) return "unsupported";
    const registration = await navigator.serviceWorker.ready;
    return registration.active?.scriptURL.endsWith("/sw.js") ? "registered" : "missing";
  });
  expect(registrationState).toBe("registered");
});
