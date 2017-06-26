import logging

from api.generic import constants
from api.generic.mano import Mano
from api.generic.traffic import Traffic
from test_cases import TestCase, TestRunError
from utils.misc import generate_name

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNF_STATE_INST_006(TestCase):
    """
    TC_VNF_STATE_INST_006 VNF Instantiation with inactive Element Management

    Sequence:
    1. Deactivate EM if needed
    2. Instantiate the VNF
    3. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
    4. Validate the right vResources have been allocated
    5. Start the low traffic load
    6. Validate no traffic flows
    """

    def setup(self):
        LOG.info('Starting setup for TC_VNF_STATE_INST_006')

        # Create objects needed by the test.
        self.mano = Mano(vendor=self.tc_input['mano_params']['type'], **self.tc_input['mano_params']['client_config'])
        self.traffic = Traffic(self.tc_input['traffic_params']['type'],
                               **self.tc_input['traffic_params']['client_config'])
        self.register_for_cleanup(self.traffic.destroy)

        # Initialize test case result.
        self.tc_result['overall_status'] = constants.TEST_PASSED
        self.tc_result['error_info'] = 'No errors'
        self.tc_result['events']['instantiate_vnf'] = dict()

        LOG.info('Finished setup for TC_VNF_STATE_INST_006')

    def run(self):
        LOG.info('Starting TC_VNF_STATE_INST_006')

        # --------------------------------------------------------------------------------------------------------------
        # 1. Deactivate EM if needed
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Deactivating EM')
        # TODO

        # --------------------------------------------------------------------------------------------------------------
        # 2. Instantiate the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Instantiating the VNF')
        self.time_record.START('instantiate_vnf')
        self.vnf_instance_id = self.mano.vnf_create_and_instantiate(
                                                 vnfd_id=self.tc_input['vnfd_id'], flavour_id=None,
                                                 vnf_instance_name=generate_name(self.tc_input['vnf']['instance_name']),
                                                 vnf_instance_description=None)
        if self.vnf_instance_id is None:
            raise TestRunError('Unexpected VNF instantiation ID', err_details='VNF instantiation operation failed')

        self.time_record.END('instantiate_vnf')

        self.tc_result['events']['instantiate_vnf']['duration'] = self.time_record.duration('instantiate_vnf')

        self.register_for_cleanup(self.mano.vnf_terminate_and_delete, vnf_instance_id=self.vnf_instance_id,
                                  termination_type='graceful')

        # --------------------------------------------------------------------------------------------------------------
        # 3. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF instantiation state is INSTANTIATED and VNF state is STARTED')
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
        # 4. Validate the right vResources have been allocated
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating the right vResources have been allocated')
        if not self.mano.validate_allocated_vresources(self.tc_input['vnfd_id'], self.vnf_instance_id):
            raise TestRunError('Allocated vResources could not be validated')

        self.tc_result['resources']['Initial'] = self.mano.get_allocated_vresources(self.vnf_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 5. Start the low traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the low traffic load')
        if not self.traffic.configure(traffic_load='LOW_TRAFFIC_LOAD',
                                      traffic_config=self.tc_input['traffic_params']['traffic_config']):
            raise TestRunError('Low traffic load and traffic configuration parameter could not be applied')

        if not self.traffic.start(return_when_emission_starts=True):
            raise TestRunError('Traffic could not be started', err_details='Low traffic could not be started')

        self.register_for_cleanup(self.traffic.stop)

        # --------------------------------------------------------------------------------------------------------------
        # 6. Validate no traffic flows
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating no traffic flows')
        if self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is not flowing', err_details='Low traffic did not flow')

        LOG.info('TC_VNF_STATE_INST_006 execution completed successfully')
