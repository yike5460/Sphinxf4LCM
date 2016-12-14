class VnfmDummyAdapter(object):
    def __init__(self, logger, **kwargs):
        self.logger = logger

    def get_operation(self, lifecycle_operation_occurrence_id):
        """
        This function provides the status of a VNF lifecycle management operation.

        :param lifecycle_operation_occurrence_id:   ID of the VNF lifecycle operation occurrence.
        :return:                                    The status of the operation ex. "Processing", "Failed".
        """
        self.logger.write_debug("Entering function %s.get_operation" % self.__module__)

        operation_status = "Successfully done"

        self.logger.write_debug("Instantiation operation status: %s" % operation_status)

        self.logger.write_debug("Exiting function %s.get_operation" % self.__module__)

        return operation_status

    def vnf_create_id(self, vnfd_id, vnf_instance_name=None, vnf_instance_description=None):
        """
        This function creates a VNF instance ID and an associated instance of a VnfInfo information element, identified
        by that identifier, in the NOT_INSTANTIATED state without instantiating the VNF or doing any additional
        lifecycle operation(s).

        :param vnfd_id:                     Identifier that identifies the VNFD which defines the VNF instance to be
                                            created.
        :param vnf_instance_name:           Human-readable name of the VNF instance to be created.
        :param vnf_instance_description:    Human-readable description of the VNF instance to be created.
        :return:                            VNF instance identifier just created.
        """
        self.logger.write_debug("Entering function %s.vnf_create_id" % self.__module__)

        vnf_instance_id = "vnfinstanceid"

        self.logger.write_debug("VNF ID: %s" % vnf_instance_id)

        self.logger.write_debug("Exiting function %s.vnf_create_id" % self.__module__)

        return vnf_instance_id

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
        :return:                            The identifier of the VNF lifecycle operation occurrence.
        """
        self.logger.write_debug("Entering function %s.vnf_instantiate" % self.__module__)

        lifecycle_operation_occurrence_id = "12345"

        self.logger.write_debug("Lifecycle operation occurrence ID: %s" % lifecycle_operation_occurrence_id)

        self.logger.write_debug("Exiting function %s.vnf_instantiate" % self.__module__)

        return lifecycle_operation_occurrence_id

    def vnf_query(self, filter, attribute_selector=None):
        """
        This operation provides information about VNF instances. The applicable VNF instances can be chosen based on
        filtering criteria, and the information can be restricted to selected attributes.

        :param filter:              Filter to select the VNF instance(s) about which information is queried.
        :param attribute_selector:  Provides a list of attribute names. If present, only these attributes are returned
                                    for the VNF instance(s) matching the filter. If absent, the complete information is
                                    returned for the VNF instance(s) matching the filter.
        :return:                    The information items about the selected VNF instance(s) that are returned. If
                                    attribute_selector is present, only the attributes listed in attribute_selector are
                                    returned for the selected VNF instance(s).
        """
        self.logger.write_debug("Entering function %s.vnf_query" % self.__module__)

        vnf_info = {'instantiation_state': 'INSTANTIATED',
                    'instantiated_vnf_info': {'vnf_state': 'STARTED'}}

        if attribute_selector == "instantiation_state":
            self.logger.write_debug("VNF instantiation state: %s" % vnf_info['instantiation_state'])
            self.logger.write_debug("Exiting function %s.vnf_query" % self.__module__)
            return vnf_info['instantiation_state']
        elif attribute_selector == "vnf_state":
            self.logger.write_debug("VNF state: %s" % vnf_info['instantiated_vnf_info']['vnf_state'])
            self.logger.write_debug("Exiting function %s.vnf_query" % self.__module__)
            return vnf_info['instantiated_vnf_info']['vnf_state']
        else:
            self.logger.write_debug("Exiting function %s.vnf_query" % self.__module__)
            return vnf_info

    def change_vnf_state(self,
                         vnf_instance_id,
                         change_state_to,
                         stop_type=None,
                         graceful_stop_timeout=None):

        """
        change_vnf_state() - change the state of a VNF instance, including starting and stopping the VNF instance.

        :param vnf_instance_id:             Identifier of the VNF instance.
        :param change_state_to:             The desired state to change the VNF to. Permitted values are: start, stop.
        :param stop_type:                   It signals whether forceful or graceful stop is requested. Allowed values
                                            are: forceful and graceful.
        :param graceful_stop_timeout:       The time interval to wait for the VNF to be taken out of service during
                                            graceful stop, before stopping the VNF.
        :return:                            The identifier of the VNF lifecycle operation occurrence.
        """
        self.logger.write_debug("Entering function %s.change_vnf_state" % self.__module__)

        lifecycle_operation_occurrence_id = "12346"

        self.logger.write_debug("Lifecycle operation occurrence ID: %s" % lifecycle_operation_occurrence_id)

        self.logger.write_debug("Exiting function %s.change_vnf_state" % self.__module__)

        return lifecycle_operation_occurrence_id