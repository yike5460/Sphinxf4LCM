import logging

from api.generic import constants
from api.generic.mano import Mano
from api.generic.traffic import Traffic
from test_cases import TestCase, TestRunError
from utils.misc import generate_name

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNF_STATE_STOP_002(TestCase):
    """
    TC_VNF_STATE_STOP_002 VNF Stop with low traffic load and measure stop time

    Sequence:
    1. Instantiate the VNF
    2. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
    3. Start the low traffic load
    4. Validate the provided functionality
    5. Stop the VNF
    6. Validate VNF instantiation state is INSTANTIATED and VNF state is STOPPED
    7. Validate that no traffic flows once stop is completed
    """
    required_elements = ('mano', 'traffic')

    def setup(self):
        LOG.info('Starting setup for TC_VNF_STATE_STOP_002')

        # Create objects needed by the test.
        self.mano = Mano(vendor=self.tc_input['mano_params']['type'], **self.tc_input['mano_params']['client_config'])
        self.traffic = Traffic(self.tc_input['traffic_params']['type'],
                               **self.tc_input['traffic_params']['client_config'])
        self.register_for_cleanup(self.traffic.destroy)

        # Initialize test case result.
        self.tc_result['events']['instantiate_vnf'] = dict()
        self.tc_result['events']['stop_vnf'] = dict()
        self.tc_result['events']['traffic_deactivation'] = dict()

        LOG.info('Finished setup for TC_VNF_STATE_STOP_002')

    def run(self):
        LOG.info('Starting TC_VNF_STATE_STOP_002')

        # --------------------------------------------------------------------------------------------------------------
        # 1. Instantiate the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Instantiating the VNF')
        self.time_record.START('instantiate_vnf')
        self.vnf_instance_id = self.mano.vnf_create_and_instantiate(
                                                 vnfd_id=self.tc_input['vnfd_id'], flavour_id=None,
                                                 vnf_instance_name=generate_name(self.tc_input['vnf']['instance_name']),
                                                 vnf_instance_description=None)

        self.time_record.END('instantiate_vnf')

        self.tc_result['events']['instantiate_vnf']['duration'] = self.time_record.duration('instantiate_vnf')

        self.register_for_cleanup(self.mano.vnf_terminate_and_delete, vnf_instance_id=self.vnf_instance_id,
                                  termination_type='graceful')
        self.register_for_cleanup(self.mano.wait_for_vnf_stable_state, vnf_instance_id=self.vnf_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 2. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF instantiation state is INSTANTIATED')
        vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id})
        if vnf_info.instantiation_state != constants.VNF_INSTANTIATED:
            raise TestRunError('Unexpected VNF instantiation state',
                               err_details='VNF instantiation state was not "%s" after the VNF was instantiated'
                                           % constants.VNF_INSTANTIATED)

        LOG.info('Validating VNF state is STARTED')
        if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STARTED:
            raise TestRunError('Unexpected VNF state',
                               err_details='VNF state was not "%s" after the VNF was instantiated'
                                           % constants.VNF_STARTED)

        # --------------------------------------------------------------------------------------------------------------
        # 3. Start the low traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the low traffic load')
        self.traffic.configure(traffic_load='LOW_TRAFFIC_LOAD',
                               traffic_config=self.tc_input['traffic_params']['traffic_config'])

        self.traffic.start(return_when_emission_starts=True)

        self.register_for_cleanup(self.traffic.stop)

        # --------------------------------------------------------------------------------------------------------------
        # 4. Validate the provided functionality
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating the provided functionality')
        if not self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is not flowing', err_details='Low traffic did not flow')

        if self.traffic.any_traffic_loss():
            raise TestRunError('Traffic is flowing with packet loss', err_details='Low traffic flew with packet loss')

        if not self.mano.validate_allocated_vresources(self.tc_input['vnfd_id'], self.vnf_instance_id):
            raise TestRunError('Allocated vResources could not be validated')

        self.tc_result['resources']['Initial'] = self.mano.get_allocated_vresources(self.vnf_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 5. Stop the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Stopping the VNF')
        # Clearing counters so traffic deactivation time is accurate
        self.traffic.clear_counters()
        self.time_record.START('stop_vnf')
        if self.mano.vnf_operate_sync(self.vnf_instance_id, change_state_to='stop') != constants.OPERATION_SUCCESS:
            raise TestRunError('MANO could not stop the VNF')
        self.time_record.END('stop_vnf')

        self.tc_result['events']['stop_vnf']['duration'] = self.time_record.duration('stop_vnf')

        self.tc_result['events']['traffic_deactivation']['duration'] = self.traffic.calculate_deactivation_time()

        # --------------------------------------------------------------------------------------------------------------
        # 6. Validate VNF instantiation state is INSTANTIATED and VNF state is STOPPED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF instantiation state is INSTANTIATED')
        vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id})
        if vnf_info.instantiation_state != constants.VNF_INSTANTIATED:
            raise TestRunError('Unexpected VNF instantiation state',
                               err_details='VNF instantiation state was not "%s" after the VNF was stopped'
                                           % constants.VNF_INSTANTIATED)

        LOG.info('Validating VNF state is STOPPED')
        if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STOPPED:
            raise TestRunError('Unexpected VNF state',
                               err_details='VNF state was not "%s" after the VNF was stopped' % constants.VNF_STOPPED)

        # --------------------------------------------------------------------------------------------------------------
        # 7. Validate that no traffic flows once stop is completed
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating that no traffic flows once stop is completed')
        if self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is still flowing', err_details='Traffic still flew after VNF was stopped')

        LOG.info('TC_VNF_STATE_STOP_002 execution completed successfully')
