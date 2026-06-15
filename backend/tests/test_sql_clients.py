from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from backend.clients.sql import QueryStatement, SnowflakeSQLClient, param
from backend.config import settings


def _configure_snowflake(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "snowflake_account", "acct")
    monkeypatch.setattr(settings, "snowflake_user", "svc_user")
    monkeypatch.setattr(settings, "snowflake_token", "approved-token-reference")
    monkeypatch.setattr(settings, "snowflake_warehouse", "warehouse")
    monkeypatch.setattr(settings, "snowflake_database", "database")
    monkeypatch.setattr(settings, "snowflake_schema", "schema")


@pytest.mark.asyncio
async def test_snowflake_sql_client_posts_parameterized_statement(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_snowflake(monkeypatch)
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "resultSetMetaData": {"rowType": [{"name": "store_id"}, {"name": "revenue_30d"}]},
                "data": [["ST-001", "24000"]],
            },
        )

    client = SnowflakeSQLClient(settings, transport=httpx.MockTransport(handler))

    rows = await client.execute(
        QueryStatement(
            statement="select * from store_master where store_id = :store_id and revenue_30d > :minimum_revenue",
            parameters=(param("store_id", "ST-001"), param("minimum_revenue", 1000, "INT")),
        )
    )

    assert captured["url"] == "https://acct.snowflakecomputing.com/api/v2/statements"
    assert captured["headers"]["authorization"] == "Bearer approved-token-reference"
    assert captured["headers"]["x-snowflake-authorization-token-type"] == "OAUTH"
    assert captured["payload"]["database"] == "database"
    assert captured["payload"]["schema"] == "schema"
    assert captured["payload"]["warehouse"] == "warehouse"
    assert captured["payload"]["bindings"] == {
        "store_id": {"type": "TEXT", "value": "ST-001"},
        "minimum_revenue": {"type": "FIXED", "value": "1000"},
    }
    assert rows == [{"store_id": "ST-001", "revenue_30d": "24000"}]


@pytest.mark.asyncio
async def test_snowflake_sql_client_fails_fast_on_missing_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_snowflake(monkeypatch)
    monkeypatch.setattr(settings, "snowflake_token", None)
    client = SnowflakeSQLClient(settings)

    with pytest.raises(RuntimeError, match="snowflake_token"):
        await client.execute(QueryStatement(statement="select 1", parameters=()))
