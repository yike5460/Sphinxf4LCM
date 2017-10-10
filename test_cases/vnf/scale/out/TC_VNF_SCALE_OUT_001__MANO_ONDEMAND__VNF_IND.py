import logging
import time

from api.generic import constants
from api.generic.mano import Mano
from api.generic.traffic import Traffic
from test_cases import TestCase, TestRunError
from utils.misc import generate_name

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNF_SCALE_OUT_001__MANO_ONDEMAND__VNF_IND(TestCase):
    """
    TC_VNF_SCALE_OUT_001__MANO_ONDEMAND__VNF_IND Scale-out VNF instance with on-demand scaling event generated by MANO.
    The stimulus for scaling out consists of value changes of one or multiple VNF related indicators on the interface
    produced by the VNF.

    Sequence:
    1. Instantiate the NS
    2. Validate NS state is INSTANTIATED
    3. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
    4. Start the low traffic load
    5. Validate the provided functionality and all traffic goes through
    6. Trigger a resize of the NS resources by altering a VNF indicator
    7. Validate NS has resized by adding VNFs
    8. Determine if and length of service disruption
    9. Validate increased capacity without loss
    """

    required_elements = ('mano', 'traffic', 'nsd_id', 'scaling_policy_name')

    def setup(self):
        LOG.info('Starting setup for TC_VNF_SCALE_OUT_001__MANO_ONDEMAND__VNF_IND')

        # Create objects needed by the test.
        self.mano = Mano(vendor=self.tc_input['mano']['type'], **self.tc_input['mano']['client_config'])
        self.traffic = Traffic(self.tc_input['traffic']['type'], **self.tc_input['traffic']['client_config'])
        self.register_for_cleanup(index=10, function_reference=self.traffic.destroy)

        # Initialize test case result.
        self.tc_result['events']['instantiate_ns'] = dict()
        self.tc_result['events']['scale_out_ns'] = dict()
        self.tc_result['events']['service_disruption'] = dict()

        LOG.info('Finished setup for TC_VNF_SCALE_OUT_001__MANO_ONDEMAND__VNF_IND')

    def run(self):
        LOG.info('Starting TC_VNF_SCALE_OUT_001__MANO_ONDEMAND__VNF_IND')

        # Get scaling policy properties
        sp = self.mano.get_nsd_scaling_properties(self.tc_input['nsd_id'], self.tc_input['scaling_policy_name'])

        # --------------------------------------------------------------------------------------------------------------
        # 1. Instantiate the NS
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

        self.register_for_cleanup(index=20, function_reference=self.mano.ns_terminate_and_delete,
                                  ns_instance_id=self.ns_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 2. Validate NS state is INSTANTIATED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating NS state is INSTANTIATED')
        ns_info = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id})
        if ns_info.ns_state != constants.NS_INSTANTIATED:
            raise TestRunError('Unexpected NS state',
                               err_details='NS state was not "%s" after the NS was instantiated'
                                           % constants.NS_INSTANTIATED)

        # --------------------------------------------------------------------------------------------------------------
        # 3. Validate VNF instantiation state is INSTANTIATED and VNF state is STARTED
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

        self.tc_result['resources']['Initial'] = self.mano.get_allocated_vresources(
                                                                                  self.vnf_instance_id,
                                                                                  self.tc_input['mano']['query_params'])

        # --------------------------------------------------------------------------------------------------------------
        # 4. Start the low traffic load
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

        self.register_for_cleanup(index=30, function_reference=self.traffic.stop)

        # --------------------------------------------------------------------------------------------------------------
        # 5. Validate the provided functionality and all traffic goes through
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating the provided functionality and all traffic goes through')
        if not self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is not flowing', err_details='Low traffic did not flow')

        if self.traffic.any_traffic_loss(tolerance=constants.traffic_tolerance):
            raise TestRunError('Traffic is flowing with packet loss', err_details='Low traffic flew with packet loss')

        self.tc_result['scaling_out']['traffic_before'] = 'LOW_TRAFFIC_LOAD'

        if not self.mano.validate_allocated_vresources(self.tc_input['vnfd_id'], self.vnf_instance_id,
                                                       self.tc_input['mano']['query_params']):
            raise TestRunError('Allocated vResources could not be validated')

        # --------------------------------------------------------------------------------------------------------------
        # 6. Trigger a resize of the NS resources by altering a VNF indicator
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering a resize of the NS resources by altering a VNF indicator')

        # The scale out is triggered by a VNF related indicator value change.
        # The VNF exposed interface Ve-Vnfm-Vnf will enable the MANO to trigger a scale out based on VNF Indicator
        # value changes. VNF related indicators are declared in the VNFD.
        # There are 2 ways for MANO to obtain VNF Indicator information:
        # - by GetIndicatorValue operation on the Ve-Vnfm-Vnf interface
        # - by subscribing for notifications related to VNF Indicator value changes with the VNF.
        # The two operations involved are Subscribe and Notify.

        # TODO: Insert here code to:
        # 1. alter the VNF related indicators so that MANO can trigger an NS scale out
        # 2. check that MANO has subscribed to VNF
        # 3. subscribe to VNF and check the notifications
        # For now we use only traffic load to trigger the scale out (we will increase the traffic load to the maximum).
        self.traffic.config_traffic_load('MAX_TRAFFIC_LOAD')

        # --------------------------------------------------------------------------------------------------------------
        # 7. Validate NS has resized by adding VNFs
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating NS has resized by adding VNFs')
        # The scale out duration will include:
        # - the time it takes the VNF CPU load to increase (caused by the max traffic load)
        # - the time after which the scaling alarm is triggered
        # - the time it takes the NS to scale out
        self.time_record.START('scale_out_ns')
        elapsed_time = 0
        while elapsed_time < constants.SCALE_INTERVAL:
            ns_info = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id})
            if len(ns_info.vnf_info_id) == sp['default_instances'] + sp['increment']:
                break
            else:
                time.sleep(constants.POLL_INTERVAL)
                elapsed_time += constants.POLL_INTERVAL
            if elapsed_time == constants.SCALE_INTERVAL:
                self.tc_result['scaling_out']['status'] = 'Fail'
                raise TestRunError('VNFs not added after traffic load was increased to the maximum')

        self.time_record.END('scale_out_ns')

        self.tc_result['events']['scale_out_ns']['duration'] = self.time_record.duration('scale_out_ns')

        self.tc_result['resources']['After scale out'] = dict()
        for vnf_instance_id in ns_info.vnf_info_id:
            self.tc_result['resources']['After scale out'].update(
                self.mano.get_allocated_vresources(vnf_instance_id, self.tc_input['mano']['query_params']))

        self.tc_result['scaling_out']['level'] = sp['default_instances'] + sp['increment']

        self.tc_result['scaling_out']['status'] = 'Success'

        # --------------------------------------------------------------------------------------------------------------
        # 8. Determine if and length of service disruption
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Determining if and length of service disruption')
        self.tc_result['events']['service_disruption']['duration'] = self.traffic.calculate_service_disruption_length()

        # --------------------------------------------------------------------------------------------------------------
        # 9. Validate increased capacity without loss
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating increased capacity without loss')
        # Because the NS scaled out, we need to reconfigure traffic so that it passes through all VNFs.

        # Stop the max traffic load.
        self.traffic.stop()

        # Configure stream destination address(es).
        dest_addr_list = ''
        for vnf_instance_id in ns_info.vnf_info_id:
            vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': vnf_instance_id,
                                                   'additional_param': self.tc_input['mano']['query_params']})
            for ext_cp_info in vnf_info.instantiated_vnf_info.ext_cp_info:
                if ext_cp_info.cpd_id == self.tc_input['traffic']['traffic_config']['ingress_cp_name']:
                    dest_addr_list += ext_cp_info.address[0] + ' '

        self.traffic.config_traffic_stream(dest_addr_list)
        self.traffic.clear_counters()

        # Start the max traffic load.
        self.traffic.start(return_when_emission_starts=True)

        if not self.traffic.does_traffic_flow(delay_time=5):
            raise TestRunError('Traffic is not flowing', err_details='Max traffic did not flow')

        if self.traffic.any_traffic_loss(tolerance=constants.traffic_tolerance):
            raise TestRunError('Traffic is flowing with packet loss', err_details='Max traffic flew with packet loss')

        self.tc_result['scaling_out']['traffic_after'] = 'MAX_TRAFFIC_LOAD'

        LOG.info('TC_VNF_SCALE_OUT_001__MANO_ONDEMAND__VNF_IND execution completed successfully')
