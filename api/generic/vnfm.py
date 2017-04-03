import logging
import time

from api.adapter import construct_adapter
from api.generic import constants
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class Vnfm(object):
    """
    Class of generic functions representing operations exposed by the VNFM towards the NFVO as defined by 
    ETSI GS NFV-IFA 007 v2.1.1 (2016-10).
    """
    def __init__(self, vendor=None, **kwargs):
        """
        Construct the VNFM object corresponding to the specified vendor.
        """
        self.vendor = vendor
        self.vnfm_adapter = construct_adapter(vendor, module_type='vnfm', **kwargs)

    @log_entry_exit(LOG)
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        """
        This function provides the status of a VNF lifecycle management operation.

        This function was written in accordance with section 7.2.13 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

        :param lifecycle_operation_occurrence_id:   ID of the VNF lifecycle operation occurrence.
        :return:                                    The status of the operation ex. 'Processing', 'Failed'.
        """

        return self.vnfm_adapter.get_operation_status(lifecycle_operation_occurrence_id)

    @log_entry_exit(LOG)
    def poll_for_operation_completion(self, lifecycle_operation_occurrence_id, final_states,
                                      max_wait_time=constants.INSTANTIATION_TIME,
                                      poll_interval=constants.POLL_INTERVAL):
        """
        This function polls the status of an operation until it reaches a final state or time is up.

        :param lifecycle_operation_occurrence_id:   ID of the VNF lifecycle operation occurrence.
        :param final_states:                        List of states of the operation that when reached, the polling
                                                    stops.
        :param max_wait_time:                       Maximum interval of time in seconds to wait for the operation to
                                                    reach a final state.
        :param poll_interval:                       Interval of time in seconds between consecutive polls.
        :return:                                    Operation status.
        """
        operation_pending = True
        elapsed_time = 0

        while operation_pending and elapsed_time < max_wait_time:
            operation_status = self.get_operation_status(lifecycle_operation_occurrence_id)
            LOG.debug('Got status %s for operation with ID %s' % (operation_status, lifecycle_operation_occurrence_id))
            if operation_status in final_states:
                operation_pending = False
            else:
                LOG.debug('Expected state to be one of %s, got %s' % (final_states, operation_status))
                LOG.debug('Sleeping %s seconds' % poll_interval)
                time.sleep(poll_interval)
                elapsed_time += poll_interval
                LOG.debug('Elapsed time %s seconds out of %s' % (elapsed_time, max_wait_time))

        return operation_status

    @log_entry_exit(LOG)
    def validate_allocated_vresources(self, vnfd_id, vnf_instance_id):
        """
        This function checks that the virtual resources allocated to the VNF match the ones in the VNFD.

        :param vnfd_id:         Identifier of the VNFD.
        :param vnf_instance_id: Identifier of the VNF instance.
        :return:                True if the allocated resources are as expected, False otherwise.
        """

        return self.vnfm_adapter.validate_allocated_vresources(vnfd_id, vnf_instance_id)

    @log_entry_exit(LOG)
    def get_allocated_vresources(self, vnf_instance_id):
        """
        This functions retrieves the virtual resources allocated to the VNF with the provided instance ID.

        :param vnf_instance_id: Identifier of the VNF instance.
        :return:                Dictionary with the resources for each VNFC.
        """

        return self.vnfm_adapter.get_allocated_vresources(vnf_instance_id)

    @log_entry_exit(LOG)
    def modify_vnf_configuration(self, vnf_instance_id, vnf_configuration_data=None, ext_virtual_link=None):
        """
        This function enables providing configuration parameters information for a VNF instance.

        This function was written in accordance with section 7.6.2 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

        :param vnf_instance_id:         Identifier of the VNF instance.
        :param vnf_configuration_data:  Configuration data for the VNF instance.
        :param ext_virtual_link:        Information about external VLs to connect the VNF to.
        :return:                        Nothing.
        """

        return self.vnfm_adapter.modify_vnf_configuration(vnf_instance_id, vnf_configuration_data, ext_virtual_link)

    @log_entry_exit(LOG)
    def vnf_create_id(self, vnfd_id, vnf_instance_name=None, vnf_instance_description=None):
        """
        This function creates a VNF instance ID and an associated instance of a VnfInfo information element, identified
        by that identifier, in the NOT_INSTANTIATED state without instantiating the VNF or doing any additional
        lifecycle operation(s).

        This function was written in accordance with section 7.2.2 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

        :param vnfd_id:                     Identifier that identifies the VNFD which defines the VNF instance to be
                                            created.
        :param vnf_instance_name:           Human-readable name of the VNF instance to be created.
        :param vnf_instance_description:    Human-readable description of the VNF instance to be created.
        :return:                            VNF instance identifier just created.
        """

        return self.vnfm_adapter.vnf_create_id(vnfd_id, vnf_instance_name, vnf_instance_description)

    @log_entry_exit(LOG)
    def vnf_create_and_instantiate(self, vnfd_id, flavour_id, vnf_instance_name=None, vnf_instance_description=None,
                                   instantiation_level_id=None, ext_virtual_link=None, ext_managed_virtual_link=None,
                                   localization_language=None, additional_param=None,
                                   max_wait_time=constants.INSTANTIATION_TIME, poll_interval=constants.POLL_INTERVAL):
        """
        This function creates a VNF instance ID and synchronously instantiates a VNF.

        :param vnfd_id:                     Identifier that identifies the VNFD which defines the VNF instance to be
                                            created.
        :param flavour_id:                  Identifier of the VNF DF to be instantiated.
        :param vnf_instance_name:           Human-readable name of the VNF instance to be created.
        :param vnf_instance_description:    Human-readable description of the VNF instance to be created.
        :param instantiation_level_id:      Identifier of the instantiation level of the DF to be instantiated. If not
                                            present, the default instantiation level as declared in the VNFD shall be
                                            instantiated.
        :param ext_virtual_link:            Information about external VLs to connect the VNF to.
        :param ext_managed_virtual_link:    Information about internal VLs that are managed by other entities than the
                                            VNFM.
        :param localization_language:       Localization language of the VNF to be instantiated.
        :param additional_param:            Additional parameters passed as input to the instantiation process, specific
                                            to the VNF being instantiated.
        :param max_wait_time:               Maximum interval of time in seconds to wait for the instantiation operation 
                                            to reach a final state.
        :param poll_interval:               Interval of time in seconds between consecutive polls on the instantiation 
                                            operation status.
        :return:                            VNF instantiation operation status.
        """
        vnf_instance_id = self.vnf_create_id(vnfd_id, vnf_instance_name, vnf_instance_description)
        LOG.debug('VNF instance ID: %s' % vnf_instance_id)

        if vnf_instance_id is None:
            return None

        operation_status = self.vnf_instantiate_sync(vnf_instance_id, flavour_id, instantiation_level_id,
                                                     ext_managed_virtual_link, ext_managed_virtual_link,
                                                     localization_language, additional_param, max_wait_time,
                                                     poll_interval)

        if operation_status != constants.OPERATION_SUCCESS:
            return None
        return vnf_instance_id

    @log_entry_exit(LOG)
    def vnf_delete_id(self, vnf_instance_id):
        """
        This function deletes a VNF instance ID and the associated instance of a VnfInfo information element.

        This function was written in accordance with section 7.2.8 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

        :param vnf_instance_id: VNF instance identifier to be deleted.
        :return:                Nothing.
        """

        return self.vnfm_adapter.vnf_delete_id(vnf_instance_id)

    @log_entry_exit(LOG)
    def vnf_instantiate(self, vnf_instance_id, flavour_id, instantiation_level_id=None, ext_virtual_link=None,
                        ext_managed_virtual_link=None, localization_language=None, additional_param=None):
        """
        This function instantiates a particular deployment flavour of a VNF based on the definition in the VNFD.

        This function was written in accordance with section 7.2.3 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

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

        return self.vnfm_adapter.vnf_instantiate(vnf_instance_id, flavour_id, instantiation_level_id, ext_virtual_link,
                                                 ext_managed_virtual_link, localization_language, additional_param)

    @log_entry_exit(LOG)
    def vnf_instantiate_sync(self, vnf_instance_id, flavour_id, instantiation_level_id=None, ext_virtual_link=None,
                             ext_managed_virtual_link=None, localization_language=None, additional_param=None,
                             max_wait_time=constants.INSTANTIATION_TIME, poll_interval=constants.POLL_INTERVAL):
        """
        This function performs a synchronous VNF instantiation, i.e. instantiates a VNF and then polls the operation
        status until the operation reaches a final state.

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
        :param max_wait_time:               Maximum interval of time in seconds to wait for the instantiation operation 
                                            to reach a final state.
        :param poll_interval:               Interval of time in seconds between consecutive polls on the instantiation
                                            operation status.
                                            seconds.

        :return:                            Operation status.
        """
        lifecycle_operation_occurrence_id = self.vnf_instantiate(vnf_instance_id, flavour_id, instantiation_level_id,
                                                                 ext_virtual_link, ext_managed_virtual_link,
                                                                 localization_language, additional_param)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES,
                                                              max_wait_time=max_wait_time, poll_interval=poll_interval)

        return operation_status

    @log_entry_exit(LOG)
    def vnf_operate(self, vnf_instance_id, change_state_to, stop_type=None, graceful_stop_timeout=None):
        """
        This function changes the state of a VNF instance.

        This function was written in accordance with section 7.2.11 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

        :param vnf_instance_id:         Identifier of the VNF instance.
        :param change_state_to:         Desired state to change the VNF to. Permitted values are: start, stop.
        :param stop_type:               It signals whether forceful or graceful stop is requested. Allowed values are: 
                                        forceful and graceful.
        :param graceful_stop_timeout:   Time interval to wait for the VNF to be taken out of service during graceful 
                                        stop, before stopping the VNF.
        :return:                        The identifier of the VNF lifecycle operation occurrence.
        """

        return self.vnfm_adapter.vnf_operate(vnf_instance_id, change_state_to, stop_type, graceful_stop_timeout)

    @log_entry_exit(LOG)
    def vnf_operate_sync(self, vnf_instance_id, change_state_to, stop_type=None, graceful_stop_timeout=None,
                         max_wait_time=constants.OPERATE_TIME, poll_interval=constants.POLL_INTERVAL):
        """
        This function performs a synchronous change of a VNF state.

        :param vnf_instance_id:         Identifier of the VNF instance.
        :param change_state_to:         Desired state to change the VNF to. Permitted values are: start, stop.
        :param stop_type:               It signals whether forceful or graceful stop is requested. Allowed values
                                        are: forceful and graceful.
        :param graceful_stop_timeout:   Time interval to wait for the VNF to be taken out of service during
                                        graceful stop, before stopping the VNF.
        :param max_wait_time:           Maximum interval of time in seconds to wait for the operate operation to reach a
                                        final state.
        :param poll_interval:           Interval of time in seconds between consecutive polls on the operate operation 
                                        result.
        :return:                        Operation status.
        """
        lifecycle_operation_occurrence_id = self.vnf_operate(vnf_instance_id, change_state_to, stop_type,
                                                             graceful_stop_timeout)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES,
                                                              max_wait_time=max_wait_time, poll_interval=poll_interval)

        return operation_status

    @log_entry_exit(LOG)
    def vnf_query(self, filter, attribute_selector=None):
        """
        This operation provides information about VNF instances. The applicable VNF instances can be chosen based on
        filtering criteria, and the information can be restricted to selected attributes.

        This function was written in accordance with section 7.2.9 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

        :param filter:              Filter to select the VNF instance(s) about which information is queried.
        :param attribute_selector:  Provides a list of attribute names. If present, only these attributes are returned
                                    for the VNF instance(s) matching the filter. If absent, the complete information is
                                    returned for the VNF instance(s) matching the filter.
        :return:                    The information items about the selected VNF instance(s) that are returned. If
                                    attribute_selector is present, only the attributes listed in attribute_selector are
                                    returned for the selected VNF instance(s).
        """

        return self.vnfm_adapter.vnf_query(filter, attribute_selector)

    @log_entry_exit(LOG)
    def vnf_scale(self, vnf_instance_id, type, aspect_id, number_of_steps=1, additional_param=None):
        """
        This function scales a VNF horizontally (out/in) or vertically (up/down).

        This function was written in accordance with section 7.2.4 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

        :param vnf_instance_id:     Identifier of the VNF instance to which this scaling request is related.
        :param type:                Defines the type of the scale operation requested (scale out, scale in).
        :param aspect_id:           Identifies the aspect of the VNF that is requested to be scaled, as declared in the
                                    VNFD. Defaults to 1.
        :param number_of_steps:     Number of scaling steps to be executed as part of this ScaleVnf operation.
        :param additional_param:    Additional parameters passed by the NFVO as input to the scaling process, specific
                                    to the VNF being scaled.
        :return:                    Identifier of the VNF lifecycle operation occurrence.
        """

        return self.vnfm_adapter.vnf_scale(vnf_instance_id, type, aspect_id, number_of_steps, additional_param)

    @log_entry_exit(LOG)
    def vnf_scale_to_level(self, vnf_instance_id, instantiation_level_id=None, scale_info=None, additional_param=None):
        """
        This function scales an instantiated VNF of a particular DF to a target size.

        This function was written in accordance with section 7.2.5 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

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

        return self.vnfm_adapter.vnf_scale_to_level(vnf_instance_id, instantiation_level_id, scale_info,
                                                    additional_param)

    @log_entry_exit(LOG)
    def vnf_scale_sync(self, vnf_instance_id, scale_type, aspect_id, number_of_steps=1, additional_param=None,
                       max_wait_time=constants.SCALE_INTERVAL, poll_interval=constants.POLL_INTERVAL):
        """
        This function scales a VNF horizontally (out/in).

        :param vnf_instance_id:     Identifier of the VNF instance to which this scaling request is related.
        :param scale_type:          Defines the type of the scale operation requested. Possible values: 'in', or 'out'
        :param aspect_id:           Identifies the aspect of the VNF that is requested to be scaled, as declared in the
                                    VNFD. Defaults to 1.
        :param number_of_steps:     Number of scaling steps to be executed as part of this ScaleVnf operation.
        :param additional_param:    Additional parameters passed by the NFVO as input to the scaling process, specific
                                    to the VNF being scaled.
        :param max_wait_time:       Maximum interval of time in seconds to wait for the scaling operation to reach a
                                    final state.
        :param poll_interval:       Interval of time in seconds between consecutive polls on the scaling operation
                                    result.
        :return:                    Operation status.
        """
        lifecycle_operation_occurrence_id = self.vnf_scale(vnf_instance_id, scale_type, aspect_id, number_of_steps,
                                                           additional_param)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES,
                                                              max_wait_time=max_wait_time, poll_interval=poll_interval)

        return operation_status

    @log_entry_exit(LOG)
    def vnf_terminate(self, vnf_instance_id, termination_type, graceful_termination_type=None):
        """
        This function terminates a VNF.

        This function was written in accordance with section 7.2.7 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

        :param vnf_instance_id:             Identifier of the VNF instance to be terminated.
        :param termination_type:            Signals whether forceful or graceful termination is requested.
        :param graceful_termination_type:   The time interval to wait for the VNF to be taken out of service during
                                            graceful termination, before shutting down the VNF and releasing the
                                            resources.
        :return:                            Identifier of the VNF lifecycle operation occurrence.
        """

        return self.vnfm_adapter.vnf_terminate(vnf_instance_id, termination_type, graceful_termination_type)

    @log_entry_exit(LOG)
    def vnf_terminate_and_delete(self, vnf_instance_id, termination_type, graceful_termination_type=None,
                                 max_wait_time=constants.INSTANTIATION_TIME, poll_interval=constants.POLL_INTERVAL):
        """
        This function synchronously terminates a VNF and deletes its instance ID.

        :param vnf_instance_id:             Identifier of the VNF instance to be terminated.
        :param termination_type:            Signals whether forceful or graceful termination is requested.
        :param graceful_termination_type:   The time interval to wait for the VNF to be taken out of service during
                                            graceful termination, before shutting down the VNF and releasing the
                                            resources.
        :param max_wait_time:               Maximum interval of time in seconds to wait for the termination operation to 
                                            reach a final state.
        :param poll_interval:               Interval of time in seconds between consecutive polls on the terminate 
                                            operation status. 
        :return:                            'SUCCESS' if both operations were successful, 'FAILED' otherwise
        """
        operation_status = self.vnf_terminate_sync(vnf_instance_id, termination_type, graceful_termination_type,
                                                   max_wait_time, poll_interval)

        if operation_status != constants.OPERATION_SUCCESS:
            LOG.debug('Expected termination operation status %s, got %s' % (
                constants.OPERATION_SUCCESS, operation_status))
            return operation_status

        self.vnf_delete_id(vnf_instance_id)

    @log_entry_exit(LOG)
    def vnf_terminate_sync(self, vnf_instance_id, termination_type, graceful_termination_type=None,
                           max_wait_time=constants.INSTANTIATION_TIME, poll_interval=constants.POLL_INTERVAL):
        """
        This function terminates synchronously a VNF.

        :param vnf_instance_id:             Identifier of the VNF instance to be terminated.
        :param termination_type:            Signals whether forceful or graceful termination is requested.
        :param graceful_termination_type:   The time interval to wait for the VNF to be taken out of service during
                                            graceful termination, before shutting down the VNF and releasing the
                                            resources.
        :param max_wait_time:               Maximum interval of time in seconds to wait for the terminate operation to 
                                            reach a final state.
        :param poll_interval:               Interval of time in seconds between consecutive polls on the terminate 
                                            operation status. 
        :return:                            Operation status.
        """
        lifecycle_operation_occurrence_id = self.vnf_terminate(vnf_instance_id, termination_type,
                                                               graceful_termination_type)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES,
                                                              max_wait_time=max_wait_time, poll_interval=poll_interval)

        return operation_status
