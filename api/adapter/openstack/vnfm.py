import json
import logging
import yaml

import os_client_config
from tackerclient.tacker.client import Client as TackerClient
import tackerclient.common.exceptions

from api.generic.vim import Vim
from api.generic import constants
from api.structures.objects import VnfInfo, InstantiatedVnfInfo, VnfcResourceInfo, ResourceHandle
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class VnfmOpenstackAdapter(object):
    """
    Class of functions that map the ETSI standard operations exposed by the VNFM to the operations exposed by the
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
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        """
        This function does not have a direct mapping in OpenStack so it will just return the status of the VNF with
        given ID.
        """
        LOG.debug('"Lifecycle Operation Occurrence Id" is not implemented in OpenStack!')
        LOG.debug('Will return the state of the resource with given Id')

        vnf_id = lifecycle_operation_occurrence_id

        try:
            tacker_show_vnf = self.tacker_client.show_vnf(vnf_id)
        except tackerclient.common.exceptions.NotFound:
            # Temporary hack. When vnf_terminate() is called, declare the VNF as terminated when Tacker raises exception
            # because the VNF can no longer be found
            return constants.OPERATION_SUCCESS

        tacker_status = tacker_show_vnf['vnf']['status']

        return constants.OPERATION_STATUS['OPENSTACK_VNF_STATE'][tacker_status]

    @log_entry_exit(LOG)
    def vnf_delete_id(self, vnf_instance_id):
        """
        This function does not have a direct mapping in OpenStack so it will just return the VNF instance ID.

        :param vnf_instance_id: VNF instance identifier to be deleted.
        :return:                Nothing.
        """
        LOG.warning('"VNF Delete ID" operation is not implemented in OpenStack!')

    @log_entry_exit(LOG)
    def vnf_instantiate(self, vnf_instance_id, flavour_id, instantiation_level_id=None, ext_virtual_link=None,
                        ext_managed_virtual_link=None, localization_language=None, additional_param=None):
        """
        This function does not have a direct mapping in OpenStack so it will just return the VNF instance ID.

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
        :return:                            VNF instance ID.
        """
        LOG.debug('"VNF Instantiate" operation is not implemented in OpenStack!')
        LOG.debug('Instead of "Lifecycle Operation Occurrence Id", will just return the "VNF Instance Id"')
        return vnf_instance_id

    @log_entry_exit(LOG)
    def vnf_create_id(self, vnfd_id, vnf_instance_name, vnf_instance_description, **kwargs):
        """
        This function creates a VNF with the specified ID and name.
        """
        vnf_dict = {'vnf': {'vnfd_id': vnfd_id,
                            'name': vnf_instance_name}}

        try:
            vnf_instance = self.tacker_client.create_vnf(body=vnf_dict)
            LOG.debug("Response from vnfm:\n%s" % json.dumps(vnf_instance, indent=4, separators=(',', ': ')))
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
        vnf_info = VnfInfo()
        vnf_info.vnf_instance_id = vnf_instance_id.encode()

        try:
            tacker_show_vnf = self.tacker_client.show_vnf(vnf_instance_id)['vnf']
        except tackerclient.common.exceptions.TackerException:
            return vnf_info

        vnf_info.vnf_instance_name = tacker_show_vnf['name'].encode()
        vnf_info.vnf_instance_description = tacker_show_vnf['description'].encode()
        vnf_info.vnfd_id = tacker_show_vnf['vnfd_id'].encode()
        vnf_info.instantiation_state = constants.VNF_INSTANTIATION_STATE['OPENSTACK_VNF_STATE'][
            tacker_show_vnf['status']]

        vnf_info.instantiated_vnf_info = InstantiatedVnfInfo()
        vnf_info.instantiated_vnf_info.vnf_state = constants.VNF_STATE['OPENSTACK_VNF_STATE'][
            tacker_show_vnf['status']]

        vnf_info.instantiated_vnf_info.vnfc_resource_info = list()
        try:
            tacker_list_vnf_resources = self.tacker_client.list_vnf_resources(vnf_instance_id)['resources']
            for vnf_resource in tacker_list_vnf_resources:
                vnf_resource_type = vnf_resource.get('type')
                vnf_resource_id = vnf_resource.get('id')
                vnf_resource_name = vnf_resource.get('name')

                if vnf_resource_type == 'OS::Nova::Server':
                    vnfc_resource_info = VnfcResourceInfo()
                    vnfc_resource_info.vnfc_instance_id = vnf_resource_id.encode()
                    vnfc_resource_info.vdu_id = vnf_resource_name.encode()

                    vnfc_resource_info.compute_resource = ResourceHandle()
                    vnfc_resource_info.compute_resource.vim_id = tacker_show_vnf['vim_id'].encode()
                    vnfc_resource_info.compute_resource.resource_id = vnf_resource_id.encode()

                    vnf_info.instantiated_vnf_info.vnfc_resource_info.append(vnfc_resource_info)

        except tackerclient.common.exceptions.TackerException:
            return vnf_info

        return vnf_info

    @log_entry_exit(LOG)
    def vnf_terminate(self, vnf_instance_id, termination_type, graceful_termination_type=None):
        """
        This function terminates the VNF with the given ID.

        :param vnf_instance_id:             Identifier of the VNF instance to be terminated.
        :param termination_type:            Signals whether forceful or graceful termination is requested.
        :param graceful_termination_type:   The time interval to wait for the VNF to be taken out of service during
                                            graceful termination, before shutting down the VNF and releasing the
                                            resources.
        :return:                            VNF instance ID.
        """
        self.tacker_client.delete_vnf(vnf_instance_id)
        return vnf_instance_id

    @log_entry_exit(LOG)
    def get_vim(self, vim_id):
        vim_details = self.tacker_client.show_vim(vim_id)['vim']
        vim_auth_cred = vim_details['auth_cred']
        vim_type = vim_details['type']

        # TODO: get from config file
        vim_auth_cred['password'] = 'admin'

        return Vim(vendor=vim_type, **vim_auth_cred)

    @log_entry_exit(LOG)
    def get_vnfd(self, vnfd_id):
        return yaml.load(self.tacker_client.show_vnfd(vnfd_id)['vnfd']['attributes']['vnfd'])
