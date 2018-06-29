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

from api.adapter.vim import VimAdapterError
from api.structures.objects import VirtualCompute, VirtualNetwork, VirtualStorage
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class DummyVimAdapterError(VimAdapterError):
    """
    A problem occurred in the VNF LifeCycle Validation Dummy VIM adapter API.
    """
    pass


class DummyVimAdapter(object):
    """
    Class of stub functions representing operations exposed by the VIM towards the NFVO/VNFM.
    """

    def __init__(self, **kwargs):
        pass

    @log_entry_exit(LOG)
    def query_virtualised_compute_resource(self, query_compute_filter):
        virtual_compute = VirtualCompute()
        return virtual_compute

    @log_entry_exit(LOG)
    def query_virtualised_network_resource(self, query_network_filter):
        virtual_network = VirtualNetwork()
        return virtual_network

    @log_entry_exit(LOG)
    def query_virtualised_storage_resource(self, query_storage_filter):
        virtual_storage = VirtualStorage()
        return virtual_storage
