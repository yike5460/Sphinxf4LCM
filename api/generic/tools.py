import time


def check_operation_status(logger, function_get_status, operation_id, expected_status, wait_time=3, interval=1, *args):
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
        logger.write_debug("Expected operation status %s, actual operation status %s" % (expected_status, status))
        if status == expected_status:
            return True
        if time_index == wait_time:
            logger.write_debug("The status of the operation is %s, waited %s seconds" % (status, wait_time))
            return False
        logger.write_debug("Sleeping %s second(s)" % interval)
        time.sleep(interval)
