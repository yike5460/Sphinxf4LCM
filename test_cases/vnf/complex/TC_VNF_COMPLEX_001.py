import logging
import time

from api.generic import constants
from api.generic.mano import Mano
from api.generic.traffic import Traffic
from test_cases import TestCase, TestRunError
from utils.misc import generate_name

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNF_COMPLEX_001(TestCase):
    """
    TC_VNF_COMPLEX_001 VNF Start and Scaling with max traffic load

    Sequence:
    1. Start the max traffic load
    2. Instantiate the VNF
    3. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
    4. Wait for the VNF to scale out to the maximum
    5. Calculate the time for the activation
    6. Validate traffic flows with no dropped packets
    7. Validate allocated vResources
    8. Stop the VNF
    9. Validate that no traffic flows once stop is completed
    """

    required_elements = ('mano', 'traffic', 'vnfd_id', 'scaling_policy_name')

    def setup(self):
        LOG.info('Starting setup for TC_VNF_COMPLEX_001')

        # Create objects needed by the test.
        self.mano = Mano(vendor=self.tc_input['mano']['type'], **self.tc_input['mano']['client_config'])
        self.traffic = Traffic(self.tc_input['traffic']['type'], **self.tc_input['traffic']['client_config'])
        self.register_for_cleanup(index=10, function_reference=self.traffic.destroy)

        # Initialize test case result.
        self.tc_result['events']['instantiate_vnf'] = dict()
        self.tc_result['events']['scale_out_vnf'] = dict()
        self.tc_result['events']['stop_vnf'] = dict()
        self.tc_result['events']['traffic_activation'] = dict()
        self.tc_result['events']['traffic_deactivation'] = dict()

        LOG.info('Finished setup for TC_VNF_COMPLEX_001')

    def run(self):
        LOG.info('Starting TC_VNF_COMPLEX_001')

        # Get scaling policy properties
        sp = self.mano.get_vnfd_scaling_properties(self.tc_input['vnfd_id'], self.tc_input['scaling_policy_name'])

        # --------------------------------------------------------------------------------------------------------------
        # 1. Start the max traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the max traffic load')
        self.traffic.configure(traffic_load='MAX_TRAFFIC_LOAD',
                               traffic_config=self.tc_input['traffic']['traffic_config'])

        self.traffic.start(return_when_emission_starts=True)

        self.register_for_cleanup(index=20, function_reference=self.traffic.stop)

        # --------------------------------------------------------------------------------------------------------------
        # 2. Instantiate the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Instantiating the VNF')
        self.time_record.START('instantiate_vnf')
        self.vnf_instance_id = self.mano.vnf_create_and_instantiate(
                          vnfd_id=self.tc_input['vnfd_id'], flavour_id=self.tc_input['flavour_id'],
                          vnf_instance_name=generate_name(self.tc_input['vnf']['instance_name']),
                          vnf_instance_description=None, instantiation_level_id=self.tc_input['instantiation_level_id'],
                          additional_param=self.tc_input['mano']['instantiation_params'])

        if self.vnf_instance_id is None:
            raise TestRunError('VNF instantiation operation failed')

        self.time_record.END('instantiate_vnf')

        self.tc_result['events']['instantiate_vnf']['duration'] = self.time_record.duration('instantiate_vnf')

        self.register_for_cleanup(index=30, function_reference=self.mano.vnf_terminate_and_delete,
                                  vnf_instance_id=self.vnf_instance_id, termination_type='graceful',
                                  additional_param=self.tc_input['mano']['termination_params'])
        self.register_for_cleanup(index=40, function_reference=self.mano.wait_for_vnf_stable_state,
                                  vnf_instance_id=self.vnf_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 3. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF instantiation state is INSTANTIATED')
        vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id,
                                               'additional_param': self.tc_input['mano']['query_params']})
        if vnf_info.instantiation_state != constants.VNF_INSTANTIATED:
            raise TestRunError('Unexpected VNF instantiation state',
                               err_details='VNF instantiation state was not "%s" after the VNF was instantiated'
                                           % constants.VNF_INSTANTIATED)

        LOG.info('Validating VNF state is STARTED')
        if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STARTED:
            raise TestRunError('Unexpected VNF state',
                               err_details='VNF state was not "%s" after the VNF was instantiated'
                                           % constants.VNF_STARTED)

        self.tc_result['resources']['Initial'] = self.mano.get_allocated_vresources(
                                                                                  self.vnf_instance_id,
                                                                                  self.tc_input['mano']['query_params'])

        self.tc_result['scaling_out']['traffic_before'] = 'MAX_TRAFFIC_LOAD'

        # --------------------------------------------------------------------------------------------------------------
        # 4. Wait for the VNF to scale out to the maximum
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Waiting for the VNF to scale out to the maximum')
        # The scale out duration will include:
        # - the time it takes the VNF CPU load to increase (caused by the max traffic load)
        # - the time after which the scaling alarm is triggered
        # - the time it takes the VNF to scale out
        self.time_record.START('scale_out_vnf')
        elapsed_time = 0
        while elapsed_time < constants.VNF_SCALE_OUT_TIMEOUT:
            vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id,
                                                   'additional_param': self.tc_input['mano']['query_params']})
            if len(vnf_info.instantiated_vnf_info.vnfc_resource_info) == sp['max_instances']:
                break
            else:
                time.sleep(constants.POLL_INTERVAL)
                elapsed_time += constants.POLL_INTERVAL
            if elapsed_time == constants.VNF_SCALE_OUT_TIMEOUT:
                self.tc_result['scaling_out']['status'] = 'Fail'
                raise TestRunError('VNF has not scaled out to the maximum')

        self.time_record.END('scale_out_vnf')

        self.tc_result['events']['scale_out_vnf']['duration'] = self.time_record.duration('scale_out_vnf')

        self.tc_result['resources']['After scale out'] = self.mano.get_allocated_vresources(
                                                                                  self.vnf_instance_id,
                                                                                  self.tc_input['mano']['query_params'])

        self.tc_result['scaling_out']['level'] = sp['max_instances']

        self.tc_result['scaling_out']['status'] = 'Success'

        # --------------------------------------------------------------------------------------------------------------
        # 5. Calculate the time for activation
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Calculating the time for traffic activation')
        self.tc_result['events']['traffic_activation']['duration'] = self.traffic.calculate_activation_time()

        # --------------------------------------------------------------------------------------------------------------
        # 6. Validate traffic flows with no dropped packets
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating traffic flows with no dropped packets')
        # Because the VNF scaled out, we need to reconfigure traffic so that it passes through all VNFCs.

        # Stop the max traffic load.
        self.traffic.stop()

        # Configure stream destination address(es).
        dest_addr_list = ''
        for ext_cp_info in vnf_info.instantiated_vnf_info.ext_cp_info:
            if ext_cp_info.cpd_id == self.tc_input['traffic']['traffic_config']['ingress_cp_name']:
                dest_addr_list += ext_cp_info.address[0] + ' '

        self.traffic.reconfig_traffic_dest(dest_addr_list)
        self.traffic.clear_counters()

        # Start the max traffic load.
        self.traffic.start(return_when_emission_starts=True)

        if not self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is not flowing', err_details='Max traffic did not flow')

        if self.traffic.any_traffic_loss(tolerance=constants.TRAFFIC_TOLERANCE):
            raise TestRunError('Traffic is flowing with packet loss', err_details='Max traffic flew with packet loss')

        self.tc_result['scaling_out']['traffic_after'] = 'MAX_TRAFFIC_LOAD'

        # --------------------------------------------------------------------------------------------------------------
        # 7. Validate allocated vResources
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating allocated vResources')
        if not self.mano.validate_allocated_vresources(self.tc_input['vnfd_id'], self.vnf_instance_id,
                                                       self.tc_input['mano']['query_params']):
            raise TestRunError('Allocated vResources could not be validated')

        # --------------------------------------------------------------------------------------------------------------
        # 8. Stop the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Stopping the VNF')
        # Clearing counters so traffic deactivation time is accurate
        self.traffic.clear_counters()
        self.time_record.START('stop_vnf')
        if self.mano.vnf_operate_sync(self.vnf_instance_id, change_state_to='stop',
                                      additional_param=self.tc_input['mano']['operate_params']) \
                != constants.OPERATION_SUCCESS:
            raise TestRunError('MANO could not stop the VNF')
        self.time_record.END('stop_vnf')

        self.tc_result['events']['stop_vnf']['duration'] = self.time_record.duration('stop_vnf')

        self.tc_result['events']['traffic_deactivation']['duration'] = self.traffic.calculate_deactivation_time()

        # --------------------------------------------------------------------------------------------------------------
        # 9. Validate that no traffic flows once stop is completed
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating that no traffic flows once stop is completed')
        if self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is still flowing', err_details='Traffic still flew after VNF was stopped')

        LOG.info('TC_VNF_COMPLEX_001 execution completed successfully')
