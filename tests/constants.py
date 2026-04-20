#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Shared test constants for ha project tests."""

# Network
LOCALHOST = 'localhost'
RABBIT_PORT = 5672
RABBIT_HOST_URI = 'localhost:5672'
HTTP_ENDPOINT = 'http://localhost:7777'

# SM database values
SM_SERVICE_NAME = 'vim'
SM_SERVICE_GROUP = 'vim-services'
SM_DOMAIN = 'controller'
SM_MGMT_IF = 'management-interface'
SM_CLUSTER_IF = 'cluster-host-interface'
SM_ADMIN_IF = 'admin-interface'
SM_STATE_ACTIVE = 'enabled-active'
SM_STATUS_NONE = 'none'
SM_PROVISIONED = 'yes'

# Network addresses
MGMT_MULTICAST = '239.1.1.1'
MGMT_ADDRESS = '192.168.1.1'
MGMT_PEER_ADDRESS = '192.168.1.2'
MGMT_PORT = '2222'
MGMT_HB_PORT = '2223'
MGMT_PEER_PORT = '2224'
MGMT_PEER_HB_PORT = '2225'

# Rabbit config
RABBIT_CONF = {
    'hosts': [RABBIT_HOST_URI],
    'host': LOCALHOST,
    'port': RABBIT_PORT,
    'userid': 'guest',
    'password': 'guest',
    'virtual_host': '/',
    'retry_interval': 1,
    'retry_backoff': 2,
    'max_retries': 0,
    'ha_queues': False,
    'use_ssl': False,
    'reconnect_delay': 1.0,
}

# Qpid config
QPID_CONF = {
    'hostname': LOCALHOST,
    'port': RABBIT_PORT,
    'hosts': [RABBIT_HOST_URI],
    'username': '',
    'password': '',
    'sasl_mechanisms': '',
    'heartbeat': 60,
    'protocol': 'tcp',
    'tcp_nodelay': True,
    'topology_version': 1,
}
