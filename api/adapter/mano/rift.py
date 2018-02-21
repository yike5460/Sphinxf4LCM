import json
import logging
import random
import time
import uuid

import requests
from requests.auth import HTTPBasicAuth
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from api.adapter import construct_adapter
from api.adapter.mano import ManoAdapterError
from api.generic import constants
from api.structures.objects import NsInfo, VnfInfo, InstantiatedVnfInfo, VnfcResourceInfo, ResourceHandle, VnfExtCpInfo
from utils.logging_module import log_entry_exit

LOG = logging.getLogger(__name__)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class RiftManoAdapterError(ManoAdapterError):
    """
    A problem occurred in the VNF LifeCycle Validation Rift MANO adapter API.
    """
    pass


class RiftManoAdapter(object):
    def __init__(self, url, username, password, project):
        self.url = url
        self.username = username
        self.password = password
        self.project = project

        self.session = requests.Session()
        self.session.headers = {
            'Accept': 'application/vnd.yang.data+json',
            'Content-type': 'application/vnd.yang.data+json'
        }
        self.session.auth = HTTPBasicAuth(username=self.username, password=self.password)
        self.session.verify = False

        self.nsr_metadata = {}

    @log_entry_exit(LOG)
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        # TODO: the get logic inside ifs should be moved into functions

        operation_type, resource_id = lifecycle_operation_occurrence_id

        if operation_type == 'ns_instantiate':
            resource = '/api/operational/project/ns-instance-opdata/nsr/%s' % resource_id
            try:
                response = self.session.get(url=self.url + resource)
                assert response.status_code == 200
                json_content = response.json()
            except Exception as e:
                LOG.exception(e)
                raise RiftManoAdapterError('Unable to get opdata for NS %s' % resource_id)

            ns_op_status = json_content['rw-project:project']['nsr:ns-instance-opdata']['nsr'][0]['operational-status']

            if ns_op_status == 'running':
                return constants.OPERATION_SUCCESS
            elif ns_op_status == 'failed':
                return constants.OPERATION_FAILED
            else:
                return constants.OPERATION_PENDING

        if operation_type == 'ns_terminate':
            resource = '/api/operational/project/ns-instance-opdata/nsr/%s' % resource_id
            try:
                response = self.session.get(url=self.url + resource)
                if response.status_code == 204:
                    return constants.OPERATION_SUCCESS

                assert response.status_code == 200
                json_content = response.json()
            except Exception as e:
                LOG.exception(e)
                raise RiftManoAdapterError('Unable to get opdata for NS %s' % resource_id)

            ns_op_status = json_content['rw-project:project']['nsr:ns-instance-opdata']['nsr'][0]['operational-status']

            if ns_op_status == 'failed':
                return constants.OPERATION_FAILED
            else:
                return constants.OPERATION_PENDING

        if operation_type == 'ns_scale_out':
            resource = '/api/operational/project/ns-instance-opdata/nsr/%s' % resource_id
            try:
                response = self.session.get(url=self.url + resource)
                assert response.status_code == 200
                json_content = response.json()
            except Exception as e:
                LOG.exception(e)
                raise RiftManoAdapterError('Unable to get opdata for NS %s' % resource_id)

            ns_op_status = json_content['rw-project:project']['nsr:ns-instance-opdata']['nsr'][0]['operational-status']

            if ns_op_status == 'running':
                return constants.OPERATION_SUCCESS
            elif ns_op_status == 'scaling-out':
                return constants.OPERATION_PENDING
            else:
                return constants.OPERATION_FAILED

        if operation_type == 'ns_scale_in':
            resource = '/api/operational/project/ns-instance-opdata/nsr/%s' % resource_id
            try:
                response = self.session.get(url=self.url + resource)
                assert response.status_code == 200
                json_content = response.json()
            except Exception as e:
                LOG.exception(e)
                raise RiftManoAdapterError('Unable to get opdata for NS %s' % resource_id)

            ns_op_status = json_content['rw-project:project']['nsr:ns-instance-opdata']['nsr'][0]['operational-status']

            if ns_op_status == 'running':
                return constants.OPERATION_SUCCESS
            elif ns_op_status == 'scaling-in':
                return constants.OPERATION_PENDING
            else:
                return constants.OPERATION_FAILED

        raise RiftManoAdapterError('Unknown operation type "%s"' % operation_type)

    @log_entry_exit(LOG)
    def ns_create_id(self, nsd_id, ns_name, ns_description):
        ns_instance_id = str(uuid.uuid4())

        self.nsr_metadata[ns_instance_id] = {
            'id': ns_instance_id,
            'name': ns_name,
            'nsd': self.get_nsd(nsd_id),
            'short-name': ns_name,
            'admin-status': 'ENABLED',
            'description': str(ns_description)
        }

        return ns_instance_id

    @log_entry_exit(LOG)
    def get_nsd(self, nsd_id):
        resource = '/api/config/project/nsd-catalog/nsd/%s' % nsd_id

        try:
            response = self.session.get(url=self.url + resource)
            assert response.status_code == 200
            json_content = response.json()
        except Exception as e:
            LOG.exception(e)
            raise RiftManoAdapterError('Unable to get NSD %s' % nsd_id)

        nsd = json_content['rw-project:project']['project-nsd:nsd-catalog']['nsd'][0]
        nsd.pop('rw-project-nsd:meta')

        return nsd

    @log_entry_exit(LOG)
    def get_vnfd(self, vnfd_id):
        resource = '/api/config/project/vnfd-catalog/vnfd/%s' % vnfd_id

        try:
            response = self.session.get(url=self.url + resource)
            assert response.status_code == 200
            json_content = response.json()
        except Exception as e:
            LOG.exception(e)
            raise RiftManoAdapterError('Unable to get VNFD %s' % vnfd_id)

        vnfd = json_content['rw-project:project']['project-vnfd:vnfd-catalog']['vnfd'][0]
        vnfd.pop('rw-project-vnfd:meta')

        return vnfd

    @log_entry_exit(LOG)
    def ns_instantiate(self, ns_instance_id, flavour_id, sap_data=None, pnf_info=None, vnf_instance_data=None,
                       nested_ns_instance_data=None, location_constraints=None, additional_param_for_ns=None,
                       additional_param_for_vnf=None, start_time=None, ns_instantiation_level_id=None,
                       additional_affinity_or_anti_affinity_rule=None):

        resource = '/api/config/project/Spirent/ns-instance-config/nsr'

        nsr_metadata = self.nsr_metadata[ns_instance_id]
        nsr_metadata['datacenter'] = additional_param_for_ns['datacenter']
        request_body = {
            'nsr': [nsr_metadata]
        }

        try:
            response = self.session.post(url=self.url + resource, json=request_body)
            assert response.status_code == 201
            assert 'ok' in response.json().get('rpc-reply', {})
        except Exception as e:
            LOG.exception(e)
            raise RiftManoAdapterError('Unable to instantiate NS %s' % ns_instance_id)

        return 'ns_instantiate', ns_instance_id

    @log_entry_exit(LOG)
    def vnf_query(self, filter, attribute_selector=None):
        vnf_instance_id = filter['vnf_instance_id']
        vnf_info = VnfInfo()
        vnf_info.vnf_instance_id = str(vnf_instance_id)

        resource = '/api/operational/project/vnfr-catalog/vnfr/%s' % vnf_instance_id
        try:
            response = self.session.get(url=self.url + resource)
            if response.status_code == 204:
                # vnf-instance-id not found, so assuming NOT_INSTANTIATED
                vnf_info.instantiation_state = constants.VNF_NOT_INSTANTIATED
                return vnf_info

            assert response.status_code == 200
            json_content = response.json()
        except Exception as e:
            LOG.exception(e)
            raise RiftManoAdapterError('Unable to get VNFR data for VNF %s' % vnf_instance_id)

        vnfr = json_content['rw-project:project']['vnfr:vnfr-catalog']['vnfr'][0]

        vnf_info.vnf_instance_name = str(vnfr['name'])

        # TODO: see if other value for vnf_product_name is more relevant
        vnf_info.vnf_product_name = str(vnfr['short-name'])

        # TODO: add logic for all states
        vnf_info.instantiation_state = constants.VNF_INSTANTIATED
        vnf_info.vnfd_id = str(vnfr['vnfd']['id'])

        vnf_info.instantiated_vnf_info = InstantiatedVnfInfo()
        if vnfr['operational-status'] == 'running':
            vnf_info.instantiated_vnf_info.vnf_state = constants.VNF_STARTED
        else:
            vnf_info.instantiated_vnf_info.vnf_state = constants.VNF_STOPPED

        vnf_info.instantiated_vnf_info.vnfc_resource_info = list()
        for vdur in vnfr['vdur']:
            vnfc_resource_info = VnfcResourceInfo()
            vnfc_resource_info.vnfc_instance_id = str(vdur['id'])
            vnfc_resource_info.vdu_id = str(vdur['vdu-id-ref'])

            vnfc_resource_info.compute_resource = ResourceHandle()
            vnfc_resource_info.compute_resource.vim_id = str(vnfr['rw-vnfr:datacenter'])
            vnfc_resource_info.compute_resource.resource_id = str(vdur['vim-id'])
            vnf_info.instantiated_vnf_info.vnfc_resource_info.append(vnfc_resource_info)

        vnf_info.instantiated_vnf_info.ext_cp_info = list()
        for connection_point in vnfr['connection-point']:
            vnf_ext_cp_info = VnfExtCpInfo()
            vnf_ext_cp_info.cp_instance_id = str(connection_point['connection-point-id'])
            vnf_ext_cp_info.address = [str(connection_point['mac-address'])]
            vnf_ext_cp_info.cpd_id = str(connection_point['name'])
            vnf_info.instantiated_vnf_info.ext_cp_info.append(vnf_ext_cp_info)

        return vnf_info

    @log_entry_exit(LOG)
    def ns_query(self, filter, attribute_selector=None):
        ns_instance_id = filter['ns_instance_id']
        ns_info = NsInfo()
        ns_info.ns_instance_id = str(ns_instance_id)

        resource = '/api/operational/project/ns-instance-opdata/nsr/%s' % ns_instance_id
        try:
            response = self.session.get(url=self.url + resource)
            if response.status_code == 204:
                # vnf-instance-id not found, so assuming NOT_INSTANTIATED
                ns_info.ns_state = constants.NS_NOT_INSTANTIATED
                return ns_info

            assert response.status_code == 200
            json_content = response.json()
        except Exception as e:
            LOG.exception(e)
            raise RiftManoAdapterError('Unable to get opdata for NS %s' % ns_instance_id)

        ns_opdata = json_content['rw-project:project']['nsr:ns-instance-opdata']['nsr'][0]

        ns_info.ns_name = str(ns_opdata['name-ref'])
        ns_info.description = '' # TODO: get from /api/config
        ns_info.nsd_id = str(ns_opdata['nsd-ref'])

        if ns_opdata['operational-status'] == 'running':
            ns_info.ns_state = constants.NS_INSTANTIATED
        else:
            ns_info.ns_state = constants.NS_NOT_INSTANTIATED

        ns_info.vnf_info = list()
        for constituent_vnfr in ns_opdata['constituent-vnfr-ref']:
            vnf_info = self.vnf_query(filter={'vnf_instance_id': constituent_vnfr['vnfr-id']})
            ns_info.vnf_info.append(vnf_info)

        return ns_info

    @log_entry_exit(LOG)
    def ns_terminate(self, ns_instance_id, terminate_time=None, additional_param=None):
        resource = '/api/config/project/Spirent/ns-instance-config/nsr/%s' % ns_instance_id

        try:
            response = self.session.delete(url=self.url + resource)
            assert response.status_code == 201
        except Exception as e:
            LOG.exception(e)
            raise RiftManoAdapterError('Unable to terminate NS %s' % ns_instance_id)

        return 'ns_terminate', ns_instance_id

    @log_entry_exit(LOG)
    def ns_delete_id(self, ns_instance_id):
        self.nsr_metadata.pop(ns_instance_id)

    @log_entry_exit(LOG)
    def get_vim_helper(self, vim_id):
        resource = '/api/config/project/cloud/account/%s' % vim_id

        try:
            response = self.session.get(url=self.url + resource)
            assert response.status_code == 200
            json_content = response.json()
        except Exception as e:
            LOG.exception(e)
            raise RiftManoAdapterError('Unable to get VIM details for %s' % vim_id)

        vim_details = json_content['rw-project:project']['rw-cloud:cloud']['account'][0]

        vim_type = vim_details['account-type']
        if vim_type == 'openstack':
            openstack_params = vim_details['openstack']

            vim_vendor = vim_type
            vim_params = {
                'auth_url': openstack_params['auth_url'],
                'username': openstack_params['key'],
                'password': openstack_params['secret'],
                'project_name': openstack_params['tenant'],
                'project_domain_name': openstack_params['project-domain'],
                'user_domain_name': openstack_params['user-domain']
            }
        else:
            raise RiftManoAdapterError('Unsupported VIM type: %s' % vim_type)

        return construct_adapter(vendor=vim_vendor, module_type='vim', **vim_params)

    @log_entry_exit(LOG)
    def verify_vnf_sw_images(self, vnf_info):
        vnfd_id = vnf_info.vnfd_id
        vnfd = self.get_vnfd(vnfd_id)

        expected_vdu_images = {}
        for vdu in vnfd['vdu']:
            expected_vdu_images[vdu['id']] = vdu['image']

        for vnfc_resource_info in vnf_info.instantiated_vnf_info.vnfc_resource_info:
            vdu_id = vnfc_resource_info.vdu_id

            vim_id = vnfc_resource_info.compute_resource.vim_id
            vim = self.get_vim_helper(vim_id)
            resource_id = vnfc_resource_info.compute_resource.resource_id
            virtual_compute = vim.query_virtualised_compute_resource(filter={'compute_id': resource_id})
            image_id = virtual_compute.vc_image_id
            image_details = vim.query_image(image_id)
            image_name_vim = image_details.name

            image_name_vnfd = expected_vdu_images[vdu_id]
            if image_name_vim != image_name_vnfd:
                LOG.debug('Unexpected image for VNFC %s, VDU type %s' % (resource_id, vdu_id))
                LOG.debug('Expected image name: %s; actual image name: %s' % (image_name_vnfd, image_name_vim))
                return False

        return True

    @log_entry_exit(LOG)
    def validate_ns_allocated_vresources(self, ns_instance_id, additional_param=None):
        ns_info = self.ns_query(filter={'ns_instance_id': ns_instance_id})
        for vnf_info in ns_info.vnf_info:
            if not self.validate_vnf_allocated_vresources(vnf_info):
                return False
        return True

    @log_entry_exit(LOG)
    def validate_vnf_allocated_vresources(self, vnf_info):
        validation_result = True

        vnfd_id = vnf_info.vnfd_id
        vnfd = self.get_vnfd(vnfd_id)

        expected_vdu_resources = {}
        for vdu in vnfd['vdu']:
            expected_vdu_resources[vdu['id']] = {
                'vcpu-count': vdu['vm-flavor']['vcpu-count'],
                'memory-mb': vdu['vm-flavor']['memory-mb'],
                'storage-gb': vdu['vm-flavor']['storage-gb'],
                'nic-count': len(vdu['interface'])
            }

        for vnfc_resource_info in vnf_info.instantiated_vnf_info.vnfc_resource_info:
            vdu_id = vnfc_resource_info.vdu_id

            # Get VIM adapter object
            vim = self.get_vim_helper(vnfc_resource_info.compute_resource.vim_id)

            resource_id = vnfc_resource_info.compute_resource.resource_id
            virtual_compute = vim.query_virtualised_compute_resource(filter={'compute_id': resource_id})

            actual_vdu_resources = {
                'vcpu-count': virtual_compute.virtual_cpu.num_virtual_cpu,
                'memory-mb': virtual_compute.virtual_memory.virtual_mem_size,
                'storage-gb': virtual_compute.virtual_disks[0].size_of_storage,
                'nic-count': len(virtual_compute.virtual_network_interface)
            }

            for resource_name, actual_value in actual_vdu_resources.items():
                expected_value = expected_vdu_resources[vdu_id][resource_name]
                if actual_value != expected_value:
                    LOG.debug('Unexpected value for %s: %s. Expected: %s'
                              % (resource_name, actual_value, expected_value))
                    validation_result = False

        return validation_result

    @log_entry_exit(LOG)
    def verify_vnf_nsd_mapping(self, ns_instance_id, additional_param=None):
        validation_result = True

        ns_info = self.ns_query(filter={'ns_instance_id': ns_instance_id, 'additional_param': additional_param})
        nsd_id = ns_info.nsd_id
        nsd = self.get_nsd(nsd_id)

        member_vnf_index_vnfd_mapping = {}
        for constituent_vnfd in nsd['constituent-vnfd']:
            member_vnf_index_vnfd_mapping[constituent_vnfd['member-vnf-index']] = constituent_vnfd['vnfd-id-ref']

        for vnf_info in ns_info.vnf_info:
            actual_vnfd_id = vnf_info.vnfd_id
            vnf_instance_id = vnf_info.vnf_instance_id

            resource = '/api/operational/project/vnfr-catalog/vnfr/%s' % vnf_instance_id
            try:
                response = self.session.get(url=self.url + resource)
                assert response.status_code == 200
                json_content = response.json()
            except Exception as e:
                LOG.exception(e)
                raise RiftManoAdapterError('Unable to get VNFR data for VNF %s' % vnf_instance_id)

            vnfr = json_content['rw-project:project']['vnfr:vnfr-catalog']['vnfr'][0]
            member_vnf_index_ref = vnfr['member-vnf-index-ref']

            expected_vnfd_id = member_vnf_index_vnfd_mapping[member_vnf_index_ref]
            if expected_vnfd_id != actual_vnfd_id:
                LOG.debug('Unexpected VNFD ID %s for VNF %s. Expected: %s'
                          % (actual_vnfd_id, vnf_info.vnf_product_name, expected_vnfd_id))
                validation_result = False

        return validation_result

    @log_entry_exit(LOG)
    def get_vnf_mgmt_addr_list(self, vnf_instance_id):
        vnf_mgmt_addr_list = list()

        resource = '/api/operational/project/vnfr-catalog/vnfr/%s' % vnf_instance_id
        try:
            response = self.session.get(url=self.url + resource)
            assert response.status_code == 200
            json_content = response.json()
        except Exception as e:
            LOG.exception(e)
            raise RiftManoAdapterError('Unable to get VNFR data for VNF %s' % vnf_instance_id)

        vnfr = json_content['rw-project:project']['vnfr:vnfr-catalog']['vnfr'][0]

        for vdur in vnfr['vdur']:
            if 'vm-management-ip' in vdur:
                vnf_mgmt_addr_list.append(vdur['vm-management-ip'])

        return vnf_mgmt_addr_list

    @log_entry_exit(LOG)
    def ns_scale(self, ns_instance_id, scale_type, scale_ns_data=None, scale_vnf_data=None, scale_time=None):
        # TODO: add support for scaling steps > 1?

        if scale_type == 'SCALE_VNF':
            raise NotImplementedError
        elif scale_type == 'SCALE_NS':
            if scale_ns_data.scale_ns_by_steps_data is None:
                raise RiftManoAdapterError('Rift MANO Adapter only supports NS scaling by steps, but'
                                           'scale_ns_by_steps_data was not provided.')

            scaling_group_name = scale_ns_data.additional_param_for_ns['scaling_group_name']

            if scale_ns_data.scale_ns_by_steps_data.scaling_direction == 'scale_out':
                resource = '/api/config/project/%s/ns-instance-config/nsr/%s/scaling-group/%s/instance'\
                           % (self.project,  ns_instance_id, scaling_group_name)

                scaling_group_instance_id = random.randint(0, 65535)
                request_body = {
                    'instance': [
                        {
                            'id': scaling_group_instance_id
                        }
                    ]
                }

                try:
                    response = self.session.post(url=self.url + resource, json=request_body)
                    assert response.status_code == 201
                    assert 'ok' in response.json().get('rpc-reply', {})
                except Exception as e:
                    LOG.exception(e)
                    raise RiftManoAdapterError('Unable to scale out NS %s' % ns_instance_id)

                return 'ns_scale_out', ns_instance_id

            elif scale_ns_data.scale_ns_by_steps_data.scaling_direction == 'scale_in':
                resource = '/api/config/project/ns-instance-config/nsr/%s/scaling-group/%s'\
                           % (ns_instance_id, scaling_group_name)
                try:
                    response = self.session.get(url=self.url + resource)
                    assert response.status_code == 200
                    json_content = response.json()
                except Exception as e:
                    LOG.exception(e)
                    raise RiftManoAdapterError('Unable to get existing instances of scaling group %s for NS %s'
                                               % (scaling_group_name, ns_instance_id))

                scaling_groups_ids = json_content['rw-project:project']['nsr:ns-instance-config']['nsr'][0][
                    'scaling-group'][0].get('instance', [])
                if len(scaling_groups_ids) == 0:
                    raise RiftManoAdapterError('Unable to scale in because no existing scaling group instances')

                removed_scaling_groups_id = scaling_groups_ids[0]['id']
                resource = '/api/config/project/%s/ns-instance-config/nsr/%s/scaling-group/%s/instance/%s' \
                           % (self.project, ns_instance_id, scaling_group_name, removed_scaling_groups_id)

                try:
                    response = self.session.delete(url=self.url + resource)
                    print json.dumps(response.json(), indent=2)
                    assert response.status_code == 201
                except Exception as e:
                    LOG.exception(e)
                    raise RiftManoAdapterError('Unable to scale in NS %s' % ns_instance_id)

                return 'ns_scale_in', ns_instance_id

            else:
                raise RiftManoAdapterError('Invalid scaling direction: %s'
                                           % scale_ns_data.scale_ns_by_steps_data.scaling_direction)

    @log_entry_exit(LOG)
    def wait_for_ns_stable_state(self, ns_instance_id, max_wait_time, poll_interval):
        stable_states = ['running', 'failed']
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            resource = '/api/operational/project/ns-instance-opdata/nsr/%s' % ns_instance_id
            try:
                response = self.session.get(url=self.url + resource)
                assert response.status_code == 200
                json_content = response.json()
            except Exception as e:
                LOG.exception(e)
                raise RiftManoAdapterError('Unable to get opdata for NS %s' % ns_instance_id)

            ns_op_status = json_content['rw-project:project']['nsr:ns-instance-opdata']['nsr'][0]['operational-status']
            LOG.debug('Got NS status %s for NS with ID %s' % (ns_op_status, ns_instance_id))
            if ns_op_status in stable_states:
                return True
            else:
                LOG.debug('Expected NS status to be one of %s, got %s' % (stable_states, ns_op_status))
                LOG.debug('Sleeping %s seconds' % poll_interval)
                time.sleep(poll_interval)
                elapsed_time += poll_interval
                LOG.debug('Elapsed time %s seconds out of %s' % (elapsed_time, max_wait_time))

        LOG.debug('NS with ID %s did not reach a stable state after %s' % (ns_instance_id, max_wait_time))
        return False
