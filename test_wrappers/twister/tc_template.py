import requests
from datetime import datetime

def twister_run(tc_module_name, tc_name):
    global _RESULT

    import importlib
    import json
    import logging

    from api.generic import constants
    from utils.logging_module import configure_logger

    tc_module = importlib.import_module(tc_module_name)
    tc_class = getattr(tc_module, tc_name)

    # Getting and configuring the RootLogger.
    root_logger = logging.getLogger()
    configure_logger(root_logger, propagate=True)

    # Logger for the current module.
    LOG = logging.getLogger(tc_name + ' wrapper')
    configure_logger(LOG, console_level='INFO', propagate=False)

    # Get TC input
    cfg_file_path = get_config(CONFIG[0], 'config/tc_input_dir')
    cfg_file = cfg_file_path + '/' + tc_name + '.json'
    with open(cfg_file) as f:
        tc_input = json.load(f)

    # Get run ID
    run_id_file = '/home/ubuntu/twister/resources/runid/current'
    with open(run_id_file) as f:
       run_id = f.read()
    set_details({'run_id': run_id})

    LOG.info('Calling test case %s' % tc_name)

    tc_result = dict()

    try:
        tc_result = tc_class(tc_input).execute()
    except:
        LOG.error('Test case %s failed' % tc_name)

    set_details({'instantiate': tc_result.get('events', {}).get('instantiate_vnf', {}).get('duration', -1)})
    set_details({'stop': tc_result.get('events', {}).get('stop_vnf', {}).get('duration', -1)})
    set_details({'scale_out': tc_result.get('events', {}).get('scale_out_vnf', {}).get('duration', -1)})
    set_details({'scale_in': tc_result.get('events', {}).get('scale_in_vnf', {}).get('duration', -1)})
    set_details({'service_disruption': tc_result.get('events', {}).get('service_disruption', {}).get('duration', -1)})
    set_details({'traffic_fwd_disruption': tc_result.get('events', {}).get('traffic_fwd_disruption', {}).get('duration', -1)})

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

    json_dict['durations'] = dict()
    json_dict['durations']['vnf_instantiate'] = int(tc_result.get('events', {}).get('instantiate_vnf', {}).get('duration', -1))

    requests.post(url='http://10.2.34.13:9200/nfv/tc-exec', json=json_dict)
