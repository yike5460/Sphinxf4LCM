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
from api.structures.objects import VnfLifecycleChangeNotification
from test_cases import TestCase, TestRunError
from utils.misc import generate_name

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNFC_SCALE_OUT_004__MANO_ONDEMAND__VNF_IND__STEP_1(TestCase):
    """
    TC_VNFC_SCALE_OUT_004__MANO_ONDEMAND__VNF_IND__STEP_1 Max vResource VNFC limit reached before max VNFD limit for
    scale-out with on-demand scaling event generated by MANO and triggered by a VNF Indicator produced by the VNF.
    Scaling step is set to max_instances.

    Sequence:
    1. Ensure NFVI has vResources so that the VNF can be scaled out only desired_scale_out_steps times
    2. Instantiate the VNF
    3. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
    4. Start the low traffic load
    5. Validate the provided functionality and all traffic goes through
    6. Subscribe for VNF Lifecycle change notifications
    7. Trigger a resize of the VNF resources to the maximum by altering the VNF indicator produced by the VNF
    8. Validate VNF scale out operation was performed desired_scale_out_steps times
    9. Validate VNF has resized to the max (limited by NFVI)
    10. Determine if and length of service disruption
    11. Validate traffic goes through
    12. Terminate the VNF
    13. Validate that the VNF is terminated and that all resources have been released by the VIM
    """

    REQUIRED_APIS = ('mano', 'vim', 'traffic')
    REQUIRED_ELEMENTS = ('vnfd_id', 'scaling_policy_name', 'desired_scale_out_steps')
    TESTCASE_EVENTS = ('instantiate_vnf', 'scale_out_vnf', 'service_disruption', 'terminate_vnf')

    def run(self):
        LOG.info('Starting %s' % self.tc_name)

        # Get scaling policy properties
        sp = self.mano.get_vnfd_scaling_properties(self.tc_input['vnfd_id'], self.tc_input['scaling_policy_name'])

        # --------------------------------------------------------------------------------------------------------------
        # 1. Ensure NFVI has vResources so that the VNF can be scaled out only desired_scale_out_steps times
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Ensuring NFVI has vResources so that the VNF can be scaled out only desired_scale_out_steps times')
        # Reserving only compute resources is enough for limiting the NFVI resources
        reservation_id = self.mano.limit_compute_resources_for_vnf_scaling(
                                                       vnfd_id=self.tc_input['vnfd_id'],
                                                       scaling_policy_name=self.tc_input['scaling_policy_name'],
                                                       desired_scale_out_steps=self.tc_input['desired_scale_out_steps'],
                                                       generic_vim_object=self.vim)
        if reservation_id is None:
            raise TestRunError('Compute resources could not be limited')

        self.register_for_cleanup(index=10, function_reference=self.vim.terminate_compute_resource_reservation,
                                  reservation_id=reservation_id)

        # --------------------------------------------------------------------------------------------------------------
        # 2. Instantiate the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Instantiating the VNF')
        self.time_record.START('instantiate_vnf')
        self.vnf_instance_id = self.mano.vnf_create_and_instantiate(
                                                 vnfd_id=self.tc_input['vnfd_id'],
                                                 flavour_id=self.tc_input.get('flavour_id'),
                                                 vnf_instance_name=generate_name(self.tc_name),
                                                 vnf_instance_description=self.tc_input.get('vnf_instance_description'),
                                                 instantiation_level_id=self.tc_input.get('instantiation_level_id'),
                                                 ext_virtual_link=self.tc_input.get('ext_virtual_link'),
                                                 ext_managed_virtual_link=self.tc_input.get('ext_managed_virtual_link'),
                                                 localization_language=self.tc_input.get('localization_language'),
                                                 additional_param=self.tc_input['mano'].get('instantiation_params'))

        if self.vnf_instance_id is None:
            raise TestRunError('VNF instantiation operation failed')

        self.time_record.END('instantiate_vnf')

        self.tc_result['events']['instantiate_vnf']['duration'] = self.time_record.duration('instantiate_vnf')

        self.register_for_cleanup(index=20, function_reference=self.mano.vnf_terminate_and_delete,
                                  vnf_instance_id=self.vnf_instance_id, termination_type='graceful',
                                  graceful_termination_timeout=self.tc_input.get('graceful_termination_timeout'),
                                  additional_param=self.tc_input['mano'].get('termination_params'))
        self.register_for_cleanup(index=30, function_reference=self.mano.wait_for_vnf_stable_state,
                                  vnf_instance_id=self.vnf_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 3. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF instantiation state is INSTANTIATED')
        vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id,
                                               'additional_param': self.tc_input['mano'].get('query_params')})
        if vnf_info.instantiation_state != constants.VNF_INSTANTIATED:
            raise TestRunError('Unexpected VNF instantiation state',
                               err_details='VNF instantiation state was not "%s" after the VNF was instantiated'
                                           % constants.VNF_INSTANTIATED)

        LOG.info('Validating VNF state is STARTED')
        if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STARTED:
            raise TestRunError('Unexpected VNF state',
                               err_details='VNF state was not "%s" after the VNF was instantiated'
                                           % constants.VNF_STARTED)

        self.tc_result['resources']['Initial'] = self.mano.get_allocated_vresources(
                                                                              self.vnf_instance_id,
                                                                              self.tc_input['mano'].get('query_params'))

        # --------------------------------------------------------------------------------------------------------------
        # 4. Start the low traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the low traffic load')
        self.traffic.configure(traffic_load='LOW_TRAFFIC_LOAD',
                               traffic_config=self.tc_input['traffic']['traffic_config'])

        self.register_for_cleanup(index=40, function_reference=self.traffic.destroy)

        # Configure stream destination address(es)
        dest_addr_list = self.mano.get_vnf_ingress_cp_addr_list(
                                                          vnf_info,
                                                          self.tc_input['traffic']['traffic_config']['ingress_cp_name'])
        self.traffic.reconfig_traffic_dest(dest_addr_list)

        self.traffic.start(return_when_emission_starts=True)

        self.register_for_cleanup(index=50, function_reference=self.traffic.stop)

        # --------------------------------------------------------------------------------------------------------------
        # 5. Validate the provided functionality and all traffic goes through
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating the provided functionality and all traffic goes through')
        if not self.traffic.does_traffic_flow(delay_time=constants.TRAFFIC_DELAY_TIME):
            raise TestRunError('Traffic is not flowing', err_details='Low traffic did not flow')

        if self.traffic.any_traffic_loss(tolerance=constants.TRAFFIC_TOLERANCE):
            raise TestRunError('Traffic is flowing with packet loss', err_details='Low traffic flew with packet loss')

        self.tc_result['scaling_out']['traffic_before'] = 'LOW_TRAFFIC_LOAD'

        if not self.mano.validate_vnf_allocated_vresources(self.vnf_instance_id,
                                                           self.tc_input['mano'].get('query_params')):
            raise TestRunError('Allocated vResources could not be validated')

        # --------------------------------------------------------------------------------------------------------------
        # 6. Subscribe for VNF Lifecycle change notifications
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Subscribing for VNF lifecycle change notifications')
        subscription_id = self.mano.vnf_lifecycle_change_notification_subscribe(
                                                          notification_filter={'vnf_instance_id': self.vnf_instance_id})

        # --------------------------------------------------------------------------------------------------------------
        # 7. Trigger a resize of the VNF resources to the maximum by altering the VNF indicator produced by EM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Trigger a resize of the VNF resources to the maximum by altering the VNF indicator produced by EM')

        # The scale out is triggered by a VNF related indicator value change.
        # The VNF exposed interface of Ve-Vnfm-Vnf will enable the MANO to trigger a scale out based on VNF Indicator
        # value changes. VNF related indicators are declared in the VNFD.
        # Insert here code alters the VNF related indicators so that MANO can trigger scale out.

        # TODO: Insert here code to:
        # 1. alter the VNF related indicators so that MANO can trigger VNF scale out in incremental steps.
        # 2. check that MANO has subscribed to VNF
        # 3. subscribe to VNF and check the notifications
        # For now we use only traffic load to trigger scale out.
        self.traffic.config_traffic_load('MAX_TRAFFIC_LOAD')

        # --------------------------------------------------------------------------------------------------------------
        # 8. Validate VNF scale out operation was performed desired_scale_out_steps times
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF scale out operation was performed desired_scale_out_steps times')
        notification_queue = self.mano.get_notification_queue(subscription_id)

        self.time_record.START('scale_out_vnf')
        # We are scaling the VNF (desired_scale_out_steps + 1) times and check at the next step that the VNF scaled out
        # only desired_scale_out_steps times
        for scale_out_level in range(self.tc_input['desired_scale_out_steps'] + 1):
            notification_info = self.mano.search_in_notification_queue(
                                                                      notification_queue=notification_queue,
                                                                      notification_type=VnfLifecycleChangeNotification,
                                                                      notification_pattern={'status': 'STARTED',
                                                                                            'operation': 'VNF_SCALE.*'},
                                                                      timeout=constants.VNF_SCALE_TIMEOUT)
            if notification_info is None:
                raise TestRunError('Could not validate that VNF scale out started')
            notification_info = self.mano.search_in_notification_queue(
                                                                      notification_queue=notification_queue,
                                                                      notification_type=VnfLifecycleChangeNotification,
                                                                      notification_pattern={'status': 'SUCCESS|FAILED',
                                                                                            'operation': 'VNF_SCALE.*'},
                                                                      timeout=constants.VNF_SCALE_TIMEOUT)
            if notification_info is None:
                raise TestRunError('Could not validate that VNF scale out finished')

        self.time_record.END('scale_out_vnf')

        self.tc_result['events']['scale_out_vnf']['duration'] = self.time_record.duration('scale_out_vnf')

        # --------------------------------------------------------------------------------------------------------------
        # 9. Validate VNF has resized to the max (limited by NFVI)
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF has resized to the max (limited by NFVI)')
        vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id,
                                               'additional_param': self.tc_input['mano'].get('query_params')})
        if len(vnf_info.instantiated_vnf_info.vnfc_resource_info) != sp['default_instances'] + sp['increment'] * \
                                                                     self.tc_input['desired_scale_out_steps']:
            raise TestRunError('VNF scaled out')

        self.tc_result['resources']['After scale out'] = self.mano.get_allocated_vresources(
                                                                              self.vnf_instance_id,
                                                                              self.tc_input['mano'].get('query_params'))

        self.tc_result['scaling_out']['level'] = sp['default_instances'] + self.tc_input['desired_scale_out_steps']

        self.tc_result['scaling_out']['status'] = 'Success'

        # --------------------------------------------------------------------------------------------------------------
        # 10. Determine if and length of service disruption
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Determining if and length of service disruption')
        self.tc_result['events']['service_disruption']['duration'] = self.traffic.calculate_service_disruption_length()

        # --------------------------------------------------------------------------------------------------------------
        # 11. Validate traffic goes through
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating traffic goes through')
        # Since the VNF scaled out only desired_scale_out_steps, we are not checking the traffic loss because we do not
        # expect all traffic to go through.
        # Decreasing the traffic load to normal would not be appropriate as it could trigger a scale in.
        if not self.traffic.does_traffic_flow(delay_time=constants.TRAFFIC_DELAY_TIME):
            raise TestRunError('Traffic is not flowing', err_details='Max traffic did not flow')

        self.tc_result['scaling_out']['traffic_after'] = 'MAX_TRAFFIC_LOAD'

        # --------------------------------------------------------------------------------------------------------------
        # 12. Terminate the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Terminating the VNF')
        self.time_record.START('terminate_vnf')
        if self.mano.vnf_terminate_sync(self.vnf_instance_id, termination_type='graceful',
                                        graceful_termination_timeout=self.tc_input.get('graceful_termination_timeout'),
                                        additional_param=self.tc_input['mano'].get('termination_params')) != \
                constants.OPERATION_SUCCESS:
            raise TestRunError('Unexpected status for terminating VNF operation',
                               err_details='VNF terminate operation failed')

        self.time_record.END('terminate_vnf')

        self.tc_result['events']['terminate_vnf']['duration'] = self.time_record.duration('terminate_vnf')

        self.unregister_from_cleanup(index=30)
        self.unregister_from_cleanup(index=20)

        self.register_for_cleanup(index=20, function_reference=self.mano.vnf_delete_id,
                                  vnf_instance_id=self.vnf_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 13. Validate that the VNF is terminated and all resources have been released by the VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating that the VNF is terminated')
        vnf_info_final = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id,
                                                     'additional_param': self.tc_input['mano'].get('query_params')})
        if vnf_info_final.instantiation_state != constants.VNF_NOT_INSTANTIATED:
            raise TestRunError('Unexpected VNF instantiation state',
                               err_details='VNF instantiation state was not "%s" after the VNF was terminated'
                                           % constants.VNF_NOT_INSTANTIATED)

        LOG.info('Validating that all resources have been released by the VIM')
        if not self.mano.validate_vnf_released_vresources(vnf_info_initial=vnf_info):
            raise TestRunError('Allocated resources have not been released by the VIM')

        LOG.info('%s execution completed successfully' % self.tc_name)
