import logging

from api.generic import constants
from test_cases import TestCase
from api.generic.vnfm import Vnfm

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNF_STATE_INST_002(TestCase):
    """
    TC_VNF_STATE_INST_002 Instantiation without Element Management without traffic without configuration file

    Sequence:
    1. Instantiate VNF without load (--> time stamp)
    2. Validate VNFM reports the state INSTANTIATED (--> time stamp when correct state reached)
    3. Validate the right vResources have been allocated
    4. Calculate the instantiation time
    """

    def setup(self):
        LOG.info('Starting setup for TC_VNF_STATE_INST_002')

        self.vnfm = Vnfm(vendor=self.tc_input['vnfm_params']['type'], **self.tc_input['vnfm_params']['client_config'])
        self.tc_result['overall_status'] = constants.TEST_PASSED
        self.tc_result['error_info'] = 'No errors'
        self.tc_result['resource_list'] = {}

        LOG.info('Finished setup for TC_VNF_STATE_INST_002')

        return True

    def run(self):
        LOG.info('Starting TC_VNF_STATE_INST_002')

        # --------------------------------------------------------------------------------------------------------------
        # 1. Instantiate VNF without load (--> time stamp)
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Instantiating VNF')
        self.time_record.START('instantiate_vnf')
        self.vnf_instance_id = self.vnfm.vnf_create_and_instantiate(
                                                                vnfd_id=self.tc_input['vnfd_id'], flavour_id=None,
                                                                vnf_instance_name=self.tc_input['vnf']['instance_name'],
                                                                vnf_instance_description=None)
        if self.vnf_instance_id is None:
            LOG.error('TC_VNF_STATE_INST_002 execution failed')
            LOG.debug('Unexpected VNF instantiation ID')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF instantiation operation failed'
            return False

        self.register_for_cleanup(self.vnfm.vnf_terminate_and_delete, vnf_instance_id=self.vnf_instance_id,
                                  termination_type='graceful')

        # --------------------------------------------------------------------------------------------------------------
        # 2. Validate VNFM reports the state INSTANTIATED (--> time stamp when correct state reached)
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF state is INSTANTIATED')
        vnf_info = self.vnfm.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id})
        if vnf_info.instantiation_state != constants.VNF_INSTANTIATED:
            LOG.error('TC_VNF_STATE_INST_002 execution failed')
            LOG.debug('Unexpected VNF state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF was not in "%s" state after instantiation' % constants.VNF_INSTANTIATED
            return False

        self.time_record.END('instantiate_vnf')

        # --------------------------------------------------------------------------------------------------------------
        # 3. Validate the right vResources have been allocated
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating the right vResources have been allocated')
        if not self.vnfm.validate_allocated_vresources(self.tc_input['vnfd_id'], self.vnf_instance_id):
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Could not validate allocated vResources')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'Could not validate allocated vResources'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 4. Calculate the instantiation time
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Calculating the time to stop a max scaled VNF under load')
        self.tc_result['durations']['instantiate_vnf'] = self.time_record.duration('instantiate_vnf')

        LOG.info('TC_VNF_STATE_INST_002 execution completed successfully')

        return True
