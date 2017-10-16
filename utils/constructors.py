import json
import os

vendor_mapping_file_name = 'constructors.json'
_vendor_constructor_mapping = None

generic_mapping_file_name = 'generic_construct.json'
_generic_constructor_mapping = None

def get_generic_constructor_mapping():
    """
    This function returns a dictionary representing the mappings between various generic modules and their API path.
    """
    global _generic_constructor_mapping
    if _generic_constructor_mapping is None:
        mapping_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), generic_mapping_file_name)
        with open(mapping_file_path, 'r') as mapping_file:
            _generic_constructor_mapping = json.load(mapping_file)
    return _generic_constructor_mapping

def get_vendor_constructor_mapping():
    """
    This function returns a dictionary representing the mappings between various vendor modules and their adapter path.
    """
    global _vendor_constructor_mapping
    if _vendor_constructor_mapping is None:
        mapping_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), vendor_mapping_file_name)
        with open(mapping_file_path, 'r') as mapping_file:
            _vendor_constructor_mapping = json.load(mapping_file)
    return _vendor_constructor_mapping
