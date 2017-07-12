import importlib
import json
import logging
import uuid
from datetime import datetime
from multiprocessing import Process, Queue

from bottle import route, run, request, response

from api.adapter import construct_adapter
from utils import reporting, logging_module

execution_queues = dict()
execution_processes = dict()
tc_results = dict()
tc_inputs = dict()

# TODO: move mapping logic in test_cases module
mapping_file_path = '../test_cases/tc_mapping.json'
tc_name_module_mapping = None

config_file_path = 'config.json'


def _read_config(key):
    """
    This function returns the content of the JSON config file.
    """
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
    try:
        with open(config_file_path, 'r') as config_file:
            config = json.load(config_file)
    except Exception:
        config = {}

    config.pop(key, None)

    with open(config_file_path, 'w') as config_file:
        json.dump(config, config_file, sort_keys=True, indent=2)


def get_tc_class(tc_name):
    """
    This function returns the test class for the specified test case name.
    """
    global tc_name_module_mapping

    if tc_name_module_mapping is None:
        with open(mapping_file_path, 'r') as mapping_file:
            tc_name_module_mapping = json.load(mapping_file)

    tc_module_name = tc_name_module_mapping[tc_name]
    tc_module = importlib.import_module(tc_module_name)
    tc_class = getattr(tc_module, tc_name)

    return tc_class


def execute_test(tc_exec_request, tc_input, queue):
    """
    This function is used as a process target and it starts the execution of a test case.
    """
    tc_name = tc_exec_request['tc_name']
    tc_class = get_tc_class(tc_name)

    root_logger = logging.getLogger()
    logging_module.configure_logger(root_logger, file_level='DEBUG', log_filename=tc_name)

    tc_start_time = datetime.utcnow()
    tc_result = tc_class(tc_input).execute()
    tc_end_time = datetime.utcnow()

    tc_result['tc_start_time'] = tc_start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    tc_result['tc_end_time'] = tc_end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    tc_result['tc_duration'] = str(tc_end_time - tc_start_time)

    queue.put(tc_result)

    kibana_srv = _read_config('kibana-srv')
    if kibana_srv is not None:
        reporting.kibana_report(kibana_srv, tc_exec_request, tc_input, tc_result)


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

    tc_input = tc_exec_request.get('tc_input')
    if tc_input is None:
        active_env = _read_config('active-env')
        if active_env is None:
            response.status = 400
            return {'error': 'Active environment not set'}

        tc_input = dict()
        for resource_type, resource_name in _read_resource('env', active_env).items():
            resource_params = _read_resource(resource_type, resource_name)
            tc_input[resource_type + '_params'] = resource_params

        tc_input['vnfd_id'] = _read_config('vnfd-id')

        tc_input['vnf'] = dict()
        tc_input['vnf']['instance_name'] = tc_exec_request['tc_name']

    execution_id = str(uuid.uuid4())
    queue = Queue()
    execution_process = Process(target=execute_test, args=(tc_exec_request, tc_input, queue))
    execution_process.start()

    tc_inputs[execution_id] = tc_input

    execution_processes[execution_id] = execution_process
    execution_queues[execution_id] = queue

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
            queue.close()
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

    global tc_name_module_mapping

    if tc_name_module_mapping is None:
        with open(mapping_file_path, 'r') as mapping_file:
            tc_name_module_mapping = json.load(mapping_file)

    for tc_name, tc_module_name in tc_name_module_mapping.items():
        tc_path = tc_module_name.rsplit('.', 1)[0].split('.', 1)[1].replace('.', '/')
        tc_list[tc_name] = tc_path

    return tc_list


def _read_resources(resource):
    """
    This function returns the contents of the JSON resource file corresponding to the specified resource.
    Example: if resource is 'mano', the function will return the contents of the file mano.json.
    """
    resource_file_name = '%s.json' % resource
    try:
        with open(resource_file_name, 'r') as resource_file:
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
    resource_file_name = '%s.json' % resource
    with open(resource_file_name, 'w') as resource_file:
        json.dump(all_resources, resource_file, sort_keys=True, indent=2)


@route('/v1.0/<resource:re:vim|mano|em|vnf|traffic|env>/<name>')
def get_resource(resource, name):
    """
    Request mapped function that returns the details for the specified resource type and name.
    """
    resource_params = _read_resource(resource, name)
    if resource_params == {}:
        response.status = 404

    return {name: resource_params}


@route('/v1.0/<resource:re:vim|mano|em|vnf|traffic|env>')
def get_resources(resource):
    """
    Request mapped function that returns all resources of the 'resource' type.
    """
    all_resources = _read_resources(resource)

    return all_resources


@route('/v1.0/<resource:re:vim|mano|em|vnf|traffic|env>/<name>', method='PUT')
def set_resource(resource, name):
    """
    Request mapped function that adds a new resource with the specified name.
    """
    all_resources = _read_resources(resource)
    all_resources[name] = request.json

    _write_resources(resource, all_resources)

    if resource in ['vim', 'mano']:
        try:
            construct_adapter(request.json['type'], resource, **request.json['client_config'])
        except Exception as e:
            response.status = 504
            return {'warning': e.message}

    return {name: request.json}


@route('/v1.0/<resource:re:vim|mano|em|vnf|traffic|env>/<name>', method='DELETE')
def delete_resource(resource, name):
    """
    Request mapped function that deletes the resource with the specified name.
    """
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
    return '"%s"' % _read_config(name)


@route('/v1.0/config/<name>', method='PUT')
def set_config(name):
    """
    Request mapped function that adds a key with the specified name and value specified in the request body in the JSON
    config file.
    """
    _write_config(name, request.json)


@route('/v1.0/config/<name>', method='DELETE')
def remove_config(name):
    """
    Request mapped function that removes the key with the specified name and its corresponding value from the JSON
    config file.
    """
    _delete_config(name)


run(host='0.0.0.0', port=8080, debug=False)
