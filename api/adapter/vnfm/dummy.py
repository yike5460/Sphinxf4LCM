import logging

from api.adapter.vnfm import VnfmAdapterError
from api.generic import constants
from api.structures.objects import InstantiatedVnfInfo, VnfInfo
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class DummyVnfmAdapterError(VnfmAdapterError):
    """
    A problem occurred in the VNF LifeCycle Validation Dummy VNFM adapter API.
    """
    pass


class DummyVnfmAdapter(object):
    """
    Class of stub functions representing operations exposed by the VNFM towards the NFVO.
    """
    def __init__(self, **kwargs):
        pass

    @log_entry_exit(LOG)
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        operation_status = 'Successfully done'

        LOG.debug('Operation status for operation with ID %s: %s'
                  % (lifecycle_operation_occurrence_id, operation_status))

        return constants.OPERATION_SUCCESS

    @log_entry_exit(LOG)
    def modify_vnf_configuration(self, vnf_instance_id, vnf_configuration_data=None, ext_virtual_link=None):
        return

    @log_entry_exit(LOG)
    def vnf_create_id(self, vnfd_id, vnf_instance_name=None, vnf_instance_description=None):
        vnf_instance_id = 'vnfinstanceid'

        LOG.debug('VNF ID: %s' % vnf_instance_id)

        return vnf_instance_id

    @log_entry_exit(LOG)
    def vnf_delete_id(self, vnf_instance_id):
        return

    @log_entry_exit(LOG)
    def vnf_instantiate(self, vnf_instance_id, flavour_id, instantiation_level_id=None, ext_virtual_link=None,
                        ext_managed_virtual_link=None, localization_language=None, additional_param=None):
        lifecycle_operation_occurrence_id = 'vnf_instantiate_operation_id'

        LOG.debug('Lifecycle operation occurrence ID: %s' % lifecycle_operation_occurrence_id)

        return lifecycle_operation_occurrence_id

    @log_entry_exit(LOG)
    def vnf_operate(self, vnf_instance_id, change_state_to, stop_type=None, graceful_stop_timeout=None):
        lifecycle_operation_occurrence_id = '12346'

        LOG.debug('Lifecycle operation occurrence ID: %s' % lifecycle_operation_occurrence_id)

        return lifecycle_operation_occurrence_id

    @log_entry_exit(LOG)
    def vnf_query(self, filter, attribute_selector=None):
        vnf_info = VnfInfo()
        vnf_info.instantiation_state = 'INSTANTIATED'
        vnf_info.instantiated_vnf_info = InstantiatedVnfInfo()
        vnf_info.instantiated_vnf_info.vnf_state = 'STARTED'

        return vnf_info

    @log_entry_exit(LOG)
    def vnf_scale(self, vnf_instance_id, type, aspect_id, number_of_steps=1, additional_param=None):
        lifecycle_operation_occurrence_id = 'vnf_scale_operation_id'

        return lifecycle_operation_occurrence_id

    @log_entry_exit(LOG)
    def vnf_scale_to_level(self, vnf_instance_id, instantiation_level_id=None, scale_info=None, additional_param=None):
        lifecycle_operation_occurrence_id = 'vnf_scale_to_level_operation_id'

        return lifecycle_operation_occurrence_id

    @log_entry_exit(LOG)
    def vnf_terminate(self, vnf_instance_id, termination_type, graceful_termination_timeout=None):
        lifecycle_operation_occurrence_id = 'vnf_vnf_terminate_operation_id'

        return lifecycle_operation_occurrence_id
