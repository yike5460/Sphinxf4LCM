import logging
import time
from api.adapter import construct_adapter

LOG = logging.getLogger(__name__)

OPERATION_SUCCESS = 'SUCCESS'
OPERATION_FAILED = 'FAILED'
OPERATION_PENDING = 'PENDING'

OPERATION_FINAL_STATES = [OPERATION_SUCCESS, OPERATION_FAILED]


class Vnfm(object):
    def __init__(self, vendor=None, **kwargs):
        self.vendor = vendor
        self.vnfm_adapter = construct_adapter(vendor, "vnfm", **kwargs)

    def __getattr__(self, attr):
        return getattr(self.vnfm_adapter, attr)

    def vnf_instantiate_sync(self, vnf_instance_id, flavour_id, instantiation_level_id=None, ext_virtual_link=None,
                             ext_managed_virtual_link=None, localization_language=None, additional_param=None):
        lifecycle_operation_occurence_id = self.vnf_instantiate(vnf_instance_id, flavour_id, instantiation_level_id,
                                                                ext_virtual_link, ext_managed_virtual_link,
                                                                localization_language, additional_param)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurence_id,
                                                              final_states=OPERATION_FINAL_STATES)

        if operation_status != OPERATION_SUCCESS:
            return OPERATION_FAILED
        return operation_status

    def poll_for_operation_completion(self, lifecycle_operation_occurence_id, final_states, max_wait_time=120,
                                      poll_interval=3):
        operation_pending = True
        elapsed_time = 0

        while operation_pending and elapsed_time < max_wait_time:
            operation_status = self.get_operation_status(lifecycle_operation_occurence_id)
            LOG.info('Got status %s for %s' % (operation_status, lifecycle_operation_occurence_id))
            if operation_status in final_states:
                operation_pending = False
            else:
                time.sleep(poll_interval)
                elapsed_time += poll_interval

        return operation_status
