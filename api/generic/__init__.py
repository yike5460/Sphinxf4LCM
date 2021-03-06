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


import importlib
from api import ApiError
from utils.constructors.mapping import get_generic_constructor_class


class ApiGenericError(ApiError):
    """
    A problem occurred in the VNF LifeCycle Validation generic API.
    """
    pass


def construct_generic(vendor, module_type, **kwargs):
    """
    This function fetches the adapter constructor for the specified vendor and module type.

    :param vendor:      The name of the vendor of the module. Ex "openstack"
    :param module_type: The module type for which to fetch the constructor. Ex. "vnfm"
    :param kwargs:      Additional key-value pairs.
    :return:            The constructor for the specified vendor and module type.
    """
    constructor = get_generic_constructor_class(module_type=module_type)

    return constructor(vendor, **kwargs)
