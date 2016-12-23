import time
import logging

LOG = logging.getLogger(__name__)


def vnfinfo_get_instantiation_state(vnfinfo_dict):
    """
    This function retrieves the value for key instantiation_state is as expected in the provided vnfInfo dictionary.

    :param logger:                          Reference to the logger object.
    :param vnfinfo_dict:                    vnfInfo dictionary.
    :return:                                True if the value for key instantiation_state is as expected, False
                                            otherwise.
    """
    vnf_instantiation_state = vnfinfo_dict.get('instantiation_state')
    LOG.debug('VNF state: %s' % vnf_instantiation_state)
    return vnf_instantiation_state


def vnfinfo_get_vnf_state(vnfinfo_dict):
    """
    This function retrieves the value for key vnf_state is as expected in the provided vnfInfo dictionary.

    :param logger:              Reference to the logger object.
    :param vnfinfo_dict:        vnfInfo dictionary.
    :return:                    True if the value for key vnf_state is as expected, False otherwise.
    """
    vnf_state = vnfinfo_dict.get('instantiated_vnf_info', {}).get('vnf_state')
    LOG.debug('VNF state: %s' % vnf_state)
    return vnf_state
