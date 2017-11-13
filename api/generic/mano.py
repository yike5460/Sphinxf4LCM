import logging
import re
import time
from threading import Thread, Event, Lock

from api.adapter import construct_adapter
from api.generic import ApiGenericError
from api.generic import constants
from utils.logging_module import log_entry_exit
from utils.misc import tee

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
        self.notification_queues = dict()

    def set_generic_config(self,
                           VNF_INSTANTIATE_TIMEOUT=constants.VNF_INSTANTIATE_TIMEOUT,
                           VNF_SCALE_OUT_TIMEOUT=constants.VNF_SCALE_OUT_TIMEOUT,
                           VNF_SCALE_IN_TIMEOUT=constants.VNF_SCALE_IN_TIMEOUT,
                           VNF_STOP_TIMEOUT=constants.VNF_STOP_TIMEOUT,
                           VNF_START_TIMEOUT=constants.VNF_START_TIMEOUT,
                           VNF_TERMINATE_TIMEOUT=constants.VNF_TERMINATE_TIMEOUT,
                           VNF_STABLE_STATE_TIMEOUT=constants.VNF_STABLE_STATE_TIMEOUT,
                           NS_INSTANTIATE_TIMEOUT=constants.NS_INSTANTIATE_TIMEOUT,
                           NS_SCALE_OUT_TIMEOUT=constants.NS_SCALE_OUT_TIMEOUT,
                           NS_SCALE_IN_TIMEOUT=constants.NS_SCALE_IN_TIMEOUT,
                           NS_TERMINATE_TIMEOUT=constants.NS_TERMINATE_TIMEOUT,
                           NS_STABLE_STATE_TIMEOUT=constants.NS_STABLE_STATE_TIMEOUT,
                           POLL_INTERVAL=constants.POLL_INTERVAL):
        self.VNF_INSTANTIATE_TIMEOUT = VNF_INSTANTIATE_TIMEOUT
        self.VNF_SCALE_OUT_TIMEOUT = VNF_SCALE_OUT_TIMEOUT
        self.VNF_SCALE_IN_TIMEOUT = VNF_SCALE_IN_TIMEOUT
        self.VNF_STOP_TIMEOUT = VNF_STOP_TIMEOUT
        self.VNF_START_TIMEOUT = VNF_START_TIMEOUT
        self.VNF_TERMINATE_TIMEOUT = VNF_TERMINATE_TIMEOUT
        self.VNF_STABLE_STATE_TIMEOUT = VNF_STABLE_STATE_TIMEOUT
        self.NS_INSTANTIATE_TIMEOUT = NS_INSTANTIATE_TIMEOUT
        self.NS_SCALE_OUT_TIMEOUT = NS_SCALE_OUT_TIMEOUT
        self.NS_SCALE_IN_TIMEOUT = NS_SCALE_IN_TIMEOUT
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

        return self.mano_adapter.validate_vnf_allocated_vresources(vnf_instance_id, additional_param)

    @log_entry_exit(LOG)
    def validate_ns_allocated_vresources(self, ns_instance_id, additional_param=None):
        """
        This function checks that the virtual resources allocated to the NS match the ones in the NSD.

        :param ns_instance_id:      Identifier of the NS instance.
        :param additional_param:    Additional parameters used for filtering.
        :return:                    True if the allocated resources are as expected, False otherwise.
        """
        ns_info = self.ns_query(filter={'ns_instance_id': ns_instance_id})
        for vnf_instance_id in ns_info.vnf_info_id:
            if not self.mano_adapter.validate_vnf_allocated_vresources(vnf_instance_id, additional_param):
                LOG.debug('Could not validate allocated vresources for VNF with ID %s' % vnf_instance_id)
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

        return self.mano_adapter.get_allocated_vresources(vnf_instance_id, additional_param)

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
        :return:                                            NS instantiation operation status.
        """
        ns_instance_id = self.ns_create_id(nsd_id, ns_name, ns_description)
        LOG.debug('NS instance ID: %s' % ns_instance_id)
        operation_status = self.ns_instantiate_sync(ns_instance_id, flavour_id, sap_data, pnf_info, vnf_instance_data,
                                                    nested_ns_instance_data, location_constraints,
                                                    additional_param_for_ns, additional_param_for_vnf, start_time,
                                                    ns_instantiation_level_id,
                                                    additional_affinity_or_anti_affinity_rule)

        if operation_status != constants.OPERATION_SUCCESS:
            raise ManoGenericError('NS instantiation operation failed')
        return ns_instance_id

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
    def ns_query(self, filter, attribute_selector=None):
        """
        This function enables the OSS/BSS to query from the NFVO information on one or more NS(s). The operation also
        supports querying information about VNF instance(s) that is (are) part of an NS.

        This function was written in accordance with section 7.3.6 of ETSI GS NFV-IFA 013 v2.1.1 (2016-10).

        :param filter:              Filter defining the NSs on which the query applies, based on attributes of the
                                    Network Service.
        :param attribute_selector:  Provides a list of attribute names of NS. If present, only these attributes are
                                    returned for the instances of NS matching the filter. If absent, the complete
                                    instances of NS(s) are returned.
        :return:                    Information on the NS and VNF instances part of the NS matching the input filter.
                                    If attributeSelector is present, only the attributes listed in attributeSelector are
                                    returned for the selected NSs and VNF instances.
        """

        return self.mano_adapter.ns_query(filter, attribute_selector)

    @log_entry_exit(LOG)
    def ns_scale(self, ns_instance_id, scale_type, scale_ns_data=None, scale_vnf_data=None, scale_time=None):
        """
        This function scales an NS instance.

        This function was written in accordance with section 7.3.4 of ETSI GS NFV-IFA 013 v2.1.1 (2016-10).

        :param ns_instance_id:  Identifier of the instance of the NS.
        :param scale_type:      Indicates the type of scaling to be performed. Possible values: 'scale_ns, 'scale_vnf'.
        :param scale_ns_data:   Provides the necessary information to scale the referenced NS instance. It shall be
                                present when scale_type = 'scale_ns'.
        :param scale_vnf_data:  Provides the information to scale a given VNF instance that is part of the referenced
                                NS instance. Shall be present when scale_type = 'scale_vnf'.
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
        :param scale_type:      Indicates the type of scaling to be performed. Possible values: 'scale_ns, 'scale_vnf'.
        :param scale_ns_data:   Provides the necessary information to scale the referenced NS instance. It shall be
                                present when scale_type = 'scale_ns'.
        :param scale_vnf_data:  Provides the information to scale a given VNF instance that is part of the referenced
                                NS instance. Shall be present when scale_type = 'scale_vnf'.
        :param scale_time:      Timestamp indicating the scale time of the NS, i.e. the NS will be scaled at this
                                timestamp.
        :return:                Operation status.
        """

        lifecycle_operation_occurrence_id = self.ns_scale(ns_instance_id, scale_type, scale_ns_data, scale_vnf_data,
                                                          scale_time)

        ns_scale_timeouts = {'ns_scale_out': self.NS_SCALE_OUT_TIMEOUT,
                             'ns_scale_in': self.NS_SCALE_IN_TIMEOUT}
        vnf_scale_timeouts = {'vnf_scale_out': self.VNF_SCALE_OUT_TIMEOUT,
                              'vnf_scale_in': self.VNF_SCALE_IN_TIMEOUT}

        if scale_type == 'scale_ns':
            scaling_direction = scale_ns_data.scale_ns_by_steps_data.scaling_direction
            operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                                  final_states=constants.OPERATION_FINAL_STATES,
                                                                  max_wait_time=ns_scale_timeouts[scaling_direction],
                                                                  poll_interval=self.POLL_INTERVAL)
        else:
            scaling_direction = scale_vnf_data.type == 'scale_out'
            operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                                  final_states=constants.OPERATION_FINAL_STATES,
                                                                  max_wait_time=vnf_scale_timeouts[scaling_direction],
                                                                  poll_interval=self.POLL_INTERVAL)

        return operation_status

    @log_entry_exit(LOG)
    def ns_terminate(self, ns_instance_id, terminate_time=None):
        """
        This function terminates an NS.

        This function was written in accordance with section 7.3.7 of ETSI GS NFV-IFA 013 v2.1.1 (2016-10).

        :param ns_instance_id:  Identifier of the NS instance to terminate.
        :param terminate_time:  Timestamp indicating the end time of the NS, i.e. the NS will be terminated
                                automatically at this timestamp.
        :return:                Identifier of the NS lifecycle operation occurrence.

        """

        return self.mano_adapter.ns_terminate(ns_instance_id, terminate_time)

    @log_entry_exit(LOG)
    def ns_terminate_and_delete(self, ns_instance_id, terminate_time=None):
        """
        This function synchronously terminates an NS and deletes its instance ID.

        :param ns_instance_id:  Identifier of the NS instance to terminate.
        :param terminate_time:  Timestamp indicating the end time of the NS, i.e. the NS will be terminated
                                automatically at this timestamp.
        :return:                'SUCCESS' if both operations were successful, 'FAILED' otherwise.
        """

        operation_status = self.ns_terminate_sync(ns_instance_id, terminate_time)

        if operation_status != constants.OPERATION_SUCCESS:
            LOG.debug('Expected termination operation status %s, got %s'
                      % (constants.OPERATION_SUCCESS, operation_status))
            raise ManoGenericError('NS termination operation failed')

        self.ns_delete_id(ns_instance_id)

    @log_entry_exit(LOG)
    def ns_terminate_sync(self, ns_instance_id, terminate_time=None):
        """
        This function synchronously terminates an NS.

        :param ns_instance_id:  Identifier of the NS instance to terminate.
        :param terminate_time:  Timestamp indicating the end time of the NS, i.e. the NS will be terminated
                                automatically at this timestamp.
        :return:                Operation status.
        """

        lifecycle_operation_occurrence_id = self.ns_terminate(ns_instance_id, terminate_time)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES,
                                                              max_wait_time=constants.NS_TERMINATE_TIMEOUT,
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
        :return:                            VNF instantiation operation status.
        """
        vnf_instance_id = self.vnf_create_id(vnfd_id, vnf_instance_name, vnf_instance_description)
        LOG.debug('VNF instance ID: %s' % vnf_instance_id)
        operation_status = self.vnf_instantiate_sync(vnf_instance_id, flavour_id, instantiation_level_id,
                                                     ext_virtual_link, ext_managed_virtual_link, localization_language,
                                                     additional_param)

        if operation_status != constants.OPERATION_SUCCESS:
            return None
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
    def vnf_query(self, filter, attribute_selector=None):
        """
        This operation provides information about VNF instances. The applicable VNF instances can be chosen based on
        filtering criteria, and the information can be restricted to selected attributes.

        This function was written in accordance with section 7.2.9 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

        :param filter:              Filter to select the VNF instance(s) about which information is queried.
        :param attribute_selector:  Provides a list of attribute names. If present, only these attributes are returned
                                    for the VNF instance(s) matching the filter. If absent, the complete information is
                                    returned for the VNF instance(s) matching the filter.
        :return:                    The information items about the selected VNF instance(s) that are returned. If
                                    attribute_selector is present, only the attributes listed in attribute_selector are
                                    returned for the selected VNF instance(s).
        """

        return self.mano_adapter.vnf_query(filter, attribute_selector)

    @log_entry_exit(LOG)
    def vnf_scale(self, vnf_instance_id, type, aspect_id, number_of_steps=1, additional_param=None):
        """
        This function scales a VNF horizontally (out/in).

        This function was written in accordance with section 7.2.4 of ETSI GS NFV-IFA 007 v2.1.1 (2016-10).

        :param vnf_instance_id:     Identifier of the VNF instance to which this scaling request is related.
        :param type:                Defines the type of the scale operation requested (scale out, scale in).
        :param aspect_id:           Identifies the aspect of the VNF that is requested to be scaled, as declared in the
                                    VNFD.
        :param number_of_steps:     Number of scaling steps to be executed as part of this ScaleVnf operation.
                                    Defaults to 1.
        :param additional_param:    Additional parameters passed by the NFVO as input to the scaling process, specific
                                    to the VNF being scaled.
        :return:                    Identifier of the VNF lifecycle operation occurrence.
        """

        return self.mano_adapter.vnf_scale(vnf_instance_id, type, aspect_id, number_of_steps, additional_param)

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

        scale_timeouts = {'out': self.VNF_SCALE_OUT_TIMEOUT,
                          'in': self.VNF_SCALE_IN_TIMEOUT}

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES,
                                                              max_wait_time=scale_timeouts[scale_type],
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
        result = dict()
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
        :return:                True if the VNF reached one of the final states, False otherwise.
        """
        return self.mano_adapter.wait_for_vnf_stable_state(vnf_instance_id, max_wait_time=self.VNF_STABLE_STATE_TIMEOUT,
                                                           poll_interval=self.POLL_INTERVAL)

    @log_entry_exit(LOG)
    def wait_for_ns_stable_state(self, ns_instance_id):
        """
        This function waits for the NS with the specified ID to be in a stable state. This is useful when an operation
        requires the NS to be in a particular state.

        :param ns_instance_id:  Identifier of the NS instance.
        :return:                True if the NS reached one of the final states, False otherwise.
        """
        return self.mano_adapter.wait_for_ns_stable_state(ns_instance_id, max_wait_time=self.NS_STABLE_STATE_TIMEOUT,
                                                          poll_interval=self.POLL_INTERVAL)

    @log_entry_exit(LOG)
    def verify_vnf_nsd_mapping(self, ns_instance_id, additional_param):
        """
        This function verifies that the VNF instance(s) that are part of the NS with the provided instance ID have been
        deployed according to the NSD.

        :param ns_instance_id:      Identifier of the NS instance.
        :param additional_param:    Additional parameters used for filtering.
        :return:                    True if the VNF instance(s) have been deployed according to the NSD, False
                                    otherwise.
        """
        return self.mano_adapter.verify_vnf_nsd_mapping(ns_instance_id, additional_param)
