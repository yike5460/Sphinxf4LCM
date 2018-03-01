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


from api.adapter import ApiAdapterError


class ManoAdapterError(ApiAdapterError):
    """
    A problem occurred in the VNF LifeCycle Validation MANO adapter API.
    """
    pass
