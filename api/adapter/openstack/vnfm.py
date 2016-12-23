import logging
import json
import os_client_config
from utils.logging_module import log_entry_exit
from tackerclient.tacker.client import Client as TackerClient
from api.generic import constants
import tackerclient.common.exceptions


LOG = logging.getLogger(__name__)


class VnfmOpenstackAdapter(object):
    def __init__(self, auth_url=None, username=None, password=None, identity_api_version=None, project_name=None,
                 project_domain_name=None, user_domain_name=None):
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

        tacker_status = tacker_show_vnf['vnf']['status']

        return constants.OPENSTACK_VNF_STATES_MAPPING[tacker_status]

    def vnf_instantiate(self, vnf_instance_id, flavour_id, instantiation_level_id=None, ext_virtual_link=None,
                        ext_managed_virtual_link=None, localization_language=None, additional_param=None):
        LOG.warning('"VNF Instantiate" operation is not implemented in OpenStack!')
        LOG.warning('Instead of "Lifecycle Operation Occurence Id", will just return the "VNF Instance Id"')
        return vnf_instance_id


    @log_entry_exit(LOG)
    def vnf_create_id(self, vnfd_id, vnf_instance_name, vnf_instance_description, **kwargs):
        vnf_dict = {'vnf': {'vnfd_id': vnfd_id,
                            'name': vnf_instance_name}}

        try:
            vnf_instance = self.tacker_client.create_vnf(body=vnf_dict)
            LOG.info("Response from vnfm:\n%s" % json.dumps(vnf_instance, indent=4, separators=(',', ': ')))
        except tackerclient.common.exceptions.TackerException:
            return None
        return vnf_instance['vnf']['id']

