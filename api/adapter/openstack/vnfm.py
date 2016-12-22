import logging
import os_client_config
from utils.logging_module import log_entry_exit
from tackerclient.tacker.client import Client as TackerClient

LOG = logging.getLogger(__name__)


class VnfmOpenstackAdapter(object):
    def __init__(self,
                 auth_url=None,
                 username=None,
                 password=None,
                 identity_api_version=None,
                 project_name=None,
                 project_domain_name=None,
                 user_domain_name=None
                 ):
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
            print 'Unable to create', self.__class__.__name__, 'instance'
            raise


    def get_operation_status(self, lifecycle_operation_occurrence_id):
        LOG.warning('"Lifecycle Operation Occurence Id" is not implemented in OpenStack!')
        LOG.warning('Will return the state of the resource with given Id')

        vnf_id = lifecycle_operation_occurrence_id
        tacker_show_vnf = self.tacker_client.show_vnf(vnf_id)

        vnf_states_mapping = {'ACTIVE': 'SUCCESS',
                              'ERROR': 'FAILED',
                              'PENDING_CREATE': 'PENDING',
                              'PENDING_DELETE': 'PENDING'}

        return vnf_states_mapping[tacker_show_vnf['vnf']['status']]


    def vnf_instantiate(self, vnf_instance_id, flavour_id, instantiation_level_id=None, ext_virtual_link=None,
                        ext_managed_virtual_link=None, localization_language=None, additional_param=None):
        LOG.warning('"VNF Instantiate" operation is not implemented in OpenStack!')
        LOG.warning('Instead of "Lifecycle Operation Occurence Id", will just return the "VNF Instance Id"')
        return vnf_instance_id

    # Working in progress for adding vnf_instance_description
    def vnf_create_id(self, vnfd_id, vnf_instance_name, vnf_instance_description):
        vnf_dict = dict()
        vnf_dict = {'vnf': {'vnfd_id': vnfd_id,
                            'name': vnf_instance_name}}
        vnf_instance = self.tacker_client.create_vnf(body=vnf_dict)
        return vnf_instance['vnf']['id']

