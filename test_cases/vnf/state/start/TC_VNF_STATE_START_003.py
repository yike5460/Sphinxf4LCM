import logging

from api.generic import constants
from api.generic.mano import Mano
from api.generic.traffic import Traffic
from test_cases import TestCase, TestRunError
from utils.misc import generate_name

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNF_STATE_START_003(TestCase):
    """
    TC_VNF_STATE_START_003 VNF Start under normal traffic load and measure start time

    Sequence:
    1. Instantiate the VNF
    2. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
    3. Start the normal traffic load
    4. Validate traffic goes through
    5. Stop the normal traffic load
    6. Stop the VNF
    7. Validate VNF instantiation state is INSTANTIATED and VNF state is STOPPED
    8. Start the normal traffic load
    9. Validate no traffic goes through
    10. Start the VNF
    11. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
    12. Calculate the time for activation
    13. Validate traffic goes through
    14. Validate no scaling has occurred
    15. Stop the VNF
    16. Validate that no traffic flows once stop is completed
    """

    required_elements = ('mano_params', 'traffic_params')

    def setup(self):
        LOG.info('Starting setup for TC_VNF_STATE_START_003')

        # Create objects needed by the test.
        self.mano = Mano(vendor=self.tc_input['mano_params']['type'], **self.tc_input['mano_params']['client_config'])
        self.traffic = Traffic(self.tc_input['traffic_params']['type'],
                               **self.tc_input['traffic_params']['client_config'])
        self.register_for_cleanup(self.traffic.destroy)

        # Initialize test case result.
        self.tc_result['events']['instantiate_vnf'] = dict()
        self.tc_result['events']['stop_vnf'] = dict()
        self.tc_result['events']['start_vnf'] = dict()
        self.tc_result['events']['traffic_activation'] = dict()

        LOG.info('Finished setup for TC_VNF_STATE_START_003')

    def run(self):
        LOG.info('Starting TC_VNF_STATE_START_003')

        # --------------------------------------------------------------------------------------------------------------
        # 1. Instantiate the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Instantiating the VNF')
        self.time_record.START('instantiate_vnf')
        self.vnf_instance_id = self.mano.vnf_create_and_instantiate(
                                          vnfd_id=self.tc_input['vnfd_id'], flavour_id=None,
                                          vnf_instance_name=generate_name(self.tc_input['vnf_params']['instance_name']),
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

        initial_instances = len(vnf_info.instantiated_vnf_info.vnfc_resource_info)

        # --------------------------------------------------------------------------------------------------------------
        # 3. Start the normal traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the normal traffic load')
        self.traffic.configure(traffic_load='NORMAL_TRAFFIC_LOAD',
                               traffic_config=self.tc_input['traffic_params']['traffic_config'])

        self.traffic.start(return_when_emission_starts=True)

        self.register_for_cleanup(self.traffic.stop)

        # --------------------------------------------------------------------------------------------------------------
        # 4. Validate traffic goes through
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating traffic goes through')
        if not self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is not flowing', err_details='Normal traffic did not flow')

        if self.traffic.any_traffic_loss(tolerance=constants.traffic_tolerance):
            raise TestRunError('Traffic is flowing with packet loss',
                               err_details='Normal traffic flew with packet loss')

        if not self.mano.validate_allocated_vresources(self.tc_input['vnfd_id'], self.vnf_instance_id):
            raise TestRunError('Allocated vResources could not be validated')

        self.tc_result['resources']['Initial'] = self.mano.get_allocated_vresources(self.vnf_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 5. Stop the normal traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Stopping the normal traffic load')
        self.traffic.stop()

        # --------------------------------------------------------------------------------------------------------------
        # 6. Stop the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Stopping the VNF')
        self.time_record.START('stop_vnf')
        if self.mano.vnf_operate_sync(self.vnf_instance_id, change_state_to='stop') != constants.OPERATION_SUCCESS:
            raise TestRunError('MANO could not stop the VNF')
        self.time_record.END('stop_vnf')

        self.tc_result['events']['stop_vnf']['duration'] = self.time_record.duration('stop_vnf')

        # --------------------------------------------------------------------------------------------------------------
        # 7. Validate VNF instantiation state is INSTANTIATED and VNF state is STOPPED
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
        # 8. Start the normal traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the normal traffic load')
        self.traffic.start(return_when_emission_starts=True)

        # --------------------------------------------------------------------------------------------------------------
        # 9. Validate no traffic goes through
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating no traffic goes through')
        if self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is flowing', err_details='Traffic flew before VNF was started')

        # --------------------------------------------------------------------------------------------------------------
        # 10. Start the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the VNF')
        self.time_record.START('start_vnf')
        if self.mano.vnf_operate_sync(self.vnf_instance_id, change_state_to='start') != constants.OPERATION_SUCCESS:
            raise TestRunError('MANO could not start the VNF')
        self.time_record.END('start_vnf')

        self.tc_result['events']['start_vnf']['duration'] = self.time_record.duration('start_vnf')

        # --------------------------------------------------------------------------------------------------------------
        # 11. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF instantiation state is INSTANTIATED')
        vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id})
        if vnf_info.instantiation_state != constants.VNF_INSTANTIATED:
            raise TestRunError('Unexpected VNF instantiation state',
                               err_details='VNF instantiation state was not "%s" after the VNF was started'
                                           % constants.VNF_INSTANTIATED)

        LOG.info('Validating VNF state is STARTED')
        if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STARTED:
            raise TestRunError('Unexpected VNF state',
                               err_details='VNF state was not "%s" after the VNF was started' % constants.VNF_STARTED)

        # --------------------------------------------------------------------------------------------------------------
        # 12. Calculate the time for activation
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Calculating the time for traffic activation')
        self.tc_result['events']['traffic_activation']['duration'] = self.traffic.calculate_activation_time()

        # --------------------------------------------------------------------------------------------------------------
        # 13. Validate traffic goes through
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating traffic goes through')

        # Clearing counters as the traffic lost so far influences the results
        self.traffic.clear_counters()

        if not self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is not flowing', err_details='Normal traffic did not flow')

        if self.traffic.any_traffic_loss(tolerance=constants.traffic_tolerance):
            raise TestRunError('Traffic is flowing with packet loss',
                               err_details='Normal traffic flew with packet loss')

        # --------------------------------------------------------------------------------------------------------------
        # 14. Validate no scaling has occurred
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating no scaling has occurred')
        vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id})
        if len(vnf_info.instantiated_vnf_info.vnfc_resource_info) != initial_instances:
            raise TestRunError('VNF scaling occurred')

        # --------------------------------------------------------------------------------------------------------------
        # 15. Stop the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Stopping the VNF')
        if self.mano.vnf_operate_sync(self.vnf_instance_id, change_state_to='stop') != constants.OPERATION_SUCCESS:
            raise TestRunError('MANO could not stop the VNF')

        # --------------------------------------------------------------------------------------------------------------
        # 16. Validate that no traffic flows once stop is completed
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating that no traffic flows once stop is completed')
        if self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is still flowing', err_details='Traffic still flew after VNF was stopped')

        LOG.info('TC_VNF_STATE_START_003 execution completed successfully')
