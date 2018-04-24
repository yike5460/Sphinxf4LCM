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


class TD_NFV_NSLCM_INSTANTIATE_NEST_NS_001(TestCase):
    """
    TD_NFV_NSLCM_INSTANTIATE_NEST_NS_001 Verify that a NS referencing an existing nested NS can be successfully
    instantiated

    Sequence:
    1. Trigger NS1 instantiation on the NFVO
    2. Verify that NS1 is instantiated
    3. Trigger NS2 instantiation on the NFVO
    4. Verify that the software images of the VNF(s) referenced in NSD2 have been successfully added to the image
       repository managed by the VIM
    5. Verify that resources associated to NS2 have been allocated by the VIM according to the descriptors
    6. Verify that the VNF instance(s) have been deployed according to the NSD (i.e. query the VIM and VNFM for VMs, VLs
       and CPs)
    7. Verify that existing VNF instance(s) in NS1 are running and reachable via the management network
    8. Verify that the VNF instance(s) in NS2 are running and reachable through the management network
    9. Verify that the VNF instances(s) in NS2 have been configured according to the VNFD(s) by querying the VNFM
    10. Verify that the VNF instance(s), VL(s) and VNFFG(s) in NS2 have been connected according to the descriptors
    11. Verify that the NFVO indicates NS2 instantiation operation result as successful
    12. Verify that NS2 is successfully instantiated by running an end-to-end functional test re-using the functionality
        of VNF instance(s) inside NS1
    13. Trigger the termination of NS2 instance on the NFVO
    14. Verify that NS2 is terminated and that all resources have been released by the VIM
    15. Trigger the termination of NS1 instance on the NFVO
    16. Verify that NS1 is terminated and that all resources have been released by the VIM
    """

    REQUIRED_APIS = ('mano', 'traffic')
    REQUIRED_ELEMENTS = ('nsd_id_ns1', 'nsd_id_ns2')
    TESTCASE_EVENTS = ('instantiate_ns', 'terminate_ns')

    def run(self):
        LOG.info('Starting %s' % self.tc_name)
        # --------------------------------------------------------------------------------------------------------------
        # 1. Trigger NS1 instantiation on the NFVO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering NS1 instantiation on the NFVO')
        self.ns_instance_id_1 = self.mano.ns_create_and_instantiate(
           nsd_id=self.tc_input['nsd_id_ns1'], ns_name=generate_name(self.tc_name),
           ns_description=self.tc_input.get('ns_description_ns1'), flavour_id=self.tc_input.get('flavour_id_ns1'),
           sap_data=self.tc_input['mano'].get('sap_data_ns1'), pnf_info=self.tc_input.get('pnf_info_ns1'),
           vnf_instance_data=self.tc_input.get('vnf_instance_data_ns1'),
           nested_ns_instance_data=self.tc_input.get('nested_ns_instance_data_ns1'),
           location_constraints=self.tc_input.get('location_constraints_ns1'),
           additional_param_for_ns=self.tc_input['mano'].get('instantiation_params_for_ns_ns1'),
           additional_param_for_vnf=self.tc_input['mano'].get('instantiation_params_for_vnf_ns1'),
           start_time=self.tc_input.get('start_time_ns1'),
           ns_instantiation_level_id=self.tc_input.get('ns_instantiation_level_id_ns1'),
           additional_affinity_or_anti_affinity_rule=self.tc_input.get('additional_affinity_or_anti_affinity_rule_ns1'))

        sleep(constants.INSTANCE_FIRST_BOOT_TIME)

        self.register_for_cleanup(index=10, function_reference=self.mano.ns_terminate_and_delete,
                                  ns_instance_id=self.ns_instance_id_1,
                                  terminate_time=self.tc_input.get('terminate_time_ns1'),
                                  additional_param=self.tc_input['mano'].get('termination_params_ns1'))
        self.register_for_cleanup(index=20, function_reference=self.mano.wait_for_ns_stable_state,
                                  ns_instance_id=self.ns_instance_id_1)

        # --------------------------------------------------------------------------------------------------------------
        # 2. Verify that NS1 is instantiated
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that NS1 is instantiated')
        ns_info_1_after_instantiation = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id_1,
                                                                   'additional_param': self.tc_input['mano'].get(
                                                                       'query_params_ns1')})
        if ns_info_1_after_instantiation.ns_state != constants.NS_INSTANTIATED:
            raise TestRunError('Unexpected NS instantiation state',
                               err_details='NS1 instantiation state was not "%s" after the NS was instantiated'
                                           % constants.NS_INSTANTIATED)

        # --------------------------------------------------------------------------------------------------------------
        # 3. Trigger NS2 instantiation on the NFVO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering NS2 instantiation on the NFVO')
        self.time_record.START('instantiate_ns')
        self.ns_instance_id_2 = self.mano.ns_create_and_instantiate(
           nsd_id=self.tc_input['nsd_id_ns2'], ns_name=generate_name(self.tc_name),
           ns_description=self.tc_input.get('ns_description_ns2'), flavour_id=self.tc_input.get('flavour_id_ns2'),
           sap_data=self.tc_input['mano'].get('sap_data_ns2'), pnf_info=self.tc_input.get('pnf_info_ns2'),
           vnf_instance_data=self.tc_input.get('vnf_instance_data_ns2'),
           nested_ns_instance_data=[self.ns_instance_id_1],
           location_constraints=self.tc_input.get('location_constraints_ns2'),
           additional_param_for_ns=self.tc_input['mano'].get('instantiation_params_for_ns_ns2'),
           additional_param_for_vnf=self.tc_input['mano'].get('instantiation_params_for_vnf_ns2'),
           start_time=self.tc_input.get('start_time_ns2'),
           ns_instantiation_level_id=self.tc_input.get('ns_instantiation_level_id_ns2'),
           additional_affinity_or_anti_affinity_rule=self.tc_input.get('additional_affinity_or_anti_affinity_rule_ns2'))

        self.time_record.END('instantiate_ns')

        self.tc_result['events']['instantiate_ns']['duration'] = self.time_record.duration('instantiate_ns')
        self.tc_result['events']['instantiate_ns']['details'] = 'Success'

        sleep(constants.INSTANCE_FIRST_BOOT_TIME)

        self.register_for_cleanup(index=30, function_reference=self.mano.ns_terminate_and_delete,
                                  ns_instance_id=self.ns_instance_id_2,
                                  terminate_time=self.tc_input.get('terminate_time_ns2'),
                                  additional_param=self.tc_input['mano'].get('termination_params_ns2'))
        self.register_for_cleanup(index=40, function_reference=self.mano.wait_for_ns_stable_state,
                                  ns_instance_id=self.ns_instance_id_2)

        # --------------------------------------------------------------------------------------------------------------
        # 4. Verify that the software images of the VNF(s) referenced in NSD2 have been successfully added to the image
        #    repository managed by the VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the software images of the VNF(s) referenced in NSD2 have been successfully added to '
                 'the image repository managed by the VIM')
        if not self.mano.verify_ns_sw_images(self.ns_instance_id_2, self.tc_input['mano'].get('query_params_ns2')):
            raise TestRunError('Not all VNFCs use the correct images')

        # --------------------------------------------------------------------------------------------------------------
        # 5. Verify that resources associated to NS2 have been allocated by the VIM according to the descriptors
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that resources associated to NS2 have been allocated by the VIM according to the '
                 'descriptors')
        if not self.mano.validate_ns_allocated_vresources(self.ns_instance_id_2,
                                                          self.tc_input['mano'].get('query_params_ns2')):
            raise TestRunError('Allocated vResources could not be validated')

        ns_info_2_after_instantiation = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id_2,
                                                                   'additional_param': self.tc_input['mano'].get(
                                                                       'query_params_ns2')})
        for vnf_info in ns_info_2_after_instantiation.vnf_info:
            self.tc_result['resources']['%s (Initial)' % vnf_info.vnf_product_name] = dict()
            self.tc_result['resources']['%s (Initial)' % vnf_info.vnf_product_name].update(
                self.mano.get_allocated_vresources(vnf_info.vnf_instance_id,
                                                   self.tc_input['mano'].get('query_params_ns2')))

        # --------------------------------------------------------------------------------------------------------------
        # 6. Verify that the VNF instance(s) have been deployed according to the NSD
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the VNF instance(s) have been deployed according to the NSD')
        if not self.mano.verify_vnf_nsd_mapping(self.ns_instance_id_2, self.tc_input['mano'].get('query_params_ns2')):
            raise TestRunError('NS2 VNF instance(s) have not been deployed according to the NSD')

        # --------------------------------------------------------------------------------------------------------------
        # 7. Verify that existing VNF instance(s) in NS1 are running and reachable via the management network
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that existing VNF instance(s) in NS1 are running and reachable via the management network')
        for vnf_info in ns_info_1_after_instantiation.vnf_info:
            mgmt_addr_list = self.mano.get_vnf_mgmt_addr_list(vnf_info.vnf_instance_id,
                                                              self.tc_input['mano'].get('query_params_ns1'))
            for mgmt_addr in mgmt_addr_list:
                if not ping(mgmt_addr):
                    raise TestRunError('Unable to PING IP address %s belonging to NS1 VNF %s'
                                       % (mgmt_addr, vnf_info.vnf_product_name))

        # --------------------------------------------------------------------------------------------------------------
        # 8. Verify that the VNF instance(s) in NS2 are running and reachable through the management network
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the VNF instance(s) in NS2 are running and reachable through the management network')
        for vnf_info in ns_info_2_after_instantiation.vnf_info:
            mgmt_addr_list = self.mano.get_vnf_mgmt_addr_list(vnf_info.vnf_instance_id,
                                                              self.tc_input['mano'].get('query_params_ns2'))
            for mgmt_addr in mgmt_addr_list:
                if not ping(mgmt_addr):
                    raise TestRunError('Unable to PING IP address %s belonging to NS2 VNF %s'
                                       % (mgmt_addr, vnf_info.vnf_product_name))

        # --------------------------------------------------------------------------------------------------------------
        # 9. Verify that the VNF instances(s) in NS2 have been configured according to the VNFD(s) by querying the VNFM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the VNF instances(s) in NS2 have been configured according to the VNFD(s) by querying '
                 'the VNFM')
        # TODO

        # --------------------------------------------------------------------------------------------------------------
        # 10. Verify that the VNF instance(s), VL(s) and VNFFG(s) in NS2 have been connected according to the
        #     descriptors
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the VNF instance(s), VL(s) and VNFFG(s) in NS2 have been connected according to the '
                 'descriptors')
        # TODO

        # --------------------------------------------------------------------------------------------------------------
        # 11. Verify that the NFVO indicates NS2 instantiation operation result as successful
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NFVO indicates NS2 instantiation operation result as successful')
        if ns_info_2_after_instantiation.ns_state != constants.NS_INSTANTIATED:
            raise TestRunError('Unexpected NS state',
                               err_details='NS2 state was not "%s" after the NS was instantiated'
                                           % constants.NS_INSTANTIATED)

        # --------------------------------------------------------------------------------------------------------------
        # 12. Verify that NS2 is successfully instantiated by running an end-to-end functional test re-using the
        #     functionality of VNF instance(s) inside NS1
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that NS2 is successfully instantiated by running an end-to-end functional test re-using the'
                 ' functionality of VNF instance(s) inside NS1')
        self.traffic.configure(traffic_load='NORMAL_TRAFFIC_LOAD',
                               traffic_config=self.tc_input['traffic']['traffic_config'])

        self.register_for_cleanup(index=50, function_reference=self.traffic.destroy)

        # Configure stream destination address(es)
        dest_addr_list_ns1 = self.mano.get_ns_ingress_cp_addr_list(
                                                          ns_info_1_after_instantiation,
                                                          self.tc_input['traffic']['traffic_config']['ingress_cp_name'])
        dest_addr_list_ns2 = self.mano.get_ns_ingress_cp_addr_list(
                                                          ns_info_2_after_instantiation,
                                                          self.tc_input['traffic']['traffic_config']['ingress_cp_name'])
        dest_addr_list = dest_addr_list_ns1 + dest_addr_list_ns2
        self.traffic.reconfig_traffic_dest(dest_addr_list)

        self.traffic.start(return_when_emission_starts=True)

        self.register_for_cleanup(index=60, function_reference=self.traffic.stop)

        if not self.traffic.does_traffic_flow(delay_time=constants.TRAFFIC_STABILIZATION_TIME):
            raise TestRunError('Traffic is not flowing', err_details='Normal traffic did not flow')

        if self.traffic.any_traffic_loss(tolerance=constants.TRAFFIC_TOLERANCE):
            raise TestRunError('Traffic is flowing with packet loss',
                               err_details='Normal traffic flew with packet loss')

        # --------------------------------------------------------------------------------------------------------------
        # 13. Trigger the termination of NS2 instance on the NFVO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering the termination of NS2 instance on the NFVO')
        self.time_record.START('terminate_ns')
        if self.mano.ns_terminate_sync(ns_instance_id=self.ns_instance_id_2,
                                       terminate_time=self.tc_input.get('terminate_time_ns2'),
                                       additional_param=self.tc_input['mano'].get('termination_params_ns2')) != \
                constants.OPERATION_SUCCESS:
            raise TestRunError('Unexpected status for NS2 termination operation',
                               err_details='NS2 termination operation failed')

        self.time_record.END('terminate_ns')

        self.tc_result['events']['terminate_ns']['duration'] = self.time_record.duration('terminate_ns')
        self.tc_result['events']['terminate_ns']['details'] = 'Success'

        self.unregister_from_cleanup(index=40)
        self.unregister_from_cleanup(index=30)

        self.register_for_cleanup(index=30, function_reference=self.mano.ns_delete_id,
                                  ns_instance_id=self.ns_instance_id_2)

        # --------------------------------------------------------------------------------------------------------------
        # 14. Verify that NS2 is terminated and that all resources have been released by the VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that NS2 is terminated')
        ns_info_2_after_termination = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id_2,
                                                                 'additional_param': self.tc_input['mano'].get(
                                                                     'query_params_ns2')})
        if ns_info_2_after_termination.ns_state != constants.NS_NOT_INSTANTIATED:
            raise TestRunError('Unexpected NS instantiation state',
                               err_details='NS2 instantiation state was not "%s" after the NS was terminated'
                                           % constants.NS_NOT_INSTANTIATED)

        LOG.info('Verifying that all NS2 VNF instance(s) have been terminated')
        for vnf_info in ns_info_2_after_instantiation.vnf_info:
            vnf_instance_id = vnf_info.vnf_instance_id
            vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': vnf_instance_id,
                                                   'additional_param': self.tc_input['mano'].get('query_params_ns2')})
            if vnf_info.instantiation_state != constants.VNF_NOT_INSTANTIATED:
                raise TestRunError('NS2 VNF instance %s was not terminated correctly. Expected state was %s but got %s'
                                   % (vnf_instance_id, constants.VNF_NOT_INSTANTIATED, vnf_info.instantiation_state))

        LOG.info('Verifying that all NS2 resources have been released by the VIM')
        if not self.mano.validate_ns_released_vresources(ns_info_2_after_instantiation):
            raise TestRunError('NS2 allocated resources have not been released by the VIM')

        # --------------------------------------------------------------------------------------------------------------
        # 15. Trigger the termination of NS1 instance on the NFVO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering the termination of NS1 instance on the NFVO')
        if self.mano.ns_terminate_sync(ns_instance_id=self.ns_instance_id_1,
                                       terminate_time=self.tc_input.get('terminate_time_ns1'),
                                       additional_param=self.tc_input['mano'].get('termination_params_ns1')) != \
                constants.OPERATION_SUCCESS:
            raise TestRunError('Unexpected status for NS1 termination operation',
                               err_details='NS1 termination operation failed')

        self.unregister_from_cleanup(index=20)
        self.unregister_from_cleanup(index=10)

        self.register_for_cleanup(index=10, function_reference=self.mano.ns_delete_id,
                                  ns_instance_id=self.ns_instance_id_1)

        # --------------------------------------------------------------------------------------------------------------
        # 16. Verify that NS1 is terminated and that all resources have been released by the VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that NS1 is terminated')
        ns_info_1_after_termination = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id_1,
                                                                 'additional_param': self.tc_input['mano'].get(
                                                                     'query_params_ns1')})
        if ns_info_1_after_termination.ns_state != constants.NS_NOT_INSTANTIATED:
            raise TestRunError('Unexpected NS instantiation state',
                               err_details='NS1 instantiation state was not "%s" after the NS was terminated'
                                           % constants.NS_NOT_INSTANTIATED)

        LOG.info('Verifying that all NS1 VNF instance(s) have been terminated')
        for vnf_info in ns_info_1_after_instantiation.vnf_info:
            vnf_instance_id = vnf_info.vnf_instance_id
            vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': vnf_instance_id,
                                                   'additional_param': self.tc_input['mano'].get('query_params_ns1')})
            if vnf_info.instantiation_state != constants.VNF_NOT_INSTANTIATED:
                raise TestRunError('NS1 VNF instance %s was not terminated correctly. Expected state was %s but got %s'
                                   % (vnf_instance_id, constants.VNF_NOT_INSTANTIATED, vnf_info.instantiation_state))

        LOG.info('Verifying that all NS1 resources have been released by the VIM')
        if not self.mano.validate_ns_released_vresources(ns_info_1_after_instantiation):
            raise TestRunError('NS1 allocated resources have not been released by the VIM')

        LOG.info('%s execution completed successfully' % self.tc_name)
