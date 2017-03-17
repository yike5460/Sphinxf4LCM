import logging

from api.generic import constants
from test_cases import TestCase
from api.generic.traffic import Traffic
from api.generic.vnfm import Vnfm

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNF_STATE_START_002(TestCase):
    """
    TC_VNF_STATE_START_002 VNF Start under low traffic load and measure start time

    Sequence:
    1. Instantiate the VNF without load
    2. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
    3. Stop the VNF
    4. Validate VNF instantiation state is INSTANTIATED and VNF state is STOPPED
    5. Start the low traffic load
    6. Validate no traffic goes through
    7. Start the VNF
    8. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED 
    9. Calculate the time for the activation
    10. Validate the provided functionality
    11. Stop the VNF
    12. Ensure that no traffic flows once stop is completed
    """

    def setup(self):
        LOG.info('Starting setup for TC_VNF_STATE_START_002')

        # Create objects needed by the test.
        self.vnfm = Vnfm(vendor=self.tc_input['vnfm_params']['type'], **self.tc_input['vnfm_params']['client_config'])
        self.traffic = Traffic(self.tc_input['traffic_params']['type'],
                               **self.tc_input['traffic_params']['client_config'])
        self.register_for_cleanup(self.traffic.destroy)

        # Initialize test case result.
        self.tc_result['overall_status'] = constants.TEST_PASSED
        self.tc_result['error_info'] = 'No errors'

        LOG.info('Finished setup for TC_VNF_STATE_START_002')

        return True

    def run(self):
        LOG.info('Starting TC_VNF_STATE_START_002')

        # --------------------------------------------------------------------------------------------------------------
        # 1. Instantiate the VNF without load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Instantiating the VNF without load')
        self.time_record.START('instantiate_vnf')
        self.vnf_instance_id = self.vnfm.vnf_create_and_instantiate(
                                                                vnfd_id=self.tc_input['vnfd_id'], flavour_id=None,
                                                                vnf_instance_name=self.tc_input['vnf']['instance_name'],
                                                                vnf_instance_description=None)
        if self.vnf_instance_id is None:
            LOG.error('TC_VNF_STATE_START_002 execution failed')
            LOG.debug('Unexpected VNF instantiation ID')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF instantiation operation failed'
            return False

        self.time_record.END('instantiate_vnf')

        self.tc_result['durations']['instantiate_vnf'] = self.time_record.duration('instantiate_vnf')

        self.register_for_cleanup(self.vnfm.vnf_terminate_and_delete, vnf_instance_id=self.vnf_instance_id,
                                  termination_type='graceful')

        # --------------------------------------------------------------------------------------------------------------
        # 2. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF instantiation state is INSTANTIATED')
        vnf_info = self.vnfm.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id})
        if vnf_info.instantiation_state != constants.VNF_INSTANTIATED:
            LOG.error('TC_VNF_STATE_START_002 execution failed')
            LOG.debug('Unexpected VNF instantiation state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF instantiation state was not "%s" after the VNF was instantiated' \
                                           % constants.VNF_INSTANTIATED
            return False

        LOG.info('Validating VNF state is STARTED')
        if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STARTED:
            LOG.error('TC_VNF_STATE_START_002 execution failed')
            LOG.debug('Unexpected VNF state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF state was not "%s" after the VNF was instantiated' % \
                                           constants.VNF_STARTED
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 3. Stop the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Stopping the VNF')
        self.time_record.START('stop_vnf')
        if self.vnfm.vnf_operate_sync(self.vnf_instance_id, change_state_to='stop') != constants.OPERATION_SUCCESS:
            LOG.error('TC_VNF_STATE_START_002 execution failed')
            LOG.debug('Could not stop VNF')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Could not stop VNF'
            return False
        self.time_record.END('stop_vnf')

        self.tc_result['durations']['stop_vnf'] = self.time_record.duration('stop_vnf')

        # --------------------------------------------------------------------------------------------------------------
        # 4. Validate VNF instantiation state is INSTANTIATED and VNF state is STOPPED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF instantiation state is INSTANTIATED')
        vnf_info = self.vnfm.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id})
        if vnf_info.instantiation_state != constants.VNF_INSTANTIATED:
            LOG.error('TC_VNF_STATE_START_002 execution failed')
            LOG.debug('Unexpected VNF instantiation state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF instantiation state was not "%s" after the VNF was stopped' \
                                           % constants.VNF_INSTANTIATED
            return False

        LOG.info('Validating VNF state is STOPPED')
        if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STOPPED:
            LOG.error('TC_VNF_STATE_START_002 execution failed')
            LOG.debug('Unexpected VNF state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF state was not "%s" after the VNF was stopped' % \
                                           constants.VNF_STOPPED
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 5. Start the low traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Start the low traffic load')
        if not self.traffic.configure(traffic_load='LOW_TRAFFIC_LOAD',
                                      traffic_config=self.tc_input['traffic_params']['traffic_config']):
            LOG.error('TC_VNF_STATE_START_002 execution failed')
            LOG.debug('Low traffic load and traffic configuration parameter could not be applied')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Low traffic load and traffic configuration parameter could not be applied'
            return False

        if not self.traffic.start(return_when_emission_starts=True):
            LOG.error('TC_VNF_STATE_START_002 execution failed')
            LOG.debug('Traffic could not be started')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Low traffic could not be started'
            return False

        self.register_for_cleanup(self.traffic.stop)

        # --------------------------------------------------------------------------------------------------------------
        # 6. Validate no traffic goes through
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating no traffic goes through')
        if self.traffic.does_traffic_flow(delay_time=5):
            LOG.error('TC_VNF_STATE_START_002 execution failed')
            LOG.debug('Traffic is flowing')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Traffic flew before VNF was started'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 7. Start the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the VNF')
        self.time_record.START('start_vnf')
        if self.vnfm.vnf_operate_sync(self.vnf_instance_id, change_state_to='start') != constants.OPERATION_SUCCESS:
            LOG.error('TC_VNF_STATE_START_002 execution failed')
            LOG.debug('Could not start VNF')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Could not start VNF'
            return False
        self.time_record.END('start_vnf')

        self.tc_result['durations']['start_vnf'] = self.time_record.duration('start_vnf')

        # --------------------------------------------------------------------------------------------------------------
        # 8. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF instantiation state is INSTANTIATED')
        vnf_info = self.vnfm.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id})
        if vnf_info.instantiation_state != constants.VNF_INSTANTIATED:
            LOG.error('TC_VNF_STATE_START_002 execution failed')
            LOG.debug('Unexpected VNF instantiation state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF instantiation state was not "%s" after the VNF was started' \
                                           % constants.VNF_INSTANTIATED
            return False

        LOG.info('Validating VNF state is STARTED')
        if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STARTED:
            LOG.error('TC_VNF_STATE_START_002 execution failed')
            LOG.debug('Unexpected VNF state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF state was not "%s" after the VNF was started' % \
                                           constants.VNF_STARTED
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 9. Calculate the time for activation
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Calculating the time for traffic activation')
        self.tc_result['durations']['traffic_activation'] = self.traffic.calculate_activation_time()

        # Clearing counters before checking traffic flows correctly
        self.traffic.clear_counters()

        # --------------------------------------------------------------------------------------------------------------
        # 10. Validate the provided functionality
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating the provided functionality')
        if not self.traffic.does_traffic_flow(delay_time=5):
            LOG.error('TC_VNF_STATE_START_002 execution failed')
            LOG.debug('Traffic is not flowing')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Normal traffic did not flow'
            return False

        if self.traffic.any_traffic_loss():
            LOG.error('TC_VNF_STATE_START_002 execution failed')
            LOG.debug('Traffic is flowing with packet loss')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Normal traffic flew with packet loss'
            return False

        if not self.vnfm.validate_allocated_vresources(self.tc_input['vnfd_id'], self.vnf_instance_id):
            LOG.error('TC_VNF_STATE_START_002 execution failed')
            LOG.debug('Could not validate allocated vResources')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Could not validate allocated vResources'
            return False

        self.tc_result['resources']['Initial'] = self.vnfm.get_allocated_vresources(self.vnf_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 11. Stop the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Stopping the VNF')
        if self.vnfm.vnf_operate_sync(self.vnf_instance_id, change_state_to='stop') != constants.OPERATION_SUCCESS:
            LOG.error('TC_VNF_STATE_START_002 execution failed')
            LOG.debug('Could not stop VNF')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Could not stop VNF'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 12. Ensure that no traffic flows once stop is completed
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Ensuring that no traffic flows once stop is completed')
        if self.traffic.does_traffic_flow(delay_time=5):
            LOG.error('TC_VNF_STATE_START_002 execution failed')
            LOG.debug('Traffic is still flowing')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Traffic still flew after VNF was stopped'
            return False

        LOG.info('TC_VNF_STATE_START_002 execution completed successfully')

        return True
