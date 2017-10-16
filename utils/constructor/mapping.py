import json
import os
from api import ApiError

adapter_mapping_file_name = 'adapter_construct.json'
generic_mapping_file_name = 'generic_construct.json'

class ConstructorError(ApiError):
    """
    A problem occurred in the VNF LifeCycle Validation constructor mapping.
    """
    pass

def get_constructor_mapping(type):
    """
    This function returns a dictionary representing the mappings between various generic modules and their API path.
    """
    if type == 'adapter':
        mapping_file_name = adapter_mapping_file_name
        _constructor_mapping = None
    elif type == 'generic':
        mapping_file_name = generic_mapping_file_name
        _constructor_mapping = None
    else:
        raise ConstructorError('Unable to load mapping file for constructor of type %s' % type)
    # global _constructor_mapping
    if _constructor_mapping is None:
        mapping_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), mapping_file_name)
        with open(mapping_file_path, 'r') as mapping_file:
            _constructor_mapping = json.load(mapping_file)
    return _constructor_mapping
