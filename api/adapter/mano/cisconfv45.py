import logging
import uuid
from collections import defaultdict
from lxml import etree

import ncclient
from ncclient import manager, NCClientError

from api.adapter import construct_adapter
from api.adapter.mano import ManoAdapterError
from api.generic import constants
from api.structures.objects import InstantiatedVnfInfo, VnfExtCpInfo, VnfInfo, VnfcResourceInfo, ResourceHandle, NsInfo
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)

VNFR_TEMPLATE = '''
<config>
    <nfvo xmlns="http://tail-f.com/pkg/tailf-etsi-rel2-nfvo">
        <vnf-info>
            <esc xmlns="http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc">
                <vnf-deployment>
                    <tenant>%(tenant)s</tenant>
                    <deployment-name>%(deployment_name)s</deployment-name>
                    <esc>%(esc)s</esc>
                    <username>%(username)s</username>
                    <vnf-info>
                        <name>%(vnf_name)s</name>
                        <vnfd>%(vnfd_id)s</vnfd>
                        <vnfd-flavor>%(vnfd_flavor)s</vnfd-flavor>
                        <instantiation-level>%(instantiation_level)s</instantiation-level>
                        %(vdu_list)s
                        %(vnfd_cp_list)s
                        %(vl_list)s
                    </vnf-info>
                </vnf-deployment>
            </esc>
        </vnf-info>
    </nfvo>
</config>'''

VDU_TEMPLATE = '''
                        <vdu>
                            <id>%(vdu_id)s</id>
                            <bootup-time>%(bootup_time)s</bootup-time>
                            <recovery-wait-time>%(recovery_wait_time)s</recovery-wait-time>
                            <image-name>%(image_name)s</image-name>
                            <flavor-name>%(flavor_name)s</flavor-name>
                            %(day0_config)s
                            %(vdu_cp_list)s
                        </vdu>'''

DAY0_TEMPLATE = '''
                            <day0>
                                <destination>%(day0_dest)s</destination>
                                <url>%(day0_url)s</url>
                            </day0>'''

VDU_CP_TEMPLATE = '''
                        <connection-point-address>
                            <id>%(cp_id)s</id>
                            <start>%(start_addr)s</start>
                            <end>%(end_addr)s</end>
                        </connection-point-address>'''

VNFD_CP_TEMPLATE = '''
                        <vnfd-connection-point>
                            <id>%(cp_id)s</id>
                            <network-name>%(vlr)s</network-name>
                        </vnfd-connection-point>'''

VL_TEMPLATE = '''
                        <virtual-link>
                            <id>%(vl_id)s</id>
                            %(vl_details)s
                        </virtual-link>'''

VL_DETAILS_TEMPLATE = '''
                            %(dhcp)s
                            <subnet>
                                <network>%(network)s</network>
                                <gateway>%(gateway)s</gateway>
                            </subnet>'''

VNFR_DELETE_TEMPLATE = '''
<config>
    <nfvo xmlns="http://tail-f.com/pkg/tailf-etsi-rel2-nfvo">
        <vnf-info>
            <esc xmlns="http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc">
                <vnf-deployment xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" nc:operation="delete">
                    <tenant>%(tenant)s</tenant>
                    <deployment-name>%(deployment_name)s</deployment-name>
                    <esc>%(esc)s</esc>
                </vnf-deployment>
            </esc>
        </vnf-info>
    </nfvo>
</config>'''

VNF_OPERATE_TEMPLATE = '''
<serviceAction xmlns="http://www.cisco.com/esc/esc">
    <actionType>%(action)s</actionType>
    <tenantName>%(tenant)s</tenantName>
    <depName>%(deployment_name)s</depName>
    <serviceName>-</serviceName>
    <serviceVersion>-</serviceVersion>
</serviceAction>'''

VM_OPERATE_TEMPLATE = '''
<vmAction xmlns="http://www.cisco.com/esc/esc">
    <actionType>%(action)s</actionType>
    <vmName>%(vm_name)s</vmName>
</vmAction>'''

SCALING_TEMPLATE = '''
<config>
    <devices xmlns="http://tail-f.com/ns/ncs">
        <device>
            <name>%(esc_name)s</name>
            <config>
                <esc_datamodel xmlns="http://www.cisco.com/esc/esc">
                    <tenants>
                        <tenant>
                            <name>%(tenant_name)s</name>
                            <deployments>
                                <deployment>
                                    <name>%(deployment_name)s</name>
                                    %(vm_group_list)s
                                </deployment>
                            </deployments>
                        </tenant>
                    </tenants>
                </esc_datamodel>
            </config>
        </device>
    </devices>
</config>'''

SCALING_VM_GROUP_TEMPLATE = '''
                                    <vm_group>
                                    <name>%(vm_group_name)s</name>
                                    <scaling>
                                        <min_active>%(min_active)s</min_active>
                                        <max_active>%(max_active)s</max_active>
                                    </scaling>
                                    </vm_group>'''

NSR_TEMPLATE = '''
<config>
    <nfvo xmlns="http://tail-f.com/pkg/tailf-etsi-rel2-nfvo">
        <ns-info>
            <esc xmlns="http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc">
                <ns-info>
                    <id>%(ns_id)s</id>
                    <username>%(username)s</username>
                    <nsd>%(nsd_id)s</nsd>
                    <flavor>%(flavor)s</flavor>
                    <instantiation-level>%(instantiation_level)s</instantiation-level>
                    %(vnf_info_list)s
                    %(vl_list)s
                    %(sap_info_list)s
                    <state>%(state)s</state>
                </ns-info>
            </esc>
        </ns-info>
    </nfvo>
</config>'''

NS_VNF_INFO_TEMPLATE = '''
        <vnf-info>
            <name>%(vnf_name)s</name>
            <vnfd>%(vnfd_id)s</vnfd>
            %(vdu_list)s
            %(vl_list)s
            <tenant>%(tenant)s</tenant>
            <deployment-name>%(deployment_name)s</deployment-name>
            <esc>%(esc)s</esc>
        </vnf-info>'''

VL_INFO_TEMPLATE = '''
        <virtual-link-info>
            <virtual-link-descriptor>%(vl_descriptor_id)s</virtual-link-descriptor>
            %(vl_details)s
        </virtual-link-info>'''

SAP_INFO_TEMPLATE = '''
        <sap-info>
            <sapd>%(sapd)s</sapd>
            <network-name>%(network_name)s</network-name>
        </sap-info>'''

NSR_DELETE_TEMPLATE = '''
<config>
    <nfvo xmlns="http://tail-f.com/pkg/tailf-etsi-rel2-nfvo">
        <ns-info>
            <esc xmlns="http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc">
                <ns-info xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" nc:operation="delete">
                    <id>%(ns_info_id)s</id>
                </ns-info>
            </esc>
        </ns-info>
    </nfvo>
</config>'''


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

            self.vim_helper = None

        except Exception as e:
            LOG.error('Unable to create %s instance' % self.__class__.__name__)
            LOG.exception(e)
            raise CiscoNFVManoAdapterError(e.message)

        self.vnf_vnfd_mapping = dict()
        self.ns_nsd_mapping = dict()
        self.lifecycle_operation_occurrence_ids = dict()
        self.vnf_instance_id_metadata = dict()

    @log_entry_exit(LOG)
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        """
        This function does not have a direct mapping in OpenStack Tacker client so it will just return the status of the
        VNF with given ID.

        :param lifecycle_operation_occurrence_id:   UUID used to retrieve the operation details from the class attribute
                                                    self.lifecycle_operation_occurrence_ids
        """
        LOG.debug('"Lifecycle Operation Occurrence Id" is not implemented in Cisco NFV MANO!')
        LOG.debug('Will return the state of the VNF/NS with the given ID')

        if lifecycle_operation_occurrence_id is None:
            raise CiscoNFVManoAdapterError('Lifecycle Operation Occurrence ID is absent')
        else:
            operation_details = self.lifecycle_operation_occurrence_ids[lifecycle_operation_occurrence_id]
            operation_type = operation_details['operation_type']

        if operation_type == 'vnf_instantiate':
            tenant_name = operation_details['tenant_name']
            deployment_name = operation_details['deployment_name']

            # Get the NSO VNF deployment state for the 'self' component
            try:
                xml = self.nso.get(('xpath',
                                    '/nfvo/vnf-info/esc/vnf-deployment[deployment-name="%s"]/plan/'
                                        'component[name="self"]/state[name="ncs:ready"]/status'
                                        % deployment_name)).data_xml
                xml = etree.fromstring(xml)
                nso_vnf_deployment_state = xml.find(
                    './/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}state/'
                    '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}status').text
                LOG.debug('VNF deployment state reported by NSO: "%s"; expected: "%s"'
                          % (nso_vnf_deployment_state, 'reached'))
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the NSO Netconf server')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)
            except AttributeError as e:
                LOG.debug('VNF deployment state not available in NSO')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)

            # Return the operation status depending on the VNF deployment state reported by NSO
            if nso_vnf_deployment_state == 'failed':
                return constants.OPERATION_FAILED
            elif nso_vnf_deployment_state == 'not-reached':
                return constants.OPERATION_PENDING

            # Get the ESC deployment state
            try:
                xml = self.esc.get(('xpath',
                                    '/esc_datamodel/opdata/tenants/tenant[name="%s"]/deployments[deployment_name="%s"]/'
                                        'state_machine/state' % (tenant_name, deployment_name))).data_xml
                xml = etree.fromstring(xml)
                esc_vnf_deployment_state = xml.find(
                    './/{http://www.cisco.com/esc/esc}state_machine/{http://www.cisco.com/esc/esc}state').text
                LOG.debug('VNF deployment state reported by ESC: "%s"; expected: "%s"'
                          % (esc_vnf_deployment_state, 'SERVICE_ACTIVE_STATE'))
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the ESC Netconf server')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)
            except AttributeError as e:
                LOG.debug('VNF deployment state not available in ESC')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)

            # Return the operation status depending on the VNF deployment state reported by ESC
            if nso_vnf_deployment_state == 'reached' and esc_vnf_deployment_state == 'SERVICE_ACTIVE_STATE':
                return constants.OPERATION_SUCCESS
            return constants.OPERATION_FAILED

        if operation_type == 'vnf_terminate':
            tenant_name = operation_details['tenant_name']
            deployment_name = operation_details['deployment_name']

            # To check that the VNF was un-deployed, try to retrieve the VNF deployment name until the AttributeError
            # exception is raised. Do this first on the ESC. When the ESC reports that the VNF was un-deployed, check on
            # the NSO.

            # Try to retrieve the VNF deployment name from the ESC.
            try:
                xml = self.esc.get(('xpath',
                                    '/esc_datamodel/opdata/tenants/tenant[name="%s"]/deployments[deployment_name="%s"]/'
                                        'state_machine/state' % (tenant_name, deployment_name))).data_xml
                xml = etree.fromstring(xml)
                esc_vnf_deployment_state = xml.find(
                    './/{http://www.cisco.com/esc/esc}state_machine/{http://www.cisco.com/esc/esc}state').text
                LOG.debug('VNF deployment state reported by ESC: "%s"; expected no state' % esc_vnf_deployment_state)
                if esc_vnf_deployment_state == 'SERVICE_ERROR_STATE':
                    return constants.OPERATION_FAILED
                else:
                    return constants.OPERATION_PENDING
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the ESC Netconf server')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)
            except AttributeError:
                LOG.debug('So far the ESC reports the VNF as un-deployed. Check the NSO reports the same')

            try:
                xml = self.nso.get(('xpath',
                                    '/nfvo/vnf-info/esc/vnf-deployment[deployment-name="%s"]/plan/'
                                        'component[name="self"]/state[name="ncs:ready"]/status'
                                        % deployment_name)).data_xml
                xml = etree.fromstring(xml)
                nso_vnf_deployment_state = xml.find(
                    './/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}state/'
                    '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}status').text
                LOG.debug(
                    'VNF deployment state reported by NSO: "%s"; expected no state' % nso_vnf_deployment_state)
                if nso_vnf_deployment_state == 'reached':
                    LOG.debug('ESC reports the VNF as un-deployed, but the NSO does not')
                    return constants.OPERATION_PENDING
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the NSO Netconf server')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)
            except AttributeError:
                return constants.OPERATION_SUCCESS

        if operation_type == 'vnf_stop':
            tenant_name = operation_details['tenant_name']
            deployment_name = operation_details['deployment_name']

            # Try to retrieve the VNF deployment name from the ESC.
            try:
                xml = self.esc.get(('xpath',
                                    '/esc_datamodel/opdata/tenants/tenant[name="%s"]/'
                                        'deployments[deployment_name="%s"]/state_machine/state' %
                                        (tenant_name, deployment_name))).data_xml
                xml = etree.fromstring(xml)
                esc_vnf_deployment_state = xml.find(
                    './/{http://www.cisco.com/esc/esc}state_machine/{http://www.cisco.com/esc/esc}state').text
                LOG.debug('VNF deployment state reported by ESC: "%s"; expected: "%s"'
                          % (esc_vnf_deployment_state, 'SERVICE_STOPPED_STATE'))
                if esc_vnf_deployment_state == 'SERVICE_STOPPED_STATE':
                    return constants.OPERATION_SUCCESS
                elif esc_vnf_deployment_state == 'SERVICE_ERROR_STATE':
                    return constants.OPERATION_FAILED
                else:
                    return constants.OPERATION_PENDING
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the ESC Netconf server')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)
            except AttributeError as e:
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)

        if operation_type == 'vnf_start':
            tenant_name = operation_details['tenant_name']
            deployment_name = operation_details['deployment_name']

            # Try to retrieve the VNF deployment name from the ESC.
            try:
                xml = self.esc.get(('xpath',
                                    '/esc_datamodel/opdata/tenants/tenant[name="%s"]/'
                                        'deployments[deployment_name="%s"]/state_machine/state' %
                                        (tenant_name, deployment_name))).data_xml
                xml = etree.fromstring(xml)
                esc_vnf_deployment_state = xml.find(
                    './/{http://www.cisco.com/esc/esc}state_machine/{http://www.cisco.com/esc/esc}state').text
                LOG.debug('VNF deployment state reported by ESC: "%s"; expected: "%s"'
                          % (esc_vnf_deployment_state, 'SERVICE_ACTIVE_STATE'))
                if esc_vnf_deployment_state == 'SERVICE_ACTIVE_STATE':
                    return constants.OPERATION_SUCCESS
                elif esc_vnf_deployment_state == 'SERVICE_ERROR_STATE':
                    return constants.OPERATION_FAILED
                else:
                    return constants.OPERATION_PENDING
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the ESC Netconf server')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)
            except AttributeError as e:
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)

        if operation_type == 'ns_instantiate':
            tenant_name = operation_details['tenant_name']
            deployment_name = operation_details['deployment_name']

            # Get the NSO NS deployment state for the 'self' component
            try:
                xml = self.nso.get(('xpath',
                                    '/nfvo/ns-info/esc/ns-info[id="%s"]/plan/component[name="self"]/state'
                                        '[name="ncs:ready"]/status' % deployment_name)).data_xml
                xml = etree.fromstring(xml)
                nso_ns_deployment_state = xml.find(
                    './/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}state/'
                    '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}status').text
                LOG.debug('NS deployment state reported by NSO: "%s"; expected: "%s"'
                          % (nso_ns_deployment_state, 'reached'))
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the NSO Netconf server')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)
            except AttributeError as e:
                LOG.debug('NS deployment state not available in NSO')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)

            # Return the operation status depending on the NS deployment state reported by NSO
            if nso_ns_deployment_state == 'failed':
                return constants.OPERATION_FAILED
            elif nso_ns_deployment_state == 'not-reached':
                return constants.OPERATION_PENDING

            # Get the NSO VNF deployment state for the 'self' component
            try:
                xml = self.nso.get(('xpath',
                                    '/nfvo/vnf-info/esc/vnf-deployment[tenant="%s"][deployment-name="%s"]/plan/'
                                        'component[name="self"]/state[name="ncs:ready"]/status'
                                        % (tenant_name, deployment_name))).data_xml
                xml = etree.fromstring(xml)
                nso_deployment_state = xml.find(
                    './/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}state/'
                    '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}status').text
                LOG.debug('Deployment state reported by NSO: "%s"; expected: "%s"'
                          % (nso_ns_deployment_state, 'reached'))
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the NSO Netconf server')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)
            except AttributeError as e:
                LOG.debug('Deployment state not available in NSO')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)

            # Return the operation status depending on the NS deployment state reported by NSO
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
                LOG.debug('Deployment state reported by ESC: "%s"; expected: "%s"'
                          % (esc_deployment_state, 'SERVICE_ACTIVE_STATE'))
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the ESC Netconf server')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)
            except AttributeError as e:
                LOG.debug('Deployment state not available in ESC')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)

            # Return the operation status depending on the VNF deployment state reported by ESC
            if nso_ns_deployment_state == 'reached'\
                    and nso_deployment_state == 'reached'\
                    and esc_deployment_state == 'SERVICE_ACTIVE_STATE':
                return constants.OPERATION_SUCCESS
            return constants.OPERATION_FAILED

        if operation_type == 'ns_terminate':
            tenant_name = operation_details['tenant_name']
            deployment_name = operation_details['deployment_name']

            # To check that the NS was un-deployed, try to retrieve the NS deployment name until the AttributeError
            # exception is raised. Do this first on the ESC. When the ESC reports that the deployment was un-deployed,
            # check that the NSO reports both the deployment state and NS deployment state as un-deployed.

            # Try to retrieve the deployment name from the ESC.
            try:
                xml = self.esc.get(('xpath',
                                    '/esc_datamodel/opdata/tenants/tenant[name="%s"]/deployments[deployment_name="%s"]/'
                                        'state_machine/state' % (tenant_name, deployment_name))).data_xml
                xml = etree.fromstring(xml)
                esc_deployment_state = xml.find(
                    './/{http://www.cisco.com/esc/esc}state_machine/{http://www.cisco.com/esc/esc}state').text
                LOG.debug('Deployment state reported by ESC: "%s"; expected no state' % esc_deployment_state)
                if esc_deployment_state == 'SERVICE_ERROR_STATE':
                    return constants.OPERATION_FAILED
                else:
                    return constants.OPERATION_PENDING
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the ESC Netconf server')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)
            except AttributeError:
                LOG.debug('So far the ESC reports the deployment as un-deployed. Check the NSO reports the same')

            try:
                xml = self.nso.get(('xpath',
                                    '/nfvo/vnf-info/esc/vnf-deployment[tenant="%s"][deployment-name="%s"]/plan/'
                                        'component[name="self"]/state[name="ncs:ready"]/status'
                                        % (tenant_name, deployment_name))).data_xml
                xml = etree.fromstring(xml)
                nso_deployment_state = xml.find(
                    './/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}state/'
                    '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}status').text
                LOG.debug(
                    'Deployment state reported by NSO: "%s"; expected no state' % nso_deployment_state)
                if nso_deployment_state == 'reached':
                    LOG.debug('ESC reports the deployment as un-deployed, but the NSO does not')
                    return constants.OPERATION_PENDING
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the NSO Netconf server')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)
            except AttributeError:
                LOG.debug('Check the NSO reports the NS as un-deployed')

            try:
                xml = self.nso.get(('xpath',
                                    '/nfvo/ns-info/esc/ns-info[id="%s"]/plan/component[name="self"]/state'
                                        '[name="ncs:ready"]/status' % deployment_name)).data_xml
                xml = etree.fromstring(xml)
                nso_ns_deployment_state = xml.find(
                    './/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}state/'
                    '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}status').text
                LOG.debug('NS deployment state reported by NSO: "%s"; expected no state'
                          % nso_ns_deployment_state)
                if nso_ns_deployment_state == 'reached':
                    LOG.debug('NSO reports the deployment as un-deployed, but the NS as deployed')
                    return constants.OPERATION_PENDING
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the NSO Netconf server')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)
            except AttributeError:
                return constants.OPERATION_SUCCESS

        if operation_type == 'vm_start':
            tenant_name = operation_details['tenant_name']
            deployment_name = operation_details['deployment_name']
            vm_name = operation_details['vm_name']

            # Try to retrieve the VM state machines from the ESC.
            try:
                xml = self.esc.get(('xpath',
                                    '/esc_datamodel/opdata/tenants/tenant[name="%s"]/deployments[deployment_name="%s"]/'
                                        'state_machine/vm_state_machines' % (tenant_name, deployment_name))).data_xml
                xml = etree.fromstring(xml)
                esc_vm_state_machine = xml.find('.//{http://www.cisco.com/esc/esc}vm_state_machine'
                                                '[{http://www.cisco.com/esc/esc}vm_name="%s"]/'
                                                '{http://www.cisco.com/esc/esc}state' % vm_name).text
                LOG.debug('State reported by ESC for VM with name %s: "%s"; expected: "%s"'
                          % (vm_name, esc_vm_state_machine, 'VM_ALIVE_STATE'))
                if esc_vm_state_machine == 'VM_ALIVE_STATE':
                    return constants.OPERATION_SUCCESS
                elif esc_vm_state_machine == 'VM_ERROR_STATE':
                    return constants.OPERATION_FAILED
                else:
                    return constants.OPERATION_PENDING
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the ESC Netconf server')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)
            except AttributeError as e:
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)

        if operation_type == 'vm_stop':
            tenant_name = operation_details['tenant_name']
            deployment_name = operation_details['deployment_name']
            vm_name = operation_details['vm_name']

            # Try to retrieve the VM state machines from the ESC.
            try:
                xml = self.esc.get(('xpath',
                                    '/esc_datamodel/opdata/tenants/tenant[name="%s"]/deployments[deployment_name="%s"]/'
                                        'state_machine/vm_state_machines' % (tenant_name, deployment_name))).data_xml
                xml = etree.fromstring(xml)
                esc_vm_state_machine = xml.find('.//{http://www.cisco.com/esc/esc}vm_state_machine'
                                                '[{http://www.cisco.com/esc/esc}vm_name="%s"]/'
                                                '{http://www.cisco.com/esc/esc}state' % vm_name).text
                LOG.debug('State reported by ESC for VM with name %s: "%s"; expected: "%s"'
                          % (vm_name, esc_vm_state_machine, 'VM_SHUTOFF_STATE'))
                if esc_vm_state_machine == 'VM_SHUTOFF_STATE':
                    return constants.OPERATION_SUCCESS
                elif esc_vm_state_machine == 'VM_ERROR_STATE':
                    return constants.OPERATION_FAILED
                else:
                    return constants.OPERATION_PENDING
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the ESC Netconf server')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)
            except AttributeError as e:
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)

        if operation_type == 'vm_scale':
            tenant_name = operation_details['tenant_name']
            deployment_name = operation_details['deployment_name']
            vm_group_name = operation_details['vm_group_name']
            number_of_instances = operation_details['number_of_instances']

            # Get the number of VM instances belonging to this VM group name and compare it with the provided one
            try:
                xml = self.esc.get(('xpath',
                                    '/esc_datamodel/opdata/tenants/tenant[name="%s"]/deployments[deployment_name="%s"]/'
                                    'vm_group[name="%s"]' % (tenant_name, deployment_name, vm_group_name))).data_xml
                xml = etree.fromstring(xml)
                vm_name_list = xml.findall('.//{http://www.cisco.com/esc/esc}vm_instance/'
                                           '{http://www.cisco.com/esc/esc}name')
                actual_number_of_instances = len(vm_name_list)
                LOG.debug('ESC reported %s VM instances as part of VM group with name %s; expected %s'
                          % (actual_number_of_instances, vm_group_name, number_of_instances))
                if actual_number_of_instances != number_of_instances:
                    return constants.OPERATION_PENDING
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the ESC Netconf server')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)
            except AttributeError as e:
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)

            # Check that all VMs are started
            operation_list = []
            for vm_name in vm_name_list:
                lifecycle_operation_occurrence_id_item = uuid.uuid4()
                lifecycle_operation_occurrence_dict = {
                    'operation_type': 'vm_start',
                    'vm_name': vm_name.text,
                    'tenant_name': tenant_name,
                    'deployment_name': deployment_name
                }
                self.lifecycle_operation_occurrence_ids[
                    lifecycle_operation_occurrence_id_item] = lifecycle_operation_occurrence_dict
                operation_list.append(lifecycle_operation_occurrence_id_item)

            # To avoid checking again the number of VM instances for this VM group, use the current
            # lifecycle_operation_occurrence_id and not generate a new one. This will forcefully override the previous
            # operation dictionary, for vm_scale operation, with a new dictionary for vm_start operation.
            lifecycle_operations_occurrence_dict = {
                'operation_type': 'multiple_operations',
                'resource_id': operation_list
            }
            self.lifecycle_operation_occurrence_ids[
                lifecycle_operation_occurrence_id] = lifecycle_operations_occurrence_dict

            return self.get_operation_status(lifecycle_operation_occurrence_id)

        if operation_type == 'multiple_operations':
            operation_list = operation_details['resource_id']
            operation_status_list = map(self.get_operation_status, operation_list)

            if constants.OPERATION_FAILED in operation_status_list:
                return constants.OPERATION_FAILED
            elif constants.OPERATION_PENDING in operation_status_list:
                return constants.OPERATION_PENDING
            else:
                return constants.OPERATION_SUCCESS

        raise CiscoNFVManoAdapterError('Cannot get operation status for operation type "%s"' % operation_type)

    @log_entry_exit(LOG)
    def get_vm_groups_aggregated_deployment_state(self, vm_group_list, deployment_name):
        # If the VM group list is empty, report the VNF instantiation state as NOT_INSTANTIATED.
        if vm_group_list == list():
            return constants.VNF_NOT_INSTANTIATED

        # Get the NSO deployment plan xml
        try:
            xml = self.nso.get(('xpath',
                                '/nfvo/vnf-info/esc/vnf-deployment[deployment-name="%s"]/plan'
                                    % deployment_name)).data_xml
            xml = etree.fromstring(xml)
        except Exception as e:
            LOG.exception(e)
            raise CiscoNFVManoAdapterError(e.message)

        # If all VMs' state status is 'reached' report the VNF instantiation state as instantiated.
        for vm_group in vm_group_list:
            component_state = xml.find('.//{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}component'
                                       '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}name="%s"]/'
                                       '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}state'
                                       '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}name="ncs:ready"]/'
                                       '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}status' % vm_group).text

            if component_state != 'reached':
                return 'not-reached'

        return 'reached'

    @log_entry_exit(LOG)
    def get_vm_groups_aggregated_service_state(self, vm_group_list, tenant_name, deployment_name):
        # If the VM group list is empty, report the VNF state as STOPPED.
        if vm_group_list == list():
            raise CiscoNFVManoAdapterError('Cannot get VNF state for empty VM group in deployment %s' % deployment_name)

        # Get the ESC deployment xml
        try:
            xml = self.esc.get(('xpath',
                                '/esc_datamodel/opdata/tenants/tenant[name="%s"]/deployments[deployment_name="%s"]'
                                % (tenant_name, deployment_name))).data_xml
            xml = etree.fromstring(xml)
        except Exception as e:
            LOG.exception(e)
            raise CiscoNFVManoAdapterError(e.message)

        # If all VMs' state status is 'VM_ALIVE_STATE' report the VNF instantiation state as instantiated.
        for vm_group in vm_group_list:
            # Get all VM instance name belonging to the current VM group
            vm_name_list = xml.findall('.//{http://www.cisco.com/esc/esc}vm_group'
                                       '[{http://www.cisco.com/esc/esc}name="%s"]/'
                                       '{http://www.cisco.com/esc/esc}vm_instance'
                                       '/{http://www.cisco.com/esc/esc}name' % vm_group)

            # Get the VM state for each VM in this VM group:
            for vm_name in vm_name_list:
                vm_state = xml.find('.//{http://www.cisco.com/esc/esc}state_machine/'
                                    '{http://www.cisco.com/esc/esc}vm_state_machines/'
                                    '{http://www.cisco.com/esc/esc}vm_state_machine'
                                    '[{http://www.cisco.com/esc/esc}vm_name="%s"]/'
                                    '{http://www.cisco.com/esc/esc}state' % vm_name.text).text

                if vm_state != 'VM_ALIVE_STATE':
                    return 'SERVICE_STOPPED_STATE'

        return 'SERVICE_ACTIVE_STATE'

    @log_entry_exit(LOG)
    def vnf_query(self, filter, attribute_selector=None):
        vnf_instance_id = filter['vnf_instance_id']
        additional_param = filter['additional_param']
        deployment_name, vnf_name = self.vnf_instance_id_metadata[vnf_instance_id]
        tenant_name = additional_param['tenant']
        vnf_info = VnfInfo()
        vnf_info.vnf_instance_id = vnf_instance_id

        # Get the VM group list corresponding to the provided VNF instance ID
        vm_group_list = self.get_vm_groups_for_vnf(vnf_instance_id, additional_param)

        # Get the VNF instantiation state
        vnf_deployment_state = self.get_vm_groups_aggregated_deployment_state(vm_group_list, deployment_name)
        vnf_info.instantiation_state = constants.VNF_INSTANTIATION_STATE['NSO_DEPLOYMENT_STATE'][vnf_deployment_state]
        if vnf_info.instantiation_state == constants.VNF_NOT_INSTANTIATED:
            return vnf_info

        # Get the VNFD ID from the NSO
        xml = self.nso.get(('xpath',
                            '/nfvo/vnf-info/esc/vnf-deployment[deployment-name="%s"]/vnf-info[name="%s"]/vnfd'
                                % (deployment_name, vnf_name))).data_xml
        xml = etree.fromstring(xml)
        vnfd_id = xml.find('.//{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}vnf-info/'
                           '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}vnfd').text

        # Get the VNFD XML from the NSO
        vnfd_xml = self.nso.get(('xpath', '/nfvo/vnfd[id="%s"]' % vnfd_id)).data_xml
        vnfd_xml = etree.fromstring(vnfd_xml)

        # Build the vnf_info data structure
        vnf_info.vnf_instance_name = vnf_instance_id
        # vnf_info.vnf_instance_description =
        vnf_info.vnfd_id = vnfd_id

        # Build the InstantiatedVnfInfo information element only if the VNF instantiation state is INSTANTIATED
        if vnf_info.instantiation_state == constants.VNF_INSTANTIATED:
            vnf_info.instantiated_vnf_info = InstantiatedVnfInfo()

            # Get the VNF state
            vnf_service_state = self.get_vm_groups_aggregated_service_state(vm_group_list, tenant_name, deployment_name)
            vnf_info.instantiated_vnf_info.vnf_state = constants.VNF_STATE['ESC_DEPLOYMENT_STATE'][vnf_service_state]

            # Initialize the VnfcResourceInfo list
            vnf_info.instantiated_vnf_info.vnfc_resource_info = list()

            # Initialize the VnfExtCpInfo list
            vnf_info.instantiated_vnf_info.ext_cp_info = list()

            # Get the operational data deployment XML from the ESC
            opdata_deployment_xml = self.esc.get(('xpath',
                                                  '/esc_datamodel/opdata/tenants/tenant[name="%s"]/'
                                                    'deployments[deployment_name="%s"]'
                                                    % (tenant_name, deployment_name))).data_xml
            opdata_deployment_xml = etree.fromstring(opdata_deployment_xml)

            # Get the deployment XML from the ESC
            deployment_xml = self.esc.get(('xpath',
                                           '/esc_datamodel/tenants/tenant[name="%s"]/deployments/deployment[name="%s"]'
                                            % (tenant_name, deployment_name))).data_xml
            deployment_xml = etree.fromstring(deployment_xml)

            for vm_group in vm_group_list:
                # Get the VDU ID corresponding to this VM group
                vdu_id = deployment_xml.find('.//{http://www.cisco.com/esc/esc}vm_group'
                                             '[{http://www.cisco.com/esc/esc}name="%s"]/'
                                             '{http://www.cisco.com/esc/esc}extensions/'
                                             '{http://www.cisco.com/esc/esc}extension'
                                             '[{http://www.cisco.com/esc/esc}name="NSO"]/'
                                             '{http://www.cisco.com/esc/esc}properties/'
                                             '{http://www.cisco.com/esc/esc}property'
                                             '[{http://www.cisco.com/esc/esc}name="VDU"]/'
                                             '{http://www.cisco.com/esc/esc}value' % vm_group)
                vdu_id_text = vdu_id.text

                # Find all VM IDs in this VM group
                vm_id_list = opdata_deployment_xml.findall('.//{http://www.cisco.com/esc/esc}vm_group'
                                                           '[{http://www.cisco.com/esc/esc}name="%s"]/'
                                                           '{http://www.cisco.com/esc/esc}vm_instance/'
                                                           '{http://www.cisco.com/esc/esc}vm_id' % vm_group)

                # Iterate over the VM IDs in this VM group
                for vm_id in vm_id_list:
                    vm_id_text = vm_id.text

                    # Get the VM name
                    name = opdata_deployment_xml.find('.//{http://www.cisco.com/esc/esc}vm_group'
                                                      '[{http://www.cisco.com/esc/esc}name="%s"]/'
                                                      '{http://www.cisco.com/esc/esc}vm_instance'
                                                      '[{http://www.cisco.com/esc/esc}vm_id="%s"]/'
                                                      '{http://www.cisco.com/esc/esc}name' % (vm_group, vm_id_text))
                    name_text = name.text

                    # Build the VnfcResourceInfo data structure
                    vnfc_resource_info = VnfcResourceInfo()
                    vnfc_resource_info.vnfc_instance_id = name_text
                    vnfc_resource_info.vdu_id = vdu_id_text

                    vnfc_resource_info.compute_resource = ResourceHandle()
                    # Cisco ESC only support one VIM. Hardcode the VIM ID to string 'default_vim'
                    vnfc_resource_info.compute_resource.vim_id = 'default_vim'
                    vnfc_resource_info.compute_resource.resource_id = vm_id_text

                    # Append the current VnfvResourceInfo element to the VnfcResourceInfo list
                    vnf_info.instantiated_vnf_info.vnfc_resource_info.append(vnfc_resource_info)

                    # Get the list NIC IDs for this VM instance
                    nic_id_list = opdata_deployment_xml.findall('.//{http://www.cisco.com/esc/esc}vm_group'
                                                                '[{http://www.cisco.com/esc/esc}name="%s"]/'
                                                                '{http://www.cisco.com/esc/esc}vm_instance'
                                                                '[{http://www.cisco.com/esc/esc}vm_id="%s"]/'
                                                                '{http://www.cisco.com/esc/esc}interfaces/'
                                                                '{http://www.cisco.com/esc/esc}interface/'
                                                                '{http://www.cisco.com/esc/esc}nicid'
                                                                % (vm_group, vm_id_text))

                    # Iterate over the NIC IDs
                    for nic_id in nic_id_list:
                        nic_id_text = nic_id.text

                        # Get the internal connection point ID from the VNFD that corresponds to this port ID
                        cpd_id = vnfd_xml.find(
                            './/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}vdu'
                            '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}id="%s"]/'
                            '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}internal-connection-point-descriptor'
                            '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}interface-id="%s"]/'
                            '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}id'
                            % (vdu_id_text, nic_id_text))
                        cpd_id_text = cpd_id.text

                        # Get the port ID
                        port_id = opdata_deployment_xml.find('.//{http://www.cisco.com/esc/esc}vm_group'
                                                             '[{http://www.cisco.com/esc/esc}name="%s"]/'
                                                             '{http://www.cisco.com/esc/esc}vm_instance'
                                                             '[{http://www.cisco.com/esc/esc}vm_id="%s"]/'
                                                             '{http://www.cisco.com/esc/esc}interfaces/'
                                                             '{http://www.cisco.com/esc/esc}interface'
                                                             '[{http://www.cisco.com/esc/esc}nicid="%s"]/'
                                                             '{http://www.cisco.com/esc/esc}port_id'
                                                             % (vm_group, vm_id_text, nic_id_text))
                        port_id_text = port_id.text

                        # Get the IP address
                        ip_address = opdata_deployment_xml.find('.//{http://www.cisco.com/esc/esc}vm_group'
                                                                '[{http://www.cisco.com/esc/esc}name="%s"]/'
                                                                '{http://www.cisco.com/esc/esc}vm_instance'
                                                                '[{http://www.cisco.com/esc/esc}vm_id="%s"]/'
                                                                '{http://www.cisco.com/esc/esc}interfaces/'
                                                                '{http://www.cisco.com/esc/esc}interface'
                                                                '[{http://www.cisco.com/esc/esc}nicid="%s"]/'
                                                                '{http://www.cisco.com/esc/esc}ip_address'
                                                                % (vm_group, vm_id_text, nic_id_text))
                        ip_address_text = ip_address.text

                        # Get the IP address
                        mac_address = opdata_deployment_xml.find('.//{http://www.cisco.com/esc/esc}vm_group'
                                                                 '[{http://www.cisco.com/esc/esc}name="%s"]/'
                                                                 '{http://www.cisco.com/esc/esc}vm_instance'
                                                                 '[{http://www.cisco.com/esc/esc}vm_id="%s"]/'
                                                                 '{http://www.cisco.com/esc/esc}interfaces/'
                                                                 '{http://www.cisco.com/esc/esc}interface'
                                                                 '[{http://www.cisco.com/esc/esc}nicid="%s"]/'
                                                                 '{http://www.cisco.com/esc/esc}mac_address'
                                                                 % (vm_group, vm_id_text, nic_id_text))
                        mac_address_text = mac_address.text

                        # Build the VnfExtCpInfo data structure
                        vnf_ext_cp_info = VnfExtCpInfo()
                        vnf_ext_cp_info.cp_instance_id = port_id_text
                        vnf_ext_cp_info.address = [mac_address_text]
                        vnf_ext_cp_info.cpd_id = cpd_id_text

                        # Append the current VnfExtCpInfo element to the VnfExtCpInfo list
                        vnf_info.instantiated_vnf_info.ext_cp_info.append(vnf_ext_cp_info)

        # VNF instantiation state is not INSTANTIATED
        else:
            raise CiscoNFVManoAdapterError('The InstantiatedVnfInfo information element cannot be built as the VNF '
                                           'instantiation state is not INSTANTIATED')

        return vnf_info

    @log_entry_exit(LOG)
    def get_vnfd(self, vnfd_id):
        netconf_reply = self.nso.get(('xpath', '/nfvo/vnfd[id="%s"]' % vnfd_id))
        vnfd_xml = netconf_reply.data_xml
        return vnfd_xml

    @log_entry_exit(LOG)
    def get_nsd(self, nsd_id):
        netconf_reply = self.nso.get(('xpath', '/nfvo/nsd[id="%s"]' % nsd_id))
        nsd_xml = netconf_reply.data_xml
        return nsd_xml

    def validate_vnf_allocated_vresources(self, vnf_instance_id, additional_param):
        vnf_info = self.vnf_query(filter={'vnf_instance_id': vnf_instance_id, 'additional_param': additional_param})
        vnfd_id = vnf_info.vnfd_id
        vnfd = self.get_vnfd(vnfd_id)
        vnfd = etree.fromstring(vnfd)

        deployment_name, _ = self.vnf_instance_id_metadata[vnf_instance_id]

        # Get the VNFR from the NSO
        vnfr = self.nso.get(('xpath',
                             '/nfvo/vnf-info/esc/vnf-deployment[deployment-name="%s"]/vnf-info'
                                % deployment_name)).data_xml

        vnfr = etree.fromstring(vnfr)

        # Iterate over each VNFC and check that the corresponding flavor name in VNFR and Nova are the same
        for vnfc_resource_info in vnf_info.instantiated_vnf_info.vnfc_resource_info:

            # Get VIM adapter object
            vim = self.get_vim_helper(vnfc_resource_info.compute_resource.vim_id)

            # Get the name of the flavor associated to this VNFC from Nova
            server_id = vnfc_resource_info.compute_resource.resource_id
            server_details = vim.server_get(server_id)
            server_flavor_id = server_details['flavor_id']
            flavor_details = vim.flavor_get(server_flavor_id)
            flavor_name_nova = str(flavor_details['name'])

            # Get the name of the flavor associated to this VNFC from the VNFR
            vdu_id = vnfc_resource_info.vdu_id
            flavor_name_vnfr = vnfr.find('.//{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}vnf-info/'
                                         '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}'
                                         'vdu[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}id="%s"]/'
                                         '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}flavor-name' % vdu_id).text

            # Check that the the two flavor names are the same
            if flavor_name_nova != flavor_name_vnfr:
                return False

            # Get the number of ports reported by Nova for the current VNFC
            resource_id = vnfc_resource_info.compute_resource.resource_id
            port_dict = vim.port_list(device_id=resource_id)
            for port_list in port_dict:
                try:
                    port_number_nova = len(port_list['ports'])
                except KeyError:
                    raise CiscoNFVManoAdapterError(
                        'Unable to iterate the port list dict returned by Nova for server with ID %s' % resource_id)

            # Get the number of ports in the VNFD for the VDU type that corresponds to the current VNFC type
            port_number_vnfd = len(vnfd.findall(
                './/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}vdu[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}'
                'id="%s"]/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}internal-connection-point-descriptor' % vdu_id))

            # Check that the number of ports reported by Nova for the current VNFC is the same as the number of ports in
            # the VNFD for the VDU type that corresponds to the current VNFC type
            if port_number_nova != port_number_vnfd:
                return False

                # TODO: Check NIC type

        return True

    @log_entry_exit(LOG)
    def build_day0_config(self, day0_config):
        day0_config__xml = ''
        if 'destination' in day0_config and 'url' in day0_config:
            day0_config_template_values = {
                'day0_dest': day0_config['destination'],
                'day0_url': day0_config['url']
            }
            day0_config__xml = DAY0_TEMPLATE % day0_config_template_values

        return day0_config__xml

    @log_entry_exit(LOG)
    def build_vdu_list(self, vdu_params):
        vdu_list_xml = ''
        for vdu_id, vdu_param in vdu_params.items():
            vdu_template_values = {
                'vdu_id': vdu_id,
                'image_name': vdu_param['image'],
                'flavor_name': vdu_param['flavor'],
                'day0_config': self.build_day0_config(vdu_param['day0']),
                'bootup_time': vdu_param['bootup_time'],
                'recovery_wait_time': vdu_param['recovery_wait_time'],
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
    def build_vl_list(self, vl_params):
        vl_list_xml = ''
        for vl_id, vl_param in vl_params.items():
            vl_template_values = {
                'vl_id': vl_id,
                'vl_details': self.build_vl_details(vl_param)
            }

            vl_xml = VL_TEMPLATE % vl_template_values
            vl_list_xml += vl_xml

        return vl_list_xml

    @log_entry_exit(LOG)
    def build_vnfr(self, deployment_name, vnf_name, vnfd_id, flavour_id, instantiation_level_id, additional_param):
        vnfr_template_values = {
            'tenant': additional_param['tenant'],
            'deployment_name': deployment_name,
            'esc': additional_param['esc'],
            'username': additional_param['username'],
            'vnf_name': vnf_name,
            'vnfd_id': vnfd_id,
            'vnfd_flavor': flavour_id,
            'instantiation_level': instantiation_level_id,
            'vdu_list': self.build_vdu_list(additional_param['vdu']),
            'vnfd_cp_list': self.build_vnfd_cp_list(additional_param['ext_cp_vlr']),
            'vl_list': self.build_vl_list(additional_param['virtual_link'])
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
    def build_vm_operate(self, vm_name, action):
        vm_operate_template_values = {
            'vm_name': vm_name,
            'action': action
        }

        vm_operate_xml = VM_OPERATE_TEMPLATE % vm_operate_template_values
        return vm_operate_xml

    @log_entry_exit(LOG)
    def build_scaling_vm_group_list(self, vm_group_params):
        scaling_vm_group_list_xml = ''
        for vm_group_name, number_of_instances in vm_group_params.items():
            scaling_vm_group_template_values = {
                'vm_group_name': vm_group_name,
                'min_active': number_of_instances,
                'max_active': number_of_instances
            }

            scaling_vm_group_xml = SCALING_VM_GROUP_TEMPLATE % scaling_vm_group_template_values
            scaling_vm_group_list_xml += scaling_vm_group_xml

        return scaling_vm_group_list_xml

    @log_entry_exit(LOG)
    def build_scaling(self, esc_name, tenant_name, deployment_name, vm_group_params):
        scaling_template_values = {
            'esc_name': esc_name,
            'tenant_name': tenant_name,
            'deployment_name': deployment_name,
            'vm_group_list': self.build_scaling_vm_group_list(vm_group_params)
        }

        scaling_xml = SCALING_TEMPLATE % scaling_template_values
        return scaling_xml

    @log_entry_exit(LOG)
    def generate_vnf_instance_id(self, deployment_name, vnf_name):
        vnf_instance_id = str(uuid.uuid3(uuid.NAMESPACE_OID, str('%s-%s' % (deployment_name, vnf_name))))
        self.vnf_instance_id_metadata[vnf_instance_id] = deployment_name, vnf_name

        return vnf_instance_id

    @log_entry_exit(LOG)
    def vnf_create_id(self, vnfd_id, vnf_instance_name=None, vnf_instance_description=None):
        vnf_instance_id = self.generate_vnf_instance_id(deployment_name=vnf_instance_name, vnf_name=vnfd_id)
        self.vnf_vnfd_mapping[vnf_instance_id] = vnfd_id

        return vnf_instance_id

    @log_entry_exit(LOG)
    def vnf_instantiate(self, vnf_instance_id, flavour_id, instantiation_level_id=None, ext_virtual_link=None,
                        ext_managed_virtual_link=None, localization_language=None, additional_param=None):
        deployment_name, vnf_name = self.vnf_instance_id_metadata[vnf_instance_id]
        vnfd_id = self.vnf_vnfd_mapping[vnf_instance_id]
        vnfr_xml = self.build_vnfr(deployment_name, vnf_name, vnfd_id, flavour_id, instantiation_level_id,
                                   additional_param)
        try:
            netconf_reply = self.nso.edit_config(target='running', config=vnfr_xml)
        except NCClientError as e:
            LOG.exception(e)
            raise CiscoNFVManoAdapterError(e.message)

        if '<ok/>' not in netconf_reply.xml:
            raise CiscoNFVManoAdapterError('NSO replied with an error')

        LOG.debug('NSO reply: %s' % netconf_reply.xml)

        lifecycle_operation_occurrence_id = uuid.uuid4()
        lifecycle_operation_occurrence_dict = {
            'operation_type': 'vnf_instantiate',
            'tenant_name': additional_param['tenant'],
            'deployment_name': deployment_name
        }
        self.lifecycle_operation_occurrence_ids[lifecycle_operation_occurrence_id] = lifecycle_operation_occurrence_dict

        return lifecycle_operation_occurrence_id

    @log_entry_exit(LOG)
    def vnf_scale_to_level(self, vnf_instance_id, instantiation_level_id=None, scale_info=None, additional_param=None):
        deployment_name, vnf_name = self.vnf_instance_id_metadata[vnf_instance_id]
        tenant_name = additional_param['tenant']

        if instantiation_level_id is not None:
            # This operation will not change de instantiation level ID as the scaling does not occur in Cisco NSO when
            # changing to an instantiation level that has a lower number of instances.
            # Instead, this operation will set the min_active and max_active values to the number of instances
            # corresponding to the provided instantiation level ID.

            # Get the deployment XML
            try:
                deployment_xml = self.nso.get(('xpath',
                                               '/nfvo/vnf-info/esc/vnf-deployment[tenant="%s"][deployment-name="%s"]'
                                                   % (tenant_name, deployment_name))).data_xml
                deployment_xml = etree.fromstring(deployment_xml)
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the ESC Netconf server')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)

            # Get the name of the ESC this deployment belongs to
            try:
                esc_name = deployment_xml.find('.//{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}vnf-deployment/'
                                               '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}esc').text
            except AttributeError as e:
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)

            # Get the deployment flavor name
            try:
                deployment_flavor = deployment_xml.find('.//{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}vnf-info/'
                                                        '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}name="%s"]/'
                                                        '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}vnfd-flavor'
                                                        % vnf_name).text
            except AttributeError as e:
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)

            # Get the VNFD ID
            try:
                vnfd_id = deployment_xml.find('.//{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}vnf-info/'
                                              '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}name="%s"]/'
                                              '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}vnfd' % vnf_name).text
            except AttributeError as e:
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)

            # Get the VNFD
            vnfd = self.get_vnfd(vnfd_id)
            vnfd = etree.fromstring(vnfd)

            # Get the instantiation level XML corresponding to the provided instantiation level ID from the VNFD
            try:
                instantiation_level_xml = vnfd.find(('.//{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}deployment-flavor'
                                                     '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}id="%s"]/'
                                                     '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}instantiation-level'
                                                     '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}id="%s"]'
                                                     % (deployment_flavor, instantiation_level_id)))
                if instantiation_level_xml is None:
                    raise CiscoNFVManoAdapterError('No instantiation level ID named %s defined in VNFD %s, under '
                                                   'deployment flavor %s' % (instantiation_level_id, vnfd_id,
                                                                             deployment_flavor))
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the ESC Netconf server')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)

            # Get the list of VDU in this instantiation level
            vdu_list = instantiation_level_xml.findall('.//{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}vdu-level/'
                                                       '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}vdu')

            # Set the min and max active instances for each VDU with the corresponding number of instances from the
            # instantiation level
            operation_list = []
            vm_group_params = {}
            for vdu_id in vdu_list:
                number_of_instances = instantiation_level_xml.find(
                    './/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}vdu-level'
                    '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}vdu="%s"]/'
                    '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}number-of-instances' % vdu_id.text).text
                vm_group_name = '%s-%s' % (vnf_name, vdu_id.text)
                vm_group_params[vm_group_name] = number_of_instances

                lifecycle_operation_occurrence_id = uuid.uuid4()
                lifecycle_operation_occurrence_dict = {
                    'operation_type': 'vm_scale',
                    'vm_group_name': vm_group_name,
                    'number_of_instances': int(number_of_instances),
                    'tenant_name': additional_param['tenant'],
                    'deployment_name': deployment_name
                }
                self.lifecycle_operation_occurrence_ids[
                    lifecycle_operation_occurrence_id] = lifecycle_operation_occurrence_dict
                operation_list.append(lifecycle_operation_occurrence_id)

            # Build the scaling XML
            scaling_xml = self.build_scaling(esc_name, tenant_name, deployment_name, vm_group_params)
            try:
                netconf_reply = self.nso.edit_config(target='running', config=scaling_xml)
            except NCClientError as e:
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)

            if '<ok/>' not in netconf_reply.xml:
                raise CiscoNFVManoAdapterError('NSO replied with an error')

            LOG.debug('NSO reply: %s' % netconf_reply.xml)

            lifecycle_operations_occurrence_id = uuid.uuid4()
            lifecycle_operations_occurrence_dict = {
                'operation_type': 'multiple_operations',
                'resource_id': operation_list
            }
            self.lifecycle_operation_occurrence_ids[
                lifecycle_operations_occurrence_id] = lifecycle_operations_occurrence_dict

            return lifecycle_operations_occurrence_id

        if scale_info is not None:
            raise NotImplementedError

        raise CiscoNFVManoAdapterError('Neither instantiationLevelId nor ScaleInfo is present')

    @log_entry_exit(LOG)
    def vnf_terminate(self, vnf_instance_id, termination_type, graceful_termination_timeout=None,
                      additional_param=None):
        LOG.debug('This function deletes the entire deployment! It should be used only in VNF lifecycle tests!')

        deployment_name, _ = self.vnf_instance_id_metadata[vnf_instance_id]
        vnfr_delete_xml = self.build_vnfr_delete(deployment_name, additional_param)

        try:
            netconf_reply = self.nso.edit_config(target='running', config=vnfr_delete_xml)
        except NCClientError as e:
            LOG.exception(e)
            raise CiscoNFVManoAdapterError(e.message)

        if '<ok/>' not in netconf_reply.xml:
            raise CiscoNFVManoAdapterError('NSO replied with an error')

        LOG.debug('NSO reply: %s' % netconf_reply.xml)

        lifecycle_operation_occurrence_id = uuid.uuid4()
        lifecycle_operation_occurrence_dict = {
            'operation_type': 'vnf_terminate',
            'tenant_name': additional_param['tenant'],
            'deployment_name': deployment_name
        }
        self.lifecycle_operation_occurrence_ids[lifecycle_operation_occurrence_id] = lifecycle_operation_occurrence_dict

        return lifecycle_operation_occurrence_id

    @log_entry_exit(LOG)
    def vnf_delete_id(self, vnf_instance_id):
        self.vnf_instance_id_metadata.pop(vnf_instance_id)
        self.vnf_vnfd_mapping.pop(vnf_instance_id)

    @log_entry_exit(LOG)
    def vnf_operate(self, vnf_instance_id, change_state_to, stop_type=None, graceful_stop_timeout=None,
                    additional_param=None):
        etsi_state_esc_action_mapping = {
            'start': 'START',
            'stop': 'STOP'
        }

        deployment_name, _ = self.vnf_instance_id_metadata[vnf_instance_id]

        xml = self.esc.get(('xpath',
                            '/esc_datamodel/opdata/tenants/tenant[name="%s"]/deployments[deployment_name="%s"]'
                            % (additional_param['tenant'], deployment_name))).data_xml
        xml = etree.fromstring(xml)

        vm_group_list = self.get_vm_groups_for_vnf(vnf_instance_id, additional_param)
        vm_name_list = []
        for vm_group in vm_group_list:
            # Get all VM instance name belonging to the current VM group
            vm_name_list += xml.findall('.//{http://www.cisco.com/esc/esc}vm_group'
                                        '[{http://www.cisco.com/esc/esc}name="%s"]/'
                                        '{http://www.cisco.com/esc/esc}vm_instance'
                                        '/{http://www.cisco.com/esc/esc}name' % vm_group)

        operation_list = []
        for vm_name in vm_name_list:
            vm_operate_xml = self.build_vm_operate(vm_name.text, etsi_state_esc_action_mapping[change_state_to])

            try:
                netconf_reply = self.esc.dispatch(rpc_command=etree.fromstring(vm_operate_xml))
            except NCClientError as e:
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)

            if '<ok/>' not in netconf_reply.xml:
                raise CiscoNFVManoAdapterError('ESC replied with an error')

            LOG.debug('ESC reply: %s' % netconf_reply.xml)

            lifecycle_operation_occurrence_id = uuid.uuid4()
            lifecycle_operation_occurrence_dict = {
                'operation_type': 'vm_%s' % change_state_to,
                'vm_name': vm_name.text,
                'tenant_name': additional_param['tenant'],
                'deployment_name': deployment_name
            }
            self.lifecycle_operation_occurrence_ids[
                lifecycle_operation_occurrence_id] = lifecycle_operation_occurrence_dict
            operation_list.append(lifecycle_operation_occurrence_id)

        lifecycle_operations_occurrence_id = uuid.uuid4()
        lifecycle_operations_occurrence_dict = {
            'operation_type': 'multiple_operations',
            'resource_id': operation_list
        }
        self.lifecycle_operation_occurrence_ids[
            lifecycle_operations_occurrence_id] = lifecycle_operations_occurrence_dict

        return lifecycle_operations_occurrence_id

    @log_entry_exit(LOG)
    def get_vim_helper(self, vim_id):
        if self.vim_helper is None:
            netconf_reply = self.esc.get(('xpath', '/esc_system_config/vim_connectors/vim_connector'))
            vim_xml = etree.fromstring(netconf_reply.data_xml)

            vim_type = vim_xml.find('.//{http://www.cisco.com/esc/esc}type').text
            if vim_type == 'OPENSTACK':
                client_params = dict()
                property_name_mapping = {
                    'os_auth_url': 'auth_url',
                    'os_password': 'password',
                    'os_project_name': 'project_name',
                    'os_project_domain_name': 'project_domain_name',
                    'os_user_domain_name': 'user_domain_name'
                }
                property_list = vim_xml.findall('.//{http://www.cisco.com/esc/esc}property')
                for property_elem in property_list:
                    property_name = property_elem.find('.//{http://www.cisco.com/esc/esc}name').text
                    property_value = property_elem.find('.//{http://www.cisco.com/esc/esc}value').text

                    vim_param = property_name_mapping.get(property_name)
                    if vim_param is not None:
                        client_params[vim_param] = property_value

                user_id_elem = vim_xml.find('.//{http://www.cisco.com/esc/esc}user/{http://www.cisco.com/esc/esc}id')
                user_id = user_id_elem.text
                client_params['username'] = user_id

                # If the ESC reports VIM project_domain_name as empty string, set it as Default
                if 'project_domain_name' in client_params and 'user_domain_name' in client_params:
                    if client_params['project_domain_name'] is None:
                        client_params['project_domain_name'] = client_params['user_domain_name']

                self.vim_helper = construct_adapter(vendor='openstack', module_type='vim', **client_params)

            else:
                raise CiscoNFVManoAdapterError('Cannot create VIM helper for unsupported type: %s' % vim_type)

        return self.vim_helper

    @log_entry_exit(LOG)
    def wait_for_vnf_stable_state(self, vnf_instance_id, max_wait_time, poll_interval):
        # Since the NSO VNF deployment state is seen as VNF instantiation state, the VNF termination is always safe, no
        # matter the VNF deployment state in the ESC.
        return True

    @log_entry_exit(LOG)
    def build_ns_vnf_info_list(self, ns_instance_id, vnf_info_params):
        ns_vnf_info_list_xml = ''
        for vnf_name, vnf_param in vnf_info_params.items():
            vnf_info_template_values = {
                'vnf_name': vnf_name,
                'vnfd_id': vnf_param['vnfd_id'],
                'vl_list': self.build_vl_list(vnf_param['virtual_link']),
                'tenant': vnf_param['tenant'],
                'vdu_list': self.build_vdu_list(vnf_param['vdu']),
                'deployment_name': ns_instance_id,
                'esc': vnf_param['esc']
            }

            ns_vnf_info_xml = NS_VNF_INFO_TEMPLATE % vnf_info_template_values
            ns_vnf_info_list_xml += ns_vnf_info_xml

        return ns_vnf_info_list_xml

    @log_entry_exit(LOG)
    def build_vl_details(self, vl_param):
        vl_details_template_values = {
            'dhcp': '<dhcp/>' if vl_param.get('dhcp', False) is True else '',
            'network': vl_param['subnet']['network'],
            'gateway': vl_param['subnet']['gateway']
        }

        vl_details_template_xml = VL_DETAILS_TEMPLATE % vl_details_template_values
        return vl_details_template_xml

    @log_entry_exit(LOG)
    def build_vl_info_list(self, vl_info_params):
        vl_info_list_xml = ''
        for vl_descriptor_id, vl_param in vl_info_params.items():
            vl_info_template_values = {
                'vl_descriptor_id': vl_descriptor_id,
                'vl_details': self.build_vl_details(vl_param)
            }
            vl_info_xml = VL_INFO_TEMPLATE % vl_info_template_values
            vl_info_list_xml += vl_info_xml

        return vl_info_list_xml

    @log_entry_exit(LOG)
    def build_sap_info_list(self, sap_info_params):
        sap_info_list_xml = ''
        for sapd in sap_info_params:
            sap_info_template_values = {
                'sapd': sapd,
                'network_name': sap_info_params[sapd]
            }

            sap_info_xml = SAP_INFO_TEMPLATE % sap_info_template_values
            sap_info_list_xml += sap_info_xml

        return sap_info_list_xml

    @log_entry_exit(LOG)
    def build_nsr(self, ns_instance_id, flavour_id, sap_data, ns_instantiation_level_id, additional_param_for_ns):
        nsd_id = self.ns_nsd_mapping[ns_instance_id]

        nsr_template_values = {
            'ns_id': ns_instance_id,
            'username': additional_param_for_ns['username'],
            'nsd_id': nsd_id,
            'flavor': flavour_id,
            'instantiation_level': ns_instantiation_level_id,
            'vnf_info_list': self.build_ns_vnf_info_list(ns_instance_id, additional_param_for_ns['vnf_info']),
            'vl_list': self.build_vl_info_list(additional_param_for_ns['virtual_link_info']),
            'state': 'instantiated',
            'sap_info_list': self.build_sap_info_list(sap_data)
        }

        nsr_xml = NSR_TEMPLATE % nsr_template_values

        return nsr_xml

    @log_entry_exit(LOG)
    def build_nsr_delete(self, ns_instance_id):
        nsr_delete_template_values = {
            'ns_info_id': ns_instance_id
        }

        nsr_delete_xml = NSR_DELETE_TEMPLATE % nsr_delete_template_values
        return nsr_delete_xml

    @log_entry_exit(LOG)
    def ns_create_id(self, nsd_id, ns_name, ns_description):
        ns_instance_id = ns_name
        self.ns_nsd_mapping[ns_instance_id] = nsd_id

        return ns_instance_id

    @log_entry_exit(LOG)
    def ns_instantiate(self, ns_instance_id, flavour_id, sap_data=None, pnf_info=None, vnf_instance_data=None,
                       nested_ns_instance_data=None, location_constraints=None, additional_param_for_ns=None,
                       additional_param_for_vnf=None, start_time=None, ns_instantiation_level_id=None,
                       additional_affinity_or_anti_affinity_rule=None):

        nsr_xml = self.build_nsr(ns_instance_id, flavour_id, sap_data, ns_instantiation_level_id,
                                 additional_param_for_ns)
        try:
            netconf_reply = self.nso.edit_config(target='running', config=nsr_xml)
        except NCClientError as e:
            LOG.exception(e)
            raise CiscoNFVManoAdapterError(e.message)

        if '<ok/>' not in netconf_reply.xml:
            raise CiscoNFVManoAdapterError('NSO replied with an error')

        LOG.debug('NSO reply: %s' % netconf_reply.xml)

        lifecycle_operation_occurrence_id = uuid.uuid4()
        lifecycle_operation_occurrence_dict = {
            'operation_type': 'ns_instantiate',
            'tenant_name': additional_param_for_ns['tenant'],
            'deployment_name': ns_instance_id
        }
        self.lifecycle_operation_occurrence_ids[lifecycle_operation_occurrence_id] = lifecycle_operation_occurrence_dict

        return lifecycle_operation_occurrence_id

    @log_entry_exit(LOG)
    def ns_query(self, filter, attribute_selector=None):
        ns_instance_id = filter['ns_instance_id']
        additional_param = filter['additional_param']
        ns_info = NsInfo()
        ns_info.ns_instance_id = ns_instance_id

        # Try to retrieve the instantiation state for the NS with the given instance ID. If the AttributeError
        # exception is raised, report the NS instantiation state as NOT_INSTANTIATED.
        try:
            nso_deployment_xml = self.nso.get(('xpath',
                                               '/nfvo/ns-info/esc/ns-info[id="%s"]' % ns_instance_id)).data_xml
            nso_deployment_xml = etree.fromstring(nso_deployment_xml)
            nso_ns_deployment_state = nso_deployment_xml.find(
                './/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}component'
                '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}name="self"]/'
                '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}state/'
                '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}status').text
        except AttributeError:
            ns_info.ns_state = constants.NS_NOT_INSTANTIATED
            return ns_info
        except Exception as e:
            LOG.exception(e)
            raise CiscoNFVManoAdapterError(e.message)

        ns_info.ns_name = ns_instance_id
        ns_info.nsd_id = self.ns_nsd_mapping[ns_instance_id]
        ns_info.ns_state = constants.NS_INSTANTIATION_STATE['NSO_DEPLOYMENT_STATE'][nso_ns_deployment_state]

        # Get the NS deployment flavor from the NSO
        ns_deployment_flavor = nso_deployment_xml.find('.//{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}flavor').text
        ns_info.flavor_id = ns_deployment_flavor

        # Build the VnfInfo data structure for each VNF that is part of the NS
        ns_info.vnf_info = list()
        vnf_ids = nso_deployment_xml.findall('.//{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}vnf-info/'
                                             '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}name')
        for vnf_name in vnf_ids:
            vnf_instance_id = self.generate_vnf_instance_id(deployment_name=ns_instance_id, vnf_name=vnf_name.text)
            vnf_info = self.vnf_query(filter={'vnf_instance_id': vnf_instance_id,
                                              'additional_param': additional_param})
            vnf_info.vnf_product_name = vnf_name.text
            ns_info.vnf_info.append(vnf_info)

        return ns_info

    @log_entry_exit(LOG)
    def ns_scale(self, ns_instance_id, scale_type, scale_ns_data=None, scale_vnf_data=None, scale_time=None):
        if scale_type == 'SCALE_NS':
            raise NotImplementedError
        elif scale_type == 'SCALE_VNF':
            operation_list = []
            for scale_data in scale_vnf_data:
                if scale_data.type == 'to_instantiation_level':
                    vnf_instance_id = self.generate_vnf_instance_id(deployment_name=ns_instance_id,
                                                                    vnf_name=scale_data.vnf_instance_id)
                    instantiation_level_id = scale_data.scale_to_level_data.instantiation_level_id
                    lifecycle_operation_occurrence_id = self.vnf_scale_to_level(
                                                       vnf_instance_id=vnf_instance_id,
                                                       instantiation_level_id=instantiation_level_id,
                                                       additional_param=scale_data.scale_to_level_data.additional_param)
                    operation_list.append(lifecycle_operation_occurrence_id)
                elif scale_data.type == 'to_scale_levels':
                    raise NotImplementedError
                elif scale_data.type == 'out':
                    raise NotImplementedError
                elif scale_data.type == 'in':
                    raise NotImplementedError

            lifecycle_operations_occurrence_id = uuid.uuid4()
            lifecycle_operations_occurrence_dict = {
                'operation_type': 'multiple_operations',
                'resource_id': operation_list
            }
            self.lifecycle_operation_occurrence_ids[
                lifecycle_operations_occurrence_id] = lifecycle_operations_occurrence_dict

            return lifecycle_operations_occurrence_id

    @log_entry_exit(LOG)
    def get_vm_groups_for_vnf(self, vnf_instance_id, additional_param):
        deployment_name, vnf_name = self.vnf_instance_id_metadata[vnf_instance_id]
        tenant_name = additional_param['tenant']

        # Get from the NSO the name of the ESC this deployment belongs to
        try:
            xml = self.nso.get(('xpath', '/nfvo/vnf-info/esc/vnf-deployment[tenant="%s"][deployment-name="%s"]'
                                % (tenant_name, deployment_name))).data_xml
            xml = etree.fromstring(xml)
            esc_name = xml.find('.//{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}vnf-deployment/'
                                '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}esc').text
        except NCClientError as e:
            LOG.debug('Error occurred while communicating with the ESC Netconf server')
            LOG.exception(e)
            raise CiscoNFVManoAdapterError(e.message)

        # Get from the NSO the VM group names belonging to this deployment
        try:
            vm_groups_xml = self.nso.get(('xpath',
                                          '/devices/device[name="%s"]/config/esc_datamodel/tenants/tenant[name="%s"]/'
                                            'deployments/deployment[name="%s"]/vm_group'
                                            % (esc_name, tenant_name, deployment_name))).data_xml
            vm_groups = etree.fromstring(vm_groups_xml)
            vm_group_names = vm_groups.findall('.//{http://www.cisco.com/esc/esc}vm_group/'
                                               '{http://www.cisco.com/esc/esc}name')
        except NCClientError as e:
            LOG.debug('Error occurred while communicating with the ESC Netconf server')
            LOG.exception(e)
            raise CiscoNFVManoAdapterError(e.message)

        # Get the list of VM groups belonging to the VNF with the name corresponding to the provided VNF instance ID
        vm_group_list = list()
        for vm_group_name in vm_group_names:
            current_vnf_name = vm_groups.find('.//{http://www.cisco.com/esc/esc}vm_group'
                                              '[{http://www.cisco.com/esc/esc}name="%s"]/'
                                              '{http://www.cisco.com/esc/esc}extensions/'
                                              '{http://www.cisco.com/esc/esc}extension'
                                              '[{http://www.cisco.com/esc/esc}name="NSO"]/'
                                              '{http://www.cisco.com/esc/esc}properties/'
                                              '{http://www.cisco.com/esc/esc}property'
                                              '[{http://www.cisco.com/esc/esc}name="VNF-INFO-NAME"]/'
                                              '{http://www.cisco.com/esc/esc}value' % vm_group_name.text).text
            if current_vnf_name == vnf_name:
                vm_group_list.append(vm_group_name.text)

        return vm_group_list

    @log_entry_exit(LOG)
    def ns_terminate(self, ns_instance_id, terminate_time=None, additional_param=None):
        nsr_delete_xml = self.build_nsr_delete(ns_instance_id)

        try:
            netconf_reply = self.nso.edit_config(target='running', config=nsr_delete_xml)
        except NCClientError as e:
            LOG.exception(e)
            raise CiscoNFVManoAdapterError(e.message)

        if '<ok/>' not in netconf_reply.xml:
            raise CiscoNFVManoAdapterError('NSO replied with an error')

        LOG.debug('NSO reply: %s' % netconf_reply.xml)

        lifecycle_operation_occurrence_id = uuid.uuid4()
        lifecycle_operation_occurrence_dict = {
            'operation_type': 'ns_terminate',
            'tenant_name': additional_param['tenant'],
            'deployment_name': ns_instance_id
        }
        self.lifecycle_operation_occurrence_ids[lifecycle_operation_occurrence_id] = lifecycle_operation_occurrence_dict

        return lifecycle_operation_occurrence_id

    @log_entry_exit(LOG)
    def ns_delete_id(self, ns_instance_id):
        self.ns_nsd_mapping.pop(ns_instance_id)

    @log_entry_exit(LOG)
    def wait_for_ns_stable_state(self, ns_instance_id, max_wait_time, poll_interval):
        # Since the NSO NS deployment state is seen as NS instantiation state, the NS termination is always safe, no
        # matter the NS deployment state in the ESC.
        return True

    @log_entry_exit(LOG)
    def verify_vnf_sw_images(self, vnf_info, additional_param=None):
        tenant_name = additional_param['tenant']
        vnf_instance_id = vnf_info.vnf_instance_id
        deployment_name, _ = self.vnf_instance_id_metadata[vnf_instance_id]

        for vnfc_resource_info in vnf_info.instantiated_vnf_info.vnfc_resource_info:
            # Get image name from the deployment for the VDU ID of the current VNFC
            vdu_id = vnfc_resource_info.vdu_id
            vm_group_name = '%s-%s' % (vnf_info.vnf_product_name, vdu_id)
            try:
                xml = self.esc.get(('xpath',
                                    '/esc_datamodel/tenants/tenant[name="%s"]/deployments/deployment[name="%s"]/'
                                    'vm_group[name="%s"]' % (tenant_name, deployment_name, vm_group_name))).data_xml
                deployment_vm_group = etree.fromstring(xml)
            except NCClientError as e:
                LOG.debug('Error occurred while communicating with the ESC Netconf server')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)
            image_name_esc = deployment_vm_group.find('.//{http://www.cisco.com/esc/esc}image').text

            # Get image name from VIM for the current VNFC
            vim_id = vnfc_resource_info.compute_resource.vim_id
            vim = self.get_vim_helper(vim_id)
            resource_id = vnfc_resource_info.compute_resource.resource_id
            virtual_compute = vim.query_virtualised_compute_resource(filter={'compute_id': resource_id})
            image_id = virtual_compute.vc_image_id
            image_details = vim.query_image(image_id)
            image_name_vim = image_details.name

            # The two image names should be identical
            if image_name_esc != image_name_vim:
                LOG.debug('Unexpected image for VNFC %s, VDU type %s' % (resource_id, vdu_id))
                LOG.debug('Expected image name: %s; actual image name: %s' % (image_name_esc, image_name_vim))
                return False

        return True

    @log_entry_exit(LOG)
    def validate_ns_allocated_vresources(self, ns_instance_id, additional_param=None):
        ns_info = self.ns_query(filter={'ns_instance_id': ns_instance_id, 'additional_param': additional_param})
        for vnf_info in ns_info.vnf_info:
            vnf_instance_id = vnf_info.vnf_instance_id
            if not self.validate_vnf_allocated_vresources(vnf_instance_id, additional_param):
                LOG.debug('For VNF instance ID %s expected resources do not match the actual ones' % vnf_instance_id)
                return False

        return True

    @log_entry_exit(LOG)
    def verify_vnf_nsd_mapping(self, ns_instance_id, additional_param=None):
        ns_info = self.ns_query(filter={'ns_instance_id': ns_instance_id, 'additional_param': additional_param})
        nsd_id = ns_info.nsd_id
        ns_deployment_flavor = ns_info.flavor_id
        nsd = self.get_nsd(nsd_id)
        nsd = etree.fromstring(nsd)

        # Build mapping between VNF names and their corresponding VNFD IDs
        vnf_profile_list_xml = nsd.findall('.//{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}nfvo'
                                           '/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}nsd'
                                           '/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}deployment-flavor'
                                           '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}id="%s"]/'
                                           '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}vnf-profile'
                                           % ns_deployment_flavor)
        vnf_name_vnfd_id_mapping = dict()
        for vnf_profile in vnf_profile_list_xml:
            vnf_profile_id = vnf_profile.find('.//{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}id').text
            vnfd_id = vnf_profile.find('.//{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}vnfd').text
            vnf_name_vnfd_id_mapping[vnf_profile_id] = vnfd_id

        # Compare the expected VNFD IDs with the actual ones
        for vnf_info in ns_info.vnf_info:
            try:
                expected_vnfd_id = vnf_name_vnfd_id_mapping[vnf_info.vnf_product_name]
                actual_vnfd_id = vnf_info.vnfd_id
                if actual_vnfd_id != expected_vnfd_id:
                    LOG.debug('VNF with instance ID %s was deployed according to VNFD %s instead of %s'
                              % (vnf_info.vnf_instance_id, actual_vnfd_id, expected_vnfd_id))
                    return False
            except KeyError:
                LOG.debug('VNF with instance ID %s was deployed according to an unknown VNFD'
                          % vnf_info.vnf_instance_id)
                return False

        return True

    @log_entry_exit(LOG)
    def get_vnf_mgmt_addr_list(self, vnf_instance_id, additional_param=None):
        deployment_name, vnf_name = self.vnf_instance_id_metadata[vnf_instance_id]
        mgmt_addr_list = list()

        # Get the VNFD corresponding to this VNF instance
        tenant_name = additional_param['tenant']
        vnf_info = self.vnf_query(filter={'vnf_instance_id': vnf_instance_id,
                                          'additional_param': {'tenant': tenant_name}})
        vnfd_id = vnf_info.vnfd_id
        vnfd = self.get_vnfd(vnfd_id)
        vnfd_xml = etree.fromstring(vnfd)

        # Finding the external-connection-point descriptor that is used by the VNF as management interface
        try:
            mgmt_cpd = vnfd_xml.find(
                './/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}external-connection-point-descriptor/'
                '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}management]/'
                '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}id').text
        except AttributeError:
            LOG.debug('VNF with instance ID %s does not have a management external connection point' % vnf_instance_id)
            return mgmt_addr_list

        # Building a mapping between VM group name and management interface ID
        vm_group_name_mgmt_if_id = dict()
        vdu_list = vnfd_xml.findall('.//{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}vnfd/'
                                    '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}vdu')
        for vdu in vdu_list:
            vdu_id = vdu.find('.//{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}id').text
            vm_group_name = '%s-%s' % (vnf_name, vdu_id)
            mgmt_if_id = vdu.find(
                './/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}internal-connection-point-descriptor'
                '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}external-connection-point-descriptor="%s"]/'
                '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}interface-id' % mgmt_cpd).text
            vm_group_name_mgmt_if_id[vm_group_name] = mgmt_if_id

        # Get the deployment XML from ESC
        try:
            esc_deployment_xml = self.esc.get(('xpath',
                                               '/esc_datamodel/opdata/tenants/tenant[name="%s"]/'
                                                   'deployments[deployment_name="%s"]/vm_group'
                                                    % (tenant_name, deployment_name))).data_xml
            esc_deployment_xml = etree.fromstring(esc_deployment_xml)
        except NCClientError as e:
            LOG.debug('Error occurred while communicating with the ESC Netconf server')
            LOG.exception(e)
            raise CiscoNFVManoAdapterError(e.message)

        # Get the address corresponding to the management interface ID for each VNFC from the ESC
        for vm_group_name, mgmt_if_id in vm_group_name_mgmt_if_id.items():
            try:
                mgmt_ip_addr_list = esc_deployment_xml.findall('.//{http://www.cisco.com/esc/esc}vm_group'
                                                               '[{http://www.cisco.com/esc/esc}name="%s"]/'
                                                               '{http://www.cisco.com/esc/esc}vm_instance/'
                                                               '{http://www.cisco.com/esc/esc}interfaces/'
                                                               '{http://www.cisco.com/esc/esc}interface'
                                                               '[{http://www.cisco.com/esc/esc}nicid="%s"]/'
                                                               '{http://www.cisco.com/esc/esc}ip_address'
                                                               % (vm_group_name, mgmt_if_id))
                for mgmt_addr in mgmt_ip_addr_list:
                    mgmt_addr_list.append(mgmt_addr.text)
            except AttributeError as e:
                LOG.debug('Management IP address not available for vm_group %s' % '')
                LOG.exception(e)
                raise CiscoNFVManoAdapterError(e.message)

        return mgmt_addr_list

    @log_entry_exit(LOG)
    def ns_update(self, ns_instance_id, update_type, add_vnf_instance=None, remove_vnf_instance_id=None,
                  instantiate_vnf_data=None, change_vnf_flavour_data=None, operate_vnf_data=None,
                  modify_vnf_info_data=None, change_ext_vnf_connectivity_data=None, add_sap=None, remove_sap_id=None,
                  add_nested_ns_id=None, remove_nested_ns_id=None, assoc_new_nsd_version_data=None,
                  move_vnf_instance_data=None, add_vnffg=None, remove_vnffg_id=None, update_vnffg=None,
                  change_ns_flavour_data=None, update_time=None):
        if update_type == 'OperateVnf':
            operation_list = []
            for update_data in operate_vnf_data:
                vnf_instance_id = update_data.vnf_instance_id
                change_state_to = update_data.change_state_to
                stop_type = update_data.stop_type
                graceful_stop_timeout = update_data.graceful_stop_timeout
                additional_param = update_data.additional_param
                operation_id = self.vnf_operate(vnf_instance_id, change_state_to, stop_type, graceful_stop_timeout,
                                                additional_param)
                operation_list.append(operation_id)

            lifecycle_operation_occurrence_id = uuid.uuid4()
            lifecycle_operation_occurrence_dict = {
                'operation_type': 'multiple_operations',
                'resource_id': operation_list
            }
            self.lifecycle_operation_occurrence_ids[
                lifecycle_operation_occurrence_id] = lifecycle_operation_occurrence_dict

            return lifecycle_operation_occurrence_id

    @log_entry_exit(LOG)
    def validate_vnf_instantiation_level(self, vnf_info, target_instantiation_level_id, additional_param=None):
        tenant_name = additional_param['tenant']
        deployment_name, vnf_name = self.vnf_instance_id_metadata[vnf_info.vnf_instance_id]

        # Get the VNFD XML
        vnfd_id = vnf_info.vnfd_id
        vnfd_xml = self.get_vnfd(vnfd_id)
        vnfd_xml = etree.fromstring(vnfd_xml)

        # Get the deployment XML
        try:
            deployment_xml = self.nso.get(('xpath',
                                           '/nfvo/vnf-info/esc/vnf-deployment[tenant="%s"][deployment-name="%s"]'
                                           % (tenant_name, deployment_name))).data_xml
            deployment_xml = etree.fromstring(deployment_xml)
        except NCClientError as e:
            LOG.debug('Error occurred while communicating with the ESC Netconf server')
            LOG.exception(e)
            raise CiscoNFVManoAdapterError(e.message)

        # Get the deployment flavor name
        try:
            deployment_flavor = deployment_xml.find(
                './/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}vnf-info/'
                '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}name="%s"]/'
                '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}vnfd-flavor' % vnf_name).text
        except AttributeError as e:
            LOG.exception(e)
            raise CiscoNFVManoAdapterError(e.message)

        # Find the current instantiation level ID
        try:
            current_instantiation_level_id = deployment_xml.find(
                './/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}vnf-info/'
                '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}name="%s"]/'
                '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}instantiation-level' % vnf_name).text
        except AttributeError as e:
            LOG.exception(e)
            raise CiscoNFVManoAdapterError(e.message)

        # Create dictionary with expected number of VNFC instances for each VDU
        expected_vnfc_count = dict()
        try:
            vdu_id_list = vnfd_xml.findall('.//{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}vdu/'
                                           '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}id')
        except AttributeError as e:
            LOG.exception(e)
            raise CiscoNFVManoAdapterError(e.message)

        for vdu_id in vdu_id_list:
            # Try to get the number of instances for the current VDU ID in the target instantiation level.
            # If AttributeError exception is raised, get it from the current instantiation level.
            try:
                number_of_instances = vnfd_xml.find(
                    './/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}deployment-flavor'
                    '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}id="%s"]/'
                    '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}instantiation-level'
                    '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}id="%s"]/'
                    '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}vdu-level'
                    '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}vdu="%s"]/'
                    '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}number-of-instances'
                    % (deployment_flavor, target_instantiation_level_id, vdu_id.text)).text
            except AttributeError:
                number_of_instances = vnfd_xml.find(
                    './/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}deployment-flavor'
                    '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}id="%s"]/'
                    '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}instantiation-level'
                    '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}id="%s"]/'
                    '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}vdu-level'
                    '[{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}vdu="%s"]/'
                    '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo}number-of-instances'
                    % (deployment_flavor, current_instantiation_level_id, vdu_id.text)).text

            # Update the expected VNFC count dictionary
            expected_vnfc_count[vdu_id.text] = int(number_of_instances)

        # Create dictionary with actual number of VNFC instances for each VDU
        actual_vnfc_count = defaultdict(int)
        for vnfc_resource_info in vnf_info.instantiated_vnf_info.vnfc_resource_info:
            vdu_id = vnfc_resource_info.vdu_id
            actual_vnfc_count[vdu_id] += 1

        # Compare actual values with expected values
        for vdu_id in expected_vnfc_count:
            LOG.debug('Expected number of VNFC instances deployed after VDU %s: %s; actual number: %s'
                      % (vdu_id, expected_vnfc_count[vdu_id], actual_vnfc_count[vdu_id]))
            if actual_vnfc_count[vdu_id] != expected_vnfc_count[vdu_id]:
                return False

        return True
