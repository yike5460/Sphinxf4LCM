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
from api.structures.objects import ChangeVnfFlavourData
from test_cases import TestCase, TestRunError
from utils.misc import generate_name
from utils.net import ping

# Instantiate logger
LOG = logging.getLogger(__name__)


class TD_NFV_NSLCM_UPDATE_VNF_DF_001(TestCase):
    """
    TD_NFV_NSLCM_UPDATE_VNF_DF_001 To verify that the deployment flavor of one or more VNF instances in a NS instance
    can be changed.

    Sequence:
    1.  Trigger NS instantiation on the NFVO
    2.  Verify that the NS is instantiated
    3.  Trigger a NS update changing the deployment flavour (DF) of one or more VNF instances in a NS instance on NFVO
    4.  Verify that the virtualised resources have been updated by the VIM according to the new deployment flavor
    5.  Verify that the impacted VNF instance(s) are running and reachable through the management network
    6.  Verify that the NFVO indicates the VNF DF update operation as successful
    7.  Verify that the NS has been updated by runnning the end-to-end functional test factoring the new VNF DF
    """

    REQUIRED_APIS = ('mano', 'traffic')
    REQUIRED_ELEMENTS = ('nsd_id', 'operate_vnf_data')
    TESTCASE_EVENTS = ('instantiate_ns', 'ns_update_vnf_df')

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

        # self.register_for_cleanup(index=10, function_reference=self.mano.ns_terminate_and_delete,
        #                           ns_instance_id=self.ns_instance_id,
        #                           terminate_time=self.tc_input.get('terminate_time'),
        #                           additional_param=self.tc_input['mano'].get('termination_params'))
        # self.register_for_cleanup(index=20, function_reference=self.mano.wait_for_ns_stable_state,
        #                           ns_instance_id=self.ns_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 2. Verify that the NS is instantiated
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating NS instantiation state is INSTANTIATED')
        ns_info = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id,
                                             'additional_param': self.tc_input['mano'].get('query_params')})
        if ns_info.ns_state != constants.NS_INSTANTIATED:
            raise TestRunError('Unexpected NS instantiation state',
                               err_details='NS instantiation state was not "%s" after the NS was instantiated'
                                           % constants.NS_INSTANTIATED)

        for vnf_info in ns_info.vnf_info:
            self.tc_result['resources']['%s (Initial)' % vnf_info.vnf_product_name] = dict()
            self.tc_result['resources']['%s (Initial)' % vnf_info.vnf_product_name].update(
                self.mano.get_allocated_vresources(vnf_info.vnf_instance_id, self.tc_input['mano'].get('query_params')))

        # --------------------------------------------------------------------------------------------------------------
        # 3. Trigger a NS update changing the deployment flavour (DF) of one or more VNF instances in a NS instance on
        #    NFVO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering the NFVO to change the deployment flavour of the target VNF instance inside the NS')
        change_vnf_flavour_data_list = list()
        for vnf_info in ns_info.vnf_info:
            if vnf_info.vnf_product_name in self.tc_input.get('change_vnf_deployment_flavour').get('vnfs').keys():
                change_vnf_flavour_data = ChangeVnfFlavourData()
                change_vnf_flavour_data.vnf_instance_id = vnf_info.vnf_instance_id
                change_vnf_flavour_data.new_flavour_id = self.tc_input.get('change_vnf_deployment_flavour').\
                    get('vnfs').get(vnf_info.vnf_product_name).get('new_flavour_id')
                change_vnf_flavour_data.instantiation_level_id = self.tc_input.get('change_vnf_deployment_flavour').\
                    get('vnfs').get(vnf_info.vnf_product_name).get('instantiation_level_id')
                change_vnf_flavour_data.additional_param = self.tc_input.get('change_vnf_deployment_flavour').get(
                    'additional_param')
                change_vnf_flavour_data_list.append(change_vnf_flavour_data)

        self.time_record.START('ns_update_vnf_df')

        if self.mano.ns_update_sync(ns_instance_id=self.ns_instance_id, update_type='ChangeVnfDf',
                                    change_vnf_flavour_data=change_vnf_flavour_data_list) != \
                                    constants.OPERATION_SUCCESS:
            raise TestRunError('Unexpected status for NS update operation',
                               err_details='NS update operation failed')

        self.time_record.END('ns_update_vnf_df')

        self.tc_result['events']['ns_update_vnf_df']['duration'] = self.time_record.duration('ns_update_vnf_df')
        self.tc_result['events']['ns_update_vnf_df']['details'] = 'Success'

        # --------------------------------------------------------------------------------------------------------------
        # 4. Verify that the virtualised resources have been updated by the VIM according to the new deployment flavor
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the virtualised resources have been updated by the VIM according to the new deployment'
                 ' flavour')
        if not self.mano.validate_ns_allocated_vresources(self.ns_instance_id,
                                                          self.tc_input['mano'].get('query_params')):
            raise TestRunError('Allocated vResources could not be validated')

        # --------------------------------------------------------------------------------------------------------------
        # 5. Verify that the impacted VNF instance(s) are running and reachable through the management network
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the impacted VNF instance(s) are running and reachable through the management network')
        for vnf_info in ns_info.vnf_info:
            if vnf_info.vnf_product_name in self.tc_input.get('change_vnf_deployment_flavour').get('vnfs').keys():
                mgmt_addr_list = self.mano.get_vnf_mgmt_addr_list(vnf_info.vnf_instance_id,
                                                                  self.tc_input['mano'].get('query_params'))
                for mgmt_addr in mgmt_addr_list:
                    if not ping(mgmt_addr):
                        raise TestRunError('Unable to PING IP address %s belonging to VNF %s'
                                           % (mgmt_addr, vnf_info.vnf_product_name))

        # --------------------------------------------------------------------------------------------------------------
        # 6. Verify that the NFVO indicates the VNF DF update operation as successful
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NFVO indicates the VNF DF update operation as successful')
        for change_vnf_flavour_data in change_vnf_flavour_data_list:
            if not self.mano.validate_vnf_deployment_flavour(change_vnf_flavour_data.vnf_instance_id,
                                                             change_vnf_flavour_data.new_flavour_id,
                                                             change_vnf_flavour_data.instantiation_level_id,
                                                             change_vnf_flavour_data.additional_param):
                raise TestRunError('Operation of changing deployment flavour for VNF instance ID %s was not successfull'
                                   '- new flavour ID %s, new instantiation level ID %s' %
                                   (change_vnf_flavour_data.vnf_instance_id, change_vnf_flavour_data.new_flavour_id,
                                    change_vnf_flavour_data.instantiation_level_id))

        # --------------------------------------------------------------------------------------------------------------
        # 7. Verify that the NS has been updated by runnning the end-to-end functional test factoring the new VNF DF
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

        LOG.info(
            'Verifying that the NS functionality that utilizes the started VNF instance operates successfully by'
            ' running the end-to-end functional test')
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

        if self.traffic.any_traffic_loss(delay_time=5, tolerance=constants.TRAFFIC_TOLERANCE):
            raise TestRunError('Traffic is flowing with packet loss',
                               err_details='Normal traffic flew with packet loss')

        LOG.info('%s execution completed successfully' % self.tc_name)
