from api import ApiError
from utils.constructors.mapping import get_constructor_class


class ApiAdapterError(ApiError):
    """
    A problem occurred in the VNF LifeCycle Validation adapter API.
    """
    pass


def construct_adapter(vendor, module_type, **kwargs):
    """
    This function fetches the adapter constructor for the specified vendor and module type.

    :param vendor:      The name of the vendor of the module. Ex "openstack"
    :param module_type: The module type for which to fetch the constructor. Ex. "vnfm"
    :param kwargs:      Additional key-value pairs.
    :return:            The constructor for the specified vendor and module type.
    """
    constructor = get_constructor_class(map='adapter', path=module_type + '.' + vendor)

    return constructor(**kwargs)
