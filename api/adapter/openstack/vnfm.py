class VnfmOpenstackAdapter(object):
    def __init__(self):
        pass

    def vnf_instantiate(self,
                        vnf_instance_id,
                        flavour_id,
                        ext_virtual_link,
                        ext_managed_virtual_link,
                        localization_language,
                        **kwargs):
        pass

    def create_vnf_id(self, vnfd_id, vnf_instance_name, vnf_instance_description):
        pass
