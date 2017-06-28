import importlib
import json
import uuid
from multiprocessing import Process, Queue

from bottle import route, run, request, response

execution_queues = dict()
execution_processes = dict()
tc_results = dict()

# TODO: move mapping logic in test_cases module
mapping_file_path = '../test_cases/tc_mapping.json'
tc_name_module_mapping = None


def get_tc_class(tc_name):
    global tc_name_module_mapping

    if tc_name_module_mapping is None:
        with open(mapping_file_path, 'r') as mapping_file:
            tc_name_module_mapping = json.load(mapping_file)

    tc_module_name = tc_name_module_mapping[tc_name]
    tc_module = importlib.import_module(tc_module_name)
    tc_class = getattr(tc_module, tc_name)

    return tc_class


def execute_test(tc_class, tc_input, queue):
    tc_result = tc_class(tc_input).execute()
    queue.put(tc_result)


@route('/version')
def get_version():
    return {'versions': ['v1.0']}


@route('/v1.0/exec', method='POST')
def do_exec():
    tc_name = request.json['tc_name']
    tc_input = request.json['tc_input']

    tc_class = get_tc_class(tc_name)

    execution_id = str(uuid.uuid4())
    queue = Queue()
    execution_process = Process(target=execute_test, args=(tc_class, tc_input, queue))
    execution_process.start()

    execution_processes[execution_id] = execution_process
    execution_queues[execution_id] = queue

    return {'execution_id': execution_id}


@route('/v1.0/exec/<execution_id>')
def get_status(execution_id):
    try:
        execution_process = execution_processes[execution_id]
    except KeyError:
        response.status = 404
        return {'status': 'NOT_FOUND'}

    if execution_process.is_alive():
        return {'status': 'PENDING'}
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
                'tc_result': tc_results[execution_id]}


@route('/v1.0/exec/<execution_id>', method='DELETE')
def do_stop_exec(execution_id):
    execution_process = execution_processes[execution_id]
    execution_process.terminate()


@route('/v1.0/exec')
def all_status():
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
    resource_file_name = '%s.json' % resource
    try:
        with open(resource_file_name, 'r') as resource_file:
            all_resources = json.load(resource_file)
    except IOError:
        all_resources = {}

    return all_resources


def _read_resource(resource, name):
    all_resources = _read_resources(resource)

    return all_resources.get(name, {})


def _write_resources(resource, all_resources):
    resource_file_name = '%s.json' % resource
    with open(resource_file_name, 'w') as resource_file:
        json.dump(all_resources, resource_file, sort_keys=True, indent=2)


@route('/v1.0/<resource:re:vim|mano|em|vnf|traffic>/<name>')
def get_resource(resource, name):
    resource_params = _read_resource(resource, name)
    if resource_params == {}:
        response.status = 404

    return {name: resource_params}


@route('/v1.0/<resource:re:vim|mano|em|vnf|traffic>')
def get_resources(resource):
    all_resources = _read_resources(resource)

    return all_resources


@route('/v1.0/<resource:re:vim|mano|em|vnf|traffic>/<name>', method='PUT')
def set_resource(resource, name):
    all_resources = _read_resources(resource)
    all_resources[name] = request.json

    _write_resources(resource, all_resources)

    return {name: request.json}


@route('/v1.0/<resource:re:vim|mano|em|vnf|traffic>/<name>', method='DELETE')
def delete_resource(resource, name):
    all_resources = _read_resources(resource)
    resource_params = all_resources.pop(name, {})

    _write_resources(resource, all_resources)

    if resource_params == {}:
        response.status = 404

    return {name: resource_params}


run(host='0.0.0.0', port=8080, debug=False)
