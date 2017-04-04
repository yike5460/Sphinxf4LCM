import logging
import time

from api.adapter import construct_adapter
from api.generic import constants
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class Em(object):
    """
    Class of generic functions representing operations exposed by the EM towards the Test Interface as defined by
    ETSI GS NFV-TST 002 v1.1.1 (2016-10).
    """
    def __init__(self, vendor=None, **kwargs):
        """
        Construct the EM object corresponding to the specified vendor.
        """
        self.vendor = vendor
        self.em_adapter = construct_adapter(vendor, module_type='em', **kwargs)

    @log_entry_exit(LOG)
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        """
        This function provides the status of a VNF lifecycle management operation.

        This function was written in accordance with section 7.2.13 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

        :param lifecycle_operation_occurrence_id:   ID of the VNF lifecycle operation occurrence.
        :return:                                    The status of the operation ex. 'Processing', 'Failed'.
        """

        return self.em_adapter.get_operation_status(lifecycle_operation_occurrence_id)

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
    def modify_vnf_configuration(self, vnf_instance_id, vnf_configuration_data=None, ext_virtual_link=None,
                                 vnfc_configuration_data=None):
        """
        This function is exposed by the EM at the Em-tst interface and is used by the Test System to trigger
        ModifyConfiguration on the VNF from the EM (and through the VNFM).

        This function is a re-exposure of the VNF Configuration Management interface offered by the VNF/VNFM over the 
        Ve-Vnfm reference points. See ETSI GS NFV-IFA 008 v2.1.1 (2016-10) section 7.6.2.

        :param vnf_instance_id:         Identifier of the VNF instance.
        :param vnf_configuration_data:  Configuration data for the VNF instance.
        :param ext_virtual_link:        Information about external VLs to connect the VNF to.
        :param vnfc_configuration_data: Configuration data related to VNFC instance(s). 
        :return:                        Nothing.
        """

        return self.em_adapter.modify_vnf_configuration(vnf_instance_id, vnf_configuration_data, ext_virtual_link,
                                                        vnfc_configuration_data)

    @log_entry_exit(LOG)
    def vnf_scale(self, vnf_instance_id, type, aspect_id, number_of_steps=1, additional_param=None):
        """
        This function is exposed by the EM at the Em-tst interface and is used by the Test System to trigger VNF scale
        operation and check results at the EM.

        This function scales a VNF horizontally (out/in).

        This function is a re-exposure of the VNF Lifecycle Management interface at the Ve-Vnfm-em reference point.
        See ETSI GS NFV-IFA 008 v2.1.1 (2016-10) section 7.2.4.

        :param vnf_instance_id:     Identifier of the VNF instance to which this scaling request is related.
        :param type:                Defines the type of the scale operation requested (scale out, scale in).
        :param aspect_id:           Identifies the aspect of the VNF that is requested to be scaled, as declared in the
                                    VNFD. Defaults to 1.
        :param number_of_steps:     Number of scaling steps to be executed as part of this ScaleVnf operation.
        :param additional_param:    Additional parameters passed by the NFVO as input to the scaling process, specific
                                    to the VNF being scaled.
        :return:                    Identifier of the VNF lifecycle operation occurrence.
        """

        return self.em_adapter.vnf_scale(vnf_instance_id, type, aspect_id, number_of_steps, additional_param)

    @log_entry_exit(LOG)
    def vnf_scale_sync(self, vnf_instance_id, scale_type, aspect_id, number_of_steps=1, additional_param=None,
                       max_wait_time=constants.SCALE_INTERVAL, poll_interval=constants.POLL_INTERVAL):
        """
        This function synchronously scales a VNF horizontally (out/in).

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
