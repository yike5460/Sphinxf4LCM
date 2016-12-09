import os
import json

mapping_file_name = 'constructors.json'
_vendor_constructor_mapping = None


def get_vendor_constructor_mapping():
    global _vendor_constructor_mapping
    if not _vendor_constructor_mapping:
        mapping_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), mapping_file_name)
        with open(mapping_file_path, 'r') as mapping_file:
            _vendor_constructor_mapping = json.load(mapping_file)
    return _vendor_constructor_mapping