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

from test_cases import TestCase

# Instantiate logger
LOG = logging.getLogger(__name__)


class TD_NFV_BASE_ONBOARD_NSD_001(TestCase):
    """
    TD_NFV_BASE_ONBOARD_NSD_001 Verify that an NSD can be on-boarded.

    Sequence:
    1. Trigger the on-boarding of the NSD on MANO
    2. Verify that NSD is successfully on-boarded in MANO (i.e query, display, ...)
    3. Verify that all VLDs and VNFFGDs referenced in the NSD have been successfully on-boarded in MANO
    """

    REQUIRED_APIS = ('mano', )
    REQUIRED_ELEMENTS = ('nsd', 'nsd_params')

    def run(self):
        LOG.info('Starting %s' % self.tc_name)

        # --------------------------------------------------------------------------------------------------------------
        # 1. Trigger the on-boarding of the NSD on MANO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Creating the NSD information object')
        nsd_info_id = self.mano.nsd_info_create(self.tc_input['nsd_params'])

        LOG.info('Triggering the on-boarding of the NSD on MANO')
        self.mano.nsd_upload(nsd_info_id, self.tc_input['nsd'])

        self.register_for_cleanup(index=10, function_reference=self.mano.nsd_delete, nsd_info_id=[nsd_info_id])

        # --------------------------------------------------------------------------------------------------------------
        # 2. Verify that NSD is successfully on-boarded in MANO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that NSD is successfully on-boarded in MANO')
        nsd = self.mano.nsd_fetch(nsd_info_id)
        # TODO: Add NSD to tc_result

        # --------------------------------------------------------------------------------------------------------------
        # 3. Verify that all VLDs and VNFFGDs referenced in the NSD have been successfully on-boarded in MANO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that all VLDs and VNFFGDs referenced in the NSD have been successfully on-boarded in MANO')
        # TODO

        LOG.info('%s execution completed successfully' % self.tc_name)
