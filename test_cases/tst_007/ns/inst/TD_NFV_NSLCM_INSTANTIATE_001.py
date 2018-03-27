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
from test_cases import TestCase, TestRunError
from utils.misc import generate_name
from utils.net import ping

# Instantiate logger
LOG = logging.getLogger(__name__)


class TD_NFV_NSLCM_INSTANTIATE_001(TestCase):
    """
    TD_NFV_NSLCM_INSTANTIATE_001 Verify that a standalone NS can be successfully instantiated

    Sequence:
    1. Trigger NS instantiation on the NFVO
    2. Verify that the software images have been successfully added to the image repository managed by the VIM
    3. Verify that the requested resources have been allocated by the VIM according to the descriptors
    4. Verify that the VNF instance(s) have been deployed according to the NSD (i.e. query the VIM and VNFM for VMs,
       VLs and CPs)
    5. Verify that the VNF instance(s) are reachable via the management network
    6. Verify that the VNF instance(s) have been configured according to the VNFD(s) by querying the VNFM
    7. Verify that the VNF instance(s), VL(s) and VNFFG(s) have been connected according to the descriptors
    8. Verify that the NFVO indicates NS instantiation operation result as successful
    9. Verify that the NS is successfully instantiated by running the end-to-end functional test
    10. Trigger the termination of the NS instance on the NFVO
    11. Verify that the NS is terminated and that all resources have been released by the VIM
    """

    REQUIRED_APIS = ('mano', 'traffic')
    REQUIRED_ELEMENTS = ('nsd_id',)
    TESTCASE_EVENTS = ('instantiate_ns', 'terminate_ns')

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

        sleep(constants.INSTANCE_FIRST_BOOT_TIME)

        self.register_for_cleanup(index=10, function_reference=self.mano.ns_terminate_and_delete,
                                  ns_instance_id=self.ns_instance_id,
                                  terminate_time=self.tc_input.get('terminate_time'),
                                  additional_param=self.tc_input['mano'].get('termination_params'))
        self.register_for_cleanup(index=20, function_reference=self.mano.wait_for_ns_stable_state,
                                  ns_instance_id=self.ns_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 2. Verify that the software images have been successfully added to the image repository managed by the VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the software images have been successfully added to the image repository managed by '
                 'the VIM')
        if not self.mano.verify_ns_sw_images(self.ns_instance_id, self.tc_input['mano'].get('query_params')):
            raise TestRunError('Not all VNFCs use the correct images')

        # --------------------------------------------------------------------------------------------------------------
        # 3. Verify that the requested resources have been allocated by the VIM according to the descriptors
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the requested resources have been allocated by the VIM according to the descriptors')
        if not self.mano.validate_ns_allocated_vresources(self.ns_instance_id,
                                                          self.tc_input['mano'].get('query_params')):
            raise TestRunError('Allocated vResources could not be validated')

        ns_info = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id,
                                             'additional_param': self.tc_input['mano'].get('query_params')})
        for vnf_info in ns_info.vnf_info:

            self.tc_result['resources']['%s (Initial)' % vnf_info.vnf_product_name] = dict()
            self.tc_result['resources']['%s (Initial)' % vnf_info.vnf_product_name].update(
                self.mano.get_allocated_vresources(vnf_info.vnf_instance_id, self.tc_input['mano'].get('query_params')))

        # --------------------------------------------------------------------------------------------------------------
        # 4. Verify that the VNF instance(s) have been deployed according to the NSD
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the VNF instance(s) have been deployed according to the NSD')
        if not self.mano.verify_vnf_nsd_mapping(self.ns_instance_id, self.tc_input['mano'].get('query_params')):
            raise TestRunError('VNF instance(s) have not been deployed according to the NSD')

        # --------------------------------------------------------------------------------------------------------------
        # 5. Verify that the VNF instance(s) are reachable via the management network
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the VNF instance(s) are reachable via the management network')
        for vnf_info in ns_info.vnf_info:
            mgmt_addr_list = self.mano.get_vnf_mgmt_addr_list(vnf_info.vnf_instance_id,
                                                              self.tc_input['mano'].get('query_params'))
            for mgmt_addr in mgmt_addr_list:
                if not ping(mgmt_addr):
                    raise TestRunError('Unable to PING IP address %s belonging to VNF %s'
                                       % (mgmt_addr, vnf_info.vnf_product_name))

        # --------------------------------------------------------------------------------------------------------------
        # 6. Verify that the VNF instance(s) have been configured according to the VNFD(s) by querying the VNFM
        # --------------------------------------------------------------------------------------------------------------
        # LOG.info('Verifying that the VNF instance(s) have been configured according to the VNFD(s) by querying the '
        #          'VNFM')
        # TODO (compare config file with vnf config; call adapter; adapter function body can be a noop)

        # --------------------------------------------------------------------------------------------------------------
        # 7. Verify that the VNF instance(s), VL(s) and VNFFG(s) have been connected according to the descriptors
        # --------------------------------------------------------------------------------------------------------------
        # LOG.info('Verifying that the VNF instance(s), VL(s) and VNFFG(s) have been connected according to the '
        #          'descriptors')
        # TODO (don't do the validation for Tacker; do the validation in the case of Cisco NSO; this step is not the
        # TODO highest priority at the moment)

        # --------------------------------------------------------------------------------------------------------------
        # 8. Verify that the NFVO indicates NS instantiation operation result as successful
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NFVO indicates NS instantiation operation result as successful')
        if ns_info.ns_state != constants.NS_INSTANTIATED:
            raise TestRunError('Unexpected NS state',
                               err_details='NS state was not "%s" after the NS was instantiated'
                                           % constants.NS_INSTANTIATED)

        # --------------------------------------------------------------------------------------------------------------
        # 9. Verify that the NS is successfully instantiated by running the end-to-end functional test
        # --------------------------------------------------------------------------------------------------------------
        if 'left_port_vnf' in self.tc_input['traffic']['traffic_config']:
            for vnf_info in ns_info.vnf_info:
                if vnf_info.vnf_product_name == self.tc_input['traffic']['traffic_config']['left_port_vnf']:
                    dest_addr = self.mano.get_vnf_mgmt_addr_list(vnf_info.vnf_instance_id,
                                                                 self.tc_input['mano'].get('query_params'))[0]
                    self.tc_input['traffic']['traffic_config']['left_port_location'] = dest_addr + \
                                                                                       self.tc_input['traffic'][
                                                                                           'traffic_config'][
                                                                                           'left_port_location']

        if 'right_port_vnf' in self.tc_input['traffic']['traffic_config']:
            for vnf_info in ns_info.vnf_info:
                if vnf_info.vnf_product_name == self.tc_input['traffic']['traffic_config']['right_port_vnf']:
                    dest_addr = self.mano.get_vnf_mgmt_addr_list(vnf_info.vnf_instance_id,
                                                                 self.tc_input['mano'].get('query_params'))[0]
                    self.tc_input['traffic']['traffic_config']['right_port_location'] = dest_addr + \
                                                                                       self.tc_input['traffic'][
                                                                                           'traffic_config'][
                                                                                           'right_port_location']

        LOG.info('Verifying that the NS is successfully instantiated by running the end-to-end functional test')
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

        if not self.traffic.does_traffic_flow(delay_time=constants.TRAFFIC_STABILIZATION_TIME):
            raise TestRunError('Traffic is not flowing', err_details='Normal traffic did not flow')

        if self.traffic.any_traffic_loss(tolerance=constants.TRAFFIC_TOLERANCE):
            raise TestRunError('Traffic is flowing with packet loss',
                               err_details='Normal traffic flew with packet loss')

        # --------------------------------------------------------------------------------------------------------------
        # 10. Trigger the termination of the NS instance on the NFVO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering the termination of the NS instance on the NFVO')
        self.time_record.START('terminate_ns')
        if self.mano.ns_terminate_sync(ns_instance_id=self.ns_instance_id,
                                       terminate_time=self.tc_input.get('terminate_time'),
                                       additional_param=self.tc_input['mano'].get('termination_params')) != \
                constants.OPERATION_SUCCESS:
            raise TestRunError('Unexpected status for NS termination operation',
                               err_details='NS termination operation failed')

        self.time_record.END('terminate_ns')

        self.tc_result['events']['terminate_ns']['duration'] = self.time_record.duration('terminate_ns')
        self.tc_result['events']['terminate_ns']['details'] = 'Success'

        self.unregister_from_cleanup(index=20)
        self.unregister_from_cleanup(index=10)

        self.register_for_cleanup(index=10, function_reference=self.mano.ns_delete_id,
                                  ns_instance_id=self.ns_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 11. Verify that the NS is terminated and that all resources have been released by the VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NS is terminated')
        ns_info_final = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id,
                                                   'additional_param': self.tc_input['mano'].get('query_params')})
        if ns_info_final.ns_state != constants.NS_NOT_INSTANTIATED:
            raise TestRunError('Unexpected NS instantiation state',
                               err_details='NS instantiation state was not "%s" after the NS was terminated'
                                           % constants.NS_NOT_INSTANTIATED)

        LOG.info('Verifying that all the VNF instance(s) have been terminated')
        for vnf_info in ns_info.vnf_info:
            vnf_instance_id = vnf_info.vnf_instance_id
            vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': vnf_instance_id,
                                                   'additional_param': self.tc_input['mano'].get('query_params')})
            if vnf_info.instantiation_state != constants.VNF_NOT_INSTANTIATED:
                raise TestRunError(
                    'VNF instance was not terminated correctly. VNF instance ID %s expected state was %s but got %s'
                    % (vnf_instance_id, constants.VNF_NOT_INSTANTIATED, vnf_info.instantiation_state))

        LOG.info('Verifying that all resources have been released by the VIM')
        if not self.mano.validate_ns_released_vresources(ns_info):
            raise TestRunError('Allocated resources have not been released by the VIM')

        LOG.info('%s execution completed successfully' % self.tc_name)
