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

from test_cases import TestCase, TestRunError, Step

# Instantiate logger
LOG = logging.getLogger(__name__)


class TD_NFV_BASE_TEARDOWN_DELETE_NSD_001(TestCase):
    """
    TD_NFV_BASE_TEARDOWN_DELETE_NSD_001 Verify that an NSD can be deleted.

    Sequence:
    1. Trigger the on-boarding of the NSD on MANO
    2. Trigger the deletion of NSD on MANO
    3. Verify that the NSD and referenced VLD(s) and VNFFGD(s) no longer exist on MANO
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

    @Step(name='Delete NSD', description='Trigger the deletion of NSD on MANO')
    def step2(self):
        # --------------------------------------------------------------------------------------------------------------
        # 2. Trigger the deletion of NSD on MANO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Triggering the deletion of NSD on MANO')
        if self.mano.nsd_delete(self.nsd_info_id) != self.nsd_info_id:
            raise TestRunError('The NSD could not be deleted by the MANO')

        self.unregister_from_cleanup(index=10)

    @Step(name='Verify NSD no longer exists',
          description='Verify that the NSD and referenced VLD(s) and VNFFGD(s) no longer exist on MANO')
    def step3(self):
        # --------------------------------------------------------------------------------------------------------------
        # 3. Verify that the NSD and referenced VLD(s) and VNFFGD(s) no longer exist on MANO
        # --------------------------------------------------------------------------------------------------------------
        LOG.info('Verifying that the NSD and referenced VLD(s) and VNFFGD(s) no longer exist on MANO')
        if self.mano.nsd_info_query(filter={'nsd_info_id': self.nsd_info_id}) is not None:
            raise TestRunError('The NsdInfo object still exists')

        # TODO: Verify that VLD(s) and VNFFGD(s) no longer exist

        LOG.info('%s execution completed successfully' % self.tc_name)
