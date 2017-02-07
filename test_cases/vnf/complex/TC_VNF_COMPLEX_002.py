import logging

from api.generic import constants
from test_cases import TestCase
from api.generic.traffic import Traffic
from api.generic.vnf import Vnf
from api.generic.vnfm import Vnfm

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNF_COMPLEX_002(TestCase):
    """
    TC_VNF_COMPLEX_002 Stop a max scale-up/scaled-out VNF instance in state Active under max traffic load

    Sequence:
    1. Instantiate VNF
    2. Validate VNF state is INSTANTIATED
    3. Start VNF
    4. Validate VNF state is STARTED
    5. Generate low traffic load
    6. Validate that traffic flows through without issues (-> no dropped packets)
    7. Trigger a resize of the NFV resources to reach the maximum
    8. Validate VNF has resized to the max and has max capacity
    9. Generate max traffic load to load all VNF instances
    10. Validate all traffic flows through and has reached max capacity
    11. Clear counters
    12. Stop the VNF (--> time stamp)
    13. Validate VNF has been stopped (--> time stamp)
    14. Validate no traffic flows through (--> last arrival time stamp)
    15. Calculate the time to stop a max scaled VNF under load (--> last arrival time stamp)
    """

    def setup(self):
        LOG.info('Starting setup for TC_VNF_COMPLEX_002')

        self.vnfm = Vnfm(vendor=self.tc_input['vnfm_params']['type'], **self.tc_input['vnfm_params']['client_config'])
        self.vnf = Vnf(vendor=self.tc_input['vnf_vendor'])
        self.traffic = Traffic()

        self.tc_result['overall_status'] = constants.TEST_PASSED
        self.tc_result['error_info'] = 'No errors'
        self.tc_result['resource_list'] = {}

        LOG.info('Finished setup for TC_VNF_COMPLEX_002')

        return True

    def run(self):
        LOG.info('Starting TC_VNF_COMPLEX_002')

        # --------------------------------------------------------------------------------------------------------------
        # 1. Instantiate VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Instantiating VNF')
        self.time_record.START('instantiate_vnf')
        self.vnf_instance_id = self.vnfm.vnf_create_and_instantiate(
                                                                   vnfd_id=self.tc_input['vnfd_id'], flavour_id=None,
                                                                   vnf_instance_name=self.tc_input['vnf_instance_name'],
                                                                   vnf_instance_description=None)
        if self.vnf_instance_id is None:
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unexpected VNF instantiation ID')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF instantiation operation failed'
            return False

        self.register_for_cleanup(self.vnfm.vnf_terminate_and_delete, vnf_instance_id=self.vnf_instance_id,
                                  termination_type='graceful')

        # --------------------------------------------------------------------------------------------------------------
        # 2. Validate VNF state is INSTANTIATED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF state is INSTANTIATED')
        vnf_info = self.vnfm.vnf_query(filter=self.vnf_instance_id)
        if vnf_info.instantiation_state != constants.VNF_INSTANTIATED:
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unexpected VNF state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF was not in "%s" state after instantiation' % constants.VNF_INSTANTIATED
            return False

        self.time_record.END('instantiate_vnf')

        self.tc_result['durations']['instantiate_vnf'] = self.time_record.duration('instantiate_vnf')

        # --------------------------------------------------------------------------------------------------------------
        # 3. Start VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting VNF')
        self.time_record.START('start_vnf')
        if self.vnfm.vnf_operate_sync(vnf_instance_id=self.vnf_instance_id, change_state_to='start') != \
                constants.OPERATION_SUCCESS:
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unexpected status for starting VNF operation')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF start operation failed'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 4. Validate VNF state is STARTED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF state is STARTED')
        vnf_info = self.vnfm.vnf_query(filter=self.vnf_instance_id)
        if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STARTED:
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unexpected VNF state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF was not in "%s" state after it was started' % constants.VNF_STARTED
            return False

        self.time_record.END('start_vnf')

        self.tc_result['durations']['start_vnf'] = self.time_record.duration('start_vnf')

        # --------------------------------------------------------------------------------------------------------------
        # 5. Generate low traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Generating low traffic load')
        if not self.traffic.configure(traffic_load="LOW_TRAFFIC_LOAD",
                                      traffic_configuration_parameter=self.tc_input['traffic_config']):
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Low traffic load and traffic configuration parameter could not be applied')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Low traffic load and traffic configuration parameter could not be applied'
            return False

        if not self.traffic.start():
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Traffic could not be started')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Low traffic could not be started'
            return False

        self.register_for_cleanup(self.traffic.stop)

        # --------------------------------------------------------------------------------------------------------------
        # 6. Validate that traffic flows through without issues
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating that traffic flows through without issues')
        if not self.traffic.does_traffic_flow():
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Traffic is not flowing')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Low traffic did not flow'
            return False

        if self.traffic.any_traffic_loss():
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Traffic is flowing with packet loss')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Low traffic flew with packet loss'
            return False

        self.tc_result['resource_list']['normal_level'] = self.vnfm.get_vResource(vnf_instance_id=self.vnf_instance_id)
        if not validate_allocated_vResources(vnf_vResource_list=self.tc_result['resource_list']['normal_level'],
                                             instantiation_level_id='normal_level_id',
                                             resource_type_list=self.tc_input['resource_type']):
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unable to validate normal resource')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF has not been assigned normal resources'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 7. Trigger a resize of the NFV resources to reach the maximum
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering a resize of the NFV resources to reach the maximum')
        scaling_result = constants.OPERATION_FAILED
        if self.tc_input['scaling_trigger'] == 'command_to_vnfm':
            scaling_result = self.vnfm.vnf_scale_to_level_sync(vnf_instance_id=self.vnf_instance_id,
                                                               instantiation_level_id='max_level_id')

        elif self.tc_input['scaling_trigger'] == 'triggered_by_vnf':
            scaling_result = self.vnf.scale_to_level_sync(vnf_instance_id=self.vnf_instance_id,
                                                          instantiation_level_id='max_level_id')

        if scaling_result != constants.OPERATION_SUCCESS:
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unexpected status for resize triggering operation')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF resize operation failed'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 8. Validate VNF has resized to the max and has max capacity
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF has resized to the max and has max capacity')
        self.tc_result['resource_list']['after_resize'] = self.vnfm.get_vResource(vnf_instance_id=self.vnf_instance_id)
        if not validate_allocated_vResources(vnf_vResource_list=self.tc_result['resource_list']['after_resize'],
                                             instantiation_level_id='max_level_id',
                                             resource_type_list=self.tc_input['resource_type']):
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unable to validate resources after resize')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF has not been assigned max resources after resize'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 9. Generate max traffic load to load all VNF instances
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Generating max traffic load to load all VNF instances')
        if not self.traffic.configure(traffic_load="MAX_TRAFFIC_LOAD",
                                      traffic_configuration_parameter=self.tc_input['traffic_config']):
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Max traffic load and traffic configuration parameter could not be applied')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Max traffic load and traffic configuration parameter could not be applied'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 10. Validate all traffic flows through and has reached max capacity
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating all traffic flows through and has reached max capacity')
        if not self.traffic.does_traffic_flow():
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Traffic is not flowing')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Max traffic is not flowing'
            return False

        if self.traffic.any_traffic_loss():
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Traffic is flowing with packet loss')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Max traffic is flowing with packet loss'
            return False

        self.tc_result['resource_list']['after_max_traffic'] = self.vnfm.get_vResource(
            vnf_instance_id=self.vnf_instance_id)
        if not validate_allocated_vResources(vnf_vResource_list=self.tc_result['resource_list']['after_max_traffic'],
                                             instantiation_level_id='max_level_id',
                                             resource_type_list=self.tc_input['resource_type']):
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unable to validate maximum resources')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'vResource change after applying max traffic'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 11. Clear counters
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Clearing counters')
        if not self.traffic.clear_counters():
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Traffic counters could not be cleared')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Traffic counters could not be cleared'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 12. Stop the VNF (--> time stamp)
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Stopping the VNF')
        self.time_record.START('stop_vnf')
        if self.vnfm.vnf_operate_sync(vnf_instance_id=self.vnf_instance_id, change_state_to='stop') != \
                constants.OPERATION_SUCCESS:
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unexpected status for starting VNF operation')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF stop operation failed'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 13. Validate VNF has been stopped (--> time stamp)
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF state is STOPPED')
        vnf_info = self.vnfm.vnf_query(filter=self.vnf_instance_id)
        if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STOPPED:
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unexpected VNF state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF was not in "%s" state after it was stopped' % constants.VNF_STOPPED
            return False

        self.time_record.END('stop_vnf')

        # --------------------------------------------------------------------------------------------------------------
        # 14. Validate no traffic flows through (--> last arrival time stamp)
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating no traffic flows through')
        if self.traffic.does_traffic_flow():
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Traffic is flowing')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Traffic still flown after the VNF was stopped'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 15. Calculate the time to stop a max scaled VNF under load (--> last arrival time stamp)
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Calculating the time to stop a max scaled VNF under load')
        self.tc_result['durations']['stop_vnf'] = self.time_record.duration('stop_vnf')

        LOG.info('TC_VNF_COMPLEX_002 execution completed successfully')

        return True
