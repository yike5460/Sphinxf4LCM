import logging
import time

from api.adapter import construct_adapter
from api.generic import ApiGenericError
from api.generic import constants
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class VnfGenericError(ApiGenericError):
    """
    A problem occurred in the VNF LifeCycle Validation VNF generic API.
    """
    pass


class Vnf(object):
    """
    Class of generic functions representing operations exposed by the VNF towards the VNFM as defined by
    ETSI GS NFV-IFA 008 v2.1.1 (2016-10).
    """
    def __init__(self, vendor, adapter_config, **kwargs):
        """
        Construct the VNF object corresponding to the specified vendor.
        """
        self.vendor = vendor
        self.vnf_adapter = construct_adapter(vendor, module_type='vnf', **adapter_config)

    @log_entry_exit(LOG)
    def config_applied(self):
        """
        This function checks if the configuration has been applied to the VNF.

        :return:            True if the configuration has been applied successfully, False otherwise.
        """

        LOG.debug('We are currently not checking if the configuration has been applied to the VNF')
        return self.vnf_adapter.config_applied()

    def license_applied(self):
        """
        This function checks if the license has been applied to the VNF.

        :return:            True if the license has been applied successfully, False otherwise.
        """

        LOG.debug('We are currently not checking if the license has been applied to the VNF')
        return self.vnf_adapter.license_applied()

    @log_entry_exit(LOG)
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        """
        This function provides the status of a VNF lifecycle management operation.

        This function was written in accordance with section 7.2.13 of ETSI GS NFV-IFA 008 v2.1.1 (2016-10).

        :param lifecycle_operation_occurrence_id:   ID of the VNF lifecycle operation occurrence.
        :return:                                    Status of the operation ex. 'Processing', 'Failed'.
        """

        if lifecycle_operation_occurrence_id is None:
            return constants.OPERATION_FAILED
        else:
            return constants.OPERATION_SUCCESS

    @log_entry_exit(LOG)
    def poll_for_operation_completion(self, lifecycle_operation_occurrence_id, final_states, max_wait_time,
                                      poll_interval):
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
    def scale(self, vnf_instance_id, type, aspect_id, number_of_steps=1, additional_param=None):
        """
        This function is exposed by the VNF at the Vnf-tst interface and is used by the Test System to trigger VNF scale
        operation at the VNF.

        This function is a re-exposure of the VNF Lifecycle Management interface at the Ve-Vnfm-vnf reference point.
        See ETSI GS NFV-IFA 008 v2.1.1 (2016-10) section 7.2.4.

        :param vnf_instance_id:     Identifier of the VNF instance to which this scaling request is related.
        :param type:                Defines the type of the scale operation requested (scale out, scale in).
        :param aspect_id:           Identifies the aspect of the VNF that is requested to be scaled, as declared in the
                                    VNFD.
        :param number_of_steps:     Number of scaling steps to be executed as part of this ScaleVnf operation.
                                    Defaults to 1.
        :param additional_param:    Additional parameters passed by the NFVO as input to the scaling process, specific
                                    to the VNF being scaled.
        :return:                    Identifier of the VNF lifecycle operation occurrence.
        """

        return self.vnf_adapter.scale(vnf_instance_id, type, aspect_id, number_of_steps, additional_param)

    @log_entry_exit(LOG)
    def scale_sync(self, vnf_instance_id, scale_type, aspect_id, number_of_steps=1, additional_param=None,
                   poll_interval=constants.POLL_INTERVAL):
        """
        This function synchronously scales the VNF horizontally (out/in).

        :param vnf_instance_id:     Identifier of the VNF instance to which this scaling request is related.
        :param scale_type:          Defines the type of the scale operation requested. Possible values: 'in', or 'out'
        :param aspect_id:           Identifies the aspect of the VNF that is requested to be scaled, as declared in the
                                    VNFD.
        :param number_of_steps:     Number of scaling steps to be executed as part of this ScaleVnf operation.
                                    Defaults to 1.
        :param additional_param:    Additional parameters passed by the NFVO as input to the scaling process, specific
                                    to the VNF being scaled.
        :param poll_interval:       Interval of time in seconds between consecutive polls on the scaling operation
                                    result.
        :return:                    Operation status.
        """
        lifecycle_operation_occurrence_id = self.scale(vnf_instance_id, scale_type, aspect_id, number_of_steps,
                                                       additional_param)

        scale_timeouts = {'out': constants.VNF_SCALE_OUT_TIMEOUT,
                          'in': constants.VNF_SCALE_IN_TIMEOUT}

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES,
                                                              max_wait_time=scale_timeouts[scale_type],
                                                              poll_interval=poll_interval)

        return operation_status
