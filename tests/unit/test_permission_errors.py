#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Tests for PermissionError handling in sm_tools modules."""
import sqlite3
import unittest
from unittest import mock

import tests.constants as tc
from tests.base import BaseHaTestCase

from sm_tools import sm_action
from sm_tools import sm_configure
from sm_tools import sm_dump
from sm_tools import sm_provision
from sm_tools import sm_query

_PERM_ERRORS = (PermissionError, OSError, sqlite3.OperationalError)


class TestSmConfigurePermissionError(BaseHaTestCase):
    def _with_bad_db(self, fn):
        orig = sm_configure.database_name
        sm_configure.database_name = '/root/no_access.db'
        try:
            with self.assertRaises(_PERM_ERRORS):
                fn()
        finally:
            sm_configure.database_name = orig

    def test_configure_if_connect_type_permission(self):
        self._with_bad_db(
            lambda: sm_configure.configure_if_connect_type(
                tc.SM_MGMT_IF, 'tor'))

    def test_configure_system_opt_permission(self):
        self._with_bad_db(
            lambda: sm_configure.configure_system_opt(
                'sm_server_port', '9999'))


class TestSmProvisionPermissionError(BaseHaTestCase):
    def test_update_db_permission(self):
        with self.assertRaises(_PERM_ERRORS):
            sm_provision.update_db('/root/no_access.db', ["SELECT 1"])


class TestSmDumpPermissionError(BaseHaTestCase):
    def test_get_pid_permission(self):
        self.assertEqual(sm_dump.get_pid('/root/no_access.pid'), -1)


class TestSmQueryPermissionError(BaseHaTestCase):
    @mock.patch('sm_tools.sm_query.os.path.exists', return_value=True)
    @mock.patch('sm_tools.sm_query.sqlite3.connect',
                side_effect=PermissionError('denied'))
    @mock.patch('builtins.print')
    def test_query_db_permission(self, *_):
        with mock.patch('sys.argv',
                        ['sm-query', 'service', tc.SM_SERVICE_NAME]):
            with self.assertRaises(SystemExit):
                sm_query.main()


class TestSmActionPermissionError(BaseHaTestCase):
    @mock.patch('sm_tools.sm_action.sqlite3.connect',
                side_effect=PermissionError('denied'))
    @mock.patch('builtins.print')
    def test_action_db_permission(self, *_):
        orig = sm_action.database_name
        sm_action.database_name = '/root/no_access.db'
        try:
            with mock.patch('sys.argv',
                            ['sm-restart', 'service', tc.SM_SERVICE_NAME]):
                with self.assertRaises(SystemExit):
                    sm_action.main()
        finally:
            sm_action.database_name = orig


if __name__ == '__main__':
    unittest.main()
