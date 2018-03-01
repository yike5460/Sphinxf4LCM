#
# Copyright (c) 2018 by Spirent Communications Plc.
# All Rights Reserved.
#
# This software is confidential and proprietary to Spirent Communications Inc.
# No part of this software may be reproduced, transmitted, disclosed or used
# in violation of the Software License Agreement without the expressed
# written consent of Spirent Communications Inc.
#
#


import logging

from api.generic import constants
from api.generic.mano import Mano
from api.generic.vim import Vim
from test_cases import TestCase, TestRunError
from utils.misc import generate_name

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNF_STATE_INST_007(TestCase):
    """
    TC_VNF_STATE_INST_007 VNF Instantiation Failure with missing required virtual resources

    Sequence:
    1. Instantiate the VNF
    2. Validate MANO reports no VNF instance and the error
    """

    REQUIRED_APIS = ('mano', 'vim')
    REQUIRED_ELEMENTS = ('vnfd_id',)
    TESTCASE_EVENTS = ('instantiate_vnf',)

    def run(self):
        LOG.info('Starting %s' % self.tc_name)

        # --------------------------------------------------------------------------------------------------------------
        # 1. Instantiate the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Instantiating the VNF')
        self.time_record.START('instantiate_vnf')
        self.vnf_instance_id = self.mano.vnf_create_id(
                                                 vnfd_id=self.tc_input['vnfd_id'],
                                                 vnf_instance_name=generate_name(self.tc_name),
                                                 vnf_instance_description=self.tc_input.get('vnf_instance_description'))

        if self.mano.vnf_instantiate_sync(vnf_instance_id=self.vnf_instance_id,
                                          flavour_id=self.tc_input.get('flavour_id'),
                                          instantiation_level_id=self.tc_input.get('instantiation_level_id'),
                                          ext_virtual_link=self.tc_input.get('ext_virtual_link'),
                                          ext_managed_virtual_link=self.tc_input.get('ext_managed_virtual_link'),
                                          localization_language=self.tc_input.get('localization_language'),
                                          additional_param=self.tc_input['mano'].get('instantiation_params')) \
                != constants.OPERATION_FAILED:
            raise TestRunError('VNF instantiation operation succeeded')

        self.time_record.END('instantiate_vnf')

        self.tc_result['events']['instantiate_vnf']['duration'] = self.time_record.duration('instantiate_vnf')

        self.register_for_cleanup(index=10, function_reference=self.mano.vnf_terminate_and_delete,
                                  vnf_instance_id=self.vnf_instance_id, termination_type='graceful',
                                  graceful_termination_timeout=self.tc_input.get('graceful_termination_timeout'),
                                  additional_param=self.tc_input['mano'].get('termination_params'))
        self.register_for_cleanup(index=20, function_reference=self.mano.wait_for_vnf_stable_state,
                                  vnf_instance_id=self.vnf_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 2. Validate MANO reports no VNF instance and the error
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating MANO reports no VNF instance and the error')
        vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id,
                                               'additional_param': self.tc_input['mano'].get('query_params')})
        if vnf_info.instantiation_state == constants.VNF_INSTANTIATED:
            raise TestRunError(
                             'Unexpected VNF instantiation state',
                              err_details='VNF instantiation state was "%s" although the instantiation operation failed'
                                          % constants.VNF_INSTANTIATED)

        self.tc_result['events']['instantiate_vnf']['details'] = vnf_info.metadata['error_reason']

        LOG.info('%s execution completed successfully' % self.tc_name)


class TC_VNF_STATE_INST_007_001(TC_VNF_STATE_INST_007):
    """
    TC_VNF_STATE_INST_007_001 VNF Instantiation Failure with missing required virtual resources 'Incompatible vCPU type'

    Sequence:
    1. Instantiate the VNF
    2. Validate MANO reports no VNF instance and the error

    """


class TC_VNF_STATE_INST_007_002(TC_VNF_STATE_INST_007):
    """
    TC_VNF_STATE_INST_007_002 VNF Instantiation Failure with missing required virtual resources 'Instructions sets'

    Sequence:
    1. Instantiate the VNF
    2. Validate MANO reports no VNF instance and the error
    """


class TC_VNF_STATE_INST_007_003(TC_VNF_STATE_INST_007):
    """
    TC_VNF_STATE_INST_007_003 VNF Instantiation Failure with missing required virtual resources 'Specialized vNIC'

    Sequence:
    1. Instantiate the VNF
    2. Validate MANO reports no VNF instance and the error
    """


class TC_VNF_STATE_INST_007_004(TC_VNF_STATE_INST_007):
    """
    TC_VNF_STATE_INST_007_004 VNF Instantiation Failure with missing required virtual resources 'Hardware Acceleration,
                              e.g. DPDK, SRIOV'

    Sequence:
    1. Instantiate the VNF
    2. Validate MANO reports no VNF instance and the error
    """


class TC_VNF_STATE_INST_007_005(TC_VNF_STATE_INST_007):
    """
    TC_VNF_STATE_INST_007_005 VNF Instantiation Failure with missing required virtual resources 'vMemory size'

    Sequence:
    1. Instantiate the VNF
    2. Validate MANO reports no VNF instance and the error
    """

    def setup(self):
        LOG.debug('Ensuring NFVI has not enough vMemory for the VNF to be instantiated')
        reservation_id = self.mano.limit_compute_resources_for_vnf_instantiation(
                                                           vnfd_id=self.tc_input['vnfd_id'],
                                                           generic_vim_object=self.vim, limit_vcpus=False,
                                                           limit_vc_instances=False,
                                                           scaling_policy_name=self.tc_input.get('scaling_policy_name'))

        if reservation_id is None:
            raise TestRunError('vMemory could not be limited')

        self.register_for_cleanup(index=30, function_reference=self.vim.terminate_compute_resource_reservation,
                                  reservation_id=reservation_id)


class TC_VNF_STATE_INST_007_006(TC_VNF_STATE_INST_007):
    """
    TC_VNF_STATE_INST_007_006 VNF Instantiation Failure with missing required virtual resources 'vStorage type'

    Sequence:
    1. Instantiate the VNF
    2. Validate MANO reports no VNF instance and the error
    """


class TC_VNF_STATE_INST_007_007(TC_VNF_STATE_INST_007):
    """
    TC_VNF_STATE_INST_007_007 VNF Instantiation Failure with missing required virtual resources 'vStorage size'

    Sequence:
    1. Instantiate the VNF
    2. Validate MANO reports no VNF instance and the error
    """

    def setup(self):
        LOG.debug('Ensuring NFVI has not enough vStorage for the VNF to be instantiated')
        reservation_id = self.mano.limit_storage_resources_for_vnf_instantiation(
                                                           vnfd_id=self.tc_input['vnfd_id'],
                                                           generic_vim_object=self.vim,
                                                           scaling_policy_name=self.tc_input.get('scaling_policy_name'))

        if reservation_id is None:
            raise TestRunError('vStorage could not be limited')

        self.register_for_cleanup(index=30, function_reference=self.vim.terminate_storage_resource_reservation,
                                  reservation_id=reservation_id)


class TC_VNF_STATE_INST_007_008(TC_VNF_STATE_INST_007):
    """
    TC_VNF_STATE_INST_007_008 VNF Instantiation Failure with missing required virtual resources 'vCPU counts'

    Sequence:
    1. Instantiate the VNF
    2. Validate MANO reports no VNF instance and the error
    """

    def setup(self):
        LOG.debug('Ensuring NFVI has not enough vCPUs for the VNF to be instantiated')
        reservation_id = self.mano.limit_compute_resources_for_vnf_instantiation(
                                                           vnfd_id=self.tc_input['vnfd_id'],
                                                           generic_vim_object=self.vim, limit_vmem=False,
                                                           limit_vc_instances=False,
                                                           scaling_policy_name=self.tc_input.get('scaling_policy_name'))

        if reservation_id is None:
            raise TestRunError('vCPU count could not be limited')

        self.register_for_cleanup(index=30, function_reference=self.vim.terminate_compute_resource_reservation,
                                  reservation_id=reservation_id)
