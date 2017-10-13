import importlib
from api import ApiError
from api.generic.generic_construct import get_generic_constructor_mapping


class ApiGenericError(ApiError):
    """
    A problem occurred in the VNF LifeCycle Validation generic API.
    """
    pass


def construct_generic(vendor, module_type, **kwargs):
    """
    This function fetches the adapter constructor for the specified vendor and module type.

    :param vendor:      The name of the vendor of the module. Ex "openstack"
    :param module_type: The module type for which to fetch the constructor. Ex. "vnfm"
    :param kwargs:      Additional key-value pairs.
    :return:            The constructor for the specified vendor and module type.
    """
    generic_constructor_mapping = get_generic_constructor_mapping()
    if module_type not in generic_constructor_mapping:
        raise ApiGenericError('Unable to find generic adapter for %s"' % module_type)

    module_name, constructor_name = generic_constructor_mapping[module_type].rsplit('.', 1)

    try:
        module = importlib.import_module(module_name)
    except ImportError:
        raise ApiGenericError('Unable to import module %s' % module_name)

    try:
        constructor = getattr(module, constructor_name)
    except AttributeError:
        raise ApiGenericError('Unable to find constructor %s in module %s' % (constructor_name, module_name))

    return constructor(vendor, **kwargs)
