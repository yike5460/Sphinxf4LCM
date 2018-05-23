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


import base64
import json
import logging
import os

import prettytable
import requests

from api.generic import constants

REPORT_DIR = '/var/log/vnflcv'

# Instantiate logger
LOG = logging.getLogger(__name__)


def report_test_case(report_file_name, tc_exec_request, tc_input, tc_result):
    report_file_path = os.path.join(REPORT_DIR, report_file_name)
    with open(report_file_path, 'w') as report_file:

        # Write run details
        report_file.write('*** Run details ***')
        report_file.write('\n\n')
        t = prettytable.PrettyTable(['Aspect', 'Value'])
        t.add_row(['Run ID', tc_exec_request['run_id'].replace('\n', '')])
        t.add_row(['Suite name', tc_exec_request['suite_name']])
        t.add_row(['TC name', tc_exec_request['tc_name']])
        t.add_row(['TC start time', tc_result['tc_start_time']])
        t.add_row(['TC end time', tc_result['tc_end_time']])
        t.add_row(['TC duration', tc_result['tc_duration']])
        report_file.write(t.get_string())
        report_file.write('\n\n')

        # Write steps summary
        report_file.write('* Steps summary:\n')
        t = prettytable.PrettyTable(['Step #', 'Name', 'Description', 'Duration (sec)', 'Status'],
                                    hrules=prettytable.ALL)
        t.max_width = 32
        for step_index, step_details in tc_result.get('steps', {}).items():
            t.add_row([step_index, step_details['name'], step_details['description'],
                       '%.3f' % step_details.get('duration', 0), step_details['status']])
        report_file.write(t.get_string())
        report_file.write('\n\n')

        # Write test case environment
        report_file.write('*** Test case environment ***')
        report_file.write('\n\n')
        t = prettytable.PrettyTable(['Module', 'Type', 'Name'])
        t.add_row(['MANO', tc_input.get('mano', {}).get('type'), tc_input.get('mano', {}).get('name', 'N/A')])
        t.add_row(['VIM', tc_input.get('vim', {}).get('type'), tc_input.get('vim', {}).get('name', 'N/A')])
        # t.add_row(['VNF', 'vcpe', tc_input.get('vnf', {}).get('name', 'N/A')])
        t.add_row(['Traffic', tc_input.get('traffic', {}).get('type'), tc_input.get('traffic', {}).get('name', 'N/A')])
        report_file.write(t.get_string())
        report_file.write('\n\n')

        t1 = prettytable.PrettyTable(
            ['Scaling type', 'Status', 'Scaling level', 'Traffic before scaling', 'Traffic after scaling'])
        print_scaling_results = False
        for direction in ['out', 'in', 'up', 'down']:
            scale_type = 'scaling_' + direction
            if bool(tc_result[scale_type]):
                # Set flag so the scaling results table will be printed
                print_scaling_results = True

                # Build the scale table row
                status = tc_result[scale_type].get('status', 'N/A')
                scale_level = tc_result[scale_type].get('level', 'N/A')

                load_before_scaling = tc_result[scale_type].get('traffic_before')
                load_after_scaling = tc_result[scale_type].get('traffic_after')

                percent_before_scaling = constants.traffic_load_percent_mapping.get(load_before_scaling, 'N/A')
                percent_after_scaling = constants.traffic_load_percent_mapping.get(load_after_scaling, 'N/A')

                traffic_before_scaling = str(percent_before_scaling) + ' %'
                traffic_after_scaling = str(percent_after_scaling) + ' %'

                # Add the row to the table
                t1.add_row([scale_type, status, scale_level, traffic_before_scaling, traffic_after_scaling])

        # Write scaling results, if any
        if print_scaling_results:
            report_file.write('* Scaling results (traffic values are expressed as percent of line rate)\n')
            report_file.write(t1.get_string())
            report_file.write('\n\n')

        # Write test case events
        report_file.write('* Events:\n')
        t = prettytable.PrettyTable(['Event', 'Duration (sec)', 'Details'])
        for event_name in tc_result.get('events', {}).keys():
            try:
                event_duration = round(tc_result['events'][event_name].get('duration'), 1)
            except TypeError:
                event_duration = 'N/A'
            event_details = tc_result['events'][event_name].get('details', '')
            t.add_row([event_name, event_duration, event_details])
        report_file.write(t.get_string())
        report_file.write('\n\n')

        # Write timestamps
        report_file.write('* Timestamps:\n')
        t = prettytable.PrettyTable(['Event', 'Timestamp (epoch time)'])
        for event_name, timestamp in tc_result.get('timestamps', {}).items():
            t.add_row([event_name, timestamp])
        report_file.write(t.get_string())
        report_file.write('\n\n')

        # Write VNF resources
        report_file.write('* VNF resources:\n')
        t_outside = prettytable.PrettyTable(
            ['VNF', 'VNFC', 'Resource type', 'Expected size', 'Actual size', 'Validation'], hrules=prettytable.ALL)
        t_outside.max_width = 16
        for key in tc_result.get('resources', {}).keys():
            for vnfc_id, vnfc_resources in tc_result['resources'].get(key, {}).items():
                row = [key, vnfc_id]
                t_inside = dict()
                t_inside['Resource type'] = prettytable.PrettyTable(['resource'], border=False, header=False)
                t_inside['Expected'] = prettytable.PrettyTable(['resource'], border=False, header=False)
                t_inside['Actual'] = prettytable.PrettyTable(['resource'], border=False, header=False)
                t_inside['Validation'] = prettytable.PrettyTable(['resource'], border=False, header=False)
                for resource_type, resource_size in vnfc_resources.items():
                    t_inside['Resource type'].add_row([resource_type])
                    t_inside['Expected'].add_row([resource_size])
                    t_inside['Actual'].add_row([resource_size])
                    t_inside['Validation'].add_row(['OK'])
                row.append(t_inside['Resource type'])
                row.append(t_inside['Expected'])
                row.append(t_inside['Actual'])
                row.append(t_inside['Validation'])
                t_outside.add_row(row)
        report_file.write(t_outside.get_string())
        report_file.write('\n\n')

        # Write test case results
        report_file.write('*** Test case results ***')
        report_file.write('\n\n')
        t = prettytable.PrettyTable(['Overall status', 'Error info'])
        t.max_width = 32
        t.add_row([tc_result['overall_status'], tc_result['error_info']])
        report_file.write(t.get_string())
        report_file.write('\n\n')


def html_report_test_case(html_report_file_name, tc_exec_request, tc_input, tc_result):
    report_file_path = os.path.join(REPORT_DIR, html_report_file_name)

    # Open html template
    with open('report_template.html', 'r') as template_file:
        template = template_file.read()

    # Open files for copying into .html
    with open('bootstrap.min.css', 'r') as f:
        bootstrap_css = f.read()
    with open('logo_Spirent.PNG', 'rb') as image_file:
        logo_base64 = base64.b64encode(image_file.read())
    with open('jquery.min.js', 'r') as f:
        jquery_js_data = f.read()
    with open('bootstrap.min.js', 'r') as f:
        bootstrap_js_data = f.read()

    # Substitute fields in the html report string
    # Select color and result values based on status
    if tc_result['overall_status'] in ['PASSED']:
        color, result = 'green', 'Pass'
    elif tc_result['overall_status'] in ['ERROR', 'FAILED']:
        color, result = 'red', 'Fail'
    else:
        color, result = '#8B0000', 'Error'

    # Format time
    start_time = (str(tc_result['tc_start_time']).split('T')[0] + ' ' +
                  str(tc_result['tc_start_time']).split('T')[1][0:8])

    # Populate Steps Summary table
    d_steps = {}
    for step_index in tc_result.get('steps', {}):
        d_steps[int(step_index)] = tc_result.get('steps', {})[step_index]
    steps_summary_body = ''
    for step_index, step_details in sorted(d_steps.items()):
        steps_summary_some_part = '''
                                        <tr>
                                            <td>%(step_index)s</td>
                                            <td>%(step_name)s</td>
                                            <td>%(step_description)s</td>
                                            <td>%(step_duration)s</td>
                                            <td>%(step_status)s</td>
                                        </tr>
         '''
        substitutes_local = {'step_index': str(step_index),
                             'step_name': str(step_details['name']),
                             'step_description': str(step_details['description']),
                             'step_duration': ('%.3f' % step_details.get('duration', 0)),
                             'step_status': str(step_details['status'])}
        steps_summary_body = steps_summary_body + (steps_summary_some_part % substitutes_local)

    # Write VNF resources
    vnf_resources = ''
    for key in tc_result.get('resources', {}).keys():
        for vnfc_id, vnfc_resources in tc_result['resources'].get(key, {}).items():
            count = 0
            for resource_type, resource_size in vnfc_resources.items():
                size = len(vnfc_resources.items())
                if count % size == 0:
                    vnf_resources_some_part = '''
                                                             <tr>
                                                                 <td rowspan="%(size)s">%(vnfc)s</td>
                                                                 <td rowspan="%(size)s">%(vnfcd)s</td>
                                                                 <td>%(resource_type)s</td>
                                                                 <td>%(resource_size)s</td>
                                                                 <td>%(resource_size)s</td>
                                                                 <td>%(status)s</td>
                                                             </tr>
                                 '''
                    substitutes_local = {'size': size,
                                         'vnfc': str(key),
                                         'vnfcd': str(vnfc_id),
                                         'resource_type': str(resource_type),
                                         'resource_size': str(resource_size),
                                         'status': 'OK'}
                    vnf_resources = vnf_resources + (vnf_resources_some_part % substitutes_local)
                else:
                    vnf_resources_some_part = '''
                                                             <tr>
                                                                 <td>%(resource_type)s</td>
                                                                 <td>%(resource_size)s</td>
                                                                 <td>%(resource_size)s</td>
                                                                 <td>%(status)s</td>
                                                             </tr>
                                 '''
                    substitutes_local = {'resource_type': str(resource_type),
                                         'resource_size': str(resource_size),
                                         'status': 'OK'}
                    vnf_resources = vnf_resources + (vnf_resources_some_part % substitutes_local)
                count += 1

    # Check for scaling info
    scaling_info = ''
    written_header = False
    for direction in ['out', 'in', 'up', 'down']:
        scale_type = 'scaling_' + direction
        if bool(tc_result[scale_type]):

            if not written_header:
                scaling_header = '''
                        <div class="col-xs-12">

                            <h4><a href="#scaling_results" data-toggle="collapse">&#65516; Scaling results &#65516;</a></h4>

                            <div id="scaling_results" class = "collapse">
                                <table class = "table table-bordered table-striped table-hover">
                                    <tbody>
                                        <tr>
                                            <th>Scaling type</th>
                                            <th>Status</th>
                                            <th>Scaling level</th>
                                            <th>Traffic before scaling</th>
                                            <th>Traffic after scaling</th>
                                        </tr>
                '''
                scaling_info = scaling_info + scaling_header

                written_header = True

            # Build the scale table row
            status = tc_result[scale_type].get('status', 'N/A')
            scale_level = tc_result[scale_type].get('level', 'N/A')

            load_before_scaling = tc_result[scale_type].get('traffic_before')
            load_after_scaling = tc_result[scale_type].get('traffic_after')

            percent_before_scaling = constants.traffic_load_percent_mapping.get(load_before_scaling, 'N/A')
            percent_after_scaling = constants.traffic_load_percent_mapping.get(load_after_scaling, 'N/A')

            traffic_before_scaling = str(percent_before_scaling) + ' %'
            traffic_after_scaling = str(percent_after_scaling) + ' %'

            scaling_results_some_part = '''
                                    <tr>
                                        <td>%(scale_type)s</td>
                                        <td>%(status)s</td>
                                        <td>%(scale_level)s</td>
                                        <td>%(traffic_before_scaling)s</td>
                                        <td>%(traffic_after_scaling)s</td>
                                    </tr>
            '''

            substitutes_local = {'scale_type': scale_type,
                                 'status': status,
                                 'scale_level': scale_level,
                                 'traffic_before_scaling': traffic_before_scaling,
                                 'traffic_after_scaling': traffic_after_scaling}
            scaling_info = scaling_info + (scaling_results_some_part % substitutes_local)

    if written_header:
        scaling_results_last_part = '''
                                </tbody>
                            </table>
                        </div>
                    </div>
                    '''
        scaling_info = scaling_info + scaling_results_last_part

    # Write timestamps
    time_stamps = ''
    for event_name, timestamp in tc_result.get('timestamps', {}).items():
        time_stamps_part = '''
                                    <tr>
                                        <td>%(event_name)s</td>
                                        <td>%(time_stamp)s</td>
                                    </tr>
        '''
        substitutes_local = {'event_name': str(event_name), 'time_stamp': str(timestamp)}
        time_stamps = time_stamps + (time_stamps_part % substitutes_local)

    # Write test case events
    events = ''
    for event_name in tc_result.get('events', {}).keys():
        try:
            event_duration = round(tc_result['events'][event_name].get('duration'), 1)
        except TypeError:
            event_duration = 'N/A'
        event_details = tc_result['events'][event_name].get('details', '')

        events_part = '''
                                    <tr>
                                        <td>%(event_name)s</td>
                                        <td>%(event_duration)s</td>
                                        <td>%(event_details)s</td>
                                    </tr>
        '''
        substitutes_local = {'event_name': str(event_name),
                             'event_duration': str(event_duration),
                             'event_details': str(event_details)}
        events = events + (events_part % substitutes_local)

    # Write the main substitution dictionary
    substitutes = {
        'tc_name': str(tc_exec_request['tc_name']),
        'start_time': start_time,
        'bootstrap_css_file': bootstrap_css,
        'logo': logo_base64,
        'color': color,
        'result': result,
        'run_id': str(tc_exec_request['run_id']),
        'suite_name': str(tc_exec_request['suite_name']),
        'tc_start_time': str(tc_result['tc_start_time']),
        'tc_end_time': str(tc_result['tc_end_time']),
        'tc_duration': str(tc_result['tc_duration']),
        'error_info': str(tc_result['error_info']),
        'mano_type': str(tc_input.get('mano', {}).get('type')),
        'mano_name': str(tc_input.get('mano', {}).get('name', 'N/A')),
        'vim_type': str(tc_input.get('vim', {}).get('type')),
        'vim_vim': str(tc_input.get('vim', {}).get('vim', 'N/A')),
        'traffic_type': str(tc_input.get('traffic', {}).get('type')),
        'traffic_vim': str(tc_input.get('traffic', {}).get('vim', 'N/A')),
        'steps_summary_body': steps_summary_body,
        'vnf_resources': vnf_resources,
        'scaling_info': scaling_info,
        'time_stamps': time_stamps,
        'events': events,
        'jquery_js_data': jquery_js_data,
        'bootstrap_js_data': bootstrap_js_data}

    # Write the html report file
    with open(report_file_path, 'w') as report_file:
        report_file.write(template % substitutes)


def kibana_report(kibana_srv, tc_exec_request, tc_input, tc_result):
    json_dict = dict()
    json_dict['run_id'] = int(tc_exec_request['run_id'])
    json_dict['suite_name'] = tc_exec_request['suite_name']
    json_dict['tc_name'] = tc_exec_request['tc_name']
    json_dict['tc_start_time'] = tc_result['tc_start_time']
    json_dict['tc_end_time'] = tc_result['tc_end_time']
    json_dict['tc_duration'] = tc_result['tc_duration']
    json_dict['tc_status'] = tc_result['overall_status']
    json_dict['error_info'] = tc_result['error_info']

    json_dict['environment'] = dict()
    json_dict['environment']['vim'] = 'OpenStack'
    json_dict['environment']['mano'] = tc_input['mano']['type']
    json_dict['environment']['vnf'] = 'CirrOS'
    json_dict['environment']['traffic'] = 'STCv'
    json_dict['environment']['em'] = 'None'

    durations = dict()
    durations['instantiate'] = tc_result.get('events', {}).get('instantiate_vnf', {}).get('duration') or \
                               tc_result.get('events', {}).get('instantiate_ns', {}).get('duration')
    durations['terminate'] = tc_result.get('events', {}).get('terminate_vnf', {}).get('duration') or \
                             tc_result.get('events', {}).get('terminate_ns', {}).get('duration')
    durations['start'] = tc_result.get('events', {}).get('start_vnf', {}).get('duration') or \
                         tc_result.get('events', {}).get('ns_update_start_vnf', {}).get('duration')
    durations['stop'] = tc_result.get('events', {}).get('stop_vnf', {}).get('duration') or \
                        tc_result.get('events', {}).get('ns_update_stop_vnf', {}).get('duration')
    durations['scale_out'] = tc_result.get('events', {}).get('scale_out_vnf', {}).get('duration') or \
                             tc_result.get('events', {}).get('scale_out_ns', {}).get('duration')
    durations['scale_in'] = tc_result.get('events', {}).get('scale_in_vnf', {}).get('duration') or \
                            tc_result.get('events', {}).get('scale_in_ns', {}).get('duration')
    durations['scale_to_level'] = tc_result.get('events', {}).get('scale_to_level_ns', {}).get('duration')
    durations['scale_from_level'] = tc_result.get('events', {}).get('scale_from_level_ns', {}).get('duration')
    durations['service_disruption'] = tc_result.get('events', {}).get('service_disruption', {}).get('duration')
    durations['traffic_fwd_disruption'] = tc_result.get('events', {}).get('traffic_fwd_disruption', {}).get('duration')

    json_dict['durations'] = dict((k, v) for k, v in durations.iteritems() if v is not None)

    try:
        requests.post(url='http://' + kibana_srv + ':9200/nfv/tc-exec', json=json_dict)
    except Exception as e:
        LOG.debug('Unable to communicate to ElasticSearch server: %s' % kibana_srv)
        LOG.exception(e)


def dump_raw_json(json_file_name, tc_exec_request, tc_input, tc_result):
    json_file_path = os.path.join(REPORT_DIR, json_file_name)
    with open(json_file_path, 'w') as json_file:
        raw_json = {
            'tc_exec_request': tc_exec_request,
            'tc_input': tc_input,
            'tc_result': tc_result
        }

        json.dump(raw_json, json_file, indent=2)
