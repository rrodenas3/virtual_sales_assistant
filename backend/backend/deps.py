from backend.adapters.osa import OSADataPort, osa_adapter
from backend.adapters.rgm import MockRGMAdapter, rgm_adapter


def get_osa_adapter() -> OSADataPort:
    return osa_adapter


def get_rgm_adapter() -> MockRGMAdapter:
    return rgm_adapter
