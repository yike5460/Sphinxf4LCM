import json
import logging
import requests
import uuid

from requests.auth import HTTPBasicAuth

from utils.logging_module import log_entry_exit

LOG = logging.getLogger(__name__)


class RiftManoAdapter(object):
    def __init__(self, url, username, password, vim_account):
        self.url = url
        self.username = username
        self.password = password
        self.vim_account = vim_account
        self.ns_vnf_mapping = dict()

    @log_entry_exit(LOG)
    def vnf_instantiate(self, vnfd_id):
        resource = '/api/config/ns-instance-config/nsr'

        LOG.debug('RIFT.ware does not support directly instantiating VNFs.')
        LOG.debug('Building a wrapper NS and instantiating it instead.')

        request_body = dict()
        request_body['nsr'] = list()

        nsr = dict()

        nsr_id = str(uuid.uuid4())
        nsr['id'] = nsr_id
        nsr['name'] = 'nsr_' + nsr_id
        nsr['admin-status'] = 'ENABLED'
        nsr['cloud-account'] = self.vim_account
        nsr['nsd'] = dict()

        nsd_id = str(uuid.uuid4())
        nsr['nsd']['id'] = nsd_id
        nsr['nsd']['name'] = 'nsd_' + nsd_id
        nsr['nsd']['constituent-vnfd'] = list()

        vnfd = dict()
        vnfd['member-vnf-index'] = 1
        vnfd['start-by-default'] = "true"
        vnfd['vnfd-id-ref'] = vnfd_id

        nsr['nsd']['constituent-vnfd'].append(vnfd)

        request_body['nsr'].append(nsr)

        LOG.debug('Attempting to instantiate NS with NSD:\n%s' % json.dumps(request_body, indent=2))

        try:
            response = requests.post(url=self.url + resource, json=request_body,
                                     auth=HTTPBasicAuth(username=self.username, password=self.password), verify=False)
            assert response.status_code == 201

        except Exception as e:
            LOG.error('Unable to instantiate NS')
            raise e

        return True

    @log_entry_exit(LOG)
    def ns_list(self):
        resource = '/api/operational/ns-instance-opdata/nsr'
        headers = dict()
        headers['Accept'] = 'application/vnd.yang.data+json'

        ns_list = list()

        try:
            response = requests.get(url=self.url + resource, headers=headers,
                                    auth=HTTPBasicAuth(username=self.username, password=self.password), verify=False)

            for nsr in json.loads(response.text)['nsr:nsr']:
                ns_list.append(nsr['ns-instance-config-ref'])

        except Exception as e:
            LOG.error('Unable to list NSs')
            raise e

        return ns_list

    @log_entry_exit(LOG)
    def ns_terminate(self, ns_id):
        resource = '/api/config/ns-instance-config/nsr/' + ns_id

        try:
            LOG.debug('Terminating NS with id: %s' % ns_id)
            response = requests.delete(url=self.url + resource,
                                       auth=HTTPBasicAuth(username=self.username, password=self.password), verify=False)
            assert response.status_code == 201
        except Exception as e:
            LOG.error('Unable to delete NS')
            raise e
