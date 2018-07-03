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


import json
import logging
import random
import time
import uuid
from collections import defaultdict

import requests
from requests.auth import HTTPBasicAuth
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from api.adapter import construct_adapter
from api.adapter.mano import ManoAdapterError
from api.generic import constants
from api.structures.objects import NsInfo, VnfInfo, InstantiatedVnfInfo, VnfcResourceInfo, ResourceHandle, NsdInfo, \
    VnfExtCpInfo, Nsd, VnfProfile, NsDf, NsVirtualLinkDesc, NsVirtualLinkConnectivity, Vnfd, Vdu, VirtualComputeDesc, \
    VirtualStorageDesc, SwImageDesc, VirtualCpuData, VirtualCpuPinningData, VirtualMemoryData, VnfExtCpd
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

        resource = '/api/operational/project/%s/project-config' % self.project
        try:
            response = self.session.get(url=self.url + resource)
            assert response.status_code == 200
        except AssertionError as e:
            LOG.exception(e)
            if response.status_code == 204:
                raise RiftManoAdapterError('Unable to create %s instance - invalid project name: %s'
                                           % (self.__class__.__name__, self.project))
            else:
                raise RiftManoAdapterError('Unable to create %s instance - %s: %s'
                                           % (self.__class__.__name__, response.status_code, response.content))
        except Exception as e:
            LOG.exception(e)
            raise RiftManoAdapterError('Unable to create %s instance - %s' % (self.__class__.__name__, e))

        self.nsr_metadata = {}
        self.nsd_info_ids = {}

        self.vim_helpers = {}

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

        if operation_type == 'scaling_group_terminate':
            ns_instance_id, scaling_group_record_id = resource_id
            resource = '/api/operational/project/%s/ns-instance-opdata/nsr/%s/scaling-group-record/instance/%s' % \
                       (self.project, ns_instance_id, scaling_group_record_id)
            try:
                response = self.session.get(url=self.url + resource)
                assert response.status_code == 200
                json_content = response.json()
            except Exception as e:
                LOG.exception(e)
                raise RiftManoAdapterError('Unable to get opdata for scaling-group-record %s, NS %s' %
                                           (scaling_group_record_id, ns_instance_id))
            scaling_group_record = json_content.get('nsr:scaling-group-record')
            if scaling_group_record is None:
                return constants.OPERATION_SUCCESS
            elif 'instance' in scaling_group_record:
                return constants.OPERATION_PENDING
            else:
                return constants.OPERATION_FAILED

        if operation_type == 'multiple_operations':
            operation_list = resource_id
            operation_status_list = map(self.get_operation_status, operation_list)

            if constants.OPERATION_FAILED in operation_status_list:
                return constants.OPERATION_FAILED
            elif constants.OPERATION_PENDING in operation_status_list:
                return constants.OPERATION_PENDING
            else:
                return constants.OPERATION_SUCCESS

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
        nsd.pop('rw-project-nsd:meta', None)

        return nsd

    @log_entry_exit(LOG)
    def get_nsd_generic(self, nsd_id):
        nsd = self.get_nsd(nsd_id)

        # Create empty generic Nsd object
        nsd_generic = Nsd()

        # Populate Nsd generic data
        nsd_generic.nsd_identifier = str(nsd['id'])
        nsd_generic.nsd_name = str(nsd['name'])
        nsd_generic.version = str(nsd['version'])
        nsd_generic.designer = str(nsd['vendor'])

        # Populate VNFD IDs and build basic VnfProfile information elements
        nsd_generic.vnfd_id = []
        nsdf = NsDf()
        nsdf.vnf_profile = []
        ns_vlc = {}
        for vnfd in nsd['constituent-vnfd']:
            vnfd_id = str(vnfd['vnfd-id-ref'])
            vnf_index = str(vnfd['member-vnf-index'])
            ns_vlc[vnf_index] = {}

            # Store the current VNFD
            if vnfd_id not in nsd_generic.vnfd_id:
                nsd_generic.vnfd_id.append(vnfd_id)

            # Build the VnfProfile information element for the VNF with the current VNF index
            vnf_profile = VnfProfile()
            vnf_profile.vnf_profile_id = vnf_index
            vnf_profile.vnfd_id = vnfd_id
            nsdf.vnf_profile.append(vnf_profile)

        # Populate NsVirtualLinkDesc information element
        if 'vld' in nsd.keys():
            nsd_generic.virtual_link_desc = []
            for vld in nsd['vld']:
                vld_id = str(vld['id'])
                ns_virtual_link_desc = NsVirtualLinkDesc()
                ns_virtual_link_desc.virtual_link_desc_id = vld_id
                nsd_generic.virtual_link_desc.append(ns_virtual_link_desc)

                # Build dict containing the list of CPs for each VL, for each member VNF index
                # Example:
                # {
                #   '1': {
                #     'link1': ['mgmt'],
                #     'link3': ['east'],
                #     'link2': ['west']
                #   }
                # }
                for cp in vld['vnfd-connection-point-ref']:
                    vnf_index = str(cp['member-vnf-index-ref'])
                    if vld_id not in ns_vlc[vnf_index]:
                        ns_vlc[vnf_index][vld_id] = []
                    ns_vlc[vnf_index][vld_id].append(str(cp['vnfd-connection-point-ref']))

        # Populate VNF profiles with NsVirtualLinkConnectivity information elements
        for vnf_profile in nsdf.vnf_profile:
            vnf_index = vnf_profile.vnf_profile_id
            vnf_profile.ns_virtual_link_connectivity = []
            for vl_id in ns_vlc[vnf_index]:
                ns_virtual_link_connectivity = NsVirtualLinkConnectivity()
                ns_virtual_link_connectivity.virtual_link_profile_id = vl_id
                ns_virtual_link_connectivity.cpd_id = ns_vlc[vnf_index][vl_id]
                vnf_profile.ns_virtual_link_connectivity.append(ns_virtual_link_connectivity)

        nsdf.ns_df_id = str(nsd['name'])
        nsd_generic.nsdf = [nsdf]

        return nsd_generic

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
        vnfd.pop('rw-project-vnfd:meta', None)

        return vnfd

    @log_entry_exit(LOG)
    def get_vnfd_generic(self, vnfd_id):
        vnfd = self.get_vnfd(vnfd_id)

        # Create empty generic Vnfd object
        vnfd_generic = Vnfd()

        # Populate general VNFD data
        vnfd_generic.vnf_product_name = str(vnfd['name'])
        vnfd_generic.vnf_product_info_name = str(vnfd['name'])
        vnfd_generic.vnf_product_info_description = str(vnfd.get('description'))
        vnfd_generic.vnfd_id = str(vnfd['id'])
        vnfd_generic.vnf_provider = str(vnfd['vendor'])
        vnfd_generic.vnfd_version = str(vnfd['version'])

        # Populate Vdu, VirtualComputeDesc and VirtualStorageDesc information elements
        vnfd_generic.vdu = []
        vnfd_generic.virtual_compute_desc = []
        vnfd_generic.virtual_storage_desc = []
        for vdu in vnfd['vdu']:
            generic_vdu = Vdu()
            generic_virtual_compute_desc = VirtualComputeDesc()
            generic_virtual_storage_desc = VirtualStorageDesc()

            generic_vdu.name = str(vdu['name'])
            generic_vdu.vdu_id = str(vdu['id'])
            generic_vdu.sw_image_desc = SwImageDesc()
            generic_vdu.sw_image_desc.name = str(vdu.get('image'))

            if 'guest-epa' in vdu.keys():
                generic_virtual_compute_desc.virtual_cpu = VirtualCpuData()
                generic_virtual_compute_desc.virtual_cpu.virtual_cpu_pinning = VirtualCpuPinningData()
                if vdu['guest-epa']['cpu-pinning-policy'] == 'SHARED':
                    generic_virtual_compute_desc.virtual_cpu.virtual_cpu_pinning.virtual_cpu_pinning_policy = 'dynamic'
                else:
                    generic_virtual_compute_desc.virtual_cpu.num_virtual_cpu = vdu['vm-flavor']['vcpu-count']
                generic_virtual_compute_desc.virtual_compute_desc_id = str(vdu['id'])

            generic_virtual_compute_desc.virtual_memory = VirtualMemoryData()
            generic_virtual_compute_desc.virtual_memory.virtual_mem_size = int(vdu['vm-flavor']['memory-mb'])

            generic_virtual_storage_desc.size_of_storage = int(vdu['vm-flavor'].get('storage-gb'))
            generic_virtual_storage_desc.id = str(vdu.get('id'))

            vnfd_generic.vdu.append(generic_vdu)
            vnfd_generic.virtual_compute_desc.append(generic_virtual_compute_desc)
            vnfd_generic.virtual_storage_desc.append(generic_virtual_storage_desc)

        # Populate VnfExtCpd information element
        vnfd_generic.vnf_ext_cpd = []
        for connection_point in vnfd['connection-point']:
            generic_vnf_ext_cpd = VnfExtCpd()
            generic_vnf_ext_cpd.cpd_id = str(connection_point['name'])
            vnfd_generic.vnf_ext_cpd.append(generic_vnf_ext_cpd)

        return vnfd_generic

    @log_entry_exit(LOG)
    def ns_instantiate(self, ns_instance_id, flavour_id, sap_data=None, pnf_info=None, vnf_instance_data=None,
                       nested_ns_instance_data=None, location_constraints=None, additional_param_for_ns=None,
                       additional_param_for_vnf=None, start_time=None, ns_instantiation_level_id=None,
                       additional_affinity_or_anti_affinity_rule=None):
        resource = '/api/config/project/%s/ns-instance-config/nsr' % self.project

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
    def vnf_query(self, query_filter, attribute_selector=None):
        vnf_instance_id = query_filter['vnf_instance_id']
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
        vnf_info.vnf_product_name = str(vnfr['member-vnf-index-ref'])

        # TODO: add logic for all states
        vnf_info.instantiation_state = constants.VNF_INSTANTIATED
        vnf_info.vnfd_id = str(vnfr['vnfd']['id'])

        vnf_info.instantiated_vnf_info = InstantiatedVnfInfo()
        if vnfr['operational-status'] == 'running':
            vnf_info.instantiated_vnf_info.vnf_state = constants.VNF_STARTED
        else:
            vnf_info.instantiated_vnf_info.vnf_state = constants.VNF_STOPPED

        vnf_info.instantiated_vnf_info.vnfc_resource_info = []
        for vdur in vnfr['vdur']:
            vnfc_resource_info = VnfcResourceInfo()
            vnfc_resource_info.vnfc_instance_id = str(vdur['id'])
            vnfc_resource_info.vdu_id = str(vdur['vdu-id-ref'])

            vnfc_resource_info.compute_resource = ResourceHandle()
            vnfc_resource_info.compute_resource.vim_id = str(vnfr['rw-vnfr:datacenter'])
            vnfc_resource_info.compute_resource.resource_id = str(vdur['vim-id'])
            vnf_info.instantiated_vnf_info.vnfc_resource_info.append(vnfc_resource_info)

        vnf_info.instantiated_vnf_info.ext_cp_info = []
        for connection_point in vnfr['connection-point']:
            vnf_ext_cp_info = VnfExtCpInfo()
            vnf_ext_cp_info.cp_instance_id = str(connection_point['connection-point-id'])
            vnf_ext_cp_info.address = {
                'mac': [str(connection_point['mac-address'])],
                'ip': [str(connection_point['ip-address'])]
            }
            vnf_ext_cp_info.cpd_id = str(connection_point['name'])
            vnf_info.instantiated_vnf_info.ext_cp_info.append(vnf_ext_cp_info)

        return vnf_info

    @log_entry_exit(LOG)
    def ns_query(self, query_filter, attribute_selector=None):
        ns_instance_id = query_filter['ns_instance_id']
        ns_info = NsInfo()
        ns_info.ns_instance_id = str(ns_instance_id)

        resource = '/api/operational/project/ns-instance-opdata/nsr/%s' % ns_instance_id
        try:
            response = self.session.get(url=self.url + resource)
            if response.status_code == 204:
                # ns-instance-id not found, so assuming NOT_INSTANTIATED
                ns_info.ns_state = constants.NS_NOT_INSTANTIATED
                return ns_info

            assert response.status_code == 200
            json_content = response.json()
        except Exception as e:
            LOG.exception(e)
            raise RiftManoAdapterError('Unable to get opdata for NS %s' % ns_instance_id)

        ns_opdata = json_content['rw-project:project']['nsr:ns-instance-opdata']['nsr'][0]

        ns_info.ns_name = str(ns_opdata['name-ref'])
        ns_info.description = ''  # TODO: get from /api/config
        ns_info.nsd_id = str(ns_opdata['nsd-ref'])

        if ns_opdata['operational-status'] == 'running':
            ns_info.ns_state = constants.NS_INSTANTIATED
        else:
            ns_info.ns_state = constants.NS_NOT_INSTANTIATED

        ns_info.vnf_info = []
        for constituent_vnfr in ns_opdata['constituent-vnfr-ref']:
            vnf_info = self.vnf_query(query_filter={'vnf_instance_id': constituent_vnfr['vnfr-id']})
            ns_info.vnf_info.append(vnf_info)

        return ns_info

    @log_entry_exit(LOG)
    def ns_terminate(self, ns_instance_id, terminate_time=None, additional_param=None):
        resource = '/api/config/project/%s/ns-instance-config/nsr/%s' % (self.project, ns_instance_id)

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
        vim_helper = self.vim_helpers.get(vim_id)
        if vim_helper is not None:
            return vim_helper

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

        vim_helper = construct_adapter(vendor=vim_vendor, module_type='vim', **vim_params)
        self.vim_helpers[vim_id] = vim_helper

        return vim_helper

    @log_entry_exit(LOG)
    def verify_vnf_sw_images(self, vnf_info, additional_param=None):
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
            virtual_compute = vim.query_virtualised_compute_resource(query_compute_filter={'compute_id': resource_id})
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
    def validate_vnf_allocated_vresources(self, vnf_info, additional_param=None):
        validation_result = True

        vnfd_id = vnf_info.vnfd_id
        vnfd = self.get_vnfd(vnfd_id)

        expected_vdu_flavor = {}
        expected_vdu_resources = {}
        for vdu in vnfd['vdu']:
            expected_vdu_flavor[vdu['id']] = vdu['vm-flavor'].get('rw-project-vnfd:vm-flavor-name')
            expected_vdu_resources[vdu['id']] = {
                'vcpu-count': vdu['vm-flavor'].get('vcpu-count'),
                'memory-mb': vdu['vm-flavor'].get('memory-mb'),
                'storage-gb': vdu['vm-flavor'].get('storage-gb'),
                'nic-count': len(vdu['interface'])
            }

        for vnfc_resource_info in vnf_info.instantiated_vnf_info.vnfc_resource_info:
            vdu_id = vnfc_resource_info.vdu_id
            # Get VIM adapter object
            vim = self.get_vim_helper(vnfc_resource_info.compute_resource.vim_id)

            resource_id = vnfc_resource_info.compute_resource.resource_id

            # Get the flavor name from the VNFD
            flavor_name_vnfd = expected_vdu_flavor[vdu_id]
            if flavor_name_vnfd is not None:

                # Get the flavor name from the VIM
                server_details = vim.server_get(resource_id)
                server_flavor_id = server_details['flavor_id']
                flavor_details = vim.flavor_get(server_flavor_id)
                flavor_name_nova = str(flavor_details['name'])

                # Compare the flavor name in the VNFD to the flavor name of the VM
                if flavor_name_nova != flavor_name_vnfd:
                    LOG.debug('Unexpected value for flavor: %s. Expected: %s' % (flavor_name_vnfd, flavor_name_nova))
                    validation_result = False
            else:
                virtual_compute = vim.query_virtualised_compute_resource(
                    query_compute_filter={'compute_id': resource_id})

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

        ns_info = self.ns_query(query_filter={'ns_instance_id': ns_instance_id, 'additional_param': additional_param})
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
    def get_vnf_mgmt_addr_list(self, vnf_instance_id, additional_param=None):
        vnf_mgmt_addr_list = []

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
                    raise RiftManoAdapterError('Unable to scale in NS because no scaling group instances exist')

                removed_scaling_groups_id = scaling_groups_ids[0]['id']
                resource = '/api/config/project/%s/ns-instance-config/nsr/%s/scaling-group/%s/instance/%s' \
                           % (self.project, ns_instance_id, scaling_group_name, removed_scaling_groups_id)

                try:
                    response = self.session.delete(url=self.url + resource)
                    assert response.status_code == 201
                except Exception as e:
                    LOG.exception(e)
                    raise RiftManoAdapterError('Unable to scale in NS %s' % ns_instance_id)

                ns_scale_in_op = 'ns_scale_in', ns_instance_id
                scaling_group_terminate_op = 'scaling_group_terminate', (ns_instance_id, removed_scaling_groups_id)
                return 'multiple_operations', [ns_scale_in_op, scaling_group_terminate_op]

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
                return
            else:
                LOG.debug('Expected NS status to be one of %s, got %s' % (stable_states, ns_op_status))
                LOG.debug('Sleeping %s seconds' % poll_interval)
                time.sleep(poll_interval)
                elapsed_time += poll_interval
                LOG.debug('Elapsed time %s seconds out of %s' % (elapsed_time, max_wait_time))

        raise RiftManoAdapterError('NS with ID %s did not reach a stable state after %s'
                                   % (ns_instance_id, max_wait_time))

    @log_entry_exit(LOG)
    def verify_ns_vnf_instance_count(self, ns_instance_id, aspect_id, number_of_steps=1, additional_param=None):
        validation_result = True

        # Get the NSR
        resource = '/api/operational/project/ns-instance-opdata/nsr/%s' % ns_instance_id
        try:
            response = self.session.get(url=self.url + resource)
            assert response.status_code == 200
            json_content = response.json()
        except Exception as e:
            LOG.exception(e)
            raise RiftManoAdapterError('Unable to get opdata for NS %s' % ns_instance_id)

        nsr = json_content['rw-project:project']['nsr:ns-instance-opdata']['nsr'][0]

        # Get the NSD
        nsd_id = str(nsr['nsd-ref'])
        nsd = self.get_nsd(nsd_id)

        # Create dictionary with expected number of instances for each VNF
        expected_vnf_count = {}
        # Since the NS is instantiated, for each VNF in the NS, set the number of instances to 1.
        for constituent_vnfd in nsd['constituent-vnfd']:
            expected_vnf_count[str(constituent_vnfd['member-vnf-index'])] = 1

        scaling_group_record_list = nsr['scaling-group-record']
        scaling_group_descriptor_list = nsd['scaling-group-descriptor']
        scaling_group_descriptor_dict = {
            scaling_group_descriptor['name']: scaling_group_descriptor for scaling_group_descriptor in
                scaling_group_descriptor_list
        }
        for scaling_group_record in scaling_group_record_list:
            scaling_group_name = str(scaling_group_record['scaling-group-name-ref'])
            number_of_instances = len(scaling_group_record.get('instance', []))
            scaling_group_descriptor = scaling_group_descriptor_dict[scaling_group_name]
            vnfd_member_list = scaling_group_descriptor['vnfd-member']
            for vnfd_member in vnfd_member_list:
                expected_vnf_count[str(vnfd_member['member-vnf-index-ref'])] += vnfd_member['count'] * \
                                                                                number_of_instances

        # Create dictionary with actual number of instances for each VNF
        actual_vnf_count = defaultdict(int)
        ns_info = self.ns_query(query_filter={'ns_instance_id': ns_instance_id})
        for vnf_info in ns_info.vnf_info:
            vnf_product_name = vnf_info.vnf_product_name
            actual_vnf_count[vnf_product_name] += 1

        # Compare actual values with expected values
        for vnf_product_name in expected_vnf_count:
            LOG.debug('Expected number of instances for VNF %s: %s; actual number: %s'
                      % (vnf_product_name, expected_vnf_count[vnf_product_name], actual_vnf_count[vnf_product_name]))
            if actual_vnf_count[vnf_product_name] != expected_vnf_count[vnf_product_name]:
                validation_result = False

        return validation_result

    @log_entry_exit(LOG)
    def nsd_info_create(self, user_defined_data=None):
        # Generating a UUID
        nsd_info_id = str(uuid.uuid4())

        # Populate the NsdInfo object
        nsd_info = NsdInfo()
        nsd_info.nsd_info_id = nsd_info_id
        nsd_info.user_defined_data = user_defined_data

        # Store the mapping between the NsdInfo object and its UUID
        self.nsd_info_ids[nsd_info_id] = nsd_info

        return nsd_info_id

    @log_entry_exit(LOG)
    def nsd_info_query(self, query_filter, attribute_selector=None):
        nsd_info_id = query_filter['nsd_info_id']
        return self.nsd_info_ids.get(nsd_info_id)

    @log_entry_exit(LOG)
    def nsd_upload(self, nsd_info_id, nsd):
        # Get the NsdInfo object corresponding to the provided nsd_info_id
        nsd_info = self.nsd_info_ids.get(nsd_info_id)
        if nsd_info is None:
            raise RiftManoAdapterError('No NsdInfo object with ID %s' % nsd_info_id)

        # Uploading the NSD
        if nsd is not None:
            raise NotImplementedError('Rift does not support ETSI NSD format')

        vendor_nsd = nsd_info.user_defined_data.get('vendor_nsd')
        if vendor_nsd is None:
            raise RiftManoAdapterError('Vendor NSD not present in user_defined_data')

        try:
            vendor_nsd = json.loads(vendor_nsd)
        except Exception as e:
            LOG.exception(e)
            raise RiftManoAdapterError('Unable to parse vendor NSD')

        resource = '/api/config/project/%s/nsd-catalog' % self.project
        request_body = {
            'nsd': [vendor_nsd]
        }
        try:
            response = self.session.post(url=self.url + resource, json=request_body)
            assert response.status_code == 201
            assert 'ok' in response.json().get('rpc-reply', {})
        except Exception as e:
            LOG.exception(e)
            raise RiftManoAdapterError('Unable to upload the NSD')

        # Retrieving details about the on-boarded NSD
        nsd_id = str(vendor_nsd['id'])

        # Updating the corresponding NsdInfo object with the details of the on-boarded NSD
        nsd_info.nsd_id = nsd_id

    @log_entry_exit(LOG)
    def nsd_fetch(self, nsd_info_id):
        # Get the NsdInfo object corresponding to the provided nsd_info_id
        nsd_info = self.nsd_info_ids.get(nsd_info_id)
        if nsd_info is None:
            raise RiftManoAdapterError('No NsdInfo object with ID %s' % nsd_info_id)

        # Get the NSD corresponding to the provided nsd_info_id
        nsd_id = nsd_info.nsd_id
        if nsd_id is None:
            raise RiftManoAdapterError('NsdInfo object with ID %s does not have the NsdId attribute set' % nsd_info_id)
        nsd = self.get_nsd(nsd_id)

        return nsd

    @log_entry_exit(LOG)
    def nsd_delete(self, nsd_info_id):
        # Get the NsdInfo object corresponding to the provided nsd_info_id
        nsd_info = self.nsd_info_ids.get(nsd_info_id)
        if nsd_info is None:
            raise RiftManoAdapterError('No NsdInfo object with ID %s' % nsd_info_id)

        # If the NsdInfo object holds information about an NSD, delete it
        nsd_id = nsd_info.nsd_id
        if nsd_id is not None:
            resource = '/api/config/project/%s/nsd-catalog/nsd/%s' % (self.project, nsd_id)
            try:
                response = self.session.delete(url=self.url + resource)
                assert response.status_code == 201
            except Exception as e:
                LOG.exception(e)
                raise RiftManoAdapterError('Unable to delete NSD %s' % nsd_id)

            # Check the NSD has been deleted by the MANO. This check is added because there is no other way of checking
            # that the NSD has been deleted.
            try:
                self.get_nsd(nsd_id)
            except RiftManoAdapterError:
                LOG.debug('NSD %s has been deleted' % nsd_id)
            else:
                raise RiftManoAdapterError('NSD %s has not been deleted' % nsd_id)

        # Delete the NsdInfo object
        self.nsd_info_ids.pop(nsd_info_id)

        return nsd_info_id
