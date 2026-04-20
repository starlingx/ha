#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for sm_configure.main() and sm_dump verbose with data."""
# pylint: disable=protected-access,unused-argument
import os
import sqlite3
import unittest
from unittest import mock

from tests import constants as tc
from tests.base import BaseHaTestCase
from tests.test_helpers import make_sm_db as _make_full_db

from sm_tools import sm_action
from sm_tools import sm_configure
from sm_tools import sm_dump
from sm_tools import sm_provision
from sm_tools import sm_query


class _SmToolsDbTestCase(BaseHaTestCase):
    """Base for tests needing a temp SM database with module patching."""

    def _with_module_db(self, module, fn):
        db = _make_full_db()
        orig = module.database_name
        module.database_name = db
        try:
            fn(db)
        finally:
            module.database_name = orig


class TestSmConfigureMainSystem(_SmToolsDbTestCase):
    """Tests for sm_configure.main() system subcommand."""

    def _run_main(self, argv):
        db = _make_full_db()
        orig = sm_configure.database_name
        sm_configure.database_name = db
        try:
            with mock.patch('sys.argv', ['sm-configure'] + argv), \
                    mock.patch.object(sm_configure, 'configure_cpe_duplex'), \
                    mock.patch.object(sm_configure, 'configure_cpe_dc'), \
                    mock.patch.object(sm_configure, 'configure_system_opt') as mo:
                try:
                    sm_configure.main()
                except SystemExit as e:
                    return e.code, mo
            return None, mo
        finally:
            sm_configure.database_name = orig

    def test_system_duplex(self):
        code, _ = self._run_main(['system', '--cpe_mode', 'duplex'])
        self.assertEqual(code, 0)

    def test_system_duplex_direct(self):
        code, _ = self._run_main(['system', '--cpe_mode', 'duplex-direct'])
        self.assertEqual(code, 0)

    def test_system_sm_server_port(self):
        code, mo = self._run_main(['system', '--sm_server_port', '9999'])
        self.assertEqual(code, 0)
        mo.assert_any_call("sm_server_port", "9999")

    def test_system_sm_client_port(self):
        code, mo = self._run_main(['system', '--sm_client_port', '8888'])
        self.assertEqual(code, 0)
        mo.assert_any_call("sm_client_port", "8888")

    def test_system_process_priority_valid(self):
        code, mo = self._run_main(['system', '--sm_process_priority', '-10'])
        self.assertEqual(code, 0)
        mo.assert_any_call("sm_process_priority", "-10")

    def test_system_process_priority_invalid(self):
        code, _ = self._run_main(['system', '--sm_process_priority', '5'])
        self.assertEqual(code, -1)


class TestSmConfigureMainSubcommands(_SmToolsDbTestCase):
    """Tests for sm_configure.main() subcommands."""

    def _run_subcommand(self, argv, mock_target):
        def fn(db):
            with mock.patch('sys.argv', ['sm-configure'] + argv), \
                    mock.patch.object(sm_configure, mock_target) as m:
                try:
                    sm_configure.main()
                except SystemExit:
                    pass
                m.assert_called_once()
        self._with_module_db(sm_configure, fn)

    def test_interface_subcommand(self):
        self._run_subcommand(
            ['interface', 'controller', 'management-interface',
             '239.1.1.1', '10.0.0.1', '5555', '5556',
             '10.0.0.2', '5557', '5558'],
            '_configure_interface')

    def test_service_instance_subcommand(self):
        self._run_subcommand(
            ['service_instance', tc.SM_SERVICE_NAME, 'inst1', 'param=val'],
            '_configure_service_instance')

    def test_service_group_subcommand(self):
        def fn(db):
            argv = ['sm-configure', 'service_group', 'yes', 'controller',
                    'new-sg', 'N', '1', '0', 'controller', 'no']
            with mock.patch('sys.argv', argv):
                try:
                    sm_configure.main()
                except SystemExit as e:
                    self.assertEqual(e.code, 0)
        self._with_module_db(sm_configure, fn)


class TestSmConfigureMainExceptions(BaseHaTestCase):
    def test_keyboard_interrupt(self):
        with mock.patch('argparse.ArgumentParser.parse_args',
                        side_effect=KeyboardInterrupt):
            with self.assertRaises(SystemExit):
                sm_configure.main()

    def test_generic_exception(self):
        with mock.patch('argparse.ArgumentParser.parse_args',
                        side_effect=RuntimeError("boom")), \
                mock.patch('builtins.print'):
            with self.assertRaises(SystemExit) as ctx:
                sm_configure.main()
            self.assertEqual(ctx.exception.code, -1)


class TestSmDumpVerboseWithData(_SmToolsDbTestCase):
    """Tests for sm_dump verbose mode with actual service data."""

    _DUMP_MOCKS = {
        'sm_tools.sm_dump.os.path.exists': True,
        'sm_tools.sm_dump.get_pid': 123,
        'sm_tools.sm_dump.get_process_name': tc.SM_SERVICE_NAME,
    }

    def _run_dump(self, argv):
        def fn(db):
            patches = {k: mock.patch(k, return_value=v)
                       for k, v in self._DUMP_MOCKS.items()}
            with mock.patch('sys.argv', argv), \
                    mock.patch('builtins.print'), \
                    mock.patch('sys.stdout'), mock.patch('sys.stderr'):
                for p in patches.values():
                    p.start()
                try:
                    sm_dump.main()
                except SystemExit:
                    pass
                finally:
                    for p in patches.values():
                        p.stop()
        self._with_module_db(sm_dump, fn)

    def test_verbose_with_services_data(self):
        self._run_dump(['sm-dump', '--verbose', '--pid',
                        '--pn', '--pid_file', '--impact'])

    def test_basic_with_all_flags(self):
        self._run_dump(['sm-dump', '--pid', '--pn',
                        '--pid_file', '--impact'])


class TestSmQueryServiceGroupMultiple(_SmToolsDbTestCase):
    def _run_query(self, argv, check_fn):
        def fn(db):
            with mock.patch('sys.argv', argv), \
                    mock.patch('sm_tools.sm_query.os.path.exists',
                               return_value=True), \
                    mock.patch('builtins.print') as mp:
                try:
                    sm_query.main()
                except SystemExit:
                    pass
            check_fn(mp)
        self._with_module_db(sm_query, fn)

    def test_multiple_not_found(self):
        self._run_query(
            ['sm-query', 'service-group', 'a', 'b'],
            lambda mp: self.assertIn('not provisioned', mp.call_args[0][0]))

    def test_service_with_status(self):
        db = _make_full_db()
        conn = sqlite3.connect(db)
        conn.execute(
            "UPDATE SERVICES SET STATUS='warn' WHERE NAME='"
            + tc.SM_SERVICE_NAME + "'")
        conn.commit()
        conn.close()
        orig = sm_query.database_name
        sm_query.database_name = db
        try:
            with mock.patch('sys.argv',
                            ['sm-query', 'service', tc.SM_SERVICE_NAME]), \
                    mock.patch('sm_tools.sm_query.os.path.exists',
                               return_value=True), \
                    mock.patch('builtins.print') as mp:
                try:
                    sm_query.main()
                except SystemExit:
                    pass
            self.assertIn('warn', mp.call_args[0][0])
        finally:
            sm_query.database_name = orig


class TestSmActionManageUnmanage(_SmToolsDbTestCase):
    def test_manage_removes_file(self):
        def fn(db):
            with mock.patch('sys.argv',
                            ['sm-manage', 'service', tc.SM_SERVICE_NAME]), \
                    mock.patch('os.path.exists', return_value=True), \
                    mock.patch('os.path.isfile', return_value=True), \
                    mock.patch('os.remove') as mr:
                try:
                    sm_action.main()
                except SystemExit:
                    pass
                mr.assert_called_once()
        self._with_module_db(sm_action, fn)

    def test_unmanage_creates_dir(self):
        _real_exists = os.path.exists
        _real_open = open

        def _fake_open(path, *args, **kwargs):
            if '/var/run/sm/services/' in str(path):
                return mock.mock_open()()
            return _real_open(path, *args, **kwargs)

        def fn(db):
            with mock.patch('sys.argv',
                            ['sm-unmanage', 'service', tc.SM_SERVICE_NAME]), \
                    mock.patch('os.path.exists',
                               side_effect=lambda p: False
                               if p == '/var/run/sm/services'
                               else _real_exists(p)), \
                    mock.patch('os.makedirs') as mm, \
                    mock.patch('os.path.isfile', return_value=False), \
                    mock.patch('builtins.open', side_effect=_fake_open):
                try:
                    sm_action.main()
                except SystemExit:
                    pass
                mm.assert_called_once()
        self._with_module_db(sm_action, fn)


class TestSmProvisionDomainInterface(_SmToolsDbTestCase):
    def _setup_provision(self, db, rt_schema, rt_data):
        rt_db = db.replace('sm.db', 'rt.db')
        conn = sqlite3.connect(rt_db)
        conn.executescript(rt_schema + rt_data)
        conn.commit()
        conn.close()
        return rt_db

    def test_deprovision_sdi_with_apply(self):
        db = _make_full_db()
        schema = ("CREATE TABLE SERVICE_DOMAIN_INTERFACES("
                  "ID INTEGER PRIMARY KEY, SERVICE_DOMAIN TEXT,"
                  " SERVICE_DOMAIN_INTERFACE TEXT, PROVISIONED TEXT);")
        data = ("INSERT INTO SERVICE_DOMAIN_INTERFACES VALUES"
                "(1,'controller','management-interface','yes');")
        rt_db = self._setup_provision(db, schema, data)
        with open(rt_db, 'ab') as f:
            f.write(b'\x00')
        orig_db, orig_rt = (sm_provision.database_name,
                            sm_provision.runtime_db_name)
        sm_provision.database_name = db
        sm_provision.runtime_db_name = rt_db
        try:
            argv = ['sm-deprovision', 'service-domain-interface',
                    '--apply', 'controller', 'management-interface']
            with mock.patch('sys.argv', argv), \
                    mock.patch.object(
                        sm_provision,
                        'deprovision_service_domain_interface') as m:
                try:
                    sm_provision.main()
                except SystemExit:
                    pass
                m.assert_called_once()
        finally:
            sm_provision.database_name = orig_db
            sm_provision.runtime_db_name = orig_rt

    def test_deprovision_sgm_with_apply(self):
        db = _make_full_db()
        schema = (
            "CREATE TABLE SERVICE_GROUP_MEMBERS("
            "ID INTEGER PRIMARY KEY, NAME TEXT,"
            " SERVICE_NAME TEXT, PROVISIONED TEXT,"
            " SERVICE_FAILURE_IMPACT TEXT);\n"
            "CREATE TABLE SERVICES("
            "ID INTEGER PRIMARY KEY, NAME TEXT,"
            " DESIRED_STATE TEXT, STATE TEXT,"
            " STATUS TEXT, PROVISIONED TEXT, PID_FILE TEXT);")
        data = (
            "INSERT INTO SERVICE_GROUP_MEMBERS VALUES"
            "(1,'" + tc.SM_SERVICE_GROUP + "','"
            + tc.SM_SERVICE_NAME + "','yes','critical');\n"
            "INSERT INTO SERVICES VALUES"
            "(1,'" + tc.SM_SERVICE_NAME
            + "','enabled-active','enabled-active',"
            "'none','yes','/var/run/vim.pid');")
        rt_db = self._setup_provision(db, schema, data)
        orig_db, orig_rt = (sm_provision.database_name,
                            sm_provision.runtime_db_name)
        sm_provision.database_name = db
        sm_provision.runtime_db_name = rt_db
        try:
            with mock.patch('sys.argv', [
                'sm-deprovision', 'service-group-member',
                '--apply', tc.SM_SERVICE_GROUP, tc.SM_SERVICE_NAME
            ]), mock.patch.object(sm_provision, 'deprovision_service') as m:
                try:
                    sm_provision.main()
                except SystemExit:
                    pass
                m.assert_called_once()
        finally:
            sm_provision.database_name = orig_db
            sm_provision.runtime_db_name = orig_rt


if __name__ == '__main__':
    unittest.main()
