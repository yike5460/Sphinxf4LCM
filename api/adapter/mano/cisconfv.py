import logging
import uuid

import ncclient
from lxml import etree
from ncclient import manager, NCClientError

from api.adapter.mano import ManoAdapterError
from api.generic import constants
from api.structures.objects import InstantiatedVnfInfo, VnfExtCpInfo, VnfInfo, VnfcResourceInfo, ResourceHandle
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

VNFR_DELETE_TEMPLATE = '''
<config>
    <nfvo xmlns="http://tail-f.com/pkg/nfvo">
        <vnfr>
            <esc xmlns="http://tail-f.com/pkg/tailf-nfvo-esc">
                <vnf-deployment operation="delete">
                    <tenant>%(tenant)s</admin>
                    <deployment-name>%(deployment_name)s</deployment-name>
                    <esc>%(esc)s</esc>
                </vnf-deployment>
            </esc>
        </vnfr>
    </nfvo>
</config>
'''

VNF_OPERATE_TEMPLATE = '''
<serviceAction xmlns="http://www.cisco.com/esc/esc">
    <actionType>%(action)s</actionType>
    <tenantName>%(tenant)s</tenantName>
    <depName>%(deployment_name)s</depName>
    <serviceName>-</serviceName>
    <serviceVersion>-</serviceVersion>
</serviceAction>
'''

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
        self.lifecycle_operation_occurrence_ids = dict()

    @log_entry_exit(LOG)
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        """
        This function does not have a direct mapping in OpenStack Tacker client so it will just return the status of the
        VNF with given ID.

        :param lifecycle_operation_occurrence_id:   UUID used to retrieve the operation details from the class
                                                     attribute self.lifecycle_operation_occurrence_ids
        """
        LOG.debug('"Lifecycle Operation Occurrence Id" is not implemented in Cisco NFV MANO!')
        LOG.debug('Will return the state of the VNF with the given ID')

        if lifecycle_operation_occurrence_id is None:
            raise CiscoNFVManoAdapterError('Lifecycle Operation Occurrence ID is absent')
        else:
            operation_details = self.lifecycle_operation_occurrence_ids[lifecycle_operation_occurrence_id]
            operation_type = operation_details['operation_type']
            tenant_name = operation_details['tenant_name']
            deployment_name = operation_details['deployment_name']

        if operation_type == 'vnf_instantiate':
            # Get the NSO VNF deployment state for the 'self' component
            try:
                xml = self.nso.get(('xpath',
                                    '/nfvo/vnfr/esc/vnf-deployment[deployment-name="%s"]/plan/component[name="self"]/'
                                                           'state[name="ncs:ready"]/status' % deployment_name)).data_xml
                xml = etree.fromstring(xml)
                nso_deployment_state = xml.find(
                     './/{http://tail-f.com/pkg/tailf-nfvo-esc}state/{http://tail-f.com/pkg/tailf-nfvo-esc}status').text
                LOG.debug('VNF deployment state reported by NSO: %s' % nso_deployment_state)
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the NSO Netconf server')
                raise CiscoNFVManoAdapterError(e.message)
            except AttributeError as e:
                LOG.debug('VNF deployment state not yet available in NSO')
                raise CiscoNFVManoAdapterError(e.message)

            # Return the operation status depending on the VNF deployment state reported by NSO
            if nso_deployment_state == 'failed':
                return constants.OPERATION_FAILED
            elif nso_deployment_state == 'not-reached':
                return constants.OPERATION_PENDING

            # Get the ESC deployment state
            try:
                xml = self.esc.get(('xpath',
                                    '/esc_datamodel/opdata/tenants/tenant[name="%s"]/deployments[deployment_name="%s"]/'
                                                       'state_machine/state' % (tenant_name, deployment_name))).data_xml
                xml = etree.fromstring(xml)
                esc_deployment_state = xml.find(
                              './/{http://www.cisco.com/esc/esc}state_machine/{http://www.cisco.com/esc/esc}state').text
                LOG.debug('VNF deployment state reported by ESC: %s' % esc_deployment_state)
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the ESC Netconf server')
                raise CiscoNFVManoAdapterError(e.message)
            except AttributeError as e:
                LOG.debug('VNF deployment state not yet available in ESC')
                raise CiscoNFVManoAdapterError(e.message)

            # Return the operation status depending on the VNF deployment state reported by ESC
            if nso_deployment_state == 'reached' and esc_deployment_state == 'SERVICE_ACTIVE_STATE':
                return constants.OPERATION_SUCCESS
            return constants.OPERATION_FAILED

        raise CiscoNFVManoAdapterError('Cannot get operation status for operation type %s' % operation_type)

    @log_entry_exit(LOG)
    def vnf_query(self, filter, attribute_selector=None):
        vnf_instance_id = filter['vnf_instance_id']
        vnf_info = VnfInfo()
        vnf_info.vnf_instance_id = vnf_instance_id.encode()

        # Try to retrieve the instantiation state for the VNF with the given deployment name. If an AttributeError
        # exception is raised, report the VNF instantiation state as NOT_INSTANTIATED.
        try:
            xml = self.nso.get(('xpath',
                                '/nfvo/vnfr/esc/vnf-deployment[deployment-name="%s"]/plan/component[name="self"]/'
                                'state[name="ncs:ready"]/status' % vnf_instance_id)).data_xml
            xml = etree.fromstring(xml)
            instantiation_state = xml.find(
                     './/{http://tail-f.com/pkg/tailf-nfvo-esc}state/{http://tail-f.com/pkg/tailf-nfvo-esc}status').text
        except AttributeError:
            vnf_info.instantiation_state = constants.VNF_NOT_INSTANTIATED
            return vnf_info
        except Exception as e:
            raise CiscoNFVManoAdapterError(e.message)

        # Get the VNF state from the ESC
        xml = self.esc.get(('xpath',
                            '/esc_datamodel/opdata/tenants/tenant[name="admin"]/deployments[deployment_name="%s"]/'
                                                                      'state_machine/state' % vnf_instance_id)).data_xml
        xml = etree.fromstring(xml)
        vnf_state = xml.find('.//{http://www.cisco.com/esc/esc}state_machine/{http://www.cisco.com/esc/esc}state').text

        # Build the vnf_info data structure
        vnf_info.vnf_instance_name = vnf_instance_id
        # vnf_info.vnf_instance_description =
        # vnf_info.vnfd_id =
        vnf_info.instantiation_state = instantiation_state

        # Build the InstantiatedVnfInfo information element only if the VNF instantiation state is INSTANTIATED
        if vnf_info.instantiation_state == constants.VNF_INSTANTIATED:
            vnf_info.instantiated_vnf_info = InstantiatedVnfInfo()
            vnf_info.instantiated_vnf_info.vnf_state = constants.VNF_STATE['ESC_SERVICE_STATE'][vnf_state]

            vnf_info.instantiated_vnf_info.vnfc_resource_info = list()

            # Build the VnfcResourceInfo data structure
            # vnfc_resource_info = VnfcResourceInfo()
            # vnfc_resource_info.vnfc_instance_id =
            # vnfc_resource_info.vdu_id =
            #
            # vnfc_resource_info.compute_resource = ResourceHandle()
            # vnfc_resource_info.compute_resource.vim_id =
            # vnfc_resource_info.compute_resource.resource_id =
            #
            # vnf_info.instantiated_vnf_info.vnfc_resource_info.append(vnfc_resource_info)

            # Build the VnfExtCpInfo data structure
            # vnf_info.instantiated_vnf_info.ext_cp_info = list()
            # for vnfc_resource_info in vnf_info.instantiated_vnf_info.vnfc_resource_info:
            #
            #     vnf_resource_id = vnfc_resource_info.compute_resource.resource_id
            #             vnf_ext_cp_info = VnfExtCpInfo()
            #             vnf_ext_cp_info.cp_instance_id =
            #             vnf_ext_cp_info.address =
            #             vnf_ext_cp_info.cpd_id =
            #
            #             vnf_info.instantiated_vnf_info.ext_cp_info.append(vnf_ext_cp_info)

        # VNF instantiation state is not INSTANTIATED
        else:
            print("")
        return vnf_info

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
    def build_vnfr_delete(self, vnf_instance_id, additional_param):
        vnfr_delete_template_values = {
            'tenant': additional_param['tenant'],
            'deployment_name': vnf_instance_id,
            'esc': additional_param['esc']
        }

        vnfr_delete_xml = VNFR_DELETE_TEMPLATE % vnfr_delete_template_values
        return vnfr_delete_xml

    @log_entry_exit(LOG)
    def build_vnf_operate(self, vnf_instance_id, action, additional_param):
        vnf_operate_template_values = {
            'action': action,
            'tenant': additional_param['tenant'],
            'deployment_name': vnf_instance_id
        }

        vnf_operate_xml = VNF_OPERATE_TEMPLATE % vnf_operate_template_values
        return vnf_operate_xml

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

        lifecycle_operation_occurrence_id = uuid.uuid4()
        lifecycle_operation_occurrence_dict = {
            'operation_type': 'vnf_instantiate',
            'tenant_name': additional_param['tenant'],
            'deployment_name': vnf_instance_id
        }
        self.lifecycle_operation_occurrence_ids[lifecycle_operation_occurrence_id] = lifecycle_operation_occurrence_dict

        return lifecycle_operation_occurrence_id

    @log_entry_exit(LOG)
    def vnf_terminate(self, vnf_instance_id, termination_type, graceful_termination_type=None, additional_param=None):
        vnfr_delete_xml = self.build_vnfr_delete(vnf_instance_id, additional_param)
        print vnfr_delete_xml

        try:
            netconf_reply = self.nso.edit_config(target='running', config=vnfr_delete_xml)
        except NCClientError as e:
            raise CiscoNFVManoAdapterError(e.message)

        if '<ok/>' not in netconf_reply.xml:
            raise CiscoNFVManoAdapterError('NSO replied with an error')

        print netconf_reply.xml

        lifecycle_operation_occurrence_id = uuid.uuid4()
        lifecycle_operation_occurrence_dict = {
            'operation_type': 'vnf_terminate',
            'tenant_name': additional_param['tenant'],
            'deployment_name': vnf_instance_id
        }
        self.lifecycle_operation_occurrence_ids[lifecycle_operation_occurrence_id] = lifecycle_operation_occurrence_dict

        return lifecycle_operation_occurrence_id

    @log_entry_exit(LOG)
    def vnf_delete_id(self, vnf_instance_id):
        self.vnf_vnfd_mapping.pop(vnf_instance_id)

    @log_entry_exit(LOG)
    def vnf_operate(self, vnf_instance_id, change_state_to, stop_type=None, graceful_stop_timeout=None,
                    additional_param=None):
        etsi_state_esc_action_mapping = {
            'start': 'START',
            'stop': 'STOP'
        }

        vnf_operate_xml = self.build_vnf_operate(vnf_instance_id, etsi_state_esc_action_mapping[change_state_to],
                                                 additional_param)
        print vnf_operate_xml

        try:
            netconf_reply = self.esc.dispatch(rpc_command=etree.fromstring(vnf_operate_xml))
        except NCClientError as e:
            raise CiscoNFVManoAdapterError(e.message)

        if '<ok/>' not in netconf_reply.xml:
            raise CiscoNFVManoAdapterError('ESC replied with an error')

        print netconf_reply.xml

        lifecycle_operation_occurrence_id = uuid.uuid4()
        lifecycle_operation_occurrence_dict = {
            'operation_type': 'vnf_%s' % change_state_to,
            'tenant_name': additional_param['tenant'],
            'deployment_name': vnf_instance_id
        }
        self.lifecycle_operation_occurrence_ids[lifecycle_operation_occurrence_id] = lifecycle_operation_occurrence_dict

        return lifecycle_operation_occurrence_id