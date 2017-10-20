import json
import os
import importlib

from api import ApiError

mapping_type = {'adapter': 'adapters.json',
                'generic': 'generics.json',
                'tc': 'tc_map.json'
                }
_constructor_mapping = {'adapter': None, 'generic': None, 'tc': None}


class ConstructorError(ApiError):
    """
    A problem occurred in the VNF LifeCycle Validation constructor mapping.
    """
    pass


def get_constructor_mapping(constructor_type):
    """
    This function returns a dictionary representing the mappings between various generic modules and their API path.
    """
    global _constructor_mapping
    mapping_file_name = mapping_type[constructor_type]
    if _constructor_mapping[constructor_type] is None:
        mapping_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), mapping_file_name)
        with open(mapping_file_path, 'r') as mapping_file:
            _constructor_mapping[constructor_type] = json.load(mapping_file)
    return _constructor_mapping[constructor_type]


def get_generic_constructor_class(module_type):
    module_info = get_constructor_mapping('generic')
    module_info = module_info[module_type]
    module_name, constructor_name = module_info.rsplit('.', 1)
    constructor = get_class(module_name, constructor_name)
    return constructor


def get_adapter_constructor_class(vendor, module_type):
    module_info = get_constructor_mapping('adapter')
    module_info = module_info[module_type][vendor]
    module_name, constructor_name = module_info.rsplit('.', 1)
    constructor = get_class(module_name, constructor_name)
    return constructor


def get_tc_constructor_class(tc_name):
    module_info = get_constructor_mapping('tc')
    module_name = module_info[tc_name]
    constructor_name = tc_name
    constructor = get_class(module_name, constructor_name)
    return constructor


def get_class(module_name, constructor_name):
    try:
        module_object = importlib.import_module(module_name)
    except ImportError:
        raise ConstructorError('Unable to import module %s' % module_name)

    try:
        constructor = getattr(module_object, constructor_name)
    except AttributeError:
        raise ConstructorError('Unable to find constructor %s in module %s' % (constructor_name, module_name))
    return constructor
