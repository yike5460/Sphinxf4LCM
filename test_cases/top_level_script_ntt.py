#! /usr/bin/env python

import logging

from utils.logging_module import configure_logger

from test_cases.vnf.state.term.TC_VNF_STATE_TERM_demo import TC_VNF_STATE_TERM_demo
from test_cases.vnf.state.stop.TC_VNF_STATE_STOP_demo import TC_VNF_STATE_STOP_demo
from test_cases.vnf.state.start.TC_VNF_STATE_START_demo import TC_VNF_STATE_START_demo

# LOG = logging.basicConfig(level=logging.DEBUG)

# Getting and configuring the RootLogger.
root_logger = logging.getLogger()
configure_logger(root_logger, file_level='DEBUG', console_level='INFO', propagate=True)

# Logger for the current module.
LOG = logging.getLogger(__name__)

if __name__ == '__main__':
    openstack = {'mano': {'type': 'cisconfv',
                          'client_config': {'nso_hostname': '10.119.17.3',
                                            'nso_username': 'info',
                                            'nso_password': 'Info1234!',
                                            'esc_hostname': '10.119.19.192',
                                            'esc_username': 'admin',
                                            'esc_password': 'Info1234!',
                                            'nso_port': '2022',
                                            'esc_port': '830'},
                          'instantiation_params': {'tenant': 'admin',
                                                   'username': 'admin',
                                                   'esc': 'e13sinjuk-aivm-pod1',
                                                   'ext_cp_vlr': {'left': 'ipv4',
                                                                  'mgmt': 'mgmt',
                                                                  'right': 'ipv6'},
                                                   'vdu': {'CSR': {'flavor': 'csrflavor',
                                                                   'image': 'csrimage',
                                                                   'day0': {'destination': 'iosxe_config.txt',
                                                                            'url': 'file:///opt/cisco/esc/images/csr-day0.txt'},
                                                                   'cp': {'left': {'start': '10.128.4.21',
                                                                                   'end': '10.128.4.30'},
                                                                          'mgmt': {'start': '10.119.18.21',
                                                                                   'end': '10.119.18.30'},
                                                                          'right': {'start': '2404:1a8:ff80:2102::21',
                                                                                    'end': '2404:1a8:ff80:2102::30'}}}}},
                          'query_params': {'tenant': 'admin'},
                          'termination_params': {'tenant': 'admin',
                                                 'esc': 'e13sinjuk-aivm-pod1'},
                          'operate_params': {'tenant': 'admin'}},
                 'vnfd_id': 'CSR1kvLuxoft',
                 'flavour_id': 'basic',
                 'instantiation_level_id': 'basic',
                 'vnf': {'instance_name': 'abc'},
                 'traffic': {'type': 'stc',
                             'client_config': {'lab_server_addr': '10.3.228.13',
                                               'user_name': 'mdragomir',
                                               'session_name': 'automation'},
                             'traffic_config': {'left_port_location': '10.3.228.28/1/1',
                                                'left_traffic_addr': '172.16.1.3',
                                                'left_traffic_plen': '24',
                                                'left_traffic_gw': '172.16.1.10',
                                                'left_traffic_gw_mac': '00:11:22:33:44:55',
                                                'left_cp_name': 'CP2',
                                                'right_port_location': '10.3.228.29/1/1',
                                                'right_traffic_addr': '172.16.2.3',
                                                'right_traffic_plen': '24',
                                                'right_traffic_gw': '0.0.0.0',
                                                'port_speed': 100}}}

    # LOG.info('Starting top level script')
    # LOG.info('Calling test case TC_VNF_STATE_TERM_001')
    tc_result = TC_VNF_STATE_TERM_demo(tc_input=openstack).execute()
    print tc_result['overall_status']
    print tc_result['error_info']
    tc_result = TC_VNF_STATE_STOP_demo(tc_input=openstack).execute()
    print tc_result['overall_status']
    print tc_result['error_info']
    tc_result = TC_VNF_STATE_START_demo(tc_input=openstack).execute()
    print tc_result['overall_status']
    print tc_result['error_info']
    print tc_result['events']
    # print tc_result['resources']
    # LOG.info('Exiting top level script')
