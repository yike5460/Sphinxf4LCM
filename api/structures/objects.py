#
# Copyright (c) 2018 by Spirent Communications Plc.
# All Rights Reserved.
#
# This software is confidential and proprietary to Spirent Communications Inc.
# No part of this software may be reproduced, transmitted, disclosed or used
# in violation of the Software License Agreement without the expressed
# written consent of Spirent Communications Inc.
#
#


import json
import os
import sys
from collections import MutableSequence
from weakref import WeakKeyDictionary

import yaml

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
    def __init__(self, entry_type_validator, data):
        super(CoercedList, self).__init__()
        self._entry_type_validator = entry_type_validator
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
        return CoercedList(self._entry_type_validator, value)

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


class PositiveInteger(Integer):
    def _validate(self, value):
        super(PositiveInteger, self)._validate(value)
        if value <= 0:
            raise ValueError('Value %s should be a positive integer' % repr(value))


class Mapping(StaticTypeAttribute):
    TYPE = dict


class NotSpecified(StaticTypeAttribute):
    TYPE = None


class MacAddress(StaticTypeAttribute):
    TYPE = str


class IpAddress(StaticTypeAttribute):
    TYPE = str


class Rule(String):
    pass


class TimeStamp(String):
    TYPE = str


class TimeDuration(Number):
    TYPE = int


class SchemaLoader(type):
    def __new__(meta, name, bases, class_dict):
        if bases != (InformationElement,):
            information_element_names = [name]
            class_schemas = list()

            for information_element_name in information_element_names:
                class_schema = get_schema(information_element_name)
                class_schemas.append(class_schema)

                for inherited_information_element in class_schema.get('inherits', []):
                    if inherited_information_element in information_element_names:
                        raise TypeError('Cyclic inheritance detected for %s: %s'
                                        % (name, information_element_names + [inherited_information_element]))
                    information_element_names.append(inherited_information_element)

            class_schemas.reverse()

            for class_schema in class_schemas:
                for class_attribute_name, class_attribute_schema in class_schema.get('attributes', {}).items():
                    if class_attribute_name in class_dict:
                        raise TypeError('attribute %s already inherited by %s' % (class_attribute_name, name))

                    class_attribute_type = class_attribute_schema.get('type')

                    class_attribute_constraints = class_attribute_schema.get('constraints')

                    constructor = getattr(this_module, class_attribute_type)
                    if not issubclass(constructor, Attribute):
                        if issubclass(constructor, InformationElement):
                            class_attribute = Attribute(constructor)
                        else:
                            raise TypeError('%s attribute type should be an Attribute subtype'
                                            % repr(class_attribute_type))
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


class LogicalNodeData(InformationElementWithExternalSchema):
    pass


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


class NsLinkPort(InformationElementWithExternalSchema):
    pass


class NsVirtualLinkInfo(InformationElementWithExternalSchema):
    pass


class AffinityOrAntiAffinityRule(InformationElementWithExternalSchema):
    pass


class Nfp(InformationElementWithExternalSchema):
    pass


class VnffgInfo(InformationElementWithExternalSchema):
    pass


class SapInfo(InformationElementWithExternalSchema):
    pass


class PnfExtCpInfo(InformationElementWithExternalSchema):
    pass


class PnfInfo(InformationElementWithExternalSchema):
    pass


class NsScaleInfo(InformationElementWithExternalSchema):
    pass


class NsInfo(InformationElementWithExternalSchema):
    pass


class ScaleByStepData(InformationElementWithExternalSchema):
    pass


class ScaleToLevelData(InformationElementWithExternalSchema):
    pass


class ScaleVnfData(InformationElementWithExternalSchema):
    pass


class VnfLocationConstraint(InformationElementWithExternalSchema):
    pass


class ParamsForVnf(InformationElementWithExternalSchema):
    pass


class ScaleNsToLevelData(InformationElementWithExternalSchema):
    pass


class ScaleNsByStepsData(InformationElementWithExternalSchema):
    pass


class VnfInstanceData(InformationElementWithExternalSchema):
    pass


class ScaleNsData(InformationElementWithExternalSchema):
    pass


class VirtualComputeQuota(InformationElementWithExternalSchema):
    pass


class VirtualNetworkQuota(InformationElementWithExternalSchema):
    pass


class VirtualStorageQuota(InformationElementWithExternalSchema):
    pass


class VirtualStorageData(InformationElementWithExternalSchema):
    pass


class VirtualNetworkInterfaceData(InformationElementWithExternalSchema):
    pass


class AffinityOrAntiAffinityResourceList(InformationElementWithExternalSchema):
    pass


class AffinityOrAntiAffinityConstraint(InformationElementWithExternalSchema):
    pass


class VirtualNetworkAttributesReservationData(InformationElementWithExternalSchema):
    pass


class VirtualNetworkPortReservationData(InformationElementWithExternalSchema):
    pass


class VirtualComputeAttributesReservationData(InformationElementWithExternalSchema):
    pass


class ComputePoolReservation(InformationElementWithExternalSchema):
    pass


class VirtualComputeFlavour(InformationElementWithExternalSchema):
    pass


class VirtualNetworkReservation(InformationElementWithExternalSchema):
    pass


class StoragePoolReservation(InformationElementWithExternalSchema):
    pass


class VirtualisationContainerReservation(InformationElementWithExternalSchema):
    pass


class ReservedVirtualComputeAttributes(InformationElementWithExternalSchema):
    pass


class ReservedComputePool(InformationElementWithExternalSchema):
    pass


class ReservedVirtualisationContainer(InformationElementWithExternalSchema):
    pass


class ReservedVirtualNetworkPort(InformationElementWithExternalSchema):
    pass


class ReservedVirtualNetworkAttributes(InformationElementWithExternalSchema):
    pass


class ReservedVirtualCompute(InformationElementWithExternalSchema):
    pass


class ReservedVirtualNetwork(InformationElementWithExternalSchema):
    pass


class ReservedStoragePool(InformationElementWithExternalSchema):
    pass


class ReservedVirtualStorage(InformationElementWithExternalSchema):
    pass


class AffectedVnfc(InformationElementWithExternalSchema):
    pass


class AffectedVirtualStorage(InformationElementWithExternalSchema):
    pass


class AffectedVirtualLink(InformationElementWithExternalSchema):
    pass


class VnfLifecycleChangeNotification(InformationElementWithExternalSchema):
    pass


class L3AddressData(InformationElementWithExternalSchema):
    pass


class AddressData(InformationElementWithExternalSchema):
    pass


class CpProtocolData(InformationElementWithExternalSchema):
    pass


class Cpd(InformationElementWithExternalSchema):
    pass


class VirtualNetworkInterfaceRequirements(InformationElementWithExternalSchema):
    pass


class VduCpd(InformationElementWithExternalSchema):
    pass


class VirtualCpuPinningData(InformationElementWithExternalSchema):
    pass


class LinkBitrateRequirements(InformationElementWithExternalSchema):
    pass


class VnfQoS(InformationElementWithExternalSchema):
    pass


class VnfLocalAffinityOrAntiAffinityRule(InformationElementWithExternalSchema):
    pass


class VduLevel(InformationElementWithExternalSchema):
    pass


class VirtualLinkBitrateLevel(InformationElementWithExternalSchema):
    pass


class ScalingDelta(InformationElementWithExternalSchema):
    pass


class AspectDeltaDetails(InformationElementWithExternalSchema):
    pass


class ScalingAspect(InformationElementWithExternalSchema):
    pass


class InstantiateVnfOpConfig(InformationElementWithExternalSchema):
    pass


class ScaleVnfOpConfig(InformationElementWithExternalSchema):
    pass


class ScaleVnfToLevelOpConfig(InformationElementWithExternalSchema):
    pass


class HealVnfOpConfig(InformationElementWithExternalSchema):
    pass


class TerminateVnfOpConfig(InformationElementWithExternalSchema):
    pass


class OperateVnfOpConfig(InformationElementWithExternalSchema):
    pass


class SwImageDesc(InformationElementWithExternalSchema):
    pass


class VnfMonitoringParameter(InformationElementWithExternalSchema):
    pass


class VnfcConfigurableProperties(InformationElementWithExternalSchema):
    pass


class RequestedAdditionalCapabilityData(InformationElementWithExternalSchema):
    pass


class VirtualMemoryData(InformationElementWithExternalSchema):
    pass


class VirtualCpuData(InformationElementWithExternalSchema):
    pass


class ConnectivityType(InformationElementWithExternalSchema):
    pass


class VirtualLinkDescFlavour(InformationElementWithExternalSchema):
    pass


class VduProfile(InformationElementWithExternalSchema):
    pass


class VnfVirtualLinkProfile(InformationElementWithExternalSchema):
    pass


class InstantiationLevel(InformationElementWithExternalSchema):
    pass


class ChangeVnfFlavourOpConfig(InformationElementWithExternalSchema):
    pass


class ChangeExtVnfConnectivityOpConfig(InformationElementWithExternalSchema):
    pass


class VnfLcmOperationsConfiguration(InformationElementWithExternalSchema):
    pass


class VnfAffinityOrAntiAffinityGroup(InformationElementWithExternalSchema):
    pass


class Vdu(InformationElementWithExternalSchema):
    pass


class VirtualComputeDesc(InformationElementWithExternalSchema):
    pass


class VirtualStorageDesc(InformationElementWithExternalSchema):
    pass


class VnfVirtualLinkDesc(InformationElementWithExternalSchema):
    pass


class VnfExtCpd(InformationElementWithExternalSchema):
    pass


class VnfDf(InformationElementWithExternalSchema):
    pass


class VnfConfigurableProperties(InformationElementWithExternalSchema):
    pass


class VnfInfoModifiableAttributes(InformationElementWithExternalSchema):
    pass


class VnfLifeCycleManagementScript(InformationElementWithExternalSchema):
    pass


class VnfdElementGroup(InformationElementWithExternalSchema):
    pass


class VnfIndicator(InformationElementWithExternalSchema):
    pass


class Vnfd(InformationElementWithExternalSchema):
    pass


class SoftwareImageInformation(InformationElementWithExternalSchema):
    pass


class NsToLevelMapping(InformationElementWithExternalSchema):
    pass


class VnfToLevelMapping(InformationElementWithExternalSchema):
    pass


class VirtualLinkToLevelMapping(InformationElementWithExternalSchema):
    pass


class Dependencies(InformationElementWithExternalSchema):
    pass


class NsQoS(InformationElementWithExternalSchema):
    pass


class NsVirtualLinkConnectivity(InformationElementWithExternalSchema):
    pass


class NsProfile(InformationElementWithExternalSchema):
    pass


class VnfToLevelMapping(InformationElementWithExternalSchema):
    pass


class NsLevel(InformationElementWithExternalSchema):
    pass


class NsScalingAspect(InformationElementWithExternalSchema):
    pass


class NsLocalAffinityOrAntiAffinityRule(InformationElementWithExternalSchema):
    pass


class NsAffinityOrAntiAffinityGroup(InformationElementWithExternalSchema):
    pass


class NsVirtualLinkProfile(InformationElementWithExternalSchema):
    pass


class VnfProfile(InformationElementWithExternalSchema):
    pass


class PnfProfile(InformationElementWithExternalSchema):
    pass


class SecurityParameters(InformationElementWithExternalSchema):
    pass


class NsDf(InformationElementWithExternalSchema):
    pass


class OperateVnfData(InformationElementWithExternalSchema):
    pass


class NsMonitoringParameter(InformationElementWithExternalSchema):
    pass


class VnfIndicatorData(InformationElementWithExternalSchema):
    pass


class MonitoredData(InformationElementWithExternalSchema):
    pass


class Nfpd(InformationElementWithExternalSchema):
    pass


class Vnffgd(InformationElementWithExternalSchema):
    pass


class VirtualLinkDf(InformationElementWithExternalSchema):
    pass


class NsVirtualLinkDesc(InformationElementWithExternalSchema):
    pass


class Sapd(InformationElementWithExternalSchema):
    pass


class NsLifeCycleManagementScript(InformationElementWithExternalSchema):
    pass


class Nsd(InformationElementWithExternalSchema):
    pass
  
  
class NsdInfo(InformationElementWithExternalSchema):
    pass