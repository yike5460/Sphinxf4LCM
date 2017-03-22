import logging

from api.adapter import construct_adapter
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class Vnf(object):
    """
    Generic VNF class.
    """
    def __init__(self, vendor=None, **kwargs):
        """
        Construct the VNF object corresponding to the specified vendor.
        """
        self.vendor = vendor
        self.vnf_adapter = construct_adapter(vendor, module_type='vnf', **kwargs)

    def __getattr__(self, attr):
        return getattr(self.vnf_adapter, attr)
