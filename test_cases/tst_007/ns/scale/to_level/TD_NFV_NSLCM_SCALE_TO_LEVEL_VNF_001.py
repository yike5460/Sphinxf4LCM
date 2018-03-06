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
from api.structures.objects import ScaleVnfData, ScaleToLevelData
from test_cases import TestCase, TestRunError
from utils.misc import generate_name
from utils.net import ping

# Instantiate logger
LOG = logging.getLogger(__name__)


class TD_NFV_NSLCM_SCALE_TO_LEVEL_VNF_001(TestCase):
    """
    TD_NFV_NSLCM_SCALE_TO_LEVEL_VNF_001 Verify that a VNF in a NS can be successfully scaled to an instantiation level
    when triggered by a NFVO operator

    Sequence:
    1. Trigger NS instantiation on the NFVO
    2. Verify that the NFVO indicates NS instantiation operation result as successful
    3. Trigger NS scale by scaling to another existing instantiation level a VNF in the NS in NFVO with an operator
       action
    4. Verify that the number of VNFC instance(s) has changed for the VNF by querying the VNFM
    5. Verify that the resources allocated by the VIM have changed according to the descriptors
    6. Verify that all VNFC instance(s) are running and reachable via the management network
    7. Verify that the VNF configuration has been updated according to the descriptors by querying the VNFM
    8. Verify that all VNFC instance(s) are connected to the VL(s) according to the descriptors
    9. Verify that the NFVO indicates the scaling operation result as successful
    10. Verify that NS has been scaled by running the end-to-end functional test in relevance to the VNF scale and
        capacity
    """

    REQUIRED_APIS = ('mano', 'traffic')
    REQUIRED_ELEMENTS = ('nsd_id', 'scale_to_level_list')
    TESTCASE_EVENTS = ('instantiate_ns', 'scale_to_level_ns')

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

        if self.ns_instance_id is None:
            raise TestRunError('NS instantiation operation failed')

        self.time_record.END('instantiate_ns')

        self.tc_result['events']['instantiate_ns']['duration'] = self.time_record.duration('instantiate_ns')
        self.tc_result['events']['instantiate_ns']['details'] = 'Success'

        sleep(constants.INSTANCE_BOOT_TIME)

        self.register_for_cleanup(index=10, function_reference=self.mano.ns_terminate_and_delete,
                                  ns_instance_id=self.ns_instance_id,
                                  terminate_time=self.tc_input.get('terminate_time'),
                                  additional_param=self.tc_input['mano'].get('termination_params'))
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

        for vnf_info in ns_info.vnf_info:
            self.tc_result['resources']['%s (Before scale to level)' % vnf_info.vnf_product_name] = dict()
            self.tc_result['resources']['%s (Before scale to level)' % vnf_info.vnf_product_name].update(
                self.mano.get_allocated_vresources(vnf_info.vnf_instance_id, self.tc_input['mano'].get('query_params')))

        # --------------------------------------------------------------------------------------------------------------
        # 3. Trigger NS scale by scaling to another existing instantiation level a VNF in the NS in NFVO with an
        #    operator action
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering NS scale by scaling to another existing instantiation level a VNF in the NS in NFVO with '
                 'an operator action')
        scale_vnf_data_list = list()
        for scale_to_level in self.tc_input['scale_to_level_list']:
            vnf_name = scale_to_level['target_vnf_name']
            instantiation_level_id = scale_to_level['target_instantiation_level_id']
            # Build the ScaleVnfData information element
            scale_vnf_data = ScaleVnfData()
            scale_vnf_data.vnf_instance_id = vnf_name
            scale_vnf_data.type = 'to_instantiation_level'
            scale_vnf_data.scale_to_level_data = ScaleToLevelData()
            scale_vnf_data.scale_to_level_data.instantiation_level_id = instantiation_level_id
            scale_vnf_data.scale_to_level_data.additional_param = self.tc_input['mano'].get('scale_params')

            scale_vnf_data_list.append(scale_vnf_data)

        self.time_record.START('scale_to_level_ns')
        if self.mano.ns_scale_sync(self.ns_instance_id, scale_type='SCALE_VNF', scale_vnf_data=scale_vnf_data_list,
                                   scale_time=self.tc_input.get('scale_time')) \
                != constants.OPERATION_SUCCESS:
            self.tc_result['scaling_to_level']['status'] = 'Fail'
            raise TestRunError('MANO could not scale to level the NS')

        self.time_record.END('scale_to_level_ns')

        self.tc_result['events']['scale_to_level_ns']['duration'] = self.time_record.duration('scale_to_level_ns')
        self.tc_result['events']['scale_to_level_ns']['details'] = 'Success'

        sleep(constants.INSTANCE_BOOT_TIME)

        # --------------------------------------------------------------------------------------------------------------
        # 4. Verify that the number of VNFC instance(s) has changed for the VNF by querying the VNFM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the number of VNFC instance(s) has changed for the VNF by querying the VNFM')
        ns_info = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id,
                                             'additional_param': self.tc_input['mano'].get('query_params')})
        if not self.mano.validate_ns_instantiation_level(ns_info, self.tc_input['scale_to_level_list'],
                                                         self.tc_input['mano'].get('scale_params')):
            raise TestRunError('Incorrect number of VNFCs')

        for vnf_info in ns_info.vnf_info:
            self.tc_result['resources']['%s (After scale to level)' % vnf_info.vnf_product_name] = dict()
            self.tc_result['resources']['%s (After scale to level)' % vnf_info.vnf_product_name].update(
                self.mano.get_allocated_vresources(vnf_info.vnf_instance_id, self.tc_input['mano'].get('query_params')))

        # TODO Add self.tc_result['scaling_to_level']['level']. We should do this only for the VNF(s) that we scaled

        self.tc_result['scaling_to_level']['status'] = 'Success'

        # --------------------------------------------------------------------------------------------------------------
        # 5. Verify that the resources allocated by the VIM have changed according to the descriptors
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the resources allocated by the VIM have changed according to the descriptors')
        if not self.mano.validate_ns_allocated_vresources(self.ns_instance_id,
                                                          self.tc_input['mano'].get('query_params')):
            raise TestRunError('Allocated vResources could not be validated')

        # --------------------------------------------------------------------------------------------------------------
        # 6. Verify that all VNFC instance(s) are running and reachable via the management network
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that all VNFC instance(s) are running and reachable via the management network')
        for vnf_info in ns_info.vnf_info:
            mgmt_addr_list = self.mano.get_vnf_mgmt_addr_list(vnf_info.vnf_instance_id,
                                                              self.tc_input['mano'].get('query_params'))
            for mgmt_addr in mgmt_addr_list:
                if not ping(mgmt_addr):
                    raise TestRunError('Unable to PING IP address %s belonging to VNF %s'
                                       % (mgmt_addr, vnf_info.vnf_product_name))

        # --------------------------------------------------------------------------------------------------------------
        # 7. Verify that the VNF configuration has been updated according to the descriptors by querying the VNFM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verify that the VNF configuration has been updated according to the descriptors by querying the VNFM')
        # TODO

        # --------------------------------------------------------------------------------------------------------------
        # 8. Verify that all VNFC instance(s) are connected to the VL(s) according to the descriptors
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that all VNFC instance(s) are connected to the VL(s) according to the descriptors')
        # TODO

        # --------------------------------------------------------------------------------------------------------------
        # 9. Verify that the NFVO indicates the scaling operation result as successful
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NFVO indicates the scaling operation result as successful')
        LOG.debug('This has implicitly been checked at step 3')

        # --------------------------------------------------------------------------------------------------------------
        # 10. Verify that NS has been scaled by running the end-to-end functional test in relevance to the VNF scale and
        #     capacity
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verify that NS has been scaled by running the end-to-end functional test in relevance to the VNF '
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
        if not self.traffic.does_traffic_flow(delay_time=60):
            raise TestRunError('Traffic is not flowing', err_details='Normal traffic did not flow')

        # Clearing counters so that any packets lost so far don't influence the results
        self.traffic.clear_counters()

        if self.traffic.any_traffic_loss(delay_time=constants.TRAFFIC_DELAY_TIME,
                                         tolerance=constants.TRAFFIC_TOLERANCE):
            raise TestRunError('Traffic is flowing with packet loss',
                               err_details='Normal traffic flew with packet loss')

        self.tc_result['scaling_to_level']['traffic_after'] = 'NORMAL_TRAFFIC_LOAD'

        LOG.info('%s execution completed successfully' % self.tc_name)
