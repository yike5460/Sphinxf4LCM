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


import logging

from api.adapter.vnf import VnfAdapterError
from api.generic import constants
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class DummyVnfAdapterError(VnfAdapterError):
    """
    A problem occurred in the VNF LifeCycle Validation Dummy VNF adapter API.
    """
    pass


class DummyVnfAdapter(object):
    """
    Class of stub functions representing operations exposed by the VNF towards the VNFM.
    """

    def __init__(self, **kwargs):
        pass

    @log_entry_exit(LOG)
    def get_operation_status(self, lifecycle_operation_occurrence_id):
        operation_status = 'Successfully done'

        LOG.debug('Instantiation operation status: %s' % operation_status)

        return constants.OPERATION_SUCCESS

    @log_entry_exit(LOG)
    def scale_to_level(self, vnf_instance_id, instantiation_level_id=None, scale_info=None, additional_param=None):
        lifecycle_operation_occurrence_id = 'scale_to_level_operation_id'

        return lifecycle_operation_occurrence_id
