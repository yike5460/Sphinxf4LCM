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


"""
Various constants and mappings.
"""

# Operation results
OPERATION_SUCCESS = 'SUCCESS'
OPERATION_FAILED = 'FAILED'
OPERATION_PENDING = 'PENDING'
OPERATION_FINAL_STATES = [OPERATION_SUCCESS, OPERATION_FAILED]

# ETSI VNF instantiation states
VNF_INSTANTIATED = 'INSTANTIATED'
VNF_NOT_INSTANTIATED = 'NOT_INSTANTIATED'

# ETSI NS instantiation states
NS_INSTANTIATED = 'INSTANTIATED'
NS_NOT_INSTANTIATED = 'NOT_INSTANTIATED'

# ETSI VNF states
VNF_STARTED = 'STARTED'
VNF_STOPPED = 'STOPPED'
VNF_FINAL_STATES = [VNF_STARTED, VNF_STOPPED]

# ETSI VirtualCompute operational states
VIRTUAL_RESOURCE_ENABLED = 'ENABLED'
VIRTUAL_RESOURCE_DISABLED = 'DISABLED'

# Mapping between operation result and various states
OPERATION_STATUS = {
    # Mapping for OpenStack VNF states
    'OPENSTACK_VNF_STATE': {
        'ACTIVE': OPERATION_SUCCESS,
        'ERROR': OPERATION_FAILED,
        'PENDING_CREATE': OPERATION_PENDING,
        'PENDING_DELETE': OPERATION_PENDING,
        'PENDING_SCALE_IN': OPERATION_PENDING,
        'PENDING_SCALE_OUT': OPERATION_PENDING,
        'PENDING_UPDATE': OPERATION_PENDING
    },
    # Mapping for OpenStack Stack states
    'OPENSTACK_STACK_STATE': {
        'CREATE_COMPLETE': OPERATION_SUCCESS,
        'CREATE_IN_PROGRESS': OPERATION_PENDING,
        'CREATE_FAILED': OPERATION_FAILED,
        'RESUME_COMPLETE': OPERATION_SUCCESS,
        'RESUME_IN_PROGRESS': OPERATION_PENDING,
        'RESUME_FAILED': OPERATION_FAILED,
        'SUSPEND_COMPLETE': OPERATION_SUCCESS,
        'SUSPEND_IN_PROGRESS': OPERATION_PENDING,
        'SUSPEND_FAILED': OPERATION_FAILED
    },
    # Mapping for OpenStack NS states
    'OPENSTACK_NS_STATE': {
        'ACTIVE': OPERATION_SUCCESS,
        'ERROR': OPERATION_FAILED,
        'PENDING_CREATE': OPERATION_PENDING,
        'PENDING_DELETE': OPERATION_PENDING
    }
}

# Mapping between ETSI VNF instantiation states and various states
VNF_INSTANTIATION_STATE = {
    # Mapping for OpenStack VNF states
    'OPENSTACK_VNF_STATE': {
        'ACTIVE': VNF_INSTANTIATED,
        'ERROR': VNF_NOT_INSTANTIATED,
        'PENDING_CREATE': VNF_NOT_INSTANTIATED,
        'PENDING_SCALE_OUT': VNF_INSTANTIATED,
        'PENDING_SCALE_IN': VNF_INSTANTIATED,
        'PENDING_DELETE': VNF_NOT_INSTANTIATED
    },
    # Mapping for Cisco NSO VNF deployment states
    'NSO_DEPLOYMENT_STATE': {
        'reached': VNF_INSTANTIATED,
        'not-reached': VNF_NOT_INSTANTIATED
    }
}

# Mapping between ETSI NS instantiation states and various states
NS_INSTANTIATION_STATE = {
    # Mapping for OpenStack NS states
    'OPENSTACK_NS_STATE': {
        'ACTIVE': NS_INSTANTIATED,
        'ERROR': NS_NOT_INSTANTIATED,
        'PENDING_CREATE': NS_NOT_INSTANTIATED,
        'PENDING_DELETE': NS_NOT_INSTANTIATED
    },
    # Mapping for Cisco NSO NS deployment states
    'NSO_DEPLOYMENT_STATE': {
        'reached': NS_INSTANTIATED,
        'not-reached': NS_NOT_INSTANTIATED
    }
}

# Mapping between ETSI VNF states and various states
VNF_STATE = {
    # Mapping for OpenStack Heat stack states
    'OPENSTACK_STACK_STATE': {
        'CREATE_COMPLETE': VNF_STARTED,
        'RESUME_COMPLETE': VNF_STARTED,
        'SUSPEND_COMPLETE': VNF_STOPPED
    },
    # Mapping for Cisco ESC VNF deployment states
    'ESC_DEPLOYMENT_STATE': {
        'SERVICE_ACTIVE_STATE': VNF_STARTED,
        'SERVICE_STOPPED_STATE': VNF_STOPPED
    },
    # Mapping for Openbaton VNF deployment states
    'OPENBATON_VNF_STATE': {
        'ACTIVE': VNF_STARTED,
        'INACTIVE': VNF_STOPPED
    }
}

# Test results
TEST_FAILED = 'FAILED'
TEST_PASSED = 'PASSED'
TEST_ERROR = 'ERROR'

# Wait time intervals
VNF_INSTANTIATE_TIMEOUT = 600
VNF_SCALE_TIMEOUT = 360
VNF_STOP_TIMEOUT = 300
VNF_START_TIMEOUT = 300
VNF_TERMINATE_TIMEOUT = 300
VNF_STABLE_STATE_TIMEOUT = 360
NS_INSTANTIATE_TIMEOUT = 600
NS_SCALE_TIMEOUT = 360
NS_UPDATE_TIMEOUT = 360
NS_TERMINATE_TIMEOUT = 300
NS_STABLE_STATE_TIMEOUT = 360
POLL_INTERVAL = 5
INSTANCE_BOOT_TIME = 30
INSTANCE_FIRST_BOOT_TIME = 60
ALARM_CREATE_TIMEOUT = 60
ALARM_CLEAR_TIMEOUT = 60
COMPUTE_TERMINATE_TIMEOUT = 300
COMPUTE_OPERATE_TIMEOUT = 300

# Traffic parameters
traffic_load_percent_mapping = {
    'LOW_TRAFFIC_LOAD': 1,
    'NORMAL_TRAFFIC_LOAD': 3,
    'MAX_TRAFFIC_LOAD': 5
}
TRAFFIC_TOLERANCE = 0.01
TRAFFIC_DELAY_TIME = 5
TRAFFIC_STABILIZATION_TIME = 60
