import os_client_config
from tackerclient.tacker.client import Client as TackerClient

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



    def vnf_instantiate(self,
                        vnf_instance_id,
                        flavour_id,
                        ext_virtual_link,
                        ext_managed_virtual_link,
                        localization_language,
                        **kwargs):
        pass

    def create_vnf_id(self, vnfd_id, vnf_instance_name, vnf_instance_description):
        pass

    def get_vnf_state(self, vnf_id):
        tacker_show_vnf = self.tacker_client.show_vnf(vnf_id)
        return tacker_show_vnf['vnf']['status']
