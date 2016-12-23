import logging
import time
from api.adapter import construct_adapter
from utils.logging_module import log_entry_exit
from api.generic import constants

LOG = logging.getLogger(__name__)


class Vnfm(object):
    def __init__(self, vendor=None, **kwargs):
        self.vendor = vendor
        self.vnfm_adapter = construct_adapter(vendor, "vnfm", **kwargs)

    def __getattr__(self, attr):
        return getattr(self.vnfm_adapter, attr)

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
        :return:                            Operation 'SUCCESS' if the synchronous instantiation succeeded, 'FAILED'
                                            otherwise.
        """
        lifecycle_operation_occurrence_id = self.vnf_instantiate(vnf_instance_id, flavour_id, instantiation_level_id,
                                                                 ext_virtual_link, ext_managed_virtual_link,
                                                                 localization_language, additional_param)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES)

        if operation_status != constants.OPERATION_SUCCESS:
            return constants.OPERATION_FAILED
        return operation_status

    @log_entry_exit(LOG)
    def poll_for_operation_completion(self, lifecycle_operation_occurrence_id, final_states, max_wait_time=120,
                                      poll_interval=3):
        """
        This function polls the status of an operation until it reaches a final state or time is up.

        :param lifecycle_operation_occurrence_id:   ID of the VNF lifecycle operation occurrence.
        :param final_states:                        List of states of the operation that when reached, the polling
                                                    stops.
        :param max_wait_time:                       Maximum interval of time in seconds to wait for the operation to
                                                    reach a final state.
        :param poll_interval:                       Interval of time in seconds between consecutive polls.
        :return:                                    VNF instantiation operation status.
        """
        operation_pending = True
        elapsed_time = 0

        while operation_pending and elapsed_time < max_wait_time:
            operation_status = self.get_operation_status(lifecycle_operation_occurrence_id)
            LOG.info('Got status %s for %s' % (operation_status, lifecycle_operation_occurrence_id))
            if operation_status in final_states:
                operation_pending = False
            else:
                time.sleep(poll_interval)
                elapsed_time += poll_interval

        return operation_status

    @log_entry_exit(LOG)
    def vnf_create_and_instantiate(self, vnfd_id, flavour_id, vnf_instance_name=None, vnf_instance_description=None,
                                   instantiation_level_id=None, ext_virtual_link=None, ext_managed_virtual_link=None,
                                   localization_language=None, additional_param=None):
        """
        This function creates a VNF instance ID and synchronously instantiates it.

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

        lifecycle_operation_occurrence_id = self.vnf_instantiate(vnf_instance_id, flavour_id, instantiation_level_id,
                                                                 ext_virtual_link, ext_managed_virtual_link,
                                                                 localization_language, additional_param)

        operation_status = self.poll_for_operation_completion(lifecycle_operation_occurrence_id,
                                                              final_states=constants.OPERATION_FINAL_STATES)

        if operation_status != constants.OPERATION_SUCCESS:
            return None
        return vnf_instance_id
