#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

"""Extended tests for sm_tools: sm_action, sm_provision, sm_query, sm_dump."""
# pylint: disable=protected-access,unused-argument
import os
import sqlite3
import unittest
from unittest import mock

import tests.constants as tc
from tests.base import BaseHaTestCase
from tests.base import SmToolsDbMixin

from sm_tools import sm_action
from sm_tools import sm_dump
from sm_tools import sm_provision
from sm_tools import sm_query


class TestSmActionMain(SmToolsDbMixin, BaseHaTestCase):
    """Tests for sm_action.main."""

    def _run_action(self, filename, service=tc.SM_SERVICE_NAME):
        db = self._setup_sm_db()
        orig = sm_action.database_name
        sm_action.database_name = db
        try:
            with mock.patch('sys.argv', [filename, 'service', service]), \
                    mock.patch('sm_tools.sm_action.restart_service'), \
                    mock.patch('sm_tools.sm_action.restart_service_safe'):
                with self.assertRaises(SystemExit) as ctx:
                    sm_action.main()
            return ctx.exception.code
        finally:
            sm_action.database_name = orig

    def test_restart(self):
        self.assertEqual(self._run_action('sm-restart'), 0)

    def test_restart_safe(self):
        self.assertEqual(self._run_action('sm-restart-safe'), 0)

    def test_manage(self):
        with mock.patch('os.path.exists', return_value=False):
            self.assertEqual(self._run_action('sm-manage'), 0)

    def test_unmanage(self):
        _real_exists = os.path.exists
        _real_open = open

        def _fake_open(path, *args, **kwargs):
            if '/var/run/sm/services/' in str(path):
                return mock.mock_open()()
            return _real_open(path, *args, **kwargs)

        with mock.patch('os.path.exists',
                        side_effect=lambda p: False
                        if p == '/var/run/sm/services'
                        else _real_exists(p)), \
                mock.patch('os.makedirs'), \
                mock.patch('os.path.isfile', return_value=False), \
                mock.patch('builtins.open', side_effect=_fake_open):
            self.assertEqual(self._run_action('sm-unmanage'), 0)

    def test_service_not_found(self):
        self._run_action('sm-restart', service='nonexistent')


class TestSmQueryMain(SmToolsDbMixin, BaseHaTestCase):
    """Tests for sm_query.main."""

    def _run_query(self, argv, assert_fn=None):
        db = self._setup_sm_db()
        orig = sm_query.database_name
        sm_query.database_name = db
        try:
            with mock.patch('sys.argv', argv), \
                    mock.patch('sm_tools.sm_query.os.path.exists',
                               return_value=True), \
                    mock.patch('builtins.print') as mp:
                try:
                    sm_query.main()
                except SystemExit:
                    pass
            if assert_fn:
                assert_fn(mp)
        finally:
            sm_query.database_name = orig

    def test_query_service_found(self):
        self._run_query(
            ['sm-query', 'service', tc.SM_SERVICE_NAME],
            lambda mp: self.assertIn(
                tc.SM_SERVICE_NAME, mp.call_args[0][0]))

    def test_query_service_not_found(self):
        self._run_query(
            ['sm-query', 'service', 'nonexistent'],
            lambda mp: self.assertIn('disabled', mp.call_args[0][0]))

    def test_query_service_group(self):
        self._run_query(
            ['sm-query', 'service-group', tc.SM_SERVICE_GROUP])

    def test_query_service_group_not_found(self):
        self._run_query(
            ['sm-query', 'service-group', 'nonexistent'],
            lambda mp: self.assertIn(
                'not provisioned', mp.call_args[0][0]))

    def test_query_service_group_desired_state(self):
        self._run_query(
            ['sm-query', 'service-group',
             '--desired-state', tc.SM_SERVICE_GROUP])


class TestSmDumpMain(SmToolsDbMixin, BaseHaTestCase):
    """Tests for sm_dump.main."""

    def _run_dump(self, argv, pid=-1, pname=''):
        db = self._setup_sm_db()
        orig = sm_dump.database_name
        sm_dump.database_name = db
        try:
            with mock.patch('sys.argv', argv), \
                    mock.patch('sm_tools.sm_dump.os.path.exists',
                               return_value=True), \
                    mock.patch('sm_tools.sm_dump.get_pid',
                               return_value=pid), \
                    mock.patch('sm_tools.sm_dump.get_process_name',
                               return_value=pname), \
                    mock.patch('builtins.print'), \
                    mock.patch('sys.stdout'), \
                    mock.patch('sys.stderr'):
                try:
                    sm_dump.main()
                except SystemExit:
                    pass
        finally:
            sm_dump.database_name = orig

    def test_dump_basic(self):
        self._run_dump(['sm-dump'])

    def test_dump_verbose(self):
        self._run_dump(['sm-dump', '--verbose'],
                       pid=123, pname=tc.SM_SERVICE_NAME)

    def test_dump_with_pid_flag(self):
        self._run_dump(['sm-dump', '--pid', '--pn', '--pid_file', '--impact'],
                       pid=123, pname=tc.SM_SERVICE_NAME)

    def test_dump_verbose_with_all_flags(self):
        self._run_dump(['sm-dump', '--verbose', '--pid', '--pn',
                        '--pid_file', '--impact'],
                       pid=123, pname=tc.SM_SERVICE_NAME)

    def test_dump_db_not_available(self):
        with mock.patch('sys.argv', ['sm-dump']), \
                mock.patch('sm_tools.sm_dump.os.path.exists',
                           return_value=False), \
                mock.patch('builtins.print'):
            with self.assertRaises(SystemExit):
                sm_dump.main()


class TestSmProvisionMain(SmToolsDbMixin, BaseHaTestCase):
    """Tests for sm_provision.main."""

    def _run_provision(self, filename, subcommand, extra_args):
        db = self._setup_sm_db()
        tmp = os.path.dirname(db)
        orig_db = sm_provision.database_name
        orig_rt = sm_provision.runtime_db_name
        sm_provision.database_name = db
        sm_provision.runtime_db_name = os.path.join(tmp, 'rt.db')
        try:
            argv = [filename, subcommand] + extra_args
            with mock.patch('sys.argv', argv), \
                    mock.patch('sm_tools.sm_provision.provision_service'), \
                    mock.patch('sm_tools.sm_provision.deprovision_service'), \
                    mock.patch('sm_tools.sm_provision'
                               '.provision_service_domain_interface'), \
                    mock.patch('sm_tools.sm_provision'
                               '.deprovision_service_domain_interface'):
                with self.assertRaises(SystemExit) as ctx:
                    sm_provision.main()
            return ctx.exception.code
        finally:
            sm_provision.database_name = orig_db
            sm_provision.runtime_db_name = orig_rt

    def test_provision_service_domain(self):
        self.assertEqual(self._run_provision(
            'sm-provision', 'service-domain', ['controller']), 0)

    def test_deprovision_service_domain(self):
        self.assertEqual(self._run_provision(
            'sm-deprovision', 'service-domain', ['controller']), 0)

    def test_provision_service_domain_member(self):
        self.assertEqual(self._run_provision(
            'sm-provision', 'service-domain-member',
            ['controller', tc.SM_SERVICE_GROUP]), 0)

    def test_provision_service_group(self):
        self.assertEqual(self._run_provision(
            'sm-provision', 'service-group',
            [tc.SM_SERVICE_GROUP]), 0)

    def test_provision_service(self):
        self.assertEqual(self._run_provision(
            'sm-provision', 'service', [tc.SM_SERVICE_NAME]), 0)

    def test_provision_service_domain_interface(self):
        self.assertEqual(self._run_provision(
            'sm-provision', 'service-domain-interface',
            ['controller', 'mgmt-if']), 0)

    def test_provision_service_group_member(self):
        self.assertEqual(self._run_provision(
            'sm-provision', 'service-group-member',
            [tc.SM_SERVICE_GROUP, tc.SM_SERVICE_NAME]), 0)

    def test_provision_sgm_with_apply(self):
        db = self._setup_sm_db()
        tmp = os.path.dirname(db)
        rt_db = os.path.join(tmp, 'rt.db')
        conn = sqlite3.connect(rt_db)
        conn.executescript("""
            CREATE TABLE SERVICE_GROUP_MEMBERS(
                ID INTEGER PRIMARY KEY, NAME TEXT,
                SERVICE_NAME TEXT, PROVISIONED TEXT,
                SERVICE_FAILURE_IMPACT TEXT);
            CREATE TABLE SERVICES(
                ID INTEGER PRIMARY KEY, NAME TEXT,
                DESIRED_STATE TEXT, STATE TEXT, STATUS TEXT,
                PROVISIONED TEXT, PID_FILE TEXT);
            INSERT INTO SERVICE_GROUP_MEMBERS
                VALUES(1,'vim-services','vim','yes','critical');
            INSERT INTO SERVICES VALUES(
                1,'vim','enabled-active','enabled-active',
                'none','yes','/var/run/vim.pid');
        """)
        conn.commit()
        conn.close()
        orig_db = sm_provision.database_name
        orig_rt = sm_provision.runtime_db_name
        sm_provision.database_name = db
        sm_provision.runtime_db_name = rt_db
        try:
            with mock.patch('sys.argv', [
                'sm-provision', 'service-group-member',
                '--apply', tc.SM_SERVICE_GROUP, tc.SM_SERVICE_NAME
            ]), mock.patch(
                'sm_tools.sm_provision.provision_service'
            ) as mp:
                with self.assertRaises(SystemExit):
                    sm_provision.main()
                mp.assert_called_once()
        finally:
            sm_provision.database_name = orig_db
            sm_provision.runtime_db_name = orig_rt


if __name__ == '__main__':
    unittest.main()
