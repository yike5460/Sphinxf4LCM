#!/usr/bin/env python

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


import requests

# TODO: Get VNF Lifecycle Verification server IP address
vnf_lcv_srv = '10.2.34.39'

# Get the list with the test cases under execution
server_response = requests.get(url='http://' + vnf_lcv_srv + ':8080/v1.0/exec')
execution_list = server_response.json()

# Stop all 'PENDING' executions
for execution_entry in execution_list['status_list']:
    execution_id = execution_entry['execution_id']
    server_response = requests.get(url='http://' + vnf_lcv_srv + ':8080/v1.0/exec/' + execution_id)
    data = server_response.json()
    if data['status'] == 'PENDING':
        requests.delete(url='http://' + vnf_lcv_srv + ':8080/v1.0/exec/' + execution_id)
