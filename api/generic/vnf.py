from api.adapter import construct_adapter


class Vnf(object):
    def __init__(self, vendor=None, **kwargs):
        self.vendor = vendor
        self.vnf_adapter = construct_adapter(vendor, "vnf", **kwargs)

    def __getattr__(self, attr):
        return getattr(self.vnf_adapter, attr)
