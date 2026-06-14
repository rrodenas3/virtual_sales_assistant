from functools import lru_cache

from backend.adapters.osa import MockOSAAdapter, OSADataPort
from backend.adapters.real import DatabricksOSAAdapter, DatabricksRGMAdapter, SnowflakeStoreMasterAdapter
from backend.adapters.rgm import MockRGMAdapter, RGMDataPort
from backend.adapters.store_master import MockStoreMasterAdapter, StoreMasterPort
from backend.config import settings
from backend.governance.discovery import assert_discovery_ready


@lru_cache
def get_osa_data_port() -> OSADataPort:
    if settings.osa_adapter == "mock":
        return MockOSAAdapter()
    assert_discovery_ready("databricks")
    return DatabricksOSAAdapter(settings)


@lru_cache
def get_rgm_data_port() -> RGMDataPort:
    if settings.rgm_adapter == "mock":
        return MockRGMAdapter()
    assert_discovery_ready("databricks")
    return DatabricksRGMAdapter(settings)


@lru_cache
def get_store_master_port() -> StoreMasterPort:
    if settings.store_master_adapter == "mock":
        return MockStoreMasterAdapter()
    assert_discovery_ready("snowflake")
    return SnowflakeStoreMasterAdapter(settings)
