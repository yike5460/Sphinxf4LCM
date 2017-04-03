import logging

from api.adapter import construct_adapter
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class Vnf(object):
    """
    Class of generic functions representing operations exposed by the VNF towards the VNFM as defined by 
    ETSI GS NFV-IFA 008 v2.1.1 (2016-10).
    """
    def __init__(self, vendor=None, **kwargs):
        """
        Construct the VNF object corresponding to the specified vendor.
        """
        self.vendor = vendor
        self.vnf_adapter = construct_adapter(vendor, module_type='vnf', **kwargs)

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

    @log_entry_exit(LOG)
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        """
        This function provides the status of a VNF lifecycle management operation.

        This function was written in accordance with section 7.2.13 of ETSI GS NFV-IFA 008 v2.1.1 (2016-10).

        :param lifecycle_operation_occurrence_id:   ID of the VNF lifecycle operation occurrence.
        :return:                                    Status of the operation ex. 'Processing', 'Failed'.
        """

        return self.vnf_adapter.get_operation_status(lifecycle_operation_occurrence_id)

    @log_entry_exit(LOG)
    def scale_to_level(self, vnf_instance_id, instantiation_level_id=None, scale_info=None, additional_param=None):
        """
        This function scales an instantiated VNF of a particular DF to a target size.

        This function was written in accordance with section 7.2.5 of ETSI GS NFV-IFA 008 v2.1.1 (2016-10).

        :param vnf_instance_id:         Identifier of the VNF instance to which this scaling request is related.
        :param instantiation_level_id:  Identifier of the target instantiation level of the current DF to which the
                                        VNF is requested to be scaled. Either instantiationLevelId or scaleInfo
                                        but not both shall be present.
        :param scale_info:              For each scaling aspect of the current DF, defines the target scale level to
                                        which the VNF is to be scaled. Either instantiationLevelId or scaleInfo
                                        but not both shall be present.
        :param additional_param:        Additional parameters passed as input to the scaling process, specific to the
                                        VNF being scaled.
        :return:                        Identifier of the VNF lifecycle operation occurrence.
        """

        return self.vnf_adapter.scale_to_level(vnf_instance_id, instantiation_level_id, scale_info, additional_param)
