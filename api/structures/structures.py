from collections import MutableSequence
import os
import sys
from weakref import WeakKeyDictionary
import yaml


schema_file_name = 'structures.yaml'
_schema = None
this_module = sys.modules[__name__]


def _load_schema_from_file():
    global _schema
    if _schema is None:
        schema_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), schema_file_name)
        with open(schema_file_path, 'r') as schema_file:
            _schema = yaml.load(schema_file)
    return _schema


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
        self._values[instance] = value

    @classmethod
    def _validate(cls, value):
        if cls.TYPE is NotImplemented:
            raise NotImplementedError
        if not isinstance(value, cls.TYPE):
            raise ValueError('value %s should be of type: %s' % (repr(value), repr(cls.TYPE)))


class MyList(MutableSequence):
    def __init__(self, data):
        super(MyList, self).__init__()
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
        if not isinstance(value, str):
            raise ValueError('Value %s must be str' % value)
        self._list.__setitem__(key, value)

    def insert(self, index, value):
        if not isinstance(value, str):
            raise ValueError('Value %s must be str' % value)
        self._list.insert(index, value)

    def __str__(self):
        return str(self._list)


class List(Attribute):
    TYPE = list

    def __init__(self, entry_type):
        if not issubclass(entry_type, Attribute):
            raise TypeError('container entry type should be an Attribute subtype')
        self.ENTRY_TYPE = entry_type
        super(List, self).__init__()

    def __set__(self, instance, value):
        self._validate(value)
        new_value = MyList(value)
        self._values[instance] = new_value

    def _validate(self, value):
        super(List, self)._validate(value)
        if self.ENTRY_TYPE is NotImplemented:
            raise NotImplementedError
        for entry in value:
            self.ENTRY_TYPE._validate(entry)


class Enum(Attribute):
    def __init__(self, *args):
        self._allowed_list = args
        super(Enum, self).__init__()

    def _validate(self, value):
        if value not in self._allowed_list:
            raise ValueError('%s value should be in %s' % (value, self._allowed_list))


class String(Attribute):
    TYPE = str


class Identifier(String):
    pass


class Version(String):
    pass


class Mapping(Attribute):
    TYPE = dict


class InstantiatedVnfInfo(object):
    l = List(String)


class SchemaLoader(type):
    def __new__(meta, name, bases, class_dict):
        if bases != (InformationElement,):
            class_schema = _load_schema_from_file().get(name)

            for class_attribute_name, class_attribute_schema in class_schema.get('attributes').items():
                class_attribute_type = class_attribute_schema.get('type')
                constructor = getattr(this_module, class_attribute_type)
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


class VnfInfo(InformationElementWithExternalSchema):
    pass


