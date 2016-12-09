class VnfmDummyAdapter(object):
    def __init__(self, **kwargs):
        pass

    def get_vnf_state(self, vnf_id):
        return 'ACTIVE'
