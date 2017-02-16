"""
Various constants and mappings.
"""

# Operation results
OPERATION_SUCCESS = 'SUCCESS'
OPERATION_FAILED = 'FAILED'
OPERATION_PENDING = 'PENDING'
OPERATION_FINAL_STATES = [OPERATION_SUCCESS, OPERATION_FAILED]

# ETSI VNF states
VNF_INSTANTIATED = 'INSTANTIATED'
VNF_NOT_INSTANTIATED = 'NOT_INSTANTIATED'

VNF_STARTED = 'STARTED'
VNF_STOPPED = 'STOPPED'
VNF_FINAL_STATES = [VNF_STARTED, VNF_STOPPED]


# Mapping between operation results and OpenStack VNF states
OPERATION_STATUS = dict()
OPERATION_STATUS['OPENSTACK_VNF_STATE'] = {'ACTIVE': OPERATION_SUCCESS,
                                           'ERROR': OPERATION_FAILED,
                                           'PENDING_CREATE': OPERATION_PENDING,
                                           'PENDING_DELETE': OPERATION_PENDING,
                                           'PENDING_UPDATE': OPERATION_PENDING}

# Mapping between OpenStack VNF states and ETSI VNF instantiation states
VNF_INSTANTIATION_STATE = dict()
VNF_INSTANTIATION_STATE['OPENSTACK_VNF_STATE'] = {'ACTIVE': VNF_INSTANTIATED,
                                                  'ERROR': VNF_NOT_INSTANTIATED,
                                                  'PENDING_CREATE': VNF_NOT_INSTANTIATED,
                                                  'PENDING_DELETE': VNF_NOT_INSTANTIATED}


# Mapping between OpenStack Heat stack states and ETSI VNF states
VNF_STATE = dict()
VNF_STATE['OPENSTACK_VNF_STATE'] = {'CREATE_COMPLETE': VNF_STARTED,
                                    'RESUME_COMPLETE': VNF_STARTED,
                                    'SUSPEND_COMPLETE': VNF_STOPPED}

# Test results
TEST_FAILED = 'FAILED'
TEST_PASSED = 'PASSED'

# Wait time intervals
COLLDOWN = 10
INSTANTIATION_TIME = 300
POLL_INTERVAL = 5
START_TIME = 300
STOP_TIME = 300
TERMINATE_TIME = 300
