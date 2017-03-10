#! /usr/bin/env python

import logging

from utils.logging_module import configure_logger
from test_cases.vnf.complex.TC_VNF_COMPLEX_002 import TC_VNF_COMPLEX_002
from test_cases.vnf.state.inst.TC_VNF_STATE_INST_001 import TC_VNF_STATE_INST_001
from test_cases.vnf.state.inst.TC_VNF_STATE_INST_002 import TC_VNF_STATE_INST_002
from test_cases.vnf.state.term.TC_VNF_STATE_TERM_002 import TC_VNF_STATE_TERM_002
from test_cases.vnf.scale.out.TC_VNF_SCALE_OUT_001 import TC_VNF_SCALE_OUT_001
from test_cases.vnf.scale.out.TC_VNF_SCALE_OUT_003 import TC_VNF_SCALE_OUT_003

# Getting and configuring the RootLogger.
root_logger = logging.getLogger()
configure_logger(root_logger, file_level='DEBUG', console_level='INFO', propagate=True)

# Logger for the current module.
LOG = logging.getLogger(__name__)


if __name__ == '__main__':
    openstack = {'vnfm_params': {'type': 'openstack',
                                 'client_config': {'auth_url': 'http://controller:35357/v3',
                                                   'username': 'admin',
                                                   'password': 'stack',
                                                   'identity_api_version': '3',
                                                   'project_name': 'admin',
                                                   'project_domain_name': 'default',
                                                   'user_domain_name': 'default'}},
                 'vim_params': {'type': 'openstack',
                                'client_config': {}},
                 'vnfd_id': '467b3f37-44e9-4cf5-bfae-304b3c987641',
                 'vnf': {'type': 'openwrt',
                         'instance_name': 'openwrt_vnf',
                         'config': '/home/mdragomir/Downloads/openwrt_config_file_defaults.yaml'},
                 'traffic_params': {'type': 'stc',
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
                                                       'port_speed': 100}},
                 'scaling': {'policies': ['SP1'],
                             'aspect': None,
                             'increment': 1,
                             'max_instances': 3,
                             'default_instances': 1},
                 'process_type': 'update',
                 'performance': {'metric': 'vCPU',
                                 'collecting_period': 60,
                                 'reporting_period': 60,
                                 'reporting_boundary': 60,
                                 'threshold': {'type': 'single_value',
                                               'value_to_be_crossed': 12,
                                               'direction_in_which_value_is_crossed': 'above'}},
                 'fault': {'injection_command': 'vim_command_to_stop_vnf',
                           'recovery_source': 'vnfm'}}

    configure_logger(LOG, file_level='DEBUG', console_level='INFO')
    # LOG.info('Starting top level script')
    # LOG.info('Calling test case TC_VNF_COMPLEX_002')
    # TC_VNF_COMPLEX_002(tc_input=dummy).execute()
    # LOG.info('Calling test case TC_VNF_STATE_INST_001')
    # TC_VNF_STATE_INST_001(tc_input=openstack).execute()
    # LOG.info('Calling test case TC_VNF_STATE_INST_002')
    # TC_VNF_STATE_INST_002(tc_input=openstack).execute()
    # LOG.info('Calling test case TC_VNF_STATE_TERM_002')
    # TC_VNF_STATE_TERM_002(tc_input=openstack).execute()
    # LOG.info('Calling test case TC_VNF_SCALE_OUT_001')
    # TC_VNF_SCALE_OUT_001(tc_input=openstack).execute()
    LOG.info('Calling test case TC_VNF_SCALE_OUT_003')
    TC_VNF_SCALE_OUT_003(tc_input=openstack).execute()
    LOG.info('Exiting top level script')
