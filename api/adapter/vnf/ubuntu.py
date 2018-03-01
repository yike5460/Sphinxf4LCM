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
from utils.logging_module import log_entry_exit

LOG = logging.getLogger(__name__)


class UbuntuVnfAdapterError(VnfAdapterError):
    """
    A problem occurred in the VNF LifeCycle Validation Ubuntu VNF adapter API.
    """
    pass


class UbuntuVnfAdapter(object):
    def __init__(self, **kwargs):
        pass

    @log_entry_exit(LOG)
    def config_applied(self):
        return True

    @log_entry_exit(LOG)
    def license_applied(self):
        return True
