import json
import logging
import re
import time
import uuid

import os_client_config
from threading import Timer

import tackerclient.common.exceptions
import yaml
from tackerclient.tacker.client import Client as TackerClient

from api.adapter import construct_adapter
from api.generic import constants
from api.structures.objects import InstantiatedVnfInfo, VnfExtCpInfo, VnfInfo, VnfcResourceInfo, ResourceHandle, \
    VnfLifecycleChangeNotification
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


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

        except:
            LOG.debug('Unable to create %s instance' % self.__class__.__name__)
            raise

    @log_entry_exit(LOG)
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        """
        This function does not have a direct mapping in OpenStack Tacker client so it will just return the status of the
        VNF with given ID.
        """
        LOG.debug('"Lifecycle Operation Occurrence Id" is not implemented in OpenStack Tacker client!')
        LOG.debug('Will return the state of the resource with given Id')

        if lifecycle_operation_occurrence_id is None:
            return constants.OPERATION_FAILED
        else:
            resource_type, resource_id = lifecycle_operation_occurrence_id

        if resource_type == 'vnf':
            try:
                tacker_show_vnf = self.tacker_client.show_vnf(resource_id)
            except tackerclient.common.exceptions.NotFound:
                # Temporary workaround. When vnf_terminate() is called, declare the VNF as terminated when Tacker raises
                # exception because the VNF can no longer be found
                return constants.OPERATION_SUCCESS

            tacker_status = tacker_show_vnf['vnf']['status']

            return constants.OPERATION_STATUS['OPENSTACK_VNF_STATE'][tacker_status]

        if resource_type == 'stack':
            # Get VNF information from Tacker
            tacker_show_vnf = self.tacker_client.show_vnf(resource_id)['vnf']

            # Get VIM object
            vim_id = tacker_show_vnf['vim_id']
            vim = self.get_vim_helper(vim_id)

            # Get the Heat stack ID from Tacker information
            stack_id = tacker_show_vnf['instance_id']

            # Get the Heat stack status
            heat_stack = vim.stack_get(stack_id)
            stack_status = heat_stack.stack_status

            return constants.OPERATION_STATUS['OPENSTACK_STACK_STATE'][stack_status]

    @log_entry_exit(LOG)
    def limit_compute_resources_for_ns_scaling(self, nsd_id, default_instances, desired_scale_out_steps, scaling_step,
                                               generic_vim_object):
        raise NotImplementedError

    @log_entry_exit(LOG)
    def limit_compute_resources_for_vnf_instantiation(self, vnfd_id, default_instances, generic_vim_object):
        vnfd = self.get_vnfd(vnfd_id)

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

        # Increase the total required compute resources by one to make sure the instantiation will not be possible.
        required_vcpus = default_instances * vcpus_req_one_inst + 1
        required_vmem = default_instances * vmem_req_one_inst + 1
        required_vc_instances = default_instances * vc_instances_req_one_inst + 1

        reservation_id = generic_vim_object.limit_compute_resources(required_vcpus, required_vmem,
                                                                    required_vc_instances)

        return reservation_id

    @log_entry_exit(LOG)
    def limit_compute_resources_for_vnf_scaling(self, vnfd_id, default_instances, desired_scale_out_steps, scaling_step,
                                                generic_vim_object):
        vnfd = self.get_vnfd(vnfd_id)

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

        # Total required compute resources
        required_vcpus = (desired_scale_out_steps * scaling_step + default_instances) * vcpus_req_one_inst
        required_vmem = (desired_scale_out_steps * scaling_step + default_instances) * vmem_req_one_inst
        required_vc_instances = (desired_scale_out_steps * scaling_step + default_instances) * vc_instances_req_one_inst

        reservation_id = generic_vim_object.limit_compute_resources(required_vcpus, required_vmem,
                                                                    required_vc_instances)

        return reservation_id

    @log_entry_exit(LOG)
    def get_vim_helper(self, vim_id):
        vim_details = self.tacker_client.show_vim(vim_id)['vim']
        vim_auth_cred = vim_details['auth_cred']
        vim_type = vim_details['type']

        # TODO: get from config file
        vim_auth_cred['password'] = 'stack'

        return construct_adapter(vim_type, module_type='vim', **vim_auth_cred)

    @log_entry_exit(LOG)
    def get_vnfd(self, vnfd_id):
        # TODO: translate to ETSI VNFD
        return yaml.load(self.tacker_client.show_vnfd(vnfd_id)['vnfd']['attributes']['vnfd'])

    def validate_allocated_vresources(self, vnfd_id, vnf_instance_id):
        vnf_info = self.vnf_query(filter={'vnf_instance_id': vnf_instance_id})
        vnfd = self.get_vnfd(vnfd_id)

        for vnfc_resource_info in vnf_info.instantiated_vnf_info.vnfc_resource_info:
            vim_id = vnfc_resource_info.compute_resource.vim_id
            vim = self.get_vim_helper(vim_id)

            resource_id = vnfc_resource_info.compute_resource.resource_id
            virtual_compute = vim.query_virtualised_compute_resource(filter={'compute_id': resource_id})

            expected_num_virtual_cpu = \
                vnfd['topology_template']['node_templates'][vnfc_resource_info.vdu_id]['capabilities']['nfv_compute'][
                    'properties']['num_cpus']
            expected_virtual_memory = \
                int(vnfd['topology_template']['node_templates'][vnfc_resource_info.vdu_id]['capabilities'][
                        'nfv_compute']['properties']['mem_size'].split(' ')[0])
            expected_size_of_storage = \
                int(vnfd['topology_template']['node_templates'][vnfc_resource_info.vdu_id]['capabilities'][
                        'nfv_compute']['properties']['disk_size'].split(' ')[0])

            expected_vnic_type = dict()
            for node in vnfd['topology_template']['node_templates'].keys():
                if vnfd['topology_template']['node_templates'][node]['type'] == 'tosca.nodes.nfv.CP.Tacker':
                    expected_vnic_type[node] = vnfd['topology_template']['node_templates'][node]['properties'].get(
                        'type', 'normal')

            actual_num_virtual_cpu = virtual_compute.virtual_cpu.num_virtual_cpu
            actual_virtual_memory = virtual_compute.virtual_memory.virtual_mem_size
            actual_size_of_storage = virtual_compute.virtual_disks[0].size_of_storage

            if actual_num_virtual_cpu != expected_num_virtual_cpu or \
                            actual_virtual_memory != expected_virtual_memory or \
                            actual_size_of_storage != expected_size_of_storage:
                LOG.debug('Expected %s vCPU(s), actual number of vCPU(s): %s' % (expected_num_virtual_cpu,
                                                                                 actual_num_virtual_cpu))
                LOG.debug('Expected %s vMemory, actual vMemory: %s' % (expected_virtual_memory, actual_virtual_memory))
                LOG.debug('Expected %s vStorage, actual vStorage: %s' % (expected_size_of_storage,
                                                                         actual_size_of_storage))
                return False

            for vnic in virtual_compute.virtual_network_interface:
                actual_vnic_type = vnic.type_virtual_nic

                # Find the name of the CP that has a cp_instance_id that matches the resource_id of this vnic
                for ext_cp in vnf_info.instantiated_vnf_info.ext_cp_info:
                    if ext_cp.cp_instance_id == vnic.resource_id:
                        cp_name = ext_cp.cpd_id
                        break

                if expected_vnic_type.get(cp_name, '') != actual_vnic_type:
                    return False

        return True

    @log_entry_exit(LOG)
    def get_allocated_vresources(self, vnf_instance_id):
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
            self.tacker_client.update_vnf(vnf_instance_id, body=vnf_attributes)

        # Poll on the VNF status until it reaches one of the final states
        operation_pending = True
        elapsed_time = 0
        max_wait_time = 300
        poll_interval = 5
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
            LOG.debug('Response from vnfm:\n%s' % json.dumps(vnf_instance, indent=4, separators=(',', ': ')))
        except tackerclient.common.exceptions.TackerException:
            return None
        return vnf_instance['vnf']['id']

    @log_entry_exit(LOG)
    def vnf_delete_id(self, vnf_instance_id):
        LOG.debug('"VNF Delete ID" operation is not implemented in OpenStack Tacker client!')

    @log_entry_exit(LOG)
    def vnf_instantiate(self, vnf_instance_id, flavour_id, instantiation_level_id=None, ext_virtual_link=None,
                        ext_managed_virtual_link=None, localization_language=None, additional_param=None):
        LOG.debug('"VNF Instantiate" operation is not implemented in OpenStack Tacker client!')
        LOG.debug('Instead of "Lifecycle Operation Occurrence Id", will just return the "VNF Instance Id"')

        tup = ('vnf', vnf_instance_id)
        return tup

    @log_entry_exit(LOG)
    def vnf_operate(self, vnf_instance_id, change_state_to, stop_type=None, graceful_stop_timeout=None):
        # Get VNF information from Tacker
        tacker_show_vnf = self.tacker_client.show_vnf(vnf_instance_id)['vnf']

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
            LOG.debug('VNF successfully started')
        # Stopping a VNF is translated to suspending the HEAT stack
        elif change_state_to == 'stop' and vnf_state == constants.VNF_STARTED:
            vim.stack_suspend(stack_id)
            LOG.debug('VNF successfully stopped')
        else:
            LOG.debug('VNF is already in the desired state')

        tup = ('stack', vnf_instance_id)
        return tup

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

        # Build the InstantiatedVnfInfo information element only if the VNF is in INSTANTIATED state
        if vnf_info.instantiation_state == constants.VNF_INSTANTIATED:
            vnf_info.instantiated_vnf_info = InstantiatedVnfInfo()
            vnf_info.instantiated_vnf_info.vnf_state = constants.VNF_STATE['OPENSTACK_STACK_STATE'][
                heat_stack.stack_status]

            vnf_info.instantiated_vnf_info.vnfc_resource_info = list()
            try:
                tacker_list_vnf_resources = self.tacker_client.list_vnf_resources(vnf_instance_id)['resources']
                for vnf_resource in tacker_list_vnf_resources:
                    # When the VNFD contains scaling policies, Heat will not show the resources (VDUs, CPs, VLs, etc),
                    # but the scaling group.
                    # In this case, grab the resources from Nova and break out of the for loop.
                    if vnf_resource.get('type').__contains__('Scaling'):

                        # Get the Nova list of servers filtering the servers based on their name.
                        # The servers' names we are looking for start with ta-...
                        # Example ta-hnrt7a-xvlcnwn2nphm-t5vjqah6itlt-VDU1-jyettvu5bvkg
                        server_list = vim.server_list(query_filter={'name': 'ta-*'})
                        for server in server_list:
                            vnf_resource_id = server.id

                            # Extract the VDU ID from the server name
                            match = re.search('VDU\d+', server.name)
                            if match:
                                vnf_resource_name = match.group()

                            # Build the VnfcResourceInfo data structure
                            vnfc_resource_info = VnfcResourceInfo()
                            vnfc_resource_info.vnfc_instance_id = vnf_resource_id.encode()
                            vnfc_resource_info.vdu_id = vnf_resource_name.encode()

                            vnfc_resource_info.compute_resource = ResourceHandle()
                            vnfc_resource_info.compute_resource.vim_id = vim_id.encode()
                            vnfc_resource_info.compute_resource.resource_id = vnf_resource_id.encode()

                            vnf_info.instantiated_vnf_info.vnfc_resource_info.append(vnfc_resource_info)

                        break

                    # Heat provides the resources as expected.
                    else:
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

                            vnf_info.instantiated_vnf_info.ext_cp_info.append(vnf_ext_cp_info)

            except tackerclient.common.exceptions.TackerException:
                return vnf_info

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
        except tackerclient.common.exceptions.NotFound:
            LOG.debug('Either VNF with instance ID %s does not exist or it does not have a scaling policy "%s"' %
                      (vnf_instance_id, additional_param['scaling_policy_name']))
            return None

        tup = ('vnf', vnf_instance_id)
        return tup

    @log_entry_exit(LOG)
    def vnf_terminate(self, vnf_instance_id, termination_type, graceful_termination_type=None):
        try:
            self.tacker_client.delete_vnf(vnf_instance_id)
        except tackerclient.common.exceptions.NotFound:
            LOG.debug('VNF with instance ID %s could not be found' % vnf_instance_id)
            return None

        tup = ('vnf', vnf_instance_id)
        return tup

    @log_entry_exit(LOG)
    def ns_lifecycle_change_notification_subscribe(self, notification_filter=None):
        raise NotImplementedError

    @log_entry_exit(LOG)
    def vnf_lifecycle_change_notification_subscribe(self, notification_filter):
        # TODO: implement notification filter
        last_vnf_event_id = list(self._get_vnf_events())[-1]['id']
        print 'Got last event id: %d' % last_vnf_event_id  # TODO: use logger instead of print

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

        vnf_events = self.tacker_client.list_vnf_events(**params)['vnf_events']
        if starting_from is not None:
            vnf_events = (vnf_event for vnf_event in vnf_events if vnf_event['id'] > starting_from)

        return vnf_events
