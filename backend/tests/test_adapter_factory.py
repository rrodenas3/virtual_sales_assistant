import pytest

from backend.adapters.factory import get_osa_data_port, get_rgm_data_port
from backend.adapters.osa import MockOSAAdapter
from backend.adapters.rgm import MockRGMAdapter
from backend.config import settings


def test_factory_returns_mock_adapters_by_default(monkeypatch) -> None:
    monkeypatch.setattr(settings, "osa_adapter", "mock")
    monkeypatch.setattr(settings, "rgm_adapter", "mock")
    get_osa_data_port.cache_clear()
    get_rgm_data_port.cache_clear()
    assert isinstance(get_osa_data_port(), MockOSAAdapter)
    assert isinstance(get_rgm_data_port(), MockRGMAdapter)


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
