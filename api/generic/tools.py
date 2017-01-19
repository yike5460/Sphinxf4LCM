import logging

from utils.logging_module import log_entry_exit
from api.generic.vim import Vim

# Instantiate logger
LOG = logging.getLogger(__name__)


@log_entry_exit(LOG)
def vnfinfo_get_instantiation_state(vnfinfo_dict):
    """
    This function retrieves the value for key instantiation_state is as expected in the provided vnfInfo dictionary.

    :param logger:                          Reference to the logger object.
    :param vnfinfo_dict:                    vnfInfo dictionary.
    :return:                                True if the value for key instantiation_state is as expected, False
                                            otherwise.
    """
    vnf_instantiation_state = vnfinfo_dict.get('instantiation_state')
    LOG.debug('VNF state: %s' % vnf_instantiation_state)
    return vnf_instantiation_state


@log_entry_exit(LOG)
def vnfinfo_get_vnf_state(vnfinfo_dict):
    """
    This function retrieves the value for key vnf_state is as expected in the provided vnfInfo dictionary.

    :param logger:              Reference to the logger object.
    :param vnfinfo_dict:        vnfInfo dictionary.
    :return:                    True if the value for key vnf_state is as expected, False otherwise.
    """
    vnf_state = vnfinfo_dict.get('instantiated_vnf_info', {}).get('vnf_state')
    LOG.debug('VNF state: %s' % vnf_state)
    return vnf_state


@log_entry_exit(LOG)
def validate_allocated_vResources(vnf_vResource_list, instantiation_level_id, resource_type_list):
    """
    This function validates that the VNF has been assigned the expected vResources in the current state.

    :param vnf_vResource_list:          A list of lists containing dictionaries of the following structure:
                                        [[{'vnfc_instance_id': compute_resource_handle}],
                                         [{'virtual_link_instance_id': network_resource_handle}],
                                         [{'virtual_storage_instance_id': storage_resource_handle}]]
    :param instantiation_level_id:      Identifier of the target instantiation level of the current DF to which the
                                        VNF is requested to be validated.
    :param resource_type_list:          A list with types of vResources to be validated.
    :return:                            TRUE - vResources are the expected ones, FALSE - vResource mismatch.
    """

    if 'compute' in resource_type_list:
        vCPU_cores = 0
        vMemory = 0
        for compute_resource in vnf_vResource_list[0]:
            (vnfc_instance_id, compute_resource_handle) = compute_resource.items()
            virtual_compute = Vim.vim_query_compute(compute_resource_handle['resource_id'])
            vCPU_cores += virtual_compute['virtual_cpu']['num_virtual_cpu']
            vMemory += virtual_compute['virtual_memory']['virtual_mem_size']
    if 'network' in resource_type_list:
        vNic = []
        for network_resource in vnf_vResource_list[0]:
            (vnfc_instance_id, network_resource_handle) = network_resource.items()
            virtual_network = Vim.vim_query_network(network_resource_handle['resource_id'])
            vNic.append(virtual_network['network_port']['network_id'])
    if 'storage' in resource_type_list:
        vStorage = 0
        for storage_resource in vnf_vResource_list[0]:
            (vnfc_instance_id, storage_resource_handle) = storage_resource.items()
            virtual_storage = Vim.vim_query_storage(storage_resource_handle['resource_id'])
            vStorage += virtual_storage['size_of_storage']

    return True
