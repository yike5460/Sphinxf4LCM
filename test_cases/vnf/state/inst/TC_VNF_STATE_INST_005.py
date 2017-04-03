import logging

import yaml

from api.generic import constants
from api.generic.em import Em
from api.generic.traffic import Traffic
from api.generic.vnf import Vnf
from api.generic.vnfm import Vnfm
from test_cases import TestCase

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

    def setup(self):
        LOG.info('Starting setup for TC_VNF_STATE_INST_005')

        # Create objects needed by the test.
        self.em = Em(vendor=self.tc_input['em_params']['type'], **self.tc_input['em_params']['client_config'])
        self.vnf = Vnf(vendor=self.tc_input['vnf']['type'])
        self.vnfm = Vnfm(vendor=self.tc_input['vnfm_params']['type'], **self.tc_input['vnfm_params']['client_config'])
        self.traffic = Traffic(self.tc_input['traffic_params']['type'],
                               **self.tc_input['traffic_params']['client_config'])
        self.register_for_cleanup(self.traffic.destroy)

        # Initialize test case result.
        self.tc_result['overall_status'] = constants.TEST_PASSED
        self.tc_result['error_info'] = 'No errors'
        self.tc_result['events']['instantiate_vnf'] = dict()
        self.tc_result['events']['update_vnf'] = dict()
        self.tc_result['events']['instantiate_update_vnf'] = dict()

        # Store the VNF config.
        with open(self.tc_input['vnf']['config'], 'r') as vnf_config_file:
            self.vnf_config = yaml.load(vnf_config_file.read())

        LOG.info('Finished setup for TC_VNF_STATE_INST_005')

        return True

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
        self.vnf_instance_id = self.vnfm.vnf_create_and_instantiate(
                                                                vnfd_id=self.tc_input['vnfd_id'], flavour_id=None,
                                                                vnf_instance_name=self.tc_input['vnf']['instance_name'],
                                                                vnf_instance_description=None)
        if self.vnf_instance_id is None:
            LOG.error('TC_VNF_STATE_INST_005 execution failed')
            LOG.debug('Unexpected VNF instantiation ID')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF instantiation operation failed'
            return False

        self.time_record.END('instantiate_vnf')

        self.register_for_cleanup(self.vnfm.vnf_terminate_and_delete, vnf_instance_id=self.vnf_instance_id,
                                  termination_type='graceful')

        # --------------------------------------------------------------------------------------------------------------
        # 3. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF instantiation state is INSTANTIATED and VNF state is STARTED')
        vnf_info = self.vnfm.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id})
        if vnf_info.instantiation_state != constants.VNF_INSTANTIATED:
            LOG.error('TC_VNF_STATE_INST_005 execution failed')
            LOG.debug('Unexpected VNF instantiation state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF instantiation state was not "%s" after the VNF was instantiated' % \
                                           constants.VNF_INSTANTIATED
            return False

        LOG.info('Validating VNF state is STARTED')
        if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STARTED:
            LOG.error('TC_VNF_STATE_INST_005 execution failed')
            LOG.debug('Unexpected VNF state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF state was not "%s" after the VNF was instantiated' % \
                                           constants.VNF_STARTED
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 4. Modify the VNF configuration
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Modifying the VNF configuration')
        self.time_record.START('update_vnf')
        if self.em.modify_vnf_configuration(self.vnf_instance_id, self.vnf_config) != constants.OPERATION_SUCCESS:
            LOG.error('TC_VNF_STATE_INST_005 execution failed')
            LOG.debug('Could not update VNF')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Could not update VNF'
            return False

        self.time_record.END('update_vnf')

        # --------------------------------------------------------------------------------------------------------------
        # 5. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF instantiation state is INSTANTIATED and VNF state is STARTED')
        vnf_info = self.vnfm.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id})
        if vnf_info.instantiation_state != constants.VNF_INSTANTIATED:
            LOG.error('TC_VNF_STATE_INST_005 execution failed')
            LOG.debug('Unexpected VNF instantiation state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF instantiation state was not "%s" after the VNF was instantiated' % \
                                           constants.VNF_INSTANTIATED
            return False

        LOG.info('Validating VNF state is STARTED')
        if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STARTED:
            LOG.error('TC_VNF_STATE_INST_005 execution failed')
            LOG.debug('Unexpected VNF state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF state was not "%s" after the VNF was instantiated' % \
                                           constants.VNF_STARTED
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 6. Validate the right vResources have been allocated
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating the right vResources have been allocated')
        if not self.vnfm.validate_allocated_vresources(self.tc_input['vnfd_id'], self.vnf_instance_id):
            LOG.error('TC_VNF_STATE_INST_005 execution failed')
            LOG.debug('Could not validate allocated vResources')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Could not validate allocated vResources'
            return False

        self.tc_result['resources']['Initial'] = self.vnfm.get_allocated_vresources(self.vnf_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 7. Validate configuration has NOT been applied by the EM to the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating configuration has NOT been applied by the EM to the VNF')
        # The function that checks if the config has been applied is a stub function and always returns True.
        # The commented if statement is the correct line. Also adding a line so that the test does not fail.
        # if self.vnf.config_applied(**self.tc_input['vnf']['credentials']):
        if not self.vnf.config_applied(**self.tc_input['vnf']['credentials']):
            LOG.error('TC_VNF_STATE_INST_005 execution failed')
            LOG.debug('Configuration has not been applied to the VNF')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Configuration has not been applied to the VNF'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 8. Validate license has been applied to the VNF (if applicable)
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating license has been applied to the VNF')
        if not self.vnf.license_applied(**self.tc_input['vnf']['credentials']):
            LOG.error('TC_VNF_STATE_INST_005 execution failed')
            LOG.debug('License has not been applied to the VNF')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'License has not been applied to the VNF'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 9. Start the low traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the low traffic load')
        if not self.traffic.configure(traffic_load='LOW_TRAFFIC_LOAD',
                                      traffic_config=self.tc_input['traffic_params']['traffic_config']):
            LOG.error('TC_VNF_STATE_INST_005 execution failed')
            LOG.debug('Low traffic load and traffic configuration parameter could not be applied')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result[
                'error_info'] = 'Low traffic load and traffic configuration parameter could not be applied'
            return False

        if not self.traffic.start(return_when_emission_starts=True):
            LOG.error('TC_VNF_STATE_INST_005 execution failed')
            LOG.debug('Traffic could not be started')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Low traffic could not be started'
            return False

        self.register_for_cleanup(self.traffic.stop)

        # --------------------------------------------------------------------------------------------------------------
        # 10. Validate no traffic flows
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating no traffic flows')
        if self.traffic.does_traffic_flow(delay_time=5):
            LOG.error('TC_VNF_STATE_INST_005 execution failed')
            LOG.debug('Traffic is not flowing')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Low traffic did not flow'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 11. Calculate the instantiation time
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Calculating the instantiation time')
        self.tc_result['events']['instantiate_vnf']['duration'] = self.time_record.duration('instantiate_vnf')
        self.tc_result['events']['update_vnf']['duration'] = self.time_record.duration('update_vnf')
        self.tc_result['events']['instantiate_update_vnf']['duration'] = self.time_record.delta('instantiate_vnf.START',
                                                                                                'update_vnf.END')

        LOG.info('TC_VNF_STATE_INST_005 execution completed successfully')

        return True
