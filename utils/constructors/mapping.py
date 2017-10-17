import json
import os
import importlib

from api import ApiError

mapping_type = {'adapter': 'adapters.json',
                'generic': 'generics.json',
                'tc': 'tc_map.json'
                }
_constructor_mapping = {'adapter': None, 'generic': None}


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


def get_constructor_class(map, path):
    module_info = get_constructor_mapping(map)
    path_list = path.rsplit('.')
    class_path = module_info
    for p in path_list:
        if p not in class_path:
            raise ConstructorError('Unable to find module for %s' % path)
        class_path = class_path[p]

    module_name, constructor_name = class_path.rsplit('.', 1)

    try:
        module = importlib.import_module(module_name)
    except ImportError:
        raise ConstructorError('Unable to import module %s' % module_name)

    try:
        constructor = getattr(module, constructor_name)
    except AttributeError:
        raise ConstructorError('Unable to find constructor %s in module %s' % (constructor_name, module_name))
    return constructor
