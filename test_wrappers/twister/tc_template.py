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
from datetime import datetime


def twister_run():
    global _RESULT

    # Get test case name
    tc_name = __file__.rsplit('/', 1)[-1].rsplit('.', 1)[0]

    # Set VNF Lifecycle Verification hostname
    vnf_lcv_srv = 'vnflcv'

    # Get run ID
    run_id_file = '/tmp/current'
    with open(run_id_file) as f:
       run_id = f.read()
    set_details({'run_id': run_id})

    # Build test case JSON
    tc_exec_request = {"tc_name": tc_name,
                       "run_id": run_id,
                       "suite_name": SUITE_NAME}

    # Start test case
    try:
        server_response = requests.post(url='http://' + vnf_lcv_srv + ':8080/v1.0/exec', json=tc_exec_request)
        assert server_response.status_code == 200
        data = server_response.json()
        execution_id = data['execution_id']
    except AssertionError:
        print '!!! Error: %s !!!' % server_response.json()['error']
        _RESULT = 'FAIL'
        return

    # Iterate throught step by step execution and print status
    current_step_index = 0
    while True:
        response = requests.get(url='http://%s:8080/v1.0/step/%s' % (vnf_lcv_srv, execution_id))
        if response.status_code == 204:
            print '-' * 32 + '[ %s ]' % datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '-' * 32
            print '=== Test case steps completed ==='
            break
        else:
            step_details = response.json()
            step_index = step_details['index']
            if step_index != current_step_index:
                step_name = step_details['name']
                step_description = step_details['description']
                print '-' * 32 + '[ %s ]' % datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '-' * 32
                print '%s. %s' % (step_index, step_name)
                print 'Description: %s' % step_description
                print 'Status:'
            step_status = step_details['status']
            print '- %s' % step_status
            if step_status == 'PAUSED':
                # interact('msg', 'Test case execution PAUSED. Click OK to resume', 1)
                # requests.post(url='http://%s:8080/v1.0/step/%s' % (vnf_lcv_srv, execution_id))
                print '   *** TC execution paused. Send the following request to resume:'
                print '       curl -XPOST http://<IP ADDRESS>:8080/v1.0/step/%s' % execution_id
            current_step_index = step_index

    # Wait for the test case execution to finish
    print '=== Waiting for test case execution to fully finish ==='
    requests.get(url='http://' + vnf_lcv_srv + ':8080/v1.0/wait/' + execution_id)

    print '=== Test case execution completed ==='
    print '-' * 32 + '[ %s ]' % datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '-' * 32

    # Get the results for this execution
    server_response = requests.get(url='http://' + vnf_lcv_srv + ':8080/v1.0/exec/' + execution_id)
    data = server_response.json()
    tc_status = data['status']
    if tc_status in ['DONE', 'NOT_FOUND']:
        tc_result = data.get('tc_result', {})
        print
        print 'Test case overall status: %s' % tc_result.get('overall_status', 'N/A')
        print 'Test case error info: %s' % tc_result.get('error_info', 'N/A')

    durations = dict()
    durations['instantiate'] = tc_result.get('events', {}).get('instantiate_vnf', {}).get('duration')
    durations['stop'] = tc_result.get('events', {}).get('stop_vnf', {}).get('duration')
    durations['scale_out'] = tc_result.get('events', {}).get('scale_out_vnf', {}).get('duration')
    durations['scale_in'] = tc_result.get('events', {}).get('scale_in_vnf', {}).get('duration')
    durations['service_disruption'] = tc_result.get('events', {}).get('service_disruption', {}).get('duration')
    durations['traffic_fwd_disruption'] = tc_result.get('events', {}).get('traffic_fwd_disruption', {}).get('duration')

    for duration_type, duration_value in durations.items():
        set_details({duration_type: duration_value})

    server_response = requests.get(url='http://' + vnf_lcv_srv + ':8080/v1.0/exec/' + execution_id)
    data = server_response.json()
    tc_input = data['tc_input']

    set_details({'vnfo': tc_input.get('mano', {}).get('type', 'N/A')})
    set_details({'vnfm': tc_input.get('mano', {}).get('type', 'N/A')})
    set_details({'vnf': tc_input.get('vnf', {}).get('type', 'N/A')})
    set_details({'vim': tc_input.get('vim', {}).get('type', 'N/A')})
    set_details({'traffic_gen': tc_input.get('traffic', {}).get('type', 'N/A')})

    if tc_result.get('overall_status') == 'PASSED':
        _RESULT = 'PASS'
    else:
        _RESULT = 'FAIL'

twister_run()
