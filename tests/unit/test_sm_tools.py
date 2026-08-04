#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

"""Unit tests for sm_tools modules: sm_api_msg_utils, sm_configure,
sm_provision, sm_action, sm_query, sm_dump."""
# pylint: disable=protected-access,unused-argument
import os
import sqlite3
import socket
import tempfile
import unittest
from unittest import mock

import tests.constants as tc
from tests.base import BaseHaTestCase
from tests.test_helpers import make_sm_db

from sm_tools import sm_api_msg_utils as mu
from sm_tools import sm_configure
from sm_tools import sm_dump
from sm_tools import sm_provision
from sm_tools import sm_query


class TestSmApiMsgUtilsConstants(BaseHaTestCase):
    """Verify module-level constants in sm_api_msg_utils."""

    def test_constants_defined(self):
        self.assertEqual(mu.SM_API_MSG_VERSION, "1")
        self.assertEqual(mu.SM_API_MSG_REVISION, "1")
        self.assertIn("RESTART_SERVICE",
                      mu.SM_API_MSG_TYPE_RESTART_SERVICE)

    def test_server_addr(self):
        self.assertTrue(mu.SM_API_SERVER_ADDR.startswith("/tmp"))

    def test_field_offsets(self):
        self.assertIsInstance(mu.SM_API_MSG_VERSION_FIELD, int)
        self.assertIsInstance(mu.SM_API_MSG_TYPE_FIELD, int)
        self.assertEqual(mu.SM_API_MSG_SERVICE_NAME_FIELD,
                         mu.SM_API_MSG_SERVICE_DOMAIN_NAME_FIELD)


class TestSendMsgToSm(BaseHaTestCase):
    """Tests for _send_msg_to_sm."""

    @mock.patch('sm_tools.sm_api_msg_utils.socket.socket')
    @mock.patch('sm_tools.sm_api_msg_utils.time.sleep')
    def test_send_msg_success(self, mock_sleep, mock_sock_cls):
        sock_inst = mock.MagicMock()
        mock_sock_cls.return_value = sock_inst
        mu._send_msg_to_sm("test_msg")
        sock_inst.setblocking.assert_called_once_with(True)
        sock_inst.sendto.assert_called_once()
        mock_sleep.assert_called_once_with(1)

    @mock.patch('sm_tools.sm_api_msg_utils.socket.socket')
    @mock.patch('sm_tools.sm_api_msg_utils.time.sleep')
    def test_send_msg_socket_error(self, mock_sleep, mock_sock_cls):
        sock_inst = mock.MagicMock()
        sock_inst.sendto.side_effect = socket.error("fail")
        mock_sock_cls.return_value = sock_inst
        mu._send_msg_to_sm("test_msg")


class TestRestartService(BaseHaTestCase):
    """Tests for restart_service and restart_service_safe."""

    @mock.patch('sm_tools.sm_api_msg_utils._send_msg_to_sm')
    def test_restart_service(self, mock_send):
        mu.restart_service("vim")
        args = mock_send.call_args[0][0]
        self.assertIn("RESTART_SERVICE", args)
        self.assertIn("vim", args)
        self.assertNotIn("skip-dep", args)

    @mock.patch('sm_tools.sm_api_msg_utils._send_msg_to_sm')
    def test_restart_service_safe(self, mock_send):
        mu.restart_service_safe("vim")
        self.assertIn("skip-dep", mock_send.call_args[0][0])


class TestProvisionFunctions(BaseHaTestCase):
    """Tests for provision/deprovision functions."""

    def _call_and_check(self, func, args, expected_str):
        with mock.patch(
            'sm_tools.sm_api_msg_utils._send_msg_to_sm'
        ) as mock_send:
            func(*args)
            self.assertIn(expected_str, mock_send.call_args[0][0])

    def test_provision_service(self):
        self._call_and_check(
            mu.provision_service, ("vim", "vim-services"),
            "PROVISION_SERVICE")

    def test_deprovision_service(self):
        self._call_and_check(
            mu.deprovision_service, ("vim", "vim-services"),
            "DEPROVISION_SERVICE")

    def test_provision_sdi(self):
        self._call_and_check(
            mu.provision_service_domain_interface,
            ("controller", "mgmt-if"),
            "PROVISION_SERVICE_DOMAIN_INTERFACE")

    def test_deprovision_sdi(self):
        self._call_and_check(
            mu.deprovision_service_domain_interface,
            ("controller", "mgmt-if"),
            "DEPROVISION_SERVICE_DOMAIN_INTERFACE")


class SmConfigureDbTestCase(BaseHaTestCase):
    """Base for sm_configure tests needing a temp DB."""

    def _with_temp_db(self, schema_sql, test_fn):
        db_path = tempfile.mktemp(suffix='.db')
        conn = sqlite3.connect(db_path)
        conn.executescript(schema_sql)
        conn.close()
        orig_db = sm_configure.database_name
        sm_configure.database_name = db_path
        try:
            test_fn(db_path)
        finally:
            sm_configure.database_name = orig_db
            os.unlink(db_path)


class TestSmConfigureHelpers(SmConfigureDbTestCase):
    """Tests for sm_configure helper functions."""

    def test_configure_if_connect_type(self):
        schema = (
            "CREATE TABLE SERVICE_DOMAIN_INTERFACES "
            "(ID INTEGER PRIMARY KEY, SERVICE_DOMAIN_INTERFACE TEXT, "
            "INTERFACE_CONNECT_TYPE TEXT);\n"
            "INSERT INTO SERVICE_DOMAIN_INTERFACES VALUES "
            "(1, 'management-interface', 'tor');")

        def check(db_path):
            sm_configure.configure_if_connect_type(
                'management-interface', 'dc')
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                "SELECT INTERFACE_CONNECT_TYPE FROM "
                "SERVICE_DOMAIN_INTERFACES WHERE ID=1").fetchone()
            conn.close()
            self.assertEqual(row[0], 'dc')

        self._with_temp_db(schema, check)

    def test_configure_system_opt(self):
        schema = (
            'CREATE TABLE CONFIGURATION '
            '(ID INTEGER PRIMARY KEY, "KEY" TEXT UNIQUE, "VALUE" TEXT);')

        def check(db_path):
            sm_configure.configure_system_opt("sm_server_port", "9999")
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                'SELECT VALUE FROM CONFIGURATION '
                'WHERE KEY="sm_server_port"').fetchone()
            conn.close()
            self.assertEqual(row[0], "9999")
            sm_configure.configure_system_opt("sm_server_port", "8888")
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                'SELECT VALUE FROM CONFIGURATION '
                'WHERE KEY="sm_server_port"').fetchone()
            conn.close()
            self.assertEqual(row[0], "8888")

        self._with_temp_db(schema, check)

    def test_configure_cpe_duplex(self):
        with mock.patch.object(
            sm_configure, 'configure_if_connect_type'
        ) as m:
            sm_configure.configure_cpe_duplex()
            self.assertEqual(len(m.call_args_list), 2)
            self.assertEqual(m.call_args_list[0][0][1], 'tor')

    def test_configure_cpe_dc(self):
        with mock.patch.object(
            sm_configure, 'configure_if_connect_type'
        ) as m:
            sm_configure.configure_cpe_dc()
            self.assertEqual(len(m.call_args_list), 2)
            self.assertEqual(m.call_args_list[0][0][1], 'dc')


class TestSmConfigureDispatch(BaseHaTestCase):
    """Tests for _dispatch_config_action."""

    def _make_interface_args(self, multicast, address, peer_address):
        args = mock.MagicMock()
        args.which = 'interface'
        args.service_domain = 'controller'
        args.service_domain_interface = 'management-interface'
        args.network_multicast = multicast
        args.network_address = address
        args.network_port = '5555'
        args.network_heartbeat_port = '5556'
        args.network_peer_address = peer_address
        args.network_peer_port = '5557'
        args.network_peer_heartbeat_port = '5558'
        return args

    def _run_dispatch(self, args, db_path=None):
        if db_path is None:
            db_path = make_sm_db()
        database = sqlite3.connect(db_path)
        sm_configure._dispatch_config_action(args, database)
        return database, db_path

    def test_dispatch_interface_update(self):
        args = self._make_interface_args('239.2.2.2', '10.0.0.1', '10.0.0.2')
        database, db_path = self._run_dispatch(args)
        try:
            row = database.execute(
                "SELECT NETWORK_ADDRESS FROM SERVICE_DOMAIN_INTERFACES "
                "WHERE ID=1").fetchone()
            database.close()
            self.assertEqual(row[0], '10.0.0.1')
        finally:
            os.unlink(db_path)

    def test_dispatch_interface_ipv6(self):
        args = self._make_interface_args('ff02::1', 'fd00::1', 'fd00::2')
        database, db_path = self._run_dispatch(args)
        try:
            row = database.execute(
                "SELECT NETWORK_TYPE FROM SERVICE_DOMAIN_INTERFACES "
                "WHERE ID=1").fetchone()
            database.close()
            self.assertEqual(row[0], 'ipv6-udp')
        finally:
            os.unlink(db_path)

    def test_dispatch_service_instance_insert(self):
        db_path = make_sm_db()
        try:
            database = sqlite3.connect(db_path)
            args = mock.MagicMock()
            args.which = 'service_instance'
            args.service = 'new-svc'
            args.instance = 'inst1'
            args.parameters = 'param=val'
            sm_configure._dispatch_config_action(args, database)
            row = database.execute(
                "SELECT INSTANCE_NAME FROM SERVICE_INSTANCES "
                "WHERE SERVICE_NAME='new-svc'").fetchone()
            database.close()
            self.assertEqual(row[0], 'inst1')
        finally:
            os.unlink(db_path)

    def test_dispatch_service_instance_update(self):
        db_path = make_sm_db()
        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                "INSERT INTO SERVICE_INSTANCES VALUES "
                "(1, 'svc1', 'old-inst', 'old-param')")
            conn.commit()
            conn.close()
            database = sqlite3.connect(db_path)
            args = mock.MagicMock()
            args.which = 'service_instance'
            args.service = 'svc1'
            args.instance = 'new-inst'
            args.parameters = 'new-param'
            sm_configure._dispatch_config_action(args, database)
            row = database.execute(
                "SELECT INSTANCE_NAME FROM SERVICE_INSTANCES "
                "WHERE SERVICE_NAME='svc1'").fetchone()
            database.close()
            self.assertEqual(row[0], 'new-inst')
        finally:
            os.unlink(db_path)

    def _make_sg_args(self, sg_name, redundancy='N', active='1', standby='0'):
        args = mock.MagicMock()
        args.which = 'service_group'
        args.provisioned = 'yes'
        args.service_domain = 'controller'
        args.service_group = sg_name
        args.redundancy = redundancy
        args.active = active
        args.standby = standby
        args.aggregate = 'controller'
        args.active_only = 'no'
        return args

    def test_dispatch_service_group_insert(self):
        db_path = make_sm_db()
        try:
            database = sqlite3.connect(db_path)
            args = self._make_sg_args('new-sg')
            sm_configure._dispatch_config_action(args, database)
            row = database.execute(
                "SELECT SERVICE_GROUP_NAME FROM SERVICE_DOMAIN_MEMBERS "
                "WHERE SERVICE_GROUP_NAME='new-sg'").fetchone()
            database.close()
            self.assertIsNotNone(row)
        finally:
            os.unlink(db_path)

    def test_dispatch_service_group_update(self):
        db_path = make_sm_db()
        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                "INSERT INTO SERVICE_DOMAIN_MEMBERS VALUES "
                "(2, 'yes', 'controller', 'sg1', 'N', '1', '0', "
                "'controller', 'no')")
            conn.commit()
            conn.close()
            database = sqlite3.connect(db_path)
            args = self._make_sg_args('sg1', 'N+M', '2', '1')
            sm_configure._dispatch_config_action(args, database)
            row = database.execute(
                "SELECT REDUNDANCY_MODEL FROM SERVICE_DOMAIN_MEMBERS "
                "WHERE SERVICE_GROUP_NAME='sg1'").fetchone()
            database.close()
            self.assertEqual(row[0], 'N+M')
        finally:
            os.unlink(db_path)


class TestSmConfigureInterface(BaseHaTestCase):
    """Tests for _configure_interface."""

    def _run(self, apply, iface, expect_dispatch_count, expect_print=False):
        with mock.patch(
            'sm_tools.sm_configure._dispatch_config_action'
        ) as md, mock.patch(
            'sm_tools.sm_configure.sqlite3.connect'
        ) as mc, mock.patch('builtins.print') as mp:
            mc.return_value = mock.MagicMock()
            args = mock.MagicMock()
            args.apply = apply
            args.service_domain_interface = iface
            sm_configure._configure_interface(args)
            self.assertEqual(md.call_count, expect_dispatch_count)
            if expect_print:
                self.assertIn("unsupported", mp.call_args[0][0].lower())

    def test_no_apply(self):
        self._run(False, 'management-interface', 1)

    def test_apply_admin(self):
        self._run(True, 'admin-interface', 2)

    def test_apply_unsupported(self):
        self._run(True, 'cluster-host-interface', 1, expect_print=True)


class TestSmConfigureServiceInstance(BaseHaTestCase):
    """Tests for _configure_service_instance."""

    def _run(self, apply, service, expect_dispatch_count, expect_print=False):
        with mock.patch(
            'sm_tools.sm_configure._dispatch_config_action'
        ) as md, mock.patch(
            'sm_tools.sm_configure.sqlite3.connect'
        ) as mc, mock.patch('builtins.print') as mp:
            mc.return_value = mock.MagicMock()
            args = mock.MagicMock()
            args.apply = apply
            args.service = service
            sm_configure._configure_service_instance(args)
            self.assertEqual(md.call_count, expect_dispatch_count)
            if expect_print:
                self.assertIn("unsupported", mp.call_args[0][0].lower())

    def test_no_apply(self):
        self._run(False, tc.SM_SERVICE_NAME, 1)

    def test_apply_ip_service(self):
        self._run(True, 'admin-ipv4', 2)

    def test_apply_unsupported_service(self):
        self._run(True, 'some-other-svc', 1, expect_print=True)


class TestSmProvisionUpdateDb(BaseHaTestCase):
    """Tests for sm_provision.update_db."""

    def test_update_db_executes_sqls(self):
        db_path = tempfile.mktemp(suffix='.db')
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE T (ID INTEGER PRIMARY KEY, V TEXT)")
        conn.commit()
        conn.close()
        sm_provision.update_db(db_path, [
            "INSERT INTO T VALUES(1, 'a')",
            "INSERT INTO T VALUES(2, 'b')",
        ])
        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT * FROM T").fetchall()
        conn.close()
        os.unlink(db_path)
        self.assertEqual(len(rows), 2)


class TestSmQuery(BaseHaTestCase):
    """Tests for sm_query.main."""

    @mock.patch('sm_tools.sm_query.os.path.exists', return_value=False)
    @mock.patch('builtins.print')
    def test_db_not_available(self, mock_print, mock_exists):
        with self.assertRaises(SystemExit):
            sm_query.main()
        self.assertIn("not available", mock_print.call_args[0][0])


class TestSmDumpGetPid(BaseHaTestCase):
    """Tests for sm_dump.get_pid."""

    def _write_pid_file(self, content):
        fd, path = tempfile.mkstemp()
        if content is not None:
            with os.fdopen(fd, 'w') as f:
                f.write(content)
        else:
            os.close(fd)
        return path

    def test_get_pid_valid_file(self):
        path = self._write_pid_file("12345\n")
        self.assertEqual(sm_dump.get_pid(path), 12345)
        os.unlink(path)

    def test_get_pid_invalid_content(self):
        path = self._write_pid_file("not-a-pid\n")
        self.assertEqual(sm_dump.get_pid(path), -1)
        os.unlink(path)

    def test_get_pid_missing_file(self):
        self.assertEqual(sm_dump.get_pid("/nonexistent/pid"), -1)

    def test_get_pid_empty_file(self):
        path = self._write_pid_file(None)
        self.assertEqual(sm_dump.get_pid(path), -1)
        os.unlink(path)


class TestSmDumpGetProcessName(BaseHaTestCase):
    """Tests for sm_dump.get_process_name."""

    def test_negative_pid(self):
        self.assertEqual(sm_dump.get_process_name(-1), '')

    @mock.patch('sm_tools.sm_dump.psutil.Process')
    def test_valid_pid(self, mock_proc_cls):
        mock_proc_cls.return_value.name.return_value = 'sm'
        self.assertEqual(sm_dump.get_process_name(1), 'sm')

    @mock.patch('sm_tools.sm_dump.psutil.Process')
    def test_python_process(self, mock_proc_cls):
        proc = mock_proc_cls.return_value
        proc.name.return_value = 'python'
        proc.cmdline.return_value = ['python', '/usr/bin/sm-api']
        self.assertEqual(sm_dump.get_process_name(1), 'sm-api')

    @mock.patch('sm_tools.sm_dump.psutil.Process',
                side_effect=Exception("no such process"))
    def test_nonexistent_process(self, mock_proc_cls):
        self.assertEqual(sm_dump.get_process_name(99999), '')


if __name__ == '__main__':
    unittest.main()
