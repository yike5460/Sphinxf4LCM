import json
import logging
import time
import uuid

import requests
from requests.auth import HTTPBasicAuth
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from api.adapter.mano import ManoAdapterError
from api.generic import constants
from api.structures.objects import NsInfo
from utils.logging_module import log_entry_exit

LOG = logging.getLogger(__name__)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class RiftManoAdapterError(ManoAdapterError):
    """
    A problem occurred in the VNF LifeCycle Validation Rift MANO adapter API.
    """
    pass


class RiftManoAdapter(object):
    def __init__(self, url, username, password, project):
        self.url = url
        self.username = username
        self.password = password
        self.project = project

        self.session = requests.Session()
        self.session.headers = {
            'Accept': 'application/vnd.yang.data+json',
            'Content-type': 'application/vnd.yang.data+json'
        }
        self.session.auth = HTTPBasicAuth(username=self.username, password=self.password)
        self.session.verify = False

        self.nsr_metadata = {}

    @log_entry_exit(LOG)
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        # TODO: the get logic inside ifs should be moved into functions

        operation_type, resource_id = lifecycle_operation_occurrence_id

        if operation_type == 'ns_instantiate':
            resource = '/api/operational/project/ns-instance-opdata/nsr/%s' % resource_id
            try:
                response = self.session.get(url=self.url + resource)
                assert response.status_code == 200
                json_content = response.json()
            except Exception as e:
                LOG.exception(e)
                raise RiftManoAdapterError('Unable to get opdata for NS %s' % resource_id)

            ns_op_status = json_content['rw-project:project']['nsr:ns-instance-opdata']['nsr'][0]['operational-status']

            if ns_op_status == 'running':
                return constants.OPERATION_SUCCESS
            elif ns_op_status == 'failed':
                return constants.OPERATION_FAILED
            else:
                return constants.OPERATION_PENDING

        if operation_type == 'ns_terminate':
            resource = '/api/operational/project/ns-instance-opdata/nsr/%s' % resource_id
            try:
                response = self.session.get(url=self.url + resource)
                if response.status_code == 204:
                    return constants.OPERATION_SUCCESS

                assert response.status_code == 200
                json_content = response.json()
            except Exception as e:
                LOG.exception(e)
                raise RiftManoAdapterError('Unable to get opdata for NS %s' % resource_id)

            ns_op_status = json_content['rw-project:project']['nsr:ns-instance-opdata']['nsr'][0]['operational-status']

            if ns_op_status == 'failed':
                return constants.OPERATION_FAILED
            else:
                return constants.OPERATION_PENDING

        raise RiftManoAdapterError('Unknown operation type "%s"' % operation_type)

    @log_entry_exit(LOG)
    def ns_create_id(self, nsd_id, ns_name, ns_description):
        ns_instance_id = str(uuid.uuid4())

        self.nsr_metadata[ns_instance_id] = {
            'id': ns_instance_id,
            'name': ns_name,
            'nsd': self.get_nsd(nsd_id),
            'short-name': ns_name,
            'admin-status': 'ENABLED',
            'description': str(ns_description)
        }

        return ns_instance_id

    @log_entry_exit(LOG)
    def get_nsd(self, nsd_id):
        resource = '/api/config/project/nsd-catalog/nsd/%s' % nsd_id

        try:
            response = self.session.get(url=self.url + resource)
            assert response.status_code == 200
            json_content = response.json()
        except Exception as e:
            LOG.exception(e)
            raise RiftManoAdapterError('Unable to get NSD %s' % nsd_id)

        nsd = json_content['rw-project:project']['project-nsd:nsd-catalog']['nsd'][0]
        nsd.pop('rw-project-nsd:meta')

        return nsd

    @log_entry_exit(LOG)
    def ns_instantiate(self, ns_instance_id, flavour_id, sap_data=None, pnf_info=None, vnf_instance_data=None,
                       nested_ns_instance_data=None, location_constraints=None, additional_param_for_ns=None,
                       additional_param_for_vnf=None, start_time=None, ns_instantiation_level_id=None,
                       additional_affinity_or_anti_affinity_rule=None):

        resource = '/api/config/project/Spirent/ns-instance-config/nsr'

        nsr_metadata = self.nsr_metadata[ns_instance_id]
        nsr_metadata['datacenter'] = additional_param_for_ns['datacenter']
        request_body = {
            'nsr': [nsr_metadata]
        }

        try:
            response = self.session.post(url=self.url + resource, json=request_body)
            assert response.status_code == 201
            assert 'ok' in response.json().get('rpc-reply', {})
        except Exception as e:
            LOG.exception(e)
            raise RiftManoAdapterError('Unable to instantiate NS %s' % ns_instance_id)

        return 'ns_instantiate', ns_instance_id

    @log_entry_exit(LOG)
    def ns_query(self, filter, attribute_selector=None):
        ns_instance_id = filter['ns_instance_id']
        ns_info = NsInfo()
        ns_info.ns_instance_id = str(ns_instance_id)

        resource = '/api/operational/project/ns-instance-opdata/nsr/%s' % ns_instance_id
        try:
            response = self.session.get(url=self.url + resource)
            assert response.status_code == 200
            json_content = response.json()
        except Exception as e:
            LOG.exception(e)
            raise RiftManoAdapterError('Unable to get opdata for NS %s' % ns_instance_id)

        ns_opdata = json_content['rw-project:project']['nsr:ns-instance-opdata']['nsr'][0]

        ns_info.ns_name = str(ns_opdata['name-ref'])
        ns_info.description = '' # TODO: get from /api/config
        ns_info.nsd_id = str(ns_opdata['nsd-ref'])

        if ns_opdata['operational-status'] == 'running':
            ns_info.ns_state = constants.NS_INSTANTIATED
        else:
            ns_info.ns_state = constants.NS_NOT_INSTANTIATED

        return ns_info

    @log_entry_exit(LOG)
    def ns_terminate(self, ns_instance_id, terminate_time=None, additional_param=None):
        resource = '/api/config/project/Spirent/ns-instance-config/nsr/%s' % ns_instance_id

        try:
            response = self.session.delete(url=self.url + resource)
            assert response.status_code == 201
        except Exception as e:
            LOG.exception(e)
            raise RiftManoAdapterError('Unable to terminate NS %s' % ns_instance_id)

        return 'ns_terminate', ns_instance_id

    @log_entry_exit(LOG)
    def ns_delete_id(self, ns_instance_id):
        self.nsr_metadata.pop(ns_instance_id)

    @log_entry_exit(LOG)
    def wait_for_ns_stable_state(self, ns_instance_id, max_wait_time, poll_interval):
        stable_states = ['running', 'failed']
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            resource = '/api/operational/project/ns-instance-opdata/nsr/%s' % ns_instance_id
            try:
                response = self.session.get(url=self.url + resource)
                assert response.status_code == 200
                json_content = response.json()
            except Exception as e:
                LOG.exception(e)
                raise RiftManoAdapterError('Unable to get opdata for NS %s' % ns_instance_id)

            ns_op_status = json_content['rw-project:project']['nsr:ns-instance-opdata']['nsr'][0]['operational-status']
            LOG.debug('Got NS status %s for NS with ID %s' % (ns_op_status, ns_instance_id))
            if ns_op_status in stable_states:
                return True
            else:
                LOG.debug('Expected NS status to be one of %s, got %s' % (stable_states, ns_op_status))
                LOG.debug('Sleeping %s seconds' % poll_interval)
                time.sleep(poll_interval)
                elapsed_time += poll_interval
                LOG.debug('Elapsed time %s seconds out of %s' % (elapsed_time, max_wait_time))

        LOG.debug('NS with ID %s did not reach a stable state after %s' % (ns_instance_id, max_wait_time))
        return False
