import logging
from utils.logging_module import configure_logger
from api.generic.vnfm import Vnfm
from api.generic.vnf import Vnf
from api.generic.tools import check_operation_status
from api.generic.tools import vnfinfo_check_instantiation_state, vnfinfo_check_vnf_state
from test_cases import TestCase
import time

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNF_COMPLEX_002(TestCase):
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
    """

    def initialize(self):
        configure_logger(LOG, file_level='DEBUG', console_level='INFO', override_parent=True)

    def run(self):
        LOG.info("Starting TC_VNF_COMPLEX_002")

        vnfm = Vnfm(vendor=self.tc_input['vnfm_vendor'])
        vnf = Vnf(vendor=self.tc_input['vnf_vendor'])

        self.tc_result = {'overall_status': 'Success',
                     'error_info': 'No errors',
                     'timeRecord': {}}

        # ------------------------------------------------------------------------------------------------------------------
        # 1. Create VNF ID
        # ------------------------------------------------------------------------------------------------------------------
        LOG.info("Creating VNF ID")
        vnf_instance_id = vnfm.vnf_create_id(vnfd_id="vnfd_id",
                                             vnf_instance_name="test_vnf",
                                             vnf_instance_description="VNF used for testing")

        # ------------------------------------------------------------------------------------------------------------------
        # 2. Instantiate VNF
        # ------------------------------------------------------------------------------------------------------------------
        LOG.info("Instantiating VNF")
        self.tc_result['timeRecord']['instantiateVNFStart'] = time.clock()
        instantiation_operation_id = vnfm.vnf_instantiate(vnf_instance_id=vnf_instance_id, flavour_id="123456")

        # Check the status of the instantiation operation
        if not check_operation_status(vnfm.get_operation_status, instantiation_operation_id, "Successfully done"):
            LOG.error("TC_VNF_COMPLEX_002 execution failed")
            LOG.debug("Unexpected status for the instantiation operation")
            self.tc_result['overall_status'] = 'Fail'
            self.tc_result['error_info'] = 'Unexpected status for the instantiation operation'
            return False

        # ------------------------------------------------------------------------------------------------------------------
        # 3. Validate VNF instantiation state is INSTANTIATED
        # ------------------------------------------------------------------------------------------------------------------
        LOG.info("Validating VNF instantiation state is INSTANTIATED")
        vnf_info = vnfm.vnf_query(vnf_instance_id)
        if not vnfinfo_check_instantiation_state(vnf_info, "INSTANTIATED"):
            LOG.error("TC_VNF_COMPLEX_002 execution failed")
            LOG.debug("Unexpected VNF instantiation state")
            self.tc_result['overall_status'] = 'Fail'
            self.tc_result['error_info'] = 'Unexpected VNF instantiation state'
            return False

        self.tc_result['timeRecord']['instantiateVNFEnd'] = time.clock()

        self.tc_result['timeRecord']['instantiateVNFTime'] = \
            round(self.tc_result['timeRecord']['instantiateVNFEnd'] - self.tc_result['timeRecord']['instantiateVNFStart'], 6)

        # ------------------------------------------------------------------------------------------------------------------
        # 4. Start VNF
        # ------------------------------------------------------------------------------------------------------------------
        LOG.info("Starting VNF")
        self.tc_result['timeRecord']['startVNFStart'] = time.clock()
        start_operation_id = vnfm.vnf_change_state(vnf_instance_id=vnf_instance_id, change_state_to="start")

        # Check the status of the starting operation
        if not check_operation_status(vnfm.get_operation_status, start_operation_id, "Successfully done"):
            LOG.error("TC_VNF_COMPLEX_002 execution failed")
            LOG.debug("Unexpected status for starting operation")
            self.tc_result['overall_status'] = 'Fail'
            self.tc_result['error_info'] = 'Unexpected status for starting operation'
            return False

        # ------------------------------------------------------------------------------------------------------------------
        # 5. Validate VNF state is STARTED
        # ------------------------------------------------------------------------------------------------------------------
        LOG.info("Validating VNF state is STARTED")
        vnf_info = vnfm.vnf_query(vnf_instance_id)
        if not vnfinfo_check_vnf_state(vnf_info, "STARTED"):
            LOG.error("TC_VNF_COMPLEX_002 execution failed")
            LOG.debug("Unexpected VNF state")
            self.tc_result['overall_status'] = 'Fail'
            self.tc_result['error_info'] = 'Unexpected VNF state'
            return False

        self.tc_result['timeRecord']['startVNFEnd'] = time.clock()

        self.tc_result['timeRecord']['StartVNFTime'] = \
            round(self.tc_result['timeRecord']['startVNFEnd'] - self.tc_result['timeRecord']['startVNFStart'], 6)

        # ------------------------------------------------------------------------------------------------------------------
        # 6. Validate that traffic flows through without issues
        # ------------------------------------------------------------------------------------------------------------------
        LOG.info("Validating that traffic flows through without issues")
        # TODO

        # ------------------------------------------------------------------------------------------------------------------
        # 7. Trigger a resize of the NFV resources to reach the maximum
        # ------------------------------------------------------------------------------------------------------------------
        LOG.info("Triggering a resize of the NFV resources to reach the maximum")
        trigger_successful = False
        if self.tc_input['scaling_trigger'] == "command_to_vnfm":
            trigger_operation_id = vnfm.vnf_scale_to_level(vnf_instance_id=vnf_instance_id,
                                                           instantiation_level_id="max_level_id")

            # Get the status of the instantiation operation
            trigger_successful = check_operation_status(vnfm.get_operation_status,
                                                        trigger_operation_id,
                                                        "Successfully done")
        elif self.tc_input['scaling_trigger'] == "triggered_by_vnf":
            trigger_operation_id = vnf.scale_to_level(vnf_instance_id=vnf_instance_id,
                                                      instantiation_level_id="max_level_id")
            # Get the status of the instantiation operation
            trigger_successful = check_operation_status(vnf.get_operation_status,
                                                        trigger_operation_id,
                                                        "Successfully done")
        # Check the status of the instantiation operation
        if not trigger_successful:
            LOG.error("TC_VNF_COMPLEX_002 execution failed")
            LOG.debug("Unexpected status for the triggering operation")
            self.tc_result['overall_status'] = 'Fail'
            self.tc_result['error_info'] = 'Unexpected status for the triggering operation'
            return False

        # ------------------------------------------------------------------------------------------------------------------
        # 8. Validate VNF has resized to the max and has max capacity
        # ------------------------------------------------------------------------------------------------------------------
        LOG.info("Validating VNF has resized to the max and has max capacity")
        # TODO

        # ------------------------------------------------------------------------------------------------------------------
        # 9. Generate max traffic load to load all VNF instances
        # ------------------------------------------------------------------------------------------------------------------
        LOG.info("Generating max traffic load to load all VNF instances")
        # TODO

        # ------------------------------------------------------------------------------------------------------------------
        # 10. Validate all traffic flows through and has reached max capacity
        # ------------------------------------------------------------------------------------------------------------------
        LOG.info("Validating all traffic flows through and has reached max capacity")
        # TODO

        # ------------------------------------------------------------------------------------------------------------------
        # 11. Clear counters
        # ------------------------------------------------------------------------------------------------------------------
        LOG.info("Clearing counters")
        # TODO

        # ------------------------------------------------------------------------------------------------------------------
        # 12. Stop the VNF (--> time stamp)
        # ------------------------------------------------------------------------------------------------------------------
        LOG.info("Stopping the VNF")
        self.tc_result['timeRecord']['stopVNFStart'] = time.clock()
        stop_operation_id = vnfm.vnf_change_state(vnf_instance_id=vnf_instance_id, change_state_to="stop")

        # Check the status of the stopping operation
        if not check_operation_status(vnfm.get_operation_status, stop_operation_id, "Successfully done"):
            LOG.error("TC_VNF_COMPLEX_002 execution failed")
            LOG.debug("Unexpected status for stopping operation")
            self.tc_result['overall_status'] = 'Fail'
            self.tc_result['error_info'] = 'Unexpected status for stopping operation'
            return False

        # ------------------------------------------------------------------------------------------------------------------
        # 13. Validate VNF has been stopped (--> time stamp)
        # ------------------------------------------------------------------------------------------------------------------
        LOG.info("Validating VNF state is STOPPED")
        vnf_state = vnfm.vnf_query(vnf_instance_id, "vnf_state")
        if vnf_state != "STOPPED":
            LOG.error("TC_VNF_COMPLEX_002 execution failed")
            LOG.debug("The VNF state was %s, expected STOPPED" % vnf_state)
            self.tc_result['overall_status'] = 'Fail'
            self.tc_result['error_info'] = 'The VNF state was %s, expected STOPPED' % vnf_state
            return False

        self.tc_result['timeRecord']['stopVNFEnd'] = time.clock()

        # ------------------------------------------------------------------------------------------------------------------
        # 14. Validate no traffic flows through (--> last arrival time stamp)
        # ------------------------------------------------------------------------------------------------------------------
        LOG.info("Validating no traffic flows through")
        # TODO

        # ------------------------------------------------------------------------------------------------------------------
        # 15. Stop traffic
        # ------------------------------------------------------------------------------------------------------------------
        LOG.info("Stopping traffic")
        # TODO

        # ------------------------------------------------------------------------------------------------------------------
        # 16. Calculate the time to stop a max scaled VNF under load (--> last arrival time stamp)
        # ------------------------------------------------------------------------------------------------------------------
        LOG.info("Calculating the time to stop a max scaled VNF under load")

        self.tc_result['timeRecord']['stopVNFTime'] = \
            round(self.tc_result['timeRecord']['stopVNFEnd'] - self.tc_result['timeRecord']['stopVNFStart'], 6)

        LOG.info("TC_VNF_COMPLEX_002 execution completed successfully")

        return True

    def cleanup(self):
        LOG.info("Starting cleanup for TC_VNF_COMPLEX_002")
        LOG.info("Finished cleanup for TC_VNF_COMPLEX_002")

        return True
