import logging
from time import sleep

from api.generic import constants
from api.structures.objects import OperateVnfData
from test_cases import TestCase, TestRunError
from utils.misc import generate_name

# Instantiate logger
LOG = logging.getLogger(__name__)


class TD_NFV_NSLCM_UPDATE_STOP_001(TestCase):
    """
    TD_NFV_NSLCM_UPDATE_STOP_001 Verify the capability to stop a VNF instance inside a NS instance

    Sequence:
    1. Trigger NS instantiation on the NFVO
    2. Verify that the NS is instantiated
    3. Trigger the NFVO to stop the target VNF instance inside the NS instance
    4. Verify that the VNF instance operational state on the VNFM is indicated as "stopped"
    5. Verify that the compute resources allocated to the VNFC instances inside the target VNF instance have been
       stopped by querying the VIM
    6. Verify that other existing compute resources have not been affected by the performed operation by querying the
       VIM
    7. Verify that the NFVO shows no "operate VNF" operation errors
    """

    REQUIRED_APIS = ('mano',)
    REQUIRED_ELEMENTS = ('nsd_id', 'operate_vnf_data')
    TESTCASE_EVENTS = ('instantiate_ns', 'ns_update_stop_vnf')

    def run(self):
        LOG.info('Starting %s' % self.tc_name)

        # --------------------------------------------------------------------------------------------------------------
        # 1. Trigger NS instantiation on the NFVO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering NS instantiation on the NFVO')
        self.time_record.START('instantiate_ns')
        self.ns_instance_id = self.mano.ns_create_and_instantiate(
               nsd_id=self.tc_input['nsd_id'], ns_name=generate_name(self.tc_name),
               ns_description=self.tc_input.get('ns_description'), flavour_id=self.tc_input.get('flavour_id'),
               sap_data=self.tc_input.get('sap_data'), pnf_info=self.tc_input.get('pnf_info'),
               vnf_instance_data=self.tc_input.get('vnf_instance_data'),
               nested_ns_instance_data=self.tc_input.get('nested_ns_instance_data'),
               location_constraints=self.tc_input.get('location_constraints'),
               additional_param_for_ns=self.tc_input.get('additional_param_for_ns'),
               additional_param_for_vnf=self.tc_input.get('additional_param_for_vnf'),
               start_time=self.tc_input.get('start_time'),
               ns_instantiation_level_id=self.tc_input.get('ns_instantiation_level_id'),
               additional_affinity_or_anti_affinity_rule=self.tc_input.get('additional_affinity_or_anti_affinity_rule'))

        if self.ns_instance_id is None:
            raise TestRunError('NS instantiation operation failed')

        self.time_record.END('instantiate_ns')

        self.tc_result['events']['instantiate_ns']['duration'] = self.time_record.duration('instantiate_ns')

        sleep(constants.INSTANCE_BOOT_TIME)

        self.register_for_cleanup(index=10, function_reference=self.mano.ns_terminate_and_delete,
                                  ns_instance_id=self.ns_instance_id,
                                  terminate_time=self.tc_input.get('terminate_time'))
        self.register_for_cleanup(index=20, function_reference=self.mano.wait_for_ns_stable_state,
                                  ns_instance_id=self.ns_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 2. Verify that the NS is instantiated
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Validating NS instantiation state is INSTANTIATED')
        ns_info = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id,
                                             'additional_param': self.tc_input['mano'].get('query_params')})
        if ns_info.ns_state != constants.NS_INSTANTIATED:
            raise TestRunError('Unexpected NS instantiation state',
                               err_details='NS instantiation state was not "%s" after the NS was instantiated'
                                           % constants.NS_INSTANTIATED)

        # --------------------------------------------------------------------------------------------------------------
        # 3. Trigger the NFVO to stop the target VNF instance inside the NS instance
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering the NFVO to stop the target VNF instance inside the NS instance')
        operate_vnf_data_list = list()
        for vnf_info in ns_info.vnf_info:
            if vnf_info.vnf_product_name in self.tc_input['operate_vnf_data']:
                vnf_data = OperateVnfData()
                vnf_data.vnf_instance_id = vnf_info.vnf_instance_id
                vnf_data.change_state_to = 'stop'
                operate_vnf_data_list.append(vnf_data)

        self.time_record.START('ns_update_stop_vnf')

        if self.mano.ns_update_sync(ns_instance_id=self.ns_instance_id, update_type='OperateVnf',
                                    operate_vnf_data=operate_vnf_data_list) != constants.OPERATION_SUCCESS:
            raise TestRunError('Unexpected status for NS update operation',
                               err_details='NS update operation failed')

        self.time_record.END('ns_update_stop_vnf')

        self.tc_result['events']['ns_update_stop_vnf']['duration'] = self.time_record.duration('ns_update_stop_vnf')

        # --------------------------------------------------------------------------------------------------------------
        # 4. Verify that the VNF instance operational state on the VNFM is indicated as "stopped"
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the VNF instance operational state on the VNFM is indicated as "stopped"')
        for vnf_data in operate_vnf_data_list:
            vnf_info = self.mano.vnf_query(filter={'vnf_instance_id': vnf_data.vnf_instance_id,
                                                   'additional_param': self.tc_input['mano'].get('query_params')})
            if vnf_info.instantiated_vnf_info.vnf_state != constants.VNF_STOPPED:
                raise TestRunError('Target VNF %s was not stopped' % vnf_info.vnf_product_name)

        # --------------------------------------------------------------------------------------------------------------
        # 5. Verify that the compute resources allocated to the VNFC instances inside the target VNF instance have been
        #    stopped by querying the VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verify that the compute resources allocated to the VNFC instances inside the target VNF instance have'
                 ' been stopped by querying the VIM')
        for vnf_data in operate_vnf_data_list:
            if not self.mano.validate_vnf_vresource_state(vnf_data.vnf_instance_id):
                raise TestRunError('Target VNF %s compute resources have not been stopped' % vnf_data.vnf_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 6. Verify that other existing compute resources have not been affected by the performed operation by querying
        #    the VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that other existing compute resources have not been affected by the performed operation by '
                 'querying the VIM')
        LOG.debug('This check is not needed as the test is run in an isolated environment')

        # --------------------------------------------------------------------------------------------------------------
        # 7. Verify that the NFVO shows no "operate VNF" operation errors
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NFVO shows no "operate VNF" operation errors')
        LOG.debug('This has implicitly been checked at step 3')

        LOG.info('%s execution completed successfully' % self.tc_name)
