import logging
import uuid
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

SEPARATOR = '###'

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
                        <name>%(vnfd_id)s</name>
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

DAY0_TEMPLATE = """
                            <day0>
                                <destination>%(day0_dest)s</destination>
                                <url>%(day0_url)s</url>
                            </day0>"""

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
                             %(dhcp)s
                             <subnet>
                                 <network>%(network)s</network>
                                 <gateway>%(gateway)s</gateway>
                             </subnet>
                        </virtual-link>'''

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

VNF_INFO_TEMPLATE = '''
        <vnf-info>
            <name>%(vnf_name)s</name>
            <vnfd>%(vnfd_id)s</vnfd>
            %(vdu_list)s
            <tenant>%(tenant)s</tenant>
            <deployment-name>%(deployment_name)s</deployment-name>
            <esc>%(esc)s</esc>
        </vnf-info>'''

NS_VDU_TEMPLATE = '''
            <vdu>
                <id>%(vdu_id)s</id>
                <bootup-time>%(bootup_time)s</bootup-time>
                <recovery-wait-time>%(recovery_wait_time)s</recovery-wait-time>
                <image-name>%(image_name)s</image-name>
                <flavor-name>%(flavor_name)s</flavor-name>
                %(day0_config)s
            </vdu>'''

VL_INFO_TEMPLATE = '''
        <virtual-link-info>
            <virtual-link-descriptor>%(vl_id)s</virtual-link-descriptor>
            %(dhcp)s
            <subnet>
                <network>%(network)s</network>
                <gateway>%(gateway)s</gateway>
            </subnet>
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
                <ns-info xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0"
                        nc:operation="delete">
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
            tenant_name = operation_details['tenant_name']
            deployment_name = operation_details['deployment_name']

        if operation_type == 'vnf_instantiate':
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
                # So far the ESC reports the VNF as un-deployed. Check the NSO reports the same.
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
            # Try to retrieve the VNF deployment name from the ESC.
            try:
                xml = self.esc.get(('xpath',
                                    '/esc_datamodel/opdata/tenants/tenant[name="%s"]/'
                                        'deployments[deployment_name="%s"]/''state_machine/state' %
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
            # Try to retrieve the VNF deployment name from the ESC.
            try:
                xml = self.esc.get(('xpath',
                                    '/esc_datamodel/opdata/tenants/tenant[name="%s"]/'
                                        'deployments[deployment_name="%s"]/''state_machine/state' %
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
            if nso_ns_deployment_state == 'reached' and nso_deployment_state == 'reached' \
                    and esc_deployment_state == 'SERVICE_ACTIVE_STATE':
                return constants.OPERATION_SUCCESS
            return constants.OPERATION_FAILED

        if operation_type == 'ns_terminate':
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
                # So far the ESC reports the deployment as un-deployed. Check the NSO reports the deployment as
                # un-deployed.
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
                    # Check the NSO reports the NS as un-deployed
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

        raise CiscoNFVManoAdapterError('Cannot get operation status for operation type %s' % operation_type)

    @log_entry_exit(LOG)
    def vnf_query(self, filter, attribute_selector=None):
        vnf_instance_id = filter['vnf_instance_id']
        if SEPARATOR in vnf_instance_id:
            deployment_name, vnf_name = vnf_instance_id.split(SEPARATOR)
        else:
            deployment_name, vnf_name = vnf_instance_id, None
        tenant_name = filter['additional_param']['tenant']
        vnf_info = VnfInfo()
        vnf_info.vnf_instance_id = vnf_instance_id.encode()

        # Try to retrieve the instantiation state for the VNF with the given deployment name. If the AttributeError
        # exception is raised, report the VNF instantiation state as NOT_INSTANTIATED.
        try:
            xml = self.nso.get(('xpath',
                                '/nfvo/vnf-info/esc/vnf-deployment[deployment-name="%s"]/plan/component[name="self"]/'
                                    'state[name="ncs:ready"]/status' % deployment_name)).data_xml
            xml = etree.fromstring(xml)
            nso_vnf_deployment_state = xml.find(
                './/{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}state/'
                '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}status').text
        except AttributeError:
            vnf_info.instantiation_state = constants.VNF_NOT_INSTANTIATED
            return vnf_info
        except Exception as e:
            LOG.exception(e)
            raise CiscoNFVManoAdapterError(e.message)

        # Get the VNF state from the ESC
        try:
            xml = self.esc.get(('xpath',
                                '/esc_datamodel/opdata/tenants/tenant[name="%s"]/deployments[deployment_name="%s"]/'
                                    'state_machine/state' % (tenant_name, deployment_name))).data_xml
            xml = etree.fromstring(xml)
            esc_vnf_deployment_state = xml.find(
                './/{http://www.cisco.com/esc/esc}state_machine/{http://www.cisco.com/esc/esc}state').text
        except Exception as e:
            LOG.exception(e)
            raise CiscoNFVManoAdapterError(e.message)

        # Get the VNFD ID from the NSO
        if vnf_name is not None:
            xpath = '/nfvo/vnf-info/esc/vnf-deployment[deployment-name="%s"]/vnf-info[name="%s"]/vnfd' \
                    % (deployment_name, vnf_name)
        else:
            xpath = '/nfvo/vnf-info/esc/vnf-deployment[deployment-name="%s"]/vnf-info/vnfd' % deployment_name
        xml = self.nso.get(('xpath', xpath)).data_xml
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
        vnf_info.instantiation_state = constants.VNF_INSTANTIATION_STATE['NSO_DEPLOYMENT_STATE'][
            nso_vnf_deployment_state]

        # Build the InstantiatedVnfInfo information element only if the VNF instantiation state is INSTANTIATED
        if vnf_info.instantiation_state == constants.VNF_INSTANTIATED:
            vnf_info.instantiated_vnf_info = InstantiatedVnfInfo()
            vnf_info.instantiated_vnf_info.vnf_state = constants.VNF_STATE['ESC_DEPLOYMENT_STATE'][
                esc_vnf_deployment_state]

            # Initialize the VnfcResourceInfo list
            vnf_info.instantiated_vnf_info.vnfc_resource_info = list()

            # Initialize the VnfExtCpInfo list
            vnf_info.instantiated_vnf_info.ext_cp_info = list()

            # Get the deployment XML from the ESC
            deployment_xml = self.esc.get(('xpath',
                                           '/esc_datamodel/opdata/tenants/tenant[name="%s"]/'
                                               'deployments[deployment_name="%s"]' %
                                               (tenant_name, deployment_name))).data_xml
            deployment_xml = etree.fromstring(deployment_xml)

            # Get the VM group list from the deployment XML
            vm_group_list = deployment_xml.findall('.//{http://www.cisco.com/esc/esc}vm_group/'
                                                   '{http://www.cisco.com/esc/esc}name')
            for vm_group in vm_group_list:
                vm_group_text = vm_group.text
                # Assuming that the VDU ID does not contain character '-'.
                vm_group_text_prefix, vm_group_text_suffix = vm_group.text.rsplit('-', 1)
                if vnf_name is not None and vnf_name != vm_group_text_prefix:
                    continue
                # Find all VM IDs in this VM group
                vm_id_list = deployment_xml.findall(
                    './/{http://www.cisco.com/esc/esc}vm_group[{http://www.cisco.com/esc/esc}name="%s"]/'
                    '{http://www.cisco.com/esc/esc}vm_instance/{http://www.cisco.com/esc/esc}vm_id' % vm_group_text)

                # Iterate over the VM IDs in this VM group
                for vm_id in vm_id_list:
                    vm_id_text = vm_id.text

                    # Get the VM name
                    name = deployment_xml.find('.//{http://www.cisco.com/esc/esc}vm_group'
                                               '[{http://www.cisco.com/esc/esc}name="%s"]/'
                                               '{http://www.cisco.com/esc/esc}vm_instance'
                                               '[{http://www.cisco.com/esc/esc}vm_id="%s"]/'
                                               '{http://www.cisco.com/esc/esc}name' % (vm_group_text, vm_id_text))
                    name_text = name.text

                    # Build the VnfcResourceInfo data structure
                    vnfc_resource_info = VnfcResourceInfo()
                    vnfc_resource_info.vnfc_instance_id = name_text
                    vnfc_resource_info.vdu_id = vm_group_text_suffix

                    vnfc_resource_info.compute_resource = ResourceHandle()
                    # Cisco ESC only support one VIM. Hardcode the VIM ID to string 'default_vim'
                    vnfc_resource_info.compute_resource.vim_id = 'default_vim'
                    vnfc_resource_info.compute_resource.resource_id = vm_id_text

                    # Append the current VnfvResourceInfo element to the VnfcResourceInfo list
                    vnf_info.instantiated_vnf_info.vnfc_resource_info.append(vnfc_resource_info)

                    # Get the list NIC IDs for this VM instance
                    nic_id_list = deployment_xml.findall('.//{http://www.cisco.com/esc/esc}vm_group'
                                                         '[{http://www.cisco.com/esc/esc}name="%s"]/'
                                                         '{http://www.cisco.com/esc/esc}vm_instance'
                                                         '[{http://www.cisco.com/esc/esc}vm_id="%s"]/'
                                                         '{http://www.cisco.com/esc/esc}interfaces/'
                                                         '{http://www.cisco.com/esc/esc}interface/'
                                                         '{http://www.cisco.com/esc/esc}nicid'
                                                         % (vm_group_text, vm_id_text))

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
                            % (vm_group_text_suffix, nic_id_text))
                        cpd_id_text = cpd_id.text

                        # Get the port ID
                        port_id = deployment_xml.find('.//{http://www.cisco.com/esc/esc}vm_group'
                                                      '[{http://www.cisco.com/esc/esc}name="%s"]/'
                                                      '{http://www.cisco.com/esc/esc}vm_instance'
                                                      '[{http://www.cisco.com/esc/esc}vm_id="%s"]/'
                                                      '{http://www.cisco.com/esc/esc}interfaces/'
                                                      '{http://www.cisco.com/esc/esc}interface'
                                                      '[{http://www.cisco.com/esc/esc}nicid="%s"]/'
                                                      '{http://www.cisco.com/esc/esc}port_id'
                                                      % (vm_group_text, vm_id_text, nic_id_text))
                        port_id_text = port_id.text

                        # Get the IP address
                        ip_address = deployment_xml.find('.//{http://www.cisco.com/esc/esc}vm_group'
                                                         '[{http://www.cisco.com/esc/esc}name="%s"]/'
                                                         '{http://www.cisco.com/esc/esc}vm_instance'
                                                         '[{http://www.cisco.com/esc/esc}vm_id="%s"]/'
                                                         '{http://www.cisco.com/esc/esc}interfaces/'
                                                         '{http://www.cisco.com/esc/esc}interface'
                                                         '[{http://www.cisco.com/esc/esc}nicid="%s"]/'
                                                         '{http://www.cisco.com/esc/esc}ip_address'
                                                         % (vm_group_text, vm_id_text, nic_id_text))
                        ip_address_text = ip_address.text

                        # Get the IP address
                        mac_address = deployment_xml.find('.//{http://www.cisco.com/esc/esc}vm_group'
                                                          '[{http://www.cisco.com/esc/esc}name="%s"]/'
                                                          '{http://www.cisco.com/esc/esc}vm_instance'
                                                          '[{http://www.cisco.com/esc/esc}vm_id="%s"]/'
                                                          '{http://www.cisco.com/esc/esc}interfaces/'
                                                          '{http://www.cisco.com/esc/esc}interface'
                                                          '[{http://www.cisco.com/esc/esc}nicid="%s"]/'
                                                          '{http://www.cisco.com/esc/esc}mac_address'
                                                          % (vm_group_text, vm_id_text, nic_id_text))
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

    def validate_vnf_allocated_vresources(self, vnf_instance_id, additional_param):
        vnf_info = self.vnf_query(filter={'vnf_instance_id': vnf_instance_id, 'additional_param': additional_param})
        vnfd_id = vnf_info.vnfd_id
        vnfd = self.get_vnfd(vnfd_id)
        vnfd = etree.fromstring(vnfd)

        if SEPARATOR in vnf_instance_id:
            deployment_name, _ = vnf_instance_id.split(SEPARATOR)
        else:
            deployment_name = vnf_instance_id

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
            flavor_name_nova = flavor_details['name'].encode()

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
            day0_config_template_values = {'day0_dest': day0_config['destination'],
                                           'day0_url': day0_config['url']}
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
                'dhcp': '<dhcp/>' if vl_param.get('dhcp', False) is True else '',
                'network': vl_param['subnet']['network'],
                'gateway': vl_param['subnet']['gateway']
            }

            vl_xml = VL_TEMPLATE % vl_template_values
            vl_list_xml += vl_xml

        return vl_list_xml

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
    def vnf_create_id(self, vnfd_id, vnf_instance_name=None, vnf_instance_description=None):
        vnf_instance_id = vnf_instance_name
        self.vnf_vnfd_mapping[vnf_instance_id] = vnfd_id

        return vnf_instance_id

    @log_entry_exit(LOG)
    def vnf_instantiate(self, vnf_instance_id, flavour_id, instantiation_level_id=None, ext_virtual_link=None,
                        ext_managed_virtual_link=None, localization_language=None, additional_param=None):

        vnfr_xml = self.build_vnfr(vnf_instance_id, flavour_id, instantiation_level_id, additional_param)
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
            'deployment_name': vnf_instance_id
        }
        self.lifecycle_operation_occurrence_ids[lifecycle_operation_occurrence_id] = lifecycle_operation_occurrence_dict

        return lifecycle_operation_occurrence_id

    @log_entry_exit(LOG)
    def vnf_terminate(self, vnf_instance_id, termination_type, graceful_termination_timeout=None,
                      additional_param=None):
        vnfr_delete_xml = self.build_vnfr_delete(vnf_instance_id, additional_param)

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

        try:
            netconf_reply = self.esc.dispatch(rpc_command=etree.fromstring(vnf_operate_xml))
        except NCClientError as e:
            LOG.exception(e)
            raise CiscoNFVManoAdapterError(e.message)

        if '<ok/>' not in netconf_reply.xml:
            raise CiscoNFVManoAdapterError('ESC replied with an error')

        LOG.debug('NSO reply: %s' % netconf_reply.xml)

        lifecycle_operation_occurrence_id = uuid.uuid4()
        lifecycle_operation_occurrence_dict = {
            'operation_type': 'vnf_%s' % change_state_to,
            'tenant_name': additional_param['tenant'],
            'deployment_name': vnf_instance_id
        }
        self.lifecycle_operation_occurrence_ids[lifecycle_operation_occurrence_id] = lifecycle_operation_occurrence_dict

        return lifecycle_operation_occurrence_id

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
    def build_vnf_info_list(self, ns_instance_id, vnf_info_params):
        vnf_info_list_xml = ''
        for vnf_name, vnf_param in vnf_info_params.items():
            vnf_info_template_values = {
                'vnf_name': vnf_name,
                'vnfd_id': vnf_param['vnfd_id'],
                'tenant': vnf_param['tenant'],
                'vdu_list': self.build_vdu_list(vnf_param['vdu']),
                'deployment_name': ns_instance_id,
                'esc': vnf_param['esc']
            }

            vnf_info_xml = VNF_INFO_TEMPLATE % vnf_info_template_values
            vnf_info_list_xml += vnf_info_xml

        return vnf_info_list_xml

    @log_entry_exit(LOG)
    def build_vl_info_list(self, vl_info_params):
        vl_info_list_xml = ''
        for vl_id, vl_param in vl_info_params.items():
            vl_info_template_values = {
                'vl_id': vl_id,
                'dhcp': '<dhcp/>' if vl_param.get('dhcp', False) is True else '',
                'network': vl_param['subnet']['network'],
                'gateway': vl_param['subnet']['gateway']
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
            'vnf_info_list': self.build_vnf_info_list(ns_instance_id, additional_param_for_ns['vnf_info']),
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
        # ns_info.description =
        ns_info.nsd_id = self.ns_nsd_mapping[ns_instance_id]
        ns_info.ns_state = constants.NS_INSTANTIATION_STATE['NSO_DEPLOYMENT_STATE'][nso_ns_deployment_state]

        # Build the VnfInfo data structure for each VNF that is part of the NS
        ns_info.vnf_info = list()
        vnf_ids = nso_deployment_xml.findall('.//{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}vnf-info/'
                                             '{http://tail-f.com/pkg/tailf-etsi-rel2-nfvo-esc}name')
        for vnf_name in vnf_ids:
            vnf_info = self.vnf_query(filter={'vnf_instance_id': '%s%s%s' % (ns_instance_id, SEPARATOR, vnf_name.text),
                                              'additional_param': {'tenant': 'cisco-etsi'}})
            vnf_info.vnf_product_name = vnf_name.text
            ns_info.vnf_info.append(vnf_info)

        return ns_info

    @log_entry_exit(LOG)
    def ns_terminate(self, ns_instance_id, terminate_time=None):
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
            # TODO: ns_terminate does not have additional_param input as per IFA 13 v2.3.1. Find a way to pass the
            # tenant as input
            'tenant_name': 'cisco-etsi',
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
    def verify_vnf_sw_images(self, vnf_info):

        # TODO We must populate the tenant name in the VnfInfo structure or any other suitable structure
        tenant_name = 'cisco-etsi'
        vnf_instance_id = vnf_info.vnf_instance_id
        if SEPARATOR in vnf_instance_id:
            deployment_name, _ = vnf_instance_id.split(SEPARATOR)
        else:
            deployment_name = vnf_instance_id

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
        ns_info = self.ns_query(filter={'ns_instance_id': ns_instance_id})
        for vnf_info in ns_info.vnf_info:
            vnf_instance_id = vnf_info.vnf_instance_id
            if not self.validate_vnf_allocated_vresources(vnf_instance_id, additional_param):
                LOG.debug('For VNF instance id %s expected resources do not match the actual ones' % vnf_instance_id)
                return False

        return True
