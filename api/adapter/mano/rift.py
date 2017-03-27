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

    @log_entry_exit(LOG)
    def vnf_instantiate(self, vnfd_id):
        resource = '/api/config/ns-instance-config/nsr'

        LOG.debug('RIFT.ware does not support directly instantiating VNFs.')
        LOG.debug('Building a wrapper NS and instantiating it instead')

        request_body = dict()
        request_body['nsr'] = list()

        nsr = dict()
        nsr['id'] = str(uuid.uuid4())
        nsr['name'] = str(uuid.uuid4())
        nsr['admin-status'] = 'ENABLED'
        nsr['cloud-account'] = self.vim_account
        nsr['nsd'] = dict()

        nsr['nsd']['id'] = str(uuid.uuid4())
        nsr['nsd']['name'] = str(uuid.uuid4())
        nsr['nsd']['constituent-vnfd'] = list()

        vnfd = dict()
        vnfd['member-vnf-index'] = 1
        vnfd['start-by-default'] = "true"
        vnfd['vnfd-id-ref'] = vnfd_id

        nsr['nsd']['constituent-vnfd'].append(vnfd)

        request_body['nsr'].append(nsr)

        print json.dumps(request_body, indent=2)

        response = requests.post(url=self.url + resource, json=request_body,
                                 auth=HTTPBasicAuth(username=self.username, password=self.password), verify=False)
        print response.__dict__
