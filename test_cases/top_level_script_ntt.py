#! /usr/bin/env python

import logging

from utils.logging_module import configure_logger

from test_cases.vnf.state.inst.TC_VNF_STATE_INST_001 import TC_VNF_STATE_INST_001
from test_cases.vnf.state.inst.TC_VNF_STATE_INST_002 import TC_VNF_STATE_INST_002
from test_cases.vnf.state.start.TC_VNF_STATE_START_001 import TC_VNF_STATE_START_001
from test_cases.vnf.state.start.TC_VNF_STATE_START_002 import TC_VNF_STATE_START_002
from test_cases.vnf.state.start.TC_VNF_STATE_START_003 import TC_VNF_STATE_START_003
from test_cases.vnf.state.stop.TC_VNF_STATE_STOP_001 import TC_VNF_STATE_STOP_001
from test_cases.vnf.state.stop.TC_VNF_STATE_STOP_002 import TC_VNF_STATE_STOP_002
from test_cases.vnf.state.stop.TC_VNF_STATE_STOP_003 import TC_VNF_STATE_STOP_003
from test_cases.vnf.state.term.TC_VNF_STATE_TERM_001 import TC_VNF_STATE_TERM_001
from test_cases.vnf.state.term.TC_VNF_STATE_TERM_002 import TC_VNF_STATE_TERM_002
from test_cases.vnf.state.term.TC_VNF_STATE_TERM_003 import TC_VNF_STATE_TERM_003
from test_cases.vnf.state.term.TC_VNF_STATE_TERM_004 import TC_VNF_STATE_TERM_004
from test_cases.vnf.state.term.TC_VNF_STATE_TERM_005 import TC_VNF_STATE_TERM_005

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
                                                                   'cp': {'left': {'start': '10.128.4.41',
                                                                                   'end': '10.128.4.50'},
                                                                          'mgmt': {'start': '10.119.18.41',
                                                                                   'end': '10.119.18.50'},
                                                                          'right': {'start': '2404:1a8:ff80:2102::41',
                                                                                    'end': '2404:1a8:ff80:2102::50'}}}}},
                          'query_params': {'tenant': 'admin'},
                          'termination_params': {'tenant': 'admin',
                                                 'esc': 'e13sinjuk-aivm-pod1'},
                          'operate_params': {'tenant': 'admin'}},
                 'vnfd_id': 'CSR1kvLuxoft',
                 'flavour_id': 'basic',
                 'instantiation_level_id': 'basic',
                 'vnf': {'instance_name': 'abc'},
                 'traffic': {'type': 'stc',
                             'client_config': {'lab_server_addr': '192.168.127.100',
                                               'lab_server_port': 8888,
                                               'user_name': 'vnflcv',
                                               'session_name': 'automation'},
                             'traffic_config': {'type': 'VNF_TERMINATED',
                                                'payload': 'icmp:IcmpEchoRequest',
                                                'port_location': '10.119.19.59/1/1',
                                                'traffic_src_addr': '10.128.4.90',
                                                'traffic_dst_addr': '10.128.4.21 10.128.4.22',
                                                'ingress_cp_name': 'left',
                                                'port_speed': 100}}}

    # LOG.info('Starting top level script')
    tc_result = TC_VNF_STATE_INST_001(tc_input=openstack).execute()
    print tc_result['overall_status']
    print tc_result['error_info']
    tc_result = TC_VNF_STATE_INST_002(tc_input=openstack).execute()
    print tc_result['overall_status']
    print tc_result['error_info']

    tc_result = TC_VNF_STATE_START_001(tc_input=openstack).execute()
    print tc_result['overall_status']
    print tc_result['error_info']
    tc_result = TC_VNF_STATE_START_002(tc_input=openstack).execute()
    print tc_result['overall_status']
    print tc_result['error_info']
    tc_result = TC_VNF_STATE_START_003(tc_input=openstack).execute()
    print tc_result['overall_status']
    print tc_result['error_info']

    tc_result = TC_VNF_STATE_STOP_001(tc_input=openstack).execute()
    print tc_result['overall_status']
    print tc_result['error_info']
    tc_result = TC_VNF_STATE_STOP_002(tc_input=openstack).execute()
    print tc_result['overall_status']
    print tc_result['error_info']
    tc_result = TC_VNF_STATE_STOP_003(tc_input=openstack).execute()
    print tc_result['overall_status']
    print tc_result['error_info']

    tc_result = TC_VNF_STATE_TERM_001(tc_input=openstack).execute()
    print tc_result['overall_status']
    print tc_result['error_info']
    tc_result = TC_VNF_STATE_TERM_002(tc_input=openstack).execute()
    print tc_result['overall_status']
    print tc_result['error_info']
    tc_result = TC_VNF_STATE_TERM_003(tc_input=openstack).execute()
    print tc_result['overall_status']
    print tc_result['error_info']
    tc_result = TC_VNF_STATE_TERM_004(tc_input=openstack).execute()
    print tc_result['overall_status']
    print tc_result['error_info']
    tc_result = TC_VNF_STATE_TERM_005(tc_input=openstack).execute()
    print tc_result['overall_status']
    print tc_result['error_info']

    # print tc_result['events']
    # print tc_result['resources']
    # LOG.info('Exiting top level script')
