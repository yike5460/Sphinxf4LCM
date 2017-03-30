import logging

from api.generic import constants
from api.generic.vnfm import Vnfm
from test_cases import TestCase

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNF_STATE_INST_007(TestCase):
    """
    TC_VNF_STATE_INST_007 VNF Instantiation Failure with missing required virtual resources

    Sequence:
    1. Instantiate the VNF
    2. Validate MANO reports no VNF instance and the error
    3. Validate VIM reports no VNF instance and the error
    """

    def setup(self):
        LOG.info('Starting setup for %s' % self.tc_name)

        # Create objects needed by the test.
        self.vnfm = Vnfm(vendor=self.tc_input['vnfm_params']['type'], **self.tc_input['vnfm_params']['client_config'])

        # Initialize test case result.
        self.tc_result['overall_status'] = constants.TEST_PASSED
        self.tc_result['error_info'] = 'No errors'
        self.tc_result['events']['instantiate_vnf'] = dict()

        LOG.info('Finished setup for %s' % self.tc_name)

        return True

    def run(self):
        LOG.info('Starting %s' % self.tc_name)

        # --------------------------------------------------------------------------------------------------------------
        # 1. Instantiate the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Instantiating the VNF')
        self.time_record.START('instantiate_vnf')
        self.vnf_instance_id = self.vnfm.vnf_create_id(vnfd_id=self.tc_input['vnfd_id'],
                                                       vnf_instance_name=self.tc_input['vnf']['instance_name'],
                                                       vnf_instance_description=None)
        if self.vnf_instance_id is None:
            LOG.error('%s execution failed' % self.tc_name)
            LOG.debug('Unexpected VNF instantiation ID')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF instantiation operation failed'
            return False

        if self.vnfm.vnf_instantiate_sync(vnf_instance_id=self.vnf_instance_id,
                                          flavour_id=None) != constants.OPERATION_FAILED:
            LOG.error('%s execution failed' % self.tc_name)
            LOG.debug('VNF instantiation operation succeeded')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = 'VNF instantiation operation succeeded'
            return False

        self.time_record.END('instantiate_vnf')

        self.tc_result['events']['instantiate_vnf']['duration'] = self.time_record.duration('instantiate_vnf')

        self.register_for_cleanup(self.vnfm.vnf_terminate_and_delete, vnf_instance_id=self.vnf_instance_id,
                                  termination_type='graceful')

        # --------------------------------------------------------------------------------------------------------------
        # 2. Validate MANO reports no VNF instance and the error
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating MANO reports no VNF instance and the error')
        vnf_info = self.vnfm.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id})
        if vnf_info.instantiation_state == constants.VNF_INSTANTIATED:
            LOG.error('%s execution failed' % self.tc_name)
            LOG.debug('Unexpected VNF instantiation state')
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result[
                'error_info'] = 'VNF instantiation state was "%s" although the instantiation operation failed' % \
                                constants.VNF_INSTANTIATED
            return False

        self.tc_result['events']['instantiate_vnf']['details'] = vnf_info.metadata['error_reason']

        # --------------------------------------------------------------------------------------------------------------
        # 3. Validate VIM reports no VNF instance and the error
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VIM reports no VNF instance and the error')
        # TODO

        LOG.info('%s execution completed successfully' % self.tc_name)

        return True


class TC_VNF_STATE_INST_007_001(TC_VNF_STATE_INST_007):
    """
    TC_VNF_STATE_INST_007_001 VNF Instantiation Failure with missing required virtual resources 'Incompatible vCPU type'

    Sequence:
    1. Instantiate the VNF
    2. Validate MANO reports no VNF instance and the error
    3. Validate VIM reports no VNF instance and the error

    """

class TC_VNF_STATE_INST_007_002(TC_VNF_STATE_INST_007):
    """
    TC_VNF_STATE_INST_007_002 VNF Instantiation Failure with missing required virtual resources 'Instructions sets'

    Sequence:
    1. Instantiate the VNF
    2. Validate MANO reports no VNF instance and the error
    3. Validate VIM reports no VNF instance and the error
    """


class TC_VNF_STATE_INST_007_003(TC_VNF_STATE_INST_007):
    """
    TC_VNF_STATE_INST_007_003 VNF Instantiation Failure with missing required virtual resources 'Specialized vNIC'

    Sequence:
    1. Instantiate the VNF
    2. Validate MANO reports no VNF instance and the error
    3. Validate VIM reports no VNF instance and the error
    """


class TC_VNF_STATE_INST_007_004(TC_VNF_STATE_INST_007):
    """
    TC_VNF_STATE_INST_007_004 VNF Instantiation Failure with missing required virtual resources 'Hardware Acceleration, 
                              e.g. DPDK, SRIOV'

    Sequence:
    1. Instantiate the VNF
    2. Validate MANO reports no VNF instance and the error
    3. Validate VIM reports no VNF instance and the error
    """


class TC_VNF_STATE_INST_007_005(TC_VNF_STATE_INST_007):
    """
    TC_VNF_STATE_INST_007_005 VNF Instantiation Failure with missing required virtual resources 'vMemory size'

    Sequence:
    1. Instantiate the VNF
    2. Validate MANO reports no VNF instance and the error
    3. Validate VIM reports no VNF instance and the error
    """


class TC_VNF_STATE_INST_007_006(TC_VNF_STATE_INST_007):
    """
    TC_VNF_STATE_INST_007_006 VNF Instantiation Failure with missing required virtual resources 'vStorage type'

    Sequence:
    1. Instantiate the VNF
    2. Validate MANO reports no VNF instance and the error
    3. Validate VIM reports no VNF instance and the error
    """


class TC_VNF_STATE_INST_007_007(TC_VNF_STATE_INST_007):
    """
    TC_VNF_STATE_INST_007_007 VNF Instantiation Failure with missing required virtual resources 'vStorage size'

    Sequence:
    1. Instantiate the VNF
    2. Validate MANO reports no VNF instance and the error
    3. Validate VIM reports no VNF instance and the error
    """


class TC_VNF_STATE_INST_007_008(TC_VNF_STATE_INST_007):
    """
    TC_VNF_STATE_INST_007_008 VNF Instantiation Failure with missing required virtual resources 'vCPU counts'

    Sequence:
    1. Instantiate the VNF
    2. Validate MANO reports no VNF instance and the error
    3. Validate VIM reports no VNF instance and the error
    """
