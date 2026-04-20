#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

# pylint: disable=redefined-outer-name
"""Shared test fixtures for ha project tests."""
import builtins
import os
import sys
import sqlite3
from unittest import mock

import pytest

# Install a passthrough _() for sm_api gettextutils compatibility
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

# Mock unavailable external modules so vendored openstack code
# can be imported and measured by coverage
_MOCK_MODULES = [
    'qpid', 'qpid.messaging', 'qpid.messaging.exceptions',
    'MySQLdb',
]
for _mod in _MOCK_MODULES:
    if _mod not in sys.modules:
        sys.modules[_mod] = mock.MagicMock()

# zmq needs __all__ attribute for eventlet.green.zmq
if 'zmq' not in sys.modules:
    _zmq = mock.MagicMock()
    _zmq.__all__ = []
    sys.modules['zmq'] = _zmq
    sys.modules['eventlet.green.zmq'] = _zmq

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))

# Ensure sub-packages are importable
for sub in (
    'service-mgmt-tools/sm-tools',
    'service-mgmt-client/sm-client',
    'service-mgmt-api/sm-api',
):
    path = os.path.join(PROJECT_ROOT, sub)
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temp SQLite DB with SM schema.

    :param tmp_path: pytest tmp_path fixture
    :returns: str path to the created database
    """
    db_path = str(tmp_path / "sm.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS SERVICE_DOMAINS (
            ID INTEGER PRIMARY KEY, PROVISIONED TEXT, NAME TEXT
        );
        CREATE TABLE IF NOT EXISTS SERVICE_DOMAIN_INTERFACES (
            ID INTEGER PRIMARY KEY, SERVICE_DOMAIN TEXT,
            SERVICE_DOMAIN_INTERFACE TEXT, INTERFACE_NAME TEXT,
            INTERFACE_CONNECT_TYPE TEXT, NETWORK_TYPE TEXT,
            NETWORK_MULTICAST TEXT, NETWORK_ADDRESS TEXT,
            NETWORK_PORT TEXT, NETWORK_HEARTBEAT_PORT TEXT,
            NETWORK_PEER_ADDRESS TEXT, NETWORK_PEER_PORT TEXT,
            NETWORK_PEER_HEARTBEAT_PORT TEXT, PROVISIONED TEXT
        );
        CREATE TABLE IF NOT EXISTS SERVICE_DOMAIN_MEMBERS (
            ID INTEGER PRIMARY KEY, PROVISIONED TEXT, NAME TEXT,
            SERVICE_GROUP_NAME TEXT, REDUNDANCY_MODEL TEXT,
            N_ACTIVE TEXT, M_STANDBY TEXT,
            SERVICE_GROUP_AGGREGATE TEXT, ACTIVE_ONLY TEXT
        );
        CREATE TABLE IF NOT EXISTS SERVICE_INSTANCES (
            ID INTEGER PRIMARY KEY, SERVICE_NAME TEXT,
            INSTANCE_NAME TEXT, INSTANCE_PARAMETERS TEXT
        );
        CREATE TABLE IF NOT EXISTS SERVICES (
            ID INTEGER PRIMARY KEY, NAME TEXT, DESIRED_STATE TEXT,
            STATE TEXT, STATUS TEXT, PROVISIONED TEXT, PID_FILE TEXT
        );
        CREATE TABLE IF NOT EXISTS SERVICE_GROUPS (
            ID INTEGER PRIMARY KEY, NAME TEXT, DESIRED_STATE TEXT,
            STATE TEXT, STATUS TEXT, CONDITION TEXT, PROVISIONED TEXT
        );
        CREATE TABLE IF NOT EXISTS SERVICE_GROUP_MEMBERS (
            ID INTEGER PRIMARY KEY, NAME TEXT, SERVICE_NAME TEXT,
            PROVISIONED TEXT, SERVICE_FAILURE_IMPACT TEXT
        );
        CREATE TABLE IF NOT EXISTS CONFIGURATION (
            ID INTEGER PRIMARY KEY, KEY TEXT UNIQUE, VALUE TEXT
        );
    """)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def populated_db(tmp_db):
    """Return DB path pre-populated with sample data.

    :param tmp_db: path to empty SM schema database
    :returns: str path to the populated database
    """
    conn = sqlite3.connect(tmp_db)
    cursor = conn.cursor()
    cursor.executescript("""
        INSERT INTO SERVICE_DOMAINS VALUES(1, 'yes', 'controller');
        INSERT INTO SERVICE_DOMAIN_INTERFACES VALUES(
            1, 'controller', 'management-interface', 'mgmt0',
            'tor', 'ipv4-udp', '239.1.1.1', '192.168.1.1',
            '2222', '2223', '192.168.1.2', '2224', '2225', 'yes'
        );
        INSERT INTO SERVICE_DOMAIN_INTERFACES VALUES(
            2, 'controller', 'cluster-host-interface', 'cluster0',
            'tor', 'ipv4-udp', '239.1.1.2', '192.168.2.1',
            '3222', '3223', '192.168.2.2', '3224', '3225', 'yes'
        );
        INSERT INTO SERVICE_DOMAIN_MEMBERS VALUES(
            1, 'yes', 'controller', 'vim-services',
            'N', '1', '0', 'controller', 'no'
        );
        INSERT INTO SERVICES VALUES(
            1, 'vim', 'enabled-active', 'enabled-active',
            'none', 'yes', '/var/run/vim.pid'
        );
        INSERT INTO SERVICES VALUES(
            2, 'vim-api', 'enabled-active', 'enabled-active',
            'none', 'yes', '/var/run/vim-api.pid'
        );
        INSERT INTO SERVICE_GROUPS VALUES(
            1, 'vim-services', 'active', 'active',
            'none', '', 'yes'
        );
        INSERT INTO SERVICE_GROUP_MEMBERS VALUES(
            1, 'vim-services', 'vim', 'yes', 'critical'
        );
        INSERT INTO CONFIGURATION VALUES(1, 'sm_server_port', '2345');
    """)
    conn.commit()
    conn.close()
    return tmp_db


@pytest.fixture
def project_root():
    """Return the project root path.

    :returns: str absolute path to project root
    """
    return PROJECT_ROOT
