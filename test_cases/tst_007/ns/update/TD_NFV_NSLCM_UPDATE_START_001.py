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
from api.structures.objects import OperateVnfData
from test_cases import TestCase, TestRunError, Step
from utils.misc import generate_name

# Instantiate logger
LOG = logging.getLogger(__name__)


class TD_NFV_NSLCM_UPDATE_START_001(TestCase):
    """
    TD_NFV_NSLCM_UPDATE_START_001 Verify the capability to start a VNF instance inside a NS instance

    Sequence:
    1.  Trigger NS instantiation on the NFVO
    2.  Verify that the NFVO indicates NS instantiation operation result as successful
    3.  Trigger the NFVO to stop the target VNF instance inside the NS
    4.  Verify that the VNF instance operational state on the VNFM is indicated as "stopped"
    5.  Verify that the compute resources allocated to the VNFC instances inside the target VNF instance have been
        stopped by querying the VIM
    6.  Verify that other existing compute resources have not been affected by the performed operation by querying the
        VIM
    7.  Trigger the NFVO to start the target VNF instance inside the NS instance
    8.  Verify that the VNF instance operational state on the VNFM is indicated as "started"
    9.  Verify that the compute resources allocated to the target VNF instance have been started by querying the VIM
    10. Verify that other existing compute resources have not been affected by the performed operation by querying the
        VIM
    11. Verify that the NFVO shows no "operate VNF" operation errors
    12. Verify that the NS functionality that utilizes the started VNF instance operates successfully by running the
        end-to-end functional test
    13. Trigger the termination of the NS instance on the NFVO
    14. Verify that the NS is terminated and that all resources have been released by the VIM
    """

    REQUIRED_APIS = ('mano', 'traffic')
    REQUIRED_ELEMENTS = ('nsd_id', 'operate_vnf_data')
    TESTCASE_EVENTS = ('instantiate_ns', 'ns_update_stop_vnf', 'ns_update_start_vnf', 'terminate_ns')

    @Step(name='Instantiate the NS', description='Trigger NS instantiation on the NFVO')
    def step1(self):
        LOG.info('Starting %s' % self.tc_name)

        # --------------------------------------------------------------------------------------------------------------
        # 1. Trigger NS instantiation on the NFVO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering NS instantiation on the NFVO')
        self.time_record.START('instantiate_ns')
        self.ns_instance_id = self.mano.ns_create_and_instantiate(
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

        self.time_record.END('instantiate_ns')

        self.tc_result['events']['instantiate_ns']['duration'] = self.time_record.duration('instantiate_ns')
        self.tc_result['events']['instantiate_ns']['details'] = 'Success'

        sleep(constants.INSTANCE_FIRST_BOOT_TIME)

        self.register_for_cleanup(index=10, function_reference=self.mano.ns_terminate_and_delete,
                                  ns_instance_id=self.ns_instance_id,
                                  terminate_time=self.tc_input.get('terminate_time'),
                                  additional_param=self.tc_input['mano'].get('termination_params'))
        self.register_for_cleanup(index=20, function_reference=self.mano.wait_for_ns_stable_state,
                                  ns_instance_id=self.ns_instance_id)

    @Step(name='Verify NS instantiation was successful',
          description='Verify that the NFVO indicates NS instantiation operation result as successful')
    def step2(self):
        # --------------------------------------------------------------------------------------------------------------
        # 2. Verify that the NFVO indicates NS instantiation operation result as successful
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NFVO indicates NS instantiation operation result as successful')
        self.ns_info_after_instantiation = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id,
                                                                      'additional_param': self.tc_input['mano'].get(
                                                                          'query_params')})
        if self.ns_info_after_instantiation.ns_state != constants.NS_INSTANTIATED:
            raise TestRunError('Unexpected NS instantiation state',
                               err_details='NS instantiation state was not "%s" after the NS was instantiated'
                                           % constants.NS_INSTANTIATED)

        for vnf_info in self.ns_info_after_instantiation.vnf_info:
            self.tc_result['resources']['%s (After instantiation)' % vnf_info.vnf_product_name] = dict()
            self.tc_result['resources']['%s (After instantiation)' % vnf_info.vnf_product_name].update(
                self.mano.get_allocated_vresources(vnf_info.vnf_instance_id, self.tc_input['mano'].get('query_params')))

    @Step(name='Stop the target VNF', description='Trigger the NFVO to stop the target VNF instance inside the NS')
    def step3(self):
        # --------------------------------------------------------------------------------------------------------------
        # 3. Trigger the NFVO to stop the target VNF instance inside the NS
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering the NFVO to stop the target VNF instance inside the NS')
        self.operate_vnf_data_list = list()
        for vnf_info in self.ns_info_after_instantiation.vnf_info:
            if vnf_info.vnf_product_name in self.tc_input['operate_vnf_data']:
                vnf_data = OperateVnfData()
                vnf_data.vnf_instance_id = vnf_info.vnf_instance_id
                vnf_data.change_state_to = 'stop'
                vnf_data.additional_param = self.tc_input['mano'].get('operate_params')
                self.operate_vnf_data_list.append(vnf_data)

        self.time_record.START('ns_update_stop_vnf')

        if self.mano.ns_update_sync(ns_instance_id=self.ns_instance_id, update_type='OperateVnf',
                                    operate_vnf_data=self.operate_vnf_data_list) != constants.OPERATION_SUCCESS:
            raise TestRunError('Unexpected status for NS update operation',
                               err_details='NS update operation failed')

        self.time_record.END('ns_update_stop_vnf')

        self.tc_result['events']['ns_update_stop_vnf']['duration'] = self.time_record.duration('ns_update_stop_vnf')
        self.tc_result['events']['ns_update_stop_vnf']['details'] = 'Success'

    @Step(name='Verify target VNF was stopped',
          description='Verify that the VNF instance operational state on the VNFM is indicated as "stopped"')
    def step4(self):
        # --------------------------------------------------------------------------------------------------------------
        # 4. Verify that the VNF instance operational state on the VNFM is indicated as "stopped"
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the VNF instance operational state on the VNFM is indicated as "stopped"')
        for vnf_data in self.operate_vnf_data_list:
            vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': vnf_data.vnf_instance_id,
                                                   'additional_param': self.tc_input['mano'].get('query_params')})
            if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STOPPED:
                raise TestRunError('Target VNF %s was not stopped' % vnf_info.vnf_product_name)

    @Step(name='Verify compute resources allocated to the target VNF instance have been stopped',
          description='Verify that the compute resources allocated to the VNFC instances inside the target VNF instance'
                      ' have been stopped by querying the VIM')
    def step5(self):
        # --------------------------------------------------------------------------------------------------------------
        # 5. Verify that the compute resources allocated to the VNFC instances inside the target VNF instance have been
        #    stopped by querying the VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the compute resources allocated to the VNFC instances inside the target VNF instance '
                 'have been stopped by querying the VIM')
        for vnf_data in self.operate_vnf_data_list:
            if not self.mano.validate_vnf_vresource_state(vnf_data.vnf_instance_id,
                                                          self.tc_input['mano'].get('query_params')):
                raise TestRunError(
                    'Target VNF %s compute resources have not been stopped' % vnf_data.vnf_instance_id)

    @Step(name='Verify other compute resources have not been affected by the stop operation',
          description='Verify that other existing compute resources have not been affected by the performed operation '
                      'by querying the VIM')
    def step6(self):
        # --------------------------------------------------------------------------------------------------------------
        # 6. Verify that other existing compute resources have not been affected by the performed operation by querying
        #    the VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that other existing compute resources have not been affected by the performed operation by '
                 'querying the VIM')
        ns_info_before_start = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id,
                                                          'additional_param': self.tc_input['mano'].get(
                                                              'query_params')})
        for vnf_info in ns_info_before_start.vnf_info:
            if vnf_info.vnf_product_name not in self.tc_input['operate_vnf_data']:
                if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STARTED:
                    raise TestRunError('Other compute resources have been affected by the VNF stop operation',
                                       err_details='VNF %s state is %s; expected %s' % (vnf_info.vnf_product_name,
                                                    vnf_info.instantiated_vnf_info.vnf_state, constants.VNF_STARTED))

    @Step(name='Start the target VNF',
          description='Trigger the NFVO to start the target VNF instance inside the NS instance')
    def step7(self):
        # --------------------------------------------------------------------------------------------------------------
        # 7. Trigger the NFVO to start the target VNF instance inside the NS instance
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Trigger the NFVO to start the target VNF instance inside the NS instance')
        for vnf_data in self.operate_vnf_data_list:
            vnf_data.change_state_to = 'start'
        self.time_record.START('ns_update_start_vnf')
        if self.mano.ns_update_sync(ns_instance_id=self.ns_instance_id, update_type='OperateVnf',
                                    operate_vnf_data=self.operate_vnf_data_list) != constants.OPERATION_SUCCESS:
            raise TestRunError('Unexpected status for NS update operation',
                               err_details='NS update operation failed')

        self.time_record.END('ns_update_start_vnf')

        self.tc_result['events']['ns_update_start_vnf']['duration'] = self.time_record.duration('ns_update_start_vnf')
        self.tc_result['events']['ns_update_start_vnf']['details'] = 'Success'

        sleep(constants.INSTANCE_BOOT_TIME)

    @Step(name='Verify target VNF was started',
          description='Verify that the VNF instance operational state on the VNFM is indicated as "started"')
    def step8(self):
        # --------------------------------------------------------------------------------------------------------------
        # 8. Verify that the VNF instance operational state on the VNFM is indicated as "started"
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the VNF instance operational state on the VNFM is indicated as started')
        for vnf_data in self.operate_vnf_data_list:
            vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': vnf_data.vnf_instance_id,
                                                   'additional_param': self.tc_input['mano'].get('query_params')})
            if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STARTED:
                raise TestRunError('Target VNF %s was not started' % vnf_info.vnf_product_name)

    @Step(name='Verify compute resources allocated to the target VNF instance have been started',
          description='Verify that the compute resources allocated to the target VNF instance have been started by '
                      'querying the VIM')
    def step9(self):
        # --------------------------------------------------------------------------------------------------------------
        # 9. Verify that the compute resources allocated to the target VNF instance have been started by querying the
        #    VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the compute resources allocated to the target VNF instance have been started by'
                 ' querying the VIM')
        for vnf_data in self.operate_vnf_data_list:
            if not self.mano.validate_vnf_vresource_state(vnf_data.vnf_instance_id,
                                                          self.tc_input['mano'].get('query_params')):
                raise TestRunError('Target VNF %s compute resources have not been started' % vnf_data.vnf_instance_id)

    @Step(name='Verify other compute resources have not been affected by the start operation',
          description='Verify that other existing compute resources have not been affected by the performed operation '
                      'by querying the VIM')
    def step10(self):
        # --------------------------------------------------------------------------------------------------------------
        # 10. Verify that other existing compute resources have not been affected by the performed operation by querying
        #     the VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that other existing compute resources have not been affected by the performed operation by '
                 'querying the VIM')
        self.ns_info_after_start = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id,
                                                              'additional_param': self.tc_input['mano'].get(
                                                                  'query_params')})
        for vnf_info in self.ns_info_after_start.vnf_info:
            if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STARTED:
                raise TestRunError('Other compute resources have been affected by the VNF start operation',
                                   err_details='VNF %s state is %s; expected %s' % (vnf_info.vnf_product_name,
                                                vnf_info.instantiated_vnf_info.vnf_state, constants.VNF_STARTED))

    @Step(name='Verify VNF start operation was successful',
          description='Verify that the NFVO shows no "operate VNF" operation errors')
    def step11(self):
        # --------------------------------------------------------------------------------------------------------------
        # 11. Verify that the NFVO shows no "operate VNF" operation errors
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NFVO shows no "operate VNF" operation errors')
        LOG.debug('This has implicitly been checked at step 7')

    @Step(name='Verify traffic flows',
          description='Verify that the NS functionality that utilizes the started VNF instance operates successfully by'
                      ' running the end-to-end functional test')
    def step12(self):
        # --------------------------------------------------------------------------------------------------------------
        # 12. Verify that the NS functionality that utilizes the started VNF instance operates successfully by running
        #     the end-to-end functional test
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NS functionality that utilizes the started VNF instance operates successfully by'
                 ' running the end-to-end functional test')
        resolved_traffic_config = self.mano.resolve_ns_cp_addr(self.ns_info_after_start,
                                                               data=self.tc_input['traffic']['traffic_config'])
        self.traffic.configure(traffic_load='NORMAL_TRAFFIC_LOAD', traffic_config=resolved_traffic_config)

        self.register_for_cleanup(index=30, function_reference=self.traffic.destroy)

        # Configure stream destination address(es)
        dest_addr_list = self.mano.get_ns_ingress_cp_addr_list(
                                                          self.ns_info_after_start,
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

        self.traffic.stop()
        self.unregister_from_cleanup(index=40)

    @Step(name='Terminate the NS', description='Trigger the termination of the NS instance on the NFVO')
    def step13(self):
        # --------------------------------------------------------------------------------------------------------------
        # 13. Trigger the termination of the NS instance on the NFVO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering the termination of the NS instance on the NFVO')
        self.time_record.START('terminate_ns')
        if self.mano.ns_terminate_sync(ns_instance_id=self.ns_instance_id,
                                       terminate_time=self.tc_input.get('terminate_time'),
                                       additional_param=self.tc_input['mano'].get('termination_params')) != \
                constants.OPERATION_SUCCESS:
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
    def step14(self):
        # --------------------------------------------------------------------------------------------------------------
        # 14. Verify that the NS is terminated and that all resources have been released by the VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NS is terminated')
        ns_info_after_termination = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id,
                                                               'additional_param': self.tc_input['mano'].get(
                                                                   'query_params')})
        if ns_info_after_termination.ns_state != constants.NS_NOT_INSTANTIATED:
            raise TestRunError('Unexpected NS instantiation state',
                               err_details='NS instantiation state was not "%s" after the NS was terminated'
                                           % constants.NS_NOT_INSTANTIATED)

        LOG.info('Verifying that all the VNF instance(s) have been terminated')
        for vnf_info in self.ns_info_after_start.vnf_info:
            vnf_instance_id = vnf_info.vnf_instance_id
            vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': vnf_instance_id,
                                                   'additional_param': self.tc_input['mano'].get('query_params')})
            if vnf_info.instantiation_state != constants.VNF_NOT_INSTANTIATED:
                raise TestRunError('VNF instance %s was not terminated correctly. Expected state was %s but got %s'
                                   % (vnf_instance_id, constants.VNF_NOT_INSTANTIATED, vnf_info.instantiation_state))

        LOG.info('Verifying that all resources have been released by the VIM')
        if not self.mano.validate_ns_released_vresources(self.ns_info_after_start):
            raise TestRunError('Allocated resources have not been released by the VIM')

        LOG.info('%s execution completed successfully' % self.tc_name)
