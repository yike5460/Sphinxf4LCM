import logging

LOG = logging.getLogger(__name__)


class VnfDummyAdapter(object):
    def __init__(self, **kwargs):
        pass

    def get_operation_status(self, lifecycle_operation_occurrence_id):
        """
        This function provides the status of a VNF lifecycle management operation.

        This function was written in accordance with section 7.2.13 of GS NFV-IFA 008 - v2.1.1.

        :param lifecycle_operation_occurrence_id:   ID of the VNF lifecycle operation occurrence.
        :return:                                    Status of the operation ex. "Processing", "Failed".
        """
        LOG.debug("Entering function %s.get_operation" % self.__module__)

        operation_status = "Successfully done"

        LOG.debug("Instantiation operation status: %s" % operation_status)

        LOG.debug("Exiting function %s.get_operation" % self.__module__)

        return operation_status

    def scale_to_level(self, vnf_instance_id, instantiation_level_id=None, scale_info=None, additional_param=None):
        """
        This function scales an instantiated VNF of a particular DF to a target size.

        This function was written in accordance with section 7.2.5 of GS NFV-IFA 008 - v2.1.1.

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
        LOG.debug("Entering function %s.scale_to_level" % self.__module__)

        lifecycle_operation_occurrence_id = "scale_to_level_operation_id"

        LOG.debug("Exiting function %s.scale_to_level" % self.__module__)

        return lifecycle_operation_occurrence_id
