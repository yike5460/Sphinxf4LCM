import time

from prettytable import PrettyTable

from api.generic import constants


def report_test_case(tc_input, tc_result):
    time.sleep(1)
    print
    print '*** Test case environment ***'
    t = PrettyTable(['Module', 'Type'])
    t.add_row(['VNFM', tc_input.get('vnfm_params', {}).get('type')])
    t.add_row(['VIM', tc_input.get('vim_params', {}).get('type')])
    t.add_row(['VNF', tc_input.get('vnf', {}).get('type')])
    t.add_row(['Traffic', tc_input.get('traffic_params', {}).get('type')])
    print t
    print

    print '*** Test case results ***'
    t = PrettyTable(['Overall status', 'Error info'])
    t.add_row([tc_result['overall_status'], tc_result['error_info']])
    print t
    print

    t1 = PrettyTable(['Scaling type', 'Status', 'Scaling level', 'Traffic before scaling', 'Traffic after scaling'])
    port_speed = tc_input['traffic_params']['traffic_config']['port_speed']
    print_scaling_results = False
    for direction in ['out', 'in', 'up', 'down']:
        scale_type = 'scaling_' + direction
        if bool(tc_result[scale_type]):

            # Set flag so the scaling results table will be printed
            print_scaling_results = True

            # Build the scale table row
            status = tc_result[scale_type].get('status', None)
            scale_level = tc_result[scale_type].get('level', None)
            load_before_scaling = tc_result[scale_type].get('traffic_before', None)
            load_after_scaling = tc_result[scale_type].get('traffic_after', None)
            traffic_before_scaling = str(
                        constants.traffic_load_percent_mapping.get(load_before_scaling, 0) * port_speed / 100) + ' Mbps'
            traffic_after_scaling = str(
                        constants.traffic_load_percent_mapping.get(load_after_scaling, 0) * port_speed / 100) + ' Mbps'

            # Add the row to the table
            t1.add_row([scale_type, status, scale_level, traffic_before_scaling, traffic_after_scaling])

    if print_scaling_results:
        print '* Scaling results'
        print t1
        print

    print '* VNF resources:'
    for key in tc_result.get('resources', {}).keys():
        print '%s:' % key
        for vnfc_id, vnfc_resources in tc_result['resources'].get(key, {}).items():
            print 'Resources for VNFC %s' % vnfc_id
            t = PrettyTable(['Resource type', 'Resource size'])
            for resource_type, resource_size in vnfc_resources.items():
                t.add_row([resource_type, resource_size])
            print t
            print

    print '* Events:'
    t = PrettyTable(['Event', 'Duration (sec)', 'Details'])
    for event_name in tc_result.get('events', {}).keys():
        try:
            event_duration = round(tc_result['events'][event_name].get('duration', None), 1)
        except TypeError:
            event_duration = 'N/A'
        event_details = tc_result['events'][event_name].get('details', '')
        t.add_row([event_name, event_duration, event_details])
    print t
    print

    print '* Timestamps:'
    t = PrettyTable(['Event', 'Timestamp (epoch time)'])
    for event_name, timestamp in tc_result.get('timestamps', {}).items():
        t.add_row([event_name, timestamp])
    print t
    print
