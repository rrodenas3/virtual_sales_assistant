from functools import lru_cache

from backend.adapters.osa import MockOSAAdapter, OSADataPort
from backend.adapters.real import DatabricksOSAAdapter, DatabricksRGMAdapter, SnowflakeStoreMasterAdapter
from backend.adapters.rgm import MockRGMAdapter, RGMDataPort
from backend.config import settings


@lru_cache
def get_osa_data_port() -> OSADataPort:
    if settings.osa_adapter == "mock":
        return MockOSAAdapter()
    return DatabricksOSAAdapter(settings)


@lru_cache
def get_rgm_data_port() -> RGMDataPort:
    if settings.rgm_adapter == "mock":
        return MockRGMAdapter()
    return DatabricksRGMAdapter(settings)


@lru_cache
def get_store_master_port() -> OSADataPort | SnowflakeStoreMasterAdapter:
    if settings.store_master_adapter == "mock":
        return get_osa_data_port()
    return SnowflakeStoreMasterAdapter(settings)
