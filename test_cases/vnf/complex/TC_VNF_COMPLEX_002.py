from utils.logging_module import LoggingClass
from api.generic.vnfm import Vnfm
from api.generic.vnf import Vnf
from api.generic.tools import check_operation_status
from datetime import datetime

# Instantiate logger
logger_object = LoggingClass(__name__, "TC_VNF_COMPLEX_002.log")


def tc_vnf_complex_002_body(logger, tc_input):
    """
    TC_VNF_COMPLEX_002 Stop a max scale-up/scaled-out VNF instance in state Active under max traffic load

    Sequence:
    1. Create VNF ID
    2. Instantiate VNF
    3. Validate VNF instantiation state is INSTANTIATED
    4. Start VNF
    5. Validate VNF state is STARTED
    6. Generate low traffic load
    7. Validate that traffic flows through without issues (-> no dropped packets)
    8. Trigger a resize of the NFV resources to reach the maximum
    9. Validate VNF has resized to the max and has max capacity
    10. Generate max traffic load to load all VNF instances
    11. Validate all traffic flows through and has reached max capacity
    12. Clear counters
    13. Stop the VNF (--> time stamp)
    14. Validate VNF has been stopped (--> time stamp)
    15. Validate no traffic flows through (--> last arrival time stamp)
    16. Stop traffic
    17. Calculate the time to stop a max scaled VNF under load (--> last arrival time stamp)

    :param logger:      Reference to the logger object.
    :param tc_input:    Reference to the test case input file.
    :return:            Dictionary containing test case results.
    """

    logger.write_info("Starting TC_VNF_COMPLEX_002")

    vnfm = Vnfm(vendor=tc_input['vnfm_vendor'], logger=logger)
    vnf = Vnf(vendor=tc_input['vnf_vendor'], logger=logger)

    tc_result = {'overall_status': 'Success',
                 'error_info': 'No errors',
                 'timeRecord': {'startVNFStart': None, 'stopVNFStart': None, 'stopVNFEnd': None}}

    # ------------------------------------------------------------------------------------------------------------------
    # 1. Create VNF ID
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Creating VNF ID")
    vnf_instance_id = vnfm.vnf_create_id(vnfd_id="vnfd_id",
                                         vnf_instance_name="test_vnf",
                                         vnf_instance_description="VNF used for testing")

    # ------------------------------------------------------------------------------------------------------------------
    # 2. Instantiate VNF
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Instantiating VNF")
    instantiation_operation_id = vnfm.vnf_instantiate(vnf_instance_id=vnf_instance_id, flavour_id="123456")

    # Check the status of the instantiation operation
    if not check_operation_status(logger, vnfm.get_operation, instantiation_operation_id, "Successfully done"):
        logger.write_error("TC_VNF_COMPLEX_002 execution failed")
        logger.write_debug("Unexpected status for the instantiation operation")
        tc_vnf_complex_002_cleanup(logger)
        tc_result['overall_status'] = 'Fail'
        tc_result['error_info'] = 'Unexpected status for the instantiation operation'
        return tc_result

    # ------------------------------------------------------------------------------------------------------------------
    # 3. Validate VNF instantiation state is INSTANTIATED
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Validating VNF instantiation state is INSTANTIATED")
    vnf_instantiation_state = vnfm.vnf_query(vnf_instance_id, "instantiation_state")
    if vnf_instantiation_state != "INSTANTIATED":
        logger.write_error("TC_VNF_COMPLEX_002 execution failed")
        logger.write_debug("The VNF instantiation state was %s, expected INSTANTIATED" % vnf_instantiation_state)
        tc_vnf_complex_002_cleanup(logger)
        tc_result['overall_status'] = 'Fail'
        return tc_result

    # ------------------------------------------------------------------------------------------------------------------
    # 4. Start VNF
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Starting VNF")
    life_cycle_operation_occurrence_id = vnfm.vnf_change_state(vnf_instance_id=vnf_instance_id, change_state_to="start")
    tc_result['timeRecord']['stopVNFStart'] = datetime.utcnow()

    # Check the status of the starting operation
    if not check_operation_status(logger, vnfm.get_operation, instantiation_operation_id, "Successfully done"):
        logger.write_error("TC_VNF_COMPLEX_002 execution failed")
        logger.write_debug("Unexpected status for starting operation")
        tc_vnf_complex_002_cleanup(logger)
        tc_result['overall_status'] = 'Fail'
        tc_result['error_info'] = 'Unexpected status for starting operation'
        return tc_result

    # ------------------------------------------------------------------------------------------------------------------
    # 5. Validate VNF state is STARTED
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Validating VNF state is STARTED")
    vnf_state = vnfm.vnf_query(vnf_instance_id, "vnf_state")
    if vnf_state != "STARTED":
        logger.write_error("TC_VNF_COMPLEX_002 execution failed")
        logger.write_debug("The VNF state was %s, expected STARTED" % vnf_state)
        tc_vnf_complex_002_cleanup(logger)
        tc_result['overall_status'] = 'Fail'
        tc_result['error_info'] = 'The VNF state was %s, expected STARTED' % vnf_state
        return tc_result

    # ------------------------------------------------------------------------------------------------------------------
    # 6. Validate that traffic flows through without issues
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Validating that traffic flows through without issues")

    # ------------------------------------------------------------------------------------------------------------------
    # 7. Trigger a resize of the NFV resources to reach the maximum
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Triggering a resize of the NFV resources to reach the maximum")
    trigger_successful = False
    if tc_input['scaling_trigger'] == "command_to_vnfm":
        trigger_operation_id = vnfm.vnf_scale_to_level(vnf_instance_id=vnf_instance_id,
                                                       instantiation_level_id="max_level_id")

        # Get the status of the instantiation operation
        trigger_successful = check_operation_status(logger,
                                                    vnfm.get_operation,
                                                    trigger_operation_id,
                                                    "Successfully done")
    elif tc_input['scaling_trigger'] == "triggered_by_vnf":
        trigger_operation_id = vnf.scale_to_level(vnf_instance_id=vnf_instance_id,
                                                  instantiation_level_id="max_level_id")
        # Get the status of the instantiation operation
        trigger_successful = check_operation_status(logger,
                                                    vnf.get_operation,
                                                    trigger_operation_id,
                                                    "Successfully done")
    # Check the status of the instantiation operation
    if not trigger_successful:
        logger.write_error("TC_VNF_COMPLEX_002 execution failed")
        logger.write_debug("Unexpected status for the triggering operation")
        tc_vnf_complex_002_cleanup(logger)
        tc_result['overall_status'] = 'Fail'
        tc_result['error_info'] = 'Unexpected status for the triggering operation'
        return tc_result

    # ------------------------------------------------------------------------------------------------------------------
    # 8. Validate VNF has resized to the max and has max capacity
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Validating VNF has resized to the max and has max capacity")
    # TODO

    # ------------------------------------------------------------------------------------------------------------------
    # 9. Generate max traffic load to load all VNF instances
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Generating max traffic load to load all VNF instances")
    # TODO

    # ------------------------------------------------------------------------------------------------------------------
    # 10. Validate all traffic flows through and has reached max capacity
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Validating all traffic flows through and has reached max capacity")
    # TODO

    # ------------------------------------------------------------------------------------------------------------------
    # 11. Clear counters
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Clearing counters")
    # TODO

    # ------------------------------------------------------------------------------------------------------------------
    # 12. Stop the VNF (--> time stamp)
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Stopping the VNF")
    life_cycle_operation_occurrence_id = vnfm.vnf_change_state(vnf_instance_id=vnf_instance_id, change_state_to="stop")
    tc_result['timeRecord']['stopVNFStart'] = datetime.utcnow()

    # Check the status of the stopping operation
    if not check_operation_status(logger, vnfm.get_operation, instantiation_operation_id, "Successfully done"):
        logger.write_error("TC_VNF_COMPLEX_002 execution failed")
        logger.write_debug("Unexpected status for stopping operation")
        tc_vnf_complex_002_cleanup(logger)
        tc_result['overall_status'] = 'Fail'
        tc_result['error_info'] = 'Unexpected status for stopping operation'
        return tc_result

    # ------------------------------------------------------------------------------------------------------------------
    # 13. Validate VNF has been stopped (--> time stamp)
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Validating VNF state is STOPPED")
    vnf_state = vnfm.vnf_query(vnf_instance_id, "vnf_state")
    if vnf_state != "STOPPED":
        logger.write_error("TC_VNF_COMPLEX_002 execution failed")
        logger.write_debug("The VNF state was %s, expected STOPPED" % vnf_state)
        tc_vnf_complex_002_cleanup(logger)
        tc_result['overall_status'] = 'Fail'
        tc_result['error_info'] = 'The VNF state was %s, expected STOPPED' % vnf_state
        return tc_result

    tc_result['timeRecord']['stopVNFEnd'] = datetime.utcnow()

    # ------------------------------------------------------------------------------------------------------------------
    # 14. Validate no traffic flows through (--> last arrival time stamp)
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Validating no traffic flows through")
    # TODO

    # ------------------------------------------------------------------------------------------------------------------
    # 15. Stop traffic
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Stopping traffic")
    # TODO

    # ------------------------------------------------------------------------------------------------------------------
    # 16. Calculate the time to stop a max scaled VNF under load (--> last arrival time stamp)
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Calculating the time to stop a max scaled VNF under load")
    # TODO

    logger.write_info("TC_VNF_COMPLEX_002 execution completed successfully")

    tc_vnf_complex_002_cleanup(logger)

    return tc_result


def tc_vnf_complex_002_cleanup(logger):
    logger.write_info("Starting cleanup for TC_VNF_COMPLEX_002")
    logger.write_info("Finished cleanup for TC_VNF_COMPLEX_002")
    logger.close_handlers()

if __name__ == "__main__":
    test_case_input = {'vnfm_vendor': 'dummy',
                       'vnf_vendor': 'dummy',
                       'scaling_trigger': 'triggered_by_vnf'}
    tc_vnf_complex_002_body(logger_object, test_case_input)
