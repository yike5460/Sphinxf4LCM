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
import re
import time

import requests

from requests.auth import HTTPBasicAuth
from api.adapter import construct_adapter
from api.adapter.mano import ManoAdapterError
from api.generic import constants
from api.structures.objects import ResourceHandle, InstantiatedVnfInfo, NsInfo, VnfInfo, VnfExtCpInfo, VnfcResourceInfo
from utils.logging_module import log_entry_exit
import json

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
    def __init__(self, api_url, username, password, project):
        self.api_url = api_url
        self.username = username
        self.password = password
        self.project = project
        self.session = requests.Session()
        self.token = self.get_token(username, password)
        self.session.headers = {
            'Content-Type': 'application/json',
            'project-id': self.project,
            'Authorization': self.token
        }
        self.vnf_to_ns_mapping = dict()

    @log_entry_exit(LOG)
    def get_token(self, username, password):
        http_headers = {
            "Accept": "application/json",
        }
        body = (('username', username), ('password', password), ('grant_type', 'password'))
        response = requests.post(url=self.api_url + '/oauth/token', auth=HTTPBasicAuth('openbatonOSClient', 'secret'),
                                 data=body, headers = http_headers, verify=False)
        try:
            assert response.status_code == 200
        except Exception:
            raise OpenbatonManoAdapterError('Unable to fetch Authorization token from %s' %
                                            self.api_url + '/oauth/token')
        token = str('Bearer ' + response.json()['access_token'])
        return token

    @log_entry_exit(LOG)
    def do_request(self, url, method, **kwargs):
        # Perform the request once. If we get a 401 back then it
        # might be because the auth token expired, so try to
        # re-authenticate and try again. If it still fails, bail.
        try:
            kwargs.setdefault('data', {})
            kwargs.setdefault('verify', False)
            resp, body = self._do_request(self.api_url + url, method, **kwargs)
        except OpenbatonManoAdapterUnauthorized:
            self.token = self.get_token(self.username, self.password)
            self.session.headers['Authorization'] = self.token
            resp, body = self._do_request(self.api_url + url, method, **kwargs)
            return resp, body
        return resp, body

    @log_entry_exit(LOG)
    def _do_request(self, url, method, **kwargs):
        data = kwargs.pop('data', {})
        verify = kwargs.pop('verify', False)
        try:
            resp = self.session.request(url=url, method=method, data=data, verify=verify)
        except Exception as e:
            LOG.exception(e)
            raise OpenbatonManoAdapterError('Unable to run request on %s, method %s. Reason: %s' % (url, method, e))
        if resp.status_code == 401:
            raise OpenbatonManoAdapterUnauthorized("Access token %s is invalid" % self.token)
        try:
            body = json.loads(resp.text)
        except ValueError:
            body = {}
        return resp, body

    @log_entry_exit(LOG)
    def ns_create_id(self, nsd_id, ns_name, ns_description):
        url = '/api/v1/ns-records/%s' % nsd_id
        method = 'post'
        try:
            resp, body = self.do_request(url=url, method=method)
            assert resp.status_code == 201
            ns_instance_id = str(body.get('id'))
        except Exception as e:
            LOG.exception(e)
            raise OpenbatonManoAdapterError('Unable to instantantiate NS for NSD ID %s. Reason: %s. '
                                            % (nsd_id, e.message))
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
        This function does not have a direct mapping in Openbaton so it will just return the status of the
        specified resource type with given ID.
        """
        LOG.debug('"Lifecycle Operation Occurrence Id" is not implemented in Openbaton!')
        LOG.debug('Will return the state of the resource with given Id')

        if lifecycle_operation_occurrence_id is None:
            raise OpenbatonManoAdapterError('Lifecycle Operation Occurrence ID is absent')
        else:
            operation_type, resource_id = lifecycle_operation_occurrence_id

        if operation_type == 'ns_instantiate':
            url = '/api/v1/ns-records/%s' % resource_id
            method = 'get'
            try:
                resp, ns_config = self.do_request(url=url, method=method)
                ns_status = str(ns_config.get('status'))
            except Exception as e:
                LOG.exception(e)
                raise OpenbatonManoAdapterError('Unable to retrieve status for NS ID %s. Reason: %s' %
                                                (resource_id, e.message))
            if ns_status == 'ACTIVE':
                for vnfr in ns_config.get('vnfr'):
                    self.vnf_to_ns_mapping[str(vnfr.get('id'))] = resource_id
                return constants.OPERATION_SUCCESS
            elif ns_status == 'NULL':
                return constants.OPERATION_PENDING
            elif ns_status == 'ERROR':
                return constants.OPERATION_FAILED

        if operation_type == 'ns_terminate':
            url = '/api/v1/ns-records/%s' % resource_id
            method = 'get'
            try:
                resp, ns_config = self.do_request(url=url, method=method)
                if resp.status_code == 404:
                    self.vnf_to_ns_mapping = {k:v for k, v in self.vnf_to_ns_mapping.items() if v != resource_id}
                    return constants.OPERATION_SUCCESS
                assert resp.status_code == 200
                ns_status = str(ns_config.get('status'))
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
            method = 'get'
            resp, ns_config = self.do_request(url=url, method=method)
            if resp.status_code == 404:
                # ns-instance-id not found, so assuming NOT_INSTANTIATED
                ns_info.ns_state = constants.NS_NOT_INSTANTIATED
                return ns_info
            assert resp.status_code == 200
        except Exception as e:
            LOG.exception(e)
            raise OpenbatonManoAdapterError('Unable to retrieve status for NS ID %s. Reason: %s' %
                                            (ns_instance_id, e.message))
        ns_info.nsd_id = str(ns_config.get('descriptor_reference'))
        if ns_config.get('status') == 'ACTIVE':
            ns_info.ns_state = constants.NS_INSTANTIATED
        else:
            ns_info.ns_state = constants.NS_NOT_INSTANTIATED
        ns_info.vnf_info = list()
        for constituent_vnfr in ns_config.get('vnfr'):
            vnf_info = VnfInfo()
            vnf_info.vnf_instance_id = str(constituent_vnfr.get('id'))
            if constituent_vnfr.get('status') == 'ACTIVE':
                vnf_info.instantiation_state = constants.VNF_INSTANTIATED
            else:
                vnf_info.instantiation_state = constants.VNF_NOT_INSTANTIATED
            vnf_info.vnfd_id = str(constituent_vnfr.get('descriptor_reference'))
            vnf_info.vnf_instance_name = str(constituent_vnfr.get('name'))
            vnf_info.vnf_product_name = str(constituent_vnfr.get('name'))
            vnf_info.instantiated_vnf_info = InstantiatedVnfInfo()
            if constituent_vnfr.get('status') == 'ACTIVE':
                vnf_info.instantiated_vnf_info.vnf_state = constants.VNF_STARTED
            else:
                vnf_info.instantiated_vnf_info.vnf_state = constants.VNF_STOPPED
            vnf_info.instantiated_vnf_info.vnfc_resource_info = list()
            vnf_info.instantiated_vnf_info.ext_cp_info = list()
            for vdu in constituent_vnfr.get('vdu'):
                for vnfc_instance in vdu.get('vnfc_instance'):
                    vnfc_resource_info = VnfcResourceInfo()
                    vnfc_resource_info.vnfc_instance_id = str(vnfc_instance.get('id'))
                    vnfc_resource_info.vdu_id = str(vdu.get('id'))
                    vnfc_resource_info.compute_resource = ResourceHandle()
                    vnfc_resource_info.compute_resource.vim_id = str(vnfc_instance.get('vim_id'))
                    vnfc_resource_info.compute_resource.resource_id = str(vnfc_instance.get('vc_id'))
                    vnf_info.instantiated_vnf_info.vnfc_resource_info.append(vnfc_resource_info)
                    vnf_info.instantiated_vnf_info.ext_cp_info = list()
                    for ext_cp in vnfc_instance.get('vnfComponent').get('connection_point'):
                        vnf_ext_cp_info = VnfExtCpInfo()
                        vnf_ext_cp_info.cp_instance_id = str(ext_cp.get('id'))
                        vnf_ext_cp_info.cpd_id = str(ext_cp.get('virtual_link_reference_id'))
                        # virtual_link_reference = str(ext_cp['virtual_link_reference'])
                        vnf_ext_cp_info.address = list()
                        # for ip in vnfc_instance['ips']:
                        #     if ip['netName'] == virtual_link_reference:
                        #         vnf_ext_cp_info.address.append(str(ip['ip']))
                        #         break
                        vnf_info.instantiated_vnf_info.ext_cp_info.append(vnf_ext_cp_info)
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
            method = 'get'
            resp, vnf_config = self.do_request(url=url, method=method)
            if resp.status_code == 400:
                # vnf-instance-id not found, so assuming NOT_INSTANTIATED
                vnf_info.instantiation_state = constants.VNF_NOT_INSTANTIATED
                return vnf_info
        except Exception as e:
            LOG.exception(e)
            raise OpenbatonManoAdapterError('Unable to retrieve status for VNF with ID %s. Reason: %s' %
                                            (vnf_instance_id, e.message))
        print resp.status_code
        print vnf_config
        vnf_info.vnf_instance_id = str(vnf_config.get('id'))
        if vnf_config.get('status') == 'ACTIVE':
            vnf_info.instantiation_state = constants.VNF_INSTANTIATED
        else:
            vnf_info.instantiation_state = constants.VNF_NOT_INSTANTIATED
        vnf_info.vnfd_id = str(vnf_config.get('descriptor_reference'))
        vnf_info.vnf_instance_name = str(vnf_config.get('name'))
        vnf_info.vnf_product_name = str(vnf_config.get('name'))
        vnf_info.instantiated_vnf_info = InstantiatedVnfInfo()
        if vnf_config.get('status') == 'ACTIVE':
            vnf_info.instantiated_vnf_info.vnf_state = constants.VNF_STARTED
        else:
            vnf_info.instantiated_vnf_info.vnf_state = constants.VNF_STOPPED
        vnf_info.instantiated_vnf_info.vnfc_resource_info = list()
        vnf_info.instantiated_vnf_info.ext_cp_info = list()
        for vdu in vnf_config.get('vdu'):
            for vnfc_instance in vdu.get('vnfc_instance'):
                vnfc_resource_info = VnfcResourceInfo()
                vnfc_resource_info.vnfc_instance_id = str(vnfc_instance.get('id'))
                vnfc_resource_info.vdu_id = str(vdu.get('id'))
                vnfc_resource_info.compute_resource = ResourceHandle()
                vnfc_resource_info.compute_resource.vim_id = str(vnfc_instance.get('vim_id'))
                vnfc_resource_info.compute_resource.resource_id = str(vnfc_instance.get('vc_id'))
                vnf_info.instantiated_vnf_info.vnfc_resource_info.append(vnfc_resource_info)
                vnf_info.instantiated_vnf_info.ext_cp_info = list()
                for ext_cp in vnfc_instance.get('vnfComponent').get('connection_point'):
                    vnf_ext_cp_info = VnfExtCpInfo()
                    vnf_ext_cp_info.cp_instance_id = str(ext_cp.get('id'))
                    vnf_ext_cp_info.cpd_id = str(ext_cp.get('virtual_link_reference_id'))
                    # virtual_link_reference = str(ext_cp['virtual_link_reference'])
                    vnf_ext_cp_info.address = list()
                    # for ip in vnfc_instance['ips']:
                    #     if ip['netName'] == virtual_link_reference:
                    #         vnf_ext_cp_info.address.append(str(ip['ip']))
                    #         break
                    vnf_info.instantiated_vnf_info.ext_cp_info.append(vnf_ext_cp_info)
        return vnf_info

    @log_entry_exit(LOG)
    def get_vim_helper(self, vim_id):
        url = '/api/v1/datacenters/%s' % vim_id
        method = 'get'
        try:
            resp, vim_config = self.do_request(url=url, method=method)
            assert resp.status_code == 200
        except Exception as e:
            LOG.exception(e)
            raise OpenbatonManoAdapterError('Unable to retrieve config for VIM with ID %s. Reason: %s' %
                                            (vim_id, e.message))
        if vim_config.get('type') == 'openstack':
            vim_vendor = 'openstack'
            vim_params = {
                'auth_url': vim_config.get('authUrl'),
                'username': vim_config.get('username'),
                # 'password': vim_config.get('password'),
                'password': 'admin',
                'project_domain_name': 'default',
                'project_name': 'admin',
                'user_domain_name': 'default'
            }
        else:
            raise OpenbatonManoAdapterError('Unsupported VIM type: %s' % vim_config.get('type'))

        return construct_adapter(vendor=vim_vendor, module_type='vim', **vim_params)

    @log_entry_exit(LOG)
    def ns_terminate(self, ns_instance_id, terminate_time=None, additional_param=None):
        url = '/api/v1/ns-records/%s' % ns_instance_id
        method = 'delete'
        try:
            resp, ns_term = self.do_request(url=url, method=method)
            assert resp.status_code == 204
        except Exception as e:
            LOG.exception(e)
            raise OpenbatonManoAdapterError('Unable to terminate NS instance ID %s. Reason: %s' %
                                            (ns_instance_id, e.message))

        return 'ns_terminate', ns_instance_id

    @log_entry_exit(LOG)
    def ns_delete_id(self, ns_instance_id):
        LOG.debug('"NS Delete ID" operation is not implemented in Openbaton!')

    @log_entry_exit(LOG)
    def wait_for_ns_stable_state(self, ns_instance_id, max_wait_time, poll_interval):
        if ns_instance_id is None:
            raise OpenbatonManoAdapterError('NS instance ID is absent')
        stable_states = ['ACTIVE', 'ERROR']
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            url = '/api/v1/ns-records/%s' % ns_instance_id
            method = 'get'
            try:
                resp, ns_config = self.do_request(url=url, method=method)
                ns_status = ns_config.get('status', 'NOTFOUND')
                assert resp.status_code == 404
                return True
            except Exception as e:
                LOG.debug('Got NS status %s for NS with ID %s' % (ns_status, ns_instance_id))
                if ns_status in stable_states:
                    return True
                else:
                    LOG.debug('Expected NS status to be one of %s, got %s' % (stable_states, ns_status))
                    LOG.debug('Sleeping %s seconds' % poll_interval)
                    time.sleep(poll_interval)
                    elapsed_time += poll_interval
                    LOG.debug('Elapsed time %s seconds out of %s' % (elapsed_time, max_wait_time))

        LOG.debug('NS with ID %s did not reach a stable state after %s' % (ns_instance_id, max_wait_time))
        return False

