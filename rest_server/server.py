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


import json
import logging
import os
import uuid
from datetime import datetime
from multiprocessing import Process, Queue, Event
from threading import Lock

from bottle import route, request, response, run

from api.adapter import construct_adapter
from utils import reporting, logging_module
from utils.constructors.mapping import get_constructor_mapping, get_tc_constructor_class

execution_queues = dict()
message_queues = dict()
step_triggers = dict()
execution_processes = dict()
tc_results = dict()
tc_inputs = dict()

json_file_path = '/etc/vnflcv'
config_file_name = 'config.json'

lock_types = ['vim', 'mano', 'em', 'vnf', 'traffic', 'env', 'config']
lock = dict()
for lock_type in lock_types:
    lock[lock_type] = Lock()


def _read_config(key):
    """
    This function returns the content of the JSON config file.
    """
    config_file_path = os.path.join(json_file_path, config_file_name)
    try:
        with open(config_file_path, 'r') as config_file:
            config = json.load(config_file)
    except Exception:
        config = {}

    return config.get(key)


def _write_config(key, value):
    """
    This function adds the specified key and value to the JSON config file.
    """
    config_file_path = os.path.join(json_file_path, config_file_name)
    try:
        with open(config_file_path, 'r') as config_file:
            config = json.load(config_file)
    except Exception:
        config = {}

    config[key] = value

    with open(config_file_path, 'w') as config_file:
        json.dump(config, config_file, sort_keys=True, indent=2)


def _delete_config(key):
    """
    This function deletes the specified key from the JSON config file.
    """
    config_file_path = os.path.join(json_file_path, config_file_name)
    try:
        with open(config_file_path, 'r') as config_file:
            config = json.load(config_file)
    except Exception:
        config = {}

    config.pop(key, None)

    with open(config_file_path, 'w') as config_file:
        json.dump(config, config_file, sort_keys=True, indent=2)


def execute_test(tc_exec_request, tc_input, execution_queue, message_queue, step_trigger):
    """
    This function is used as a process target and it starts the execution of a test case.
    """
    tc_name = tc_exec_request['tc_name']
    tc_class = get_tc_constructor_class(tc_name)

    timestamp = '{:%Y_%m_%d_%H_%M_%S}'.format(datetime.now())
    log_file_name = '%s_%s.log' % (timestamp, str(tc_name))
    report_file_name = '%s_%s.txt' % (timestamp, str(tc_name))
    html_report_file_name = '%s_%s.html' % (timestamp, str(tc_name))
    json_file_name = '%s_%s.json' % (timestamp, str(tc_name))

    root_logger = logging.getLogger()
    logging_module.configure_logger(root_logger, file_level='DEBUG', log_filename=log_file_name)

    tc_start_time = datetime.utcnow()
    tc_instance = tc_class(tc_input)
    tc_instance.message_queue = message_queue
    tc_instance.step_trigger = step_trigger
    tc_result = tc_instance.execute()
    tc_end_time = datetime.utcnow()

    tc_result['tc_start_time'] = tc_start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    tc_result['tc_end_time'] = tc_end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    tc_result['tc_duration'] = str(tc_end_time - tc_start_time)

    execution_queue.put(tc_result)
    message_queue.put(None)

    kibana_srv = _read_config('kibana-srv')
    if kibana_srv is not None:
        reporting.kibana_report(kibana_srv, tc_exec_request, tc_input, tc_result)

    reporting.report_test_case(report_file_name, tc_exec_request, tc_input, tc_result)
    reporting.html_report_test_case(html_report_file_name, tc_exec_request, tc_input, tc_result)
    reporting.dump_raw_json(json_file_name, tc_exec_request, tc_input, tc_result)


@route('/version')
def get_version():
    """
    Request mapped function that returns the list of REST server supported versions.
    """
    return {'versions': ['v1.0']}


@route('/v1.0/exec', method='POST')
def do_exec():
    """
    Request mapped function that starts the execution of a test case in a new process.
    """
    tc_exec_request = request.json
    timeout_timers = ['VNF_INSTANTIATE_TIMEOUT', 'VNF_SCALE_TIMEOUT', 'VNF_STOP_TIMEOUT', 'VNF_START_TIMEOUT',
                      'VNF_TERMINATE_TIMEOUT', 'VNF_STABLE_STATE_TIMEOUT', 'NS_INSTANTIATE_TIMEOUT', 'NS_SCALE_TIMEOUT',
                      'NS_UPDATE_TIMEOUT', 'NS_TERMINATE_TIMEOUT', 'NS_STABLE_STATE_TIMEOUT', 'POLL_INTERVAL']

    tc_name = tc_exec_request.get('tc_name')
    try:
        get_tc_constructor_class(tc_name)
    except KeyError:
        response.status = 404
        return {'error': 'Test case %s not found' % tc_name}

    tc_input = tc_exec_request.get('tc_input')
    if tc_input is None:
        active_env = _read_config('active-env')
        if active_env is None:
            response.status = 400
            return {'error': 'Active environment not set'}

        tc_input = dict()
        for resource_type, resource_name in _read_resource('env', active_env).items():
            resource_params = _read_resource(resource_type, resource_name)
            tc_input[resource_type] = dict()
            tc_input[resource_type]['type'] = resource_params['type']
            tc_input[resource_type]['name'] = resource_name
            tc_input[resource_type]['adapter_config'] = resource_params['client_config']
            if resource_type == 'traffic':
                tc_input[resource_type]['traffic_config'] = resource_params['traffic_config']
            if resource_type == 'mano':
                tc_input['mano']['instantiation_params'] = resource_params.get('instantiation_params', {})
                tc_input['mano']['instantiation_params_for_ns'] = resource_params.get('instantiation_params_for_ns', {})
                tc_input['mano']['instantiation_params_for_vnf'] = resource_params.get('instantiation_params_for_vnf',
                                                                                       {})
                tc_input['mano']['query_params'] = resource_params.get('query_params', {})
                tc_input['mano']['termination_params'] = resource_params.get('termination_params', {})
                tc_input['mano']['operate_params'] = resource_params.get('operate_params', {})
                tc_input['mano']['scale_params'] = resource_params.get('scale_params', {})
                tc_input['mano']['sap_data'] = resource_params.get('sap_data', {})
                tc_input['mano']['alarm_list_params'] = resource_params.get('alarm_list_params', {})
                tc_input['vnfd_id'] = resource_params.get('vnfd_id')
                tc_input['flavour_id'] = resource_params.get('flavour_id')
                tc_input['instantiation_level_id'] = resource_params.get('instantiation_level_id')
                tc_input['nsd_id'] = resource_params.get('nsd_id')
                tc_input['nested_ns_instance_data'] = resource_params.get('nested_ns_instance_data')
                tc_input['ns_instantiation_level_id'] = resource_params.get('ns_instantiation_level_id')
                tc_input['scale_to_level_list'] = resource_params.get('scale_to_level_list')
                tc_input['scale_from_level_list'] = resource_params.get('scale_from_level_list')
                tc_input['operate_vnf_data'] = resource_params.get('operate_vnf_data')
                tc_input['nsd'] = resource_params.get('nsd')
                tc_input['nsd_params'] = resource_params.get('nsd_params', {})
                if tc_input['nsd_params'].get('vendor_nsd_file'):
                    try:
                        with open(tc_input['nsd_params']['vendor_nsd_file'], 'r') as nsd_file:
                            tc_input['nsd_params']['vendor_nsd'] = nsd_file.read()
                            tc_input['nsd_params'].pop('vendor_nsd_file')
                    except Exception as e:
                        response.status = 504
                        return {'Error': '%s' % e}
                tc_input[resource_type]['generic_config'] = dict()
                for timeout_timer in timeout_timers:
                    timeout = _read_config(timeout_timer)
                    if timeout is not None:
                        tc_input[resource_type]['generic_config'][timeout_timer] = timeout

        tc_input['scaling_policy_name'] = _read_config('scaling_policy_name')
        tc_input['scaling_policy_list'] = _read_config('scaling_policy_list')
        tc_input['operate_vnf_data'] = _read_config('operate_vnf_data')

        # TODO: remove
        if 'vnf' not in tc_input.keys():
            tc_input['vnf'] = dict()
            tc_input['vnf']['instance_name'] = tc_exec_request['tc_name']
    execution_id = str(uuid.uuid4())
    execution_queue = Queue()
    message_queue = Queue()
    if _read_config('debug') is True:
        step_trigger = Event()
    else:
        step_trigger = None
    execution_process = Process(target=execute_test,
                                args=(tc_exec_request, tc_input, execution_queue, message_queue, step_trigger))
    execution_process.start()

    tc_inputs[execution_id] = tc_input

    execution_processes[execution_id] = execution_process
    execution_queues[execution_id] = execution_queue
    message_queues[execution_id] = message_queue
    step_triggers[execution_id] = step_trigger

    return {'execution_id': execution_id}


@route('/v1.0/exec/<execution_id>')
def get_status(execution_id):
    """
    Request mapped function that returns the status of the specified test execution ID.
    """
    try:
        execution_process = execution_processes[execution_id]
    except KeyError:
        response.status = 404
        return {'status': 'NOT_FOUND'}

    if execution_process.is_alive():
        return {'status': 'PENDING',
                'tc_input': tc_inputs[execution_id]}
    else:
        if tc_results.get(execution_id) is None:
            queue = execution_queues[execution_id]
            if queue.empty():
                tc_result = {}
            else:
                tc_result = queue.get_nowait()
            tc_results[execution_id] = tc_result
        return {'status': 'DONE',
                'tc_result': tc_results[execution_id],
                'tc_input': tc_inputs[execution_id]}


@route('/v1.0/exec/<execution_id>', method='DELETE')
def do_stop_exec(execution_id):
    """
    Request mapped function that stops the test execution with the specified ID.
    """
    execution_process = execution_processes[execution_id]
    execution_process.terminate()


@route('/v1.0/exec')
def all_status():
    """
    Request mapped function that returns the status of all test execution IDs.
    """
    status_list = list()
    for execution_id, execution_process in execution_processes.items():
        execution_status = dict()
        execution_status['execution_id'] = execution_id
        if execution_process.is_alive():
            execution_status['status'] = 'PENDING'
        else:
            execution_status['status'] = 'DONE'

        status_list.append(execution_status)

    return {'status_list': status_list}


@route('/v1.0/tcs')
def get_tcs():
    """
    Request mapped function that returns the mappings between all existing test case names and their module path.
    Example: "TC_VNF_STATE_TERM_003": "vnf/state/term"
    """
    tc_list = dict()
    tc_name_module_mapping = get_constructor_mapping('tc')
    for tc_name, tc_module_name in tc_name_module_mapping.items():
        tc_path = tc_module_name.rsplit('.', 1)[0].split('.', 1)[1].replace('.', '/')
        tc_list[tc_name] = tc_path

    return tc_list


def _read_resources(resource):
    """
    This function returns the contents of the JSON resource file corresponding to the specified resource.
    Example: if resource is 'mano', the function will return the contents of the file mano.json.
    """
    resource_file_path = os.path.join(json_file_path, '%s.json' % resource)
    try:
        with open(resource_file_path, 'r') as resource_file:
            all_resources = json.load(resource_file)
    except IOError:
        all_resources = {}

    return all_resources


def _read_resource(resource, name):
    """
    This function returns the details for the specified resource type and name.
    Example: if resource is 'mano' and name is tacker1 the function will return the details about the MANO with the name
    tacker1.
    """
    all_resources = _read_resources(resource)

    return all_resources.get(name, {})


def _write_resources(resource, all_resources):
    """
    This function creates a JSON resource file containing the specified resources.
    """
    resource_file_path = os.path.join(json_file_path, '%s.json' % resource)
    with open(resource_file_path, 'w') as resource_file:
        json.dump(all_resources, resource_file, sort_keys=True, indent=2)


@route('/v1.0/<resource:re:vim|mano|em|vnf|traffic|env>/<name>')
def get_resource(resource, name):
    """
    Request mapped function that returns the details for the specified resource type and name.
    """
    with lock[resource]:
        resource_params = _read_resource(resource, name)
        if resource_params == {}:
            response.status = 404

        return {name: resource_params}


@route('/v1.0/<resource:re:vim|mano|em|vnf|traffic|env>')
def get_resources(resource):
    """
    Request mapped function that returns all resources of the 'resource' type.
    """
    with lock[resource]:
        all_resources = _read_resources(resource)

        return all_resources


@route('/v1.0/<resource:re:vim|mano|em|vnf|traffic|env>/<name>', method='PUT')
def set_resource(resource, name):
    """
    Request mapped function that adds a new resource with the specified name.
    """
    with lock[resource]:
        all_resources = _read_resources(resource)
        all_resources[name] = request.json

        _write_resources(resource, all_resources)

        return {name: request.json}


@route('/v1.0/<resource:re:vim|mano|em|vnf|traffic|env>/<name>', method='DELETE')
def delete_resource(resource, name):
    """
    Request mapped function that deletes the resource with the specified name.
    """
    with lock[resource]:
        all_resources = _read_resources(resource)
        resource_params = all_resources.pop(name, {})

        _write_resources(resource, all_resources)

        if resource_params == {}:
            response.status = 404

        return {name: resource_params}


@route('/v1.0/config/<name>')
def get_config(name):
    """
    Request mapped function that returns the value corresponding to the specified key name in the JSON config file.
    """
    with lock['config']:
        return '"%s"' % _read_config(name)


@route('/v1.0/config/<name>', method='PUT')
def set_config(name):
    """
    Request mapped function that adds a key with the specified name and value specified in the request body in the JSON
    config file.
    """
    with lock['config']:
        _write_config(name, request.json)


@route('/v1.0/config/<name>', method='DELETE')
def delete_config(name):
    """
    Request mapped function that removes the key with the specified name and its corresponding value from the JSON
    config file.
    """
    with lock['config']:
        _delete_config(name)


@route('/v1.0/validate/<resource:re:vim|mano>', method="PUT")
def validate(resource):
    """
    Validate parameters for connecting to resource.
    """
    if resource in ['vim', 'mano']:
        try:
            construct_adapter(request.json['type'], resource, **request.json['client_config'])
        except Exception as e:
            response.status = 504
            return {'warning': '%s' % e}
        response.status = 200
        return {'message': "Object validated."}


@route('/v1.0/wait/<execution_id>')
def wait_for_exec(execution_id):
    """
    Request mapped function that waits for the process that executes the test corresponding to the specified execution
    ID to finish.
    """
    try:
        execution_process = execution_processes[execution_id]
    except KeyError:
        response.status = 404
        return {'status': 'NOT_FOUND'}

    execution_process.join()
    return {'status': 'DONE'}


@route('/v1.0/step/<execution_id>')
def wait_for_step(execution_id):
    try:
        message_queue = message_queues[execution_id]
    except KeyError:
        response.status = 404
        return {'error': 'NOT_FOUND'}

    if message_queue is None:
        msg = None
    else:
        msg = message_queue.get()

    if msg is None:
        message_queues[execution_id] = None
        response.status = 204
        return {'status': 'DONE'}
    else:
        response.status = 200
        return msg


@route('/v1.0/step/<execution_id>', method='POST')
def trigger_step(execution_id):
    try:
        step_trigger = step_triggers[execution_id]
    except KeyError:
        response.status = 404
        return {'error': 'NOT_FOUND'}

    if step_trigger is None:
        response.status = 204
        return {'error': 'Not running in debug mode'}
    else:
        step_trigger.set()
        response.status = 200
        return {}


run(host='0.0.0.0', port=8080, server='paste')
