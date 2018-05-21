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


import logging
from novaclient.exceptions import NotFound

import os_client_config

from api.adapter.vim import VimAdapterError
from api.generic import constants
from api.structures.objects import VirtualCompute, VirtualCpu, VirtualMemory, VirtualStorage, VirtualNetworkInterface, \
    VirtualComputeQuota, VirtualNetworkQuota, VirtualStorageQuota, SoftwareImageInformation
from utils.logging_module import log_entry_exit

LOG = logging.getLogger(__name__)


class OpenstackVimAdapterError(VimAdapterError):
    """
    A problem occurred in the VNF LifeCycle Validation Openstack VIM adapter API.
    """
    pass


class OpenstackVimAdapter(object):
    """
    Class of functions that map the ETSI standard operations exposed by the VIM to the operations exposed by the
    OpenStack Heat, Neutron and Nova clients.
    """

    def __init__(self, auth_url=None, username=None, password=None, identity_api_version=None, project_name=None,
                 project_domain_name=None, user_domain_name=None, verify=False, **kwargs):
        """
        Create the Heat, Neutron and Nova clients.
        """
        try:
            self.heat_client = os_client_config.make_client('orchestration',
                                                            auth_url=auth_url,
                                                            username=username,
                                                            password=password,
                                                            identity_api_version=identity_api_version,
                                                            project_name=project_name,
                                                            project_domain_name=project_domain_name,
                                                            user_domain_name=user_domain_name,
                                                            verify=verify)

            self.neutron_client = os_client_config.make_client('network',
                                                               auth_url=auth_url,
                                                               username=username,
                                                               password=password,
                                                               identity_api_version=identity_api_version,
                                                               project_name=project_name,
                                                               project_domain_name=project_domain_name,
                                                               user_domain_name=user_domain_name,
                                                               verify=verify)

            self.nova_client = os_client_config.make_client('compute',
                                                            auth_url=auth_url,
                                                            username=username,
                                                            password=password,
                                                            identity_api_version=identity_api_version,
                                                            project_name=project_name,
                                                            project_domain_name=project_domain_name,
                                                            user_domain_name=user_domain_name,
                                                            verify=verify)

            self.cinder_client = os_client_config.make_client('volume',
                                                              auth_url=auth_url,
                                                              username=username,
                                                              password=password,
                                                              identity_api_version=identity_api_version,
                                                              project_name=project_name,
                                                              project_domain_name=project_domain_name,
                                                              user_domain_name=user_domain_name,
                                                              verify=verify)

            self.glance_client = os_client_config.make_client('image',
                                                              auth_url=auth_url,
                                                              username=username,
                                                              password=password,
                                                              identity_api_version=identity_api_version,
                                                              project_name=project_name,
                                                              project_domain_name=project_domain_name,
                                                              user_domain_name=user_domain_name,
                                                              verify=verify)

        except Exception as e:
            LOG.exception(e)
            raise OpenstackVimAdapterError('Unable to create %s instance - %s' % (self.__class__.__name__, e))

    @log_entry_exit(LOG)
    def get_operation_status(self, operation_id):
        if operation_id is None:
            raise OpenstackVimAdapterError('Operation ID is absent')
        else:
            operation_type, resource_id = operation_id

        if operation_type == 'server_terminate':
            try:
                self.nova_client.servers.get(resource_id)
            except NotFound:
                LOG.debug('Resource ID %s no longer present in VIM, as expected' % resource_id)
                return constants.OPERATION_SUCCESS
            except Exception as e:
                LOG.exception(e)
                return constants.OPERATION_PENDING
            else:
                LOG.debug('Resource ID %s still present in VIM, not as expected' % resource_id)
                return constants.OPERATION_PENDING

    @log_entry_exit(LOG)
    def create_compute_resource_reservation(self, resource_group_id, compute_pool_reservation=None,
                                            virtualisation_container_reservation=None, affinity_constraint=None,
                                            anti_affinity_constraint=None, start_time=None, end_time=None,
                                            expiry_time=None, location_constraints=None):
        LOG.debug('Reservations are not implemented in Openstack yet')
        raise NotImplementedError

    @log_entry_exit(LOG)
    def terminate_compute_resource_reservation(self, reservation_id):
        LOG.debug('Reservations are not implemented in Openstack yet')
        raise NotImplementedError

    @log_entry_exit(LOG)
    def create_storage_resource_reservation(self, resource_group_id, storage_pool_reservation=None, start_time=None,
                                            end_time=None, expiry_time=None, affinity_constraint=None,
                                            anti_affinity_constraint=None, location_constraints=None):
        LOG.debug('Reservations are not implemented in Openstack yet')
        raise NotImplementedError

    @log_entry_exit(LOG)
    def terminate_storage_resource_reservation(self, reservation_id):
        LOG.debug('Reservations are not implemented in Openstack yet')
        raise NotImplementedError

    def get_resource_group_id(self):
        try:
            project_id = self.nova_client.client.session.auth.auth_ref._data['token']['project']['id']
        except Exception as e:
            LOG.exception(e)
            raise OpenstackVimAdapterError('Unable to get project ID - %s' % e)
        return project_id.encode()

    @log_entry_exit(LOG)
    def query_virtualised_compute_resource(self, filter):
        virtual_compute = VirtualCompute()

        compute_id = filter['compute_id']
        virtual_compute.compute_id = compute_id
        server_details = self.server_get(compute_id)
        server_flavor_id = server_details['flavor_id']
        virtual_compute.flavour_id = server_flavor_id
        server_status = server_details['status']
        if server_status == 'ACTIVE':
            virtual_compute.operational_state = 'ENABLED'
        else:
            virtual_compute.operational_state = 'DISABLED'
        flavor_details = self.flavor_get(server_flavor_id)

        virtual_cpu = VirtualCpu()
        virtual_cpu.num_virtual_cpu = flavor_details['vcpus']
        virtual_compute.virtual_cpu = virtual_cpu

        virtual_memory = VirtualMemory()
        virtual_memory.virtual_mem_size = flavor_details['ram']
        virtual_compute.virtual_memory = virtual_memory

        virtual_storage = VirtualStorage()
        virtual_storage.size_of_storage = flavor_details['disk']
        virtual_compute.virtual_disks = [virtual_storage]

        virtual_compute.virtual_network_interface = list()
        port_dict = self.port_list(device_id=compute_id)
        for port_list in port_dict:
            for port in port_list['ports']:
                virtual_network_interface = VirtualNetworkInterface()
                virtual_network_interface.resource_id = port['id'].encode()
                virtual_network_interface.owner_id = port['device_id'].encode()
                virtual_network_interface.network_id = port['network_id'].encode()
                virtual_network_interface.type_virtual_nic = port['binding:vnic_type'].encode()
                virtual_network_interface.mac_address = port['mac_address'].encode()
                virtual_network_interface.acceleration_capability = list()
                virtual_compute.virtual_network_interface.append(virtual_network_interface)

        virtual_compute.vc_image_id = server_details['image_id']
        # TODO: What should the function return when the specified resources are not found?
        return virtual_compute

    @log_entry_exit(LOG)
    def trigger_compute_resource_termination(self, identifier):
        try:
            self.nova_client.servers.force_delete(identifier)
        except Exception as e:
            LOG.exception(e)
            raise OpenstackVimAdapterError('Unable to delete server %s - %s' % (identifier, e))
        return 'server_terminate', identifier

    @log_entry_exit(LOG)
    def port_list(self, **query_filter):
        """
        This function gets the list of ports.

        :param query_filter:    Additional params.
        :return:                List of ports.
        """
        try:
            neutron_ports = self.neutron_client.list_ports(retrieve_all=False, **query_filter)
        except Exception as e:
            LOG.exception(e)
            raise OpenstackVimAdapterError('Unable to get the list of ports - %s' % e)
        return neutron_ports

    @log_entry_exit(LOG)
    def server_list(self, query_filter=None):
        """
        This function gets the list of servers.

        :param query_filter:    Filter out servers which don't match the search_opts (optional). The search opts format
                                is a dictionary of key / value pairs that will be appended to the query string.
        :return:                List of 'Server' objects.
        """
        try:
            nova_servers = self.nova_client.servers.list(search_opts=query_filter)
        except Exception as e:
            LOG.exception(e)
            raise OpenstackVimAdapterError('Unable to get the list of servers - %s' % e)
        return nova_servers

    @log_entry_exit(LOG)
    def server_get(self, server_id):
        """
        This function retrieves the details for the server with the given ID.

        :param server_id:   ID of the server to get details for.
        :return:            Dictionary with server details.
        """
        try:
            server = self.nova_client.servers.get(server_id)
        except Exception as e:
            LOG.exception(e)
            raise OpenstackVimAdapterError('Unable to get details for server %s - %s' % (server_id, e))

        server_details = dict()
        server_details['flavor_id'] = server.flavor['id'].encode()
        server_details['hostId'] = server.hostId.encode()
        server_details['image_id'] = server.image['id'].encode()
        server_details['name'] = server.name.encode()
        server_details['status'] = server.status.encode()
        server_details['user_id'] = server.user_id.encode()

        return server_details

    @log_entry_exit(LOG)
    def stack_get(self, stack_id):
        """
        This function gets the metadata for the specified stack ID.
        """
        try:
            stack_state = self.heat_client.stacks.get(stack_id)
        except Exception as e:
            LOG.exception(e)
            raise OpenstackVimAdapterError('Unable to get details for stack %s - %s' % (stack_id, e))
        return stack_state

    @log_entry_exit(LOG)
    def stack_resume(self, stack_id):
        """
        This function resumes the stack with the given ID.
        """
        try:
            self.heat_client.actions.resume(stack_id)
        except Exception as e:
            LOG.exception(e)
            raise OpenstackVimAdapterError('Unable to resume stack %s - %s' % (stack_id, e))

    @log_entry_exit(LOG)
    def stack_suspend(self, stack_id):
        """
        This function suspends the stack with the given ID.
        """
        try:
            self.heat_client.actions.suspend(stack_id)
        except Exception as e:
            LOG.exception(e)
            raise OpenstackVimAdapterError('Unable to suspend stack %s - %s' % (stack_id, e))

    @log_entry_exit(LOG)
    def stack_resource_list(self, stack_id):
        """
        This function shows a list of resources belonging to a stack.

        :param stack_id:    ID of the stack to show the resources for.
        :return:            List of 'Resource' objects.
        """
        try:
            stack_resource_list = self.heat_client.resources.list(stack_id)
        except Exception as e:
            LOG.exception(e)
            raise OpenstackVimAdapterError('Unable to get resources for stack %s - %s' % (stack_id, e))
        return stack_resource_list

    @log_entry_exit(LOG)
    def query_compute_capacity(self, zone_id, compute_resource_type_id, resource_criteria, attribute_selector,
                               time_period):
        limits = dict()
        resource_types = ['vcpu', 'vmem', 'instances']

        for resource_type in resource_types:
            limits[resource_type] = dict()

        try:
            nova_limits = self.nova_client.limits.get().absolute
        except Exception as e:
            LOG.exception(e)
            raise OpenstackVimAdapterError('Unable to get compute capacity - %s' % e)
        for nova_limit in nova_limits:
            if nova_limit.name == 'totalCoresUsed':
                limits['vcpu']['used'] = nova_limit.value
            elif nova_limit.name == 'maxTotalCores':
                limits['vcpu']['max'] = nova_limit.value
            elif nova_limit.name == 'totalRAMUsed':
                limits['vmem']['used'] = nova_limit.value
            elif nova_limit.name == 'maxTotalRAMSize':
                limits['vmem']['max'] = nova_limit.value
            elif nova_limit.name == 'totalInstancesUsed':
                limits['instances']['used'] = nova_limit.value
            elif nova_limit.name == 'maxTotalInstances':
                limits['instances']['max'] = nova_limit.value

        return limits

    @log_entry_exit(LOG)
    def query_storage_capacity(self, zone_id, storage_resource_type_id, resource_criteria, attribute_selector,
                               time_period):
        limits = dict()
        resource_types = ['vstorage']

        for resource_type in resource_types:
            limits[resource_type] = dict()

        try:
            cinder_limits = self.cinder_client.limits.get().absolute
        except Exception as e:
            LOG.exception(e)
            raise OpenstackVimAdapterError('Unable to get storage capacity - %s' % e)
        for cinder_limit in cinder_limits:
            if cinder_limit.name == 'totalGigabytesUsed':
                limits['vstorage']['used'] = cinder_limit.value
            elif cinder_limit.name == 'maxTotalVolumeGigabytes':
                limits['vstorage']['max'] = cinder_limit.value

        return limits

    @log_entry_exit(LOG)
    def query_compute_resource_quota(self, filter):
        """
        This function gets quota information for resources specified in the filter for project_id retrieved from nova.
        """
        project_id = self.get_resource_group_id()
        try:
            quotas = self.nova_client.quotas.get(tenant_id=project_id)
        except Exception as e:
            LOG.exception(e)
            raise OpenstackVimAdapterError('Unable to get compute resource quota - %s' % e)
        virtual_compute_quota = VirtualComputeQuota()
        virtual_compute_quota.resource_group_id = quotas._info['id'].encode()
        resources = {'num_vcpus': quotas.cores, 'num_vc_instances': quotas.instances, 'virtual_mem_size': quotas.ram}
        for item, value in resources.items():
            if value != -1:
                setattr(virtual_compute_quota, item, value)
        return virtual_compute_quota

    @log_entry_exit(LOG)
    def query_network_resource_quota(self, filter):
        """
        This function gets quota information for resources specified in the filter for project_id retrieved from
        neutron.
        """
        project_id = self.get_resource_group_id()
        try:
            quotas = self.neutron_client.show_quota(project_id)
        except Exception as e:
            LOG.exception(e)
            raise OpenstackVimAdapterError('Unable to get network resource quota - %s' % e)
        virtual_network_quota = VirtualNetworkQuota()
        virtual_network_quota.resource_group_id = project_id.encode()
        resources = {'num_public_ips': quotas['quota']['floatingip'], 'num_ports': quotas['quota']['port'],
                     'num_subnets': quotas['quota']['subnet']}
        for item, value in resources.items():
            if value != -1:
                setattr(virtual_network_quota, item, value)
        return virtual_network_quota

    @log_entry_exit(LOG)
    def query_storage_resource_quota(self, filter):
        """
        This function gets quota information for resources specified in the filter for project_id retrieved from
        neutron.
        """
        project_id = self.get_resource_group_id()
        try:
            quotas = self.cinder_client.quotas.get(project_id)
        except Exception as e:
            LOG.exception(e)
            raise OpenstackVimAdapterError('Unable to get storage resource quota - %s' % e)
        virtual_storage_quota = VirtualStorageQuota()
        virtual_storage_quota.resource_group_id = project_id.encode()
        resources = {'storage_size': quotas.gigabytes, 'num_snapshots': quotas.snapshots,
                     'num_volumes': quotas.volumes}
        for item, value in resources.items():
            if value != -1:
                setattr(virtual_storage_quota, item, value)
        return virtual_storage_quota

    @log_entry_exit(LOG)
    def flavor_get(self, flavor_id):
        """
        This function retrieves the details for the flavor with the given ID.

        :param flavor_id:   ID of the flavor to get details for.
        :return:            Dictionary with flavor details.
        """
        try:
            flavor = self.nova_client.flavors.get(flavor_id)
        except Exception as e:
            LOG.exception(e)
            raise OpenstackVimAdapterError('Unable to get details for flavor %s - %s' % (flavor_id, e))

        flavor_details = dict()
        flavor_details['name'] = flavor.name
        flavor_details['vcpus'] = flavor.vcpus
        flavor_details['ram'] = flavor.ram
        flavor_details['disk'] = flavor.disk

        return flavor_details

    @log_entry_exit(LOG)
    def query_image(self, image_id):
        try:
            image = self.glance_client.images.get(image_id)
        except Exception as e:
            LOG.exception(e)
            raise OpenstackVimAdapterError('Unable to get details for image %s - %s' % (image_id, e))

        software_image_information = SoftwareImageInformation()
        software_image_information.id = image_id
        software_image_information.name = image.name.encode()
        software_image_information.created_at = image.created_at.encode()
        software_image_information.updated_at = image.updated_at.encode()
        software_image_information.min_disk = image.min_disk
        software_image_information.min_ram = image.min_ram

        return software_image_information
