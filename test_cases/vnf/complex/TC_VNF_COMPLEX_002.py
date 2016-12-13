from utils.logging_module import LoggingClass
from api.generic.vnfm import Vnfm
import time

# Instantiate logger
logger_object = LoggingClass(__name__, "TC_VNF_COMPLEX_002.log")


def tc_vnf_complex_002_body(logger):
    """
    TC_VNF_COMPLEX_002 Stop a max scale-up/scaled-out VNF instance in state Active under max traffic load

    Sequence:
    1. Create VNF ID
    2. Instantiate VNF
    3. Validate VNF state is Inactive
    4. Start VNF
    5. Validate VNF state is Active
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
    17. Calculate the time to stop a max scaled VNF under load (-> last arrival time stamp)
    """

    logger.write_info("Starting TC_VNF_COMPLEX_002")

    max_operation_time = 3
    max_vnf_instantiation_time = 3
    max_vnf_activation_time = 3
    vnfm = Vnfm(vendor="dummy", logger=logger)

    # ------------------------------------------------------------------------------------------------------------------
    # 1. Create VNF ID
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Creating VNF ID")
    vnf_instance_id = vnfm.vnf_create_id(vnfd_id="1234",
                                         vnf_instance_name="test_vnf",
                                         vnf_instance_description="VNF used for testing")

    # ------------------------------------------------------------------------------------------------------------------
    # 2. Instantiate VNF
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Instantiating VNF")
    life_cycle_operation_occurrence_id = vnfm.vnf_instantiate(vnf_instance_id=vnf_instance_id, flavour_id="12345")

    # Check the status of the operation
    for time_index in xrange(1, max_operation_time+1):
        status = vnfm.get_operation(life_cycle_operation_occurrence_id)
        if status == "Successfully done":
            break
        if status == "Failed":
            logger.write_error("TC_VNF_COMPLEX_002 execution failed")
            logger.write_debug("The status of the instantiation operation was Failed")
            tc_vnf_complex_002_cleanup(logger)
            return
        if time_index == max_operation_time:
            logger.write_error("TC_VNF_COMPLEX_002 execution failed")
            logger.write_debug("The status of the instantiation operation was %s, waited %s seconds" % (status, max_operation_time))
            tc_vnf_complex_002_cleanup(logger)
            return
        logger.write_debug("Sleeping one second")
        time.sleep(1)

    # ------------------------------------------------------------------------------------------------------------------
    # 3. Validate VNF state is Inactive
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Validating VNF state is Inactive")
    for time_index in xrange(1, max_vnf_instantiation_time+1):
        vnf_instantiatiob_state = vnfm.vnf_query(vnf_instance_id, "instantiation_state")
        if vnf_instantiatiob_state == "INSTANTIATED":
            break
        if time_index == max_vnf_instantiation_time:
            logger.write_error("TC_VNF_COMPLEX_002 execution failed")
            logger.write_debug("The VNF instantiation state was %s, waited %s seconds" % (vnf_instantiatiob_state, max_vnf_instantiation_time))
            tc_vnf_complex_002_cleanup(logger)
            return
        logger.write_debug("Sleeping one second")
        time.sleep(1)

    # ------------------------------------------------------------------------------------------------------------------
    # 4. Start VNF
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Starting VNF")
    # TODO by Raluca

    # ------------------------------------------------------------------------------------------------------------------
    # 4. Validate VNF state is Active
    # ------------------------------------------------------------------------------------------------------------------
    logger.write_info("Validating VNF state is Active")

    for time_index in xrange(1, max_vnf_activation_time+1):
        vnf_state = vnfm.vnf_query(vnf_instance_id, "vnf_state")
        if vnf_state == "STARTED":
            break
        if time_index == max_vnf_activation_time:
            logger.write_error("TC_VNF_COMPLEX_002 execution failed")
            logger.write_debug("The VNF state was %s, waited %s seconds" % (vnf_state, max_vnf_activation_time))
            tc_vnf_complex_002_cleanup(logger)
            return
        logger.write_debug("Sleeping one second")
        time.sleep(1)




    logger.write_info("TC_VNF_COMPLEX_002 execution completed successfully")

    tc_vnf_complex_002_cleanup(logger)

    return


def tc_vnf_complex_002_cleanup(logger):
    logger.write_info("Starting cleanup for TC_VNF_COMPLEX_002")
    logger.write_info("Finished cleanup for TC_VNF_COMPLEX_002")
    logger.close_handlers()

if __name__ == "__main__":
    tc_vnf_complex_002_body(logger_object)
