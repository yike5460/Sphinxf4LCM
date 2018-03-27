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
from test_cases import TestCase, TestRunError
from utils.misc import generate_name

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNF_STATE_START_003(TestCase):
    """
    TC_VNF_STATE_START_003 VNF Start under normal traffic load and measure start time

    Sequence:
    1. Instantiate the VNF
    2. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
    3. Start the normal traffic load
    4. Validate traffic goes through
    5. Stop the normal traffic load
    6. Stop the VNF
    7. Validate VNF instantiation state is INSTANTIATED and VNF state is STOPPED
    8. Start the normal traffic load
    9. Validate no traffic goes through
    10. Start the VNF
    11. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
    12. Calculate the time for activation
    13. Validate traffic goes through
    14. Validate no scaling has occurred
    15. Stop the VNF
    16. Validate that no traffic flows once stop is completed
    """

    REQUIRED_APIS = ('mano', 'traffic')
    REQUIRED_ELEMENTS = ('vnfd_id',)
    TESTCASE_EVENTS = ('instantiate_vnf', 'stop_vnf', 'start_vnf', 'traffic_activation')

    def run(self):
        LOG.info('Starting %s' % self.tc_name)

        # --------------------------------------------------------------------------------------------------------------
        # 1. Instantiate the VNF
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

        self.time_record.END('instantiate_vnf')

        self.tc_result['events']['instantiate_vnf']['duration'] = self.time_record.duration('instantiate_vnf')

        self.register_for_cleanup(index=10, function_reference=self.mano.vnf_terminate_and_delete,
                                  vnf_instance_id=self.vnf_instance_id, termination_type='graceful',
                                  graceful_termination_timeout=self.tc_input.get('graceful_termination_timeout'),
                                  additional_param=self.tc_input['mano'].get('termination_params'))
        self.register_for_cleanup(index=20, function_reference=self.mano.wait_for_vnf_stable_state,
                                  vnf_instance_id=self.vnf_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 2. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
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

        initial_instances = len(vnf_info.instantiated_vnf_info.vnfc_resource_info)

        # --------------------------------------------------------------------------------------------------------------
        # 3. Start the normal traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the normal traffic load')
        self.traffic.configure(traffic_load='NORMAL_TRAFFIC_LOAD',
                               traffic_config=self.tc_input['traffic']['traffic_config'])

        self.register_for_cleanup(index=30, function_reference=self.traffic.destroy)

        # Configure stream destination address(es)
        dest_addr_list = self.mano.get_vnf_ingress_cp_addr_list(
                                                          vnf_info,
                                                          self.tc_input['traffic']['traffic_config']['ingress_cp_name'])
        self.traffic.reconfig_traffic_dest(dest_addr_list)

        self.traffic.start(return_when_emission_starts=True)

        self.register_for_cleanup(index=40, function_reference=self.traffic.stop)

        # --------------------------------------------------------------------------------------------------------------
        # 4. Validate traffic goes through
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating traffic goes through')
        if not self.traffic.does_traffic_flow(delay_time=constants.TRAFFIC_DELAY_TIME):
            raise TestRunError('Traffic is not flowing', err_details='Normal traffic did not flow')

        if self.traffic.any_traffic_loss(tolerance=constants.TRAFFIC_TOLERANCE):
            raise TestRunError('Traffic is flowing with packet loss',
                               err_details='Normal traffic flew with packet loss')

        if not self.mano.validate_vnf_allocated_vresources(self.vnf_instance_id,
                                                           self.tc_input['mano'].get('query_params')):
            raise TestRunError('Allocated vResources could not be validated')

        self.tc_result['resources']['Initial'] = self.mano.get_allocated_vresources(
                                                                              self.vnf_instance_id,
                                                                              self.tc_input['mano'].get('query_params'))

        # --------------------------------------------------------------------------------------------------------------
        # 5. Stop the normal traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Stopping the normal traffic load')
        self.traffic.stop()

        # --------------------------------------------------------------------------------------------------------------
        # 6. Stop the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Stopping the VNF')
        self.time_record.START('stop_vnf')
        if self.mano.vnf_operate_sync(self.vnf_instance_id, change_state_to='stop',
                                      stop_type=self.tc_input.get('stop_type'),
                                      graceful_stop_timeout=self.tc_input.get('graceful_stop_timeout'),
                                      additional_param=self.tc_input['mano'].get('operate_params')) \
                != constants.OPERATION_SUCCESS:
            raise TestRunError('MANO could not stop the VNF')
        self.time_record.END('stop_vnf')

        self.tc_result['events']['stop_vnf']['duration'] = self.time_record.duration('stop_vnf')

        # --------------------------------------------------------------------------------------------------------------
        # 7. Validate VNF instantiation state is INSTANTIATED and VNF state is STOPPED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF instantiation state is INSTANTIATED')
        vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id,
                                               'additional_param': self.tc_input['mano'].get('query_params')})
        if vnf_info.instantiation_state != constants.VNF_INSTANTIATED:
            raise TestRunError('Unexpected VNF instantiation state',
                               err_details='VNF instantiation state was not "%s" after the VNF was stopped'
                                           % constants.VNF_INSTANTIATED)

        LOG.info('Validating VNF state is STOPPED')
        if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STOPPED:
            raise TestRunError('Unexpected VNF state',
                               err_details='VNF state was not "%s" after the VNF was stopped' % constants.VNF_STOPPED)

        # --------------------------------------------------------------------------------------------------------------
        # 8. Start the normal traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the normal traffic load')
        self.traffic.start(return_when_emission_starts=False)

        # --------------------------------------------------------------------------------------------------------------
        # 9. Validate no traffic goes through
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating no traffic goes through')
        if self.traffic.does_traffic_flow(delay_time=constants.TRAFFIC_DELAY_TIME):
            raise TestRunError('Traffic is flowing', err_details='Traffic flew before VNF was started')

        # --------------------------------------------------------------------------------------------------------------
        # 10. Start the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the VNF')
        self.time_record.START('start_vnf')
        if self.mano.vnf_operate_sync(self.vnf_instance_id, change_state_to='start',
                                      additional_param=self.tc_input['mano'].get('operate_params')) \
                != constants.OPERATION_SUCCESS:
            raise TestRunError('MANO could not start the VNF')
        self.time_record.END('start_vnf')

        self.tc_result['events']['start_vnf']['duration'] = self.time_record.duration('start_vnf')

        # --------------------------------------------------------------------------------------------------------------
        # 11. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF instantiation state is INSTANTIATED')
        vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id,
                                               'additional_param': self.tc_input['mano'].get('query_params')})
        if vnf_info.instantiation_state != constants.VNF_INSTANTIATED:
            raise TestRunError('Unexpected VNF instantiation state',
                               err_details='VNF instantiation state was not "%s" after the VNF was started'
                                           % constants.VNF_INSTANTIATED)

        LOG.info('Validating VNF state is STARTED')
        if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STARTED:
            raise TestRunError('Unexpected VNF state',
                               err_details='VNF state was not "%s" after the VNF was started' % constants.VNF_STARTED)

        # --------------------------------------------------------------------------------------------------------------
        # 12. Calculate the time for activation
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Calculating the time for traffic activation')
        self.tc_result['events']['traffic_activation']['duration'] = self.traffic.calculate_activation_time()

        # --------------------------------------------------------------------------------------------------------------
        # 13. Validate traffic goes through
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating traffic goes through')

        # Clearing counters as the traffic lost so far influences the results
        self.traffic.clear_counters()

        if not self.traffic.does_traffic_flow(delay_time=constants.TRAFFIC_DELAY_TIME):
            raise TestRunError('Traffic is not flowing', err_details='Normal traffic did not flow')

        if self.traffic.any_traffic_loss(tolerance=constants.TRAFFIC_TOLERANCE):
            raise TestRunError('Traffic is flowing with packet loss',
                               err_details='Normal traffic flew with packet loss')

        # --------------------------------------------------------------------------------------------------------------
        # 14. Validate no scaling has occurred
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating no scaling has occurred')
        vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id,
                                               'additional_param': self.tc_input['mano'].get('query_params')})
        if len(vnf_info.instantiated_vnf_info.vnfc_resource_info) != initial_instances:
            raise TestRunError('VNF scaling occurred')

        # --------------------------------------------------------------------------------------------------------------
        # 15. Stop the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Stopping the VNF')
        if self.mano.vnf_operate_sync(self.vnf_instance_id, change_state_to='stop',
                                      stop_type=self.tc_input.get('stop_type'),
                                      graceful_stop_timeout=self.tc_input.get('graceful_stop_timeout'),
                                      additional_param=self.tc_input['mano'].get('operate_params')) \
                != constants.OPERATION_SUCCESS:
            raise TestRunError('MANO could not stop the VNF')

        # --------------------------------------------------------------------------------------------------------------
        # 16. Validate that no traffic flows once stop is completed
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating that no traffic flows once stop is completed')
        if self.traffic.does_traffic_flow(delay_time=constants.TRAFFIC_DELAY_TIME):
            raise TestRunError('Traffic is still flowing', err_details='Traffic still flew after VNF was stopped')

        LOG.info('%s execution completed successfully' % self.tc_name)
