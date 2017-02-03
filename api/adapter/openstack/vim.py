import logging

import os_client_config

from api.structures.objects import VirtualCompute, VirtualCpu, VirtualMemory, VirtualStorage
from utils.logging_module import log_entry_exit

LOG = logging.getLogger(__name__)


class VimOpenstackAdapter(object):
    def __init__(self, auth_url=None, username=None, password=None, identity_api_version=None, project_name=None,
                 project_domain_name=None, user_domain_name=None):
        try:
            self.nova_client = os_client_config.make_client('compute',
                                                            auth_url=auth_url,
                                                            username=username,
                                                            password=password,
                                                            identity_api_version=identity_api_version,
                                                            project_name=project_name,
                                                            project_domain_name=project_domain_name,
                                                            user_domain_name=user_domain_name)

        except:
            print 'Unable to create', self.__class__.__name__, 'instance'
            raise

    @log_entry_exit(LOG)
    def query_virtualised_network_resource(self, filter):
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

        return virtual_compute
