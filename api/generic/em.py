import logging

from api.adapter import construct_adapter
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class Em(object):
    """
    Class of generic functions representing operations exposed by the EM towards the NFVO as defined by GS NFV-IFA 007.
    """
    def __init__(self, vendor=None, **kwargs):
        """
        Construct the EM object corresponding to the specified vendor.
        """
        self.vendor = vendor
        self.em_adapter = construct_adapter(vendor, module_type='em', **kwargs)

    @log_entry_exit(LOG)
    def modify_vnf_configuration(self, vnf_instance_id, vnf_configuration_data=None, ext_virtual_link=None,
                                 vnfc_configuration_data=None):
        """
        This function is exposed by the EM at the Em-tst interface and is used by the Test System to trigger 
        ModifyConfiguration on the VNF from the EM.

        This function is a re-exposure of the VNF Configuration Management interface offered by the VNF/VNFM over the 
        Ve-Vnfm reference points. See ETSI GS NFV-IFA 008. 

        :param vnf_instance_id:         Identifier of the VNF instance.
        :param vnf_configuration_data:  Configuration data for the VNF instance.
        :param ext_virtual_link:        Information about external VLs to connect the VNF to.
        :param vnfc_configuration_data: Configuration data related to VNFC instance(s). 
        :return:                        Nothing.
        """

        return self.em_adapter.modify_vnf_configuration(vnf_instance_id, vnf_configuration_data, ext_virtual_link,
                                                        vnfc_configuration_data)
