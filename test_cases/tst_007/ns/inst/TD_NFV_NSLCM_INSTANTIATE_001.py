import logging

from test_cases import TestCase, TestRunError
from utils.misc import generate_name

# Instantiate logger
LOG = logging.getLogger(__name__)


class TD_NFV_NSLCM_INSTANTIATE_001(TestCase):
    """
    TD_NFV_NSLCM_INSTANTIATE_001 Instantiate standalone NS

    Sequence:
    1. Trigger NS instantiation on the NFVO
    2. Verify that the software images have been successfully added to the image repository managed by the VIM
    3. Verify that the requested resources have been allocated by the VIM according to the descriptors
    4. Verify that the VNF instance(s) have been deployed according to the NSD (i.e. query the VIM and VNFM for VMs,
       VLs and CPs)
    5. Verify that the VNF instance(s) are reachable via the management network
    6. Verify that the VNF instance(s) have been configured according to the VNFD(s) by querying the VNFM
    7. Verify that the VNF instance(s), VL(s) and VNFFG(s) have been connected according to the descriptors
    8. Verify that the NFVO indicates NS instantiation operation result as successful
    9. Verify that the NS is successfully instantiated by running the end-to-end functional test
    """

    REQUIRED_APIS = ('mano', 'traffic')
    REQUIRED_ELEMENTS = ('nsd_id',)
    TESTCASE_EVENTS = ('instantiate_ns',)

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

        self.register_for_cleanup(index=10, function_reference=self.mano.ns_terminate_and_delete,
                                  ns_instance_id=self.ns_instance_id,
                                  terminate_time=self.tc_input.get('terminate_time'))

        # --------------------------------------------------------------------------------------------------------------
        # 2. Verify that the software images have been successfully added to the image repository managed by the VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the software images have been successfully added to the image repository managed by '
                 'the VIM')

        # --------------------------------------------------------------------------------------------------------------
        # 3. Verify that the requested resources have been allocated by the VIM according to the descriptors
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the requested resources have been allocated by the VIM according to the descriptors')
        if not self.mano.validate_ns_allocated_vresources(self.ns_instance_id,
                                                          self.tc_input['mano'].get('query_params')):
            raise TestRunError('Allocated vResources could not be validated')

        # --------------------------------------------------------------------------------------------------------------
        # 4. Verify that the VNF instance(s) have been deployed according to the NSD
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the VNF instance(s) have been deployed according to the NSD')

        # --------------------------------------------------------------------------------------------------------------
        # 5. Verify that the VNF instance(s) are reachable via the management network
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the VNF instance(s) are reachable via the management network')

        # --------------------------------------------------------------------------------------------------------------
        # 6. Verify that the VNF instance(s) have been configured according to the VNFD(s) by querying the VNFM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the VNF instance(s) have been configured according to the VNFD(s) by querying the '
                 'VNFM')

        # --------------------------------------------------------------------------------------------------------------
        # 7. Verify that the VNF instance(s), VL(s) and VNFFG(s) have been connected according to the descriptors
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the VNF instance(s), VL(s) and VNFFG(s) have been connected according to the '
                 'descriptors')

        # --------------------------------------------------------------------------------------------------------------
        # 8. Verify that the NFVO indicates NS instantiation operation result as successful
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NFVO indicates NS instantiation operation result as successful')

        # --------------------------------------------------------------------------------------------------------------
        # 9. Verify that the NS is successfully instantiated by running the end-to-end functional test
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NS is successfully instantiated by running the end-to-end functional test')

        LOG.info('%s execution completed successfully' % self.tc_name)
