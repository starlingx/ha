#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Shared helper functions for ha project tests."""
import os
import sqlite3
import tempfile
from unittest import mock

from tests import constants as tc

_SM_SCHEMA = """
CREATE TABLE SERVICES(
    ID INTEGER PRIMARY KEY, NAME TEXT, DESIRED_STATE TEXT,
    STATE TEXT, STATUS TEXT, CONDITION TEXT,
    PROVISIONED TEXT, PID_FILE TEXT);
CREATE TABLE SERVICE_GROUPS(
    ID INTEGER PRIMARY KEY, NAME TEXT, DESIRED_STATE TEXT,
    STATE TEXT, STATUS TEXT, CONDITION TEXT, PROVISIONED TEXT);
CREATE TABLE SERVICE_GROUP_MEMBERS(
    ID INTEGER PRIMARY KEY, NAME TEXT, SERVICE_NAME TEXT,
    PROVISIONED TEXT, SERVICE_FAILURE_IMPACT TEXT);
CREATE TABLE SERVICE_DOMAINS(
    ID INTEGER PRIMARY KEY, PROVISIONED TEXT, NAME TEXT);
CREATE TABLE SERVICE_DOMAIN_MEMBERS(
    ID INTEGER PRIMARY KEY, PROVISIONED TEXT, NAME TEXT,
    SERVICE_GROUP_NAME TEXT, REDUNDANCY_MODEL TEXT,
    N_ACTIVE TEXT, M_STANDBY TEXT,
    SERVICE_GROUP_AGGREGATE TEXT, ACTIVE_ONLY TEXT);
CREATE TABLE SERVICE_DOMAIN_INTERFACES(
    ID INTEGER PRIMARY KEY, SERVICE_DOMAIN TEXT,
    SERVICE_DOMAIN_INTERFACE TEXT, INTERFACE_NAME TEXT,
    INTERFACE_CONNECT_TYPE TEXT, NETWORK_TYPE TEXT,
    NETWORK_MULTICAST TEXT, NETWORK_ADDRESS TEXT,
    NETWORK_PORT TEXT, NETWORK_HEARTBEAT_PORT TEXT,
    NETWORK_PEER_ADDRESS TEXT, NETWORK_PEER_PORT TEXT,
    NETWORK_PEER_HEARTBEAT_PORT TEXT, PROVISIONED TEXT);
CREATE TABLE SERVICE_INSTANCES(
    ID INTEGER PRIMARY KEY, SERVICE_NAME TEXT,
    INSTANCE_NAME TEXT, INSTANCE_PARAMETERS TEXT);
CREATE TABLE CONFIGURATION(
    ID INTEGER PRIMARY KEY, "KEY" TEXT UNIQUE, "VALUE" TEXT);
"""


def safe_call(func):
    """Call func safely, return None on error."""
    try:
        return func()
    except Exception:
        return None


def make_sm_db(tmp_dir=None):
    """Create temp SQLite DB with full SM schema and sample data."""
    if tmp_dir is None:
        tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, 'sm.db')
    conn = sqlite3.connect(db_path)
    conn.executescript(_SM_SCHEMA)
    c = conn.cursor()
    c.execute("INSERT INTO SERVICES VALUES(1,?,?,?,?,?,?,?)",
              (tc.SM_SERVICE_NAME, tc.SM_STATE_ACTIVE, tc.SM_STATE_ACTIVE,
               tc.SM_STATUS_NONE, '', tc.SM_PROVISIONED, '/var/run/vim.pid'))
    c.execute("INSERT INTO SERVICE_GROUPS VALUES(1,?,?,?,?,?,?)",
              (tc.SM_SERVICE_GROUP, 'active', 'active',
               tc.SM_STATUS_NONE, '', tc.SM_PROVISIONED))
    c.execute("INSERT INTO SERVICE_GROUP_MEMBERS VALUES(1,?,?,?,?)",
              (tc.SM_SERVICE_GROUP, tc.SM_SERVICE_NAME,
               tc.SM_PROVISIONED, 'critical'))
    c.execute("INSERT INTO SERVICE_DOMAINS VALUES(1,?,?)",
              (tc.SM_PROVISIONED, tc.SM_DOMAIN))
    c.execute("INSERT INTO SERVICE_DOMAIN_MEMBERS VALUES(1,?,?,?,?,?,?,?,?)",
              (tc.SM_PROVISIONED, tc.SM_DOMAIN, tc.SM_SERVICE_GROUP,
               'N', '1', '0', tc.SM_DOMAIN, 'no'))
    c.execute("INSERT INTO SERVICE_DOMAIN_INTERFACES"
              " VALUES(1,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (tc.SM_DOMAIN, tc.SM_MGMT_IF, 'mgmt0', 'tor', 'ipv4-udp',
               tc.MGMT_MULTICAST, tc.MGMT_ADDRESS, tc.MGMT_PORT,
               tc.MGMT_HB_PORT, tc.MGMT_PEER_ADDRESS,
               tc.MGMT_PEER_PORT, tc.MGMT_PEER_HB_PORT, tc.SM_PROVISIONED))
    conn.commit()
    conn.close()
    return db_path


def make_mock_rabbit_conf():
    """Create a mock oslo.config for rabbit."""
    conf = mock.MagicMock()
    for key, val in tc.RABBIT_CONF.items():
        setattr(conf, 'rabbit_' + key, val)
    conf.kombu_reconnect_delay = tc.RABBIT_CONF['reconnect_delay']
    return conf


def make_mock_qpid_conf():
    """Create a mock oslo.config for qpid."""
    conf = mock.MagicMock()
    for key, val in tc.QPID_CONF.items():
        setattr(conf, 'qpid_' + key, val)
    return conf
