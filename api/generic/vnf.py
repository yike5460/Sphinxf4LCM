import logging
import time

from api.generic import constants
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
