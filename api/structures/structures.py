import json
import os
import sys
import yaml
from collections import MutableSequence
from weakref import WeakKeyDictionary


this_module = sys.modules[__name__]

schema_locations_file_name = 'schemas.json'
schema_locations = None
schemas = dict()


def get_schema(name):
    global schemas
    if name not in schemas:
        schemas[name] = load_schema_from_file(name)
    return schemas[name]


def load_schema_from_file(name):
    schema_file_name = get_schema_location(name)
    schema_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), schema_file_name)
    with open(schema_file_path, 'r') as schema_file:
        schema = yaml.load(schema_file)
    return schema[name]


def get_schema_location(name):
    global schema_locations
    if schema_locations is None:
        schema_locations_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), schema_locations_file_name)
        with open(schema_locations_file_path, 'r') as schema_locations_file:
            schema_locations = json.load(schema_locations_file)
    return schema_locations[name]


class Attribute(object):
    TYPE = NotImplemented

    def __init__(self):
        self._values = WeakKeyDictionary()

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            return self._values[instance]

    def __set__(self, instance, value):
        self._validate(value)
        coerced_value = self._coerce(value)
        self._values[instance] = coerced_value

    def _coerce(self, value):
        return value

    @classmethod
    def _validate(self, value):
        if self.TYPE is NotImplemented:
            raise NotImplementedError
        if not isinstance(value, self.TYPE):
            raise ValueError('value %s should be of type: %s' % (repr(value), repr(self.TYPE)))


class CoercedList(MutableSequence):
    def __init__(self, entry_type, data):
        super(CoercedList, self).__init__()
        self.ENTRY_TYPE = entry_type
        if data is None:
            self._list = list()
        else:
            self._list = list(data)

    def __delitem__(self, key):
        self._list.__delitem__(key)

    def __getitem__(self, item):
        return self._list.__getitem__(item)

    def __len__(self):
        return self._list.__len__()

    def __setitem__(self, key, value):
        self.ENTRY_TYPE._validate(value)
        self._list.__setitem__(key, value)

    def insert(self, index, value):
        self.ENTRY_TYPE._validate(value)
        self._list.insert(index, value)

    def __str__(self):
        return str(self._list)


class List(Attribute):
    TYPE = list

    def __init__(self, entry_type, **kwargs):
        if not issubclass(entry_type, Attribute):
            if issubclass(entry_type, InformationElement):
                entry_type = Object(entry_type)
            else:
                raise TypeError('container entry type should be an Attribute subtype')

        self.ENTRY_TYPE = entry_type
        super(List, self).__init__()

    def _coerce(self, value):
        return CoercedList(self.ENTRY_TYPE, value)

    def _validate(self, value):
        super(List, self)._validate(value)
        if self.ENTRY_TYPE is NotImplemented:
            raise NotImplementedError
        for entry in value:
            self.ENTRY_TYPE._validate(entry)


class Object(Attribute):
    def __init__(self, obj_type):
        self.OBJ_TYPE = obj_type
        super(Object, self).__init__()

    def _validate(self, value):
        if not isinstance(value, self.OBJ_TYPE):
            raise ValueError('value %s should be of type %s' % (repr(value), repr(self.OBJ_TYPE)))



class Enum(Attribute):
    def __init__(self, entry_type, valid_values):
        self.ENTRY_TYPE = entry_type
        self._valid_values = map(self.ENTRY_TYPE.TYPE, valid_values)
        super(Enum, self).__init__()

    def _validate(self, value):
        self.ENTRY_TYPE._validate(value)
        if value not in self._valid_values:
            raise ValueError('%s value should be in %s' % (repr(value), repr(self._valid_values)))


class String(Attribute):
    TYPE = str


class Identifier(String):
    pass


class Version(String):
    pass


class Number(Attribute):
    TYPE = int


class Integer(Attribute):
    TYPE = int


class Mapping(Attribute):
    TYPE = dict


class NotSpecified(Attribute):
    pass


class SchemaLoader(type):
    def __new__(meta, name, bases, class_dict):
        if bases != (InformationElement,):
            class_schema = get_schema(name)

            for class_attribute_name, class_attribute_schema in class_schema.get('attributes').items():
                class_attribute_type = class_attribute_schema.get('type')

                class_attribute_constraints = class_attribute_schema.get('constraints')

                constructor = getattr(this_module, class_attribute_type)
                if not issubclass(constructor, Attribute):
                    if issubclass(constructor, InformationElement):
                        class_attribute = Object(obj_type=constructor)
                    else:
                        raise TypeError('%s attribute type should be an Attribute subtype' % repr(class_attribute_type))
                else:
                    if class_attribute_constraints is not None:
                        class_attribute = constructor(entry_type=getattr(this_module, class_attribute_constraints.get('entry_type')),
                                                      valid_values=class_attribute_constraints.get('valid_values'))
                    else:
                        class_attribute = constructor()
                class_dict[class_attribute_name] = class_attribute
        return type.__new__(meta, name, bases, class_dict)


class InformationElement(object):
    def __setattr__(self, key, value):
        if key not in type(self).__dict__:
            raise ValueError('trying to set invalid attribute %s' % key)
        super(InformationElement, self).__setattr__(key, value)


class InformationElementWithExternalSchema(InformationElement):
    __metaclass__ = SchemaLoader

class VnfExtCpInfo(InformationElementWithExternalSchema): pass
class ResourceHandle(InformationElementWithExternalSchema): pass
class VirtualLinkResourceInfo(InformationElementWithExternalSchema): pass
class VnfLinkPort(InformationElementWithExternalSchema): pass
class ExtVirtualLinkInfo(InformationElementWithExternalSchema): pass
class ExtManagedVirtualLinkInfo(InformationElementWithExternalSchema): pass
class VnfcResourceInfo(InformationElementWithExternalSchema): pass
class VirtualStorageResourceInfo(InformationElementWithExternalSchema): pass
class ScaleInfo(InformationElementWithExternalSchema): pass
class VimInfo(InformationElementWithExternalSchema): pass
class InstantiatedVnfInfo(InformationElementWithExternalSchema): pass
class VnfInfo(InformationElementWithExternalSchema): pass

