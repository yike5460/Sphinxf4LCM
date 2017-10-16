import json
import os
from api import ApiError

adapter_mapping_file_name = 'adapter_construct.json'
generic_mapping_file_name = 'generic_construct.json'
_constructor_mapping = {'adapter': None, 'generic': None}

class ConstructorError(ApiError):
    """
    A problem occurred in the VNF LifeCycle Validation constructor mapping.
    """
    pass

def get_constructor_mapping(type):
    """
    This function returns a dictionary representing the mappings between various generic modules and their API path.
    """
    global _constructor_mapping
    if type == 'adapter':
        mapping_file_name = adapter_mapping_file_name
    elif type == 'generic':
        mapping_file_name = generic_mapping_file_name
    else:
        raise ConstructorError('Unable to load mapping file for constructor of type %s' % type)
    if _constructor_mapping[type] is None:
        mapping_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), mapping_file_name)
        with open(mapping_file_path, 'r') as mapping_file:
            _constructor_mapping[type] = json.load(mapping_file)
    return _constructor_mapping[type]
