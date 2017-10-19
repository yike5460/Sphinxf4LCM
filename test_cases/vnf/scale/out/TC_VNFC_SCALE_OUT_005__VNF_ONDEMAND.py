import logging
import time

from api.generic import constants
from test_cases import TestCase, TestRunError
from utils.misc import generate_name

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNFC_SCALE_OUT_005__VNF_ONDEMAND(TestCase):
    """
    TC_VNFC_SCALE_OUT_005__VNF_ONDEMAND Removal of virtualized specialized hardware acceleration for VNFC scale-in with
    on-demand scaling event generated by VNF

    Sequence:
    1. Instantiate the VNF
    2. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
    3. Start the low traffic load
    4. Validate traffic flows through without issues
    5. Trigger a resize of the VNF resources to use more specialized hardware by increasing the traffic load to the
       maximum
    6. Validate VNF has resized
    7. Validate increased capacity without traffic loss
    8. Validate that MANO has allocated more specialized hardware resources
    9. Trigger a resize of the VNF resources to use less specialized hardware by decreasing the traffic load to the
       minimum
    10. Validate VNF has resized and has decreased its capacity and removed VNFCs
    11. Validate that MANO has allocated less specialized hardware resources and the previous specialized hardware
        resources have been freed up
    12. Determine the service disruption during the resizing
    13. Validate traffic flows through without issues
    """

    REQUIRED_APIS = ('mano', 'traffic')
    REQUIRED_ELEMENTS = ('vnfd_id', 'scaling_policy_name')
    TESTCASE_EVENTS = ('instantiate_vnf', 'scale_out_vnf', 'service_disruption', 'scale_in_vnf')

    def run(self):
        LOG.info('Starting %s' % self.tc_name)
        # TODO: Check the VNFD to see if hardware acceleration is present. This check will be added after we create an
        # internal representation for the VNFD.

        # Get scaling policy properties
        sp = self.mano.get_vnfd_scaling_properties(self.tc_input['vnfd_id'], self.tc_input['scaling_policy_name'])

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

        if self.vnf_instance_id is None:
            raise TestRunError('VNF instantiation operation failed')

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
                                               'additional_param': self.tc_input['mano']['query_params']})
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
                                                                                  self.tc_input['mano']['query_params'])

        # --------------------------------------------------------------------------------------------------------------
        # 3. Start the low traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the low traffic load')
        self.traffic.configure(traffic_load='LOW_TRAFFIC_LOAD',
                               traffic_config=self.tc_input['traffic']['traffic_config'])

        self.register_for_cleanup(index=30, function_reference=self.traffic.destroy)

        # Configure stream destination address(es)
        dest_addr_list = ''
        for ext_cp_info in vnf_info.instantiated_vnf_info.ext_cp_info:
            if ext_cp_info.cpd_id == self.tc_input['traffic']['traffic_config']['ingress_cp_name']:
                dest_addr_list += ext_cp_info.address[0] + ' '
        self.traffic.reconfig_traffic_dest(dest_addr_list)

        self.traffic.start(return_when_emission_starts=True)

        self.register_for_cleanup(index=40, function_reference=self.traffic.stop)

        # --------------------------------------------------------------------------------------------------------------
        # 4. Validate traffic flows through without issues
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating traffic flows through without issues')
        if not self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is not flowing', err_details='Low traffic did not flow')

        if self.traffic.any_traffic_loss(tolerance=constants.TRAFFIC_TOLERANCE):
            raise TestRunError('Traffic is flowing with packet loss', err_details='Low traffic flew with packet loss')

        if not self.mano.validate_allocated_vresources(self.vnf_instance_id, self.tc_input['mano']['query_params']):
            raise TestRunError('Allocated vResources could not be validated')

        self.tc_result['scaling_out']['traffic_before'] = 'LOW_TRAFFIC_LOAD'

        # --------------------------------------------------------------------------------------------------------------
        # 5. Trigger a resize of the VNF resources to use more specialized hardware by increasing the traffic load to
        #    the maximum
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering a resize of the VNF resources to use more specialized hardware by increasing the traffic '
                 'load to the maximum')
        self.traffic.config_traffic_load('MAX_TRAFFIC_LOAD')

        # --------------------------------------------------------------------------------------------------------------
        # 6. Validate VNF has resized
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF has resized')
        # The scale out duration will include:
        # - the time it takes the VNF CPU load to increase (caused by the max traffic load)
        # - the time after which the scaling alarm is triggered
        # - the time it takes the VNF to scale out
        self.time_record.START('scale_out_vnf')
        elapsed_time = 0
        while elapsed_time < constants.VNF_SCALE_OUT_TIMEOUT:
            vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id,
                                                   'additional_param': self.tc_input['mano']['query_params']})
            if len(vnf_info.instantiated_vnf_info.vnfc_resource_info) == sp['default_instances'] + sp['increment']:
                break
            else:
                time.sleep(constants.POLL_INTERVAL)
                elapsed_time += constants.POLL_INTERVAL
            if elapsed_time == constants.VNF_SCALE_OUT_TIMEOUT:
                self.tc_result['scaling_out']['status'] = 'Fail'
                raise TestRunError('VNF has not resized')

        self.time_record.END('scale_out_vnf')

        self.tc_result['events']['scale_out_vnf']['duration'] = self.time_record.duration('scale_out_vnf')

        self.tc_result['resources']['After scale out'] = self.mano.get_allocated_vresources(
                                                                                  self.vnf_instance_id,
                                                                                  self.tc_input['mano']['query_params'])

        self.tc_result['scaling_out']['level'] = sp['default_instances'] + sp['increment']

        self.tc_result['scaling_out']['status'] = 'Success'

        # --------------------------------------------------------------------------------------------------------------
        # 7. Validate increased capacity without traffic loss
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating increased capacity without traffic loss')
        # Because the VNF scaled out, we need to reconfigure traffic so that it passes through all VNFCs.

        # Stop the max traffic load.
        self.traffic.stop()

        # Configure stream destination address(es).
        dest_addr_list = ''
        for ext_cp_info in vnf_info.instantiated_vnf_info.ext_cp_info:
            if ext_cp_info.cpd_id == self.tc_input['traffic']['traffic_config']['ingress_cp_name']:
                dest_addr_list += ext_cp_info.address[0] + ' '

        self.traffic.reconfig_traffic_dest(dest_addr_list)
        self.traffic.clear_counters()

        # Start the max traffic load.
        self.traffic.start(return_when_emission_starts=True)

        if not self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is not flowing', err_details='Max traffic did not flow')

        if self.traffic.any_traffic_loss(tolerance=constants.TRAFFIC_TOLERANCE):
            raise TestRunError('Traffic is flowing with packet loss', err_details='Max traffic flew with packet loss')

        self.tc_result['scaling_out']['traffic_after'] = 'MAX_TRAFFIC_LOAD'
        self.tc_result['scaling_in']['traffic_before'] = 'MAX_TRAFFIC_LOAD'

        # --------------------------------------------------------------------------------------------------------------
        # 8. Validate that MANO has allocated more specialized hardware resources
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validate that MANO has allocated more specialized hardware resources')
        if not self.mano.validate_allocated_vresources(self.vnf_instance_id, self.tc_input['mano']['query_params']):
            raise TestRunError('Allocated vResources could not be validated')

        # --------------------------------------------------------------------------------------------------------------
        # 9. Trigger a resize of the VNF resources to use less specialized hardware by decreasing the traffic load to
        #    the minimum
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering a resize of the VNF resources to use less specialized hardware by decreasing the traffic '
                 'load to the minimum')
        self.traffic.config_traffic_load('LOW_TRAFFIC_LOAD')

        # --------------------------------------------------------------------------------------------------------------
        # 10. Validate VNF has resized and has decreased its capacity and removed VNFCs
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF has resized and has decreased its capacity and removed VNFCs')
        # The scale in duration will include:
        # - the time it takes the VNF CPU load to decrease (caused by the low traffic load)
        # - the time after which the scaling alarm is triggered
        # - the time it takes the VNF to scale in
        self.time_record.START('scale_in_vnf')
        elapsed_time = 0
        while elapsed_time < constants.VNF_SCALE_IN_TIMEOUT:
            vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id,
                                                   'additional_param': self.tc_input['mano']['query_params']})
            if len(vnf_info.instantiated_vnf_info.vnfc_resource_info) == sp['default_instances']:
                break
            else:
                time.sleep(constants.POLL_INTERVAL)
                elapsed_time += constants.POLL_INTERVAL
            if elapsed_time == constants.VNF_SCALE_IN_TIMEOUT:
                self.tc_result['scaling_in']['status'] = 'Fail'
                raise TestRunError('VNF has not decreased the VNFCs')

        self.time_record.END('scale_in_vnf')

        self.tc_result['events']['scale_in_vnf']['duration'] = self.time_record.duration('scale_in_vnf')

        self.tc_result['resources']['After scale in'] = self.mano.get_allocated_vresources(
                                                                                  self.vnf_instance_id,
                                                                                  self.tc_input['mano']['query_params'])

        self.tc_result['scaling_in']['level'] = sp['default_instances']

        self.tc_result['scaling_in']['status'] = 'Success'

        # --------------------------------------------------------------------------------------------------------------
        # 11. Validate that MANO has allocated less specialized hardware resources and the previous specialized hardware
        #     resources have been freed up
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validate that MANO has allocated less specialized hardware resources and the previous specialized '
                 'hardware resources have been freed up')
        if not self.mano.validate_allocated_vresources(self.vnf_instance_id, self.tc_input['mano']['query_params']):
            raise TestRunError('Allocated vResources could not be validated')

        # --------------------------------------------------------------------------------------------------------------
        # 12. Determine the service disruption during the resizing
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Determining the service disruption during the resizing')
        self.tc_result['events']['service_disruption']['duration'] = self.traffic.calculate_service_disruption_length()

        # --------------------------------------------------------------------------------------------------------------
        # 13. Validate traffic flows through without issues
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating traffic flows through without issues')

        # Stop the low traffic load.
        self.traffic.stop()

        # Configure stream destination address(es).
        dest_addr_list = ''
        for ext_cp_info in vnf_info.instantiated_vnf_info.ext_cp_info:
            if ext_cp_info.cpd_id == self.tc_input['traffic']['traffic_config']['ingress_cp_name']:
                dest_addr_list += ext_cp_info.address[0] + ' '

        self.traffic.reconfig_traffic_dest(dest_addr_list)
        self.traffic.clear_counters()

        # Start the low traffic load.
        self.traffic.start(return_when_emission_starts=True)

        # Checking the traffic flow.
        if not self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is not flowing', err_details='Low traffic did not flow')

        if self.traffic.any_traffic_loss(tolerance=constants.TRAFFIC_TOLERANCE):
            raise TestRunError('Traffic is flowing with packet loss', err_details='Low traffic flew with packet loss')

        self.tc_result['scaling_in']['traffic_after'] = 'LOW_TRAFFIC_LOAD'

        LOG.info('%s execution completed successfully' % self.tc_name)
