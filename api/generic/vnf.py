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

    @log_entry_exit(LOG)
    def config_applied(self, **credentials):
        """
        This function checks if the configuration has been applied to the VNF.

        :param credentials: Packed dictionary containing the credentials used to login onto the VNF.
        :return:            True if the configuration has been applied successfully, False otherwise.
        """

        LOG.debug('We are currently not checking if the configuration has been applied to the VNF')
        return self.vnf_adapter.config_applied(**credentials)

    def license_applied(self, **credentials):
        """
        This function checks if the license has been applied to the VNF.

        :param credentials: Packed dictionary containing the credentials used to login onto the VNF.
        :return:            True if the license has been applied successfully, False otherwise.
        """

        LOG.debug('We are currently not checking if the license has been applied to the VNF')
        return self.vnf_adapter.license_applied(**credentials)
