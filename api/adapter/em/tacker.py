import logging
import time

import os_client_config
from tackerclient.tacker.client import Client as TackerClient

from api.generic import constants
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class TackerEmAdapter(object):
    """
    Class of functions that map the ETSI standard operations exposed by the EM to the operations exposed by the
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
    def modify_vnf_configuration(self, vnf_instance_id, vnf_configuration_data=None, ext_virtual_link=None):
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