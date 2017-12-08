import json
import logging
import re
import time
import uuid
from threading import Timer

import os_client_config
import tackerclient.common.exceptions
import yaml
from tackerclient.tacker.client import Client as TackerClient

from api.adapter import construct_adapter
from api.adapter.mano import ManoAdapterError
from api.generic import constants
from api.structures.objects import InstantiatedVnfInfo, VnfExtCpInfo, VnfInfo, VnfcResourceInfo, ResourceHandle, \
    VnfLifecycleChangeNotification, NsInfo
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class TackerManoAdapterError(ManoAdapterError):
    """
    A problem occurred in the VNF LifeCycle Validation Tacker MANO adapter API.
    """
    pass


class TackerManoAdapter(object):
    """
    Class of functions that map the generic operations exposed by the MANO to the operations exposed by the
    OpenStack Tacker client.
    """

    def __init__(self, auth_url=None, username=None, password=None, identity_api_version=None, project_name=None,
                 project_domain_name=None, user_domain_name=None):
        """
        Create the Tacker client.
        """
        try:
            self.keystone_client = os_client_config.make_client('identity',
                                                                auth_url=auth_url,
                                                                username=username,
                                                                password=password,
                                                                identity_api_version=identity_api_version,
                                                                project_name=project_name,
                                                                project_domain_name=project_domain_name,
                                                                user_domain_name=user_domain_name)

            self.tacker_client = TackerClient(api_version='1.0', session=self.keystone_client.session)
            self.password = password

        except Exception as e:
            LOG.error('Unable to create %s instance' % self.__class__.__name__)
            LOG.exception(e)
            raise TackerManoAdapterError(e.message)

    @log_entry_exit(LOG)
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        """
        This function does not have a direct mapping in OpenStack Tacker client so it will just return the status of the
        VNF with given ID.
        """
        LOG.debug('"Lifecycle Operation Occurrence Id" is not implemented in OpenStack Tacker client!')
        LOG.debug('Will return the state of the resource with given Id')

        if lifecycle_operation_occurrence_id is None:
            raise TackerManoAdapterError('Lifecycle Operation Occurrence ID is absent')
        else:
            resource_type, resource_id = lifecycle_operation_occurrence_id

        if resource_type == 'vnf':
            try:
                tacker_vnf_status = self.tacker_client.show_vnf(resource_id)['vnf']['status']
            except tackerclient.common.exceptions.NotFound:
                # Temporary workaround. When vnf_terminate() is called, declare the VNF as terminated if Tacker raises
                # the NotFound exception
                return constants.OPERATION_SUCCESS
            except tackerclient.common.exceptions.TackerClientException:
                return constants.OPERATION_PENDING
            except Exception as e:
                LOG.exception(e)
                raise TackerManoAdapterError(e.message)

            return constants.OPERATION_STATUS['OPENSTACK_VNF_STATE'][tacker_vnf_status]

        if resource_type == 'stack':
            # Get VNF information from Tacker
            try:
                tacker_show_vnf = self.tacker_client.show_vnf(resource_id)['vnf']
            except Exception as e:
                LOG.exception(e)
                raise TackerManoAdapterError(e.message)

            # Get VIM object
            vim_id = tacker_show_vnf['vim_id']
            vim = self.get_vim_helper(vim_id)

            # Get the Heat stack ID from Tacker information
            stack_id = tacker_show_vnf['instance_id']

            # Get the Heat stack status
            heat_stack = vim.stack_get(stack_id)
            stack_status = heat_stack.stack_status

            return constants.OPERATION_STATUS['OPENSTACK_STACK_STATE'][stack_status]

        if resource_type == 'ns':
            try:
                tacker_ns_status = self.tacker_client.show_ns(resource_id)['ns']['status']
            except tackerclient.common.exceptions.TackerClientException:
                # Temporary workaround. When ns_terminate() is called, declare the NS as terminated if Tacker raises
                # the TackerClientException exception
                return constants.OPERATION_SUCCESS
            except Exception as e:
                LOG.exception(e)
                raise TackerManoAdapterError(e.message)

            return constants.OPERATION_STATUS['OPENSTACK_NS_STATE'][tacker_ns_status]

        if resource_type in ['vnf-list', 'stack-list']:
            return self.get_operation_group_status(lifecycle_operation_occurrence_id)

    @log_entry_exit(LOG)
    def get_operation_group_status(self, lifecycle_operation_occurrence_id):
        """
        This function does not have a direct mapping in OpenStack Tacker client so it will just return the status of a
        group of VNF instance IDs.
        """
        resource_type, resource_id = lifecycle_operation_occurrence_id
        resource_type_mapping = {'vnf-list': 'vnf',
                                 'stack-list': 'stack'}
        vnf_status_list = []
        for vnf in resource_id:
            vnf_operation_status = self.get_operation_status((resource_type_mapping[resource_type], vnf))
            vnf_status_list.append(vnf_operation_status)
        if constants.OPERATION_FAILED in vnf_status_list:
            return constants.OPERATION_FAILED
        elif constants.OPERATION_PENDING in vnf_status_list:
            return constants.OPERATION_PENDING
        else:
            return constants.OPERATION_SUCCESS

    @log_entry_exit(LOG)
    def get_vnfd_scaling_properties(self, vnfd_id, scaling_policy_name):
        vnfd = self.get_vnfd(vnfd_id)

        # Get scaling details for the provided scaling policy name.
        if 'policies' in vnfd['topology_template'].keys():
            for sp in vnfd['topology_template']['policies']:
                if scaling_policy_name in sp.keys():
                    # TOSCA policies regarding Tacker scaling indicate that all scaling properties are required, except
                    # the cooldown, which has a default value of 120 seconds
                    sp_properties = dict()
                    sp_properties['increment'] = sp[scaling_policy_name]['properties']['increment']
                    sp_properties['targets'] = sp[scaling_policy_name]['properties']['targets']
                    sp_properties['min_instances'] = sp[scaling_policy_name]['properties']['min_instances']
                    sp_properties['max_instances'] = sp[scaling_policy_name]['properties']['max_instances']
                    sp_properties['default_instances'] = sp[scaling_policy_name]['properties']['default_instances']
                    sp_properties['cooldown'] = sp[scaling_policy_name]['properties'].get('cooldown', 120)
                    break
            else:
                raise TackerManoAdapterError('No scaling policy named %s in the VNFD with ID %s'
                                             % (scaling_policy_name, vnfd_id))
        else:
            raise TackerManoAdapterError('VNFD with ID %s does not have a scaling policy' % vnfd_id)

        return sp_properties

    @log_entry_exit(LOG)
    def get_nsd_scaling_properties(self, nsd_id, scaling_policy_name):
        raise NotImplementedError

    @log_entry_exit(LOG)
    def limit_compute_resources_for_ns_scaling(self, nsd_id, scaling_policy_name, desired_scale_out_steps,
                                               generic_vim_object):
        raise NotImplementedError

    @log_entry_exit(LOG)
    def limit_compute_resources_for_vnf_instantiation(self, vnfd_id, generic_vim_object, limit_vcpus, limit_vmem,
                                                      limit_vc_instances, scaling_policy_name):
        vnfd = self.get_vnfd(vnfd_id)

        # Get the scaling policy properties, if present.
        if scaling_policy_name is not None:
            sp = self.get_vnfd_scaling_properties(vnfd_id, scaling_policy_name)
            default_instances = sp['default_instances']
        else:
            default_instances = 1

        # Get the resources required by one instance of the VNF
        vcpus_req_one_inst = 0
        vmem_req_one_inst = 0
        vc_instances_req_one_inst = 0
        for node in vnfd['topology_template']['node_templates'].keys():
            if vnfd['topology_template']['node_templates'][node]['type'] == 'tosca.nodes.nfv.VDU.Tacker':
                vcpus_req_one_inst += int(
                    vnfd['topology_template']['node_templates'][node]['capabilities']['nfv_compute']['properties'].get(
                        'num_cpus', 0))
                vmem_req_one_inst += int(
                    vnfd['topology_template']['node_templates'][node]['capabilities']['nfv_compute']['properties'].get(
                        'mem_size', 0).split(' ')[0])
                vc_instances_req_one_inst += 1

        # Decrease the total required compute resources by one to make sure the instantiation will not be possible.
        if limit_vcpus:
            required_vcpus = default_instances * vcpus_req_one_inst - 1
        else:
            required_vcpus = 0
        if limit_vmem:
            required_vmem = default_instances * vmem_req_one_inst - 1
        else:
            required_vmem = 0
        if limit_vc_instances:
            required_vc_instances = default_instances * vc_instances_req_one_inst - 1
        else:
            required_vc_instances = 0

        reservation_id = generic_vim_object.limit_compute_resources(required_vcpus, required_vmem,
                                                                    required_vc_instances)

        return reservation_id

    @log_entry_exit(LOG)
    def limit_storage_resources_for_vnf_instantiation(self, vnfd_id, generic_vim_object, scaling_policy_name):
        vnfd = self.get_vnfd(vnfd_id)
        # Get the scaling policy properties, if present.
        if scaling_policy_name is not None:
            sp = self.get_vnfd_scaling_properties(vnfd_id, scaling_policy_name)
            default_instances = sp['default_instances']
        else:
            default_instances = 1
        # Get the resources required by one instance of the VNF
        vstorage_req_one_inst = 0
        for node in vnfd['topology_template']['node_templates'].keys():
            if vnfd['topology_template']['node_templates'][node]['type'] == 'tosca.nodes.nfv.VDU.Tacker':
                vstorage_req_one_inst += int(
                    vnfd['topology_template']['node_templates'][node]['capabilities']['nfv_compute']['properties'].get(
                        'disk_size', 0).split(' ')[0])
        # Decrease the total required storage resources by one to make sure the instantiation will not be possible.
        required_vstorage = default_instances * vstorage_req_one_inst - 1
        reservation_id = generic_vim_object.limit_storage_resources(required_vstorage)
        return reservation_id

    @log_entry_exit(LOG)
    def limit_compute_resources_for_vnf_scaling(self, vnfd_id, scaling_policy_name, desired_scale_out_steps,
                                                generic_vim_object):
        vnfd = self.get_vnfd(vnfd_id)

        # Get the scaling policy properties.
        sp = self.get_vnfd_scaling_properties(vnfd_id, scaling_policy_name)
        increment = sp['increment']
        default_instances = sp['default_instances']

        # Get the resources required by one instance of the VNF
        # Currently, Tacker scales all VDUs, regardless of the those mentioned in the targets list
        vcpus_req_one_inst = 0
        vmem_req_one_inst = 0
        vc_instances_req_one_inst = 0
        for node in vnfd['topology_template']['node_templates'].keys():
            if vnfd['topology_template']['node_templates'][node]['type'] == 'tosca.nodes.nfv.VDU.Tacker':
                vcpus_req_one_inst += int(
                    vnfd['topology_template']['node_templates'][node]['capabilities']['nfv_compute']['properties'].get(
                        'num_cpus', 0))
                vmem_req_one_inst += int(
                    vnfd['topology_template']['node_templates'][node]['capabilities']['nfv_compute']['properties'].get(
                        'mem_size', 0).split(' ')[0])
                vc_instances_req_one_inst += 1

        # Total required compute resources
        required_vcpus = (desired_scale_out_steps * increment + default_instances) * vcpus_req_one_inst
        required_vmem = (desired_scale_out_steps * increment + default_instances) * vmem_req_one_inst
        required_vc_instances = (desired_scale_out_steps * increment + default_instances) * vc_instances_req_one_inst

        reservation_id = generic_vim_object.limit_compute_resources(required_vcpus, required_vmem,
                                                                    required_vc_instances)

        return reservation_id

    @log_entry_exit(LOG)
    def get_vim_helper(self, vim_id):
        try:
            vim_details = self.tacker_client.show_vim(vim_id)['vim']
        except Exception as e:
            LOG.exception(e)
            raise TackerManoAdapterError(e.message)
        vim_auth_cred = vim_details['auth_cred']
        vim_type = vim_details['type']

        # TODO: get from config file
        vim_auth_cred['password'] = self.password

        return construct_adapter(vim_type, module_type='vim', **vim_auth_cred)

    @log_entry_exit(LOG)
    def get_vnfd(self, vnfd):
        # 'vnfd' input can either be the VNFD ID or the VNFD name
        # TODO: translate to ETSI VNFD
        try:
            tacker_show_vnfd = self.tacker_client.show_vnfd(vnfd)['vnfd']['attributes']['vnfd']
        except Exception as e:
            LOG.exception(e)
            raise TackerManoAdapterError(e.message)
        return yaml.load(tacker_show_vnfd)

    @log_entry_exit(LOG)
    def get_nsd(self, nsd):
        # 'nsd' input can either be the NSD ID or the NSD name
        # TODO: translate to ETSI NSD
        try:
            tacker_show_nsd = self.tacker_client.show_nsd(nsd)['nsd']['attributes']['nsd']
        except Exception as e:
            LOG.exception(e)
            raise TackerManoAdapterError(e.message)
        return yaml.load(tacker_show_nsd)

    @log_entry_exit(LOG)
    def validate_vnf_allocated_vresources(self, vnf_instance_id, additional_param=None):
        vnf_info = self.vnf_query(filter={'vnf_instance_id': vnf_instance_id})
        vnfd_id = vnf_info.vnfd_id
        vnfd = self.get_vnfd(vnfd_id)

        for vnfc_resource_info in vnf_info.instantiated_vnf_info.vnfc_resource_info:
            vim_id = vnfc_resource_info.compute_resource.vim_id
            vim = self.get_vim_helper(vim_id)

            resource_id = vnfc_resource_info.compute_resource.resource_id
            virtual_compute = vim.query_virtualised_compute_resource(filter={'compute_id': resource_id})

            # Get expected values
            expected_num_vcpus = \
                vnfd['topology_template']['node_templates'][vnfc_resource_info.vdu_id]['capabilities']['nfv_compute'][
                    'properties']['num_cpus']
            expected_vmemory_size = \
                int(vnfd['topology_template']['node_templates'][vnfc_resource_info.vdu_id]['capabilities'][
                        'nfv_compute']['properties']['mem_size'].split(' ')[0])
            expected_vstorage_size = \
                int(vnfd['topology_template']['node_templates'][vnfc_resource_info.vdu_id]['capabilities'][
                        'nfv_compute']['properties']['disk_size'].split(' ')[0])
            expected_num_vnics = 0
            expected_vnic_types = dict()
            for node in vnfd['topology_template']['node_templates'].keys():
                if vnfd['topology_template']['node_templates'][node]['type'] == 'tosca.nodes.nfv.CP.Tacker':
                    for req in vnfd['topology_template']['node_templates'][node]['requirements']:
                        if 'virtualBinding' in req.keys():
                            if req['virtualBinding']['node'] == vnfc_resource_info.vdu_id:
                                expected_num_vnics += 1
                                expected_vnic_types[node] = vnfd['topology_template']['node_templates'][node][
                                    'properties'].get('type', 'normal')

            # Get actual values
            actual_num_vcpus = virtual_compute.virtual_cpu.num_virtual_cpu
            actual_vmemory_size = virtual_compute.virtual_memory.virtual_mem_size
            actual_vstorage_size = virtual_compute.virtual_disks[0].size_of_storage
            actual_num_vnics = len(virtual_compute.virtual_network_interface)

            # Compare actual values with expected values for number of vCPUs, vMemory vStorage and number of vNICs
            if actual_num_vcpus != expected_num_vcpus or \
                            actual_vmemory_size != expected_vmemory_size or \
                            actual_vstorage_size != expected_vstorage_size or \
                            actual_num_vnics != expected_num_vnics:
                LOG.debug('For VNFC with id %s expected resources do not match the actual ones' % resource_id)
                LOG.debug('Expected %s vCPU(s), actual number of vCPU(s): %s' % (expected_num_vcpus, actual_num_vcpus))
                LOG.debug('Expected %s vMemory, actual vMemory: %s' % (expected_vmemory_size, actual_vmemory_size))
                LOG.debug('Expected %s vStorage, actual vStorage: %s' % (expected_vstorage_size, actual_vstorage_size))
                LOG.debug('Expected %s vNICs, actual number of vNICs: %s' % (expected_num_vnics, actual_num_vnics))
                return False

            # Compare expected vNIC types with actual vNIC types
            for vnic in virtual_compute.virtual_network_interface:
                actual_vnic_type = vnic.type_virtual_nic

                # Find the name of the CP that has a cp_instance_id that matches the resource_id of this vNIC
                for ext_cp in vnf_info.instantiated_vnf_info.ext_cp_info:
                    if ext_cp.cp_instance_id == vnic.resource_id:
                        cp_name = ext_cp.cpd_id
                        break

                expected_vnic_type = expected_vnic_types.get(cp_name, '')
                if expected_vnic_type != actual_vnic_type:
                    LOG.debug('For VNFC with id %s actual vNIC types do not match the expected ones' % resource_id)
                    LOG.debug('Expected "%s" type for the vNIC corresponding to CP %s, actual type: %s' %
                              (expected_vnic_type, cp_name, actual_vnic_type))
                    return False

        return True

    @log_entry_exit(LOG)
    def get_allocated_vresources(self, vnf_instance_id, additional_param=None):
        vnf_info = self.vnf_query(filter={'vnf_instance_id': vnf_instance_id})

        vresources = dict()

        for vnfc_resource_info in vnf_info.instantiated_vnf_info.vnfc_resource_info:
            vim_id = vnfc_resource_info.compute_resource.vim_id
            vim = self.get_vim_helper(vim_id)

            resource_id = vnfc_resource_info.compute_resource.resource_id
            virtual_compute = vim.query_virtualised_compute_resource(filter={'compute_id': resource_id})

            vresources[resource_id] = dict()

            num_virtual_cpu = virtual_compute.virtual_cpu.num_virtual_cpu
            virtual_memory = virtual_compute.virtual_memory.virtual_mem_size
            size_of_storage = virtual_compute.virtual_disks[0].size_of_storage
            num_vnics = len(virtual_compute.virtual_network_interface)

            vresources[resource_id]['vCPU'] = num_virtual_cpu
            vresources[resource_id]['vMemory'] = str(virtual_memory) + ' MB'
            vresources[resource_id]['vStorage'] = str(size_of_storage) + ' GB'
            vresources[resource_id]['vNIC'] = str(num_vnics)

        return vresources

    @log_entry_exit(LOG)
    def modify_vnf_configuration(self, vnf_instance_id, vnf_configuration_data=None, ext_virtual_link=None):
        # Build a dict with the following structure (this is specified by the Tacker API):
        # "vnf": {
        #     "attributes": {
        #         "config": "vdus:\n  vdu1: <sample_vdu_config> \n\n"
        #     }
        # }
        if vnf_configuration_data is not None:
            LOG.debug('Sleeping 10 seconds to allow the VNF to boot')
            time.sleep(10)
            vnf_attributes = {'vnf': {'attributes': {'config': vnf_configuration_data}}}
            try:
                self.tacker_client.update_vnf(vnf_instance_id, body=vnf_attributes)
            except Exception as e:
                LOG.exception(e)
                raise TackerManoAdapterError(e.message)

        # Poll on the VNF status until it reaches one of the final states
        operation_pending = True
        elapsed_time = 0
        max_wait_time = 300
        poll_interval = constants.POLL_INTERVAL
        lifecycle_operation_occurrence_id = ('vnf', vnf_instance_id)
        final_states = constants.OPERATION_FINAL_STATES

        while operation_pending and elapsed_time < max_wait_time:
            operation_status = self.get_operation_status(lifecycle_operation_occurrence_id)
            LOG.debug('Got status %s for operation with ID %s' % (operation_status, lifecycle_operation_occurrence_id))
            if operation_status in final_states:
                operation_pending = False
            else:
                LOG.debug('Expected state to be one of %s, got %s' % (final_states, operation_status))
                LOG.debug('Sleeping %s seconds' % poll_interval)
                time.sleep(poll_interval)
                elapsed_time += poll_interval
                LOG.debug('Elapsed time %s seconds out of %s' % (elapsed_time, max_wait_time))

        return operation_status

    @log_entry_exit(LOG)
    def vnf_create_id(self, vnfd_id, vnf_instance_name, vnf_instance_description):
        vnf_dict = {'vnf': {'vnfd_id': vnfd_id,
                            'name': vnf_instance_name}}

        try:
            vnf_instance = self.tacker_client.create_vnf(body=vnf_dict)
            LOG.debug('Response from VNFM:\n%s' % json.dumps(vnf_instance, indent=4, separators=(',', ': ')))
        except Exception as e:
            LOG.exception(e)
            raise TackerManoAdapterError(e.message)
        return vnf_instance['vnf']['id']

    @log_entry_exit(LOG)
    def vnf_delete_id(self, vnf_instance_id):
        LOG.debug('"VNF Delete ID" operation is not implemented in OpenStack Tacker client!')

    @log_entry_exit(LOG)
    def vnf_instantiate(self, vnf_instance_id, flavour_id, instantiation_level_id=None, ext_virtual_link=None,
                        ext_managed_virtual_link=None, localization_language=None, additional_param=None):
        LOG.debug('"VNF Instantiate" operation is not implemented in OpenStack Tacker client!')
        LOG.debug('Instead of "Lifecycle Operation Occurrence Id", will just return the "VNF Instance Id"')
        return 'vnf', vnf_instance_id

    @log_entry_exit(LOG)
    def vnf_operate(self, vnf_instance_id, change_state_to, stop_type=None, graceful_stop_timeout=None,
                    additional_param=None):
        LOG.debug('"VNF Operate" operation is not implemented in OpenStack Tacker client!')
        LOG.debug('As a workaround, we will perform the action of the VIM stack')

        # Get VNF information from Tacker
        try:
            tacker_show_vnf = self.tacker_client.show_vnf(vnf_instance_id)['vnf']
        except Exception as e:
            LOG.exception(e)
            raise TackerManoAdapterError(e.message)

        # Get VIM object
        vim_id = tacker_show_vnf['vim_id']
        vim = self.get_vim_helper(vim_id)

        # Get the Heat stack ID from Tacker information
        stack_id = tacker_show_vnf['instance_id']

        # Get VNF state
        vnf_info = self.vnf_query(filter={'vnf_instance_id': vnf_instance_id})
        vnf_state = vnf_info.instantiated_vnf_info.vnf_state

        # Change VNF state
        # Starting a VNF is translated to resuming the HEAT stack
        if change_state_to == 'start' and vnf_state == constants.VNF_STOPPED:
            vim.stack_resume(stack_id)
            LOG.debug('Resume operation initiated on VIM stack %s' % stack_id)
        # Stopping a VNF is translated to suspending the HEAT stack
        elif change_state_to == 'stop' and vnf_state == constants.VNF_STARTED:
            vim.stack_suspend(stack_id)
            LOG.debug('Suspend operation initiated on VIM stack %s' % stack_id)
        else:
            LOG.debug('VIM stack is already in the desired state')

        return 'stack', vnf_instance_id

    @log_entry_exit(LOG)
    def vnf_query(self, filter, attribute_selector=None):
        vnf_instance_id = filter['vnf_instance_id']
        vnf_info = VnfInfo()
        vnf_info.vnf_instance_id = vnf_instance_id.encode()

        try:
            tacker_show_vnf = self.tacker_client.show_vnf(vnf_instance_id)['vnf']
        except tackerclient.common.exceptions.TackerException:
            vnf_info.instantiation_state = constants.VNF_NOT_INSTANTIATED
            return vnf_info
        except Exception as e:
            LOG.exception(e)
            raise TackerManoAdapterError(e.message)
        # Get the Heat stack ID
        stack_id = tacker_show_vnf['instance_id']

        # Query Heat stack
        vim_id = tacker_show_vnf['vim_id']
        vim = self.get_vim_helper(vim_id)
        heat_stack = vim.stack_get(stack_id)

        # Build the vnf_info data structure
        vnf_info.vnf_instance_name = tacker_show_vnf['name'].encode()
        vnf_info.vnf_instance_description = tacker_show_vnf['description'].encode()
        vnf_info.vnfd_id = tacker_show_vnf['vnfd_id'].encode()
        vnf_info.instantiation_state = constants.VNF_INSTANTIATION_STATE['OPENSTACK_VNF_STATE'][
            tacker_show_vnf['status']]
        vnf_info.metadata = {'error_reason': str(tacker_show_vnf['error_reason']),
                             'heat_stack_id': stack_id.encode()}

        # Build the InstantiatedVnfInfo information element only if the VNF instantiation state is INSTANTIATED
        if vnf_info.instantiation_state == constants.VNF_INSTANTIATED:
            vnf_info.instantiated_vnf_info = InstantiatedVnfInfo()
            vnf_info.instantiated_vnf_info.vnf_state = constants.VNF_STATE['OPENSTACK_STACK_STATE'][
                heat_stack.stack_status]

            vnf_info.instantiated_vnf_info.vnfc_resource_info = list()
            try:
                tacker_list_vnf_resources = self.tacker_client.list_vnf_resources(vnf_instance_id)['resources']
                scaling_resources = [vnf_resource for vnf_resource in tacker_list_vnf_resources
                                     if vnf_resource.get('type') == 'OS::Heat::AutoScalingGroup']

                if len(scaling_resources) > 0:
                    # When the VNFD contains scaling policies, Heat will not show the resources (VDUs, CPs, VLs, etc),
                    # but the scaling group.
                    # In this case, grab the resources from Nova

                    # Get the auto scaling group physical resource IDs
                    resource_list = []
                    for scaling_resource in scaling_resources:
                        resource_list += vim.stack_resource_list(scaling_resource['id'])

                    # Get details from Nova for the servers corresponding to each resource belonging to the auto
                    # scaling group
                    for resource in resource_list:
                        resource_name = resource.resource_name

                        # Get the Nova list of servers filtering the servers based on their name.
                        # The servers' names we are looking for start with ta-...
                        # Example ta-hnrt7a-xvlcnwn2nphm-t5vjqah6itlt-VDU1-jyettvu5bvkg
                        # The server name we are looking for should match the following pattern
                        pattern = 'ta-[a-z0-9]{6}-' + resource_name + '-[a-z0-9]{12}-VDU[0-9]+-[a-z0-9]{12}'
                        server_list = vim.server_list(query_filter={'name': pattern})
                        if len(server_list) == 0:
                            raise TackerManoAdapterError('No Nova server name contains string %s' % resource_name)

                        for server in server_list:
                            vnf_resource_id = server.id

                            # Extract the VDU ID from the server name
                            match = re.search('VDU\d+', server.name)
                            vnf_resource_name = match.group()

                            # Build the VnfcResourceInfo data structure
                            vnfc_resource_info = VnfcResourceInfo()
                            vnfc_resource_info.vnfc_instance_id = vnf_resource_id.encode()
                            vnfc_resource_info.vdu_id = vnf_resource_name.encode()

                            vnfc_resource_info.compute_resource = ResourceHandle()
                            vnfc_resource_info.compute_resource.vim_id = vim_id.encode()
                            vnfc_resource_info.compute_resource.resource_id = vnf_resource_id.encode()

                            vnf_info.instantiated_vnf_info.vnfc_resource_info.append(vnfc_resource_info)
                else:
                    # Heat provides the resources as expected.
                    for vnf_resource in tacker_list_vnf_resources:

                        vnf_resource_type = vnf_resource.get('type')
                        vnf_resource_id = vnf_resource.get('id')
                        vnf_resource_name = vnf_resource.get('name')

                        if vnf_resource_type == 'OS::Nova::Server':
                            # Build the VnfcResourceInfo data structure
                            vnfc_resource_info = VnfcResourceInfo()
                            vnfc_resource_info.vnfc_instance_id = vnf_resource_id.encode()
                            vnfc_resource_info.vdu_id = vnf_resource_name.encode()

                            vnfc_resource_info.compute_resource = ResourceHandle()
                            vnfc_resource_info.compute_resource.vim_id = vim_id.encode()
                            vnfc_resource_info.compute_resource.resource_id = vnf_resource_id.encode()

                            vnf_info.instantiated_vnf_info.vnfc_resource_info.append(vnfc_resource_info)

                # Build the VnfExtCpInfo data structure
                vnf_info.instantiated_vnf_info.ext_cp_info = list()
                for vnfc_resource_info in vnf_info.instantiated_vnf_info.vnfc_resource_info:

                    vnf_resource_id = vnfc_resource_info.compute_resource.resource_id
                    port_dict = vim.port_list(device_id=vnf_resource_id)
                    for port_list in port_dict:
                        for port in port_list['ports']:
                            vnf_ext_cp_info = VnfExtCpInfo()
                            vnf_ext_cp_info.cp_instance_id = port['id'].encode()
                            vnf_ext_cp_info.address = [port['mac_address'].encode()]

                            # Extract the CP ID from the port name
                            match = re.search('CP\d+', port['name'])
                            if match:
                                vnf_ext_cp_info.cpd_id = match.group().encode()
                            else:
                                raise TackerManoAdapterError('Cannot get the CP ID')

                            vnf_info.instantiated_vnf_info.ext_cp_info.append(vnf_ext_cp_info)

            except tackerclient.common.exceptions.TackerException:
                return vnf_info
            except Exception as e:
                LOG.exception(e)
                raise TackerManoAdapterError(e.message)

        return vnf_info

    @log_entry_exit(LOG)
    def vnf_scale(self, vnf_instance_id, scale_type, aspect_id, number_of_steps=1, additional_param=None):
        # Build a dict with the following structure (this is specified by the Tacker API):
        # "scale": {
        #   "type": "<type>",
        #   "policy" : "<scaling-policy-name>"}
        try:
            body = {'scale': {'type': scale_type, 'policy': additional_param['scaling_policy_name']}}
            self.tacker_client.scale_vnf(vnf_instance_id, body)
        except tackerclient.common.exceptions.NotFound as e:
            LOG.debug('Either VNF with instance ID %s does not exist or it does not have a scaling policy "%s"' %
                      (vnf_instance_id, additional_param['scaling_policy_name']))
            LOG.exception(e)
            raise TackerManoAdapterError(e.message)
        except Exception as e:
            LOG.exception(e)
            raise TackerManoAdapterError(e.message)

        return 'vnf', vnf_instance_id

    @log_entry_exit(LOG)
    def vnf_terminate(self, vnf_instance_id, termination_type, graceful_termination_timeout=None,
                      additional_param=None):
        try:
            self.tacker_client.delete_vnf(vnf_instance_id)
        except tackerclient.common.exceptions.NotFound:
            # Treat the case when the VNF termination is attempted multiple times (ex. during test execution and as part
            # of the cleanup procedure)
            LOG.debug('VNF with instance ID %s could not be found' % vnf_instance_id)
        except Exception as e:
            raise TackerManoAdapterError(e.message)
        return 'vnf', vnf_instance_id

    @log_entry_exit(LOG)
    def ns_lifecycle_change_notification_subscribe(self, notification_filter=None):
        raise NotImplementedError

    @log_entry_exit(LOG)
    def vnf_lifecycle_change_notification_subscribe(self, notification_filter):
        # TODO: implement notification filter
        last_vnf_event_id = list(self._get_vnf_events())[-1]['id']
        LOG.debug('Got last event id: %d' % last_vnf_event_id)

        def notification_generator(starting_event_id):
            while True:
                vnf_events = self._get_vnf_events(starting_from=starting_event_id)
                timer = Timer(10, lambda: None)  # TODO: define polling interval as parameter
                timer.start()

                for vnf_event in vnf_events:
                    starting_event_id = vnf_event['id']
                    notification = self.translate_vnf_event(vnf_event)
                    if notification is not None:
                        yield notification

                yield None
                timer.join()

        subscription_id = uuid.uuid4()
        return subscription_id, notification_generator(last_vnf_event_id)

    @log_entry_exit(LOG)
    def translate_vnf_event(self, vnf_event):
        operations_mapping = {
            ('CREATE', 'PENDING_CREATE'): ('VNF_INSTANTIATE', 'STARTED'),
            ('CREATE', 'ACTIVE'): ('VNF_INSTANTIATE', 'SUCCESS'),
            ('CREATE', 'ERROR'): ('VNF_INSTANTIATE', 'FAILED'),
            ('SCALE', 'PENDING_SCALE_OUT'): ('VNF_SCALE_OUT', 'STARTED'),
            ('SCALE', 'ACTIVE'): ('VNF_SCALE', 'SUCCESS'),
            ('SCALE', 'PENDING_SCALE_IN'): ('VNF_SCALE_IN', 'STARTED'),
            ('DELETE', 'PENDING_DELETE'): {
                'VNF delete initiated': ('VNF_TERMINATE', 'STARTED'),
                'VNF Delete Complete': ('VNF_TERMINATE', 'SUCCESS')
            },
            ('UPDATE', 'PENDING_UPDATE'): ('VNF_MODIFY_CONFIG', 'STARTED'),
            ('UPDATE', 'ACTIVE'): ('VNF_MODIFY_CONFIG', 'SUCCESS'),
            ('MONITOR', 'PENDING_CREATE'): None,
            ('MONITOR', 'ACTIVE'): None
        }

        notification = VnfLifecycleChangeNotification()
        notification.vnf_instance_id = str(vnf_event['id']).encode()  # TODO: Modify to show vnf instance id

        vnf_event_type = vnf_event['event_type'].encode()
        vnf_resource_state = vnf_event['resource_state'].encode()

        notification_attributes = operations_mapping[(vnf_event_type, vnf_resource_state)]
        if isinstance(notification_attributes, tuple):
            # we are able to determine mapping unambigously
            notification_operation, notification_status = notification_attributes
        if isinstance(notification_attributes, dict):
            # ambiguity; must resolve based on event_details
            vnf_event_details = vnf_event['event_details'].encode()
            notification_operation, notification_status = notification_attributes[vnf_event_details]
        if notification_attributes is None:
            # internal event; no ETSI mapping, ignoring
            return None

        notification.operation = notification_operation
        notification.status = notification_status

        return notification

    @log_entry_exit(LOG)
    def _get_vnf_events(self, starting_from=None, event_type=None, resource_id=None):
        params = dict()
        if resource_id is not None:
            params['resource_id'] = resource_id
        if event_type is not None:
            params['event_type'] = event_type

        try:
            vnf_events = self.tacker_client.list_vnf_events(**params)['vnf_events']
        except Exception as e:
            raise TackerManoAdapterError(e.message)
        if starting_from is not None:
            vnf_events = (vnf_event for vnf_event in vnf_events if vnf_event['id'] > starting_from)

        return vnf_events

    @log_entry_exit(LOG)
    def wait_for_vnf_stable_state(self, vnf_instance_id, max_wait_time, poll_interval):

        if vnf_instance_id is None:
            raise TackerManoAdapterError('VNF instance ID is absent')

        stable_states = ['ACTIVE', 'ERROR', 'NOTFOUND']
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            try:
                vnf_status = self.tacker_client.show_vnf(vnf_instance_id)['vnf']['status']
            except tackerclient.common.exceptions.NotFound:
                # Temporary workaround. When vnf_terminate() is called, declare the VNF as terminated if Tacker raises
                # the NotFound exception
                vnf_status = 'NOTFOUND'
            except tackerclient.common.exceptions.TackerClientException:
                return constants.OPERATION_PENDING
            except Exception as e:
                raise TackerManoAdapterError(e.message)
            LOG.debug('Got VNF status %s for VNF with ID %s' % (vnf_status, vnf_instance_id))
            if vnf_status in stable_states:
                return True
            else:
                LOG.debug('Expected VNF status to be one of %s, got %s' % (stable_states, vnf_status))
                LOG.debug('Sleeping %s seconds' % poll_interval)
                time.sleep(poll_interval)
                elapsed_time += poll_interval
                LOG.debug('Elapsed time %s seconds out of %s' % (elapsed_time, max_wait_time))

        LOG.debug('VNF with ID %s did not reach a stable state after %s' % (vnf_instance_id, max_wait_time))
        return False

    @log_entry_exit(LOG)
    def ns_create_id(self, nsd_id, ns_name, ns_description):
        ns_dict = {'ns': {'nsd_id': nsd_id,
                          'name': ns_name}}

        try:
            ns_instance = self.tacker_client.create_ns(body=ns_dict)
            LOG.debug('Response from NFVO:\n%s' % json.dumps(ns_instance, indent=4, separators=(',', ': ')))
        except Exception as e:
            LOG.exception(e)
            raise TackerManoAdapterError(e.message)
        return ns_instance['ns']['id']

    @log_entry_exit(LOG)
    def ns_instantiate(self, ns_instance_id, flavour_id, sap_data=None, pnf_info=None, vnf_instance_data=None,
                       nested_ns_instance_data=None, location_constraints=None, additional_param_for_ns=None,
                       additional_param_for_vnf=None, start_time=None, ns_instantiation_level_id=None,
                       additional_affinity_or_anti_affinity_rule=None):
        LOG.debug('"NS Instantiate" operation is not implemented in OpenStack Tacker client!')
        LOG.debug('Instead of "Lifecycle Operation Occurrence Id", will just return the "NS Instance Id"')
        return 'ns', ns_instance_id

    @log_entry_exit(LOG)
    def ns_terminate(self, ns_instance_id, terminate_time=None):
        try:
            self.tacker_client.delete_ns(ns_instance_id)
        except tackerclient.common.exceptions.TackerClientException:
            # Treat the case when the NS termination is attempted multiple times (ex. during test execution and as part
            # of the cleanup procedure)
            LOG.debug('NS with instance ID %s could not be found' % ns_instance_id)
        except Exception as e:
            raise TackerManoAdapterError(e.message)
        return 'ns', ns_instance_id

    @log_entry_exit(LOG)
    def ns_delete_id(self, ns_instance_id):
        LOG.debug('"NS Delete ID" operation is not implemented in OpenStack Tacker client!')

    @log_entry_exit(LOG)
    def wait_for_ns_stable_state(self, ns_instance_id, max_wait_time, poll_interval):

        if ns_instance_id is None:
            raise TackerManoAdapterError('NS instance ID is absent')

        stable_states = ['ACTIVE', 'ERROR', 'NOTFOUND']
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            try:
                ns_status = self.tacker_client.show_ns(ns_instance_id)['ns']['status']
            except tackerclient.common.exceptions.TackerClientException:
                ns_status = 'NOTFOUND'
            except Exception as e:
                raise TackerManoAdapterError(e.message)
            LOG.debug('Got NS status %s for NS with ID %s' % (ns_status, ns_instance_id))
            if ns_status in stable_states:
                return True
            else:
                LOG.debug('Expected NS status to be one of %s, got %s' % (stable_states, ns_status))
                LOG.debug('Sleeping %s seconds' % poll_interval)
                time.sleep(poll_interval)
                elapsed_time += poll_interval
                LOG.debug('Elapsed time %s seconds out of %s' % (elapsed_time, max_wait_time))

        LOG.debug('NS with ID %s did not reach a stable state after %s' % (ns_instance_id, max_wait_time))
        return False

    @log_entry_exit(LOG)
    def ns_scale(self, ns_instance_id, scale_type, scale_ns_data=None, scale_vnf_data=None, scale_time=None):
        if scale_type == 'SCALE_NS':
            raise NotImplementedError
        elif scale_type == 'SCALE_VNF':
            vnf_list = []
            for scale_data in scale_vnf_data:
                vnf_instance_id = scale_data.vnf_instance_id
                vnf_list.append(vnf_instance_id)
                self.vnf_scale(vnf_instance_id, scale_type=scale_data.type,
                               aspect_id=scale_data.scale_by_step_data.aspect_id,
                               additional_param=scale_data.scale_by_step_data.additional_param)
            return 'vnf-list', vnf_list

    @log_entry_exit(LOG)
    def ns_update(self, ns_instance_id, update_type, add_vnf_instance=None, remove_vnf_instance_id=None,
                  instantiate_vnf_data=None, change_vnf_flavour_data=None, operate_vnf_data=None,
                  modify_vnf_info_data=None, change_ext_vnf_connectivity_data=None, add_sap=None, remove_sap_id=None,
                  add_nested_ns_id=None, remove_nested_ns_id=None, assoc_new_nsd_version_data=None,
                  move_vnf_instance_data=None, add_vnffg=None, remove_vnffg_id=None, update_vnffg=None,
                  change_ns_flavour_data=None, update_time=None):
        if update_type == 'OperateVnf':
            vnf_list = []
            for update_data in operate_vnf_data:
                vnf_instance_id = update_data.vnf_instance_id
                vnf_list.append(vnf_instance_id)
                change_state_to = update_data.change_state_to
                stop_type = update_data.stop_type
                graceful_stop_timeout = update_data.graceful_stop_timeout
                additional_param = update_data.additional_param
                self.vnf_operate(vnf_instance_id, change_state_to, stop_type, graceful_stop_timeout, additional_param)
            return 'stack-list', vnf_list

    @log_entry_exit(LOG)
    def ns_query(self, filter, attribute_selector=None):
        ns_instance_id = filter['ns_instance_id']
        ns_info = NsInfo()
        ns_info.ns_instance_id = ns_instance_id.encode()

        try:
            tacker_show_ns = self.tacker_client.show_ns(ns_instance_id)['ns']
        except tackerclient.common.exceptions.TackerClientException:
            ns_info.ns_state = constants.NS_NOT_INSTANTIATED
            return ns_info
        except Exception as e:
            LOG.exception(e)
            raise TackerManoAdapterError(e.message)

        ns_info.ns_name = tacker_show_ns['name'].encode()
        ns_info.description = tacker_show_ns['description'].encode()
        ns_info.nsd_id = tacker_show_ns['nsd_id'].encode()
        ns_info.ns_state = constants.NS_INSTANTIATION_STATE['OPENSTACK_NS_STATE'][tacker_show_ns['status']]

        # Build the VnfInfo data structure for each VNF that is part of the NS
        ns_info.vnf_info = list()
        vnf_ids = tacker_show_ns['vnf_ids']
        vnf_ids_str = str(vnf_ids).replace("'", '"')
        vnf_ids_dict = json.loads(vnf_ids_str)
        for vnf_name in vnf_ids_dict.keys():
            vnf_instance_id = vnf_ids_dict[vnf_name]
            vnf_info = self.vnf_query(filter={'vnf_instance_id': vnf_instance_id})
            vnf_info.vnf_product_name = vnf_name.encode()
            ns_info.vnf_info.append(vnf_info)

        return ns_info

    @log_entry_exit(LOG)
    def validate_ns_allocated_vresources(self, ns_instance_id, additional_param=None):
        ns_info = self.ns_query(filter={'ns_instance_id': ns_instance_id})
        for vnf_info in ns_info.vnf_info:
            # TODO: validate_vnf_allocated_vresources should be called, but avoid building the VnfInfo twice

            vnfd_id = vnf_info.vnfd_id
            vnfd = self.get_vnfd(vnfd_id)

            for vnfc_resource_info in vnf_info.instantiated_vnf_info.vnfc_resource_info:
                vim_id = vnfc_resource_info.compute_resource.vim_id
                vim = self.get_vim_helper(vim_id)

                resource_id = vnfc_resource_info.compute_resource.resource_id
                virtual_compute = vim.query_virtualised_compute_resource(filter={'compute_id': resource_id})

                # Get expected values
                expected_num_vcpus = \
                    vnfd['topology_template']['node_templates'][vnfc_resource_info.vdu_id]['capabilities'][
                        'nfv_compute']['properties']['num_cpus']
                expected_vmemory_size = \
                    int(vnfd['topology_template']['node_templates'][vnfc_resource_info.vdu_id]['capabilities'][
                            'nfv_compute']['properties']['mem_size'].split(' ')[0])
                expected_vstorage_size = \
                    int(vnfd['topology_template']['node_templates'][vnfc_resource_info.vdu_id]['capabilities'][
                            'nfv_compute']['properties']['disk_size'].split(' ')[0])
                expected_num_vnics = 0
                expected_vnic_types = dict()
                for node in vnfd['topology_template']['node_templates'].keys():
                    if vnfd['topology_template']['node_templates'][node]['type'] == 'tosca.nodes.nfv.CP.Tacker':
                        for req in vnfd['topology_template']['node_templates'][node]['requirements']:
                            if req.get('virtualBinding', '')['node'] == vnfc_resource_info.vdu_id:
                                    expected_num_vnics += 1
                                    expected_vnic_types[node] = vnfd['topology_template']['node_templates'][node][
                                        'properties'].get('type', 'normal')

                # Get actual values
                actual_num_vcpus = virtual_compute.virtual_cpu.num_virtual_cpu
                actual_vmemory_size = virtual_compute.virtual_memory.virtual_mem_size
                actual_vstorage_size = virtual_compute.virtual_disks[0].size_of_storage
                actual_num_vnics = len(virtual_compute.virtual_network_interface)

                # Compare actual values with expected values for number of vCPUs, vMemory vStorage and number of vNICs
                if actual_num_vcpus != expected_num_vcpus or \
                                actual_vmemory_size != expected_vmemory_size or \
                                actual_vstorage_size != expected_vstorage_size or \
                                actual_num_vnics != expected_num_vnics:
                    LOG.debug('For VNFC with id %s expected resources do not match the actual ones' % resource_id)
                    LOG.debug(
                        'Expected %s vCPU(s), actual number of vCPU(s): %s' % (expected_num_vcpus, actual_num_vcpus))
                    LOG.debug('Expected %s vMemory, actual vMemory: %s' % (expected_vmemory_size, actual_vmemory_size))
                    LOG.debug(
                        'Expected %s vStorage, actual vStorage: %s' % (expected_vstorage_size, actual_vstorage_size))
                    LOG.debug('Expected %s vNICs, actual number of vNICs: %s' % (expected_num_vnics, actual_num_vnics))
                    return False

                # Compare expected vNIC types with actual vNIC types
                for vnic in virtual_compute.virtual_network_interface:
                    actual_vnic_type = vnic.type_virtual_nic

                    # Find the name of the CP that has a cp_instance_id that matches the resource_id of this vNIC
                    for ext_cp in vnf_info.instantiated_vnf_info.ext_cp_info:
                        if ext_cp.cp_instance_id == vnic.resource_id:
                            cp_name = ext_cp.cpd_id
                            break

                    expected_vnic_type = expected_vnic_types.get(cp_name, '')
                    if expected_vnic_type != actual_vnic_type:
                        LOG.debug('For VNFC with id %s actual vNIC types do not match the expected ones' % resource_id)
                        LOG.debug('Expected "%s" type for the vNIC corresponding to CP %s, actual type: %s' %
                                  (expected_vnic_type, cp_name, actual_vnic_type))
                        return False

        return True

    @log_entry_exit(LOG)
    def verify_vnf_nsd_mapping(self, ns_instance_id, additional_param=None):
        ns_info = self.ns_query(filter={'ns_instance_id': ns_instance_id, 'additional_param': additional_param})
        nsd_id = ns_info.nsd_id
        nsd = self.get_nsd(nsd_id)
        for vnf_info in ns_info.vnf_info:
            # Get the VNF product name
            vnf_name = vnf_info.vnf_product_name

            # Get the node type from the NSD that corresponds to the above VNF name
            node_type = nsd['topology_template']['node_templates'].get(vnf_name, {}).get('type')
            if node_type is None:
                LOG.debug('NSD with ID %s does not have a node template named "%s"' % (nsd_id, vnf_name))
                return False

            # Check if the above node type is defined in the VNFD after which the VNF with the above name has been
            # deployed after
            vnfd_id = vnf_info.vnfd_id
            vnfd = self.get_vnfd(vnfd_id)
            if node_type not in vnfd['node_types'].keys():
                LOG.debug('VNFD with ID %s does not define the node type "%s"' % (vnfd_id, node_type))
                return False
        return True

    @log_entry_exit(LOG)
    def verify_vnf_sw_images(self, vnf_info):
        vnfd_id = vnf_info.vnfd_id
        vnfd = self.get_vnfd(vnfd_id)

        for vnfc_resource_info in vnf_info.instantiated_vnf_info.vnfc_resource_info:
            # Get image name from the VNFD for the VDU ID of the current VNFC
            vdu_id = vnfc_resource_info.vdu_id
            image_name_vnfd = vnfd['topology_template']['node_templates'][vdu_id]['properties']['image']

            # Get image name from VIM for the current VNFC
            vim_id = vnfc_resource_info.compute_resource.vim_id
            vim = self.get_vim_helper(vim_id)
            resource_id = vnfc_resource_info.compute_resource.resource_id
            virtual_compute = vim.query_virtualised_compute_resource(filter={'compute_id': resource_id})
            image_id = virtual_compute.vc_image_id
            image_details = vim.query_image(image_id)
            image_name_vim = image_details.name

            # The two image names should be identical
            if image_name_vnfd != image_name_vim:
                LOG.debug('Unexpected image for VNFC %s, VDU type %s' % (resource_id, vdu_id))
                LOG.debug('Expected image name: %s; actual image name: %s' % (image_name_vnfd, image_name_vim))
                return False

        return True

    @log_entry_exit(LOG)
    def get_vnfd_name_from_nsd_vnf_name(self, nsd_id, vnf_name):
        nsd = self.get_nsd(nsd_id)
        vnf_type = nsd['topology_template']['node_templates'][vnf_name]['type']
        for vnfd_name in nsd['imports']:
            vnfd = self.get_vnfd(vnfd_name)
            if vnf_type in vnfd['node_types'].keys():
                return vnfd_name
