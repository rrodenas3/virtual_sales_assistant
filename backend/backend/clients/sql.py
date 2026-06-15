from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal, Protocol

import httpx

from backend.config import Settings

QueryParamType = Literal["STRING", "DOUBLE", "INT", "DATE"]


@dataclass(frozen=True)
class QueryParam:
    name: str
    value: str | int | float
    type: QueryParamType = "STRING"

    def as_databricks(self) -> dict[str, Any]:
        return {"name": self.name, "value": str(self.value), "type": self.type}

    def as_snowflake(self) -> dict[str, Any]:
        return {"name": self.name, "value": str(self.value), "type": self.type}


@dataclass(frozen=True)
class QueryStatement:
    statement: str
    parameters: tuple[QueryParam, ...]


class SQLClient(Protocol):
    async def execute(self, query: QueryStatement) -> list[dict[str, Any]]:
        ...


class DatabricksSQLClient:
    def __init__(self, settings: Settings) -> None:
        self.host = settings.databricks_host.rstrip("/") if settings.databricks_host else ""
        self.token = settings.databricks_token
        self.warehouse_id = settings.databricks_sql_warehouse_id

    async def execute(self, query: QueryStatement) -> list[dict[str, Any]]:
        payload = {
            "warehouse_id": self.warehouse_id,
            "statement": query.statement,
            "parameters": [param.as_databricks() for param in query.parameters],
            "format": "JSON_ARRAY",
            "disposition": "INLINE",
            "wait_timeout": "10s",
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.host}/api/2.0/sql/statements/",
                headers={"Authorization": f"Bearer {self.token}"},
                json=payload,
            )
            response.raise_for_status()
        body = response.json()
        columns = [column["name"] for column in body.get("manifest", {}).get("schema", {}).get("columns", [])]
        data = body.get("result", {}).get("data_array", [])
        return [dict(zip(columns, row, strict=False)) for row in data]


class SnowflakeSQLClient:
    def __init__(self, settings: Settings) -> None:
        self.account = settings.snowflake_account
        self.user = settings.snowflake_user
        self.warehouse = settings.snowflake_warehouse
        self.database = settings.snowflake_database
        self.schema = settings.snowflake_schema

    async def execute(self, query: QueryStatement) -> list[dict[str, Any]]:
        raise NotImplementedError("Snowflake SQL API execution is deferred until auth method is confirmed")


def param(name: str, value: str | int | float | date | datetime, type_: QueryParamType = "STRING") -> QueryParam:
    if isinstance(value, datetime):
        value = value.date().isoformat()
        type_ = "DATE"
    elif isinstance(value, date):
        value = value.isoformat()
        type_ = "DATE"
    return QueryParam(name=name, value=value, type=type_)
