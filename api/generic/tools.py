import time
import logging

LOG = logging.getLogger(__name__)


def check_operation_status(function_get_status, operation_id, expected_status, wait_time=3, interval=1, *args):
    """
    This function check the status of a VNF lifecycle management operation is as expected.

    :param logger:              Reference to the logger object.
    :param function_get_status: Reference to function used to get the status of the operation.
    :param expected_status:     Expected state of the operation. Ex. "Processing", "Failed".
    :param operation_id:        ID of the VNF lifecycle management operation.
    :param wait_time:           Total amount time, in seconds, to wait for the operation to reach the expected state.
                                Default value 3 seconds.
    :param interval:            Interval of time, in seconds, between the checks on the operation status.
                                Default value 1 second.
    :param args:                Additional params.
    :return:                    True if the operation status is as expected, False otherwise.
    """
    for time_index in xrange(1, wait_time+1):
        status = function_get_status(operation_id)
        LOG.debug("Expected operation status %s, actual operation status %s" % (expected_status, status))
        if status == expected_status:
            return True
        if time_index == wait_time:
            LOG.debug("The status of the operation is %s, waited %s seconds" % (status, wait_time))
            return False
        LOG.debug("Sleeping %s second(s)" % interval)
        time.sleep(interval)


def vnfinfo_check_instantiation_state(vnfinfo_dict, expected_instantiation_state):
    """
    This function checks that the value for key instantiation_state is as expected in the provided vnfInfo dictionary.

    :param logger:                          Reference to the logger object.
    :param vnfinfo_dict:                    vnfInfo dictionary.
    :param expected_instantiation_state:    Expected value for key instantiation_state.
    :return:                                True if the value for key instantiation_state is as expected, False
                                            otherwise.
    """
    if 'instantiation_state' in vnfinfo_dict.keys():
        LOG.debug("Expected VNF instantiation state %s, actual instantiation state %s" %
                           (expected_instantiation_state, vnfinfo_dict['instantiation_state']))
        if vnfinfo_dict['instantiation_state'] == expected_instantiation_state:
            return True
        else:
            return False
    else:
        raise Exception("Unable to find key instantiation_state in the provided dictionary")


def vnfinfo_check_vnf_state(vnfinfo_dict, expected_vnf_state):
    """
    This function checks that the value for key vnf_state is as expected in the provided vnfInfo dictionary.

    :param logger:              Reference to the logger object.
    :param vnfinfo_dict:        vnfInfo dictionary.
    :param expected_vnf_state:  Expected value for key vnf_state.
    :return:                    True if the value for key vnf_state is as expected, False otherwise.
    """
    if 'vnf_state' in vnfinfo_dict['instantiated_vnf_info'].keys():
        LOG.debug("Expected VNF state %s, actual state %s" %
                           (expected_vnf_state, vnfinfo_dict['instantiated_vnf_info']['vnf_state']))
        if vnfinfo_dict['instantiated_vnf_info']['vnf_state'] == expected_vnf_state:
            return True
        else:
            return False
    else:
        raise Exception("Unable to find key vnf_state in the provided dictionary")
