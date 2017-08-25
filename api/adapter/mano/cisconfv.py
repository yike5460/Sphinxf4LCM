import logging
from xml.dom import minidom

import ncclient
from ncclient import manager
from ncclient.operations.rpc import RPC

from api.adapter.mano import ManoAdapterError
from api.adapter.mano.resources import ADD_NSD
from utils.logging_module import log_entry_exit
from utils.misc import generate_name

# Instantiate logger
LOG = logging.getLogger(__name__)


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

    @log_entry_exit(LOG)
    def vnf_create_id(self, vnfd_id, vnf_instance_name, vnf_instance_description):
        vnfd_data = self.get_vnfd_details(vnfd_id)

        # Creating temporary NSD
        try:
            nsd_id = self.create_nsd(vnfd_connection_point=vnfd_data['connection-points'], vnfd_id=vnfd_id,
                                           vnfd_flavour_id=vnfd_data['flavours'][0], vnfd_vdu_id=vnfd_data['vdus'][0])
            LOG.debug('Successfully created NSD %s' % nsd_id)
        except Exception as e:
            raise CiscoNFVManoAdapterError(e.message)

        #Instantiating NSR - ar trebui sa chemam o alta functie pentru crearea unui NSR


    @log_entry_exit(LOG)
    def create_nsr(self, nsr, vnfm, tenant, connection_point, address):
        return True

    @log_entry_exit(LOG)
    def create_nsd(self, vnfd_connection_point, vnfd_id, vnfd_flavour_id, vnfd_vdu_id):
        nsd = generate_name(vnfd_id + '-temp-nsd')
        member_vnf = vnfd_id + '-1'
        nsd_flavour_id = 'flavour1'
        config = ADD_NSD % (nsd, nsd_flavour_id, member_vnf, vnfd_id, vnfd_flavour_id, vnfd_vdu_id)
        config_xml = minidom.parseString(config)
        conn_point_name = 'a'
        for vnfd_connection in vnfd_connection_point:
            xml_connection_point = self.add_connection_point(vnfd_connection, conn_point_name, member_vnf)
            conn_point_name = chr(ord(conn_point_name) + 1)
            config_xml.getElementsByTagName('config')[0].getElementsByTagName('mano')[0].getElementsByTagName('nsd')[
                0].appendChild(xml_connection_point)
        try:
            rpc_obj = self.nso.edit_config(target='running', config=config_xml.toxml())
            if rpc_obj.ok:
                return nsd
        except Exception as e:
            raise CiscoNFVManoAdapterError(e.message)

    @log_entry_exit(LOG)
    def get_vnfd_details(self, vnfd_id):
        raw_data = self.nso.get(filter=('xpath', '/mano/vnfd[name="%s"]' % vnfd_id))
        vnfd_data = minidom.parseString(raw_data.data_xml)

        # Initialise VNFD data structures
        vnfd_info = {}
        conn_point_id_list = []
        flavour_id_list = []
        vdu_id_list = []
        vnfm_list = []

        # Populate VNFD connection-points list
        conn_points = vnfd_data.getElementsByTagName('connection-points')
        for conn_point in conn_points:
            conn_point_data = conn_point.getElementsByTagName('connection-point-id')[0]
            conn_point_id_list.append(conn_point_data.firstChild.data)
        vnfd_info['connection-points'] = conn_point_id_list

        # Populate VNFD flavours list
        flavours = vnfd_data.getElementsByTagName('flavours')[0].getElementsByTagName('flavour-id')
        for flavour in flavours:
            flavour_id_list.append(flavour.firstChild.data)
        vnfd_info['flavours'] = flavour_id_list

        # Populate VNFD VDUs list
        vdus = vnfd_data.getElementsByTagName('flavours')[0].getElementsByTagName('vdus')[0].getElementsByTagName(
            'vdu-id')
        for vdu in vdus:
            vdu_id_list.append(vdu.firstChild.data)
        vnfd_info['vdus'] = vdu_id_list

        # Populate with VNFD structure with VNFM responsible for it
        vnfms = vnfd_data.getElementsByTagName('vnfm')[0].getElementsByTagName('esc')[0].getElementsByTagName('name')
        for vnfm in vnfms:
            vnfm_list.append(vnfm.firstChild.data)
        vnfd_info['vnfm'] = vnfm_list

        return vnfd_info

    @log_entry_exit(LOG)
    def add_connection_point(self, connection_point, conn_point_name, member_vnf):
        config = "<connection-points></connection-points>"
        config_xml = minidom.parseString(config)
        for elem_name, elem_val in zip(['connection-point-id', 'member-vnf', 'vnfd-connection-point'],
                                       [conn_point_name, member_vnf, connection_point]):
            elem = config_xml.createElement(elem_name)
            val = config_xml.createTextNode(elem_val)
            if elem_name in ['member-vnf', 'vnfd-connection-point']:
                elem.setAttributeNS("", "xmlns", "http://cisco.com/yang/nso/tail-f-nsd")
            elem.appendChild(val)
            config_xml.childNodes[0].appendChild(elem)
        result = config_xml.getElementsByTagName('connection-points')[0]

        return result
