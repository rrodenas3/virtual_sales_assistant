from backend.adapters.crm import CRMPort
from backend.adapters.erp import ERPPort
from backend.adapters.factory import get_crm_port, get_erp_port, get_osa_data_port, get_rgm_data_port, get_shelf_image_port
from backend.adapters.osa import OSADataPort
from backend.adapters.rgm import RGMDataPort
from backend.adapters.shelf_image import ShelfImagePort


def get_osa_adapter() -> OSADataPort:
    return get_osa_data_port()


def get_rgm_adapter() -> RGMDataPort:
    return get_rgm_data_port()


def get_crm_adapter() -> CRMPort:
    return get_crm_port()


def get_erp_adapter() -> ERPPort:
    return get_erp_port()


def get_shelf_image_adapter() -> ShelfImagePort:
    return get_shelf_image_port()
