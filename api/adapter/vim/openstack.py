import logging

import os_client_config

from api.structures.objects import VirtualCompute, VirtualCpu, VirtualMemory, VirtualStorage, VirtualNetworkInterface
from utils.logging_module import log_entry_exit

LOG = logging.getLogger(__name__)


class OpenstackVimAdapter(object):
    """
    Class of functions that map the ETSI standard operations exposed by the VIM to the operations exposed by the
    OpenStack Heat, Neutron and Nova clients.
    """
    def __init__(self, auth_url=None, username=None, password=None, identity_api_version=None, project_name=None,
                 project_domain_name=None, user_domain_name=None, **kwargs):
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
                                                            user_domain_name=user_domain_name)

            self.neutron_client = os_client_config.make_client('network',
                                                               auth_url=auth_url,
                                                               username=username,
                                                               password=password,
                                                               identity_api_version=identity_api_version,
                                                               project_name=project_name,
                                                               project_domain_name=project_domain_name,
                                                               user_domain_name=user_domain_name)

            self.nova_client = os_client_config.make_client('compute',
                                                            auth_url=auth_url,
                                                            username=username,
                                                            password=password,
                                                            identity_api_version=identity_api_version,
                                                            project_name=project_name,
                                                            project_domain_name=project_domain_name,
                                                            user_domain_name=user_domain_name)

        except:
            LOG.debug('Unable to create %s instance' % self.__class__.__name__)
            raise

    @log_entry_exit(LOG)
    def query_virtualised_compute_resource(self, filter):
        virtual_compute = VirtualCompute()

        compute_id = filter['compute_id']
        virtual_compute.compute_id = compute_id

        nova_server = self.nova_client.servers.get(compute_id)
        server_flavor_id = nova_server.flavor['id']
        virtual_compute.flavour_id = server_flavor_id.encode()

        server_flavor = self.nova_client.flavors.get(server_flavor_id)

        virtual_cpu = VirtualCpu()
        virtual_cpu.num_virtual_cpu = server_flavor.vcpus
        virtual_compute.virtual_cpu = virtual_cpu

        virtual_memory = VirtualMemory()
        virtual_memory.virtual_mem_size = server_flavor.ram
        virtual_compute.virtual_memory = virtual_memory

        virtual_storage = VirtualStorage()
        virtual_storage.size_of_storage = server_flavor.disk
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

        return virtual_compute

    @log_entry_exit(LOG)
    def port_list(self, **query_filter):
        """
        This function gets the list of ports.

        :param query_filter:    Additional params.
        :return:                List of ports.
        """
        neutron_ports = self.neutron_client.list_ports(retrieve_all=False, **query_filter)
        return neutron_ports

    @log_entry_exit(LOG)
    def server_list(self, query_filter=None):
        """
        This function gets the list of servers.

        :param query_filter:    Filter out servers which don't match the search_opts (optional). The search opts format
                                is a dictionary of key / value pairs that will be appended to the query string.
        :return:                List of servers.
        """
        nova_servers = self.nova_client.servers.list(search_opts=query_filter)
        return nova_servers

    @log_entry_exit(LOG)
    def stack_get(self, stack_id):
        """
        This function gets the metadata for the specified stack ID.
        """
        stack_state = self.heat_client.stacks.get(stack_id)
        return stack_state

    @log_entry_exit(LOG)
    def stack_resume(self, stack_id):
        """
        This function resumes the stack with the given ID.
        """
        self.heat_client.actions.resume(stack_id)

    @log_entry_exit(LOG)
    def stack_suspend(self, stack_id):
        """
        This function suspends the stack with the given ID.
        """
        self.heat_client.actions.suspend(stack_id)
