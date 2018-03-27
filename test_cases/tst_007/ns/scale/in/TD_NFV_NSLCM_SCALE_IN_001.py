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
from api.structures.objects import ScaleNsData, ScaleNsByStepsData
from time import sleep
from test_cases import TestCase, TestRunError
from utils.misc import generate_name
from utils.net import ping

# Instantiate logger
LOG = logging.getLogger(__name__)


class TD_NFV_NSLCM_SCALE_IN_001(TestCase):
    """
    TD_NFV_NSLCM_SCALE_IN_001 Verify that the NS can be successfully scaled in by removing VNF instances triggered by an
    operator action

    Sequence:
    1. Trigger NS instantiation on the NFVO
    2. Verify that the NFVO indicates NS instantiation operation result as successful
    3. Trigger NS scale out by adding VNF instances to the NS in NFVO with an operator action
    4. Verify that the additional VNF instance(s) have been deployed by querying the VNFM
    5. Trigger NS scale in by removing VNF instances from the NS in NFVO with an operator action
    6. Verify that the impacted VNF instance(s) have been terminated by querying the VNFM
    7. Verify that the impacted VNF related resources have been released by the VIM
    8. Verify that the remaining VNF instances(s) are still running and reachable via their management network
    9. Verify that the remaining VNF instances(s), VL(s) and VNFFG(s) are still connected according to the descriptors
    10. Verify that the NFVO indicates the scaling operation result as successful
    11. Verify that NS has been scaled in by running the end-to-end functional test factoring the VNF scale and capacity
    """

    REQUIRED_APIS = ('mano', 'traffic')
    REQUIRED_ELEMENTS = ('nsd_id', )
    TESTCASE_EVENTS = ('instantiate_ns', 'scale_out_ns', 'scale_in_ns')

    def run(self):
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

        self.register_for_cleanup(index=10, function_reference=self.mano.ns_terminate_and_delete,
                                  ns_instance_id=self.ns_instance_id,
                                  terminate_time=self.tc_input.get('terminate_time'))
        self.register_for_cleanup(index=20, function_reference=self.mano.wait_for_ns_stable_state,
                                  ns_instance_id=self.ns_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 2. Verify that the NFVO indicates NS instantiation operation result as successful
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NFVO indicates NS instantiation operation result as successful')
        ns_info = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id,
                                             'additional_param': self.tc_input['mano'].get('query_params')})
        if ns_info.ns_state != constants.NS_INSTANTIATED:
            raise TestRunError('Unexpected NS state',
                               err_details='NS state was not "%s" after the NS was instantiated'
                                           % constants.NS_INSTANTIATED)

        # --------------------------------------------------------------------------------------------------------------
        # 3. Trigger NS scale out by adding VNF instances to the NS in NFVO with an operator action
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering NS scale out by adding VNF instances to the NS in NFVO with an operator action')
        scale_ns_data = ScaleNsData()
        scale_ns_data.scale_ns_by_steps_data = ScaleNsByStepsData()
        scale_ns_data.scale_ns_by_steps_data.scaling_direction = 'scale_out'
        scale_ns_data.scale_ns_by_steps_data.aspect_id = self.tc_input.get('aspect_id', '')
        scale_ns_data.scale_ns_by_steps_data.number_of_steps = 1
        scale_ns_data.additional_param_for_ns = self.tc_input['mano'].get('scale_params')

        self.time_record.START('scale_out_ns')
        if self.mano.ns_scale_sync(self.ns_instance_id, scale_type='SCALE_NS', scale_ns_data=scale_ns_data,
                                   scale_time=self.tc_input.get('scale_time')) \
                != constants.OPERATION_SUCCESS:
            self.tc_result['scaling_out']['status'] = 'Fail'
            raise TestRunError('MANO could not scale out the NS')

        self.time_record.END('scale_out_ns')

        self.tc_result['events']['scale_out_ns']['duration'] = self.time_record.duration('scale_out_ns')
        self.tc_result['events']['scale_out_ns']['details'] = 'Success'

        sleep(constants.INSTANCE_FIRST_BOOT_TIME)

        # --------------------------------------------------------------------------------------------------------------
        # 4. Verify that the additional VNF instance(s) have been deployed by querying the VNFM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the additional VNF instance(s) have been deployed by querying the VNFM')
        if not self.mano.verify_ns_vnf_instance_count(ns_instance_id=self.ns_instance_id,
                                                      aspect_id=self.tc_input.get('aspect_id', ''),
                                                      additional_param=self.tc_input['mano'].get('scale_params')):
            raise TestRunError('Incorrect number of VNF instances after NS scale out')

        # --------------------------------------------------------------------------------------------------------------
        # 5. Trigger NS scale in by removing VNF instances from the NS in NFVO with an operator action
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering NS scale in by removing VNF instances from the NS in NFVO with an operator action')
        scale_ns_data = ScaleNsData()
        scale_ns_data.scale_ns_by_steps_data = ScaleNsByStepsData()
        scale_ns_data.scale_ns_by_steps_data.scaling_direction = 'scale_in'
        scale_ns_data.scale_ns_by_steps_data.aspect_id = self.tc_input.get('aspect_id', '')
        scale_ns_data.scale_ns_by_steps_data.number_of_steps = 1
        scale_ns_data.additional_param_for_ns = self.tc_input['mano'].get('scale_params')

        self.time_record.START('scale_in_ns')
        if self.mano.ns_scale_sync(self.ns_instance_id, scale_type='SCALE_NS', scale_ns_data=scale_ns_data,
                                   scale_time=self.tc_input.get('scale_time')) \
                != constants.OPERATION_SUCCESS:
            self.tc_result['scaling_in']['status'] = 'Fail'
            raise TestRunError('MANO could not scale in the NS')

        self.time_record.END('scale_in_ns')

        self.tc_result['events']['scale_in_ns']['duration'] = self.time_record.duration('scale_in_ns')
        self.tc_result['events']['scale_in_ns']['details'] = 'Success'

        # --------------------------------------------------------------------------------------------------------------
        # 6. Verify that the impacted VNF instance(s) have been terminated by querying the VNFM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the impacted VNF instance(s) have been terminated by querying the VNFM')
        if not self.mano.verify_ns_vnf_instance_count(ns_instance_id=self.ns_instance_id,
                                                      aspect_id=self.tc_input.get('aspect_id', ''),
                                                      additional_param=self.tc_input['mano'].get('scale_params')):
            raise TestRunError('Incorrect number of VNF instances after NS scale in')

        # --------------------------------------------------------------------------------------------------------------
        # 7. Verify that the impacted VNF related resources have been released by the VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the impacted VNF related resources have been released by the VIM')
        if not self.mano.validate_ns_allocated_vresources(self.ns_instance_id,
                                                          self.tc_input['mano'].get('query_params')):
            raise TestRunError('Allocated vResources could not be validated')

        # --------------------------------------------------------------------------------------------------------------
        # 8. Verify that the remaining VNF instances(s) are still running and reachable via their management network
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the remaining VNF instances(s) are still running and reachable via their management '
                 'network')
        for vnf_info in ns_info.vnf_info:
            mgmt_addr_list = self.mano.get_vnf_mgmt_addr_list(vnf_info.vnf_instance_id)
            for mgmt_addr in mgmt_addr_list:
                if not ping(mgmt_addr):
                    raise TestRunError('Unable to PING IP address %s belonging to %s'
                                       % (mgmt_addr, vnf_info.vnf_product_name))

        # --------------------------------------------------------------------------------------------------------------
        # 9. Verify that the remaining VNF instances(s), VL(s) and VNFFG(s) are still connected according to the
        #    descriptors
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the remaining VNF instances(s), VL(s) and VNFFG(s) are still connected according to '
                 'the descriptors')
        # TODO

        # --------------------------------------------------------------------------------------------------------------
        # 10. Verify that the NFVO indicates the scaling operation result as successful
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NFVO indicates the scaling operation result as successful')
        LOG.debug('This has implicitly been checked at step 3')

        # --------------------------------------------------------------------------------------------------------------
        # 11. Verify that NS has been scaled in by running the end-to-end functional test factoring the VNF scale and
        #     capacity
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that NS has been scaled in by running the end-to-end functional test factoring the VNF '
                 'scale and capacity')
        self.traffic.configure(traffic_load='NORMAL_TRAFFIC_LOAD',
                               traffic_config=self.tc_input['traffic']['traffic_config'])

        self.register_for_cleanup(index=30, function_reference=self.traffic.destroy)

        # Configure stream destination address(es)
        dest_addr_list = self.mano.get_ns_ingress_cp_addr_list(
                                                          ns_info,
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

        self.tc_result['scaling_out']['traffic_after'] = 'NORMAL_TRAFFIC_LOAD'

        LOG.info('%s execution completed successfully' % self.tc_name)
