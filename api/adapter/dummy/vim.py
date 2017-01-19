import logging

from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class VimDummyAdapter(object):
    def __init__(self, **kwargs):
        pass

    @log_entry_exit(LOG)
    def vim_query_compute(self, query_compute_filter):
        """
        This operation allows querying information about instantiated virtualized compute resources.

        This function was written in accordance with section 7.3.1.3 and 8.4.3 of GS NFV-IFA 005 - v2.1.1.

        :param query_compute_filter:        Query filter based on e.g. name, identifier, meta-data information or status
                                            information.
        :return:                            Element containing information about the virtual compute resource(s)
                                            matching the filter.
        """

        virtual_compute = {'compute_id': '',
                           'compute_name': '',
                           'flavour_id': '',
                           'acceleration_capability': '',
                           'virtual_cpu': {'cpu_architecture': '',
                                           'num_virtual_cpu': '',
                                           'virtual_cpu_clock': '',
                                           'virtual_cpu_oversubscriptionPolicy': '',
                                           'virtual_cpu_pinning': {'cpu_pinning_policy': '',
                                                                   'cpu_pinning_map': ''}},
                           'virtual_memory': {'virtual_mem_size': '',
                                              'virtual_mem_oversubscription_policy': '',
                                              'numa_enabled': ''},
                           'virtual_network_interface': {'resource_id': '',
                                                         'owner_id': '',
                                                         'network_id': '',
                                                         'network_port_id': '',
                                                         'ip_address': '',
                                                         'type_virtual_nic': '',
                                                         'type_configuration': '',
                                                         'mac_address': '',
                                                         'bandwidth': '',
                                                         'acceleration_capability': '',
                                                         'operational_state': '',
                                                         'metadata': ''},
                           'virtual_disks': '',
                           'vc_image_id': '',
                           'zone_id': '',
                           'host_id': '',
                           'operational_state': '',
                           'metadata': ''}

        return virtual_compute

    @log_entry_exit(LOG)
    def vim_query_network(self, query_network_filter):
        """
        This operation allows querying information about instantiated virtualized network resources.

        This function was written in accordance with section 7.4.1.3 and 8.4.5 of GS NFV-IFA 005 - v2.1.1.

        :param query_network_filter:        Query filter based on e.g. name, identifier, meta-data information or status
                                            information.
        :return:                            Element containing information about the virtual network resource(s)
                                            matching the filter.
        """

        virtual_network = {'network_resource_id': '',
                           'network_resource_name': '',
                           'subnet': '',
                           'network_port': {'resource_id': '',
                                            'network_id': '',
                                            'attached_resource_id': '',
                                            'port_type': '',
                                            'segment_id': '',
                                            'bandwidth': '',
                                            'operational_state': '',
                                            'metadata': ''},
                           'bandwidth': '',
                           'network_type': '',
                           'segment_type': '',
                           'network_qos': '',
                           'is_shared': '',
                           'sharing_data': '',
                           'zone_id': '',
                           'operational_state': '',
                           'metadata': ''}

        return virtual_network

    @log_entry_exit(LOG)
    def vim_query_storage(self, query_storage_filter):
        """
        This operation allows querying information about instantiated virtualized storage resources.

        This function was written in accordance with section 7.5.1.3 and 8.4.7 of GS NFV-IFA 005 - v2.1.1.

        :param query_storage_filter:        Query filter based on e.g. name, identifier, meta-data information or status
                                            information.
        :return:                            Element containing information about the virtual storage resource(s)
                                            matching the filter.
        """

        virtual_storage = {'storage_id': '',
                           'storage_name': '',
                           'flavour_id': '',
                           'type_of_storage': '',
                           'size_of_storage': '',
                           'rdma_enabled': '',
                           'owner_id': '',
                           'zone_id': '',
                           'host_id': '',
                           'operational_state': '',
                           'metadata': ''}

        return virtual_storage
