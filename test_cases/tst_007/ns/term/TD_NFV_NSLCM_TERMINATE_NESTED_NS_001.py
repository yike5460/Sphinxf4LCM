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
from time import sleep

from api.generic import constants
from test_cases import TestCase, TestRunError, Step
from utils.misc import generate_name
from utils.net import ping

# Instantiate logger
LOG = logging.getLogger(__name__)


class TD_NFV_NSLCM_TERMINATE_NESTED_NS_001(TestCase):
    """
    TD_NFV_NSLCM_TERMINATE_NESTED_NS_001 Verify that a NS referencing an existing nested NS can be successfully
    terminated

    Sequence:
    1. Trigger nested NS instantiation on the NFVO
    2. Verify that the NFVO indicates nested NS instantiation operation result as successful
    3. Trigger nesting NS instantiation on the NFVO
    4. Verify that the NFVO indicates nesting NS instantiation operation result as successful
    5. Trigger nesting NS instance termination on the NFVO
    6. Verify that the resources that were allocated to the VNF instance(s) inside the nesting NS have been released by
       the VIM
    7. Verify that VNF instance(s) inside the nested NS are still running and reachable through the management network
    8. Verify that all VNF instance(s) in the nesting NS have been terminated by querying the VNFM
    9. Verify that the NFVO indicates the nesting NS instance termination operation result as successful
    10. Verify that the nested NS instance was unaffected by the nesting NS instance termination by running an
        end-to-end functional test factoring in the functionality of VNF instance(s) in nested NS
    11. Trigger nested NS instance termination on the NFVO
    12. Verify that the nested NS is terminated and that all resources have been released by the VIM
    """

    REQUIRED_APIS = ('mano', 'traffic')
    REQUIRED_ELEMENTS = ('nested_ns_params', 'nsd_id')
    TESTCASE_EVENTS = ('instantiate_ns', 'terminate_ns')

    @Step(name='Instantiate the nested NS', description='Trigger nested NS instantiation on the NFVO')
    def step1(self):
        LOG.info('Starting %s' % self.tc_name)

        self.nested_ns_params = self.tc_input['nested_ns_params']
        # --------------------------------------------------------------------------------------------------------------
        # 1. Trigger nested NS instantiation on the NFVO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering nested NS instantiation on the NFVO')
        self.ns_instance_id_nested, operation_status = self.mano.ns_create_and_instantiate(
            nsd_id=self.nested_ns_params['nsd_id'], ns_name=generate_name(self.tc_name),
            ns_description=self.nested_ns_params.get('ns_description'),
            flavour_id=self.nested_ns_params.get('flavour_id'), sap_data=self.nested_ns_params.get('sap_data'),
            pnf_info=self.nested_ns_params.get('pnf_info'),
            vnf_instance_data=self.nested_ns_params.get('vnf_instance_data'),
            nested_ns_instance_data=self.nested_ns_params.get('nested_ns_instance_data'),
            location_constraints=self.nested_ns_params.get('location_constraints'),
            additional_param_for_ns=self.nested_ns_params.get('instantiation_params_for_ns'),
            additional_param_for_vnf=self.nested_ns_params.get('instantiation_params_for_vnf'),
            start_time=self.nested_ns_params.get('start_time'),
            ns_instantiation_level_id=self.nested_ns_params.get('ns_instantiation_level_id'),
            additional_affinity_or_anti_affinity_rule=self.nested_ns_params.get(
                'additional_affinity_or_anti_affinity_rule'))

        self.register_for_cleanup(index=10, function_reference=self.mano.ns_terminate_and_delete, verify_result=True,
                                  expected_result=constants.OPERATION_SUCCESS,
                                  ns_instance_id=self.ns_instance_id_nested,
                                  terminate_time=self.nested_ns_params.get('terminate_time'),
                                  additional_param=self.nested_ns_params.get('termination_params'))
        self.register_for_cleanup(index=20, function_reference=self.mano.wait_for_ns_stable_state,
                                  ns_instance_id=self.ns_instance_id_nested)

        if operation_status != constants.OPERATION_SUCCESS:
            raise TestRunError('Nested NS instantiation operation failed')

        LOG.debug('Sleeping %s seconds to allow the VDUs to complete first boot' % constants.INSTANCE_FIRST_BOOT_TIME)
        sleep(constants.INSTANCE_FIRST_BOOT_TIME)

    @Step(name='Verify nested NS instantiation was successful',
          description='Verify that the NFVO indicates nested NS instantiation operation result as successful')
    def step2(self):
        # --------------------------------------------------------------------------------------------------------------
        # 2. Verify that the NFVO indicates nested NS instantiation operation result as successful
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NFVO indicates nested NS instantiation operation result as successful')
        self.ns_info_nested_after_instantiation = self.mano.ns_query(
            filter={'ns_instance_id': self.ns_instance_id_nested,
                    'additional_param': self.nested_ns_params.get('query_params')})
        if self.ns_info_nested_after_instantiation.ns_state != constants.NS_INSTANTIATED:
            raise TestRunError('Unexpected NS instantiation state',
                               err_details='Nested NS instantiation state was not "%s" after the NS was instantiated'
                                           % constants.NS_INSTANTIATED)

    @Step(name='Instantiate the nesting NS', description='Trigger nesting NS instantiation on the NFVO')
    def step3(self):
        # --------------------------------------------------------------------------------------------------------------
        # 3. Trigger nesting NS instantiation on the NFVO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering nesting NS instantiation on the NFVO')
        self.time_record.START('instantiate_ns')
        self.ns_instance_id_nesting, operation_status = self.mano.ns_create_and_instantiate(
            nsd_id=self.tc_input['nsd_id'], ns_name=generate_name(self.tc_name),
            ns_description=self.tc_input.get('ns_description'), flavour_id=self.tc_input.get('flavour_id'),
            sap_data=self.tc_input['mano'].get('sap_data'), pnf_info=self.tc_input.get('pnf_info'),
            vnf_instance_data=self.tc_input.get('vnf_instance_data'),
            nested_ns_instance_data=[self.ns_instance_id_nested],
            location_constraints=self.tc_input.get('location_constraints'),
            additional_param_for_ns=self.tc_input['mano'].get('instantiation_params_for_ns'),
            additional_param_for_vnf=self.tc_input['mano'].get('instantiation_params_for_vnf'),
            start_time=self.tc_input.get('start_time'),
            ns_instantiation_level_id=self.tc_input.get('ns_instantiation_level_id'),
            additional_affinity_or_anti_affinity_rule=self.tc_input.get('additional_affinity_or_anti_affinity_rule'))

        self.register_for_cleanup(index=30, function_reference=self.mano.ns_terminate_and_delete, verify_result=True,
                                  expected_result=constants.OPERATION_SUCCESS,
                                  ns_instance_id=self.ns_instance_id_nesting,
                                  terminate_time=self.tc_input.get('terminate_time'),
                                  additional_param=self.tc_input['mano'].get('termination_params'))
        self.register_for_cleanup(index=40, function_reference=self.mano.wait_for_ns_stable_state,
                                  ns_instance_id=self.ns_instance_id_nesting)

        if operation_status != constants.OPERATION_SUCCESS:
            self.tc_result['events']['instantiate_ns']['details'] = 'Fail'
            raise TestRunError('Nesting NS instantiation operation failed')

        self.time_record.END('instantiate_ns')

        self.tc_result['events']['instantiate_ns']['duration'] = self.time_record.duration('instantiate_ns')
        self.tc_result['events']['instantiate_ns']['details'] = 'Success'

        LOG.debug('Sleeping %s seconds to allow the VDUs to complete first boot' % constants.INSTANCE_FIRST_BOOT_TIME)
        sleep(constants.INSTANCE_FIRST_BOOT_TIME)

    @Step(name='Verify nesting NS instantiation was successful',
          description='Verify that the NFVO indicates nesting NS instantiation operation result as successful')
    def step4(self):
        # --------------------------------------------------------------------------------------------------------------
        # 4. Verify that the NFVO indicates nesting NS instantiation operation result as successful
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NFVO indicates nesting NS instantiation operation result as successful')
        self.ns_info_nesting_after_instantiation = self.mano.ns_query(
            filter={'ns_instance_id': self.ns_instance_id_nesting,
                    'additional_param': self.tc_input['mano'].get('query_params')})
        if self.ns_info_nesting_after_instantiation.ns_state != constants.NS_INSTANTIATED:
            raise TestRunError('Unexpected NS instantiation state',
                               err_details='Nesting NS instantiation state was not "%s" after the NS was instantiated'
                                           % constants.NS_INSTANTIATED)

        for vnf_info in self.ns_info_nesting_after_instantiation.vnf_info:
            self.tc_result['resources']['%s (After instantiation)' % vnf_info.vnf_product_name] = {}
            self.tc_result['resources']['%s (After instantiation)' % vnf_info.vnf_product_name].update(
                self.mano.get_allocated_vresources(vnf_info.vnf_instance_id, self.tc_input['mano'].get('query_params')))

    @Step(name='Terminate the nesting NS', description='Trigger nesting NS instance termination on the NFVO')
    def step5(self):
        # --------------------------------------------------------------------------------------------------------------
        # 5. Trigger nesting NS instance termination on the NFVO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering nesting NS instance termination on the NFVO')
        self.time_record.START('terminate_ns')
        if self.mano.ns_terminate_sync(ns_instance_id=self.ns_instance_id_nesting,
                                       terminate_time=self.tc_input.get('terminate_time'),
                                       additional_param=self.tc_input['mano'].get('termination_params')) != \
                constants.OPERATION_SUCCESS:
            self.tc_result['events']['terminate_ns']['details'] = 'Fail'
            raise TestRunError('Unexpected status for NS termination operation',
                               err_details='Nesting NS termination operation failed')

        self.time_record.END('terminate_ns')

        self.tc_result['events']['terminate_ns']['duration'] = self.time_record.duration('terminate_ns')
        self.tc_result['events']['terminate_ns']['details'] = 'Success'

        self.unregister_from_cleanup(index=40)
        self.unregister_from_cleanup(index=30)

        self.register_for_cleanup(index=30, function_reference=self.mano.ns_delete_id,
                                  ns_instance_id=self.ns_instance_id_nesting)

    @Step(name='Verify nesting NS allocated resources have been released',
          description='Verify that the resources that were allocated to the VNF instance(s) inside the nesting NS have '
                      'been released by the VIM')
    def step6(self):
        # --------------------------------------------------------------------------------------------------------------
        # 6. Verify that the resources that were allocated to the VNF instance(s) inside the nesting NS have been
        #    released by the VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the resources that were allocated to the VNF instance(s) inside the nesting NS have '
                 'been released by the VIM')
        for vnf_info in self.ns_info_nesting_after_instantiation.vnf_info:
            vnf_instance_id = vnf_info.vnf_instance_id
            vnf_info = self.mano.vnf_query(query_filter={'vnf_instance_id': vnf_instance_id,
                                                         'additional_param': self.tc_input['mano'].get('query_params')})
            if vnf_info.instantiation_state != constants.VNF_NOT_INSTANTIATED:
                raise TestRunError(
                    'Nesting NS VNF instance %s was not terminated correctly. Expected state was %s but got %s'
                    % (vnf_instance_id, constants.VNF_NOT_INSTANTIATED, vnf_info.instantiation_state))

    @Step(name='Verify nested NS VNF instance(s) are reachable through the management network',
          description='Verify that VNF instance(s) inside the nested NS are still running and reachable through the '
                      'management network')
    def step7(self):
        # --------------------------------------------------------------------------------------------------------------
        # 7. Verify that VNF instance(s) inside the nested NS are still running and reachable through the management
        #    network
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that VNF instance(s) inside the nested NS are still running and reachable through the '
                 'management network')
        for vnf_info in self.ns_info_nested_after_instantiation.vnf_info:
            mgmt_addr_list = self.mano.get_vnf_mgmt_addr_list(vnf_info.vnf_instance_id,
                                                              self.nested_ns_params.get('query_params'))
            for mgmt_addr in mgmt_addr_list:
                if not ping(mgmt_addr):
                    raise TestRunError('Unable to PING IP address %s belonging to nested NS VNF %s'
                                       % (mgmt_addr, vnf_info.vnf_product_name))

    @Step(name='Verify nesting NS VNF instance(s) have been terminated',
          description='Verify that all VNF instance(s) in the nesting NS have been terminated by querying the VNFM')
    def step8(self):
        # --------------------------------------------------------------------------------------------------------------
        # 8. Verify that all VNF instance(s) in the nesting NS have been terminated by querying the VNFM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that all VNF instance(s) in nesting NS have been terminated by querying the VNFM')
        if not self.mano.validate_ns_released_vresources(self.ns_info_nesting_after_instantiation):
            raise TestRunError('Nesting NS allocated resources have not been released by the VIM')

    @Step(name='Verify nesting NS termination was successful',
          description='Verify that the NFVO indicates the nesting NS instance termination operation result as '
                      'successful')
    def step9(self):
        # --------------------------------------------------------------------------------------------------------------
        # 9. Verify that the NFVO indicates the nesting NS instance termination operation result as successful
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NFVO indicates the nesting NS instance termination operation result as successful')
        ns_info_nesting_after_termination = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id_nesting,
                                                                       'additional_param': self.tc_input['mano'].get(
                                                                           'query_params')})
        if ns_info_nesting_after_termination.ns_state != constants.NS_NOT_INSTANTIATED:
            raise TestRunError('Unexpected NS instantiation state',
                               err_details='Nesting NS instantiation state was not "%s" after the NS was terminated'
                                           % constants.NS_NOT_INSTANTIATED)

    @Step(name='Verify traffic flows',
          description='Verify that the nested NS instance was unaffected by the nesting NS instance termination by '
                      'running an end-to-end functional test factoring in the functionality of VNF instance(s) in the '
                      'nested NS')
    def step10(self):
        # --------------------------------------------------------------------------------------------------------------
        # 10. Verify that the nested NS instance was unaffected by the nesting NS instance termination by running an
        #     end-to-end functional test factoring in the functionality of VNF instance(s) in the nested NS
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the nested NS instance was unaffected by the nesting NS instance termination by '
                 'running an end-to-end functional test factoring in the functionality of VNF instance(s) in the nested'
                 ' NS')
        resolved_traffic_config = self.mano.resolve_ns_cp_addr(self.ns_info_nested_after_instantiation,
                                                               data=self.tc_input['traffic']['traffic_config'])
        self.traffic.configure(traffic_load='NORMAL_TRAFFIC_LOAD', traffic_config=resolved_traffic_config)

        self.register_for_cleanup(index=40, function_reference=self.traffic.destroy)

        # Configure stream destination address(es)
        dest_addr_list = self.mano.get_ns_ingress_cp_addr_list(
                                                          self.ns_info_nested_after_instantiation,
                                                          self.tc_input['traffic']['traffic_config']['ingress_cp_name'])
        self.traffic.reconfig_traffic_dest(dest_addr_list)

        self.traffic.start(return_when_emission_starts=True)

        self.register_for_cleanup(index=50, function_reference=self.traffic.stop)

        if not self.traffic.does_traffic_flow(delay_time=constants.TRAFFIC_STABILIZATION_TIME):
            raise TestRunError('Traffic is not flowing', err_details='Normal traffic did not flow')

        if self.traffic.any_traffic_loss(tolerance=constants.TRAFFIC_TOLERANCE):
            raise TestRunError('Traffic is flowing with packet loss',
                               err_details='Normal traffic flew with packet loss')

        self.traffic.stop()
        self.unregister_from_cleanup(index=50)

    @Step(name='Terminate the nested NS', description='Trigger nested NS instance termination on the NFVO')
    def step11(self):
        # --------------------------------------------------------------------------------------------------------------
        # 11. Trigger nested NS instance termination on the NFVO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering nested NS instance termination on the NFVO')
        if self.mano.ns_terminate_sync(ns_instance_id=self.ns_instance_id_nested,
                                       terminate_time=self.nested_ns_params.get('terminate_time'),
                                       additional_param=self.nested_ns_params.get('termination_params')) != \
                constants.OPERATION_SUCCESS:
            raise TestRunError('Unexpected status for NS termination operation',
                               err_details='Nested NS termination operation failed')

        self.unregister_from_cleanup(index=20)
        self.unregister_from_cleanup(index=10)

        self.register_for_cleanup(index=10, function_reference=self.mano.ns_delete_id,
                                  ns_instance_id=self.ns_instance_id_nested)

    @Step(name='Verify nested NS is terminated',
          description='Verify that the nested NS is terminated and that all resources have been released by the VIM')
    def step12(self):
        # --------------------------------------------------------------------------------------------------------------
        # 12. Verify that the nested NS is terminated and that all resources have been released by the VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the nested NS is terminated')
        ns_info_nested_after_termination = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id_nested,
                                                                      'additional_param': self.nested_ns_params.get(
                                                                          'query_params')})
        if ns_info_nested_after_termination.ns_state != constants.NS_NOT_INSTANTIATED:
            raise TestRunError('Unexpected NS instantiation state',
                               err_details='Nested NS instantiation state was not "%s" after the NS was terminated'
                                           % constants.NS_NOT_INSTANTIATED)

        LOG.info('Verifying that all nested NS VNF instance(s) have been terminated')
        for vnf_info in self.ns_info_nested_after_instantiation.vnf_info:
            vnf_instance_id = vnf_info.vnf_instance_id
            vnf_info = self.mano.vnf_query(query_filter={'vnf_instance_id': vnf_instance_id,
                                                         'additional_param': self.nested_ns_params.get('query_params')})
            if vnf_info.instantiation_state != constants.VNF_NOT_INSTANTIATED:
                raise TestRunError(
                    'Nested NS VNF instance %s was not terminated correctly. Expected state was %s but got %s'
                    % (vnf_instance_id, constants.VNF_NOT_INSTANTIATED, vnf_info.instantiation_state))

        LOG.info('Verifying that all nested NS resources have been released by the VIM')
        if not self.mano.validate_ns_released_vresources(self.ns_info_nested_after_instantiation):
            raise TestRunError('Nested NS allocated resources have not been released by the VIM')

        LOG.info('%s execution completed successfully' % self.tc_name)
