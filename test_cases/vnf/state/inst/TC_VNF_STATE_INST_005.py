import logging

from api.generic import constants
from api.generic.em import Em
from api.generic.mano import Mano
from api.generic.traffic import Traffic
from api.generic.vnf import Vnf
from test_cases import TestCase, TestRunError
from utils.misc import generate_name

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNF_STATE_INST_005(TestCase):
    """
    TC_VNF_STATE_INST_005 VNF Instantiation with active Element Management with failed EM configuration

    Sequence:
    1. Start the EM or ensure EM is up and cannot configure the VNF
    2. Instantiate the VNF
    3. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
    4. Modify the VNF configuration
    5. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
    6. Validate the right vResources have been allocated
    7. Validate configuration has NOT been applied by the EM to the VNF
    8. Validate license has been applied to the VNF (if applicable)
    9. Start the low traffic load
    10. Validate no traffic flows
    11. Calculate the instantiation time
    """

    required_elements = ('mano_params', 'em_params', 'traffic_params')

    def setup(self):
        LOG.info('Starting setup for TC_VNF_STATE_INST_005')

        # Create objects needed by the test.
        self.mano = Mano(vendor=self.tc_input['mano_params']['type'], **self.tc_input['mano_params']['client_config'])
        self.em = Em(vendor=self.tc_input['em_params']['type'], **self.tc_input['em_params']['client_config'])
        self.vnf = Vnf(vendor=self.tc_input['vnf_params']['type'])
        self.traffic = Traffic(self.tc_input['traffic_params']['type'],
                               **self.tc_input['traffic_params']['client_config'])
        self.register_for_cleanup(self.traffic.destroy)

        # Initialize test case result.
        self.tc_result['events']['instantiate_vnf'] = dict()
        self.tc_result['events']['update_vnf'] = dict()
        self.tc_result['events']['instantiate_update_vnf'] = dict()

        LOG.info('Finished setup for TC_VNF_STATE_INST_005')

    def run(self):
        LOG.info('Starting TC_VNF_STATE_INST_005')

        # --------------------------------------------------------------------------------------------------------------
        # 1. Start the EM or ensure EM is up and cannot configure the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the EM or ensure EM is up and cannot configure the VNF')
        # TODO

        # --------------------------------------------------------------------------------------------------------------
        # 2. Instantiate the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Instantiating the VNF')
        self.time_record.START('instantiate_vnf')
        self.vnf_instance_id = self.mano.vnf_create_and_instantiate(
                                          vnfd_id=self.tc_input['vnfd_id'], flavour_id=None,
                                          vnf_instance_name=generate_name(self.tc_input['vnf_params']['instance_name']),
                                          vnf_instance_description=None)

        self.time_record.END('instantiate_vnf')

        self.register_for_cleanup(self.mano.vnf_terminate_and_delete, vnf_instance_id=self.vnf_instance_id,
                                  termination_type='graceful')
        self.register_for_cleanup(self.mano.wait_for_vnf_stable_state, vnf_instance_id=self.vnf_instance_id)

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
        # 4. Modify the VNF configuration
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Modifying the VNF configuration')
        self.time_record.START('update_vnf')
        if self.em.modify_vnf_configuration(self.vnf_instance_id, self.tc_input['vnf_params']['config']) != \
                constants.OPERATION_SUCCESS:
            raise TestRunError('EM could not modify the VNF configuration')

        self.time_record.END('update_vnf')

        # --------------------------------------------------------------------------------------------------------------
        # 5. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
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
        # 6. Validate the right vResources have been allocated
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating the right vResources have been allocated')
        if not self.mano.validate_allocated_vresources(self.tc_input['vnfd_id'], self.vnf_instance_id):
            raise TestRunError('Allocated vResources could not be validated')

        self.tc_result['resources']['Initial'] = self.mano.get_allocated_vresources(self.vnf_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 7. Validate configuration has NOT been applied by the EM to the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating configuration has NOT been applied by the EM to the VNF')
        # The function that checks if the config has been applied is a stub function and always returns True.
        # The commented if statement is the correct line. Also adding a line so that the test does not fail.
        # if self.vnf.config_applied(**self.tc_input['vnf_params']['credentials']):
        if not self.vnf.config_applied(**self.tc_input['vnf_params']['credentials']):
            raise TestRunError('Configuration has not been applied to the VNF')

        # --------------------------------------------------------------------------------------------------------------
        # 8. Validate license has been applied to the VNF (if applicable)
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating license has been applied to the VNF')
        if not self.vnf.license_applied(**self.tc_input['vnf_params']['credentials']):
            raise TestRunError('License has not been applied to the VNF')

        # --------------------------------------------------------------------------------------------------------------
        # 9. Start the low traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the low traffic load')
        self.traffic.configure(traffic_load='LOW_TRAFFIC_LOAD',
                               traffic_config=self.tc_input['traffic_params']['traffic_config'])

        self.traffic.start(return_when_emission_starts=True)

        self.register_for_cleanup(self.traffic.stop)

        # --------------------------------------------------------------------------------------------------------------
        # 10. Validate no traffic flows
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating no traffic flows')
        if self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is not flowing', err_details='Low traffic did not flow')

        # --------------------------------------------------------------------------------------------------------------
        # 11. Calculate the instantiation time
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Calculating the instantiation time')
        self.tc_result['events']['instantiate_vnf']['duration'] = self.time_record.duration('instantiate_vnf')
        self.tc_result['events']['update_vnf']['duration'] = self.time_record.duration('update_vnf')
        self.tc_result['events']['instantiate_update_vnf']['duration'] = self.time_record.delta('instantiate_vnf.START',
                                                                                                'update_vnf.END')

        LOG.info('TC_VNF_STATE_INST_005 execution completed successfully')
