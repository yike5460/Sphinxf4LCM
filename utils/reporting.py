import time
from prettytable import PrettyTable


def report_test_case(tc_input, tc_result):
    time.sleep(1)
    print '*** Test case environment ***'
    t = PrettyTable(['Module', 'Type'])
    t.add_row(['VNFM', tc_input['vnfm_params']['type']])
    t.add_row(['VIM', tc_input['vim_params']['type']])
    t.add_row(['VNF', tc_input['vnf']['type']])
    t.add_row(['Traffic', tc_input['traffic_params']['type']])
    print t
    print

    print '*** Test case results ***'
    t = PrettyTable()
    t.add_row(['Overall status', tc_result['overall_status']])
    t.add_row(['Error info', tc_result['error_info']])

    print '* VNF resources:'
    for vnfc_id, vnfc_resources in tc_result.get('resources').items():
        print 'Resources for VNFC: %s' % vnfc_id
        t = PrettyTable(['Resource type', 'Resource size'])
        for resource_type, resource_size in vnfc_resources.items():
            t.add_row([resource_type, resource_size])
        print t
        print

    print '* Durations:'
    t = PrettyTable(['Event', 'Duration (sec)'])
    for event_name, event_duration in tc_result.get('durations').items():
        t.add_row([event_name, event_duration])
    print t
    print

    print '* Timestamps:'
    t = PrettyTable(['Event', 'Timestamp (epoch time)'])
    for event_name, timestamp in tc_result.get('timestamps').items():
        t.add_row([event_name, timestamp])
    print t
    print