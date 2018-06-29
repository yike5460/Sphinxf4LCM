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
import re
import time
from collections import OrderedDict
from threading import Thread, Event, Lock

from api.adapter import construct_adapter
from api.generic import ApiGenericError
from api.generic import constants
from utils.logging_module import log_entry_exit
from utils.misc import recursive_map, tee

# Instantiate logger
LOG = logging.getLogger(__name__)


class ManoGenericError(ApiGenericError):
    """
    A problem occurred in the VNF LifeCycle Validation MANO generic API.
    """
    pass


class Mano(object):
    """
    Class of generic functions representing operations exposed by the MANO.
    """

    def __init__(self, vendor, generic_config, adapter_config):
        """
        Construct the Mano object corresponding to the specified vendor.
        """
        self.set_generic_config(**generic_config)
        self.mano_adapter = construct_adapter(vendor, module_type='mano', **adapter_config)
        self.notification_queues = {}

    def set_generic_config(self,
                           VNF_INSTANTIATE_TIMEOUT=constants.VNF_INSTANTIATE_TIMEOUT,
                           VNF_SCALE_TIMEOUT=constants.VNF_SCALE_TIMEOUT,
                           VNF_STOP_TIMEOUT=constants.VNF_STOP_TIMEOUT,
                           VNF_START_TIMEOUT=constants.VNF_START_TIMEOUT,
                           VNF_TERMINATE_TIMEOUT=constants.VNF_TERMINATE_TIMEOUT,
                           VNF_STABLE_STATE_TIMEOUT=constants.VNF_STABLE_STATE_TIMEOUT,
                           NS_INSTANTIATE_TIMEOUT=constants.NS_INSTANTIATE_TIMEOUT,
                           NS_SCALE_TIMEOUT=constants.NS_SCALE_TIMEOUT,
                           NS_UPDATE_TIMEOUT=constants.NS_UPDATE_TIMEOUT,
                           NS_TERMINATE_TIMEOUT=constants.NS_TERMINATE_TIMEOUT,
                           NS_STABLE_STATE_TIMEOUT=constants.NS_STABLE_STATE_TIMEOUT,
                           POLL_INTERVAL=constants.POLL_INTERVAL):
        self.VNF_INSTANTIATE_TIMEOUT = VNF_INSTANTIATE_TIMEOUT
        self.VNF_SCALE_TIMEOUT = VNF_SCALE_TIMEOUT
        self.VNF_STOP_TIMEOUT = VNF_STOP_TIMEOUT
        self.VNF_START_TIMEOUT = VNF_START_TIMEOUT
        self.VNF_TERMINATE_TIMEOUT = VNF_TERMINATE_TIMEOUT
        self.VNF_STABLE_STATE_TIMEOUT = VNF_STABLE_STATE_TIMEOUT
        self.NS_INSTANTIATE_TIMEOUT = NS_INSTANTIATE_TIMEOUT
        self.NS_SCALE_TIMEOUT = NS_SCALE_TIMEOUT
        self.NS_UPDATE_TIMEOUT = NS_UPDATE_TIMEOUT
        self.NS_TERMINATE_TIMEOUT = NS_TERMINATE_TIMEOUT
        self.NS_STABLE_STATE_TIMEOUT = NS_STABLE_STATE_TIMEOUT
        self.POLL_INTERVAL = POLL_INTERVAL

    @log_entry_exit(LOG)
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        """
        This function provides the status of a VNF lifecycle management operation.

        This function was written in accordance with section 7.2.13 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

        :param lifecycle_operation_occurrence_id:   ID of the VNF lifecycle operation occurrence.
        :return:                                    The status of the operation ex. 'Processing', 'Failed'.
        """

        return self.mano_adapter.get_operation_status(lifecycle_operation_occurrence_id)

    @log_entry_exit(LOG)
    def get_vnfd_scaling_properties(self, vnfd_id, scaling_policy_name):
        """
        This function returns the scaling properties for the provided scaling policy name from the VNFD with the
        provided ID.

        :param vnfd_id:             ID of the VNFD to get the scaling properties from.
        :param scaling_policy_name: Name of the scaling policy to get the properties for.
        :return:                    Dictionary with the scaling properties.
        """

        return self.mano_adapter.get_vnfd_scaling_properties(vnfd_id, scaling_policy_name)

    @log_entry_exit(LOG)
    def get_vim_helper(self, vim_id):
        """
        This function returns an instance of Vim class
        :param vim_id:      ID of the VIM as known by the MANO element
        :return:            Vim object
        """

        return self.mano_adapter.get_vim_helper(vim_id)

    @log_entry_exit(LOG)
    def get_nsd_scaling_properties(self, nsd_id, scaling_policy_name):
        """
        This function returns the scaling properties for the provided scaling policy name from the NSD with the
        provided ID.

        :param nsd_id:              ID of the NSD to get the scaling properties from.
        :param scaling_policy_name: Name of the scaling policy to get the properties for.
        :return:                    Dictionary with the scaling properties.
        """

        return self.mano_adapter.get_nsd_scaling_properties(nsd_id, scaling_policy_name)

    @log_entry_exit(LOG)
    def limit_compute_resources_for_ns_scaling(self, nsd_id, scaling_policy_name, desired_scale_out_steps,
                                               generic_vim_object):
        """
        This function reserves compute resources so that the remaining resources are enough only for instantiating the
        NS defined by the provided nsd_id, with the provided number of default instances and scaling the NS
        desired_scale_out_steps times.

        :param nsd_id:                  Identifier of the NSD which defines the NS.
        :param scaling_policy_name:     Name of the scaling policy as stated in the NSD.
        :param desired_scale_out_steps: Desired number of steps the NS should be scaled out.
        :param generic_vim_object:      Generic VIM object.
        :return:                        The reservation ID if the reservation was successful, None otherwise.
        """
        return self.mano_adapter.limit_compute_resources_for_ns_scaling(nsd_id, scaling_policy_name,
                                                                        desired_scale_out_steps,
                                                                        generic_vim_object)

    @log_entry_exit(LOG)
    def limit_compute_resources_for_vnf_instantiation(self, vnfd_id, generic_vim_object, limit_vcpus=True,
                                                      limit_vmem=True, limit_vc_instances=True,
                                                      scaling_policy_name=None):
        """
        This function reserves compute resources so that the remaining resources are not enough for instantiating the
        VNF defined by the provided vnfd_id and with the provided number of default instances.

        :param vnfd_id:                 Identifier of the VNFD which defines the VNF.
        :param generic_vim_object:      Generic VIM object.
        :param limit_vcpus:             Boolean, specifying whether vCPUs should be limited or not.
        :param limit_vmem:              Boolean, specifying whether vMemory should be limited or not.
        :param limit_vc_instances:      Boolean, specifying whether virtual container instances should be limited or
                                        not.
        :param scaling_policy_name:     Optional, name of the scaling policy as stated in the VNFD.
        :return:                        The reservation ID if the reservation was successful, None otherwise.
        """
        return self.mano_adapter.limit_compute_resources_for_vnf_instantiation(vnfd_id, generic_vim_object, limit_vcpus,
                                                                               limit_vmem, limit_vc_instances,
                                                                               scaling_policy_name)

    @log_entry_exit(LOG)
    def limit_storage_resources_for_vnf_instantiation(self, vnfd_id, generic_vim_object, scaling_policy_name=None):
        """
        This function reserves storage resources so that the remaining resources are not enough for instantiating the
        VNF defined by the provided vnfd_id and with the provided number of default instances.

        :param vnfd_id:                 Identifier of the VNFD which defines the VNF.
        :param generic_vim_object:      Generic VIM object.
        :param scaling_policy_name:     Optional, name of the scaling policy as stated in the VNFD.
        :return:                        The reservation ID if the reservation was successful, None otherwise.
        """
        return self.mano_adapter.limit_storage_resources_for_vnf_instantiation(vnfd_id, generic_vim_object,
                                                                               scaling_policy_name)

    @log_entry_exit(LOG)
    def limit_compute_resources_for_vnf_scaling(self, vnfd_id, scaling_policy_name, desired_scale_out_steps,
                                                generic_vim_object):
        """
        This function reserves compute resources so that the remaining resources are enough only for instantiating the
        VNF defined by the provided vnfd_id, and scaling the VNF desired_scale_out_steps times according to the provided
        scaling policy name.

        :param vnfd_id:                 Identifier of the VNFD which defines the VNF.
        :param scaling_policy_name:     Name of the scaling policy as stated in the VNFD.
        :param desired_scale_out_steps: Desired number of steps the VNF should be scaled out.
        :param generic_vim_object:      Generic VIM object.
        :return:                        The reservation ID if the reservation was successful, None otherwise.
        """
        return self.mano_adapter.limit_compute_resources_for_vnf_scaling(vnfd_id, scaling_policy_name,
                                                                         desired_scale_out_steps, generic_vim_object)

    @log_entry_exit(LOG)
    def poll_for_operation_completion(self, lifecycle_operation_occurrence_id, final_states, max_wait_time,
                                      poll_interval):
        """
        This function polls the status of an operation until it reaches a final state or time is up.

        :param lifecycle_operation_occurrence_id:   ID of the VNF lifecycle operation occurrence.
        :param final_states:                        List of states of the operation that when reached, the polling
                                                    stops.
        :param max_wait_time:                       Maximum interval of time in seconds to wait for the operation to
                                                    reach a final state.
        :param poll_interval:                       Interval of time in seconds between consecutive polls.
        :return:                                    Operation status.
        """
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
    def validate_vnf_allocated_vresources(self, vnf_instance_id, additional_param=None):
        """
        This function checks that the virtual resources allocated to the VNF match the ones in the VNFD.

        :param vnf_instance_id:     Identifier of the VNF instance.
        :param additional_param:    Additional parameters used for filtering.
        :return:                    True if the allocated resources are as expected, False otherwise.
        """
        vnf_info = self.vnf_query(query_filter={'vnf_instance_id': vnf_instance_id,
                                                'additional_param': additional_param})
        return self.mano_adapter.validate_vnf_allocated_vresources(vnf_info, additional_param)

    @log_entry_exit(LOG)
    def validate_ns_allocated_vresources(self, ns_instance_id, additional_param=None):
        """
        This function checks that the virtual resources allocated to the NS match the ones in the NSD.

        :param ns_instance_id:      Identifier of the NS instance.
        :param additional_param:    Additional parameters used for filtering.
        :return:                    True if the allocated resources are as expected, False otherwise.
        """
        ns_info = self.ns_query(query_filter={'ns_instance_id': ns_instance_id, 'additional_param': additional_param})
        for vnf_info in ns_info.vnf_info:
            if not self.mano_adapter.validate_vnf_allocated_vresources(vnf_info, additional_param):
                LOG.debug('For VNF instance ID %s expected resources do not match the actual ones'
                          % vnf_info.vnf_instance_id)
                return False

        return True

    @log_entry_exit(LOG)
    def validate_ns_released_vresources(self, ns_info):
        """
        This functions validates that the resources allocated to an NS instance have been released.

        :param ns_info: NsInfo structure holding information about the NS instance.
        :return:        True if the resources have been released, False otherwise.
        """
        for vnf_info in ns_info.vnf_info:
            if not self.validate_vnf_released_vresources(vnf_info):
                return False
        return True

    @log_entry_exit(LOG)
    def validate_vnf_released_vresources(self, vnf_info_initial, vnf_info_final=None):
        """
        This functions validates that the resources allocated to a VNF instance have been released.

        :param vnf_info_initial:    VnfInfo structure holding information about the initial state of the VNF instance.
        :param vnf_info_final:      VnfInfo structure holding information about the final state of the VNF instance
        :return:                    True if the resources allocated to the initial VNF and not allocated to the final
                                    VNF have been released, False otherwise.
        """

        vnfc_resource_id_list_final = []
        if vnf_info_final is not None:
            if vnf_info_final.instantiation_state == constants.VNF_NOT_INSTANTIATED:
                LOG.debug('Cannot perform validation because vnf_info_final reports the VNF instantiation state as %s'
                          % constants.VNF_NOT_INSTANTIATED)
                return False
            for vnfc_resource_info in vnf_info_final.instantiated_vnf_info.vnfc_resource_info:
                vnfc_resource_id_list_final.append(vnfc_resource_info.compute_resource.resource_id)

        if vnf_info_initial.instantiation_state == constants.VNF_NOT_INSTANTIATED:
            LOG.debug('Cannot perform validation because vnf_info_initial reports the VNF instantiation state as %s'
                      % constants.VNF_NOT_INSTANTIATED)
            return False
        for vnfc_resource_info in vnf_info_initial.instantiated_vnf_info.vnfc_resource_info:
            if vnfc_resource_info.compute_resource.resource_id not in vnfc_resource_id_list_final:
                vim_id = vnfc_resource_info.compute_resource.vim_id
                vim = self.get_vim_helper(vim_id)
                resource_id = vnfc_resource_info.compute_resource.resource_id
                try:
                    vim.query_virtualised_compute_resource(filter={'compute_id': resource_id})
                    LOG.debug('Resource ID %s found in VIM, not as expected' % resource_id)
                    return False
                except Exception:
                    LOG.debug('Resource ID %s not found in VIM, as expected' % resource_id)
        return True

    @log_entry_exit(LOG)
    def validate_vnf_vresource_state(self, vnf_instance_id, additional_param=None):
        """
        This function validates if the VNF state indicated by the VNFM matches the state indicated by the VIM

        :param vnf_instance_id:     Vnf Instance ID value.
        :param additional_param:    Additional parameters used for filtering.
        :return:                    True if the the VNF state in the VNFM matches the state indicated by the VIM,
                                    False otherwise
        """

        VNF_TO_VRESOURCE_MAPPING = {constants.VNF_STARTED: constants.VIRTUAL_RESOURCE_ENABLED,
                                    constants.VNF_STOPPED: constants.VIRTUAL_RESOURCE_DISABLED}
        vnf_info = self.vnf_query(query_filter={'vnf_instance_id': vnf_instance_id,
                                                'additional_param': additional_param})

        # Check if the VNF instantiation state is INSTANTIATED
        if vnf_info.instantiation_state == constants.VNF_NOT_INSTANTIATED:
            LOG.debug('Cannot perform validation because VnfInfo reports the VNF instantiation state as %s'
                      % constants.VNF_NOT_INSTANTIATED)
            return False

        # Validate the state of the VNF and its resources
        vnf_state = vnf_info.instantiated_vnf_info.vnf_state
        for vnfc_resource_info in vnf_info.instantiated_vnf_info.vnfc_resource_info:
            vim_id = vnfc_resource_info.compute_resource.vim_id
            vim = self.get_vim_helper(vim_id)
            resource_id = vnfc_resource_info.compute_resource.resource_id
            try:
                virtual_compute = vim.query_virtualised_compute_resource(filter={'compute_id': resource_id})
                if virtual_compute.operational_state != VNF_TO_VRESOURCE_MAPPING[vnf_state]:
                    return False
            except Exception:
                LOG.debug('Resource ID %s corresponding to VNF %s not found in VIM' %
                          (resource_id, vnf_info.vnf_product_name))
                return False
        return True

    @log_entry_exit(LOG)
    def get_allocated_vresources(self, vnf_instance_id, additional_param=None):
        """
        This functions retrieves the virtual resources allocated to the VNF with the provided instance ID.

        :param vnf_instance_id:     Identifier of the VNF instance.
        :param additional_param:    Additional parameters used for filtering.
        :return:                    Dictionary with the resources for each VNFC.
        """

        vnf_info = self.vnf_query(query_filter={'vnf_instance_id': vnf_instance_id,
                                                'additional_param': additional_param})
        vresources = {}

        # Check if the VNF instantiation state is INSTANTIATED
        if vnf_info.instantiation_state == constants.VNF_NOT_INSTANTIATED:
            LOG.debug('Cannot get allocated resources because VnfInfo reports the VNF instantiation state as %s'
                      % constants.VNF_NOT_INSTANTIATED)
            return vresources

        # Retrieve the allocated resources
        for vnfc_resource_info in vnf_info.instantiated_vnf_info.vnfc_resource_info:
            vim_id = vnfc_resource_info.compute_resource.vim_id
            vim = self.get_vim_helper(vim_id)

            resource_id = vnfc_resource_info.compute_resource.resource_id
            virtual_compute = vim.query_virtualised_compute_resource(filter={'compute_id': resource_id})

            resource_string = '%s (%s)' % (resource_id, vnfc_resource_info.vdu_id)
            vresources[resource_string] = OrderedDict()

            num_virtual_cpu = virtual_compute.virtual_cpu.num_virtual_cpu
            virtual_memory = virtual_compute.virtual_memory.virtual_mem_size
            size_of_storage = virtual_compute.virtual_disks[0].size_of_storage
            num_vnics = len(virtual_compute.virtual_network_interface)
            vc_image_id = virtual_compute.vc_image_id
            software_image_information = vim.query_image(vc_image_id)
            vc_image_name = software_image_information.name

            vresources[resource_string]['vCPU'] = num_virtual_cpu
            vresources[resource_string]['vMemory'] = str(virtual_memory) + ' MB'
            vresources[resource_string]['vStorage'] = str(size_of_storage) + ' GB'
            vresources[resource_string]['vNIC'] = str(num_vnics)
            vresources[resource_string]['Image name'] = str(vc_image_name)

        return vresources

    @log_entry_exit(LOG)
    def modify_vnf_configuration(self, vnf_instance_id, vnf_configuration_data=None, ext_virtual_link=None):
        """
        This function enables providing configuration parameters information for a VNF instance.

        This function was written in accordance with section 7.6.2 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

        :param vnf_instance_id:         Identifier of the VNF instance.
        :param vnf_configuration_data:  Configuration data for the VNF instance.
        :param ext_virtual_link:        Information about external VLs to connect the VNF to.
        :return:                        None.
        """

        return self.mano_adapter.modify_vnf_configuration(vnf_instance_id, vnf_configuration_data, ext_virtual_link)

    @log_entry_exit(LOG)
    def ns_create_id(self, nsd_id, ns_name, ns_description):
        """
        This function creates an NS instance ID and an associated instance of a NsInfo information element, identified
        by that identifier, in the NOT_INSTANTIATED state without instantiating the NS or doing any additional lifecycle
        operation(s).

        This function was written in accordance with section 7.3.2 of ETSI GS NFV-IFA 013 v2.1.1 (2016-10).

        :param nsd_id:          Reference to the NSD used to create this NS instance.
        :param ns_name:         Human readable name of the NS instance.
        :param ns_description:  Human readable description of the NS instance.
        :return:                Identifier of the instance of an NS that has been created.
        """

        return self.mano_adapter.ns_create_id(nsd_id, ns_name, ns_description)

    @log_entry_exit(LOG)
    def ns_create_and_instantiate(self, nsd_id, ns_name, ns_description, flavour_id, sap_data=None, pnf_info=None,
                                  vnf_instance_data=None, nested_ns_instance_data=None, location_constraints=None,
                                  additional_param_for_ns=None, additional_param_for_vnf=None, start_time=None,
                                  ns_instantiation_level_id=None, additional_affinity_or_anti_affinity_rule=None):
        """
        This function creates an NS instance ID and synchronously instantiates an NS.

        :param nsd_id:                                      Reference to the NSD used to create this NS instance.
        :param ns_name:                                     Human readable name of the NS instance.
        :param ns_description:                              Human readable description of the NS instance.
        :param flavour_id:                                  Flavour of the NSD used to instantiate this NS.
        :param sap_data:                                    Create data concerning the SAPs of this NS.
        :param pnf_info:                                    Information on the PNF(s) that are part of this NS.
        :param vnf_instance_data:                           Specify an existing VNF instance to be used in the NS.
        :param nested_ns_instance_data:                     Specify an existing NS instance to be used as a nested NS
                                                            within the NS.
        :param location_constraints:                        Defines the location constraints for the VNF to be
                                                            instantiated as part of the NS instantiation.
        :param additional_param_for_ns:                     Allows the OSS/BSS to provide additional parameter(s) at the
                                                            NS level.
        :param additional_param_for_vnf:                    Allows the OSS/BSS to provide additional parameter(s) per
                                                            VNF instance.
        :param start_time:                                  Timestamp indicating the earliest time to instantiate the
                                                            NS.
        :param ns_instantiation_level_id:                   Identifies one of the NS instantiation levels declared in
                                                            the DF applicable to this NS instance.
        :param additional_affinity_or_anti_affinity_rule:   Specifies additional affinity or anti-affinity constraint
                                                            for the VNF instances to be instantiated as part of the NS
                                                            instantiation.
        :return:                                            Identifier of the NS instance.
        """
        ns_instance_id = self.ns_create_id(nsd_id, ns_name, ns_description)
        LOG.debug('NS instance ID: %s' % ns_instance_id)
        operation_status = self.ns_instantiate_sync(ns_instance_id, flavour_id, sap_data, pnf_info, vnf_instance_data,
                                                    nested_ns_instance_data, location_constraints,
                                                    additional_param_for_ns, additional_param_for_vnf, start_time,
                                                    ns_instantiation_level_id,
                                                    additional_affinity_or_anti_affinity_rule)

        return ns_instance_id, operation_status

    @log_entry_exit(LOG)
    def ns_delete_id(self, ns_instance_id):
        """
        This function an NS instance identifier and the associated NsInfo information element.

        This function was written in accordance with section 7.3.8 of ETSI GS NFV-IFA 013 v2.1.1 (2016-10).

        :param ns_instance_id:  NS instance identifier to be deleted.
        :return:                None
        """

        return self.mano_adapter.ns_delete_id(ns_instance_id)

    @log_entry_exit(LOG)
    def ns_instantiate(self, ns_instance_id, flavour_id, sap_data=None, pnf_info=None, vnf_instance_data=None,
                       nested_ns_instance_data=None, location_constraints=None, additional_param_for_ns=None,
                       additional_param_for_vnf=None, start_time=None, ns_instantiation_level_id=None,
                       additional_affinity_or_anti_affinity_rule=None):
        """
        This operation will instantiate an NS.

        This function was written in accordance with section 7.3.3 of ETSI GS NFV-IFA 013 v2.1.1 (2016-10).

        :param ns_instance_id:                              Identifier of the instance of the NS.
        :param flavour_id:                                  Flavour of the NSD used to instantiate this NS.
        :param sap_data:                                    Create data concerning the SAPs of this NS.
        :param pnf_info:                                    Information on the PNF(s) that are part of this NS.
        :param vnf_instance_data:                           Specify an existing VNF instance to be used in the NS.
        :param nested_ns_instance_data:                     Specify an existing NS instance to be used as a nested NS
                                                            within the NS.
        :param location_constraints:                        Defines the location constraints for the VNF to be
                                                            instantiated as part of the NS instantiation.
        :param additional_param_for_ns:                     Allows the OSS/BSS to provide additional parameter(s) at the
                                                            NS level.
        :param additional_param_for_vnf:                    Allows the OSS/BSS to provide additional parameter(s) per
                                                            VNF instance.
        :param start_time:                                  Timestamp indicating the earliest time to instantiate the
                                                            NS.
        :param ns_instantiation_level_id:                   Identifies one of the NS instantiation levels declared in
                                                            the DF applicable to this NS instance.
        :param additional_affinity_or_anti_affinity_rule:   Specifies additional affinity or anti-affinity constraint
                                                            for the VNF instances to be instantiated as part of the NS
                                                            instantiation.
        :return:                                            Identifier of the NS lifecycle operation occurrence.

        """

        return self.mano_adapter.ns_instantiate(ns_instance_id, flavour_id, sap_data, pnf_info, vnf_instance_data,
                                                nested_ns_instance_data, location_constraints, additional_param_for_ns,
                                                additional_param_for_vnf, start_time, ns_instantiation_level_id,
                                                additional_affinity_or_anti_affinity_rule)

    @log_entry_exit(LOG)
    def ns_instantiate_sync(self, ns_instance_id, flavour_id, sap_data=None, pnf_info=None, vnf_instance_data=None,
                            nested_ns_instance_data=None, location_constraints=None, additional_param_for_ns=None,
                            additional_param_for_vnf=None, start_time=None, ns_instantiation_level_id=None,
                            additional_affinity_or_anti_affinity_rule=None):
        """
        This function performs a synchronous NS instantiation, i.e. instantiates an NS and then polls the operation
        status until the operation reaches a final state.

        :param ns_instance_id:                              Identifier of the instance of the NS.
        :param flavour_id:                                  Flavour of the NSD used to instantiate this NS.
        :param sap_data:                                    Create data concerning the SAPs of this NS.
        :param pnf_info:                                    Information on the PNF(s) that are part of this NS.
        :param vnf_instance_data:                           Specify an existing VNF instance to be used in the NS.
        :param nested_ns_instance_data:                     Specify an existing NS instance to be used as a nested NS
                                                            within the NS.
        :param location_constraints:                        Defines the location constraints for the VNF to be
                                                            instantiated as part of the NS instantiation.
        :param additional_param_for_ns:                     Allows the OSS/BSS to provide additional parameter(s) at the
                                                            NS level.
        :param additional_param_for_vnf:                    Allows the OSS/BSS to provide additional parameter(s) per
                                                            VNF instance.
        :param start_time:                                  Timestamp indicating the earliest time to instantiate the
                                                            NS.
        :param ns_instantiation_level_id:                   Identifies one of the NS instantiation levels declared in
                                                            the DF applicable to this NS instance.
        :param additional_affinity_or_anti_affinity_rule:   Specifies additional affinity or anti-affinity constraint
                                                            for the VNF instances to be instantiated as part of the NS
                                                            instantiation.
        :return:                                            Operation status.
        """

        lifecycle_operation_occurrence_id = self.ns_instantiate(ns_instance_id, flavour_id, sap_data, pnf_info,
                                                                vnf_instance_data, nested_ns_instance_data,
                                                                location_constraints, additional_param_for_ns,
                                                                additional_param_for_vnf, start_time,
                                                                ns_instantiation_level_id,
                                                                additional_affinity_or_anti_affinity_rule)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES,
                                                              max_wait_time=self.NS_INSTANTIATE_TIMEOUT,
                                                              poll_interval=self.POLL_INTERVAL)

        return operation_status

    @log_entry_exit(LOG)
    def ns_query(self, query_filter, attribute_selector=None):
        """
        This function enables the OSS/BSS to query from the NFVO information on one or more NS(s). The operation also
        supports querying information about VNF instance(s) that is (are) part of an NS.

        This function was written in accordance with section 7.3.6 of ETSI GS NFV-IFA 013 v2.1.1 (2016-10).

        :param query_filter:        Filter defining the NSs on which the query applies, based on attributes of the
                                    Network Service.
        :param attribute_selector:  Provides a list of attribute names of NS. If present, only these attributes are
                                    returned for the instances of NS matching the filter. If absent, the complete
                                    instances of NS(s) are returned.
        :return:                    Information on the NS and VNF instances part of the NS matching the input filter.
                                    If attributeSelector is present, only the attributes listed in attributeSelector are
                                    returned for the selected NSs and VNF instances.
        """

        return self.mano_adapter.ns_query(query_filter, attribute_selector)

    @log_entry_exit(LOG)
    def ns_scale(self, ns_instance_id, scale_type, scale_ns_data=None, scale_vnf_data=None, scale_time=None):
        """
        This function scales an NS instance.

        This function was written in accordance with section 7.3.4 of ETSI GS NFV-IFA 013 v2.1.1 (2016-10).

        :param ns_instance_id:  Identifier of the instance of the NS.
        :param scale_type:      Indicates the type of scaling to be performed. Possible values: 'SCALE_NS, 'SCALE_VNF'.
        :param scale_ns_data:   Provides the necessary information to scale the referenced NS instance. It shall be
                                present when scale_type = 'SCALE_NS'.
        :param scale_vnf_data:  Provides the information to scale a given VNF instance that is part of the referenced
                                NS instance. Shall be present when scale_type = 'SCALE_VNF'.
        :param scale_time:      Timestamp indicating the scale time of the NS, i.e. the NS will be scaled at this
                                timestamp.
        :return:                Identifier of the NS lifecycle operation occurrence.

        """

        return self.mano_adapter.ns_scale(ns_instance_id, scale_type, scale_ns_data, scale_vnf_data, scale_time)

    @log_entry_exit(LOG)
    def ns_scale_sync(self, ns_instance_id, scale_type, scale_ns_data=None, scale_vnf_data=None, scale_time=None):
        """
        This function synchronously scales an NS instance.

        :param ns_instance_id:  Identifier of the instance of the NS.
        :param scale_type:      Indicates the type of scaling to be performed. Possible values: 'SCALE_NS, 'SCALE_VNF'.
        :param scale_ns_data:   Provides the necessary information to scale the referenced NS instance. It shall be
                                present when scale_type = 'SCALE_NS'.
        :param scale_vnf_data:  Provides the information to scale a given VNF instance that is part of the referenced
                                NS instance. Shall be present when scale_type = 'SCALE_VNF'.
        :param scale_time:      Timestamp indicating the scale time of the NS, i.e. the NS will be scaled at this
                                timestamp.
        :return:                Operation status.
        """

        lifecycle_operation_occurrence_id = self.ns_scale(ns_instance_id, scale_type, scale_ns_data, scale_vnf_data,
                                                          scale_time)
        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES,
                                                              max_wait_time=self.NS_SCALE_TIMEOUT,
                                                              poll_interval=self.POLL_INTERVAL)
        return operation_status

    @log_entry_exit(LOG)
    def ns_terminate(self, ns_instance_id, terminate_time=None, additional_param=None):
        """
        This function terminates an NS.

        This function was written in accordance with section 7.3.7 of ETSI GS NFV-IFA 013 v2.1.1 (2016-10). The
        additional_param inout is not part of the standard specification.

        :param ns_instance_id:      Identifier of the NS instance to terminate.
        :param terminate_time:      Timestamp indicating the end time of the NS, i.e. the NS will be terminated
                                    automatically at this timestamp.
        :param additional_param:    Additional parameters passed by the NFVO as input to the Terminate NS operation,
                                    specific to the NS being terminated.
        :return:                    Identifier of the NS lifecycle operation occurrence.

        """

        return self.mano_adapter.ns_terminate(ns_instance_id, terminate_time, additional_param)

    @log_entry_exit(LOG)
    def ns_terminate_and_delete(self, ns_instance_id, terminate_time=None, additional_param=None):
        """
        This function synchronously terminates an NS and deletes its instance ID.

        :param ns_instance_id:      Identifier of the NS instance to terminate.
        :param terminate_time:      Timestamp indicating the end time of the NS, i.e. the NS will be terminated
                                    automatically at this timestamp.
        :param additional_param:    Additional parameters passed by the NFVO as input to the Terminate NS operation,
                                    specific to the NS being terminated.
        :return:                    'SUCCESS' if both operations were successful, 'FAILED' otherwise.
        """

        operation_status = self.ns_terminate_sync(ns_instance_id, terminate_time, additional_param)

        self.ns_delete_id(ns_instance_id)

        return operation_status

    @log_entry_exit(LOG)
    def ns_terminate_sync(self, ns_instance_id, terminate_time=None, additional_param=None):
        """
        This function synchronously terminates an NS.

        :param ns_instance_id:      Identifier of the NS instance to terminate.
        :param terminate_time:      Timestamp indicating the end time of the NS, i.e. the NS will be terminated
                                    automatically at this timestamp.
        :param additional_param:    Additional parameters passed by the NFVO as input to the Terminate NS operation,
                                    specific to the NS being terminated.
        :return:                    Operation status.
        """

        lifecycle_operation_occurrence_id = self.ns_terminate(ns_instance_id, terminate_time, additional_param)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES,
                                                              max_wait_time=self.NS_TERMINATE_TIMEOUT,
                                                              poll_interval=self.POLL_INTERVAL)

        return operation_status

    @log_entry_exit(LOG)
    def ns_update(self, ns_instance_id, update_type, add_vnf_instance=None, remove_vnf_instance_id=None,
                  instantiate_vnf_data=None, change_vnf_flavour_data=None, operate_vnf_data=None,
                  modify_vnf_info_data=None, change_ext_vnf_connectivity_data=None, add_sap=None, remove_sap_id=None,
                  add_nested_ns_id=None, remove_nested_ns_id=None, assoc_new_nsd_version_data=None,
                  move_vnf_instance_data=None, add_vnffg=None, remove_vnffg_id=None, update_vnffg=None,
                  change_ns_flavour_data=None, update_time=None):
        """
        This function updates an NS instance. This operation is also used to embed VNF LCM operations in support of
        fine grained NS LCM approach. See the informative message flows in annex C. Actions that can be performed with
        an update include:
        - Adding existing VNF instances to the NS instance.
        - Removing VNF instances from the NS instance.
        - Instantiating new VNF instances and adding them to the NS instance.
        - Changing the DF of VNF instances belonging to the NS instance.
        - Changing the operational state of a VNF instance belonging to the NS instance.
        - Modifying information data and/or the configurable properties of a VNF instance belonging to the NS instance.
        - Changing the external connectivity of a VNF instance belonging to the NS instance.
        - Adding SAPs to the NS instance.
        - Removing SAPs from the NS instance.
        - Adding existing NS instances to the NS instance.
        - Removing nested NS instances from the NS instance.
        - Associate a new NSD version to the NS instance.
        - Moving VNF instances from one NS instance to another NS instance.
        - Adding VNFFGs to the NS instance.
        - Removing VNFFGs from the NS instance.
        - Update VNFFGs of the NS instance.
        - Changing the DF of the NS instance.
        Only one type of update shall be allowed per operation.

        This function was written in accordance with section 7.3.5 of ETSI GS NFV-IFA 013 v2.3.1 (2017-08).

        :param ns_instance_id:                      Identifier of the NS instance being updated.
        :param update_type:                         Specifies the type of update. This parameter determines also which
                                                    one of the following parameter is present in the operation. Possible
                                                    values are:
                                                    - AddVnf (adding existing VNF instance(s)),
                                                    - RemoveVnf (removing VNF instance(s)),
                                                    - InstantiateVnf (instantiating new VNF(s)),
                                                    - ChangeVnfDf (Changing VNF DF),
                                                    - OperateVnf (changing VNF state),
                                                    - ModifyVnfInformation (modifying VNF information and/or the
                                                    configurable properties of VNF instance(s)),
                                                    - ChangeExtVnfConnectivity (changing the external connectivity of
                                                    VNF instance(s))
                                                    - AddSap (adding SAP(s)),
                                                    - RemoveSap (removing SAP(s)),
                                                    - AddNestedNs      (adding existing NS instance(s) as nested NS(s)),
                                                    - RemoveNestedNs      (removing existing nested NS instance(s)),
                                                    - AssocNewNsdVersion (associating a new NSD version to the NS
                                                    instance),
                                                    - MoveVnf (moving VNF instance(s) from one origin NS instance to a
                                                    another target NS instance),
                                                    - AddVnffg (adding VNFFG(s)),
                                                    - RemoveVnffg      (removing VNFFG(s)),
                                                    - UpdateVnffg      (updating VNFFG(s)),
                                                    - ChangeNsDf (changing NS DF).
        :param add_vnf_instance:                    Specify an existing VNF instance to be added to the NS instance.
                                                    This parameter shall be present only if updateType=AddVnf.
        :param remove_vnf_instance_id:              Specify an existing VNF instance to be removed from the NS instance.
                                                    The parameter contains the identifier(s) of the VNF instances to be
                                                    removed. This parameter shall be present only if
                                                    updateType=RemoveVnf.
        :param instantiate_vnf_data:                Specify the new VNF to be instantiated. This parameter can be used
                                                    e.g. for the bottom-up NS creation. This parameter shall be present
                                                    only if updateType=InstantiateVnf.
        :param change_vnf_flavour_data:             Specify the new DF of the VNF instance to be changed to. This
                                                    parameter shall be present only if updateType=ChangeVnfDf.
        :param operate_vnf_data:                    Specify the state of the VNF instance to be changed. This parameter
                                                    shall be present only if updateType=OperateVnf.
        :param modify_vnf_info_data:                Specify the VNF Information parameters and/or the configurable
                                                    properties of VNF instance to be modified. This parameter shall be
                                                    present only if updateType=ModifyVnfInformation.
        :param change_ext_vnf_connectivity_data:    Specify the new external connectivity data of the VNF instance to
                                                    be changed. This parameter shall be present only if
                                                    updateType=ChangeExtVnfConnectivity.
        :param add_sap:                             Specify a new SAP to be added to the NS instance. This parameter
                                                    shall be present only if updateType=AddSap.
        :param remove_sap_id:                       Specify an existing SAP to be removed from the NS instance. The
                                                    parameter shall be present only if updateType=RemoveSap.
        :param add_nested_ns_id:                    Specify an existing nested NS instance to be added to (nested
                                                    within) the NS instance. This parameter shall be present only if
                                                    updateType=AddNestedNs.
        :param remove_nested_ns_id:                 Specify an existing nested NS instance to be removed from the NS
                                                    instance. The parameter shall be present only if
                                                    updateType=RemoveVnfNestedNs.
        :param assoc_new_nsd_version_data:          Specify the new NSD to be used for the NS instance. This parameter
                                                    shall be present only if updateType=AssocNewNsdVersion.
        :param move_vnf_instance_data:              Specify existing VNF instance to be moved from one NS instance to
                                                    another NS instance. This parameter shall be present only if
                                                    updateType=MoveVnf.
        :param add_vnffg:                           Specify the new VNFFG to be created to the NS Instance. This
                                                    parameter shall be present only if updateType=AddVnffg.
        :param remove_vnffg_id:                     Identifier of an existing VNFFG to be removed from the NS Instance.
                                                    This parameter shall be present only if updateType=RemoveVnffg.
        :param update_vnffg:                        Specify the new VNFFG Information data to be updated for a VNFFG of
                                                    the NS Instance. This parameter shall be present only if
                                                    updateType=UpdateVnffg.
        :param change_ns_flavour_data:              Specifies the new DF to be applied to the NS instance. It shall be
                                                    present only if updateType=ChangeNsDf.
        :param update_time:                         Timestamp indicating the update time of the NS, i.e. the NS will be
                                                    updated at this timestamp. Cardinality "0" indicates the NS update
                                                    takes place immediately.
        :return:                                    Identifier of the NS lifecycle operation occurrence.
        """
        return self.mano_adapter.ns_update(ns_instance_id, update_type, add_vnf_instance, remove_vnf_instance_id,
                                           instantiate_vnf_data, change_vnf_flavour_data, operate_vnf_data,
                                           modify_vnf_info_data, change_ext_vnf_connectivity_data, add_sap,
                                           remove_sap_id, add_nested_ns_id, remove_nested_ns_id,
                                           assoc_new_nsd_version_data, move_vnf_instance_data, add_vnffg,
                                           remove_vnffg_id, update_vnffg, change_ns_flavour_data, update_time)

    @log_entry_exit(LOG)
    def ns_update_sync(self, ns_instance_id, update_type, add_vnf_instance=None, remove_vnf_instance_id=None,
                       instantiate_vnf_data=None, change_vnf_flavour_data=None, operate_vnf_data=None,
                       modify_vnf_info_data=None, change_ext_vnf_connectivity_data=None, add_sap=None,
                       remove_sap_id=None, add_nested_ns_id=None, remove_nested_ns_id=None,
                       assoc_new_nsd_version_data=None, move_vnf_instance_data=None, add_vnffg=None,
                       remove_vnffg_id=None, update_vnffg=None, change_ns_flavour_data=None, update_time=None):
        """
        This function synchronously updates an NS instance.

        :param ns_instance_id:                      Identifier of the instance of the NS.
        :param update_type:                         Specifies the type of update. See function ns_update for explanation
                                                    of allowed values.
        :param add_vnf_instance:                    Specify an existing VNF instance to be added to the NS instance.
                                                    This parameter shall be present only if updateType=AddVnf.
        :param remove_vnf_instance_id:              Specify an existing VNF instance to be removed from the NS instance.
                                                    The parameter contains the identifier(s) of the VNF instances to be
                                                    removed. This parameter shall be present only if
                                                    updateType=RemoveVnf.
        :param instantiate_vnf_data:                Specify the new VNF to be instantiated. This parameter can be used
                                                    e.g. for the bottom-up NS creation. This parameter shall be present
                                                    only if updateType=InstantiateVnf.
        :param change_vnf_flavour_data:             Specify the new DF of the VNF instance to be changed to. This
                                                    parameter shall be present only if updateType=ChangeVnfDf.
        :param operate_vnf_data:                    Specify the state of the VNF instance to be changed. This parameter
                                                    shall be present only if updateType=OperateVnf.
        :param modify_vnf_info_data:                Specify the VNF Information parameters and/or the configurable
                                                    properties of VNF instance to be modified. This parameter shall
                                                    be present only if updateType=ModifyVnfInformation.
        :param change_ext_vnf_connectivity_data:    Specify the new external connectivity data of the VNF instance to be
                                                    changed. This parameter shall be present only if
                                                    updateType=ChangeExtVnfConnectivity.
        :param add_sap:                             Specify a new SAP to be added to the NS instance. This parameter
                                                    shall be present only if updateType=AddSap.
        :param remove_sap_id:                       Specify an existing SAP to be removed from the NS instance. The
                                                    parameter shall be present only if updateType=RemoveSap.
        :param add_nested_ns_id:                    Specify an existing nested NS instance to be added to (nested
                                                    within) the NS instance. This parameter shall be present only if
                                                    updateType=AddNestedNs.
        :param remove_nested_ns_id:                 Specify an existing nested NS instance to be removed from the NS
                                                    instance. The parameter shall be present only if
                                                    updateType=RemoveVnfNestedNs.
        :param assoc_new_nsd_version_data:          Specify the new NSD to be used for the NS instance. This parameter
                                                    shall be present only if updateType=AssocNewNsdVersion.
        :param move_vnf_instance_data:              Specify existing VNF instance to be moved from one NS instance to
                                                    another NS instance. This parameter shall be present only if
                                                    updateType=MoveVnf.
        :param add_vnffg:                           Specify the new VNFFG to be created to the NS Instance. This
                                                    parameter shall be present only if updateType=AddVnffg.
        :param remove_vnffg_id:                     Identifier of an existing VNFFG to be removed from the NS Instance.
                                                    This parameter shall be present only if updateType=RemoveVnffg.
        :param update_vnffg:                        Specify the new VNFFG Information data to be updated for a VNFFG of
                                                    the NS Instance. This parameter shall be present only if
                                                    updateType=UpdateVnffg.
        :param change_ns_flavour_data:              Specifies the new DF to be applied to the NS instance. It shall be
                                                    present only if updateType=ChangeNsDf.
        :param update_time:                         Timestamp indicating the update time of the NS, i.e. the NS will be
                                                    updated at this timestamp. Cardinality "0" indicates the NS update
                                                    takes place immediately.
        :return:                                    Operation status.
        """

        lifecycle_operation_occurrence_id = self.ns_update(ns_instance_id, update_type, add_vnf_instance,
                                                           remove_vnf_instance_id, instantiate_vnf_data,
                                                           change_vnf_flavour_data, operate_vnf_data,
                                                           modify_vnf_info_data, change_ext_vnf_connectivity_data,
                                                           add_sap, remove_sap_id, add_nested_ns_id,
                                                           remove_nested_ns_id, assoc_new_nsd_version_data,
                                                           move_vnf_instance_data, add_vnffg, remove_vnffg_id,
                                                           update_vnffg, change_ns_flavour_data, update_time)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES,
                                                              max_wait_time=self.NS_UPDATE_TIMEOUT,
                                                              poll_interval=self.POLL_INTERVAL)

        return operation_status

    @log_entry_exit(LOG)
    def vnf_create_id(self, vnfd_id, vnf_instance_name=None, vnf_instance_description=None):
        """
        This function creates a VNF instance ID and an associated instance of a VnfInfo information element, identified
        by that identifier, in the NOT_INSTANTIATED state without instantiating the VNF or doing any additional
        lifecycle operation(s).

        This function was written in accordance with section 7.2.2 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

        :param vnfd_id:                     Identifier that identifies the VNFD which defines the VNF instance to be
                                            created.
        :param vnf_instance_name:           Human-readable name of the VNF instance to be created.
        :param vnf_instance_description:    Human-readable description of the VNF instance to be created.
        :return:                            VNF instance identifier just created.
        """

        return self.mano_adapter.vnf_create_id(vnfd_id, vnf_instance_name, vnf_instance_description)

    @log_entry_exit(LOG)
    def vnf_create_and_instantiate(self, vnfd_id, flavour_id, vnf_instance_name=None, vnf_instance_description=None,
                                   instantiation_level_id=None, ext_virtual_link=None, ext_managed_virtual_link=None,
                                   localization_language=None, additional_param=None):
        """
        This function creates a VNF instance ID and synchronously instantiates a VNF.

        :param vnfd_id:                     Identifier that identifies the VNFD which defines the VNF instance to be
                                            created.
        :param flavour_id:                  Identifier of the VNF DF to be instantiated.
        :param vnf_instance_name:           Human-readable name of the VNF instance to be created.
        :param vnf_instance_description:    Human-readable description of the VNF instance to be created.
        :param instantiation_level_id:      Identifier of the instantiation level of the DF to be instantiated. If not
                                            present, the default instantiation level as declared in the VNFD shall be
                                            instantiated.
        :param ext_virtual_link:            Information about external VLs to connect the VNF to.
        :param ext_managed_virtual_link:    Information about internal VLs that are managed by other entities than the
                                            VNFM.
        :param localization_language:       Localization language of the VNF to be instantiated.
        :param additional_param:            Additional parameters passed as input to the instantiation process, specific
                                            to the VNF being instantiated.
        :return:                            Identifier of the VNF instance.
        """
        vnf_instance_id = self.vnf_create_id(vnfd_id, vnf_instance_name, vnf_instance_description)
        LOG.debug('VNF instance ID: %s' % vnf_instance_id)
        operation_status = self.vnf_instantiate_sync(vnf_instance_id, flavour_id, instantiation_level_id,
                                                     ext_virtual_link, ext_managed_virtual_link, localization_language,
                                                     additional_param)

        if operation_status != constants.OPERATION_SUCCESS:
            raise ManoGenericError('VNF instantiation operation failed')
        return vnf_instance_id

    @log_entry_exit(LOG)
    def vnf_delete_id(self, vnf_instance_id):
        """
        This function deletes a VNF instance ID and the associated instance of a VnfInfo information element.

        This function was written in accordance with section 7.2.8 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

        :param vnf_instance_id: VNF instance identifier to be deleted.
        :return:                None.
        """

        return self.mano_adapter.vnf_delete_id(vnf_instance_id)

    @log_entry_exit(LOG)
    def vnf_instantiate(self, vnf_instance_id, flavour_id, instantiation_level_id=None, ext_virtual_link=None,
                        ext_managed_virtual_link=None, localization_language=None, additional_param=None):
        """
        This function instantiates a particular deployment flavour of a VNF based on the definition in the VNFD.

        This function was written in accordance with section 7.2.3 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

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
        :return:                            Identifier of the VNF lifecycle operation occurrence.
        """

        return self.mano_adapter.vnf_instantiate(vnf_instance_id, flavour_id, instantiation_level_id, ext_virtual_link,
                                                 ext_managed_virtual_link, localization_language, additional_param)

    @log_entry_exit(LOG)
    def vnf_instantiate_sync(self, vnf_instance_id, flavour_id, instantiation_level_id=None, ext_virtual_link=None,
                             ext_managed_virtual_link=None, localization_language=None, additional_param=None):
        """
        This function performs a synchronous VNF instantiation, i.e. instantiates a VNF and then polls the operation
        status until the operation reaches a final state.

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
        :return:                            Operation status.
        """
        lifecycle_operation_occurrence_id = self.vnf_instantiate(vnf_instance_id, flavour_id, instantiation_level_id,
                                                                 ext_virtual_link, ext_managed_virtual_link,
                                                                 localization_language, additional_param)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES,
                                                              max_wait_time=self.VNF_INSTANTIATE_TIMEOUT,
                                                              poll_interval=self.POLL_INTERVAL)

        return operation_status

    @log_entry_exit(LOG)
    def vnf_operate(self, vnf_instance_id, change_state_to, stop_type=None, graceful_stop_timeout=None,
                    additional_param=None):
        """
        This function changes the state of a VNF instance.

        This function was written in accordance with section 7.2.11 of ETSI GS NFV-IFA 007 v2.1.6 (2017-06).

        :param vnf_instance_id:         Identifier of the VNF instance.
        :param change_state_to:         Desired state to change the VNF to. Permitted values are: start, stop.
        :param stop_type:               It signals whether forceful or graceful stop is requested. Possible values:
                                        'forceful' and 'graceful'.
        :param graceful_stop_timeout:   Time interval to wait for the VNF to be taken out of service during graceful
                                        stop, before stopping the VNF.
        :param additional_param:        Additional parameters passed by the NFVO as input to the Operate VNF operation,
                                        specific to the VNF being operated.
        :return:                        Identifier of the VNF lifecycle operation occurrence.
        """

        return self.mano_adapter.vnf_operate(vnf_instance_id, change_state_to, stop_type, graceful_stop_timeout,
                                             additional_param)

    @log_entry_exit(LOG)
    def vnf_operate_sync(self, vnf_instance_id, change_state_to, stop_type=None, graceful_stop_timeout=None,
                         additional_param=None):
        """
        This function performs a synchronous change of a VNF state.

        :param vnf_instance_id:         Identifier of the VNF instance.
        :param change_state_to:         Desired state to change the VNF to. Permitted values are: start, stop.
        :param stop_type:               It signals whether forceful or graceful stop is requested. Possible values:
                                        'forceful' and 'graceful'.
        :param graceful_stop_timeout:   Time interval to wait for the VNF to be taken out of service during
                                        graceful stop, before stopping the VNF.
        :param additional_param:        Additional parameters passed by the NFVO as input to the Operate VNF operation,
                                        specific to the VNF being operated.
        :return:                        Operation status.
        """
        lifecycle_operation_occurrence_id = self.vnf_operate(vnf_instance_id, change_state_to, stop_type,
                                                             graceful_stop_timeout, additional_param)

        operate_timeouts = {'start': self.VNF_START_TIMEOUT,
                            'stop': self.VNF_STOP_TIMEOUT}

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES,
                                                              max_wait_time=operate_timeouts[change_state_to],
                                                              poll_interval=self.POLL_INTERVAL)

        return operation_status

    @log_entry_exit(LOG)
    def vnf_query(self, query_filter, attribute_selector=None):
        """
        This operation provides information about VNF instances. The applicable VNF instances can be chosen based on
        filtering criteria, and the information can be restricted to selected attributes.

        This function was written in accordance with section 7.2.9 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

        :param query_filter:        Filter to select the VNF instance(s) about which information is queried.
        :param attribute_selector:  Provides a list of attribute names. If present, only these attributes are returned
                                    for the VNF instance(s) matching the filter. If absent, the complete information is
                                    returned for the VNF instance(s) matching the filter.
        :return:                    The information items about the selected VNF instance(s) that are returned. If
                                    attribute_selector is present, only the attributes listed in attribute_selector are
                                    returned for the selected VNF instance(s).
        """

        return self.mano_adapter.vnf_query(query_filter, attribute_selector)

    @log_entry_exit(LOG)
    def vnf_scale(self, vnf_instance_id, scale_type, aspect_id, number_of_steps=1, additional_param=None):
        """
        This function scales a VNF horizontally (out/in).

        This function was written in accordance with section 7.2.4 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

        :param vnf_instance_id:     Identifier of the VNF instance to which this scaling request is related.
        :param scale_type:          Defines the type of the scale operation requested (scale out, scale in).
        :param aspect_id:           Identifies the aspect of the VNF that is requested to be scaled, as declared in the
                                    VNFD.
        :param number_of_steps:     Number of scaling steps to be executed as part of this ScaleVnf operation.
                                    Defaults to 1.
        :param additional_param:    Additional parameters passed by the NFVO as input to the scaling process, specific
                                    to the VNF being scaled.
        :return:                    Identifier of the VNF lifecycle operation occurrence.
        """

        return self.mano_adapter.vnf_scale(vnf_instance_id, scale_type, aspect_id, number_of_steps, additional_param)

    @log_entry_exit(LOG)
    def vnf_scale_to_level(self, vnf_instance_id, instantiation_level_id=None, scale_info=None, additional_param=None):
        """
        This function scales an instantiated VNF of a particular DF to a target size.

        This function was written in accordance with section 7.2.5 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

        :param vnf_instance_id:         Identifier of the VNF instance to which this scaling request is related.
        :param instantiation_level_id:  Identifier of the target instantiation level of the current DF to which the
                                        VNF is requested to be scaled. Either instantiationLevelId or scaleInfo
                                        but not both shall be present.
        :param scale_info:              For each scaling aspect of the current DF, defines the target scale level to
                                        which the VNF is to be scaled. Either instantiationLevelId or scaleInfo
                                        but not both shall be present.
        :param additional_param:        Additional parameters passed as input to the scaling process, specific to the
                                        VNF being scaled.
        :return:                        Identifier of the VNF lifecycle operation occurrence.
        """

        return self.mano_adapter.vnf_scale_to_level(vnf_instance_id, instantiation_level_id, scale_info,
                                                    additional_param)

    @log_entry_exit(LOG)
    def vnf_scale_sync(self, vnf_instance_id, scale_type, aspect_id, number_of_steps=1, additional_param=None):
        """
        This function synchronously scales a VNF horizontally (out/in).

        :param vnf_instance_id:     Identifier of the VNF instance to which this scaling request is related.
        :param scale_type:          Defines the type of the scale operation requested. Possible values: 'in', or 'out'
        :param aspect_id:           Identifies the aspect of the VNF that is requested to be scaled, as declared in the
                                    VNFD.
        :param number_of_steps:     Number of scaling steps to be executed as part of this ScaleVnf operation.
                                    Defaults to 1.
        :param additional_param:    Additional parameters passed by the NFVO as input to the scaling process, specific
                                    to the VNF being scaled.
        :return:                    Operation status.
        """
        lifecycle_operation_occurrence_id = self.vnf_scale(vnf_instance_id, scale_type, aspect_id, number_of_steps,
                                                           additional_param)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES,
                                                              max_wait_time=self.VNF_SCALE_TIMEOUT,
                                                              poll_interval=self.POLL_INTERVAL)

        return operation_status

    @log_entry_exit(LOG)
    def vnf_scale_to_level_sync(self, vnf_instance_id, instantiation_level_id=None, scale_info=None,
                                additional_param=None):
        """
        This function synchronously scales an instantiated VNF of a particular DF to a target size.

        :param vnf_instance_id:         Identifier of the VNF instance to which this scaling request is related.
        :param instantiation_level_id:  Identifier of the target instantiation level of the current DF to which the
                                        VNF is requested to be scaled. Either instantiationLevelId or scaleInfo
                                        but not both shall be present.
        :param scale_info:              For each scaling aspect of the current DF, defines the target scale level to
                                        which the VNF is to be scaled. Either instantiationLevelId or scaleInfo
                                        but not both shall be present.
        :param additional_param:        Additional parameters passed as input to the scaling process, specific to the
                                        VNF being scaled.
        :return:                        Operation status.
        """
        lifecycle_operation_occurrence_id = self.vnf_scale_to_level(vnf_instance_id, instantiation_level_id, scale_info,
                                                                    additional_param)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES,
                                                              max_wait_time=self.VNF_SCALE_TIMEOUT,
                                                              poll_interval=self.POLL_INTERVAL)

        return operation_status

    @log_entry_exit(LOG)
    def vnf_terminate(self, vnf_instance_id, termination_type, graceful_termination_timeout=None,
                      additional_param=None):
        """
        This function terminates a VNF.

        This function was written in accordance with section 7.2.7 of ETSI GS NFV-IFA 007 v2.1.6 (2017-06).

        :param vnf_instance_id:                 Identifier of the VNF instance to be terminated.
        :param termination_type:                Signals whether forceful or graceful termination is requested.
        :param graceful_termination_timeout:    The time interval to wait for the VNF to be taken out of service during
                                                graceful termination, before shutting down the VNF and releasing the
                                                resources.
        :param additional_param:                Additional parameters passed by the NFVO as input to the Terminate VNF
                                                operation, specific to the VNF being terminated.
        :return:                                Identifier of the VNF lifecycle operation occurrence.
        """

        return self.mano_adapter.vnf_terminate(vnf_instance_id, termination_type, graceful_termination_timeout,
                                               additional_param)

    @log_entry_exit(LOG)
    def vnf_terminate_and_delete(self, vnf_instance_id, termination_type, graceful_termination_timeout=None,
                                 additional_param=None):
        """
        This function synchronously terminates a VNF and deletes its instance ID.

        :param vnf_instance_id:                 Identifier of the VNF instance to be terminated.
        :param termination_type:                Signals whether forceful or graceful termination is requested.
        :param graceful_termination_timeout:    The time interval to wait for the VNF to be taken out of service during
                                                graceful termination, before shutting down the VNF and releasing the
                                                resources.
        :param additional_param:                Additional parameters passed by the NFVO as input to the Terminate VNF
                                                operation, specific to the VNF being terminated.
        :return:                                'SUCCESS' if both operations were successful, 'FAILED' otherwise.
        """
        operation_status = self.vnf_terminate_sync(vnf_instance_id, termination_type, graceful_termination_timeout,
                                                   additional_param)

        if operation_status != constants.OPERATION_SUCCESS:
            LOG.debug('Expected termination operation status %s, got %s'
                      % (constants.OPERATION_SUCCESS, operation_status))
            raise ManoGenericError('VNF termination operation failed')

        self.vnf_delete_id(vnf_instance_id)

    @log_entry_exit(LOG)
    def vnf_terminate_sync(self, vnf_instance_id, termination_type, graceful_termination_timeout=None,
                           additional_param=None):
        """
        This function synchronously terminates a VNF.

        :param vnf_instance_id:                 Identifier of the VNF instance to be terminated.
        :param termination_type:                Signals whether forceful or graceful termination is requested.
        :param graceful_termination_timeout:    The time interval to wait for the VNF to be taken out of service during
                                                graceful termination, before shutting down the VNF and releasing the
                                                resources.
        :param additional_param:                Additional parameters passed by the NFVO as input to the Terminate VNF
                                                operation, specific to the VNF being terminated.
        :return:                                Operation status.
        """
        lifecycle_operation_occurrence_id = self.vnf_terminate(vnf_instance_id, termination_type,
                                                               graceful_termination_timeout, additional_param)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES,
                                                              max_wait_time=self.VNF_TERMINATE_TIMEOUT,
                                                              poll_interval=self.POLL_INTERVAL)

        return operation_status

    @log_entry_exit(LOG)
    def ns_lifecycle_change_notification_subscribe(self, notification_filter=None):
        """
        This function allows the OSS/BSS to subscribe to NS lifecycle change notifications, and the NFVO to provide such
        notifications to the subscriber.

        This function was written in accordance with section 7.4.2 of ETSI GS NFV-IFA 013 v2.1.1 (2016-10).

        :param notification_filter: Input filter for selecting the notifications.
        :return:                    Identifier of the subscription realized.
        """
        subscription_id, notification_queue = self.mano_adapter.ns_lifecycle_change_notification_subscribe(
                                                                                                    notification_filter)
        self.notification_queues[subscription_id] = notification_queue
        return subscription_id

    @log_entry_exit(LOG)
    def vnf_lifecycle_change_notification_subscribe(self, notification_filter=None):
        subscription_id, notification_queue = self.mano_adapter.vnf_lifecycle_change_notification_subscribe(
                                                                                                    notification_filter)
        self.notification_queues[subscription_id] = notification_queue
        return subscription_id

    @log_entry_exit(LOG)
    def get_notification_queue(self, subscription_id):
        self.notification_queues[subscription_id], notification_queue_copy = tee(
                                                                              self.notification_queues[subscription_id])
        return notification_queue_copy

    @log_entry_exit(LOG)
    def search_in_notification_queue(self, notification_queue, notification_type, notification_pattern, timeout):
        timeout_occurred = Event()
        result = {}
        lock = Lock()

        def notification_loop():
            for notification in notification_queue:
                if isinstance(notification, notification_type):
                    all_matched = True
                    for attr, regex in notification_pattern.items():
                        attr_value = getattr(notification, attr, None)
                        if re.match(regex, str(attr_value)) is None:
                            all_matched = False
                            break

                    if all_matched:
                        with lock:
                            result['found'] = notification
                        break
                if timeout_occurred.is_set():
                    break

        notification_thread = Thread(target=notification_loop)
        notification_thread.start()
        notification_thread.join(timeout)
        timeout_occurred.set()

        with lock:
            return result.get('found')

    @log_entry_exit(LOG)
    def wait_for_notification(self, subscription_id, notification_type, notification_pattern, timeout):
        notification_queue = self.get_notification_queue(subscription_id)
        return self.search_in_notification_queue(notification_queue, notification_type, notification_pattern, timeout)

    @log_entry_exit(LOG)
    def wait_for_vnf_stable_state(self, vnf_instance_id):
        """
        This function waits for the VNF with the specified ID to be in a stable state. This is useful when an operation
        requires the VNF to be in a particular state.

        :param vnf_instance_id: Identifier of the VNF instance.
        :return:                None.
        """
        self.mano_adapter.wait_for_vnf_stable_state(vnf_instance_id, max_wait_time=self.VNF_STABLE_STATE_TIMEOUT,
                                                    poll_interval=self.POLL_INTERVAL)

    @log_entry_exit(LOG)
    def wait_for_ns_stable_state(self, ns_instance_id):
        """
        This function waits for the NS with the specified ID to be in a stable state. This is useful when an operation
        requires the NS to be in a particular state.

        :param ns_instance_id:  Identifier of the NS instance.
        :return:                None.
        """
        self.mano_adapter.wait_for_ns_stable_state(ns_instance_id, max_wait_time=self.NS_STABLE_STATE_TIMEOUT,
                                                   poll_interval=self.POLL_INTERVAL)

    @log_entry_exit(LOG)
    def verify_vnf_nsd_mapping(self, ns_instance_id, additional_param=None):
        """
        This function verifies that the VNF instance(s) that are part of the NS with the provided instance ID have been
        deployed according to the NSD.

        :param ns_instance_id:      Identifier of the NS instance.
        :param additional_param:    Additional parameters used for filtering.
        :return:                    True if the VNF instance(s) have been deployed according to the NSD, False
                                    otherwise.
        """
        return self.mano_adapter.verify_vnf_nsd_mapping(ns_instance_id, additional_param)

    @log_entry_exit(LOG)
    def get_vnf_ingress_cp_addr_list(self, vnf_info, ingress_cp_list):
        """
        This function retrieves from the provided VnfInfo information element the destination address(es) for each
        connection point in the ingress_cp_list.

        :param vnf_info:            VnfInfo information element for the VNF for which the ingress CP address list needs
                                    to be retrieved.
        :param ingress_cp_list:     List of connection points for which to get the corresponding address(es).
                                    Expected format: ['CP1:ip', 'CP2:mac', ...]
        :return:                    String with space-separated addresses.
        """
        # Check if the VNF instantiation state is INSTANTIATED
        if vnf_info.instantiation_state == constants.VNF_NOT_INSTANTIATED:
            LOG.debug('Cannot get destination address list because VnfInfo reports the VNF instantiation state as %s'
                      % constants.VNF_NOT_INSTANTIATED)
            return ''

        # Retrieve the destination address list
        dest_addr_list = []
        for ext_cp_info in vnf_info.instantiated_vnf_info.ext_cp_info:
            for addr_type, addr_value in ext_cp_info.address.items():
                cp_details = '%s:%s' % (ext_cp_info.cpd_id, addr_type)
                if cp_details in ingress_cp_list:
                    dest_addr_list.append(' '.join(addr_value))

        return ' '.join(dest_addr_list)

    @log_entry_exit(LOG)
    def get_ns_ingress_cp_addr_list(self, ns_info, ingress_cp_list):
        """
        This function goes through each VNF inside the NS with the provided instance ID and retrieves the destination
        address(es) for each connection point in the ingress_cp_list.

        :param ns_info:             NsInfo information element for the NS for which the ingress CP address list needs to
                                    be retrieved.
        :param ingress_cp_list:     List of connection points for which to get the corresponding address(es).
                                    Expected format: ['VNF1:CP1:ip', 'VNF1:CP2:mac', 'VNF2:CP2:ip' ...]
        :return:                    String containing space-separated addresses.
        """
        # Build a dict that has as keys the names of the VNFs for which ingress CP addresses need to be retrieved and as
        # values lists with CPs whose addresses need to be retrieved
        # Example:
        # ingress_cp_list = ['VNF1:CP1:ip', 'VNF2:CP2:mac', 'VNF1:CP3:ip']
        # ns_ingress_cps = {'VNF1': ['CP1:ip', 'CP3:ip'],
        #                   'VNF2': ['CP2:mac']}
        ns_ingress_cps = {}
        for ingress_cp in ingress_cp_list:
            vnf_name, cp_details = ingress_cp.split(':', 1)
            if vnf_name not in ns_ingress_cps.keys():
                ns_ingress_cps[vnf_name] = []
            ns_ingress_cps[vnf_name].append(cp_details)

        # Build the list with the destination addresses
        dest_addr_list = []
        for vnf_info in ns_info.vnf_info:
            if vnf_info.vnf_product_name in ns_ingress_cps.keys():
                dest_addr_list.append(self.get_vnf_ingress_cp_addr_list(vnf_info,
                                                                        ns_ingress_cps[vnf_info.vnf_product_name]))
        return ' '.join(dest_addr_list)

    @log_entry_exit(LOG)
    def verify_vnf_sw_images(self, vnf_instance_id, additional_param=None):
        """
        This function verifies that each VNFC part of the VNF with the given instance ID uses the image indicated in the
        VNFD at the corresponding VDU.

        :param vnf_instance_id:     Identifier of the VNF instance.
        :param additional_param:    Additional parameters used for filtering.
        :return:                    True if all VNFCs use the correct images, False otherwise.
        """
        vnf_info = self.vnf_query(query_filter={'vnf_instance_id': vnf_instance_id,
                                                'additional_param': additional_param})
        return self.mano_adapter.verify_vnf_sw_images(vnf_info, additional_param)

    @log_entry_exit(LOG)
    def verify_ns_sw_images(self, ns_instance_id, additional_param=None):
        """
        This function verifies that each VNFC in each VNF of the NS with the given instance ID uses the image indicated
        in the corresponding VNFD at the corresponding VDU.

        :param ns_instance_id:      Identifier of the NS instance.
        :param additional_param:    Additional parameters used for filtering.
        :return:                    True if all VNFCs use the correct images, False otherwise.
        """
        ns_info = self.ns_query(query_filter={'ns_instance_id': ns_instance_id, 'additional_param': additional_param})
        for vnf_info in ns_info.vnf_info:
            if not self.mano_adapter.verify_vnf_sw_images(vnf_info, additional_param):
                LOG.error('Not all VNFCs in VNF with instance ID %s use the correct images' % vnf_info.vnf_instance_id)
                return False
        return True

    @log_entry_exit(LOG)
    def get_vnfd_name_from_nsd_vnf_name(self, nsd_id, vnf_name):
        """
        This function retrieves from the NSD with the provided instance ID the VNFD name that corresponds to the
        provided VNF name.

        :param nsd_id:      Identifier of the NSD from which to retrieve the VNFD name.
        :param vnf_name:    Name of the VNF whose VNFD name should be retrieved.
        :return:            String representing the name of the VNFD name.
        """
        return self.mano_adapter.get_vnfd_name_from_nsd_vnf_name(nsd_id, vnf_name)

    @log_entry_exit(LOG)
    def get_vnf_instance_id_from_ns_vnf_name(self, ns_info, vnf_name):
        """
        This function retrieves from the provided NsInfo information element the VNF instance ID that corresponds to the
        VNF with the provided name.

        :param ns_info:     NsInfo information element for the NS that contains the VNF with the provided name.
        :param vnf_name:    Name of the VNF whose instance ID should be retrieved.
        :return:            String representing the VNF instance ID.
        """
        for vnf_info in ns_info.vnf_info:
            if vnf_info.vnf_product_name == vnf_name:
                return vnf_info.vnf_instance_id

    @log_entry_exit(LOG)
    def get_vnf_mgmt_addr_list(self, vnf_instance_id, additional_param=None):
        """
        This function retrieves the management addresses of the VNFCs that belong to the VNF with the given instance ID.

        :param vnf_instance_id:     Identifier of the VNF instance.
        :param additional_param:    Additional parameters used for filtering.
        :return:                    List of management addresses.
        """
        return self.mano_adapter.get_vnf_mgmt_addr_list(vnf_instance_id, additional_param)

    @log_entry_exit(LOG)
    def verify_ns_vnf_instance_count(self, ns_instance_id, aspect_id, number_of_steps=1, additional_param=None):
        """
        This function verifies that the NS with the provided instance ID contains the correct number of VNF instances.
        It can also be used to validate the result of the NS scale in/out operation.

        :param ns_instance_id:      Identifier of the NS instance.
        :param aspect_id:           Provides the aspect of the NS that is requested to be scaled, as declared in the
                                    NSD.
        :param number_of_steps:     Specifies the number of scaling steps to be performed. Defaults to 1.
        :param additional_param:    Additional scaling parameters.
        :return:                    True if the number of VNF instances is correct, False otherwise.
        """
        return self.mano_adapter.verify_ns_vnf_instance_count(ns_instance_id, aspect_id, number_of_steps,
                                                              additional_param)

    @log_entry_exit(LOG)
    def validate_vnf_instantiation_level(self, vnf_info, instantiation_level_id, additional_param=None):
        """
        This function verifies that the number of VNFC instances in the provided VnfInfo information element matches the
        number of instances indicated by the provided instantiation level ID of the current deployment flavor.

        If the number of instances for a particular VDU is not present in the provided instantiation level ID, the
        number of instances for that VDU will be compared to the number of instances indicated by the default
        instantiation level ID of the current deployment flavor.

        :param vnf_info:                VnfInfo information element.
        :param instantiation_level_id:  ID of the instantiation level.
        :param additional_param:        Additional parameters used for filtering.
        :return:                        True if the number of VNFC instances is correct, False otherwise.
        """
        return self.mano_adapter.validate_vnf_instantiation_level(vnf_info, instantiation_level_id, additional_param)

    @log_entry_exit(LOG)
    def validate_ns_instantiation_level(self, ns_info, instantiation_level_list, additional_param):
        """
        This function verifies that the number of VNFC instances for each VNF in the provided NsInfo information element
        matches the number of instances indicated by the instantiation level ID corresponding to that VNF.

        If no instantiation level ID corresponds to a particular VNF, the number of VNFC instances for that VNF will be
        compared to the number of instances indicated by the default instantiation level ID corresponding to that VNF.

        :param ns_info:                     NsInfo information element.
        :param instantiation_level_list:    List of dictionaries containing the VNF name and the corresponding target
                                            instantiation level ID.
                                            Example: [{'target_vnf_name': 'empirix',
                                                       'target_instantiation_level_id': 'scaled'}]
        :param additional_param:            Additional parameters used for filtering.
        :return:                            True if the number of VNFC instances for each VNF is correct,
                                            False otherwise.
        """
        vnf_name_level_id_mapping = {}
        for scale_to_level in instantiation_level_list:
            vnf_name = scale_to_level['target_vnf_name']
            target_instantiation_level_id = scale_to_level['target_instantiation_level_id']
            vnf_name_level_id_mapping[vnf_name] = target_instantiation_level_id
        for vnf_info in ns_info.vnf_info:
            instantiation_level_id = vnf_name_level_id_mapping.get(vnf_info.vnf_product_name)
            if not self.validate_vnf_instantiation_level(vnf_info, instantiation_level_id, additional_param):
                LOG.debug('Incorrect number of VNFC instances for VNF %s' % vnf_info.vnf_product_name)
                return False
        return True

    @log_entry_exit(LOG)
    def vnf_change_flavour(self, vnf_instance_id, new_flavour_id, instantiation_level_id=None, ext_virtual_link=None,
                           ext_managed_virtual_link=None, vim_connection_info=None, additional_param=None):
        """
        This function changes the deployment flavour of a VNF instance.

        This function was written in accordance with section 7.2.6 of ETSI GS NFV-IFA 007 v2.4.1 (2018-02).

        :param vnf_instance_id:             Identifier of the VNF instance to be modified.
        :param new_flavour_id:              Identifier of the new VNF DF to apply to this VNF instance.
        :param instantiation_level_id:      Identifier of the instantiation level of the DF to be used. If not present,
                                            the default instantiation level as declared in the VNFD shall be used.
        :param ext_virtual_link:            Information about external VLs to connect the VNF to.
        :param ext_managed_virtual_link:    Information about internal VLs that are managed by other entities than the
                                            VNFM.
        :param vim_connection_info:         Information about VIM connection(s) for managing resources for the VNF
                                            instance, or external/externally-managed virtual links. This attribute shall
                                            be supported and present if VNF-related resource management in direct mode
                                            is applicable. In that case, this attribute shall be present if there is the
                                            need to communicate VIM connection information for external or
                                            externally-managed virtual links.
        :param additional_param:            Additional parameters passed by the NFVO as input to the flavour change
                                            process, specific to the VNF being modified as declared in the VNFD.
        :return:                            Identifier of the VNF lifecycle operation occurrence.
        """

        return self.mano_adapter.vnf_change_flavour(vnf_instance_id, new_flavour_id, instantiation_level_id,
                                                    ext_virtual_link, ext_managed_virtual_link, vim_connection_info,
                                                    additional_param)

    @log_entry_exit(LOG)
    def validate_vnf_deployment_flavour(self, vnf_instance_id, expected_flavour_id,
                                        expected_instantiation_level_id=None, additional_param=None):
        """
        This function validates that the VNF with the given instance ID uses the correct deployment flavor and
        instantiation level ID.

        :param vnf_instance_id:                 Identifier of the VNF instance whose deployment flavor and instantiation
                                                level ID should be validated.
        :param expected_flavour_id:             Expected deployment flavour of the VNF instance.
        :param expected_instantiation_level_id: Expected instantiation level ID of the VNF instance.
        :param additional_param:                Additional parameters used for filtering.
        :return:                                True if the VNF instance uses the correct deployment flavor and
                                                instantiation level ID, False otherwise.
        """

        return self.mano_adapter.validate_vnf_deployment_flavour(vnf_instance_id, expected_flavour_id,
                                                                 expected_instantiation_level_id, additional_param)

    @log_entry_exit(LOG)
    def nsd_info_create(self, user_defined_data=None):
        """
        This function will create an NSD information object in the NFVO for the NSD to be uploaded.

        This function was written in accordance with section 7.2.16 of ETSI GS NFV-IFA 013 v2.4.1 (2018-02).

        :param user_defined_data:   User defined data for the NSD to be uploaded.
        :return:                    Identifier of the created NSD information object.
        """

        return self.mano_adapter.nsd_info_create(user_defined_data)

    @log_entry_exit(LOG)
    def nsd_info_query(self, query_filter, attribute_selector=None):
        """
        This function will enable the OSS/BSS to query the NFVO concerning details of one or more NSD information
        objects.

        This function was written in accordance with section 7.2.7 of ETSI GS NFV-IFA 013 v2.4.1 (2018-02).

        :param query_filter:        Filter defining the NSD information objects on which the query applies, based on
                                    attributes of the NSD information objects. It can also be used to specify one or
                                    more NSD information objects to be queried by providing their identifiers.
        :param attribute_selector:  Provides a list of attribute names of the NSD information objects. If present, only
                                    these attributes are returned for the NSD information objects matching the filter.
                                    If absent, the complete NSD information objects are returned.
        :return:                    Details of the NSD information objects matching the input filter.
        """

        return self.mano_adapter.nsd_info_query(query_filter, attribute_selector)

    @log_entry_exit(LOG)
    def nsd_upload(self, nsd_info_id, nsd):
        """
        This function will upload an NSD to the NFVO.

        This function was written in accordance with section 7.2.2 of ETSI GS NFV-IFA 013 v2.4.1 (2018-02).

        :param nsd_info_id: Identifier of the NSD information object associated with the NSD to be uploaded.
        :param nsd:         NSD to be uploaded.
        :return:            None.
        """

        return self.mano_adapter.nsd_upload(nsd_info_id, nsd)

    @log_entry_exit(LOG)
    def nsd_fetch(self, nsd_info_id):
        """
        This function will fetch an NSD from the NFVO.

        This function was written in accordance with section 7.2.17 of ETSI GS NFV-IFA 013 v2.4.1 (2018-02).

        :param nsd_info_id: Identifier of the NSD information object associated with the NSD to be fetched.
        :return:            The fetched NSD.
        """

        return self.mano_adapter.nsd_fetch(nsd_info_id)

    @log_entry_exit(LOG)
    def nsd_delete(self, nsd_info_id):
        """
        This function will delete one or more NSD(s). The associated NSD information objects will be deleted as well.

        This function was written in accordance with section 7.2.6 of ETSI GS NFV-IFA 013 v2.4.1 (2018-02).

        :param nsd_info_id: Identifier of the NSD information objects to be deleted.
        :return:            Identifier of the deleted NSD information objects.
        """

        return self.mano_adapter.nsd_delete(nsd_info_id)

    @recursive_map
    def resolve_ns_cp_addr(self, ns_info, data):
        """
        This function will search for pattern like ${vnf_name:cp_name:addr_type} (e.g ${VNF1:east:ip}) recursively
        inside 'data' and resolve them using information found in 'ns_info'

        :param ns_info:     NsInfo information element.
        :param data:        Data structure containing patterns that may need resolving.
        :return:            Data structure with resolved patterns.
        """

        pattern = '\$\{(.*?)\}'

        data = re.sub(pattern, lambda x: self.get_ns_ingress_cp_addr_list(ns_info, [x.group(1)]), data)
        data = re.sub(pattern, '\\1', data)

        return data

    @log_entry_exit(LOG)
    def ns_get_alarm_list(self, query_filter):
        """
        This function enables the OSS/BSSs to query the active alarms from the NFVO.

        This function was written in accordance with section 7.6.4 of ETSI GS NFV-IFA 013 v2.4.1 (2018-02).

        :param query_filter:    Input filter for selecting alarms. This can contain the list of the NS identifiers,
                                severity and cause.
        :return:                Information about an alarm including AlarmId, affected NS Id, and FaultDetails. The
                                cardinality can be "0" to indicate that no Alarm could be retrieved based on the input
                                filter information.
        """

        return self.mano_adapter.ns_get_alarm_list(query_filter)
