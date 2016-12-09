from api.adapter.openstack.vnfm import VnfmOpenstackAdapter


def construct_vnfm_adapter(vendor):
    if vendor == "openstack":
        return VnfmOpenstackAdapter()
