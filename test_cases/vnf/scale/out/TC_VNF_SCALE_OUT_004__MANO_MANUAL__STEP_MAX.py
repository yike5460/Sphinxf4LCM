import logging

from api.generic import constants
from api.structures.objects import ScaleNsData, ScaleNsByStepsData
from test_cases import TestCase, TestRunError
from utils.misc import generate_name

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNF_SCALE_OUT_004__MANO_MANUAL__STEP_MAX(TestCase):
    """
    TC_VNF_SCALE_OUT_004__MANO_MANUAL__STEP_MAX Max vResource VNF limit reached before max NSD limit for scale-out with
    manual scaling event generated by MANO and scaling step set to max_instances

    Sequence:
    1. Ensure NFVI has not enough vResources for the NS to be scaled out
    2. Instantiate the NS
    3. Validate NS state is INSTANTIATED
    4. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
    5. Start the low traffic load
    6. Validate the provided functionality and all traffic goes through
    7. Trigger a resize of the NS resources to the maximum by instructing the MANO to scale out the NS
    8. Validate NS has not resized
    9. Determine if and length of service disruption
    10. Validate all traffic goes through
    """

    REQUIRED_APIS = ('mano', 'vim', 'traffic')
    REQUIRED_ELEMENTS = ('nsd_id', 'scaling_policy_name')
    TESTCASE_EVENTS = ('instantiate_ns', 'scale_out_ns', 'service_disruption')

    def run(self):
        LOG.info('Starting %s' % self.tc_name)

        # Get scaling policy properties
        sp = self.mano.get_nsd_scaling_properties(self.tc_input['nsd_id'], self.tc_input['scaling_policy_name'])

        # --------------------------------------------------------------------------------------------------------------
        # 1. Ensure NFVI has not enough vResources for the NS to be scaled out
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Ensure NFVI has not enough vResources for the NS to be scaled out')
        # Reserving only compute resources is enough for limiting the NFVI resources
        reservation_id = self.mano.limit_compute_resources_for_ns_scaling(
                                                               nsd_id=self.tc_input['nsd_id'],
                                                               scaling_policy_name=self.tc_input['scaling_policy_name'],
                                                               desired_scale_out_steps=0, generic_vim_object=self.vim)
        if reservation_id is None:
            raise TestRunError('Compute resources could not be limited')

        self.register_for_cleanup(index=10, function_reference=self.vim.terminate_compute_resource_reservation,
                                  reservation_id=reservation_id)

        # --------------------------------------------------------------------------------------------------------------
        # 2. Instantiate the NS
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Instantiating the NS')
        self.time_record.START('instantiate_ns')
        self.ns_instance_id = self.mano.ns_create_and_instantiate(
               nsd_id=self.tc_input['nsd_id'], ns_name=generate_name(self.tc_name),
               ns_description=self.tc_input.get('ns_description'), flavour_id=self.tc_input.get('flavour_id'),
               sap_data=self.tc_input.get('sap_data'), pnf_info=self.tc_input.get('pnf_info'),
               vnf_instance_data=self.tc_input.get('vnf_instance_data'),
               nested_ns_instance_data=self.tc_input.get('nested_ns_instance_data'),
               location_constraints=self.tc_input.get('location_constraints'),
               additional_param_for_ns=self.tc_input.get('additional_param_for_ns'),
               additional_param_for_vnf=self.tc_input.get('additional_param_for_vnf'),
               start_time=self.tc_input.get('start_time'),
               ns_instantiation_level_id=self.tc_input.get('ns_instantiation_level_id'),
               additional_affinity_or_anti_affinity_rule=self.tc_input.get('additional_affinity_or_anti_affinity_rule'))

        if self.ns_instance_id is None:
            raise TestRunError('NS instantiation operation failed')

        self.time_record.END('instantiate_ns')

        self.tc_result['events']['instantiate_ns']['duration'] = self.time_record.duration('instantiate_ns')

        self.register_for_cleanup(index=20, function_reference=self.mano.ns_terminate_and_delete,
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
        # 5. Start the low traffic load
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
        # 6 Validate the provided functionality and all traffic goes through
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating the provided functionality and all traffic goes through')
        if not self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is not flowing', err_details='Low traffic did not flow')

        if self.traffic.any_traffic_loss(tolerance=constants.TRAFFIC_TOLERANCE):
            raise TestRunError('Traffic is flowing with packet loss', err_details='Low traffic flew with packet loss')

        self.tc_result['scaling_out']['traffic_before'] = 'LOW_TRAFFIC_LOAD'

        if not self.mano.validate_allocated_vresources(self.vnf_instance_id, self.tc_input['mano'].get('query_params')):
            raise TestRunError('Allocated vResources could not be validated')

        # --------------------------------------------------------------------------------------------------------------
        # 7. Trigger a resize of the NS resources to the maximum by instructing the MANO to scale out the NS
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering a resize of the NS resources to the maximum by instructing the MANO to scale out the NS')

        # Build the ScaleNsData information element
        scale_ns_data = ScaleNsData()
        scale_ns_data.scale_ns_by_steps_data = ScaleNsByStepsData()
        scale_ns_data.scale_ns_by_steps_data.scaling_direction = 'scale_out'
        scale_ns_data.scale_ns_by_steps_data.aspect_id = sp['targets']
        scale_ns_data.scale_ns_by_steps_data.number_of_steps = sp['increment']

        self.time_record.START('scale_out_ns')
        if self.mano.ns_scale_sync(self.ns_instance_id, scale_type='scale_ns', scale_ns_data=scale_ns_data) \
                != constants.OPERATION_SUCCESS:
            self.tc_result['scaling_out']['status'] = 'Fail'
            raise TestRunError('MANO could not scale out the NS')

        self.time_record.END('scale_out_ns')

        self.tc_result['events']['scale_out_ns']['duration'] = self.time_record.duration('scale_out_ns')

        # --------------------------------------------------------------------------------------------------------------
        # 8. Validate NS has not resized
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating NS has not resized')
        ns_info = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id})
        if len(ns_info.vnf_info_id) != sp['default_instances']:
            raise TestRunError('NS did not scale out to the max NFVI limit')

        self.tc_result['resources']['After scale out'] = dict()
        for vnf_instance_id in ns_info.vnf_info_id:
            self.tc_result['resources']['After scale out'].update(
                self.mano.get_allocated_vresources(vnf_instance_id, self.tc_input['mano'].get('query_params')))

        self.tc_result['scaling_out']['level'] = sp['default_instances']

        self.tc_result['scaling_out']['status'] = 'Success'

        # --------------------------------------------------------------------------------------------------------------
        # 9. Determine is and length of service disruption
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Determining if and length of service disruption')
        self.tc_result['events']['service_disruption']['duration'] = self.traffic.calculate_service_disruption_length()

        # --------------------------------------------------------------------------------------------------------------
        # 10. Validate all traffic goes through
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating all traffic goes through')
        if not self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is not flowing', err_details='Low traffic did not flow')

        if self.traffic.any_traffic_loss(tolerance=constants.TRAFFIC_TOLERANCE):
            raise TestRunError('Traffic is flowing with packet loss', err_details='Low traffic flew with packet loss')

        self.tc_result['scaling_out']['traffic_after'] = 'LOW_TRAFFIC_LOAD'

        LOG.info('%s execution completed successfully' % self.tc_name)
