import logging
from api.generic import constants
from api.generic.vnf import Vnf
from api.generic.vnfm import Vnfm
from api.generic.tools import vnfinfo_get_instantiation_state, vnfinfo_get_vnf_state
from api.generic.traffic import Traffic
from test_cases import TestCase

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNF_COMPLEX_002(TestCase):
    """
    TC_VNF_COMPLEX_002 Stop a max scale-up/scaled-out VNF instance in state Active under max traffic load

    Sequence:
    1. Instantiate VNF
    2. Validate VNF instantiation state is INSTANTIATED
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
    15. Stop traffic
    16. Calculate the time to stop a max scaled VNF under load (--> last arrival time stamp)
    """

    def run(self):
        LOG.info('Starting TC_VNF_COMPLEX_002')

        vnfm = Vnfm(vendor=self.tc_input['vnfm_vendor'])
        vnf = Vnf(vendor=self.tc_input['vnf_vendor'])
        traffic = Traffic()

        self.tc_result['overall_status'] = constants.TEST_PASSED
        self.tc_result['error_info'] = 'No errors'

        # --------------------------------------------------------------------------------------------------------------
        # 1. Instantiate VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Instantiating VNF')
        self.time_record.START('instantiate_vnf')
        vnf_instance_id = vnfm.vnf_create_and_instantiate(vnfd_id='vnfd_id', flavour_id='123456',
                                                          vnf_instance_name='test_vnf',
                                                          vnf_instance_description='VNF used for testing')
        if vnf_instance_id is None:
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unexpected VNF instantiation ID')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF instantiation operation failed'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 2. Validate VNF instantiation state is INSTANTIATED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF instantiation state is INSTANTIATED')
        vnf_info = vnfm.vnf_query(filter=vnf_instance_id)
        if vnfinfo_get_instantiation_state(vnfinfo_dict=vnf_info) != constants.VNF_INSTANTIATED:
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unexpected VNF instantiation state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF was not in "%s" state after instantiation' % constants.VNF_INSTANTIATED
            return False

        self.time_record.END('instantiate_vnf')

        # --------------------------------------------------------------------------------------------------------------
        # 3. Start VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting VNF')
        self.time_record.START('start_vnf')
        if vnfm.vnf_operate_sync(vnf_instance_id=vnf_instance_id, change_state_to='start') != \
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
        vnf_info = vnfm.vnf_query(filter=vnf_instance_id)
        if vnfinfo_get_vnf_state(vnfinfo_dict=vnf_info) != constants.VNF_STARTED:
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unexpected VNF state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF was not in "%s" state after it was started' % constants.VNF_STARTED
            return False

        self.time_record.END('start_vnf')

        # --------------------------------------------------------------------------------------------------------------
        # 5. Generate low traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Generating low traffic load')
        if not traffic.configure(traffic_load="LOW_TRAFFIC_LOAD",
                                 traffic_configuration_parameter=self.tc_input['traffic_config']):
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Low traffic load and traffic configuration parameter could not be applied')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Low traffic load and traffic configuration parameter could not be applied'
            return False

        if not traffic.start():
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Traffic could not be started')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Low traffic could not be started'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 6. Validate that traffic flows through without issues
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating that traffic flows through without issues')
        if not traffic.does_traffic_flow():
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Traffic is not flowing')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Low traffic did not flow'
            return False

        if traffic.any_traffic_loss():
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Traffic is flowing with packet loss')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Low traffic flew with packet loss'
            return False

        self.tc_result['resource_list'] = {}
        self.tc_result['resource_list']['normal_level'] = vnfm.get_vResource(vnf_instance_id=vnf_instance_id)
        if not vnfm.validate_allocated_vResources(
                           vnf_vResource_list=self.tc_result['resource_list']['normal_level'],
                           instantiation_level_id='normal_level_id', resource_type_list=self.tc_input['resource_type']):
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
            scaling_result = vnfm.vnf_scale_to_level_sync(vnf_instance_id=vnf_instance_id,
                                                          instantiation_level_id='max_level_id')

        elif self.tc_input['scaling_trigger'] == 'triggered_by_vnf':
            scaling_result = vnf.scale_to_level_sync(vnf_instance_id=vnf_instance_id,
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
        self.tc_result['resource_list']['after_resize'] = vnfm.get_vResource(vnf_instance_id=vnf_instance_id)
        if not vnfm.validate_allocated_vResources(
                              vnf_vResource_list=self.tc_result['resource_list']['after_resize'],
                              instantiation_level_id='max_level_id', resource_type_list=self.tc_input['resource_type']):
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unable to validate resources after resize')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF has not been assigned max resources after resize'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 9. Generate max traffic load to load all VNF instances
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Generating max traffic load to load all VNF instances')
        if not traffic.configure(traffic_load="MAX_TRAFFIC_LOAD",
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
        if not traffic.does_traffic_flow():
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Traffic is not flowing')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Max traffic is not flowing'
            return False

        if traffic.any_traffic_loss():
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Traffic is flowing with packet loss')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Max traffic is flowing with packet loss'
            return False

        self.tc_result['resource_list']['after_max_traffic'] = vnfm.get_vResource(vnf_instance_id=vnf_instance_id)
        if not vnfm.validate_allocated_vResources(
                vnf_vResource_list=self.tc_result['resource_list']['after_max_traffic'],
                instantiation_level_id='max_level_id', resource_type_list=self.tc_input['resource_type']):
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unable to validate maximum resources')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'vResource change after applying max traffic'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 11. Clear counters
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Clearing counters')
        if not traffic.clear_counters():
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
        if vnfm.vnf_operate_sync(vnf_instance_id=vnf_instance_id, change_state_to='stop') != \
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
        vnf_info = vnfm.vnf_query(filter=vnf_instance_id)
        if vnfinfo_get_vnf_state(vnfinfo_dict=vnf_info) != constants.VNF_STOPPED:
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
        if traffic.does_traffic_flow():
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Traffic is flowing')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Traffic still flown after the VNF was stopped'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 15. Stop traffic
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Stopping traffic')
        if not traffic.stop():
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Traffic could not be stopped')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Traffic could not be stopped'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 16. Calculate the time to stop a max scaled VNF under load (--> last arrival time stamp)
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Calculating the time to stop a max scaled VNF under load')
        self.tc_result['time_records']['stop_vnf_time'] = self.time_record.duration('stop_vnf')

        LOG.info('TC_VNF_COMPLEX_002 execution completed successfully')

        return True

    def cleanup(self):
        LOG.info('Starting cleanup for TC_VNF_COMPLEX_002')
        LOG.info('Finished cleanup for TC_VNF_COMPLEX_002')

        return True
