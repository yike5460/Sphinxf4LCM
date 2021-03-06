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
from api.structures.objects import ScaleVnfData, ScaleToLevelData
from test_cases import TestCase, TestRunError, Step
from utils.misc import generate_name
from utils.net import ping

# Instantiate logger
LOG = logging.getLogger(__name__)


class TD_NFV_NSLCM_SCALE_TO_LEVEL_VNF_001(TestCase):
    """
    TD_NFV_NSLCM_SCALE_TO_LEVEL_VNF_001 Verify that a VNF in a NS can be successfully scaled to an instantiation level
    when triggered by a NFVO operator

    Sequence:
    1. Trigger NS instantiation on the NFVO
    2. Verify that the NFVO indicates NS instantiation operation result as successful
    3. Trigger NS scale by scaling to another existing instantiation level a VNF in the NS in NFVO with an operator
       action
    4. Verify that the number of VNFC instance(s) has changed for the VNF by querying the VNFM
    5. Verify that the resources allocated by the VIM have changed according to the descriptors
    6. Verify that all VNFC instance(s) are running and reachable via the management network
    7. Verify that the VNF configuration has been updated according to the descriptors by querying the VNFM
    8. Verify that all VNFC instance(s) are connected to the VL(s) according to the descriptors
    9. Verify that the NFVO indicates the scaling operation result as successful
    10. Verify that NS has been scaled by running the end-to-end functional test in relevance to the VNF scale and
        capacity
    11. Trigger the termination of the NS instance on the NFVO
    12. Verify that the NS is terminated and that all resources have been released by the VIM
    """

    REQUIRED_APIS = ('mano', 'traffic')
    REQUIRED_ELEMENTS = ('nsd_id', 'scale_to_level_list')
    TESTCASE_EVENTS = ('instantiate_ns', 'scale_to_level_ns', 'terminate_ns')

    @Step(name='Instantiate the NS', description='Trigger NS instantiation on the NFVO')
    def step1(self):
        LOG.info('Starting %s' % self.tc_name)

        # --------------------------------------------------------------------------------------------------------------
        # 1. Trigger NS instantiation on the NFVO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering NS instantiation on the NFVO')
        self.time_record.START('instantiate_ns')
        self.ns_instance_id, operation_status = self.mano.ns_create_and_instantiate(
               nsd_id=self.tc_input['nsd_id'], ns_name=generate_name(self.tc_name),
               ns_description=self.tc_input.get('ns_description'), flavour_id=self.tc_input.get('flavour_id'),
               sap_data=self.tc_input['mano'].get('sap_data'), pnf_info=self.tc_input.get('pnf_info'),
               vnf_instance_data=self.tc_input.get('vnf_instance_data'),
               nested_ns_instance_data=self.tc_input.get('nested_ns_instance_data'),
               location_constraints=self.tc_input.get('location_constraints'),
               additional_param_for_ns=self.tc_input['mano'].get('instantiation_params_for_ns'),
               additional_param_for_vnf=self.tc_input['mano'].get('instantiation_params_for_vnf'),
               start_time=self.tc_input.get('start_time'),
               ns_instantiation_level_id=self.tc_input.get('ns_instantiation_level_id'),
               additional_affinity_or_anti_affinity_rule=self.tc_input.get('additional_affinity_or_anti_affinity_rule'))

        self.register_for_cleanup(index=10, function_reference=self.mano.ns_terminate_and_delete, verify_result=True,
                                  expected_result=constants.OPERATION_SUCCESS, ns_instance_id=self.ns_instance_id,
                                  terminate_time=self.tc_input.get('terminate_time'),
                                  additional_param=self.tc_input['mano'].get('termination_params'))
        self.register_for_cleanup(index=20, function_reference=self.mano.wait_for_ns_stable_state,
                                  ns_instance_id=self.ns_instance_id)

        if operation_status != constants.OPERATION_SUCCESS:
            self.tc_result['events']['instantiate_ns']['details'] = 'Fail'
            raise TestRunError('NS instantiation operation failed')

        self.time_record.END('instantiate_ns')

        self.tc_result['events']['instantiate_ns']['duration'] = self.time_record.duration('instantiate_ns')
        self.tc_result['events']['instantiate_ns']['details'] = 'Success'

        LOG.debug('Sleeping %s seconds to allow the VDUs to complete first boot' % constants.INSTANCE_FIRST_BOOT_TIME)
        sleep(constants.INSTANCE_FIRST_BOOT_TIME)

    @Step(name='Verify NS instantiation was successful',
          description='Verify that the NFVO indicates NS instantiation operation result as successful')
    def step2(self):
        # --------------------------------------------------------------------------------------------------------------
        # 2. Verify that the NFVO indicates NS instantiation operation result as successful
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NFVO indicates NS instantiation operation result as successful')
        self.ns_info_before_scale_to_level = self.mano.ns_query(query_filter={'ns_instance_id': self.ns_instance_id,
                                                                              'additional_param': self.tc_input[
                                                                                  'mano'].get('query_params')})
        if self.ns_info_before_scale_to_level.ns_state != constants.NS_INSTANTIATED:
            raise TestRunError('Unexpected NS state',
                               err_details='NS state was not "%s" after the NS was instantiated'
                                           % constants.NS_INSTANTIATED)

        for vnf_info in self.ns_info_before_scale_to_level.vnf_info:
            self.tc_result['resources']['%s (Before scale to level)' % vnf_info.vnf_product_name] = {}
            self.tc_result['resources']['%s (Before scale to level)' % vnf_info.vnf_product_name].update(
                self.mano.get_allocated_vresources(vnf_info.vnf_instance_id, self.tc_input['mano'].get('query_params')))

    @Step(name='Scale the NS to a new level',
          description='Trigger NS scale by scaling to another existing instantiation level a VNF in the NS in NFVO with'
                      ' an operator action')
    def step3(self):
        # --------------------------------------------------------------------------------------------------------------
        # 3. Trigger NS scale by scaling to another existing instantiation level a VNF in the NS in NFVO with an
        #    operator action
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering NS scale by scaling to another existing instantiation level a VNF in the NS in NFVO with '
                 'an operator action')
        scale_vnf_data_list = []
        for scale_to_level in self.tc_input['scale_to_level_list']:
            vnf_name = scale_to_level['target_vnf_name']
            instantiation_level_id = scale_to_level['target_instantiation_level_id']
            # Build the ScaleVnfData information element
            scale_vnf_data = ScaleVnfData()
            scale_vnf_data.vnf_instance_id = self.mano.get_vnf_instance_id_from_ns_vnf_name(
                self.ns_info_before_scale_to_level, vnf_name)
            scale_vnf_data.type = 'to_instantiation_level'
            scale_vnf_data.scale_to_level_data = ScaleToLevelData()
            scale_vnf_data.scale_to_level_data.instantiation_level_id = str(instantiation_level_id)
            scale_vnf_data.scale_to_level_data.additional_param = self.tc_input['mano'].get('scale_params')

            scale_vnf_data_list.append(scale_vnf_data)

        self.time_record.START('scale_to_level_ns')
        if self.mano.ns_scale_sync(self.ns_instance_id, scale_type='SCALE_VNF', scale_vnf_data=scale_vnf_data_list,
                                   scale_time=self.tc_input.get('scale_time')) \
                != constants.OPERATION_SUCCESS:
            self.tc_result['scaling_to_level']['status'] = 'Fail'
            self.tc_result['events']['scale_to_level_ns']['details'] = 'Fail'
            raise TestRunError('MANO could not scale to level the NS')

        self.time_record.END('scale_to_level_ns')

        self.tc_result['events']['scale_to_level_ns']['duration'] = self.time_record.duration('scale_to_level_ns')
        self.tc_result['events']['scale_to_level_ns']['details'] = 'Success'

        LOG.debug('Sleeping %s seconds to allow the VDUs to complete first boot' % constants.INSTANCE_FIRST_BOOT_TIME)
        sleep(constants.INSTANCE_FIRST_BOOT_TIME)

    @Step(name='Verify NS has scaled',
          description='Verify that the number of VNFC instance(s) has changed for the VNF by querying the VNFM')
    def step4(self):
        # --------------------------------------------------------------------------------------------------------------
        # 4. Verify that the number of VNFC instance(s) has changed for the VNF by querying the VNFM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the number of VNFC instance(s) has changed for the VNF by querying the VNFM')
        self.ns_info_after_scale_to_level = self.mano.ns_query(query_filter={'ns_instance_id': self.ns_instance_id,
                                                                             'additional_param': self.tc_input[
                                                                                 'mano'].get('query_params')})
        if not self.mano.validate_ns_instantiation_level(self.ns_info_after_scale_to_level,
                                                         self.tc_input['scale_to_level_list'],
                                                         self.tc_input['mano'].get('scale_params')):
            raise TestRunError('Incorrect number of VNFCs')

        for vnf_info in self.ns_info_after_scale_to_level.vnf_info:
            self.tc_result['resources']['%s (After scale to level)' % vnf_info.vnf_product_name] = {}
            self.tc_result['resources']['%s (After scale to level)' % vnf_info.vnf_product_name].update(
                self.mano.get_allocated_vresources(vnf_info.vnf_instance_id, self.tc_input['mano'].get('query_params')))

        # TODO Add self.tc_result['scaling_to_level']['level']. We should do this only for the VNF(s) that we scaled

        self.tc_result['scaling_to_level']['status'] = 'Success'

    @Step(name='Verify allocated resources',
          description='Verify that the resources allocated by the VIM have changed according to the descriptors')
    def step5(self):
        # --------------------------------------------------------------------------------------------------------------
        # 5. Verify that the resources allocated by the VIM have changed according to the descriptors
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the resources allocated by the VIM have changed according to the descriptors')
        if not self.mano.validate_ns_allocated_vresources(self.ns_instance_id,
                                                          self.tc_input['mano'].get('query_params')):
            raise TestRunError('Allocated vResources could not be validated')

    @Step(name='Verify VNFC instance(s) are reachable via the management network',
          description='Verify that all VNFC instance(s) are running and reachable via the management network')
    def step6(self):
        # --------------------------------------------------------------------------------------------------------------
        # 6. Verify that all VNFC instance(s) are running and reachable via the management network
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that all VNFC instance(s) are running and reachable via the management network')
        for vnf_info in self.ns_info_after_scale_to_level.vnf_info:
            mgmt_addr_list = self.mano.get_vnf_mgmt_addr_list(vnf_info.vnf_instance_id,
                                                              self.tc_input['mano'].get('query_params'))
            for mgmt_addr in mgmt_addr_list:
                if not ping(mgmt_addr):
                    raise TestRunError('Unable to PING IP address %s belonging to VNF %s'
                                       % (mgmt_addr, vnf_info.vnf_product_name))

    @Step(name='Verify VNF configuration',
          description='Verify that the VNF configuration has been updated according to the descriptors by querying the '
                      'VNFM',
          runnable=False)
    def step7(self):
        # --------------------------------------------------------------------------------------------------------------
        # 7. Verify that the VNF configuration has been updated according to the descriptors by querying the VNFM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the VNF configuration has been updated according to the descriptors by querying the '
                 'VNFM')
        # TODO

    @Step(name='Verify VNFC instance(s) connection(s)',
          description='Verify that all VNFC instance(s) are connected to the VL(s) according to the descriptors',
          runnable=False)
    def step8(self):
        # --------------------------------------------------------------------------------------------------------------
        # 8. Verify that all VNFC instance(s) are connected to the VL(s) according to the descriptors
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that all VNFC instance(s) are connected to the VL(s) according to the descriptors')
        # TODO

    @Step(name='Verify NS scale to level was successful',
          description='Verify that the NFVO indicates the scaling operation result as successful')
    def step9(self):
        # --------------------------------------------------------------------------------------------------------------
        # 9. Verify that the NFVO indicates the scaling operation result as successful
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NFVO indicates the scaling operation result as successful')
        LOG.debug('This has implicitly been checked at step 3')

    @Step(name='Verify traffic flows',
          description='Verify that NS has been scaled by running the end-to-end functional test in relevance to the VNF'
                      ' scale and capacity')
    def step10(self):
        # --------------------------------------------------------------------------------------------------------------
        # 10. Verify that NS has been scaled by running the end-to-end functional test in relevance to the VNF scale and
        #     capacity
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that NS has been scaled by running the end-to-end functional test in relevance to the VNF '
                 'scale and capacity')
        resolved_traffic_config = self.mano.resolve_ns_cp_addr(self.ns_info_after_scale_to_level,
                                                               data=self.tc_input['traffic']['traffic_config'])
        self.traffic.configure(traffic_load='NORMAL_TRAFFIC_LOAD', traffic_config=resolved_traffic_config)

        self.register_for_cleanup(index=30, function_reference=self.traffic.destroy)

        # Configure stream destination address(es)
        dest_addr_list = self.mano.get_ns_ingress_cp_addr_list(
                                                          self.ns_info_after_scale_to_level,
                                                          self.tc_input['traffic']['traffic_config']['ingress_cp_name'])
        self.traffic.reconfig_traffic_dest(dest_addr_list)

        self.traffic.start(return_when_emission_starts=True)

        self.register_for_cleanup(index=40, function_reference=self.traffic.stop)

        # Letting the traffic flow for a bit to make sure the network has converged
        if not self.traffic.does_traffic_flow(delay_time=constants.TRAFFIC_STABILIZATION_TIME):
            raise TestRunError('Traffic is not flowing', err_details='Normal traffic did not flow')

        # Clearing counters so that any packets lost so far don't influence the results
        self.traffic.clear_counters()

        if self.traffic.any_traffic_loss(delay_time=constants.TRAFFIC_DELAY_TIME,
                                         tolerance=constants.TRAFFIC_TOLERANCE):
            raise TestRunError('Traffic is flowing with packet loss',
                               err_details='Normal traffic flew with packet loss')

        self.tc_result['scaling_to_level']['traffic_after'] = 'NORMAL_TRAFFIC_LOAD'

        self.traffic.stop()
        self.unregister_from_cleanup(index=40)

    @Step(name='Terminate the NS', description='Trigger the termination of the NS instance on the NFVO')
    def step11(self):
        # --------------------------------------------------------------------------------------------------------------
        # 11. Trigger the termination of the NS instance on the NFVO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering the termination of the NS instance on the NFVO')
        self.time_record.START('terminate_ns')
        if self.mano.ns_terminate_sync(ns_instance_id=self.ns_instance_id,
                                       terminate_time=self.tc_input.get('terminate_time'),
                                       additional_param=self.tc_input['mano'].get('termination_params')) != \
                constants.OPERATION_SUCCESS:
            self.tc_result['events']['terminate_ns']['details'] = 'Fail'
            raise TestRunError('Unexpected status for NS termination operation',
                               err_details='NS termination operation failed')

        self.time_record.END('terminate_ns')

        self.tc_result['events']['terminate_ns']['duration'] = self.time_record.duration('terminate_ns')
        self.tc_result['events']['terminate_ns']['details'] = 'Success'

        self.unregister_from_cleanup(index=20)
        self.unregister_from_cleanup(index=10)

        self.register_for_cleanup(index=10, function_reference=self.mano.ns_delete_id,
                                  ns_instance_id=self.ns_instance_id)

    @Step(name='Verify NS is terminated',
          description='Verify that the NS is terminated and that all resources have been released by the VIM')
    def step12(self):
        # --------------------------------------------------------------------------------------------------------------
        # 12. Verify that the NS is terminated and that all resources have been released by the VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NS is terminated')
        ns_info_after_termination = self.mano.ns_query(query_filter={'ns_instance_id': self.ns_instance_id,
                                                                     'additional_param': self.tc_input['mano'].get(
                                                                         'query_params')})
        if ns_info_after_termination.ns_state != constants.NS_NOT_INSTANTIATED:
            raise TestRunError('Unexpected NS instantiation state',
                               err_details='NS instantiation state was not "%s" after the NS was terminated'
                                           % constants.NS_NOT_INSTANTIATED)

        LOG.info('Verifying that all the VNF instance(s) have been terminated')
        for vnf_info in self.ns_info_after_scale_to_level.vnf_info:
            vnf_instance_id = vnf_info.vnf_instance_id
            vnf_info = self.mano.vnf_query(query_filter={'vnf_instance_id': vnf_instance_id,
                                                         'additional_param': self.tc_input['mano'].get('query_params')})
            if vnf_info.instantiation_state != constants.VNF_NOT_INSTANTIATED:
                raise TestRunError('VNF instance %s was not terminated correctly. Expected state was %s but got %s'
                                   % (vnf_instance_id, constants.VNF_NOT_INSTANTIATED, vnf_info.instantiation_state))

        LOG.info('Verifying that all resources have been released by the VIM')
        if not self.mano.validate_ns_released_vresources(self.ns_info_after_scale_to_level):
            raise TestRunError('Allocated resources have not been released by the VIM')

        LOG.info('%s execution completed successfully' % self.tc_name)
