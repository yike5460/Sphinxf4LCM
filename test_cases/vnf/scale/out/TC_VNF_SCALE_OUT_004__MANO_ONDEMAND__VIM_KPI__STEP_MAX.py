import logging

from api.generic import constants
from api.generic.mano import Mano
from api.generic.traffic import Traffic
from api.generic.vim import Vim
from api.structures.objects import VnfLifecycleChangeNotification
from test_cases import TestCase, TestRunError
from utils.misc import generate_name

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNF_SCALE_OUT_004__MANO_ONDEMAND__VIM_KPI__STEP_MAX(TestCase):
    """
    TC_VNF_SCALE_OUT_004__MANO_ONDEMAND__VIM_KPI__STEP_MAX Max vResource VNF limit reached before max NSD limit for
    scale-out with manual scaling event generated by MANO and scaling step set to max_instances. The stimulus for
    scaling out is a VIM key performance indicator threshold crossing.

    Sequence:
    1. Ensure NFVI has not enough vResources for the NS to be scaled out
    2. Instantiate the NS
    3. Validate NS state is INSTANTIATED
    4. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
    5. Start the low traffic load
    6. Validate the provided functionality and all traffic goes through
    7. Subscribe for VNF Lifecycle change notifications
    8. Trigger a resize of the NS resources to the maximum by altering a VIM KPI
    9. Validate that the scale out started and the operation finished
    10. Validate NS has not resized
    11. Determine if and length of service disruption
    12. Start the low traffic load
    13. Validate all traffic goes through
    """

    def setup(self):
        LOG.info('Starting setup for TC_VNF_SCALE_OUT_004__MANO_ONDEMAND__VIM_KPI__STEP_MAX')

        # Create objects needed by the test.
        self.mano = Mano(vendor=self.tc_input['mano_params']['type'], **self.tc_input['mano_params']['client_config'])
        self.vim = Vim(vendor=self.tc_input['vim_params']['type'], **self.tc_input['vim_params']['client_config'])
        self.traffic = Traffic(self.tc_input['traffic_params']['type'],
                               **self.tc_input['traffic_params']['client_config'])
        self.register_for_cleanup(self.traffic.destroy)

        # Initialize test case result.
        self.tc_result['overall_status'] = constants.TEST_PASSED
        self.tc_result['error_info'] = 'No errors'
        self.tc_result['events']['instantiate_ns'] = dict()
        self.tc_result['events']['scale_out_ns'] = dict()
        self.tc_result['events']['service_disruption'] = dict()

        LOG.info('Finished setup for TC_VNF_SCALE_OUT_004__MANO_ONDEMAND__VIM_KPI__STEP_MAX')

    def run(self):
        LOG.info('Starting TC_VNF_SCALE_OUT_004__MANO_ONDEMAND__VIM_KPI__STEP_MAX')

        # --------------------------------------------------------------------------------------------------------------
        # 1. Ensure NFVI has not enough vResources for the NS to be scaled out
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Ensure NFVI has not enough vResources for the NS to be scaled out')
        # Reserving only compute resources is enough for limiting the NFVI resources
        reservation_id = self.mano.limit_compute_resources_for_ns_scaling(
                               nsd_id=self.tc_input['nsd_id'], scaling_policy_name=self.tc_input['scaling_policy_name'],
                               desired_scale_out_steps=0, generic_vim_object=self.vim)
        if reservation_id is None:
            raise TestRunError('Compute resources could not be limited')

        self.register_for_cleanup(self.vim.terminate_compute_resource_reservation, reservation_id)

        # --------------------------------------------------------------------------------------------------------------
        # 2. Instantiate the NS
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Instantiating the NS')
        self.time_record.START('instantiate_ns')
        self.ns_instance_id = self.mano.ns_create_and_instantiate(nsd_id=self.tc_input['nsd_id'],
                                                                  ns_name=generate_name(self.tc_input['ns']['name']),
                                                                  ns_description=None, flavour_id=None)
        if self.ns_instance_id is None:
            raise TestRunError('Unexpected NS instantiation ID', err_details='NS instantiation operation failed')

        self.time_record.END('instantiate_ns')

        self.tc_result['events']['instantiate_ns']['duration'] = self.time_record.duration('instantiate_ns')

        self.register_for_cleanup(self.mano.ns_terminate_and_delete, ns_instance_id=self.ns_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 3. Validate NS state is INSTANTIATED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating NS state is INSTANTIATED')
        ns_info = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id})
        if ns_info.ns_state != constants.NS_INSTANTIATED:
            raise TestRunError('Unexpected NS state',
                               err_details='NS state was not "%s" after the NS was instantiated'
                                           % constants.NS_INSTANTIATED)

        # --------------------------------------------------------------------------------------------------------------
        # 4. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF instantiation state is INSTANTIATED')

        # Get the instance ID of the VNF inside the NS
        self.vnf_instance_id = ns_info.vnf_info_id[0]

        vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': self.vnf_instance_id})
        if vnf_info.instantiation_state != constants.VNF_INSTANTIATED:
            raise TestRunError('Unexpected VNF instantiation state',
                               err_details='VNF instantiation state was not "%s" after the VNF was instantiated'
                                           % constants.VNF_INSTANTIATED)

        LOG.info('Validating VNF state is STARTED')
        if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STARTED:
            raise TestRunError('Unexpected VNF state',
                               err_details='VNF state was not "%s" after the VNF was instantiated'
                                           % constants.VNF_STARTED)

        self.tc_result['resources']['Initial'] = self.mano.get_allocated_vresources(self.vnf_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 5. Start the low traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the low traffic load')
        if not self.traffic.configure(traffic_load='LOW_TRAFFIC_LOAD',
                                      traffic_config=self.tc_input['traffic_params']['traffic_config']):
            raise TestRunError('Low traffic load and traffic configuration parameter could not be applied')

        # Configure stream destination MAC address(es)
        dest_mac_addr_list = ''
        for ext_cp_info in vnf_info.instantiated_vnf_info.ext_cp_info:
            if ext_cp_info.cpd_id == self.tc_input['traffic_params']['traffic_config']['left_cp_name']:
                dest_mac_addr_list += ext_cp_info.address[0] + ' '
        self.traffic.config_traffic_stream(dest_mac_addr_list)

        if not self.traffic.start(return_when_emission_starts=True):
            raise TestRunError('Traffic could not be started', err_details='Low traffic could not be started')

        self.register_for_cleanup(self.traffic.stop)

        # --------------------------------------------------------------------------------------------------------------
        # 6 Validate the provided functionality and all traffic goes through
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating the provided functionality and all traffic goes through')
        if not self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is not flowing', err_details='Low traffic did not flow')

        if self.traffic.any_traffic_loss():
            raise TestRunError('Traffic is flowing with packet loss', err_details='Low traffic flew with packet loss')

        self.tc_result['scaling_out']['traffic_before'] = 'LOW_TRAFFIC_LOAD'

        if not self.mano.validate_allocated_vresources(self.tc_input['vnfd_id'], self.vnf_instance_id):
            raise TestRunError('Allocated vResources could not be validated')

        # --------------------------------------------------------------------------------------------------------------
        # 7. Subscribe for VNF Lifecycle change notifications
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Subscribing for VNF lifecycle change notifications')
        subscription_id = self.mano.vnf_lifecycle_change_notification_subscribe(
                                                                       filter={'vnf_instance_id': self.vnf_instance_id})

        # --------------------------------------------------------------------------------------------------------------
        # 8. Trigger a resize of the NS resources to the maximum by altering a VIM KPI
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering a resize of the NS resources to the maximum by altering a VIM KPI')

        # The scale out is triggered by a VIM KPI threshold crossing.
        # The Virtualised Resources Performance Management interface Or-Vi will enable the MANO to trigger a scale
        # out based on a VIM KPI.
        # There are 2 ways for MANO to obtain KPI information:
        # - by polling the VIM periodically on the Or-Vi interface (by means of a PM job)
        # - by subscribing for notifications related to performance information with the VIM. The MANO can define
        #   thresholds that generate notifications from the VIM when they are crossed.

        # TODO: Insert here code to:
        # 1. alter a VIM KPI so that MANO can trigger an NS scale out
        # 2. check that MANO has subscribed to VIM
        # 3. subscribe to VIM and check the notifications
        # For now we use only traffic load to trigger the scale out (we will increase the traffic load to the maximum).
        self.traffic.config_traffic_load('MAX_TRAFFIC_LOAD')

        # --------------------------------------------------------------------------------------------------------------
        # 9. Validate that the scaling out started and the operation finished
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating that the scale out started')
        notification_info = self.mano.wait_for_notification(subscription_id,
                                                            notification_type=VnfLifecycleChangeNotification,
                                                            notification_pattern={'status': 'STARTED',
                                                                                  'operation': 'NS_SCALE.*'},
                                                            timeout=120)
        if notification_info is None:
            raise TestRunError('Could not validate that NS scale out started')

        self.time_record.START('scale_out_ns')

        LOG.info('Validating that the scale out finished')
        notification_info = self.mano.wait_for_notification(subscription_id,
                                                            notification_type=VnfLifecycleChangeNotification,
                                                            notification_pattern={'status': 'SUCCESS|FAILED',
                                                                                  'operation': 'NS_SCALE.*'},
                                                            timeout=constants.SCALE_INTERVAL)
        if notification_info is None:
            raise TestRunError('Could not validate that NS scale out finished')

        self.time_record.END('scale_out_ns')

        self.tc_result['events']['scale_out_ns']['duration'] = self.time_record.duration('scale_out_ns')

        self.tc_result['resources']['After scale out'] = dict()
        ns_info = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id})
        for vnf_instance_id in ns_info.vnf_info_id:
            self.tc_result['resources']['After scale out'].update(self.mano.get_allocated_vresources(vnf_instance_id))

        self.tc_result['scaling_out']['status'] = notification_info.status

        # --------------------------------------------------------------------------------------------------------------
        # 10. Validate NS has not resized
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating NS has not resized')
        if len(ns_info.vnf_info_id) != self.tc_input['scaling']['default_instances']:
            raise TestRunError('NS did not scale out to the max NFVI limit')
        self.tc_result['scaling_out']['level'] = self.tc_input['scaling']['default_instances']

        # --------------------------------------------------------------------------------------------------------------
        # 11. Determine is and length of service disruption
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Determining if and length of service disruption')
        self.tc_result['events']['service_disruption']['duration'] = self.traffic.calculate_service_disruption_length()

        # --------------------------------------------------------------------------------------------------------------
        # 12. Start the low traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the low traffic load')

        # Stop the max traffic load.
        if not self.traffic.stop():
            raise TestRunError('Traffic could not be stopped', err_details='MAX traffic could not be stopped')

        # Configure the traffic load and clear counters.
        self.traffic.config_traffic_load('LOW_TRAFFIC_LOAD')
        self.traffic.clear_counters()

        # Start the low traffic load.
        if not self.traffic.start(return_when_emission_starts=True):
            raise TestRunError('Traffic could not be started', err_details='Low traffic could not be started')

        # --------------------------------------------------------------------------------------------------------------
        # 13. Validate all traffic goes through
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating all traffic goes through')
        if not self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is not flowing', err_details='Low traffic did not flow')

        if self.traffic.any_traffic_loss():
            raise TestRunError('Traffic is flowing with packet loss', err_details='Low traffic flew with packet loss')

        self.tc_result['scaling_out']['traffic_after'] = 'LOW_TRAFFIC_LOAD'

        LOG.info('TC_VNF_SCALE_OUT_004__MANO_ONDEMAND__VIM_KPI__STEP_MAX execution completed successfully')
