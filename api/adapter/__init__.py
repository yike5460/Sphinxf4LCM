from api.adapter.openstack.vnfm import VnfmOpenstackAdapter


def construct_vnfm_adapter(vendor=None, **kwargs):
    if vendor == 'openstack':
        return VnfmOpenstackAdapter(**kwargs)

