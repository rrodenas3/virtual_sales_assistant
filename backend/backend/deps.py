from backend.adapters.factory import get_osa_data_port, get_rgm_data_port
from backend.adapters.osa import OSADataPort
from backend.adapters.rgm import RGMDataPort


def get_osa_adapter() -> OSADataPort:
    return get_osa_data_port()


def get_rgm_adapter() -> RGMDataPort:
    return get_rgm_data_port()
