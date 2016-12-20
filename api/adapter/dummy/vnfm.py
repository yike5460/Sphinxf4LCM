import logging
from utils.logging_module import log_entry_exit

LOG = logging.getLogger(__name__)


class VnfmDummyAdapter(object):
    def __init__(self, **kwargs):
        pass

    @log_entry_exit(LOG)
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        """
        This function provides the status of a VNF lifecycle management operation.

        This function was written in accordance with section 7.2.13 of GS NFV-IFA 007 - v2.1.1.

        :param lifecycle_operation_occurrence_id:   ID of the VNF lifecycle operation occurrence.
        :return:                                    The status of the operation ex. "Processing", "Failed".
        """
        operation_status = "Successfully done"

        LOG.debug("Operation status for operation with ID %s: %s" % (lifecycle_operation_occurrence_id,
                                                                                   operation_status))

        return operation_status

    @log_entry_exit(LOG)
    def vnf_change_state(self,
                         vnf_instance_id,
                         change_state_to,
                         stop_type=None,
                         graceful_stop_timeout=None):

        """
        vnf_change_state() - change the state of a VNF instance, including starting and stopping the VNF instance.

        :param vnf_instance_id:             Identifier of the VNF instance.
        :param change_state_to:             Desired state to change the VNF to. Permitted values are: start, stop.
        :param stop_type:                   It signals whether forceful or graceful stop is requested. Allowed values
                                            are: forceful and graceful.
        :param graceful_stop_timeout:       Time interval to wait for the VNF to be taken out of service during
                                            graceful stop, before stopping the VNF.
        :return:                            The identifier of the VNF lifecycle operation occurrence.
        """
        lifecycle_operation_occurrence_id = "12346"

        LOG.debug("Lifecycle operation occurrence ID: %s" % lifecycle_operation_occurrence_id)

        return lifecycle_operation_occurrence_id

    @log_entry_exit(LOG)
    def vnf_create_id(self, vnfd_id, vnf_instance_name=None, vnf_instance_description=None):
        """
        This function creates a VNF instance ID and an associated instance of a VnfInfo information element, identified
        by that identifier, in the NOT_INSTANTIATED state without instantiating the VNF or doing any additional
        lifecycle operation(s).

        This function was written in accordance with section 7.2.2 of GS NFV-IFA 007 - v2.1.1.

        :param vnfd_id:                     Identifier that identifies the VNFD which defines the VNF instance to be
                                            created.
        :param vnf_instance_name:           Human-readable name of the VNF instance to be created.
        :param vnf_instance_description:    Human-readable description of the VNF instance to be created.
        :return:                            VNF instance identifier just created.
        """
        vnf_instance_id = "vnfinstanceid"

        LOG.debug("VNF ID: %s" % vnf_instance_id)

        return vnf_instance_id

    @log_entry_exit(LOG)
    def vnf_instantiate(self,
                        vnf_instance_id,
                        flavour_id,
                        instantiation_level_id=None,
                        ext_virtual_link=None,
                        ext_managed_virtual_link=None,
                        localization_language=None,
                        additional_param=None):
        """
        This function instantiates a particular deployment flavour of a VNF based on the definition in the VNFD.

        This function was written in accordance with section 7.2.3 of GS NFV-IFA 007 - v2.1.1.

        :param vnf_instance_id:             Identifier of the VNF instance.
        :param flavour_id:                  Identifier of the VNF DF to be instantiated.
        :param instantiation_level_id:      Identifier of the instantiation level of the DF to be instantiated. If not
                                            present, the default instantiation level as declared in the VNFD shall be
                                            instantiated.
        :param ext_virtual_link:            Information about external VLs to connect the VNF to.
        :param ext_managed_virtual_link:    Information about internal VLs that are managed by other entities than the
                                            VNFM.
        :param localization_language:       Localization language of the VNF to be instantiated.
        :param additional_param:            Additional parameters passed as input to the instantiation process, specific
                                            to the VNF being instantiated.
        :return:                            Identifier of the VNF lifecycle operation occurrence.
        """
        lifecycle_operation_occurrence_id = "vnf_instantiate_operation_id"

        LOG.debug("Lifecycle operation occurrence ID: %s" % lifecycle_operation_occurrence_id)

        return lifecycle_operation_occurrence_id

    @log_entry_exit(LOG)
    def vnf_query(self, filter, attribute_selector=None):
        """
        This operation provides information about VNF instances. The applicable VNF instances can be chosen based on
        filtering criteria, and the information can be restricted to selected attributes.

        This function was written in accordance with section 7.2.9 of GS NFV-IFA 007 - v2.1.1.

        :param filter:              Filter to select the VNF instance(s) about which information is queried.
        :param attribute_selector:  Provides a list of attribute names. If present, only these attributes are returned
                                    for the VNF instance(s) matching the filter. If absent, the complete information is
                                    returned for the VNF instance(s) matching the filter.
        :return:                    The information items about the selected VNF instance(s) that are returned. If
                                    attribute_selector is present, only the attributes listed in attribute_selector are
                                    returned for the selected VNF instance(s).
        """
        vnf_info = {'vnf_instance_id': '',
                    'vnf_instance_name': '',
                    'vnf_instance_description': '',
                    'vnfd_id': '',
                    'vnf_provider': '',
                    'vnf_product_name': '',
                    'vnf_software_version': '',
                    'vnfd_version': '',
                    'onboarded_vnf_pkg_info_id': '',
                    'vnf_configurable_property': '',
                    'instantiation_state': 'INSTANTIATED',
                    'instantiated_vnf_info': {'flavour_id': '',
                                              'vnf_state': 'STARTED',
                                              'scale_status': '',
                                              'ext_cp_info': '',
                                              'ext_virtual_link_info': '',
                                              'ext_managed_virtual_link_info': '',
                                              'monitoring_parameter': '',
                                              'localization_language': '',
                                              'vim_info': '',
                                              'vnfc_resource_info': {'vnfc_instance_id': '',
                                                                     'vdu_id': '',
                                                                     'compute_resource': '',
                                                                     'storage_resource_id': '',
                                                                     'reservation_id': ''},
                                              'virtual_link_resource_info': {'virtual_link_instance_id': '',
                                                                             'virtual_link_desc_id': '',
                                                                             'network_resource': '',
                                                                             'reservation_id': ''},
                                              'virtual_storage_resource_info': {'virtual_storage_instance_id': '',
                                                                                'virtual_storage_desc_id': '',
                                                                                'storage_resource': '',
                                                                                'reservation_id': ''}},
                    'metadata': '',
                    'extension': ''}

        # TODO Add code to parse the vnfInfo dictionary and return a specific attribute.
        # For the moment, return the entire dictionary.

        return vnf_info

    @log_entry_exit(LOG)
    def vnf_scale_to_level(self, vnf_instance_id, instantiation_level_id=None, scale_info=None, additional_param=None):
        """
        This function scales an instantiated VNF of a particular DF to a target size.

        This function was written in accordance with section 7.2.5 of GS NFV-IFA 007 - v2.1.1.

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
        lifecycle_operation_occurrence_id = "vnf_scale_to_level_operation_id"

        return lifecycle_operation_occurrence_id

    @log_entry_exit(LOG)
    def vnf_terminate(self, vnf_instance_id, termination_type, graceful_termination_type=None):
        """
        This function terminates a VNF.

        This function was written in accordance with section 7.2.7 of GS NFV-IFA 007 - v2.1.1.

        :param vnf_instance_id:             Identifier of the VNF instance to be terminated.
        :param termination_type:            Signals whether forceful or graceful termination is requested.
        :param graceful_termination_type:   The time interval to wait for the VNF to be taken out of service during
                                            graceful termination, before shutting down the VNF and releasing the
                                            resources.
        :return:                            Identifier of the VNF lifecycle operation occurrence.
        """
        lifecycle_operation_occurrence_id = "vnf_vnf_terminate_operation_id"

        return lifecycle_operation_occurrence_id
