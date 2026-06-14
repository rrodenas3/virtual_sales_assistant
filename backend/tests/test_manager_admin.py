import base64
import json

from fastapi.testclient import TestClient

from backend.main import app


def token(claims: dict) -> str:
    def enc(data: dict) -> str:
        raw = json.dumps(data, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{enc({'alg': 'none', 'typ': 'JWT'})}.{enc(claims)}."


REP_001 = token({"sub": "REP-001", "territory_code": "WEST-01", "role": "rep"})
MANAGER = token({"sub": "MGR-001", "territory_code": "WEST-01", "role": "manager"})
ADMIN = token({"sub": "ADMIN-001", "role": "admin"})


def authorized_client(jwt: str) -> TestClient:
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {jwt}"})
    return c


def test_manager_can_read_territory_summary_and_store_alerts() -> None:
    with authorized_client(MANAGER) as c:
        summary = c.get("/api/v1/manager/territory-summary?territory_code=WEST-01")
        assert summary.status_code == 200
        body = summary.json()
        assert body["store_count"] == 25
        assert body["total_oos_alerts"] >= 100

        alerts = c.get("/api/v1/stores/ST-001/alerts")
        assert alerts.status_code == 200
        assert alerts.json()["alerts"]


def test_rep_cannot_read_manager_summary() -> None:
    with authorized_client(REP_001) as c:
        summary = c.get("/api/v1/manager/territory-summary?territory_code=WEST-01")
        assert summary.status_code == 403


def test_admin_audit_requires_admin_role() -> None:
    with authorized_client(REP_001) as c:
        forbidden = c.get("/api/v1/admin/audit-events")
        assert forbidden.status_code == 403

    with authorized_client(ADMIN) as c:
        allowed = c.get("/api/v1/admin/audit-events")
        assert allowed.status_code == 200
        assert "events" in allowed.json()
