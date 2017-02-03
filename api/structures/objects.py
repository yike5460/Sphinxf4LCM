import json
import os
import sys
import yaml
from collections import MutableSequence
from weakref import WeakKeyDictionary


this_module = sys.modules[__name__]

schema_locations_file_name = 'schemas/schemas.json'
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
        schema_locations_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                  schema_locations_file_name)
        with open(schema_locations_file_path, 'r') as schema_locations_file:
            schema_locations = json.load(schema_locations_file)
    return schema_locations[name]


class TypeValidator(object):
    def __init__(self, attribute_type):
        self._type = attribute_type

    def validate(self, value):
        if self._type is NotImplemented:
            raise NotImplementedError
        if self._type is None:
            return
        if not isinstance(value, self._type):
            raise ValueError('value %s should be of type: %s' % (repr(value), repr(self._type)))


class Attribute(object):
    def __init__(self, attribute_type):
        self._values = WeakKeyDictionary()
        self._type_validator = TypeValidator(attribute_type)

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            return self._values.get(instance, None)

    def __set__(self, instance, value):
        self._validate(value)
        coerced_value = self._coerce(value)
        self._values[instance] = coerced_value

    def _coerce(self, value):
        return value

    def _validate(self, value):
        self._type_validator.validate(value)


class StaticTypeAttribute(Attribute):
    TYPE = NotImplemented

    def __init__(self):
        super(StaticTypeAttribute, self).__init__(self.TYPE)


class CoercedList(MutableSequence):
    def __init__(self, entry_type, data):
        super(CoercedList, self).__init__()
        self._entry_type_validator = TypeValidator(entry_type)
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
        self._entry_type_validator.validate(value)
        self._list.__setitem__(key, value)

    def insert(self, index, value):
        self._entry_type_validator.validate(value)
        self._list.insert(index, value)

    def __str__(self):
        return str(self._list)

    @property
    def dump(self):
        data = []
        for entry in self:
            if isinstance(entry, InformationElement):
                entry = entry.dump
            data.append(entry)

        return data


class List(StaticTypeAttribute):
    TYPE = list

    def __init__(self, entry_type, **kwargs):
        if issubclass(entry_type, Attribute):
            self._entry_type_validator = entry_type()._type_validator
        elif issubclass(entry_type, InformationElement):
            self._entry_type_validator = Attribute(entry_type)._type_validator
        else:
            raise TypeError(
                'invalid entry type %s. It should be an Attribute or InformationElement subclass' % entry_type)

        self.entry_type = entry_type
        super(List, self).__init__()

    def _coerce(self, value):
        return CoercedList(self.entry_type, value)

    def _validate(self, value):
        super(List, self)._validate(value)
        for entry in value:
            self._entry_type_validator.validate(entry)


class Enum(Attribute):
    def __init__(self, entry_type, valid_values):
        super(Enum, self).__init__(entry_type.TYPE)
        self._valid_values = valid_values

    def _validate(self, value):
        super(Enum, self)._validate(value)
        if value not in self._valid_values:
            raise ValueError('%s value should be in %s' % (repr(value), repr(self._valid_values)))


class String(StaticTypeAttribute):
    TYPE = str


class Identifier(String):
    pass


class Version(String):
    pass


class Boolean(StaticTypeAttribute):
    TYPE = bool


class Value(String):
    pass


class Number(StaticTypeAttribute):
    TYPE = int


class Integer(StaticTypeAttribute):
    TYPE = int


class Mapping(StaticTypeAttribute):
    TYPE = dict


class NotSpecified(StaticTypeAttribute):
    TYPE = None


class MacAddress(StaticTypeAttribute):
    TYPE = str


class IpAddress(StaticTypeAttribute):
    TYPE = str


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
                        class_attribute = Attribute(constructor)
                    else:
                        raise TypeError('%s attribute type should be an Attribute subtype' % repr(class_attribute_type))
                else:
                    if class_attribute_constraints is not None:
                        class_attribute = constructor(
                            entry_type=getattr(this_module, class_attribute_constraints.get('entry_type')),
                            valid_values=class_attribute_constraints.get('valid_values'))
                    else:
                        try:
                            class_attribute = constructor()
                        except TypeError:
                            raise TypeError('unable to call __init__ for %s' % class_attribute_type)

                class_dict[class_attribute_name] = class_attribute
        return type.__new__(meta, name, bases, class_dict)


class InformationElement(object):
    def __setattr__(self, key, value):
        if key not in type(self).__dict__:
            raise ValueError('trying to set invalid attribute %s' % key)
        super(InformationElement, self).__setattr__(key, value)

    @property
    def dump(self):
        data = dict()
        for key, value in type(self).__dict__.items():
            if isinstance(value, Attribute):
                data_value = getattr(self, key)

                if isinstance(data_value, InformationElement):
                    data_value = data_value.dump
                if isinstance(data_value, CoercedList):
                    data_value = data_value.dump

                data[key] = data_value
        return data

    def __str__(self):
        return yaml.dump(self.dump, default_flow_style=False)


class InformationElementWithExternalSchema(InformationElement):
    __metaclass__ = SchemaLoader


class VnfExtCpInfo(InformationElementWithExternalSchema):
    pass


class ResourceHandle(InformationElementWithExternalSchema):
    pass


class VirtualLinkResourceInfo(InformationElementWithExternalSchema):
    pass


class VnfLinkPort(InformationElementWithExternalSchema):
    pass


class ExtVirtualLinkInfo(InformationElementWithExternalSchema):
    pass


class ExtManagedVirtualLinkInfo(InformationElementWithExternalSchema):
    pass


class VnfcResourceInfo(InformationElementWithExternalSchema):
    pass


class VirtualStorage(InformationElementWithExternalSchema):
    pass


class VirtualStorageResourceInfo(InformationElementWithExternalSchema):
    pass


class ScaleInfo(InformationElementWithExternalSchema):
    pass


class VimInfo(InformationElementWithExternalSchema):
    pass


class InstantiatedVnfInfo(InformationElementWithExternalSchema):
    pass


class VnfInfo(InformationElementWithExternalSchema):
    pass


class VirtualMemory(InformationElementWithExternalSchema):
    pass


class VirtualCpuPinning(InformationElementWithExternalSchema):
    pass


class VirtualCpu(InformationElementWithExternalSchema):
    pass


class VirtualNetworkInterface(InformationElementWithExternalSchema):
    pass


class VirtualCompute(InformationElementWithExternalSchema):
    pass


class VirtualNetworkPort(InformationElementWithExternalSchema):
    pass


class NetworkSubnet(InformationElementWithExternalSchema):
    pass


class NetworkQoS(InformationElementWithExternalSchema):
    pass


class VirtualNetwork(InformationElementWithExternalSchema):
    pass