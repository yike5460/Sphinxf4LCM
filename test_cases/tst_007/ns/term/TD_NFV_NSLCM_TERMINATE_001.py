import logging
from time import sleep

from api.generic import constants
from test_cases import TestCase, TestRunError
from utils.misc import generate_name

# Instantiate logger
LOG = logging.getLogger(__name__)


class TD_NFV_NSLCM_TERMINATE_001(TestCase):
    """
    TD_NFV_NSLCM_TERMINATE_001 Terminate standalone NS

    Sequence:
    1. Trigger NS instantiation on the NFVO
    2. Verify that the NS is instantiated and started
    3. Trigger the termination of the NS instance on the NFVO
    4. Verify that all the VNF instance(s) have been terminated by querying the VNFM
    5. Verify that the resources allocated to the NS and VNF instance(s) have been released by the VIM
    6. Verify that the NFVO indicates NS instance operation termination operation result as successful
    """

    REQUIRED_APIS = ('mano',)
    REQUIRED_ELEMENTS = ('nsd_id',)
    TESTCASE_EVENTS = ('instantiate_ns', 'terminate_ns')

    def run(self):
        LOG.info('Starting %s' % self.tc_name)

        # --------------------------------------------------------------------------------------------------------------
        # 1. Trigger NS instantiation on the NFVO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering NS instantiation on the NFVO')
        self.time_record.START('instantiate_ns')
        self.ns_instance_id = self.mano.ns_create_and_instantiate(
               nsd_id=self.tc_input['nsd_id'], ns_name=generate_name(self.tc_name),
               ns_description=self.tc_input.get('ns_description'), flavour_id=self.tc_input.get('flavour_id'),
               sap_data=self.tc_input.get('sap_data'), pnf_info=self.tc_input.get('pnf_info'),
               vnf_instance_data=self.tc_input.get('vnf_instance_data'),
               nested_ns_instance_data=self.tc_input.get('nested_ns_instance_data'),
               location_constraints=self.tc_input.get('location_constraints'),
               additional_param_for_ns=self.tc_input.get('additional_param_for_ns'),
               additional_param_for_vnf=self.tc_input.get('additional_param_for_vnf'),
               start_time=self.tc_input.get('start_time'),
               ns_instantiation_level_id=self.tc_input.get('ns_instantiation_level_id'),
               additional_affinity_or_anti_affinity_rule=self.tc_input.get('additional_affinity_or_anti_affinity_rule'))

        if self.ns_instance_id is None:
            raise TestRunError('NS instantiation operation failed')

        self.time_record.END('instantiate_ns')

        self.tc_result['events']['instantiate_ns']['duration'] = self.time_record.duration('instantiate_ns')

        self.register_for_cleanup(index=10, function_reference=self.mano.ns_terminate_and_delete,
                                  ns_instance_id=self.ns_instance_id,
                                  terminate_time=self.tc_input.get('terminate_time'))
        self.register_for_cleanup(index=20, function_reference=self.mano.wait_for_ns_stable_state,
                                  ns_instance_id=self.ns_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 2. Verify that the NS is instantiated
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating NS instantiation state is INSTANTIATED')
        ns_info = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id,
                                             'additional_param': self.tc_input['mano'].get('query_params')})
        if ns_info.ns_state != constants.NS_INSTANTIATED:
            raise TestRunError('Unexpected NS instantiation state',
                               err_details='NS instantiation state was not "%s" after the NS was instantiated'
                                           % constants.NS_INSTANTIATED)

        # --------------------------------------------------------------------------------------------------------------
        # 3. Trigger the termination of the NS instance on the NFVO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering the termination of the NS instance on the NFVO')
        self.time_record.START('terminate_ns')
        if self.mano.ns_terminate_sync(ns_instance_id=self.ns_instance_id) != constants.OPERATION_SUCCESS:
            raise TestRunError('Unexpected status for NS termination operation',
                               err_details='NS termination operation failed')

        self.time_record.END('terminate_ns')

        self.tc_result['events']['terminate_ns']['duration'] = self.time_record.duration('terminate_ns')

        self.unregister_from_cleanup(index=20)
        self.unregister_from_cleanup(index=10)

        # --------------------------------------------------------------------------------------------------------------
        # 4. Verify that all the VNF instance(s) have been terminated by querying the VNFM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Sleeping 5 seconds to allow MANO to finalize termination of resources')
        sleep(5)
        LOG.info('Verifying that all the VNF instance(s) have been terminated')
        for vnf_info in ns_info.vnf_info:
            vnf_instance_id = vnf_info.vnf_instance_id
            vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': vnf_instance_id,
                                                   'additional_param': self.tc_input['mano'].get('query_params')})
            if vnf_info.instantiation_state != constants.VNF_NOT_INSTANTIATED:
                raise TestRunError(
                    'VNF instance was not terminated correctly. VNF instance ID %s expected state was %s but got %s'
                    % (vnf_instance_id, constants.VNF_NOT_INSTANTIATED, vnf_info.instantiation_state))

        # --------------------------------------------------------------------------------------------------------------
        # 5. Verify that the resources allocated to the NS and VNF instance(s) have been released by the VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the resources allocated to the NS and VNF instance(s) have been released by the VIM')
        if not self.mano.validate_ns_released_vresources(ns_info):
            raise TestRunError('NS resources have not been released by the VIM')

        # --------------------------------------------------------------------------------------------------------------
        # 6. Verify that the NFVO indicates NS instance operation termination operation result as successful
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NFVO indicates NS instance operation termination operation result as successful')
        ns_info = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id,
                                             'additional_param': self.tc_input['mano'].get('query_params')})
        if ns_info.ns_state != constants.NS_NOT_INSTANTIATED:
            raise TestRunError(
                'NS instance was not terminated correctly. NS instance ID %s expected state was %s, but got %s'
                % (self.ns_instance_id, constants.NS_NOT_INSTANTIATED, ns_info.ns_state))
