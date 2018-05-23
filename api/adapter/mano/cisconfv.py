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
import uuid

import ncclient
from lxml import etree
from ncclient import manager, NCClientError

from api.adapter import construct_adapter
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
                    <tenant>%(tenant)s</tenant>
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

            self.vim_helper = None

        except Exception as e:
            LOG.exception(e)
            raise CiscoNFVManoAdapterError('Unable to create %s instance - %s' % (self.__class__.__name__, e))

        self.vnf_vnfd_mapping = dict()
        self.lifecycle_operation_occurrence_ids = dict()

    @log_entry_exit(LOG)
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        """
        This function does not have a direct mapping in Cisco NFV client so it will just return the status of the VNF
        with given ID.

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
                nso_vnf_deployment_state = xml.find(
                     './/{http://tail-f.com/pkg/tailf-nfvo-esc}state/{http://tail-f.com/pkg/tailf-nfvo-esc}status').text
                LOG.debug('VNF deployment state reported by NSO: "%s"; expected: "%s"'
                          % (nso_vnf_deployment_state, 'reached'))
            except NCClientError as e:
                LOG.exception(e)
                raise CiscoNFVManoAdapterError('Unable to communicate with the NSO Netconf server - %s' % e)
            except AttributeError as e:
                LOG.exception(e)
                raise CiscoNFVManoAdapterError('VNF deployment state not available in NSO')

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
                LOG.exception(e)
                raise CiscoNFVManoAdapterError('Unable to communicate with the ESC Netconf server - %s' % e)
            except AttributeError as e:
                LOG.exception(e)
                raise CiscoNFVManoAdapterError('VNF deployment state not available in ESC')

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
                                    '/esc_datamodel/opdata/tenants/tenant[name="%s"]/'
                                        'deployments[deployment_name="%s"]/state_machine/state' %
                                    (tenant_name, deployment_name))).data_xml
                xml = etree.fromstring(xml)
                esc_vnf_deployment_state = xml.find(
                    './/{http://www.cisco.com/esc/esc}state_machine/{http://www.cisco.com/esc/esc}state').text
                LOG.debug('VNF deployment state reported by ESC: "%s"; expected no state' % esc_vnf_deployment_state)
                if esc_vnf_deployment_state == 'SERVICE_ERROR_STATE':
                    return constants.OPERATION_FAILED
                else:
                    return constants.OPERATION_PENDING
            except NCClientError as e:
                LOG.exception(e)
                raise CiscoNFVManoAdapterError('Unable to communicate with the ESC Netconf server - %s' % e)
            except AttributeError:
                # So far the ESC reports the VNF as un-deployed. Check the NSO reports the same.
                try:
                    xml = self.nso.get(('xpath',
                                        '/nfvo/vnfr/esc/vnf-deployment[deployment-name="%s"]/plan/component[name="self"]'
                                            '/state[name="ncs:ready"]/status' % deployment_name)).data_xml
                    xml = etree.fromstring(xml)
                    nso_vnf_deployment_state = xml.find('.//{http://tail-f.com/pkg/tailf-nfvo-esc}state/'
                                                            '{http://tail-f.com/pkg/tailf-nfvo-esc}status').text
                    LOG.debug('VNF deployment state reported by NSO: "%s"; expected no state' % nso_vnf_deployment_state)
                    if nso_vnf_deployment_state == 'reached':
                        LOG.debug('ESC reports the VNF as un-deployed, but the NSO does not')
                        return constants.OPERATION_PENDING
                except NCClientError as e:
                    LOG.exception(e)
                    raise CiscoNFVManoAdapterError('Unable to communicate with the NSO Netconf server - %s' % e)
                except AttributeError:
                    return constants.OPERATION_SUCCESS

        if operation_type == 'vnf_stop':
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
                LOG.exception(e)
                raise CiscoNFVManoAdapterError('Unable to communicate with the ESC Netconf server - %s' % e)
            except AttributeError as e:
                LOG.exception(e)
                raise CiscoNFVManoAdapterError('VNF deployment state not available in ESC')

        if operation_type == 'vnf_start':
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
                LOG.exception(e)
                raise CiscoNFVManoAdapterError('Unable to communicate with the ESC Netconf server - %s' % e)
            except AttributeError as e:
                LOG.exception(e)
                raise CiscoNFVManoAdapterError('VNF deployment state not available in ESC')

        raise CiscoNFVManoAdapterError('Cannot get operation status for operation type %s' % operation_type)

    @log_entry_exit(LOG)
    def vnf_query(self, filter, attribute_selector=None):
        vnf_instance_id = filter['vnf_instance_id']
        tenant_name = filter['additional_param']['tenant']
        vnf_info = VnfInfo()
        vnf_info.vnf_instance_id = vnf_instance_id.encode()

        # Try to retrieve the instantiation state for the VNF with the given deployment name. If the AttributeError
        # exception is raised, report the VNF instantiation state as NOT_INSTANTIATED.
        try:
            xml = self.nso.get(('xpath',
                                '/nfvo/vnfr/esc/vnf-deployment[deployment-name="%s"]/plan/component[name="self"]/'
                                    'state[name="ncs:ready"]/status' % vnf_instance_id)).data_xml
            xml = etree.fromstring(xml)
            nso_vnf_deployment_state = xml.find(
                     './/{http://tail-f.com/pkg/tailf-nfvo-esc}state/{http://tail-f.com/pkg/tailf-nfvo-esc}status').text
        except AttributeError:
            vnf_info.instantiation_state = constants.VNF_NOT_INSTANTIATED
            return vnf_info
        except Exception as e:
            LOG.exception(e)
            raise CiscoNFVManoAdapterError('Unable to get VNF instantiation state from the NSO - %s' % e)

        # Get the VNF state from the ESC
        try:
            xml = self.esc.get(('xpath',
                                '/esc_datamodel/opdata/tenants/tenant[name="%s"]/deployments[deployment_name="%s"]/'
                                                       'state_machine/state' % (tenant_name, vnf_instance_id))).data_xml
            xml = etree.fromstring(xml)
            esc_vnf_deployment_state = xml.find(
                              './/{http://www.cisco.com/esc/esc}state_machine/{http://www.cisco.com/esc/esc}state').text
        except Exception as e:
            LOG.exception(e)
            raise CiscoNFVManoAdapterError('Unable to get VNF state from the ESC - %s' % e)

        # Get the VNFD ID from the NSO
        xml = self.nso.get(('xpath',
                            '/nfvo/vnfr/esc/vnf-deployment[deployment-name="%s"]/vnfr/id' % vnf_instance_id)).data_xml
        xml = etree.fromstring(xml)
        vnfd_id = xml.find(
            './/{http://tail-f.com/pkg/tailf-nfvo-esc}vnfr/{http://tail-f.com/pkg/tailf-nfvo-esc}id').text

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
                                                                               (tenant_name, vnf_instance_id))).data_xml
            deployment_xml = etree.fromstring(deployment_xml)

            # Get the VM group list from the deployment XML
            vm_group_list = deployment_xml.findall(
                './/{http://www.cisco.com/esc/esc}vm_group/{http://www.cisco.com/esc/esc}name')
            for vm_group in vm_group_list:
                vm_group_text = vm_group.text

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
                    vnfc_resource_info.vdu_id = vm_group_text

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
                        cpd_id = vnfd_xml.find('.//{http://tail-f.com/pkg/nfvo}vdu'
                                                   '[{http://tail-f.com/pkg/nfvo}id="%s"]/'
                                                   '{http://tail-f.com/pkg/nfvo}internal-connection-point'
                                                   '[{http://tail-f.com/pkg/tailf-nfvo-esc}interface-id="%s"]/'
                                                   '{http://tail-f.com/pkg/nfvo}id' % (vm_group_text, nic_id_text))
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

                        # Get the MAC address
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
                        vnf_ext_cp_info.address = {
                            'ip': [ip_address_text],
                            'mac': [mac_address_text]
                        }
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

    def validate_vnf_allocated_vresources(self, vnf_info, additional_param=None):
        vnf_instance_id = vnf_info.vnf_instance_id
        vnfd_id = vnf_info.vnfd_id
        vnfd = self.get_vnfd(vnfd_id)
        vnfd = etree.fromstring(vnfd)

        # Get the VNFR from the NSO
        vnfr = self.nso.get(('xpath',
                             '/nfvo/vnfr/esc/vnf-deployment[deployment-name="%s"]/vnfr' % vnf_instance_id)).data_xml
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
            flavor_name_vnfr = vnfr.find(
                './/{http://tail-f.com/pkg/tailf-nfvo-esc}vnfr/'
                    '{http://tail-f.com/pkg/tailf-nfvo-esc}vdu[{http://tail-f.com/pkg/tailf-nfvo-esc}id="%s"]/'
                    '{http://tail-f.com/pkg/tailf-nfvo-esc}flavor-name' % vdu_id).text

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
                './/{http://tail-f.com/pkg/nfvo}vdu[{http://tail-f.com/pkg/nfvo}id="%s"]/'
                    '{http://tail-f.com/pkg/nfvo}internal-connection-point' % vdu_id))

            # Check that the number of ports reported by Nova for the current VNFC is the same as the number of ports in
            # the VNFD for the VDU type that corresponds to the current VNFC type
            if port_number_nova != port_number_vnfd:
                return False

            # TODO: Check NIC type

        return True

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
        try:
            netconf_reply = self.nso.edit_config(target='running', config=vnfr_xml)
        except NCClientError as e:
            LOG.exception(e)
            raise CiscoNFVManoAdapterError('Unable to communicate with the NSO Netconf server - %s' % e)

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
            raise CiscoNFVManoAdapterError('Unable to communicate with the NSO Netconf server - %s' % e)

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
            raise CiscoNFVManoAdapterError('Unable to communicate with the ESC Netconf server - %s' % e)

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
                    'os_tenant_name': 'project_name'
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

                self.vim_helper = construct_adapter(vendor='openstack', module_type='vim', **client_params)

            else:
                raise CiscoNFVManoAdapterError('Cannot create VIM helper for unsupported type: %s' % vim_type)

        return self.vim_helper

    @log_entry_exit(LOG)
    def wait_for_vnf_stable_state(self, vnf_instance_id, max_wait_time, poll_interval):
        # Since the NSO VNF deployment state is seen as VNF instantiation state, the VNF termination is always safe, no
        # matter the VNF deployment state in the ESC.
        pass
