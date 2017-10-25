import logging

from api.adapter.vnf import VnfAdapterError
from utils.logging_module import log_entry_exit

LOG = logging.getLogger(__name__)


class CirrosVnfAdapterError(VnfAdapterError):
    """
    A problem occurred in the VNF LifeCycle Validation Cirros VNF adapter API.
    """
    pass


class CirrosVnfAdapter(object):
    def __init__(self, **kwargs):
        pass

    @log_entry_exit(LOG)
    def config_applied(self):
        return True

    @log_entry_exit(LOG)
    def license_applied(self):
        return True
