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

from test_cases import TestCase, Step

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
    REQUIRED_ELEMENTS = ('nsd', )

    @Step(name='On-board NSD', description='Trigger the on-boarding of the NSD on MANO')
    def step1(self):
        LOG.info('Starting %s' % self.tc_name)

        # --------------------------------------------------------------------------------------------------------------
        # 1. Trigger the on-boarding of the NSD on MANO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Creating the NSD information object')
        self.nsd_info_id = self.mano.nsd_info_create(self.tc_input.get('nsd_params', {}))

        LOG.info('Triggering the on-boarding of the NSD on MANO')
        self.mano.nsd_upload(self.nsd_info_id, self.tc_input['nsd'])

        self.register_for_cleanup(index=10, function_reference=self.mano.nsd_delete, nsd_info_id=self.nsd_info_id)

    @Step(name='Verify NSD is successfully on-boarded',
          description='Verify that NSD is successfully on-boarded in MANO')
    def step2(self):
        # --------------------------------------------------------------------------------------------------------------
        # 2. Verify that NSD is successfully on-boarded in MANO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that NSD is successfully on-boarded in MANO')
        self.tc_result['nsd'] = self.mano.nsd_fetch(self.nsd_info_id)

    @Step(name='Verify VLDs and VNFFGDs have been successfully on-boarded',
          description='Verify that all VLDs and VNFFGDs referenced in the NSD have been successfully on-boarded in '
                      'MANO',
          runnable=False)
    def step3(self):
        # --------------------------------------------------------------------------------------------------------------
        # 3. Verify that all VLDs and VNFFGDs referenced in the NSD have been successfully on-boarded in MANO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that all VLDs and VNFFGDs referenced in the NSD have been successfully on-boarded in MANO')
        # TODO

        LOG.info('%s execution completed successfully' % self.tc_name)
