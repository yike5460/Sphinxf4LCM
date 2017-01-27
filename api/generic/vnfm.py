import logging
import time

from api.generic import constants
from api.adapter import construct_adapter
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class Vnfm(object):
    """
    Generic VNFM class.
    """
    def __init__(self, vendor=None, **kwargs):
        """
        Construct the VNFM object corresponding to the specified vendor.
        """
        self.vendor = vendor
        self.vnfm_adapter = construct_adapter(vendor, module_type='vnfm', **kwargs)

    def __getattr__(self, attr):
        return getattr(self.vnfm_adapter, attr)

    @log_entry_exit(LOG)
    def vnf_create_and_instantiate(self, vnfd_id, flavour_id, vnf_instance_name=None, vnf_instance_description=None,
                                   instantiation_level_id=None, ext_virtual_link=None, ext_managed_virtual_link=None,
                                   localization_language=None, additional_param=None):
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
        :return:                            VNF instantiation operation status.
        """
        vnf_instance_id = self.vnf_create_id(vnfd_id, vnf_instance_name, vnf_instance_description)

        if vnf_instance_id is None:
            return None

        lifecycle_operation_occurrence_id = self.vnf_instantiate(vnf_instance_id, flavour_id, instantiation_level_id,
                                                                 ext_virtual_link, ext_managed_virtual_link,
                                                                 localization_language, additional_param)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES)

        if operation_status != constants.OPERATION_SUCCESS:
            return None
        return vnf_instance_id

    @log_entry_exit(LOG)
    def vnf_instantiate_sync(self, vnf_instance_id, flavour_id, instantiation_level_id=None, ext_virtual_link=None,
                             ext_managed_virtual_link=None, localization_language=None, additional_param=None):
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
        :return:                            Operation status.
        """
        lifecycle_operation_occurrence_id = self.vnf_instantiate(vnf_instance_id, flavour_id, instantiation_level_id,
                                                                 ext_virtual_link, ext_managed_virtual_link,
                                                                 localization_language, additional_param)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES)

        return operation_status

    @log_entry_exit(LOG)
    def vnf_operate_sync(self, vnf_instance_id, change_state_to, stop_type=None, graceful_stop_timeout=None):
        """
        This function performs a synchronous change of a VNF state.

        :param vnf_instance_id:         Identifier of the VNF instance.
        :param change_state_to:         Desired state to change the VNF to. Permitted values are: start, stop.
        :param stop_type:               It signals whether forceful or graceful stop is requested. Allowed values
                                        are: forceful and graceful.
        :param graceful_stop_timeout:   Time interval to wait for the VNF to be taken out of service during
                                        graceful stop, before stopping the VNF.
        :return:                        Operation status.
        """
        lifecycle_operation_occurrence_id = self.vnf_operate(vnf_instance_id, change_state_to, stop_type,
                                                             graceful_stop_timeout)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES)

        return operation_status

    @log_entry_exit(LOG)
    def vnf_scale_to_level_sync(self, vnf_instance_id, instantiation_level_id=None, scale_info=None,
                                additional_param=None):
        """
        This function scales synchronously an instantiated VNF of a particular DF to a target size.

        :param vnf_instance_id:         Identifier of the VNF instance to which this scaling request is related.
        :param instantiation_level_id:  Identifier of the target instantiation level of the current DF to which the
                                        VNF is requested to be scaled. Either instantiationLevelId or scaleInfo
                                        but not both shall be present.
        :param scale_info:              For each scaling aspect of the current DF, defines the target scale level to
                                        which the VNF is to be scaled. Either instantiationLevelId or scaleInfo
                                        but not both shall be present.
        :param additional_param:        Additional parameters passed as input to the scaling process, specific to the
                                        VNF being scaled.
        :return:                        Operation status.
        """
        lifecycle_operation_occurrence_id = self.vnf_scale_to_level(vnf_instance_id, instantiation_level_id, scale_info,
                                                                    additional_param)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES)

        return operation_status

    @log_entry_exit(LOG)
    def vnf_terminate_sync(self, vnf_instance_id, termination_type, graceful_termination_type=None):
        """
        This function terminates synchronously a VNF.

        :param vnf_instance_id:             Identifier of the VNF instance to be terminated.
        :param termination_type:            Signals whether forceful or graceful termination is requested.
        :param graceful_termination_type:   The time interval to wait for the VNF to be taken out of service during
                                            graceful termination, before shutting down the VNF and releasing the
                                            resources.
        :return:                            Identifier of the VNF lifecycle operation occurrence.
        """
        lifecycle_operation_occurrence_id = self.vnf_terminate(vnf_instance_id, termination_type,
                                                               graceful_termination_type)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES)

        return operation_status

    @log_entry_exit(LOG)
    def poll_for_operation_completion(self, lifecycle_operation_occurrence_id, final_states, max_wait_time=120,
                                      poll_interval=3):
        """
        This function polls the status of an operation until it reaches a final state or time is up.

        :param lifecycle_operation_occurrence_id:   ID of the VNF lifecycle operation occurrence.
        :param final_states:                        List of states of the operation that when reached, the polling
                                                    stops.
        :param max_wait_time:                       Maximum interval of time in seconds to wait for the operation to
                                                    reach a final state.
        :param poll_interval:                       Interval of time in seconds between consecutive polls.
        :return:                                    VNF instantiation operation status.
        """
        operation_pending = True
        elapsed_time = 0

        while operation_pending and elapsed_time < max_wait_time:
            operation_status = self.get_operation_status(lifecycle_operation_occurrence_id)
            LOG.debug('Got status %s for operation with ID %s' % (operation_status, lifecycle_operation_occurrence_id))
            if operation_status in final_states:
                operation_pending = False
            else:
                LOG.debug('Expected states %s, got %s' % (final_states, operation_status))
                LOG.debug('Sleeping %s seconds' % poll_interval)
                time.sleep(poll_interval)
                LOG.debug('Elapsed time %s seconds out of %s' % (elapsed_time, max_wait_time))
                elapsed_time += poll_interval

        return operation_status
