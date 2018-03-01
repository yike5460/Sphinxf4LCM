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
from subprocess import Popen, PIPE

from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


@log_entry_exit(LOG)
def ping(ip_addr):
    """
    This function uses Linux 'ping' command to check connectivity to the host with provided IP address.

    :param ip_addr: IP address of the host to 'ping'.
    :return:        True if 'ping' is successful, False otherwise.
    """
    proc = Popen(['ping', '-c', '1', ip_addr], stdout=PIPE, stderr=PIPE)

    stdout, stderr = proc.communicate()
    for line in (stdout+stderr).split('\n'):
        LOG.debug(line)

    if proc.returncode == 0:
        return True
    else:
        return False
