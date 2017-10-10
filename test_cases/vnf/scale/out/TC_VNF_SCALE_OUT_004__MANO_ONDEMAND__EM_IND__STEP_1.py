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


class TC_VNF_SCALE_OUT_004__MANO_ONDEMAND__EM_IND__STEP_1(TestCase):
    """
    TC_VNF_SCALE_OUT_004__MANO_ONDEMAND__EM_IND__STEP_1 Max vResource VNF limit reached before max NSD limit for
    scale-out with manual scaling event generated by MANO and scaling step set to 1. The stimulus for scaling out
    consists of value changes of one or multiple VNF related indicators on the interface produced by the EM.

    Sequence:
    1. Ensure NFVI has vResources so that the NS can be scaled out only desired_scale_out_steps times
    2. Instantiate the NS
    3. Validate NS state is INSTANTIATED
    4. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
    5. Start the low traffic load
    6. Validate the provided functionality and all traffic goes through
    7. Subscribe for NS Lifecycle change notifications
    8. Trigger a resize of the NS resources to the maximum by altering a VNF indicator that is produced by the EM
    9. Validate NS scale out operation was performed desired_scale_out_steps times
    10. Validate NS has resized to the max (limited by NFVI)
    11. Determine if and length of service disruption
    12. Validate traffic goes through
    """

    required_elements = ('mano', 'vim', 'traffic', 'nsd_id', 'scaling_policy_name', 'desired_scale_out_steps')

    def setup(self):
        LOG.info('Starting setup for TC_VNF_SCALE_OUT_004__MANO_ONDEMAND__EM_IND__STEP_1')

        # Create objects needed by the test.
        self.mano = Mano(vendor=self.tc_input['mano']['type'], **self.tc_input['mano']['client_config'])
        self.vim = Vim(vendor=self.tc_input['vim']['type'], **self.tc_input['vim']['client_config'])
        self.traffic = Traffic(self.tc_input['traffic']['type'], **self.tc_input['traffic']['client_config'])
        self.register_for_cleanup(index=10, function_reference=self.traffic.destroy)

        # Initialize test case result.
        self.tc_result['events']['instantiate_ns'] = dict()
        self.tc_result['events']['scale_out_ns'] = dict()
        self.tc_result['events']['service_disruption'] = dict()

        LOG.info('Finished setup for TC_VNF_SCALE_OUT_004__MANO_ONDEMAND__EM_IND__STEP_1')

    def run(self):
        LOG.info('Starting TC_VNF_SCALE_OUT_004__MANO_ONDEMAND__EM_IND__STEP_1')

        # Get scaling policy properties
        sp = self.mano.get_nsd_scaling_properties(self.tc_input['nsd_id'], self.tc_input['scaling_policy_name'])

        # --------------------------------------------------------------------------------------------------------------
        # 1. Ensure NFVI has vResources so that the NS can be scaled out only desired_scale_out_steps times
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Ensuring NFVI has vResources so that the NS can be scaled out only desired_scale_out_steps times')
        # Reserving only compute resources is enough for limiting the NFVI resources
        reservation_id = self.mano.limit_compute_resources_for_ns_scaling(self.tc_input['nsd_id'],
                                                                          self.tc_input['scaling_policy_name'],
                                                                          self.tc_input['desired_scale_out_steps'],
                                                                          self.vim)
        if reservation_id is None:
            raise TestRunError('Compute resources could not be limited')

        self.register_for_cleanup(index=20, function_reference=self.vim.terminate_compute_resource_reservation,
                                  reservation_id=reservation_id)

        # --------------------------------------------------------------------------------------------------------------
        # 2. Instantiate the NS
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Instantiating the NS')
        self.time_record.START('instantiate_ns')
        self.ns_instance_id = self.mano.ns_create_and_instantiate(nsd_id=self.tc_input['nsd_id'],
                                                                  ns_name=generate_name(self.tc_input['ns']['name']),
                                                                  ns_description=None, flavour_id=None)
        if self.ns_instance_id is None:
            raise TestRunError('NS instantiation operation failed')

        self.time_record.END('instantiate_ns')

        self.tc_result['events']['instantiate_ns']['duration'] = self.time_record.duration('instantiate_ns')

        self.register_for_cleanup(index=30, function_reference=self.mano.ns_terminate_and_delete,
                                  ns_instance_id=self.ns_instance_id)

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

        self.tc_result['resources']['Initial'] = self.mano.get_allocated_vresources(self.vnf_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 5. Start the low traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting the low traffic load')
        self.traffic.configure(traffic_load='LOW_TRAFFIC_LOAD',
                               traffic_config=self.tc_input['traffic']['traffic_config'])

        # Configure stream destination address(es)
        dest_addr_list = ''
        for ext_cp_info in vnf_info.instantiated_vnf_info.ext_cp_info:
            if ext_cp_info.cpd_id == self.tc_input['traffic']['traffic_config']['ingress_cp_name']:
                dest_addr_list += ext_cp_info.address[0] + ' '
        self.traffic.config_traffic_stream(dest_addr_list)

        self.traffic.start(return_when_emission_starts=True)

        self.register_for_cleanup(index=40, function_reference=self.traffic.stop)

        # --------------------------------------------------------------------------------------------------------------
        # 6 Validate the provided functionality and all traffic goes through
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating the provided functionality and all traffic goes through')
        if not self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is not flowing', err_details='Low traffic did not flow')

        if self.traffic.any_traffic_loss(tolerance=constants.traffic_tolerance):
            raise TestRunError('Traffic is flowing with packet loss', err_details='Low traffic flew with packet loss')

        self.tc_result['scaling_out']['traffic_before'] = 'LOW_TRAFFIC_LOAD'

        if not self.mano.validate_allocated_vresources(self.tc_input['vnfd_id'], self.vnf_instance_id):
            raise TestRunError('Allocated vResources could not be validated')

        # --------------------------------------------------------------------------------------------------------------
        # 7. Subscribe to NS Lifecycle change notifications
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Subscribing to NS lifecycle change notifications')
        subscription_id = self.mano.ns_lifecycle_change_notification_subscribe(
                                                                         filter={'ns_instance_id': self.ns_instance_id})

        # --------------------------------------------------------------------------------------------------------------
        # 8. Trigger a resize of the NS resources to the maximum by altering a VNF indicator that is produced by the EM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering a resize of the NS resources to the maximum by altering a VNF indicator that is produced '
                 'by the EM')

        # The scale out is triggered by a VNF related indicator value change.
        # The EM exposed interface Ve-Vnfm-Em will enable the MANO to trigger a scale out based on VNF Indicator
        # value changes. VNF related indicators are declared in the VNFD.
        # There are 2 ways for MANO to obtain VNF Indicator information:
        # - by GetIndicatorValue operation on the Ve-Vnfm-Em interface
        # - by subscribing for notifications related to VNF Indicator value changes with the EM.
        # The two operations involved are Subscribe and Notify.

        # TODO: Insert here code to:
        # 1. alter the VNF related indicators so that MANO can trigger an NS scale out
        # 2. check that MANO has subscribed to EM
        # 3. subscribe to EM and check the notifications
        # For now we use only traffic load to trigger the scale out (we will increase the traffic load to the maximum).
        self.traffic.config_traffic_load('MAX_TRAFFIC_LOAD')

        # --------------------------------------------------------------------------------------------------------------
        # 9. Validate NS scale out operation was performed desired_scale_out_steps times
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF scale out operation was performed desired_scale_out_steps times')
        notification_queue = self.mano.get_notification_queue(subscription_id)

        self.time_record.START('scale_out_ns')
        # We are scaling the NS (desired_scale_out_steps + 1) times and check at the next step that the NS scaled out
        # only desired_scale_out_steps times
        for scale_out_step in range(self.tc_input['desired_scale_out_steps'] + 1):
            notification_info = self.mano.search_in_notification_queue(notification_queue=notification_queue,
                                                                       notification_type=VnfLifecycleChangeNotification,
                                                                       notification_pattern={'status': 'STARTED',
                                                                                             'operation': 'NS_SCALE.*'},
                                                                       timeout=constants.SCALE_INTERVAL)
            if notification_info is None:
                raise TestRunError('Could not validate that NS scale out started')
            notification_info = self.mano.search_in_notification_queue(notification_queue=notification_queue,
                                                                       notification_type=VnfLifecycleChangeNotification,
                                                                       notification_pattern={'status': 'SUCCESS|FAILED',
                                                                                             'operation': 'NS_SCALE.*'},
                                                                       timeout=constants.SCALE_INTERVAL)
            if notification_info is None:
                raise TestRunError('Could not validate that NS scale out finished')

        self.time_record.END('scale_out_ns')

        self.tc_result['events']['scale_out_ns']['duration'] = self.time_record.duration('scale_out_ns')

        # --------------------------------------------------------------------------------------------------------------
        # 10. Validate NS has resized to the max (limited by NFVI)
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating NS has resized to the max (limited by NFVI)')
        # The NS should have default_instances + desired_scale_out_steps * increment VNFs after scale out
        ns_info = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id})
        if len(ns_info.vnf_info_id) != sp['default_instances'] + sp['increment'] * \
                                       self.tc_input['desired_scale_out_steps']:
            raise TestRunError('NS did not scale out to the max NFVI limit')

        self.tc_result['resources']['After scale out'] = dict()
        for vnf_instance_id in ns_info.vnf_info_id:
            self.tc_result['resources']['After scale out'].update(self.mano.get_allocated_vresources(vnf_instance_id))

        self.tc_result['scaling_out']['level'] = sp['default_instances'] + sp['increment'] * \
                                                 self.tc_input['desired_scale_out_steps']

        self.tc_result['scaling_out']['status'] = 'Success'

        # --------------------------------------------------------------------------------------------------------------
        # 11. Determine is and length of service disruption
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Determining if and length of service disruption')
        self.tc_result['events']['service_disruption']['duration'] = self.traffic.calculate_service_disruption_length()

        # --------------------------------------------------------------------------------------------------------------
        # 12. Validate traffic goes through
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating traffic goes through')
        # Since the NS scaled out only desired_scale_out_steps, we are not checking the traffic loss because we do not
        # expect all traffic to go through.
        # Decreasing the traffic load to normal would not be appropriate as it could trigger a scale in.
        if not self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is not flowing', err_details='Max traffic did not flow')

        self.tc_result['scaling_out']['traffic_after'] = 'MAX_TRAFFIC_LOAD'

        LOG.info('TC_VNF_SCALE_OUT_004__MANO_ONDEMAND__EM_IND__STEP_1 execution completed successfully')
