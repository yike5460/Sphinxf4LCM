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

# Instantiate logger
LOG = logging.getLogger(__name__)


class TD_NFV_FM_VNF_NOTIFY_001(TestCase):
    """
    TD_NFV_FM_VNF_NOTIFY_001 Verify that a VNF fault alarm notification propagates via the VNFM to the NFVO when a VNF
    fault is triggered by a failed virtualized resource

    Sequence:
    1. Trigger NS instantiation on the NFVO
    2. Verify that the NFVO indicates NS instantiation operation result as successful
    3. Verify that no fault alarms have been created on the VIM, VNFM and NFVO
    4. Trigger a failure on a virtualized resource allocated to the relevant VNF instance (e.g. terminate the
       virtualized resource directly on the VIM)
    5. Verify that a virtualized resource fault alarm has been created on the VIM by querying the list of virtualized
       resource fault alarms
    6. Verify that a VNF fault alarm has been created for the affected VNF instance on the VNFM by querying the list of
       VNF fault alarms
    7. Verify that a NS fault alarm has been created on the NFVO by querying the list of NS fault alarms
    8. Trigger the termination of the NS instance on the NFVO
    9. Verify that the NS is terminated and that all resources have been released by the VIM
    """

    REQUIRED_APIS = ('mano', 'vim')
    REQUIRED_ELEMENTS = ('nsd_id',)
    TESTCASE_EVENTS = ('instantiate_ns', 'terminate_ns')

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
                self.mano.get_allocated_vresources(vnf_info.vnf_instance_id,
                                                   self.tc_input['mano'].get('query_params')))

    @Step(name='Verify that no fault alarms have been created on the VIM, VNFM and NFVO',
          description='Verify that no fault alarms have been created on the VIM, VNFM and NFVO')
    def step3(self):
        # --------------------------------------------------------------------------------------------------------------
        # 3. Verify that no fault alarms have been created on the VIM, VNFM and NFVO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that no fault alarms have been created on the VIM, VNFM and NFVO')
        # Verify that no fault alarms have been created on the VIM
        # TODO

        # Verify that no fault alarms have been created on the VNFM
        # TODO

        # Verify that no fault alarms have been created on the NFVO
        self.nfvo_alarm_filter = self.tc_input['mano'].get('alarm_list_params', {})
        self.nfvo_alarm_filter.update({'ns_instance_id': self.ns_instance_id})
        self.nfvo_alarm_filter.update({'alarm_state': 'ALARM_TRIGGERED'})
        nfvo_alarm_list = self.mano.ns_get_alarm_list(self.nfvo_alarm_filter)
        if len(nfvo_alarm_list) != 0:
            raise TestRunError('Fault alarms have been created on the NFVO before triggering the failure')

    @Step(name='Terminate a virtualized resource directly on the VIM',
          description='Trigger a failure on a virtualized resource allocated to the relevant VNF instance')
    def step4(self):
        # --------------------------------------------------------------------------------------------------------------
        # 4. Trigger a failure on a virtualized resource allocated to the relevant VNF instance
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering a failure on a virtualized resource allocated to the relevant VNF instance')
        for vnf_info in self.ns_info_after_instantiation.vnf_info:
            for vnfc_resource_info in vnf_info.instantiated_vnf_info.vnfc_resource_info:
                self.resource_id = vnfc_resource_info.compute_resource.resource_id
                self.vim.terminate_virtualised_compute_resources(self.resource_id)
                break
            break

    @Step(name='Verify that a virtualized resource fault alarm has been created on the VIM',
          description='Verify that a virtualized resource fault alarm has been created on the VIM by querying the list '
                      'of virtualized resource fault alarms',
          runnable=False)
    def step5(self):
        # --------------------------------------------------------------------------------------------------------------
        # 5. Verify that a virtualized resource fault alarm has been created on the VIM by querying the list of
        #    virtualized resource fault alarms
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that a virtualized resource fault alarm has been created on the VIM by querying the list of'
                 ' virtualized resource fault alarms')
        # TODO

    @Step(name='Verify that a VNF fault alarm has been created on the VNFM',
          description='Verify that a VNF fault alarm has been created for the affected VNF instance on the VNFM by '
                      'querying the list of VNF fault alarms',
          runnable=False)
    def step6(self):
        # --------------------------------------------------------------------------------------------------------------
        # 6. Verify that a VNF fault alarm has been created for the affected VNF instance on the VNFM by querying the
        #    list of VNF fault alarms
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that a VNF fault alarm has been created for the affected VNF instance on the VNFM by '
                 'querying the list of VNF fault alarms')
        # TODO

    @Step(name='Verify that a NS fault alarm has been created on the NFVO',
          description='Verify that a NS fault alarm has been created on the NFVO by querying the list of NS fault '
                      'alarms')
    def step7(self):
        # --------------------------------------------------------------------------------------------------------------
        # 7. Verify that a NS fault alarm has been created on the NFVO by querying the list of NS fault alarms
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that a NS fault alarm has been created on the NFVO by querying the list of NS fault alarms')
        elapsed_time = 0
        while elapsed_time < constants.ALARM_CREATE_TIMEOUT:
            alarm_list = self.mano.ns_get_alarm_list(self.nfvo_alarm_filter)
            if len(alarm_list) != 0:
                break
            else:
                sleep(constants.POLL_INTERVAL)
                elapsed_time += constants.POLL_INTERVAL
            if elapsed_time == constants.ALARM_CREATE_TIMEOUT:
                raise TestRunError('No fault alarm created on the NFVO after %s seconds' % elapsed_time)

        notification_matched = False
        for alarm in alarm_list:
            resource_type = alarm.root_cause_faulty_resource.faulty_resource_type
            resource_id = alarm.root_cause_faulty_resource.faulty_resource.resource_id

            if resource_type == 'COMPUTE' and resource_id == self.resource_id:
                notification_matched = True
                break

        if not notification_matched:
            raise TestRunError('No fault alarm created on the NFVO for compute resource %s' % self.resource_id)

    @Step(name='Terminate the NS', description='Trigger the termination of the NS instance on the NFVO')
    def step8(self):
        # --------------------------------------------------------------------------------------------------------------
        # 8. Trigger the termination of the NS instance on the NFVO
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
    def step9(self):
        # --------------------------------------------------------------------------------------------------------------
        # 9. Verify that the NS is terminated and that all resources have been released by the VIM
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
        for vnf_info in self.ns_info_after_instantiation.vnf_info:
            vnf_instance_id = vnf_info.vnf_instance_id
            vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': vnf_instance_id,
                                                   'additional_param': self.tc_input['mano'].get('query_params')})
            if vnf_info.instantiation_state != constants.VNF_NOT_INSTANTIATED:
                raise TestRunError('VNF instance %s was not terminated correctly. Expected state was %s but got %s'
                                   % (vnf_instance_id, constants.VNF_NOT_INSTANTIATED, vnf_info.instantiation_state))

        LOG.info('Verifying that all resources have been released by the VIM')
        if not self.mano.validate_ns_released_vresources(self.ns_info_after_instantiation):
            raise TestRunError('Allocated resources have not been released by the VIM')

        LOG.info('%s execution completed successfully' % self.tc_name)
