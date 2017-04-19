import logging

from api.generic import constants
from api.generic.mano import Mano
from api.generic.traffic import Traffic
from test_cases import TestCase

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNF_COMPLEX_003(TestCase):
    """
    TC_VNF_COMPLEX_003 Terminate max scale-up/out VNF in state Active under max traffic load

    Sequence:
    1. Instantiate the VNF
    2. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
    3. Start the low traffic load
    4. Validate that traffic flows through without issues
    5. Trigger a resize of the VNF resources to reach the maximum
    6. Validate VNF has resized to the max and has max capacity
    7. Start the max traffic load
    8. Validate all traffic flows through and has reached max capacity
    9. Terminate the VNF
    10. Validate VNF is terminated and all resources have been released
    11. Validate no traffic flows through
    """

    def setup(self):
        LOG.info('Starting setup for TC_VNF_COMPLEX_003')

        # Create objects needed by the test.
        self.mano = Mano(vendor=self.tc_input['mano_params']['type'], **self.tc_input['mano_params']['client_config'])
        self.traffic = Traffic(self.tc_input['traffic_params']['type'],
                               **self.tc_input['traffic_params']['client_config'])
        self.register_for_cleanup(self.traffic.destroy)

        # Initialize test case result.
        self.tc_result['overall_status'] = constants.TEST_PASSED
        self.tc_result['error_info'] = 'No errors'
        self.tc_result['events']['instantiate_vnf'] = dict()
        self.tc_result['events']['scale_out_vnf'] = dict()
        self.tc_result['events']['service_disruption'] = dict()
        self.tc_result['events']['terminate_vnf'] = dict()
        self.tc_result['events']['traffic_deactivation'] = dict()

        LOG.info('Finished setup for TC_VNF_COMPLEX_003')

        return True

    def run(self):
        LOG.info('Starting TC_VNF_COMPLEX_003')

        # --------------------------------------------------------------------------------------------------------------
        # 1. Instantiate the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Instantiating the VNF')
        self.time_record.START('instantiate_vnf')
        self.vnf_instance_id = self.mano.vnf_create_and_instantiate(
                                                                vnfd_id=self.tc_input['vnfd_id'], flavour_id=None,
                                                                vnf_instance_name=self.tc_input['vnf']['instance_name'],
                                                                vnf_instance_description=None)
        if self.vnf_instance_id is None:
            LOG.error('TC_VNF_COMPLEX_003 execution failed')
            LOG.debug('Unexpected VNF instantiation ID')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF instantiation operation failed'
            return False

        self.time_record.END('instantiate_vnf')

        self.tc_result['events']['instantiate_vnf']['duration'] = self.time_record.duration('instantiate_vnf')

        self.register_for_cleanup(self.mano.vnf_terminate_and_delete, vnf_instance_id=self.vnf_instance_id,
                                  termination_type='graceful')

        # --------------------------------------------------------------------------------------------------------------
        # 2. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF instantiation state is INSTANTIATED')
        vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id})
        if vnf_info.instantiation_state != constants.VNF_INSTANTIATED:
            LOG.error('TC_VNF_COMPLEX_003 execution failed')
            LOG.debug('Unexpected VNF instantiation state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF instantiation state was not "%s" after the VNF was instantiated' \
                                           % constants.VNF_INSTANTIATED
            return False

        LOG.info('Validating VNF state is STARTED')
        if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STARTED:
            LOG.error('TC_VNF_COMPLEX_003 execution failed')
            LOG.debug('Unexpected VNF state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF state was not "%s" after the VNF was instantiated' % \
                                           constants.VNF_STARTED
            return False

        self.tc_result['resources']['Initial'] = self.mano.get_allocated_vresources(self.vnf_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 3. Start the low traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the low traffic load')
        if not self.traffic.configure(traffic_load='LOW_TRAFFIC_LOAD',
                                      traffic_config=self.tc_input['traffic_params']['traffic_config']):
            LOG.error('TC_VNF_COMPLEX_003 execution failed')
            LOG.debug('Low traffic load and traffic configuration parameter could not be applied')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Low traffic load and traffic configuration parameter could not be applied'
            return False

        # Configure stream destination MAC address(es)
        dest_mac_addr_list = ''
        for ext_cp_info in vnf_info.instantiated_vnf_info.ext_cp_info:
            if ext_cp_info.cpd_id == self.tc_input['traffic_params']['traffic_config']['left_cp_name']:
                dest_mac_addr_list += ext_cp_info.address[0] + ' '
        self.traffic.config_traffic_stream(dest_mac_addr_list)

        if not self.traffic.start(return_when_emission_starts=True):
            LOG.error('TC_VNF_COMPLEX_003 execution failed')
            LOG.debug('Traffic could not be started')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Low traffic could not be started'
            return False

        self.register_for_cleanup(self.traffic.stop)

        # --------------------------------------------------------------------------------------------------------------
        # 4. Validate that traffic flows through without issues
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating that traffic flows through without issues')
        if not self.traffic.does_traffic_flow(delay_time=5):
            LOG.error('TC_VNF_COMPLEX_003 execution failed')
            LOG.debug('Traffic is not flowing')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Low traffic did not flow'
            return False

        if self.traffic.any_traffic_loss():
            LOG.error('TC_VNF_COMPLEX_003 execution failed')
            LOG.debug('Traffic is flowing with packet loss')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Low traffic flew with packet loss'
            return False

        self.tc_result['scaling_out']['traffic_before'] = 'LOW_TRAFFIC_LOAD'

        if not self.mano.validate_allocated_vresources(self.tc_input['vnfd_id'], self.vnf_instance_id):
            LOG.error('TC_VNF_COMPLEX_003 execution failed')
            LOG.debug('Could not validate allocated vResources')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Could not validate allocated vResources'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 5. Trigger a resize of the VNF resources to reach the maximum
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering a resize of the VNF resources to reach the maximum')
        self.time_record.START('scale_out_vnf')
        if self.mano.vnf_scale_sync(self.vnf_instance_id, scale_type='out',
                                    aspect_id=self.tc_input['scaling']['aspect'],
                                    additional_param={'scaling_policy_name': self.tc_input['scaling']['policies'][0]}) \
                != constants.OPERATION_SUCCESS:
            LOG.error('TC_VNF_COMPLEX_003 execution failed')
            LOG.debug('Could not scale out VNF')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Could not scale out VNF'
            self.tc_result['scaling_out']['status'] = 'Fail'
            return False

        self.time_record.END('scale_out_vnf')

        self.tc_result['events']['scale_out_vnf']['duration'] = self.time_record.duration('scale_out_vnf')

        self.tc_result['resources']['After scale out'] = self.mano.get_allocated_vresources(self.vnf_instance_id)

        self.tc_result['scaling_out']['status'] = 'Success'

        # --------------------------------------------------------------------------------------------------------------
        # 6. Validate VNF has resized to the max and has max capacity
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF has resized to the max and has max capacity')
        vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id})
        if len(vnf_info.instantiated_vnf_info.vnfc_resource_info) != self.tc_input['scaling']['max_instances']:
            LOG.error('TC_VNF_COMPLEX_003 execution failed')
            LOG.debug('VNF did not scale to the max')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF did not scale to the max'
            return False
        self.tc_result['scaling_out']['level'] = self.tc_input['scaling']['max_instances']

        self.tc_result['events']['service_disruption']['duration'] = self.traffic.calculate_service_disruption_length()

        # --------------------------------------------------------------------------------------------------------------
        # 7. Start the max traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the max traffic load')

        # Stop the low traffic load.
        if not self.traffic.stop():
            LOG.error('TC_VNF_COMPLEX_003 execution failed')
            LOG.debug('Traffic could not be stopped')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Low traffic could not be stopped'
            return False

        # Configure stream destination MAC address(es).
        vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id})
        dest_mac_addr_list = ''
        for ext_cp_info in vnf_info.instantiated_vnf_info.ext_cp_info:
            if ext_cp_info.cpd_id == self.tc_input['traffic_params']['traffic_config']['left_cp_name']:
                dest_mac_addr_list += ext_cp_info.address[0] + ' '

        self.traffic.config_traffic_stream(dest_mac_addr_list)
        self.traffic.config_traffic_load('MAX_TRAFFIC_LOAD')

        # Start the max traffic load.
        if not self.traffic.start(return_when_emission_starts=True):
            LOG.error('TC_VNF_COMPLEX_003 execution failed')
            LOG.debug('Traffic could not be started')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Max traffic could not be started'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 8. Validate all traffic flows through and has reached max capacity
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating all traffic flows through and has reached max capacity')
        if not self.traffic.does_traffic_flow(delay_time=5):
            LOG.error('TC_VNF_COMPLEX_003 execution failed')
            LOG.debug('Traffic is not flowing')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Max traffic did not flow'
            return False

        if self.traffic.any_traffic_loss():
            LOG.error('TC_VNF_COMPLEX_003 execution failed')
            LOG.debug('Traffic is flowing with packet loss')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Max traffic flew with packet loss'
            return False

        self.tc_result['scaling_out']['traffic_after'] = 'MAX_TRAFFIC_LOAD'

        # --------------------------------------------------------------------------------------------------------------
        # 9. Terminate the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Terminating the VNF')
        # Clearing counters so traffic deactivation time is accurate
        self.traffic.clear_counters()
        self.time_record.START('terminate_vnf')
        if self.mano.vnf_terminate_sync(self.vnf_instance_id, termination_type='graceful') != \
                constants.OPERATION_SUCCESS:
            LOG.error('TC_VNF_COMPLEX_003 execution failed')
            LOG.debug('Unexpected status for terminating VNF operation')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF terminate operation failed'
            return False

        self.time_record.END('terminate_vnf')

        self.tc_result['events']['terminate_vnf']['duration'] = self.time_record.duration('terminate_vnf')

        self.tc_result['events']['traffic_deactivation']['duration'] = self.traffic.calculate_deactivation_time()

        # --------------------------------------------------------------------------------------------------------------
        # 10. Validate VNF is terminated and all resources have been released
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF is terminated and all resources have been released')
        vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id})
        if vnf_info.instantiation_state != constants.VNF_NOT_INSTANTIATED:
            LOG.error('TC_VNF_COMPLEX_003 execution failed')
            LOG.debug('Unexpected VNF instantiation state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF instantiation state was not "%s" after the VNF was terminated' \
                                           % constants.VNF_NOT_INSTANTIATED
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 11. Validate no traffic flows through
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating no traffic flows through')
        if self.traffic.does_traffic_flow(delay_time=5):
            LOG.error('TC_VNF_COMPLEX_003 execution failed')
            LOG.debug('Traffic is still flowing')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Traffic still flew after VNF was terminated'
            return False

        LOG.info('TC_VNF_COMPLEX_003 execution completed successfully')

        return True
