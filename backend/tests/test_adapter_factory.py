import pytest

from backend.adapters.factory import get_osa_data_port, get_rgm_data_port, get_store_master_port
from backend.adapters.osa import MockOSAAdapter
from backend.adapters.rgm import MockRGMAdapter
from backend.adapters.store_master import MockStoreMasterAdapter
from backend.config import settings


def test_factory_returns_mock_adapters_by_default(monkeypatch) -> None:
    monkeypatch.setattr(settings, "osa_adapter", "mock")
    monkeypatch.setattr(settings, "rgm_adapter", "mock")
    monkeypatch.setattr(settings, "store_master_adapter", "mock")
    get_osa_data_port.cache_clear()
    get_rgm_data_port.cache_clear()
    get_store_master_port.cache_clear()
    assert isinstance(get_osa_data_port(), MockOSAAdapter)
    assert isinstance(get_rgm_data_port(), MockRGMAdapter)
    assert isinstance(get_store_master_port(), MockStoreMasterAdapter)


def test_databricks_adapter_fails_fast_without_required_settings(monkeypatch) -> None:
    monkeypatch.setattr(settings, "osa_adapter", "databricks")
    monkeypatch.setattr(settings, "discovery_data_sharing_model", "client_databricks")
    monkeypatch.setattr(settings, "discovery_data_residency", "eu-west")
    monkeypatch.setattr(settings, "databricks_host", None)
    monkeypatch.setattr(settings, "databricks_token", None)
    monkeypatch.setattr(settings, "databricks_sql_warehouse_id", None)
    get_osa_data_port.cache_clear()
    with pytest.raises(RuntimeError, match="Databricks OSA adapter missing settings"):
        get_osa_data_port()
    get_osa_data_port.cache_clear()


def test_snowflake_store_master_adapter_fails_fast_without_required_settings(monkeypatch) -> None:
    monkeypatch.setattr(settings, "store_master_adapter", "snowflake")
    monkeypatch.setattr(settings, "discovery_data_sharing_model", "client_databricks")
    monkeypatch.setattr(settings, "discovery_data_residency", "eu-west")
    monkeypatch.setattr(settings, "snowflake_account", None)
    monkeypatch.setattr(settings, "snowflake_user", None)
    monkeypatch.setattr(settings, "snowflake_warehouse", None)
    monkeypatch.setattr(settings, "snowflake_database", None)
    monkeypatch.setattr(settings, "snowflake_schema", None)
    get_store_master_port.cache_clear()
    with pytest.raises(RuntimeError, match="Snowflake store master adapter missing settings"):
        get_store_master_port()
    get_store_master_port.cache_clear()
