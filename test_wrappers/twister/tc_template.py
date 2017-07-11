import json
import time
import os
from datetime import datetime

import requests


def twister_run():
    global _RESULT

    # Get test case name
    tc_name = __file__.rsplit('/', 1)[-1].rsplit('.', 1)[0]

    # Set VNF Lifecycle Verification hostname
    vnf_lcv_srv = 'vnflcv'

    # Set poll interval
    poll_interval = 5

    # Get run ID
    run_id_file = '/home/spirent/twister/resources/runid/current'
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

    # Poll on test case status
    elapsed_time = 0
    while True:
        server_response = requests.get(url='http://' + vnf_lcv_srv + ':8080/v1.0/exec/' + execution_id)
        data = server_response.json()
        tc_status = data['status']
        if tc_status in ['DONE', 'NOT_FOUND']:
            tc_result = data.get('tc_result', {})
            print
            print 'Test case overall status: %s' % tc_result.get('overall_status', 'N/A')
            print 'Test case error info: %s' % tc_result.get('error_info', 'N/A')
            break
        time.sleep(poll_interval)
        elapsed_time += poll_interval
        print 'Test case execution pending. Elapsed time: %s seconds' % elapsed_time

    durations = dict()
    durations['instantiate'] = tc_result.get('events', {}).get('instantiate_vnf', {}).get('duration', None)
    durations['stop'] = tc_result.get('events', {}).get('stop_vnf', {}).get('duration', None)
    durations['scale_out'] = tc_result.get('events', {}).get('scale_out_vnf', {}).get('duration', None)
    durations['scale_in'] = tc_result.get('events', {}).get('scale_in_vnf', {}).get('duration', None)
    durations['service_disruption'] = tc_result.get('events', {}).get('service_disruption', {}).get('duration', None)
    durations['traffic_fwd_disruption'] = tc_result.get('events', {}).get('traffic_fwd_disruption', {}).get('duration', None)

    for duration_type, duration_value in durations.items():
        set_details({duration_type: duration_value})

    server_response = requests.get(url='http://' + vnf_lcv_srv + ':8080/v1.0/exec/' + execution_id)
    data = server_response.json()
    tc_input = data['tc_input']

    set_details({'vnfo': tc_input['mano_params']['type']})
    set_details({'vnfm': tc_input['mano_params']['type']})
    set_details({'vim': 'OpenStack'})
    set_details({'vnf': 'CirrOS'})
    set_details({'traffic_gen': 'STCv'})

    if tc_result.get('overall_status') == 'PASSED':
        _RESULT = 'PASS'
    else:
        _RESULT = 'FAIL'

twister_run()
