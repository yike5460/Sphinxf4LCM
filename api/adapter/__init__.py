import importlib
from api.adapter.constructors import get_vendor_constructor_mapping


def construct_vnfm_adapter(vendor=None, **kwargs):
    vendor_constructor_mapping = get_vendor_constructor_mapping()
    if vendor not in vendor_constructor_mapping:
        raise Exception('Unable to find constructor for vendor "%s"' % (vendor))

    module_name, constructor_name = vendor_constructor_mapping[vendor].rsplit('.', 1)

    try:
        module = importlib.import_module(module_name)
    except ImportError:
        print 'Unable to import module %s' % (module_name)
        raise

    try:
        constructor = getattr(module, constructor_name)
    except AttributeError:
        print 'Unable to find constructor %s in module %s' % (constructor_name, module_name)
        raise

    return constructor(**kwargs)
