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
import time

from api.adapter.mano import ManoAdapterError
from api.generic import constants
from api.structures.objects import InstantiatedVnfInfo, VnfInfo, VnfcResourceInfo, ResourceHandle, NsInfo
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class DummyManoAdapterError(ManoAdapterError):
    """
    A problem occurred in the VNF LifeCycle Validation Dummy MANO adapter API.
    """
    pass


class DummyManoAdapter(object):
    """
    Class of functions that map the generic operations exposed by the MANO to dummy client.
    """

    def __init__(self, auth_url=None, username=None, password=None, identity_api_version=None, project_name=None,
                 project_domain_name=None, user_domain_name=None):
        pass

    @log_entry_exit(LOG)
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        """
        This function does not have a direct mapping so it will just return the status of the VNF with given ID.
        """
        LOG.debug('"Lifecycle Operation Occurrence Id" is not implemented in OpenStack Tacker client!')
        LOG.debug('Will return the state of the resource with given Id')

        return constants.OPERATION_SUCCESS

    @log_entry_exit(LOG)
    def poll_for_operation_completion(self, lifecycle_operation_occurrence_id, final_states, max_wait_time,
                                      poll_interval):
        operation_pending = True
        elapsed_time = 0

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
    def validate_vnf_allocated_vresources(self, vnf_info, additional_param=None):
        return True

    @log_entry_exit(LOG)
    def get_allocated_vresources(self, vnf_instance_id, additional_param=None):
        vnf_info = self.vnf_query(filter={'vnf_instance_id': vnf_instance_id})

        vresources = {}

        for vnfc_resource_info in vnf_info.instantiated_vnf_info.vnfc_resource_info:
            resource_id = vnfc_resource_info.compute_resource.resource_id
            vresources[resource_id] = {}
            vresources[resource_id]['vCPU'] = '1'
            vresources[resource_id]['vMemory'] = '64 MB'
            vresources[resource_id]['vStorage'] = '1 GB'
            vresources[resource_id]['vNIC'] = '3'

        return vresources

    @log_entry_exit(LOG)
    def ns_create_id(self, nsd_id, ns_name, ns_description):
        ns_instance_id = 'ns_instance_id'
        return ns_instance_id

    @log_entry_exit(LOG)
    def ns_delete_id(self, ns_instance_id):
        return

    @log_entry_exit(LOG)
    def ns_instantiate(self, ns_instance_id, flavour_id, sap_data=None, pnf_info=None, vnf_instance_data=None,
                       nested_ns_instance_data=None, location_constraints=None, additional_param_for_ns=None,
                       additional_param_for_vnf=None, start_time=None, ns_instantiation_level_id=None,
                       additional_affinity_or_anti_affinity_rule=None):
        lifecycle_operation_occurrence_id = 'ns_instantiate_operation_id'

        LOG.debug('Lifecycle operation occurrence ID: %s' % lifecycle_operation_occurrence_id)

        return lifecycle_operation_occurrence_id

    @log_entry_exit(LOG)
    def ns_query(self, filter, attribute_selector=None):
        ns_instance_id = filter['ns_instance_id']
        ns_info = NsInfo
        ns_info.ns_instance_id = ns_instance_id
        ns_info.ns_name = 'ns_name'
        ns_info.description = 'ns_description'
        ns_info.nsd_id = 'nsd_id'
        ns_info.ns_state = 'INSTANTIATED'
        ns_info.vnf_info_id = ['vnf_info_id1', 'vnf_info_id2']

        return ns_info

    @log_entry_exit(LOG)
    def ns_scale(self, ns_instance_id, scale_type, scale_ns_data=None, scale_vnf_data=None, scale_time=None):
        ns_instance_id = 'ns_instance_id'
        return 'vnf', ns_instance_id

    @log_entry_exit(LOG)
    def ns_terminate(self, ns_instance_id, terminate_time=None, additional_param=None):
        ns_instance_id = 'ns_instance_id'
        return 'vnf', ns_instance_id

    @log_entry_exit(LOG)
    def vnf_query(self, filter, attribute_selector=None):
        vnf_instance_id = filter['vnf_instance_id']
        vnf_info = VnfInfo()
        vnf_info.vnf_instance_id = str(vnf_instance_id)

        # Build the vnf_info data structure
        vnf_info.vnf_instance_name = 'instance_name'
        vnf_info.vnf_instance_description = 'instance_description'
        vnf_info.vnfd_id = 'vnfd_id'
        vnf_info.instantiation_state = 'INSTANTIATED'

        # Build the InstantiatedVnfInfo information element only if the VNF is in INSTANTIATED state
        if vnf_info.instantiation_state == constants.VNF_INSTANTIATED:
            vnf_info.instantiated_vnf_info = InstantiatedVnfInfo()
            vnf_info.instantiated_vnf_info.vnf_state = 'STARTED'

            vnf_info.instantiated_vnf_info.vnfc_resource_info = []

            for vnf_resource in range(0, 2):

                # Build the VnfcResourceInfo data structure
                vnfc_resource_info = VnfcResourceInfo()
                vnfc_resource_info.vnfc_instance_id = 'vnfc_instance_id'
                vnfc_resource_info.vdu_id = 'vdu_id'

                vnfc_resource_info.compute_resource = ResourceHandle()
                vnfc_resource_info.compute_resource.vim_id = 'vim_id'
                vnfc_resource_info.compute_resource.resource_id = 'resource_id'

                vnf_info.instantiated_vnf_info.vnfc_resource_info.append(vnfc_resource_info)

        return vnf_info
