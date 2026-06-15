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
        snowflake_type = {
            "STRING": "TEXT",
            "DATE": "TEXT",
            "DOUBLE": "REAL",
            "INT": "FIXED",
        }[self.type]
        return {"type": snowflake_type, "value": str(self.value)}


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
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.account = settings.snowflake_account
        self.user = settings.snowflake_user
        self.token = settings.snowflake_token
        self.warehouse = settings.snowflake_warehouse
        self.database = settings.snowflake_database
        self.schema = settings.snowflake_schema
        self.transport = transport

    async def execute(self, query: QueryStatement) -> list[dict[str, Any]]:
        missing = [
            name
            for name, value in {
                "snowflake_account": self.account,
                "snowflake_user": self.user,
                "snowflake_token": self.token,
                "snowflake_warehouse": self.warehouse,
                "snowflake_database": self.database,
                "snowflake_schema": self.schema,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Snowflake SQL client missing setting: {', '.join(missing)}")
        payload = {
            "statement": query.statement,
            "timeout": 20,
            "database": self.database,
            "schema": self.schema,
            "warehouse": self.warehouse,
            "bindings": {param.name: param.as_snowflake() for param in query.parameters},
        }
        async with httpx.AsyncClient(timeout=20.0, transport=self.transport) as client:
            response = await client.post(
                f"https://{self.account}.snowflakecomputing.com/api/v2/statements",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "X-Snowflake-Authorization-Token-Type": "OAUTH",
                    "Accept": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
        body = response.json()
        metadata = body.get("resultSetMetaData", {})
        columns = [column["name"] for column in metadata.get("rowType", [])]
        data = body.get("data", [])
        return [dict(zip(columns, row, strict=False)) for row in data]


def param(name: str, value: str | int | float | date | datetime, type_: QueryParamType = "STRING") -> QueryParam:
    if isinstance(value, datetime):
        value = value.date().isoformat()
        type_ = "DATE"
    elif isinstance(value, date):
        value = value.isoformat()
        type_ = "DATE"
    return QueryParam(name=name, value=value, type=type_)
