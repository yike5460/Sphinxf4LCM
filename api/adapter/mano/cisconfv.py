import logging
import uuid

import ncclient
from ncclient import manager, NCClientError

from api.adapter.mano import ManoAdapterError
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)

VNFR_TEMPLATE = '''
<config>
    <nfvo xmlns="http://tail-f.com/pkg/nfvo">
        <vnfr>
            <esc xmlns="http://tail-f.com/pkg/tailf-nfvo-esc">
                <vnf-deployment>
                    <tenant>%(tenant)s</tenant>
                    <deployment-name>%(deployment_name)s</deployment-name>
                    <esc>%(esc)s</esc>
                    <username>%(username)s</username>
                    <vnfr>
                        <id>%(vnfd_id)s</id>
                        <vnfd-flavor>%(vnfd_flavor)s</vnfd-flavor>
                        <instantiation-level>%(instantiation_level)s</instantiation-level>
                        %(vdu_list)s
                        %(vnfd_cp_list)s
                    </vnfr>
                </vnf-deployment>
            </esc>
        </vnfr>
    </nfvo>
</config>'''

VDU_TEMPLATE = '''
                        <vdu>
                            <id>%(vdu_id)s</id>
                            <image-name>%(image_name)s</image-name>
                            <flavor-name>%(flavor_name)s</flavor-name>
                            <day0>
                                <destination>%(day0_dest)s</destination>
                                <url>%(day0_url)s</url>
                            </day0>
                            %(vdu_cp_list)s
                        </vdu>'''

VDU_CP_TEMPLATE = '''
                        <connection-point-address>
                            <id>%(cp_id)s</id>
                            <start>%(start_addr)s</start>
                            <end>%(end_addr)s</end>
                        </connection-point-address>'''

VNFD_CP_TEMPLATE = '''
                        <vnfd-connection-point>
                            <id>%(cp_id)s</id>
                            <vlr>%(vlr)s</vlr>
                        </vnfd-connection-point>'''

class CiscoNFVManoAdapterError(ManoAdapterError):
    """
    A problem occurred in the VNF LifeCycle Validation Cisco NFV MANO adapter API.
    """
    pass


class CiscoNFVManoAdapter(object):
    """
    Class of functions that map the generic operations exposed by the MANO to the operations exposed by the
    Cisco NFV MANO solution.
    """

    def __init__(self, nso_hostname, nso_username, nso_password, esc_hostname, esc_username, esc_password,
                 nso_port=2022, esc_port=830):
        try:
            self.nso = ncclient.manager.connect(host=nso_hostname, port=nso_port, username=nso_username,
                                                password=nso_password,
                                                hostkey_verify=False, look_for_keys=False)
            self.esc = ncclient.manager.connect(host=esc_hostname, port=esc_port, username=esc_username,
                                                password=esc_password,
                                                hostkey_verify=False, look_for_keys=False)
        except Exception as e:
            LOG.error('Unable to create %s instance' % self.__class__.__name__)
            raise CiscoNFVManoAdapterError(e.message)

        self.vnf_vnfd_mapping = dict()
        self.lifecycle_operation_occurence_ids = dict()

    @log_entry_exit(LOG)
    def get_vnfd(self, vnfd_id):
        netconf_reply = self.nso.get(('xpath', '/nfvo/vnfd[id="%s"]' % vnfd_id))
        vnfd_xml = netconf_reply.data_xml
        return vnfd_xml

    @log_entry_exit(LOG)
    def build_vdu_list(self, vdu_params):
        vdu_list_xml = ''
        for vdu_id, vdu_param in vdu_params.items():
            vdu_template_values = {
                'vdu_id': vdu_id,
                'image_name': vdu_param['image'],
                'flavor_name': vdu_param['flavor'],
                'day0_dest': vdu_param['day0']['destination'],
                'day0_url': vdu_param['day0']['url'],
                'vdu_cp_list': self.build_vdu_cp_list(vdu_param['cp'])
            }

            vdu_xml = VDU_TEMPLATE % vdu_template_values
            vdu_list_xml += vdu_xml

        return vdu_list_xml

    @log_entry_exit(LOG)
    def build_vdu_cp_list(self, vdu_cp_params):
        vdu_cp_list_xml = ''
        for vdu_cp_id, vdu_cp_addr in vdu_cp_params.items():
            vdu_cp_template_values = {
                'cp_id': vdu_cp_id,
                'start_addr': vdu_cp_addr['start'],
                'end_addr': vdu_cp_addr['end']
            }

            vdu_cp_xml = VDU_CP_TEMPLATE % vdu_cp_template_values
            vdu_cp_list_xml += vdu_cp_xml

        return vdu_cp_list_xml

    @log_entry_exit(LOG)
    def build_vnfd_cp_list(self, ext_cp_vlr):
        vnfd_cp_list_xml = ''
        for cp_id, vlr_name in ext_cp_vlr.items():
            vnfd_cp_template_values = {
                'cp_id': cp_id,
                'vlr': vlr_name
            }

            vnfd_cp_xml = VNFD_CP_TEMPLATE % vnfd_cp_template_values
            vnfd_cp_list_xml += vnfd_cp_xml

        return vnfd_cp_list_xml

    @log_entry_exit(LOG)
    def build_vnfr(self, vnf_instance_id, flavour_id, instantiation_level_id, additional_param):
        vnfd_id = self.vnf_vnfd_mapping[vnf_instance_id]

        vnfr_template_values = {
            'tenant': additional_param['tenant'],
            'deployment_name': vnf_instance_id,
            'esc': additional_param['esc'],
            'username': additional_param['username'],
            'vnfd_id': vnfd_id,
            'vnfd_flavor': flavour_id,
            'instantiation_level': instantiation_level_id,
            'vdu_list': self.build_vdu_list(additional_param['vdu']),
            'vnfd_cp_list': self.build_vnfd_cp_list(additional_param['ext_cp_vlr'])
        }

        vnfr_xml = VNFR_TEMPLATE % vnfr_template_values
        return vnfr_xml

    @log_entry_exit(LOG)
    def vnf_create_id(self, vnfd_id, vnf_instance_name=None, vnf_instance_description=None):
        vnf_instance_id = vnf_instance_name
        self.vnf_vnfd_mapping[vnf_instance_id] = vnfd_id

        return vnf_instance_id

    @log_entry_exit(LOG)
    def vnf_instantiate(self, vnf_instance_id, flavour_id, instantiation_level_id=None, ext_virtual_link=None,
                        ext_managed_virtual_link=None, localization_language=None, additional_param=None):

        vnfr_xml = self.build_vnfr(vnf_instance_id, flavour_id, instantiation_level_id, additional_param)
        print vnfr_xml
        try:
            netconf_reply = self.nso.edit_config(target='running', config=vnfr_xml)
        except NCClientError as e:
            raise CiscoNFVManoAdapterError(e.message)

        if '<ok/>' not in netconf_reply.xml:
            raise CiscoNFVManoAdapterError('NSO replied with an error')

        print netconf_reply.xml

        lifecycle_operation_occurence_id = uuid.uuid4()
        lifecycle_operation_occurence_dict = {
            'operation_type': 'vnf_instantiate',
            'tenant_name': additional_param['tenant'],
            'deployment_name': vnf_instance_id
        }
        self.lifecycle_operation_occurence_ids[lifecycle_operation_occurence_id] = lifecycle_operation_occurence_dict

        return lifecycle_operation_occurence_id
