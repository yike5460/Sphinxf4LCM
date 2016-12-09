from api.adapter import construct_vnfm_adapter


class Vnfm(object):
    def __init__(self, vendor=None, **kwargs):
        self.vendor = vendor
        self.vnfm_adapter = construct_vnfm_adapter(vendor, **kwargs)

    def __getattr__(self, attr):
        return getattr(self.vnfm_adapter, attr)
