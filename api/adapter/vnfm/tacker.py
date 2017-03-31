import json
import logging
import re
import time

import os_client_config
import tackerclient.common.exceptions
import yaml
from tackerclient.tacker.client import Client as TackerClient

from api.adapter import construct_adapter
from api.generic import constants
from api.structures.objects import InstantiatedVnfInfo, VnfExtCpInfo, VnfInfo, VnfcResourceInfo, ResourceHandle
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class TackerVnfmAdapter(object):
    """
    Class of functions that map the ETSI standard operations exposed by the VNFM to the operations exposed by the
    OpenStack Tacker Client.
    """

    def __init__(self, auth_url=None, username=None, password=None, identity_api_version=None, project_name=None,
                 project_domain_name=None, user_domain_name=None):
        """
        Create the Tacker Client.
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
        This function does not have a direct mapping in OpenStack so it will just return the status of the VNF with
        given ID.
        """
        LOG.debug('"Lifecycle Operation Occurrence Id" is not implemented in OpenStack!')
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

            actual_num_virtual_cpu = virtual_compute.virtual_cpu.num_virtual_cpu
            actual_virtual_memory = virtual_compute.virtual_memory.virtual_mem_size
            actual_size_of_storage = virtual_compute.virtual_disks[0].size_of_storage

            expected_num_virtual_cpu = \
                vnfd['topology_template']['node_templates'][vnfc_resource_info.vdu_id]['capabilities']['nfv_compute'][
                    'properties']['num_cpus']
            expected_virtual_memory = \
                int(vnfd['topology_template']['node_templates'][vnfc_resource_info.vdu_id]['capabilities'][
                        'nfv_compute']['properties']['mem_size'].split(' ')[0])
            expected_size_of_storage = \
                int(vnfd['topology_template']['node_templates'][vnfc_resource_info.vdu_id]['capabilities'][
                        'nfv_compute']['properties']['disk_size'].split(' ')[0])

            if actual_num_virtual_cpu != expected_num_virtual_cpu or \
                            actual_virtual_memory != expected_virtual_memory or \
                            actual_size_of_storage != expected_size_of_storage:
                LOG.debug('Expected %s vCPU(s), actual number of vCPU(s): %s' % (expected_num_virtual_cpu,
                                                                                 actual_num_virtual_cpu))
                LOG.debug('Expected %s vMemory, actual vMemory: %s' % (expected_virtual_memory, actual_virtual_memory))
                LOG.debug('Expected %s vStorage, actual vStorage: %s' % (expected_size_of_storage,
                                                                         actual_size_of_storage))
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

            actual_num_virtual_cpu = virtual_compute.virtual_cpu.num_virtual_cpu
            actual_virtual_memory = virtual_compute.virtual_memory.virtual_mem_size
            actual_size_of_storage = virtual_compute.virtual_disks[0].size_of_storage

            vresources[resource_id]['num_virtual_cpu'] = actual_num_virtual_cpu
            vresources[resource_id]['virtual_memory'] = str(actual_virtual_memory) + ' MB'
            vresources[resource_id]['size_of_storage'] = str(actual_size_of_storage) + ' GB'

        return vresources

    @log_entry_exit(LOG)
    def modify_vnf_configuration(self, vnf_instance_id, vnf_configuration_data=None, ext_virtual_link=None):
        """
        This function enables providing configuration parameters information for a VNF instance.

        :param vnf_instance_id:         Identifier of the VNF instance.
        :param vnf_configuration_data:  Configuration data for the VNF instance.
        :param ext_virtual_link:        Information about external VLs to connect the VNF to.
        :return:                        True.
        """
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
        """
        This function creates a VNF with the specified ID and name.
        """
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
        """
        This function does not have a direct mapping in OpenStack so it will just return the VNF instance ID.

        :param vnf_instance_id: VNF instance identifier to be deleted.
        :return:                Nothing.
        """
        LOG.debug('"VNF Delete ID" operation is not implemented in OpenStack!')

    @log_entry_exit(LOG)
    def vnf_instantiate(self, vnf_instance_id, flavour_id, instantiation_level_id=None, ext_virtual_link=None,
                        ext_managed_virtual_link=None, localization_language=None, additional_param=None):
        """
        This function does not have a direct mapping in OpenStack so it will just return the VNF instance ID.

        :param vnf_instance_id:             Identifier of the VNF instance.
        :param flavour_id:                  Identifier of the VNF DF to be instantiated.
        :param instantiation_level_id:      Identifier of the instantiation level of the DF to be instantiated. If not
                                            present, the default instantiation level as declared in the VNFD shall be
                                            instantiated.
        :param ext_virtual_link:            Information about external VLs to connect the VNF to.
        :param ext_managed_virtual_link:    Information about internal VLs that are managed by other entities than the
                                            VNFM.
        :param localization_language:       Localization language of the VNF to be instantiated.
        :param additional_param:            Additional parameters passed as input to the instantiation process, specific
                                            to the VNF being instantiated.
        :return:                            VNF instance ID.
        """
        LOG.debug('"VNF Instantiate" operation is not implemented in OpenStack!')
        LOG.debug('Instead of "Lifecycle Operation Occurrence Id", will just return the "VNF Instance Id"')

        tup = ('vnf', vnf_instance_id)
        return tup

    @log_entry_exit(LOG)
    def vnf_operate(self, vnf_instance_id, change_state_to, stop_type=None, graceful_stop_timeout=None):
        """
        This function changes the state of a VNF instance.

        :param vnf_instance_id:             Identifier of the VNF instance.
        :param change_state_to:             Desired state to change the VNF to. Permitted values are: start, stop.
        :param stop_type:                   It signals whether forceful or graceful stop is requested. Allowed values
                                            are: forceful and graceful.
        :param graceful_stop_timeout:       Time interval to wait for the VNF to be taken out of service during
                                            graceful stop, before stopping the VNF.
        :return:                            The identifier of the VNF lifecycle operation occurrence.
        """
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
        """
        This operation provides information about VNF instances. The applicable VNF instances can be chosen based on
        filtering criteria, and the information can be restricted to selected attributes.

        :param filter:              Filter to select the VNF instance(s) about which information is queried.
        :param attribute_selector:  Provides a list of attribute names. If present, only these attributes are returned
                                    for the VNF instance(s) matching the filter. If absent, the complete information is
                                    returned for the VNF instance(s) matching the filter.
        :return:                    The information items about the selected VNF instance(s) that are returned. If
                                    attribute_selector is present, only the attributes listed in attribute_selector are
                                    returned for the selected VNF instance(s).
        """
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
        """
        This function scales a VNF horizontally (out/in).

        :param vnf_instance_id:     Identifier of the VNF instance to which this scaling request is related.
        :param scale_type:          Defines the type of the scale operation requested. Possible values: 'in', or 'out'
        :param aspect_id:           Identifies the aspect of the VNF that is requested to be scaled, as declared in the
                                    VNFD.
        :param number_of_steps:     Number of scaling steps to be executed as part of this ScaleVnf operation. Defaults
                                    to 1.
        :param additional_param:    Additional parameters passed by the NFVO as input to the scaling process, specific
                                    to the VNF being scaled.
        :return:                    Identifier of the VNF lifecycle operation occurrence.
        """
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
        """
        This function terminates the VNF with the given ID.

        :param vnf_instance_id:             Identifier of the VNF instance to be terminated.
        :param termination_type:            Signals whether forceful or graceful termination is requested.
        :param graceful_termination_type:   The time interval to wait for the VNF to be taken out of service during
                                            graceful termination, before shutting down the VNF and releasing the
                                            resources.
        :return:                            VNF instance ID.
        """
        try:
            self.tacker_client.delete_vnf(vnf_instance_id)
        except tackerclient.common.exceptions.NotFound:
            LOG.debug('VNF with instance ID %s could not be found' % vnf_instance_id)
            return None

        tup = ('vnf', vnf_instance_id)
        return tup
