import logging

from api.generic import constants
from test_cases import TestCase, TestRunError
from utils.misc import generate_name

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNF_STATE_STOP_003(TestCase):
    """
    TC_VNF_STATE_STOP_003 VNF Stop with normal traffic load and measure stop time

    Sequence:
    1. Instantiate the VNF
    2. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
    3. Start the normal traffic load
    4. Validate the provided functionality
    5. Stop the VNF
    6. Validate VNF instantiation state is INSTANTIATED and VNF state is STOPPED
    7. Validate that no traffic flows once stop is completed
    """

    REQUIRED_APIS = ('mano', 'traffic')
    REQUIRED_ELEMENTS = ('vnfd_id',)
    TESTCASE_EVENTS = ('instantiate_vnf', 'stop_vnf', 'traffic_deactivation')

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

        # --------------------------------------------------------------------------------------------------------------
        # 3. Start the normal traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the normal traffic load')
        self.traffic.configure(traffic_load='NORMAL_TRAFFIC_LOAD',
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
        # 4. Validate the provided functionality
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating the provided functionality')
        if not self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is not flowing', err_details='Normal traffic did not flow')

        if self.traffic.any_traffic_loss(tolerance=constants.TRAFFIC_TOLERANCE):
            raise TestRunError('Traffic is flowing with packet loss',
                               err_details='Normal traffic flew with packet loss')

        if not self.mano.validate_allocated_vresources(self.vnf_instance_id, self.tc_input['mano'].get('query_params')):
            raise TestRunError('Allocated vResources could not be validated')

        self.tc_result['resources']['Initial'] = self.mano.get_allocated_vresources(
                                                                              self.vnf_instance_id,
                                                                              self.tc_input['mano'].get('query_params'))

        # --------------------------------------------------------------------------------------------------------------
        # 5. Stop the VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Stopping the VNF')
        # Clearing counters so traffic deactivation time is accurate
        self.traffic.clear_counters()
        self.time_record.START('stop_vnf')
        if self.mano.vnf_operate_sync(self.vnf_instance_id, change_state_to='stop',
                                      stop_type=self.tc_input.get('stop_type'),
                                      graceful_stop_timeout=self.tc_input.get('graceful_stop_timeout'),
                                      additional_param=self.tc_input['mano'].get('operate_params')) \
                != constants.OPERATION_SUCCESS:
            raise TestRunError('MANO could not stop the VNF')
        self.time_record.END('stop_vnf')

        self.tc_result['events']['stop_vnf']['duration'] = self.time_record.duration('stop_vnf')

        self.tc_result['events']['traffic_deactivation']['duration'] = self.traffic.calculate_deactivation_time()

        # --------------------------------------------------------------------------------------------------------------
        # 6. Validate VNF instantiation state is INSTANTIATED and VNF state is STOPPED
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
        # 7. Validate that no traffic flows once stop is completed
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating that no traffic flows once stop is completed')
        if self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is still flowing', err_details='Traffic still flew after VNF was stopped')

        LOG.info('%s execution completed successfully' % self.tc_name)
