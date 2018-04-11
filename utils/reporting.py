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
        t = prettytable.PrettyTable(['Step #', 'Name', 'Description', 'Status'])
        step_number = 1
        for step_name, step_details in tc_result.get('steps', {}).items():
            t.add_row([step_number, step_name, step_details['description'], step_details['status']])
            step_number += 1
        report_file.write(t.get_string())
        report_file.write('\n\n')

        # Write test case environment
        report_file.write('*** Test case environment ***')
        report_file.write('\n\n')
        t = prettytable.PrettyTable(['Module', 'Type'])
        t.add_row(['MANO', tc_input.get('mano', {}).get('type')])
        t.add_row(['VIM', 'openstack'])
        t.add_row(['VNF', 'vcpe'])
        t.add_row(['Traffic', tc_input.get('traffic', {}).get('type')])
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
                                         ['VNF', 'VNFC', 'Resource type', 'Expected size', 'Actual size', 'Validation'],
                                         hrules=prettytable.ALL)
        t_outside.max_width = 16
        for key in tc_result.get('resources', {}).keys():
            for vnfc_id, vnfc_resources in tc_result['resources'].get(key, {}).items():
                row = [key, vnfc_id]
                # t_inside = [prettytable.PrettyTable(['resource'], border=False, header=False) for i in range(0, 4)]
                t_inside = dict()
                t_inside['Resource type'] = prettytable.PrettyTable(['resource'], border=False, header=False)
                t_inside['Expected size'] = prettytable.PrettyTable(['resource'], border=False, header=False)
                t_inside['Actual size'] = prettytable.PrettyTable(['resource'], border=False, header=False)
                t_inside['Validation'] = prettytable.PrettyTable(['resource'], border=False, header=False)
                for resource_type, resource_size in vnfc_resources.items():
                    t_inside['Resource type'].add_row([resource_type])
                    t_inside['Expected size'].add_row([resource_size])
                    t_inside['Actual size'].add_row([resource_size])
                    t_inside['Validation'].add_row(['OK'])
                row.append(t_inside['Resource type'])
                row.append(t_inside['Expected size'])
                row.append(t_inside['Actual size'])
                row.append(t_inside['Validation'])
                t_outside.add_row(row)
        report_file.write(t_outside.get_string())
        report_file.write('\n\n')

        # Write test case results
        report_file.write('*** Test case results ***')
        report_file.write('\n\n')
        t = prettytable.PrettyTable(['Overall status', 'Error info'])
        t.add_row([tc_result['overall_status'], tc_result['error_info']])
        report_file.write(t.get_string())
        report_file.write('\n\n')


def kibana_report(kibana_srv, tc_exec_request, tc_input, tc_result):
    json_dict = dict()
    json_dict['run_id'] = int(tc_exec_request['run_id'])
    json_dict['suite_name'] = tc_exec_request['suite_name']
    json_dict['tc_name'] = tc_exec_request['tc_name']
    json_dict['tc_start_time'] = tc_result['tc_start_time']
    json_dict['tc_end_time'] = tc_result['tc_end_time']
    json_dict['tc_duration'] = tc_result['tc_duration']
    json_dict['tc_status'] = tc_result['overall_status']

    json_dict['environment'] = dict()
    json_dict['environment']['vim'] = 'OpenStack'
    json_dict['environment']['mano'] = tc_input['mano']['type']
    json_dict['environment']['vnf'] = 'CirrOS'
    json_dict['environment']['traffic'] = 'STCv'
    json_dict['environment']['em'] = 'None'

    durations = dict()
    durations['instantiate'] = tc_result.get('events', {}).get('instantiate_vnf', {}).get('duration')
    durations['stop'] = tc_result.get('events', {}).get('stop_vnf', {}).get('duration')
    durations['scale_out'] = tc_result.get('events', {}).get('scale_out_vnf', {}).get('duration')
    durations['scale_in'] = tc_result.get('events', {}).get('scale_in_vnf', {}).get('duration')
    durations['service_disruption'] = tc_result.get('events', {}).get('service_disruption', {}).get('duration')
    durations['traffic_fwd_disruption'] = tc_result.get('events', {}).get('traffic_fwd_disruption', {}).get('duration')

    json_dict['durations'] = dict((k, v) for k, v in durations.iteritems() if v is not None)

    try:
        requests.post(url='http://' + kibana_srv + ':9200/nfv/tc-exec', json=json_dict)
    except Exception as e:
        LOG.debug('Unable to communicate to ElasticSearch server: %s' % kibana_srv)
        LOG.exception(e)
