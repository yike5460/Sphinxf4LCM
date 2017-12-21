import json
import logging
import requests

from api.adapter import construct_adapter
from api.adapter.mano import ManoAdapterError
from api.generic import constants
from api.structures.objects import ResourceHandle, InstantiatedVnfInfo, NsInfo, VnfInfo, VnfcResourceInfo
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class SdlManoAdapterError(ManoAdapterError):
    """
    A problem occurred in the VNF LifeCycle Validation SDL MANO adapter API.
    """
    pass


class SdlManoAdapter(object):
    def __init__(self, endpoint_url, tenant_id):
        self.endpoint_url = endpoint_url

        # TODO: may need to be moved in instantiation_params
        self.tenant_id = tenant_id

        self.ns_catalog = {
            'ns1': '{"is_enabled":false,"description":"","sla_path_list":[],"edge_list":[{"start_node_id":1,\
                     "end_interface_id":1,"end_node_id":2,"edge_id":3,"qos_desc":{"excessBw":"100","maxDelay":500,\
                     "committedBw":"100","DSCP":"0"},"start_interface_id":1},{"start_node_id":2,"end_interface_id":1,\
                     "end_node_id":1,"edge_id":4,"qos_desc":{"excessBw":"100","maxDelay":500,"committedBw":"100","DSCP":\
                     "0"},"start_interface_id":1}],"schedule_list":[],"metadata":{"zoom":1,"pan":{"y":0,"x":0}},\
                     "service_desc_list":[{"description":"","parameters":{},"service_version":"1.1.6",\
                     "service_revision":0,"interfaces":[{"nb":1,"in":{"interface":1,"id":2,"name":"t2"}\
                     ,"description":"Data interface eth1","name":"eth1","out":{"interface":1,"id":2,"name":"t2"}},\
                     {"nb":2,"description":"Data interface eth2","name":"eth2"},{"nb":3,"description":\
                     "Data interface eth3","name":"eth3"}],"service_instance_type":"router-os","service_type":\
                     "vyos_router","node_id":1,"num_interfaces":3,"location_constraints":{"virp_id":"",\
                     "virp_type":null},"metadata":{"position":{"y":170,"x":378}},"name":"t1"},{"description":"",\
                     "parameters":{"DHCP_SERVER_IP":"","DHCP_RANGE":""},"service_version":"1.0","service_revision":0,\
                     "interfaces":[{"nb":1,"in":{"interface":1,"id":1,"name":"t1"},"description":\
                     "Data interface eth1","name":"eth1","out":{"interface":1,"id":1,"name":"t1"}},{"nb":2,\
                     "description":"Data interface eth2","name":"eth2"},{"nb":3,"description":"Data interface eth3",\
                     "name":"eth3"},{"nb":4,"description":"Data interface eth4","name":"eth4"},{"nb":5,"description":\
                     "Data interface eth5","name":"eth5"}],"service_instance_type":"vnaas_small-os","service_type":\
                     "ubuntu_vnaas","node_id":2,"num_interfaces":5,"location_constraints":{"virp_id":"","virp_type":\
                     null},"metadata":{"position":{"y":172,"x":702}},"name":"t2"}],"default_location_constraints":\
                     {"virp_type": "OPENSTACK"},"end_node_desc_list":[],"name":""}'
        }

        self.ns_update_json_mapping = dict()
        self.ns_nsd_mapping = dict()

    @log_entry_exit(LOG)
    def ns_create_id(self, nsd_id, ns_name, ns_description):
        nsd_dict = json.loads(self.ns_catalog[nsd_id])
        nsd_dict['is_enabled'] = False
        nsd_dict['name'] = ns_name
        nsd_dict['description'] = ns_description

        response = requests.post(url=self.endpoint_url + '/nfv_network_service', params={'tenant_id': self.tenant_id},
                                 json=nsd_dict)
        assert response.status_code == 200
        ns_instance_id = response.json()['nfvns_uuid']

        self.ns_update_json_mapping[ns_instance_id] = nsd_dict
        self.ns_nsd_mapping[ns_instance_id] = nsd_id

        return ns_instance_id

    @log_entry_exit(LOG)
    def ns_instantiate(self, ns_instance_id, flavour_id, sap_data=None, pnf_info=None, vnf_instance_data=None,
                       nested_ns_instance_data=None, location_constraints=None, additional_param_for_ns=None,
                       additional_param_for_vnf=None, start_time=None, ns_instantiation_level_id=None,
                       additional_affinity_or_anti_affinity_rule=None):

        ns_update_dict = self.ns_update_json_mapping[ns_instance_id]
        ns_update_dict['is_enabled'] = True

        response = requests.put(url=self.endpoint_url + '/nfv_network_service/%s' % ns_instance_id, json=ns_update_dict)
        assert response.status_code == 200

        return 'ns_instantiate', ns_instance_id

    @log_entry_exit(LOG)
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        operation_type, resource_id = lifecycle_operation_occurrence_id

        if operation_type == 'ns_instantiate':
            response = requests.get(url=self.endpoint_url + '/nfv_network_service/%s' % resource_id)
            ns_instance_state = response.json()['state']

            if ns_instance_state == 'running':
                return constants.OPERATION_SUCCESS
            elif ns_instance_state == 'failed':
                return constants.OPERATION_FAILED
            else:
                return constants.OPERATION_PENDING

        if operation_type == 'ns_terminate':
            response = requests.get(url=self.endpoint_url + '/nfv_network_service/%s' % resource_id)
            ns_instance_state = response.json()['state']

            if ns_instance_state == 'disabled':
                return constants.OPERATION_SUCCESS
            elif ns_instance_state == 'failed':
                return constants.OPERATION_FAILED
            else:
                return constants.OPERATION_PENDING

    @log_entry_exit(LOG)
    def ns_query(self, filter, attribute_selector=None):
        ns_instance_id = filter['ns_instance_id']
        ns_info = NsInfo()
        ns_info.ns_instance_id = str(ns_instance_id)

        response = requests.get(url=self.endpoint_url + '/nfv_network_service/%s' % ns_instance_id)
        ns_instance_dict = response.json()

        ns_info.ns_name = str(ns_instance_dict['name'])
        ns_info.description = str(ns_instance_dict['description'])
        ns_info.nsd_id = self.ns_nsd_mapping[ns_info.ns_instance_id]

        if ns_instance_dict['state'] == 'running':
            ns_info.ns_state = constants.NS_INSTANTIATED
        else:
            ns_info.ns_state = constants.NS_NOT_INSTANTIATED

        ns_info.vnf_info = list()
        for service_desc in ns_instance_dict['service_desc_list']:
            vnf_instance_id = service_desc['instance_id']
            if vnf_instance_id != '':
                vnf_info = self.vnf_query(filter={'vnf_instance_id': vnf_instance_id})
                ns_info.vnf_info.append(vnf_info)

        return ns_info

    @log_entry_exit(LOG)
    def vnf_query(self, filter, attribute_selector=None):
        vnf_instance_id = filter['vnf_instance_id']
        vnf_info = VnfInfo()
        vnf_info.vnf_instance_id = vnf_instance_id.encode()

        response = requests.get(url=self.endpoint_url + '/nfv/vnf/vnf-instance/%s' % vnf_instance_id)
        vnf_instance_dict = response.json()

        if response.status_code == 404:
            vnf_info.instantiation_state = constants.VNF_NOT_INSTANTIATED
            return vnf_info

        vnf_info.vnf_instance_name = str(vnf_instance_dict['vnf-instance']['inst_name'])
        vnf_info.vnf_product_name = str(vnf_instance_dict['vnf-instance']['inst_name'])

        # TODO: add logic for all states
        vnf_info.instantiation_state = constants.VNF_INSTANTIATED
        vnf_info.vnfd_id = str(vnf_instance_dict['vnf-instance']['vnf_id'])

        vnf_info.instantiated_vnf_info = InstantiatedVnfInfo()
        if vnf_instance_dict['vnf-instance']['state']['oper_state'] == 'ACTIVE':
            vnf_info.instantiated_vnf_info.vnf_state = constants.VNF_STARTED
        else:
            vnf_info.instantiated_vnf_info.vnf_state = constants.VNF_STOPPED

        vnf_info.instantiated_vnf_info.vnfc_resource_info = list()
        for vnfc_id, vnfc_details in vnf_instance_dict['vnf-instance']['vnfc_instance_list'].items():
            vnfc_resource_info = VnfcResourceInfo()
            vnfc_resource_info.vnfc_instance_id = str(vnfc_details['vnfc_id'])
            vnfc_resource_info.vdu_id = str(vnfc_details['vi_resources']['vdu_id'])

            vnfc_resource_info.compute_resource = ResourceHandle()
            vnfc_resource_info.compute_resource.vim_id = str(vnfc_details['vi_resources']['vi_descriptor']['virp_id'])
            vnfc_resource_info.compute_resource.resource_id = str(vnfc_details['vi_resources']['vi_descriptor']
                                                                  ['vi_resources']['mgmt_objects']['OPENSTACK_SERVER'])
            vnf_info.instantiated_vnf_info.vnfc_resource_info.append(vnfc_resource_info)

        return vnf_info

    @log_entry_exit(LOG)
    def get_vim_helper(self, vim_id):
        return construct_adapter(vendor='openstack', module_type='vim', auth_url='http://10.2.16.50:35357',
                                 username='root', password='pass', project_name='demo')

    @log_entry_exit(LOG)
    def ns_terminate(self, ns_instance_id, terminate_time=None):
        ns_update_dict = self.ns_update_json_mapping[ns_instance_id]
        ns_update_dict['is_enabled'] = False

        response = requests.put(url=self.endpoint_url + '/nfv_network_service/%s' % ns_instance_id, json=ns_update_dict)
        assert response.status_code == 200

        return 'ns_terminate', ns_instance_id

    @log_entry_exit(LOG)
    def ns_delete_id(self, ns_instance_id):
        response = requests.delete(url=self.endpoint_url + '/nfv_network_service/%s' % ns_instance_id)
        assert response.status_code == 200
