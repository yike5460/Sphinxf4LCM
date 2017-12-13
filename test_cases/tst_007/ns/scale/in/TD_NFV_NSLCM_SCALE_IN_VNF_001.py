import logging

from api.generic import constants
from api.structures.objects import ScaleVnfData, ScaleByStepData
from test_cases import TestCase, TestRunError
from utils.misc import generate_name

# Instantiate logger
LOG = logging.getLogger(__name__)


class TD_NFV_NSLCM_SCALE_IN_VNF_001(TestCase):
    """
    TD_NFV_NSLCM_SCALE_IN_VNF_001 Scale in VNF inside NS by removing VNFC instances from an existing VNF triggered by an
    operator action

    Sequence:
    1. Trigger NS instantiation on the NFVO
    2. Verify that the NFVO indicates NS instantiation operation result as successful
    3. Trigger NS scale out by adding VNFC instance(s) to a VNF in the NS in NFVO with an operator action
    4. Trigger NS scale in by removing VNFC instance(s) from a VNF in the NS in NFVO with an operator action
    5. Verify that the impacted VNFC instance(s) inside the VNF have been terminated by querying the VNFM
    6. Verify that the impacted VNFC instance(s) resources have been released by the VIM
    7. Verify that the remaining VNFC instance(s) are still running and reachable via the management network
    8. Verify that the VNF configuration has been updated to exclude the removed VNFC instances according to the
       descriptors by querying the VNFM
    9. Verify that the remaining VNFC instances(s) and VL(s) are still connected according to the descriptors
    10. Verify that the NFVO indicates the scaling operation result as successful
    11. Verify that NS has been scaled in by running the end-to-end functional test in relevance to the VNF scale and
        capacity
    """

    REQUIRED_APIS = ('mano', 'traffic')
    REQUIRED_ELEMENTS = ('nsd_id',)
    TESTCASE_EVENTS = ('instantiate_ns', 'scale_out_ns','scale_in_ns')

    def run(self):
        LOG.info('Starting %s' % self.tc_name)

        # --------------------------------------------------------------------------------------------------------------
        # 1.  Trigger NS instantiation on the NFVO
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
        self.register_for_cleanup(index=20, function_reference=self.mano.wait_for_ns_stable_state,
                                  ns_instance_id=self.ns_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 2.  Verify that the NFVO indicates NS instantiation operation result as successful
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NFVO indicates NS instantiation operation result as successful')
        ns_info = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id,
                                             'additional_param': self.tc_input['mano'].get('query_params')})
        if ns_info.ns_state != constants.NS_INSTANTIATED:
            raise TestRunError('Unexpected NS state',
                               err_details='NS state was not "%s" after the NS was instantiated'
                                           % constants.NS_INSTANTIATED)

        self.tc_result['resources']['Initial'] = dict()
        for vnf_info in ns_info.vnf_info:
            self.tc_result['resources']['Initial'].update(
                self.mano.get_allocated_vresources(vnf_info.vnf_instance_id, self.tc_input['mano'].get('query_params')))

        # --------------------------------------------------------------------------------------------------------------
        # 3.  Trigger NS scale out by adding VNFC instance(s) to a VNF in the NS in NFVO with an operator action
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering NS scale out by adding VNFC instance(s) to a VNF in the NS in NFVO with an operator '
                 'action')
        scale_vnf_data_list = list()
        expected_nr_vnfc = dict()
        for vnf_sp in self.tc_input['scaling_policy_list']:
            vnf_name, sp_name = vnf_sp.split(':')
            vnfd_name = self.mano.get_vnfd_name_from_nsd_vnf_name(self.tc_input['nsd_id'], vnf_name)
            sp = self.mano.get_vnfd_scaling_properties(vnfd_name, sp_name)

            # Build the ScaleVnfData information element
            scale_vnf_data = ScaleVnfData()
            scale_vnf_data.vnf_instance_id = self.mano.get_vnf_instance_id_from_ns_vnf_name(ns_info, vnf_name)
            scale_vnf_data.type = 'out'
            scale_vnf_data.scale_by_step_data = ScaleByStepData()
            scale_vnf_data.scale_by_step_data.type = 'out'
            scale_vnf_data.scale_by_step_data.aspect_id = sp['targets'][0]
            scale_vnf_data.scale_by_step_data.number_of_steps = sp['increment']
            scale_vnf_data.scale_by_step_data.additional_param = {'scaling_policy_name': sp_name}

            scale_vnf_data_list.append(scale_vnf_data)

            LOG.info('### VNF %s - Default number of instances: %s' % (vnf_name, sp['default_instances']))
            LOG.info('### VNF %s - Increment number of instances: %s' % (vnf_name, sp['increment']))
            expected_nr_vnfc[vnf_name] = sp['default_instances'] + sp['increment']
            LOG.info('### After scale out:')
            LOG.info('### VNF %s - Expected number of instances: %s' % (vnf_name, expected_nr_vnfc[vnf_name]))

        self.time_record.START('scale_out_ns')
        if self.mano.ns_scale_sync(self.ns_instance_id, scale_type='SCALE_VNF', scale_vnf_data=scale_vnf_data_list,
                                   scale_time=self.tc_input.get('scale_time')) \
                != constants.OPERATION_SUCCESS:
            self.tc_result['scaling_out']['status'] = 'Fail'
            raise TestRunError('MANO could not scale out the NS')

        self.time_record.END('scale_out_ns')

        self.tc_result['events']['scale_out_ns']['duration'] = self.time_record.duration('scale_out_ns')

        # Retrieving the list of VnfInfo objects for the impacted VNFs before the scale in operation
        ns_info_before_scale_in = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id,
                                             'additional_param': self.tc_input['mano'].get('query_params')})
        vnf_info_impacted_list = []
        for vnf_info in ns_info_before_scale_in.vnf_info:
            if vnf_info.vnf_product_name in expected_nr_vnfc.keys():
                vnf_info_impacted_list.append(vnf_info)

        # --------------------------------------------------------------------------------------------------------------
        # 4.  Trigger NS scale in by removing VNFC instance(s) from a VNF in the NS in NFVO with an operator action
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering NS scale in by removing VNFC instance(s) from a VNF in the NS in NFVO with an operator'
                 ' action')
        # scale_vnf_data_list = list()
        # expected_nr_vnfc = dict()
        for scale_vnf_data in scale_vnf_data_list:
            # vnf_name, sp_name = vnf_sp.split(':')
            # vnfd_name = self.mano.get_vnfd_name_from_nsd_vnf_name(self.tc_input['nsd_id'], vnf_name)
            # sp = self.mano.get_vnfd_scaling_properties(vnfd_name, sp_name)
            #
            # # Build the ScaleVnfData information element
            # scale_vnf_data = ScaleVnfData()
            # scale_vnf_data.vnf_instance_id = self.mano.get_vnf_instance_id_from_ns_vnf_name(ns_info, vnf_name)
            scale_vnf_data.type = 'in'
            # scale_vnf_data.scale_by_step_data = ScaleByStepData()
            scale_vnf_data.scale_by_step_data.type = 'in'
            # scale_vnf_data.scale_by_step_data.aspect_id = sp['targets'][0]
            # scale_vnf_data.scale_by_step_data.number_of_steps = sp['increment']
            # scale_vnf_data.scale_by_step_data.additional_param = {'scaling_policy_name': sp_name}
            #
            # scale_vnf_data_list.append(scale_vnf_data)

            # LOG.info('### Before scale in:')
            # LOG.info('### VNF %s - Expected number of instances: %s' % (vnf_name, expected_nr_vnfc[vnf_name]))
            # expected_nr_vnfc[vnf_name] = expected_nr_vnfc[vnf_name] - scale_vnf_data.scale_by_step_data.number_of_steps
            # LOG.info('### After scale in:')
            # LOG.info('### VNF %s - Expected number of instances: %s' % (vnf_name, expected_nr_vnfc[vnf_name]))

        self.time_record.START('scale_in_ns')
        if self.mano.ns_scale_sync(self.ns_instance_id, scale_type='SCALE_VNF', scale_vnf_data=scale_vnf_data_list,
                                   scale_time=self.tc_input.get('scale_time')) \
                != constants.OPERATION_SUCCESS:
            self.tc_result['scaling_in']['status'] = 'Fail'
            raise TestRunError('MANO could not scale in the NS')

        self.time_record.END('scale_in_ns')

        self.tc_result['events']['scale_in_ns']['duration'] = self.time_record.duration('scale_in_ns')

        # --------------------------------------------------------------------------------------------------------------
        # 5.  Verify that the impacted VNFC instance(s) inside the VNF have been terminated by querying the VNFM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the impacted VNFC instance(s) inside the VNF have been terminated by querying the'
                 ' VNFM')
        ns_info = self.mano.ns_query(filter={'ns_instance_id': self.ns_instance_id,
                                             'additional_param': self.tc_input['mano'].get('query_params')})
        for vnf_info in ns_info.vnf_info:
            vnf_name = vnf_info.vnf_product_name
            if vnf_name in expected_nr_vnfc.keys():
                # LOG.info('### VNF %s - Actual number of instances after scale out and in: %s' %
                #          (vnf_name, len(vnf_info.instantiated_vnf_info.vnfc_resource_info)))
                if len(vnf_info.instantiated_vnf_info.vnfc_resource_info) != expected_nr_vnfc[vnf_name]:
                    raise TestRunError('VNFCs not removed after VNF scaled in')

        self.tc_result['resources']['After scale in'] = dict()
        for vnf_info in ns_info.vnf_info:
            self.tc_result['resources']['After scale in'].update(
                self.mano.get_allocated_vresources(vnf_info.vnf_instance_id, self.tc_input['mano'].get('query_params')))

        # TODO Add self.tc_result['scaling_in']['level']. We should do this only for the VNF(s) that we scaled

        self.tc_result['scaling_in']['status'] = 'Success'

        # --------------------------------------------------------------------------------------------------------------
        # 6.  Verify that the impacted VNFC instance(s) resources have been released by the VIM
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the impacted VNFC instance(s) resources have been released by the VIM')
        for vnf_info_impacted in vnf_info_impacted_list:
            vnf_info_final = self.mano.vnf_query(filter={'vnf_instance_id': vnf_info_impacted.vnf_instance_id,
                                                         'additional_param': self.tc_input['mano'].get('query_params')})
            if not self.mano.validate_vnf_released_vresources(vnf_info_initial=vnf_info_impacted,
                                                              vnf_info_final=vnf_info_final):
                raise TestRunError('Allocated vResources were not released for VNF instance ID %s' %
                                   vnf_info_impacted.vnf_instance_id)

        # --------------------------------------------------------------------------------------------------------------
        # 7.  Verify that the remaining VNFC instance(s) are still running and reachable via the management network
        # --------------------------------------------------------------------------------------------------------------


        # --------------------------------------------------------------------------------------------------------------
        # 8.  Verify that the VNF configuration has been updated to exclude the removed VNFC instances according to the
        # descriptors by querying the VNFM
        # --------------------------------------------------------------------------------------------------------------


        # --------------------------------------------------------------------------------------------------------------
        # 9.  Verify that the remaining VNFC instances(s) and VL(s) are still connected according to the descriptors
        # --------------------------------------------------------------------------------------------------------------


        # --------------------------------------------------------------------------------------------------------------
        # 10.  Verify that the NFVO indicates the scaling operation result as successful
        # --------------------------------------------------------------------------------------------------------------


        # --------------------------------------------------------------------------------------------------------------
        # 11. Verify that NS has been scaled in by running the end-to-end functional test in relevance to the VNF scale
        # and capacity
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('%s execution completed successfully' % self.tc_name)
