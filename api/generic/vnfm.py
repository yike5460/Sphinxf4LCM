from api.adapter import construct_adapter


class Vnfm(object):
    def __init__(self, vendor=None, **kwargs):
        self.vendor = vendor
        self.vnfm_adapter = construct_adapter(vendor, "vnfm", **kwargs)

    def __getattr__(self, attr):
        return getattr(self.vnfm_adapter, attr)
