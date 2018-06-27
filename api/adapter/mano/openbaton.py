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
import time
import uuid

import requests
from requests.auth import HTTPBasicAuth

from api.adapter import construct_adapter
from api.adapter.mano import ManoAdapterError
from api.generic import constants
from api.structures.objects import ResourceHandle, InstantiatedVnfInfo, NsInfo, VnfInfo, VnfExtCpInfo, \
    VnfcResourceInfo, NsdInfo
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class OpenbatonManoAdapterError(ManoAdapterError):
    """
    A problem occurred in the VNF LifeCycle Validation Openbaton MANO adapter API.
    """
    pass


class OpenbatonManoAdapterUnauthorized(Exception):
    """
    Openbaton access token not valid.
    """
    pass


class OpenbatonManoAdapter(object):
    def __init__(self, url, username, password, project, vim_info):
        self.url = url
        self.username = username
        self.password = password
        self.project = project
        self.vim_info = vim_info
        self.session = requests.Session()
        self.token = self.get_token(username, password)
        self.session.headers = {
            'Content-Type': 'application/json',
            'project-id': self.project,
            'Authorization': self.token
        }
        self.vnf_to_ns_mapping = {}
        self.nsd_info_ids = {}
        self.nsd_info_id_to_vnfd_ids = {}

    @log_entry_exit(LOG)
    def get_token(self, username, password):
        http_headers = {
            "Accept": "application/json",
        }
        body = {'username': username, 'password': password, 'grant_type': 'password'}
        try:
            response = requests.post(url=self.url + '/oauth/token',
                                     auth=HTTPBasicAuth('openbatonOSClient', 'secret'),
                                     data=body, headers=http_headers, verify=False)
            assert response.status_code == 200
        except Exception as e:
            LOG.debug(e)
            raise OpenbatonManoAdapterError('Unable to fetch Authorization token from %s' % self.url + '/oauth/token')
        token = str('Bearer ' + response.json()['access_token'])
        return token

    @log_entry_exit(LOG)
    def request(self, url, method, data=None, verify=False):
        # Perform the request once. If we get a 401 back then it might be because the auth token expired, so try to
        # re-authenticate and try again. If it still fails, bail.
        try:
            status_code, body = self.do_request(self.url + url, method, data, verify)
        except OpenbatonManoAdapterUnauthorized:
            self.token = self.get_token(self.username, self.password)
            self.session.headers['Authorization'] = self.token
            status_code, body = self.do_request(self.url + url, method, data, verify)
        return status_code, body

    @log_entry_exit(LOG)
    def do_request(self, url, method, data=None, verify=False):
        try:
            resp = self.session.request(url=url, method=method, data=data, verify=verify)
        except Exception as e:
            LOG.exception(e)
            raise OpenbatonManoAdapterError('Unable to run request on %s, method %s. Reason: %s' % (url, method, e))

        status_code = resp.status_code
        if status_code == 401:
            raise OpenbatonManoAdapterUnauthorized("Access token %s is invalid" % self.token)

        try:
            body = resp.json()
        except ValueError:
            body = None
        except Exception as e:
            LOG.exception(e)
            raise OpenbatonManoAdapterError('Unable to parse response. Reason: %s' % e)

        return status_code, body

    @log_entry_exit(LOG)
    def ns_create_id(self, nsd_id, ns_name, ns_description):
        url = '/api/v1/ns-records/%s' % nsd_id
        try:
            status_code, body = self.request(url=url, method='post')
            assert status_code == 201
            ns_instance_id = str(body['id'])
        except Exception as e:
            LOG.exception(e)
            raise OpenbatonManoAdapterError('Unable to instantiate NS for NSD ID %s. Reason: %s.' % (nsd_id, e))
        return ns_instance_id

    @log_entry_exit(LOG)
    def ns_instantiate(self, ns_instance_id, flavour_id, sap_data=None, pnf_info=None, vnf_instance_data=None,
                       nested_ns_instance_data=None, location_constraints=None, additional_param_for_ns=None,
                       additional_param_for_vnf=None, start_time=None, ns_instantiation_level_id=None,
                       additional_affinity_or_anti_affinity_rule=None):
        LOG.debug('"NS Instantiate" operation is not implemented in Openbaton!')
        LOG.debug('Instead of "Lifecycle Operation Occurrence Id", will just return the "NS Instance Id"')
        return 'ns_instantiate', ns_instance_id

    @log_entry_exit(LOG)
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        """
        This function does not have a direct mapping in Openbaton so it will just return the status of the specified
        resource type with given ID.
        """
        LOG.debug('"Lifecycle Operation Occurrence Id" is not implemented in Openbaton!')
        LOG.debug('Will return the state of the resource with given Id')

        if lifecycle_operation_occurrence_id is None:
            raise OpenbatonManoAdapterError('Lifecycle Operation Occurrence ID is absent')
        else:
            operation_type, resource_id = lifecycle_operation_occurrence_id

        if operation_type == 'ns_instantiate':
            url = '/api/v1/ns-records/%s' % resource_id
            try:
                resp, ns_config = self.request(url=url, method='get')
                ns_status = str(ns_config['status'])
            except Exception as e:
                LOG.exception(e)
                raise OpenbatonManoAdapterError('Unable to retrieve status for NS ID %s. Reason: %s' % (resource_id, e))
            if ns_status == 'ACTIVE':
                for vnfr in ns_config['vnfr']:
                    self.vnf_to_ns_mapping[str(vnfr['id'])] = resource_id
                return constants.OPERATION_SUCCESS
            elif ns_status == 'ERROR':
                return constants.OPERATION_FAILED
            else:
                return constants.OPERATION_PENDING

        if operation_type == 'ns_terminate':
            url = '/api/v1/ns-records/%s' % resource_id
            try:
                status_code, ns_config = self.request(url=url, method='get')
                if status_code == 404:
                    self.vnf_to_ns_mapping = {k: v for k, v in self.vnf_to_ns_mapping.items() if v != resource_id}
                    return constants.OPERATION_SUCCESS
                assert status_code == 200
                ns_status = str(ns_config['status'])
            except Exception as e:
                LOG.exception(e)
                raise OpenbatonManoAdapterError('Unable to get status for NS %s' % resource_id)

            if ns_status == 'ERROR':
                return constants.OPERATION_FAILED
            else:
                return constants.OPERATION_PENDING

    @log_entry_exit(LOG)
    def ns_query(self, filter, attribute_selector=None):
        ns_instance_id = filter['ns_instance_id']
        ns_info = NsInfo()
        ns_info.ns_instance_id = ns_instance_id
        try:
            url = '/api/v1/ns-records/%s' % ns_instance_id
            status_code, ns_config = self.request(url=url, method='get')
            if status_code == 404:
                # ns-instance-id not found, so assuming NOT_INSTANTIATED
                ns_info.ns_state = constants.NS_NOT_INSTANTIATED
                return ns_info
            assert status_code == 200
        except Exception as e:
            LOG.exception(e)
            raise OpenbatonManoAdapterError('Unable to retrieve status for NS ID %s. Reason: %s' %
                                            (ns_instance_id, e))
        ns_info.nsd_id = str(ns_config['descriptor_reference'])
        if ns_config['status'] == 'ACTIVE':
            ns_info.ns_state = constants.NS_INSTANTIATED
        else:
            ns_info.ns_state = constants.NS_NOT_INSTANTIATED
        ns_info.vnf_info = list()
        for constituent_vnfr in ns_config['vnfr']:
            vnf_info = self.build_vnf_info(constituent_vnfr)
            ns_info.vnf_info.append(vnf_info)
        return ns_info

    @log_entry_exit(LOG)
    def vnf_query(self, filter, attribute_selector=None):
        vnf_instance_id = filter['vnf_instance_id']
        vnf_info = VnfInfo()
        vnf_info.vnf_instance_id = vnf_instance_id
        ns_instance_id = self.vnf_to_ns_mapping.get(vnf_instance_id, '')
        try:
            url = '/api/v1/ns-records/%s/vnfrecords/%s' % (ns_instance_id, vnf_instance_id)
            status_code, vnf_config = self.request(url=url, method='get')
            if status_code == 400:
                vnf_info.instantiation_state = constants.VNF_NOT_INSTANTIATED
                return vnf_info
        except Exception as e:
            LOG.exception(e)
            raise OpenbatonManoAdapterError('Unable to retrieve status for VNF with ID %s. Reason: %s' %
                                            (vnf_instance_id, e))
        vnf_info = self.build_vnf_info(vnf_config)
        return vnf_info

    @log_entry_exit(LOG)
    def get_vim_helper(self, vim_id):
        url = '/api/v1/datacenters/%s' % vim_id
        try:
            status_code, vim_config = self.request(url=url, method='get')
            assert status_code == 200
        except Exception as e:
            LOG.exception(e)
            raise OpenbatonManoAdapterError('Unable to retrieve config for VIM with ID %s. Reason: %s' % (vim_id, e))
        try:
            vim_params = self.vim_info[vim_config['name']]
        except Exception as e:
            LOG.exception(e)
            raise OpenbatonManoAdapterError('Input Error. The VIM where the resource is instantiated is %s. '
                                            'Information about this VIM were not provided.' % str(vim_config['name']))

        return construct_adapter(vendor=vim_params['type'], module_type='vim', **vim_params['client_config'])

    @log_entry_exit(LOG)
    def ns_terminate(self, ns_instance_id, terminate_time=None, additional_param=None):
        url = '/api/v1/ns-records/%s' % ns_instance_id
        try:
            status_code, ns_term = self.request(url=url, method='delete')
            assert status_code == 204
        except Exception as e:
            LOG.exception(e)
            raise OpenbatonManoAdapterError('Unable to terminate NS instance ID %s. Reason: %s' % (ns_instance_id, e))

        return 'ns_terminate', ns_instance_id

    @log_entry_exit(LOG)
    def ns_delete_id(self, ns_instance_id):
        LOG.debug('"NS Delete ID" operation is not implemented in Openbaton!')

    @log_entry_exit(LOG)
    def wait_for_ns_stable_state(self, ns_instance_id, max_wait_time, poll_interval):
        if ns_instance_id is None:
            raise OpenbatonManoAdapterError('NS instance ID is absent')
        stable_states = ['ACTIVE', 'INACTIVE', 'ERROR', 'NOTFOUND']
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            url = '/api/v1/ns-records/%s' % ns_instance_id
            try:
                resp, ns_config = self.request(url=url, method='get')
                ns_status = ns_config.get('status', 'NOTFOUND')
                if ns_status in stable_states:
                    return True
                else:
                    LOG.debug('Expected NS status to be one of %s, got %s' % (stable_states, ns_status))
                    LOG.debug('Sleeping %s seconds' % poll_interval)
                    time.sleep(poll_interval)
                    elapsed_time += poll_interval
                    LOG.debug('Elapsed time %s seconds out of %s' % (elapsed_time, max_wait_time))
            except Exception as e:
                LOG.debug('Could not retrieve status for NS with ID %s' % ns_instance_id)
                raise OpenbatonManoAdapterError(e)
        LOG.debug('NS with ID %s did not reach a stable state after %s' % (ns_instance_id, max_wait_time))
        return False

    @log_entry_exit(LOG)
    def get_vnfd(self, vnfd_id):
        url = '/api/v1/vnf-descriptors/%s' % vnfd_id
        try:
            status_code, vnfd = self.request(url=url, method='get')
            assert status_code == 200
        except Exception as e:
            LOG.exception(e)
            raise OpenbatonManoAdapterError('Unable to retrieve config for VNFD with ID %s. Reason: %s' % (vnfd_id, e))
        return vnfd

    @log_entry_exit(LOG)
    def verify_vnf_sw_images(self, vnf_info, additional_param=None):
        vnfd_id = vnf_info.vnfd_id
        vnfd = self.get_vnfd(vnfd_id)

        expected_vdu_images = {}
        for vdu in vnfd['vdu']:
            expected_vdu_images[vdu['id']] = vdu['vm_image']

        for vnfc_resource_info in vnf_info.instantiated_vnf_info.vnfc_resource_info:
            vdu_id = vnfc_resource_info.vdu_id

            vim_id = vnfc_resource_info.compute_resource.vim_id
            vim = self.get_vim_helper(vim_id)
            resource_id = vnfc_resource_info.compute_resource.resource_id
            virtual_compute = vim.query_virtualised_compute_resource(filter={'compute_id': resource_id})
            image_id = virtual_compute.vc_image_id
            image_details = vim.query_image(image_id)
            image_name_vim = image_details.name

            image_name_vnfd = expected_vdu_images[vdu_id]
            if image_name_vim not in image_name_vnfd:
                LOG.debug('Unexpected image for VNFC %s, VDU type %s' % (resource_id, vdu_id))
                LOG.debug('Expected image name: %s; actual image name: %s' % (image_name_vnfd, image_name_vim))
                return False

        return True

    @log_entry_exit(LOG)
    def validate_vnf_allocated_vresources(self, vnf_info, additional_param=None):
        validation_result = True

        vnfd_id = vnf_info.vnfd_id
        vnfd = self.get_vnfd(vnfd_id)

        expected_vdu_flavours = {}
        for vdu in vnfd['vdu']:
            vdu_id = str(vdu['id'])
            expected_vdu_flavours[vdu_id] = list()
            if vdu.get('computation_requirement') is not None:
                vdu_flavour = str(vdu.get('computation_requirement', ''))
                expected_vdu_flavours[vdu_id].append(vdu_flavour)
            else:
                for flavour in vnfd['deployment_flavour']:
                    vdu_flavour = str(flavour['flavour_key'])
                    expected_vdu_flavours[vdu_id].append(vdu_flavour)

        for vnfc_resource_info in vnf_info.instantiated_vnf_info.vnfc_resource_info:
            vdu_id = vnfc_resource_info.vdu_id

            # Get VIM adapter object
            vim = self.get_vim_helper(vnfc_resource_info.compute_resource.vim_id)

            server_id = vnfc_resource_info.compute_resource.resource_id
            server_details = vim.server_get(server_id)
            server_flavour_id = server_details['flavor_id']
            flavour_details = vim.flavor_get(server_flavour_id)
            flavour_name_nova = str(flavour_details['name'])
            if flavour_name_nova not in expected_vdu_flavours.get(vdu_id, []):
                validation_result = False

        return validation_result

    @log_entry_exit(LOG)
    def verify_vnf_nsd_mapping(self, ns_instance_id, additional_param=None):
        ns_info = self.ns_query(filter={'ns_instance_id': ns_instance_id, 'additional_param': additional_param})
        nsd_id = ns_info.nsd_id
        nsd = self.get_nsd(nsd_id)
        expected_vnf_vnfd_mapping = {}
        for vnfd in nsd['vnfd']:
            vnf_product_name = str(vnfd['type'])
            expected_vnf_vnfd_mapping[vnf_product_name] = str(vnfd['id'])

        for vnf_info in ns_info.vnf_info:
            vnf_product_name = vnf_info.vnf_product_name
            if vnf_info.vnfd_id != expected_vnf_vnfd_mapping[vnf_product_name]:
                return False

        return True

    @log_entry_exit(LOG)
    def get_nsd(self, nsd_id):
        url = '/api/v1/ns-descriptors/%s' % nsd_id
        try:
            status_code, nsd = self.request(url=url, method='get')
            assert status_code == 200
        except Exception as e:
            LOG.exception(e)
            raise OpenbatonManoAdapterError('Unable to retrieve config for NSD with ID %s. Reason: %s' % (nsd_id, e))
        return nsd

    @log_entry_exit(LOG)
    def get_vnf_mgmt_addr_list(self, vnf_instance_id, additional_param=None):
        LOG.debug('Cannot get VNF management address in Openbaton')
        mgmt_addr_list = list()
        # TODO The rest of the function is commented because Openbaton populates vnf_address field with the IP addresses
        # TODO of all interfaces, hence the tests fail when we ping the management addresses. The comments should be
        # TODO removed when Openbaton will populate vnf_address field only with the management interface IP address.
        # ns_instance_id = self.vnf_to_ns_mapping.get(vnf_instance_id)
        # url = '/api/v1/ns-records/%s/vnfrecords/%s' % (ns_instance_id, vnf_instance_id)
        # try:
        #     status_code, vnf_config = self.request(url=url, method='get')
        #     assert status_code == 200
        # except Exception as e:
        #     LOG.exception(e)
        #     raise OpenbatonManoAdapterError('Unable to retrieve config for VNF with ID %s. Reason: %s' %
        #                                     (vnf_instance_id, e))
        # mgmt_addr_list = [str(addr) for addr in vnf_config['vnf_address']]

        return mgmt_addr_list

    @log_entry_exit(LOG)
    def build_vnf_info(self, vnf_config):
        vnf_info = VnfInfo()
        vnf_info.vnf_instance_id = str(vnf_config['id'])
        if vnf_config['status'] not in ['ACTIVE', 'INACTIVE']:
            vnf_info.instantiation_state = constants.VNF_NOT_INSTANTIATED
            return vnf_info

        vnf_info.instantiation_state = constants.VNF_INSTANTIATED
        vnf_info.vnfd_id = str(vnf_config['descriptor_reference'])
        vnf_info.vnf_instance_name = str(vnf_config['name'])
        vnf_info.vnf_product_name = str(vnf_config['type'])

        vnf_info.instantiated_vnf_info = InstantiatedVnfInfo()
        vnf_info.instantiated_vnf_info.vnf_state = constants.VNF_STATE['OPENBATON_VNF_STATE'][vnf_config['status']]

        vnf_info.instantiated_vnf_info.vnfc_resource_info = list()
        vnf_info.instantiated_vnf_info.ext_cp_info = list()

        for vdu in vnf_config['vdu']:
            for vnfc_instance in vdu['vnfc_instance']:
                vnfc_resource_info = VnfcResourceInfo()
                vnfc_resource_info.vnfc_instance_id = str(vnfc_instance['id'])
                vnfc_resource_info.vdu_id = str(vdu['parent_vdu'])

                vnfc_resource_info.compute_resource = ResourceHandle()
                vnfc_resource_info.compute_resource.vim_id = str(vnfc_instance['vim_id'])
                vnfc_resource_info.compute_resource.resource_id = str(vnfc_instance['vc_id'])

                vnf_info.instantiated_vnf_info.vnfc_resource_info.append(vnfc_resource_info)

                for ext_cp in vnfc_instance['vnfComponent']['connection_point']:
                    vnf_ext_cp_info = VnfExtCpInfo()
                    port_name = 'VNFD-' + str(ext_cp['id'])
                    vim_id = str(vnfc_instance['vim_id'])

                    vim = self.get_vim_helper(vim_id)
                    port_dict = vim.port_list(name=port_name)

                    for port_list in port_dict:
                        for port in port_list['ports']:
                            vnf_ext_cp_info = VnfExtCpInfo()
                            vnf_ext_cp_info.cp_instance_id = str(port['id'])
                            vnf_ext_cp_info.address = {
                                'mac': [str(port['mac_address'])],
                                'ip': []
                            }

                            for fixed_ip in port['fixed_ips']:
                                vnf_ext_cp_info.address['ip'].append(str(fixed_ip['ip_address']))

                    virtual_link_reference = str(ext_cp['virtual_link_reference'])
                    vnf_ext_cp_info.cpd_id = virtual_link_reference + '@' + str(vdu['name'])
                    vnf_info.instantiated_vnf_info.ext_cp_info.append(vnf_ext_cp_info)

        return vnf_info

    @log_entry_exit(LOG)
    def nsd_info_create(self, user_defined_data=None):
        # Generating a UUID
        nsd_info_id = str(uuid.uuid4())

        # Populate the NsdInfo object
        nsd_info = NsdInfo()
        nsd_info.nsd_info_id = nsd_info_id
        nsd_info.user_defined_data = user_defined_data

        # Store the mapping between the NsdInfo object and its UUID
        self.nsd_info_ids[nsd_info_id] = nsd_info

        return nsd_info_id

    @log_entry_exit(LOG)
    def nsd_info_query(self, filter, attribute_selector=None):
        nsd_info_id = filter['nsd_info_id']
        return self.nsd_info_ids.get(nsd_info_id)

    @log_entry_exit(LOG)
    def nsd_upload(self, nsd_info_id, nsd):
        # Get the NsdInfo object corresponding to the provided nsd_info_id
        nsd_info = self.nsd_info_ids.get(nsd_info_id)
        if nsd_info is None:
            raise OpenbatonManoAdapterError('No NsdInfo object with ID %s' % nsd_info_id)

        # Uploading the NSD
        if nsd is not None:
            raise NotImplementedError('Openbaton does not support ETSI NSD format')

        vendor_nsd = nsd_info.user_defined_data.get('vendor_nsd')
        if vendor_nsd is None:
            raise OpenbatonManoAdapterError('Vendor NSD not present in the user_defined_data')

        url = '/api/v1/ns-descriptors'
        try:
            status_code, body = self.request(url=url, method='post', data=vendor_nsd)
            assert status_code == 201
        except Exception as e:
            LOG.exception(e)
            raise OpenbatonManoAdapterError('Unable to upload the NSD')

        # Retrieving details about the on-boarded NSD
        nsd_id = str(body['id'])

        # Storing the IDs of the VNFDs to be deleted after the NSD is deleted
        constituent_vnfd_ids = list()
        for vnfd in body['vnfd']:
            constituent_vnfd_ids.append(vnfd['id'])
        self.nsd_info_id_to_vnfd_ids[nsd_info_id] = constituent_vnfd_ids

        # Updating the corresponding NsdInfo object with the details of the on-boarded NSD
        nsd_info.nsd_id = nsd_id

    @log_entry_exit(LOG)
    def nsd_fetch(self, nsd_info_id):
        # Get the NsdInfo object corresponding to the provided nsd_info_id
        nsd_info = self.nsd_info_ids.get(nsd_info_id)
        if nsd_info is None:
            raise OpenbatonManoAdapterError('No NsdInfo object with ID %s' % nsd_info_id)

        # Get the NSD corresponding to the provided nsd_info_id
        nsd_id = nsd_info.nsd_id
        if nsd_id is None:
            raise OpenbatonManoAdapterError('NsdInfo object with ID %s does not have the NsdId attribute set'
                                            % nsd_info_id)
        nsd = self.get_nsd(nsd_id)

        return nsd

    @log_entry_exit(LOG)
    def nsd_delete(self, nsd_info_id):
        # Get the NsdInfo object corresponding to the provided nsd_info_id
        nsd_info = self.nsd_info_ids.get(nsd_info_id)
        if nsd_info is None:
            raise OpenbatonManoAdapterError('No NsdInfo object with ID %s' % nsd_info_id)

        # If the NsdInfo object holds information about an NSD, delete it
        nsd_id = nsd_info.nsd_id
        if nsd_id is not None:
            url = '/api/v1/ns-descriptors/%s' % nsd_id
            try:
                status_code, _ = self.request(url=url, method='delete')
                assert status_code == 204
            except Exception as e:
                LOG.exception(e)
                raise OpenbatonManoAdapterError('Unable to delete NSD %s' % nsd_id)

            # Check the NSD has been deleted by the MANO. This check is added because there is no other way of checking
            # that the NSD has been deleted.
            try:
                self.get_nsd(nsd_id)
            except OpenbatonManoAdapterError:
                LOG.debug('NSD %s has been deleted' % nsd_id)
            else:
                raise OpenbatonManoAdapterError('NSD %s has not been deleted' % nsd_id)

        # Delete the NsdInfo object
        self.nsd_info_ids.pop(nsd_info_id)

        # Delete the VNFDs on-boarded together with the NSD
        constituent_vnfd_ids = self.nsd_info_id_to_vnfd_ids[nsd_info_id]
        for vnfd_id in constituent_vnfd_ids:
            url = '/api/v1/vnf-descriptors/%s' % vnfd_id
            try:
                status_code, _ = self.request(url=url, method='delete')
                assert status_code == 204
            except Exception as e:
                LOG.exception(e)
                raise OpenbatonManoAdapterError('Unable to delete VNFD %s' % vnfd_id)

        return nsd_info_id
