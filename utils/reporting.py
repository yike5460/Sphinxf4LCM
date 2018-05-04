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
        for step_index, step_details in tc_result.get('steps', {}).items():
            t.add_row([step_index, step_details['name'], step_details['description'], step_details['status']])
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


def html_report_test_case(html_report_file_name, tc_exec_request, tc_input, tc_result):
    report_file_path = os.path.join(REPORT_DIR, html_report_file_name)
    with open(report_file_path, 'w') as report_file:

        # Write HTML header
        report_file.write('<!DOCTYPE html> \n')
        report_file.write('<html> \n ')
        report_file.write('<head> \n ')
        report_file.write('<title> VNF/NS TEST REPORT </title> \n ')

        ## Table style section
        report_file.write('<style> \n')
        report_file.write("table {")
        report_file.write("    font-family: arial, sans-serif; \n")
        report_file.write("    border-collapse: collapse; \n")
        report_file.write("    width: 25% \n")
        report_file.write("} \n")

        report_file.write("td { \n")
        report_file.write("    border: 1px solid black; \n")
        report_file.write("    text-align: center; \n")
        report_file.write("    padding: 8px; \n")
        report_file.write("} \n")

        report_file.write("th { \n")
        report_file.write("    border: 2px solid black; \n")
        report_file.write("    text-align: center; \n")
        report_file.write("    padding: 8px; \n")
        report_file.write("    background-color: white")
        report_file.write("} \n")

        report_file.write("tr:nth-child(even) { \n")
        report_file.write("    background-color: #dddddd \n")
        report_file.write("} \n")

        report_file.write("img { \n")
        report_file.write("width:100%; \n")
        report_file.write("} \n")
        report_file.write('</style>')

        report_file.write('</head> \n ')

        report_file.write('<body>')

        report_file.write('<h1> VNF/NS TEST REPORT </h1> \n ')

        report_file.write('<img src="/var/log/vnflcv/logo_Spirent.PNG" alt="Spirent logo" style="width:100px;height:100px;">')

        # Write run details
        report_file.write('<h2> RUN DETAILS </h2> \n ')
        report_file.write("<table> \n")

        ## Write table header
        report_file.write("    <tr> \n")
        report_file.write("        <th>Aspect</th> \n")
        report_file.write("        <th>Value</th> \n")
        report_file.write("    </tr> \n")

        ## Write table body
        report_file.write("    <tr> \n")
        report_file.write("        <td>Run ID</td> \n")
        report_file.write("        <td>" + tc_exec_request['run_id'] + "</td> \n")
        report_file.write("    </tr> \n")

        report_file.write("    <tr> \n")
        report_file.write("        <td>Suite name</td> \n")
        report_file.write("        <td>" + tc_exec_request['suite_name'] + "</td> \n")
        report_file.write("    </tr> \n")

        report_file.write("    <tr> \n")
        report_file.write("        <td>TC name</td> \n")
        report_file.write("        <td>" + tc_exec_request['tc_name'] + "</td> \n")
        report_file.write("    </tr> \n")

        report_file.write("    <tr> \n")
        report_file.write("        <td>TC start time</td> \n")
        report_file.write("        <td>" + tc_result['tc_start_time'] + "</td> \n")
        report_file.write("    </tr> \n")

        report_file.write("    <tr> \n")
        report_file.write("        <td>TC end time</td> \n")
        report_file.write("        <td>"+ tc_result['tc_end_time'] + "</td> \n")
        report_file.write("    </tr> \n")

        report_file.write("    <tr> \n")
        report_file.write("        <td>TC duration</td> \n")
        report_file.write("        <td>"+ tc_result['tc_duration'] + "</td> \n")
        report_file.write("    </tr> \n")

        report_file.write("</table \n")

        # Write steps summary
        report_file.write('<h2> Steps Summary </h2> \n ')

        report_file.write("<table> \n")

        ## Write table header
        report_file.write("    <tr> \n")
        report_file.write("        <th>Step #</th> \n")
        report_file.write("        <th>Name</th> \n")
        report_file.write("        <th>Description</th> \n")
        report_file.write("        <th>Status</th> \n")
        report_file.write("    </tr> \n")

        ## Write table body
        for step_index, step_details in tc_result.get('steps', {}).items():
            report_file.write("    <tr> \n")
            report_file.write("        <td>"+ step_index +"</td> \n")
            report_file.write("        <td>" + step_details['name'] + "</td> \n")
            report_file.write("        <td>" + step_details['description'] + "</td> \n")
            report_file.write("        <td>" + step_details['status'] + "</td> \n")
            report_file.write("    </tr> \n")

        report_file.write("</table> \n")



        # Write test case environment

        report_file.write('<h2> Test Case Environment  </h2> \n ')
        report_file.write("<table> \n")

        ## Write table header
        report_file.write("    <tr> \n")
        report_file.write("        <th>Module</th> \n")
        report_file.write("        <th>Type</th> \n")
        report_file.write("    </tr> \n")

        ## Write table body
        report_file.write("    <tr> \n")
        report_file.write("        <td>MANO</th> \n")
        report_file.write("        <td>"+ tc_input.get('mano', {}).get('type') +"</th> \n")
        report_file.write("    </tr> \n")

        report_file.write("    <tr> \n")
        report_file.write("        <td>VIM</th> \n")
        report_file.write("        <td>OpenStack</th> \n")
        report_file.write("    </tr> \n")

        report_file.write("    <tr> \n")
        report_file.write("        <td>VNF</th> \n")
        report_file.write("        <td>vCPE</th> \n")
        report_file.write("    </tr> \n")

        report_file.write("    <tr> \n")
        report_file.write("        <td>Traffic</th> \n")
        report_file.write("        <td>"+str(tc_input.get('traffic', {}).get('type'))+"</th> \n")
        report_file.write("    </tr> \n")

        report_file.write("</table> \n")

        # Check for scaling info
        print_scaling_results = False
        wrote_header = False
        for direction in ['out', 'in', 'up', 'down']:
            scale_type = 'scaling_' + direction
            if bool(tc_result[scale_type]):
                # Set flag so the scaling results table will be printed
                print_scaling_results = True


                if not wrote_header:
                    report_file.write('<h2> Scaling results (traffic values are expressed as percent of line rate) </h2> \n ')
                    report_file.write("<table> \n")

                    ## Write table header
                    report_file.write("    <tr> \n")
                    report_file.write("        <th>'Scaling type'</th> \n")
                    report_file.write("        <th>'Status'> \n")
                    report_file.write("        <th>'Scaling level'> \n")
                    report_file.write("        <th>'Traffic before scaling'> \n")
                    report_file.write("        <th>'Traffic after scaling'> \n")
                    report_file.write("    </tr> \n")
                    wrote_header = True

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
                report_file.write("    <tr> \n")
                report_file.write("        <td>" + scale_type + "</th> \n")
                report_file.write("        <td>" + status + "</th> \n")
                report_file.write("        <td>" + scale_level + "</th> \n")
                report_file.write("        <td>" + traffic_before_scaling + "</th> \n")
                report_file.write("        <td>" + traffic_after_scaling + "</th> \n")
                report_file.write("    </tr> \n")


        # Write test case events

        report_file.write('<h2> Events  </h2> \n ')
        report_file.write("<table> \n")

        ## Write table header

        report_file.write("    <tr> \n")
        report_file.write("        <th>Event</th> \n")
        report_file.write("        <th>Duration (sec) </th> \n")
        report_file.write("        <th>Details</th> \n")
        report_file.write("    </tr> \n")

        for event_name in tc_result.get('events', {}).keys():
            try:
                event_duration = round(tc_result['events'][event_name].get('duration'), 1)
            except TypeError:
                event_duration = 'N/A'
            event_details = tc_result['events'][event_name].get('details', '')

            ## Write table body
            report_file.write("    <tr> \n")
            report_file.write("        <td>" + event_name + "</th> \n")
            report_file.write("        <td>" + event_duration + "</th> \n")
            report_file.write("        <td>" + event_details + "</th> \n")
            report_file.write("    </tr> \n")

        report_file.write("</table> \n")

        # Write timestamps
        report_file.write('<h2> Timestamps  </h2> \n ')
        report_file.write("<table> \n")

        ## Write table header

        report_file.write("    <tr> \n")
        report_file.write("        <th>Event</th> \n")
        report_file.write("        <th>Timestamp (epoch time) </th> \n")
        report_file.write("    </tr> \n")

        for event_name, timestamp in tc_result.get('timestamps', {}).items():
            report_file.write("    <tr> \n")
            report_file.write("        <td>" + event_name + "</th> \n")
            report_file.write("        <td>" + timestamp + "</th> \n")
            report_file.write("    </tr> \n")

        report_file.write("</table> \n")

        # Write VNF resources
        report_file.write('<h2> VNF resources  </h2> \n ')
        report_file.write("<table> \n")

        ## Write table header

        report_file.write("    <tr> \n")
        report_file.write("        <th>VNF</th> \n")
        report_file.write("        <th>VNFC</th> \n")
        report_file.write("        <th>Resource type </th> \n")
        report_file.write("        <th>Expected size </th> \n")
        report_file.write("        <th>Actual size </th> \n")
        report_file.write("        <th>Validation</th> \n")
        report_file.write("    </tr> \n")

        # for key in tc_result.get('resources', {}).keys():
        #     for vnfc_id, vnfc_resources in tc_result['resources'].get(key, {}).items():
        #         for resource_type, resource_size in vnfc_resources.items():

        report_file.write("</table> \n")

        #Write test case results

        report_file.write(" Test case results ")
        report_file.write("<table> \n")

        ## Write table header

        report_file.write("    <tr> \n")
        report_file.write("        <th>Overall status</th> \n")
        report_file.write("        <th>Error info</th> \n")
        report_file.write("    </tr> \n")

        ## Write table body

        report_file.write("    <tr> \n")
        report_file.write("        <td>" + tc_result['overall_status'] + "</th> \n")
        report_file.write("        <td>" + tc_result['error_info'] + "</th> \n")
        report_file.write("    </tr> \n")

        report_file.write("</table> \n")

        # # Write VNF resources
        # report_file.write('* VNF resources:\n')
        # t_outside = prettytable.PrettyTable(
        #                                  ['VNF', 'VNFC', 'Resource type', 'Expected size', 'Actual size', 'Validation'],
        #                                  hrules=prettytable.ALL)
        # t_outside.max_width = 16
        # for key in tc_result.get('resources', {}).keys():
        #     for vnfc_id, vnfc_resources in tc_result['resources'].get(key, {}).items():
        #         row = [key, vnfc_id]
        #         # t_inside = [prettytable.PrettyTable(['resource'], border=False, header=False) for i in range(0, 4)]
        #         t_inside = dict()
        #         t_inside['Resource type'] = prettytable.PrettyTable(['resource'], border=False, header=False)
        #         t_inside['Expected size'] = prettytable.PrettyTable(['resource'], border=False, header=False)
        #         t_inside['Actual size'] = prettytable.PrettyTable(['resource'], border=False, header=False)
        #         t_inside['Validation'] = prettytable.PrettyTable(['resource'], border=False, header=False)
        #         for resource_type, resource_size in vnfc_resources.items():
        #             t_inside['Resource type'].add_row([resource_type])
        #             t_inside['Expected size'].add_row([resource_size])
        #             t_inside['Actual size'].add_row([resource_size])
        #             t_inside['Validation'].add_row(['OK'])
        #         row.append(t_inside['Resource type'])
        #         row.append(t_inside['Expected size'])
        #         row.append(t_inside['Actual size'])
        #         row.append(t_inside['Validation'])
        #         t_outside.add_row(row)
        # report_file.write(t_outside.get_string())
        # report_file.write('\n\n')
        #
        # # Write test case results
        # report_file.write('*** Test case results ***')
        # report_file.write('\n\n')
        # t = prettytable.PrettyTable(['Overall status', 'Error info'])
        # t.add_row([tc_result['overall_status'], tc_result['error_info']])
        # report_file.write(t.get_string())
        # report_file.write('\n\n')



        report_file.write('</body>')
        report_file.write('</html>')

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
