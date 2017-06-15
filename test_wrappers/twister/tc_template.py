import json
import time
from datetime import datetime

import requests

from api.generic import constants

# Get test case name
tc_name = __file__.rsplit('/', 1)[-1].rsplit('.', 1)[0]

# Get test case input
cfg_file_path = get_config(CONFIG[0], 'config/tc_input_dir')
cfg_file = cfg_file_path + '/' + tc_name + '.json'
with open(cfg_file) as f:
    tc_input = json.load(f)

# Get run ID
run_id_file = '/home/ubuntu/twister/resources/runid/current'
with open(run_id_file) as f:
   run_id = f.read()
set_details({'run_id': run_id})

# Build test case JSON
tc_json = {"tc_name": tc_name}
tc_json.update({'tc_input': tc_input})

# Start test case
try:
    server_response = requests.post(url='http://vnf_lcv_srv:8080/v1.0/exec', json=tc_json)
    assert server_response.status_code == 200
    data = server_response.json()
    execution_id = data['execution_id']
except:
    _RESULT = 'FAIL'
    exit()

# Poll on test case status
while True:
    server_response = requests.get(url='http://vnf_lcv_srv:8080/v1.0/exec/' + execution_id)
    data = server_response.json()
    tc_status = data['status']
    if tc_status in ['DONE', 'NOT_FOUND']:
        tc_result = data.get('tc_result', {})
        break
    time.sleep(constants.POLL_INTERVAL)

durations = dict()
durations['instantiate'] = tc_result.get('events', {}).get('instantiate_vnf', {}).get('duration', None)
durations['stop'] = tc_result.get('events', {}).get('stop_vnf', {}).get('duration', None)
durations['scale_out'] = tc_result.get('events', {}).get('scale_out_vnf', {}).get('duration', None)
durations['scale_in'] = tc_result.get('events', {}).get('scale_in_vnf', {}).get('duration', None)
durations['service_disruption'] = tc_result.get('events', {}).get('service_disruption', {}).get('duration', None)
durations['traffic_fwd_disruption'] = tc_result.get('events', {}).get('traffic_fwd_disruption', {}).get('duration', None)

for duration_type, duration_value in durations.items():
    set_details({duration_type: duration_value})

set_details({'vnfo': tc_input['mano_params']['type']})
set_details({'vnfm': tc_input['mano_params']['type']})
set_details({'vim': 'OpenStack'})
set_details({'vnf': 'CirrOS'})
set_details({'traffic_gen': 'STCv'})

if tc_result.get('overall_status') == constants.TEST_PASSED:
    _RESULT = 'PASS'
else:
    _RESULT = 'FAIL'


json_dict = dict()
json_dict['run_id'] = int(run_id)
json_dict['suite_name'] = SUITE_NAME
json_dict['tc_name'] = FILE_NAME.rsplit('/', 1)[-1].rsplit('.', 1)[0]
json_dict['tc_start_time'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
json_dict['tc_status'] = _RESULT

json_dict['environment'] = dict()
json_dict['environment']['vim'] = 'OpenStack'
json_dict['environment']['mano'] = tc_input['mano_params']['type']
json_dict['environment']['vnf'] = 'CirrOS'
json_dict['environment']['traffic'] = 'STCv'
json_dict['environment']['em'] = 'None'

json_dict['durations'] = dict((k, v) for k, v in durations.iteritems() if v is not None)

requests.post(url='http://kibana:9200/nfv/tc-exec', json=json_dict)
