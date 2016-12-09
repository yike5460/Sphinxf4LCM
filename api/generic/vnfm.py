from api.adapter import construct_vnfm_adapter

class Vnfm(object):
    def __init__(self, vendor = None, **kwargs):
        self.vendor = vendor
        self.vnfm_adapter = construct_vnfm_adapter(vendor)

    def vnf_instantiate(self):
        return self.vnfm_adapter.vnf_instantiate()

    def create_vnf_id(self, vnfd_id, vnf_instance_name = None, vnf_instance_description = None):
        return self.vnfm_adapter.create_vnf_id(vnfd_id, vnf_instance_name, vnf_instance_description)