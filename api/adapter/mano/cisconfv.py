import logging
import ncclient

from ncclient import manager

from api.adapter.mano import ManoAdapterError

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

    def __init__(self, nso_host, nso_user, nso_pass, esc_host, esc_user, esc_pass, nso_port=2022, esc_port=830):
        try:
            self.nso = ncclient.manager.connect(host=nso_host, port=nso_port, username=nso_user, password=nso_pass,
                                           hostkey_verify=False, look_for_keys=False)
            self.esc = ncclient.manager.connect(host=esc_host, port=esc_port, username=esc_user, password=esc_pass,
                                           hostkey_verify=False, look_for_keys=False)
        except Exception as e:
            LOG.error('Unable to create %s instance' % self.__class__.__name__)
            raise CiscoNFVManoAdapterError(e.message)

