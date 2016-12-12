class VnfmDummyAdapter(object):
    def __init__(self, **kwargs):
        pass

    def get_operation(self, life_cycle_operation_occurrence_id):
        operation_status = "Successfully done"
        return operation_status

    def vnf_create_id(self, vnfd_id, vnf_instance_name=None, vnf_instance_description=None):
        vnf_instance_id = "vnfinstanceid"
        return vnf_instance_id

    def vnf_instantiate(self,
                        vnf_instance_id,
                        flavour_id,
                        instantiation_level_id=None,
                        ext_virtual_link=None,
                        ext_managed_virtual_link=None,
                        localization_language=None,
                        additional_param=None):
        life_cycle_operation_occurrence_id = "12345"
        return life_cycle_operation_occurrence_id

    def vnf_query(self, filter, attribute_selector=None):
        vnf_info = {'instantiation_state': 'INSTANTIATED',
                    'instantiated_vnf_info': {'vnf_state': 'STARTED'}}
        return vnf_info
