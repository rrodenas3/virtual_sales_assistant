from functools import lru_cache

from backend.adapters.crm import CRMPort, ExternalCRMAdapter, LocalCRMAdapter
from backend.adapters.erp import ERPPort, ExternalERPAdapter, SandboxERPAdapter
from backend.adapters.osa import MockOSAAdapter, OSADataPort
from backend.adapters.real import DatabricksOSAAdapter, DatabricksRGMAdapter, SnowflakeStoreMasterAdapter
from backend.adapters.rgm import MockRGMAdapter, RGMDataPort
from backend.adapters.shelf_image import ExternalShelfImageAdapter, MockShelfImageAdapter, ShelfImagePort
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


@lru_cache
def get_crm_port() -> CRMPort:
    if settings.crm_adapter == "local":
        return LocalCRMAdapter()
    assert_discovery_ready("crm_writeback")
    return ExternalCRMAdapter(settings)


@lru_cache
def get_erp_port() -> ERPPort:
    if settings.erp_adapter == "sandbox":
        return SandboxERPAdapter()
    assert_discovery_ready("erp_submit")
    return ExternalERPAdapter(settings)


@lru_cache
def get_shelf_image_port() -> ShelfImagePort:
    if settings.shelf_image_adapter == "mock":
        return MockShelfImageAdapter()
    assert_discovery_ready("shelf_image")
    return ExternalShelfImageAdapter(settings)
