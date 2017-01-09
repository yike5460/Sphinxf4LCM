import logging
from api.generic.vnfm import Vnfm
from api.generic.vnf import Vnf
from api.generic.tools import vnfinfo_get_instantiation_state, vnfinfo_get_vnf_state
from test_cases import TestCase
import time
from api.generic import constants

# Instantiate logger
LOG = logging.getLogger(__name__)


class TC_VNF_COMPLEX_002(TestCase):
    """
    TC_VNF_COMPLEX_002 Stop a max scale-up/scaled-out VNF instance in state Active under max traffic load

    Sequence:
    1. Instantiate VNF
    2. Validate VNF instantiation state is INSTANTIATED
    3. Start VNF
    4. Validate VNF state is STARTED
    5. Generate low traffic load
    6. Validate that traffic flows through without issues (-> no dropped packets)
    7. Trigger a resize of the NFV resources to reach the maximum
    8. Validate VNF has resized to the max and has max capacity
    9. Generate max traffic load to load all VNF instances
    10. Validate all traffic flows through and has reached max capacity
    11. Clear counters
    12. Stop the VNF (--> time stamp)
    13. Validate VNF has been stopped (--> time stamp)
    14. Validate no traffic flows through (--> last arrival time stamp)
    15. Stop traffic
    16. Calculate the time to stop a max scaled VNF under load (--> last arrival time stamp)
    """

    def run(self):
        LOG.info('Starting TC_VNF_COMPLEX_002')

        vnfm = Vnfm(vendor=self.tc_input['vnfm_vendor'])
        vnf = Vnf(vendor=self.tc_input['vnf_vendor'])

        self.tc_result = {'overall_status': 'Success', 'error_info': 'No errors', 'timeRecord': {}}

        # --------------------------------------------------------------------------------------------------------------
        # 1. Instantiate VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Instantiating VNF')
        self.tc_result['timeRecord']['instantiateVNFStart'] = time.time()
        vnf_instance_id = vnfm.vnf_create_and_instantiate(vnfd_id='vnfd_id', flavour_id='123456',
                                                          vnf_instance_name='test_vnf',
                                                          vnf_instance_description='VNF used for testing')
        if vnf_instance_id is None:
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unexpected VNF instantiation ID')
            self.tc_result['overall_status'] = 'Fail'
            self.tc_result['error_info'] = 'Unexpected VNF instantiation ID'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 2. Validate VNF instantiation state is INSTANTIATED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF instantiation state is INSTANTIATED')
        vnf_info = vnfm.vnf_query(filter=vnf_instance_id)
        if vnfinfo_get_instantiation_state(vnfinfo_dict=vnf_info) != constants.VNF_INSTANTIATED:
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unexpected VNF instantiation state')
            self.tc_result['overall_status'] = 'Fail'
            self.tc_result['error_info'] = 'Unexpected VNF instantiation state'
            return False

        self.tc_result['timeRecord']['instantiateVNFEnd'] = time.time()

        self.tc_result['timeRecord']['instantiateVNFTime'] = round(self.tc_result['timeRecord']['instantiateVNFEnd'] -
                                                                   self.tc_result['timeRecord']['instantiateVNFStart'],
                                                                   6)

        # --------------------------------------------------------------------------------------------------------------
        # 3. Start VNF
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Starting VNF')
        self.tc_result['timeRecord']['startVNFStart'] = time.time()
        if vnfm.vnf_operate_sync(vnf_instance_id=vnf_instance_id, change_state_to='start') != \
                constants.OPERATION_SUCCESS:
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unexpected status for starting VNF operation')
            self.tc_result['overall_status'] = 'Fail'
            self.tc_result['error_info'] = 'Unexpected status for starting VNF operation'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 4. Validate VNF state is STARTED
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF state is STARTED')
        vnf_info = vnfm.vnf_query(filter=vnf_instance_id)
        if vnfinfo_get_vnf_state(vnfinfo_dict=vnf_info) != constants.VNF_STARTED:
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unexpected VNF state')
            self.tc_result['overall_status'] = 'Fail'
            self.tc_result['error_info'] = 'Unexpected VNF state'
            return False

        self.tc_result['timeRecord']['startVNFEnd'] = time.time()

        self.tc_result['timeRecord']['StartVNFTime'] = \
            round(self.tc_result['timeRecord']['startVNFEnd'] - self.tc_result['timeRecord']['startVNFStart'], 6)

        # --------------------------------------------------------------------------------------------------------------
        # 5. Generate low traffic load
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Generating low traffic load')
        # TODO

        # --------------------------------------------------------------------------------------------------------------
        # 6. Validate that traffic flows through without issues
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating that traffic flows through without issues')
        # TODO

        # --------------------------------------------------------------------------------------------------------------
        # 7. Trigger a resize of the NFV resources to reach the maximum
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering a resize of the NFV resources to reach the maximum')
        if self.tc_input['scaling_trigger'] == 'command_to_vnfm':
            if vnfm.vnf_scale_to_level_sync(vnf_instance_id=vnf_instance_id, instantiation_level_id='max_level_id') != \
                    constants.OPERATION_SUCCESS:
                LOG.error('TC_VNF_COMPLEX_002 execution failed')
                LOG.debug('Unexpected status for resize triggering operation')
                self.tc_result['overall_status'] = 'Fail'
                self.tc_result['error_info'] = 'Unexpected status for resize triggering operation'
                return False

        elif self.tc_input['scaling_trigger'] == 'triggered_by_vnf':
            if vnf.scale_to_level_sync(vnf_instance_id=vnf_instance_id, instantiation_level_id='max_level_id') != \
                    constants.OPERATION_SUCCESS:
                LOG.error('TC_VNF_COMPLEX_002 execution failed')
                LOG.debug('Unexpected status for resize triggering operation')
                self.tc_result['overall_status'] = 'Fail'
                self.tc_result['error_info'] = 'Unexpected status for resize triggering operation'
                return False

        # --------------------------------------------------------------------------------------------------------------
        # 8. Validate VNF has resized to the max and has max capacity
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF has resized to the max and has max capacity')
        # self.tc_result['resource_list'] = {}
        # self.tc_result['resource_list']['max_resource'] = vnfm.get_vResource(vnf_instance_id=vnf_instance_id)
        # if not vnfm.validate_allocated_vResources(vnf_vResource_list=self.tc_result['resource_list']['max_resource'],
        #                                           instantiation_level_id='max_level_id',
        #                                           resource_type_list=self.tc_input['resource_type']):
        #     LOG.error('TC_VNF_COMPLEX_002 execution failed')
        #     LOG.debug('Unable to validate maximum resources')
        #     self.tc_result['overall_status'] = 'Fail'
        #     self.tc_result['error_info'] = 'Unable to validate maximum resources'
        #     return False

        # --------------------------------------------------------------------------------------------------------------
        # 9. Generate max traffic load to load all VNF instances
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Generating max traffic load to load all VNF instances')
        # TODO

        # --------------------------------------------------------------------------------------------------------------
        # 10. Validate all traffic flows through and has reached max capacity
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating all traffic flows through and has reached max capacity')
        # TODO

        # --------------------------------------------------------------------------------------------------------------
        # 11. Clear counters
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Clearing counters')
        # TODO

        # --------------------------------------------------------------------------------------------------------------
        # 12. Stop the VNF (--> time stamp)
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Stopping the VNF')
        self.tc_result['timeRecord']['stopVNFStart'] = time.time()
        if vnfm.vnf_operate_sync(vnf_instance_id=vnf_instance_id, change_state_to='stop') != \
                constants.OPERATION_SUCCESS:
            LOG.error('TC_VNF_COMPLEX_002 execution failed')
            LOG.debug('Unexpected status for starting VNF operation')
            self.tc_result['overall_status'] = 'Fail'
            self.tc_result['error_info'] = 'Unexpected status for starting VNF operation'
            return False

        # --------------------------------------------------------------------------------------------------------------
        # 13. Validate VNF has been stopped (--> time stamp)
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating VNF state is STOPPED')
        # vnf_info = vnfm.vnf_query(filter=vnf_instance_id)
        # if vnfinfo_get_vnf_state(vnfinfo_dict=vnf_info) != constants.VNF_STOPPED:
        #     LOG.error('TC_VNF_COMPLEX_002 execution failed')
        #     LOG.debug('Unexpected VNF state')
        #     self.tc_result['overall_status'] = 'Fail'
        #     self.tc_result['error_info'] = 'Unexpected VNF state'
        #     return False

        self.tc_result['timeRecord']['stopVNFEnd'] = time.time()

        # --------------------------------------------------------------------------------------------------------------
        # 14. Validate no traffic flows through (--> last arrival time stamp)
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating no traffic flows through')
        # TODO

        # --------------------------------------------------------------------------------------------------------------
        # 15. Stop traffic
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Stopping traffic')
        # TODO

        # --------------------------------------------------------------------------------------------------------------
        # 16. Calculate the time to stop a max scaled VNF under load (--> last arrival time stamp)
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Calculating the time to stop a max scaled VNF under load')

        self.tc_result['timeRecord']['stopVNFTime'] = \
            round(self.tc_result['timeRecord']['stopVNFEnd'] - self.tc_result['timeRecord']['stopVNFStart'], 6)

        LOG.info('TC_VNF_COMPLEX_002 execution completed successfully')

        print self.tc_result

        return True

    def cleanup(self):
        LOG.info('Starting cleanup for TC_VNF_COMPLEX_002')
        LOG.info('Finished cleanup for TC_VNF_COMPLEX_002')

        return True
