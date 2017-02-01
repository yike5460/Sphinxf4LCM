import logging

import os_client_config

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
        compute_id = filter['compute_id']

        nova_server = self.nova_client.servers.get(compute_id)
