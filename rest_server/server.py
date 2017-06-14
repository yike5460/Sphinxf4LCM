import importlib
import json
import uuid
from threading import Thread
from bottle import route, run, request, response, abort

execution_threads = dict()
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


@route('/v1.0/version')
def version():
    return {'version': 'v1.0'}


def execute_test(tc_class, tc_input, execution_id):
    tc_result = tc_class(tc_input).execute()
    tc_results[execution_id] = tc_result


@route('/v1.0/exec', method='POST')
def do_exec():
    tc_name = request.json['tc_name']
    tc_input = request.json['tc_input']

    tc_class = get_tc_class(tc_name)

    execution_id = str(uuid.uuid4())
    execution_thread = Thread(target=execute_test, args=(tc_class, tc_input, execution_id))
    execution_thread.start()

    execution_threads[execution_id] = execution_thread

    return {'execution_id': execution_id}


@route('/v1.0/exec/<execution_id>')
def get_status(execution_id):
    try:
        execution_thread = execution_threads[execution_id]
    except KeyError:
        response.status = 404
        return {'status': 'NOT_FOUND'}

    if execution_thread.is_alive():
        return {'status': 'PENDING'}
    else:
        return {'status': 'DONE',
                'tc_result': tc_results[execution_id]}


@route('/v1.0/exec')
def all_status():
    status_list = list()
    for execution_id, execution_thread in execution_threads.items():
        execution_status = dict()
        execution_status['execution_id'] = execution_id
        if execution_thread.is_alive():
            execution_status['status'] = 'PENDING'
        else:
            execution_status['status'] = 'DONE'

        status_list.append(execution_status)

    return {'status_list': status_list}


run(host='0.0.0.0', port=8080, debug=True)