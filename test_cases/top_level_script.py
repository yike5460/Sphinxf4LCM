#! /usr/bin/env python

import logging

from utils.logging_module import configure_logger
from test_cases.vnf.complex.TC_VNF_COMPLEX_002 import TC_VNF_COMPLEX_002
from test_cases.vnf.state.inst.TC_VNF_STATE_INST_001 import TC_VNF_STATE_INST_001
from test_cases.vnf.state.inst.TC_VNF_STATE_INST_002 import TC_VNF_STATE_INST_002
from test_cases.vnf.state.term.TC_VNF_STATE_TERM_002 import TC_VNF_STATE_TERM_002

# Getting and configuring the RootLogger.
root_logger = logging.getLogger()
configure_logger(root_logger, file_level='DEBUG', console_level='INFO', propagate=True)

# Logger for the current module.
LOG = logging.getLogger(__name__)


if __name__ == '__main__':
    dummy = {'vnfm_params': {'type': 'dummy',
                             'client_config': {}},
             'vim_params': {'type': 'dummy',
                            'client_config': {}},
             'vnfd_id': '8549a1d5-7c6f-4c71-b57d-6f90127b6dd4',
             'vnf': {'type': 'openwrt',
                     'instance_name': 'openwrt_vnf',
                     'config': 'vnf.conf'},
             'traffic_config': 'traffic.conf',
             'scaling': {'trigger': 'triggered_by_vnf',
                         'type': 'out',
                         'aspect': 'vcpu',
                         'number_of_steps': '1'},
             'process_type': 'update',
             'performance': {'metric': 'vcpu',
                             'collecting_period': '60',
                             'reporting_period': '60',
                             'reporting_boundary': '60',
                             'threshold': {'type': 'single_value',
                                           'value_to_be_crossed': '12',
                                           'direction_in_which_value_is_crossed': 'above'}},
             'fault': {'injection_command': 'vim_command_to_stop_vnf',
                       'recovery_source': 'vnfm'}}

    openstack = {'vnfm_params': {'type': 'openstack',
                                 'client_config': {'auth_url': 'http://controller:35357/v3',
                                                   'username': 'admin',
                                                   'password': 'admin',
                                                   'identity_api_version': '3',
                                                   'project_name': 'admin',
                                                   'project_domain_name': 'default',
                                                   'user_domain_name': 'default'}},
                 'vim_params': {'type': 'openstack',
                                'client_config': {}},
                 'vnfd_id': '81e43ea7-d064-47d3-b188-02ff78b2c4e2',
                 'vnf': {'type': 'openwrt',
                         'instance_name': 'openwrt_vnf',
                         'config': '/home/carpalex/Downloads/openwrt_config_file_defaults.yaml'},
                 'traffic_params': {'type': 'stc',
                                    'client_config' : {'lab_server_addr': '10.2.34.63',
                                                       'user_name': 'nfv',
                                                       'session_name': 'automation'},
                                    'traffic_config': {'left_port_location': '10.2.34.209/1/1',
                                                       'left_traffic_addr': '172.16.10.111',
                                                       'left_traffic_plen': '24',
                                                       'left_traffic_gw': '172.16.10.101',
                                                       'right_port_location': '10.2.34.210/1/1',
                                                       'right_traffic_addr': '172.16.20.106',
                                                       'right_traffic_plen': '24',
                                                       'right_traffic_gw': '172.16.20.101'}},
                 'scaling': {'trigger': 'triggered_by_vnf',
                             'type': 'out',
                             'aspect': None,
                             'number_of_steps': '1'},
                 'process_type': 'update',
                 'performance': {'metric': 'vCPU',
                                 'collecting_period': '60',
                                 'reporting_period': '60',
                                 'reporting_boundary': '60',
                                 'threshold': {'type': 'single_value',
                                               'value_to_be_crossed': '12',
                                               'direction_in_which_value_is_crossed': 'above'}},
                 'fault': {'injection_command': 'vim_command_to_stop_vnf',
                           'recovery_source': 'vnfm'}}

    configure_logger(LOG, file_level='DEBUG', console_level='INFO')
    # LOG.info('Starting top level script')
    # LOG.info('Calling test case TC_VNF_COMPLEX_002')
    # TC_VNF_COMPLEX_002(tc_input=dummy).execute()
    LOG.info('Calling test case TC_VNF_STATE_TERM_002')
    TC_VNF_STATE_TERM_002(tc_input=openstack).execute()
    # LOG.info('Calling test case TC_VNF_STATE_INST_002')
    # TC_VNF_STATE_INST_002(tc_input=openstack).execute()
    LOG.info('Exiting top level script')
