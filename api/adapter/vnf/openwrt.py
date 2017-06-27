import logging

from api.adapter.vnf import VnfAdapterError
from utils.logging_module import log_entry_exit

LOG = logging.getLogger(__name__)


class OpenwrtVnfAdapterError(VnfAdapterError):
    """
    A problem occurred in the VNF LifeCycle Validation Openwrt VNF adapter API.
    """
    pass


class OpenwrtVnfAdapter(object):
    def __init__(self):
        pass

    @log_entry_exit(LOG)
    def config_applied(self, **credentials):

        return True

    @log_entry_exit(LOG)
    def license_applied(self, **credentials):

        return True

    @log_entry_exit(LOG)
    def scale(self, vnf_instance_id, type, aspect_id, number_of_steps=1, additional_param=None):
        return None
