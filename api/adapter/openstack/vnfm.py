import json
import logging

import os_client_config
from tackerclient.tacker.client import Client as TackerClient
import tackerclient.common.exceptions

from api.generic import constants
from utils.logging_module import log_entry_exit

# Instantiate logger
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

    @log_entry_exit(LOG)
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        LOG.warning('"Lifecycle Operation Occurence Id" is not implemented in OpenStack!')
        LOG.warning('Will return the state of the resource with given Id')

        # TODO: call etsi standard function
        vnf_id = lifecycle_operation_occurrence_id
        tacker_show_vnf = self.tacker_client.show_vnf(vnf_id)

        tacker_status = tacker_show_vnf['vnf']['status']

        return constants.OPERATION_STATUS['OPENSTACK_VNF_STATE'][tacker_status]

    @log_entry_exit(LOG)
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

    @log_entry_exit(LOG)
    def vnf_query(self, filter, attribute_selector=None):
        """
        This operation provides information about VNF instances. The applicable VNF instances can be chosen based on
        filtering criteria, and the information can be restricted to selected attributes.

        This function was written in accordance with section 7.2.9 of GS NFV-IFA 007 - v2.1.1.

        :param filter:              Filter to select the VNF instance(s) about which information is queried.
        :param attribute_selector:  Provides a list of attribute names. If present, only these attributes are returned
                                    for the VNF instance(s) matching the filter. If absent, the complete information is
                                    returned for the VNF instance(s) matching the filter.
        :return:                    The information items about the selected VNF instance(s) that are returned. If
                                    attribute_selector is present, only the attributes listed in attribute_selector are
                                    returned for the selected VNF instance(s).
        """
        vnf_instance_id = filter['vnf_instance_id']
        vnf_info = dict()
        vnf_info['vnf_instance_id'] = vnf_instance_id

        try:
            tacker_show_vnf = self.tacker_client.show_vnf(vnf_instance_id)['vnf']
        except tackerclient.common.exceptions.TackerException:
            return vnf_info

        vnf_info['vnf_instance_name'] = tacker_show_vnf['name']
        vnf_info['vnf_instance_description'] = tacker_show_vnf['description']
        vnf_info['vnfd_id'] = tacker_show_vnf['vnfd_id']
        vnf_info['instantiation_state'] = constants.VNF_INSTANTIATION_STATE['OPENSTACK_VNF_STATE'][tacker_show_vnf['status']]

        vnf_info['instantiated_vnf_info'] = dict()
        vnf_info['instantiated_vnf_info']['vnf_state'] = constants.VNF_STATE['OPENSTACK_VNF_STATE'][tacker_show_vnf['status']]

        return vnf_info
