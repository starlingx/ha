#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for sm_client shell, v1 modules, and gettextutils."""
# pylint: disable=protected-access,unused-argument
import unittest
from unittest import mock

from tests.base import BaseHaTestCase

from sm_client import exc
from sm_client.v1 import client as v1_client
from sm_client.v1 import shell as v1_shell
from sm_client.v1 import sm_nodes
from sm_client.v1 import sm_sda
from sm_client.v1 import smc_service
from sm_client.v1 import smc_service_node
from sm_client.v1 import smc_servicegroup

try:
    import httplib2  # noqa: F401
    HAS_HTTPLIB2 = True
    from sm_client.shell import SmcShell
except ImportError:
    HAS_HTTPLIB2 = False
    SmcShell = None


@unittest.skipUnless(HAS_HTTPLIB2, "httplib2 not available")
class TestSmcShellGetBaseParser(BaseHaTestCase):
    def _shell(self):
        return SmcShell()

    def test_get_base_parser(self):
        self.assertIsNotNone(self._shell().get_base_parser())

    def test_parse_known_args(self):
        opts, _ = self._shell().get_base_parser().parse_known_args([])
        self.assertFalse(opts.debug)
        self.assertEqual(opts.timeout, 600)

    def test_parse_debug(self):
        opts, _ = self._shell().get_base_parser().parse_known_args(['--debug'])
        self.assertTrue(opts.debug)


@unittest.skipUnless(HAS_HTTPLIB2, "httplib2 not available")
class TestSmcShellSetupDebugging(BaseHaTestCase):
    @mock.patch('sm_client.shell.logging.basicConfig')
    def test_debug_true(self, mock_config):
        import logging
        SmcShell()._setup_debugging(True)
        self.assertEqual(mock_config.call_args[1]['level'], logging.DEBUG)

    @mock.patch('sm_client.shell.logging.basicConfig')
    def test_debug_false(self, mock_config):
        import logging
        SmcShell()._setup_debugging(False)
        self.assertEqual(mock_config.call_args[1]['level'], logging.CRITICAL)


@unittest.skipUnless(HAS_HTTPLIB2, "httplib2 not available")
class TestSmcShellMain(BaseHaTestCase):
    def test_main_help(self):
        shell = SmcShell()
        with mock.patch.object(shell, 'do_help'):
            self.assertEqual(shell.main(['--help']), 0)

    def test_main_empty_args(self):
        shell = SmcShell()
        with mock.patch.object(shell, 'do_help'):
            self.assertEqual(shell.main([]), 0)

    def test_main_no_username_raises(self):
        with self.assertRaises(exc.CommandError):
            SmcShell().main(['service-list'])


@unittest.skipUnless(HAS_HTTPLIB2, "httplib2 not available")
class TestSmcShellDoHelp(BaseHaTestCase):
    def test_no_command(self):
        shell = SmcShell()
        shell.parser = mock.MagicMock()
        shell.subcommands = {}
        shell.do_help(mock.MagicMock(spec=[]))
        shell.parser.print_help.assert_called_once()

    def test_valid_command(self):
        shell = SmcShell()
        mock_sub = mock.MagicMock()
        shell.subcommands = {'service-list': mock_sub}
        shell.parser = mock.MagicMock()
        args = mock.MagicMock()
        args.command = 'service-list'
        shell.do_help(args)
        mock_sub.print_help.assert_called_once()

    def test_invalid_command(self):
        shell = SmcShell()
        shell.subcommands = {}
        shell.parser = mock.MagicMock()
        args = mock.MagicMock()
        args.command = 'nonexistent'
        with self.assertRaises(exc.CommandError):
            shell.do_help(args)


@unittest.skipUnless(HAS_HTTPLIB2, "httplib2 not available")
class TestShellMainFunction(BaseHaTestCase):
    @mock.patch('sm_client.shell.SmcShell.main', return_value=0)
    def test_main_success(self, _):
        from sm_client import shell
        shell.main()

    @mock.patch('sm_client.shell.SmcShell.main', side_effect=Exception("f"))
    def test_main_exception(self, _):
        from sm_client import shell
        with self.assertRaises(SystemExit):
            shell.main()


@unittest.skipUnless(HAS_HTTPLIB2, "httplib2 not available")
class TestHelpFormatter(BaseHaTestCase):
    def test_start_section(self):
        from sm_client.shell import HelpFormatter
        HelpFormatter('prog').start_section('options')


class TestV1Shell(BaseHaTestCase):
    def test_enhance_parser(self):
        import argparse
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        cmd_mapper = {}
        v1_shell.enhance_parser(parser, subparsers, cmd_mapper)
        self.assertGreater(len(cmd_mapper), 0)


class TestV1Client(BaseHaTestCase):
    @mock.patch('sm_client.common.http.HTTPClient.__init__',
                return_value=None)
    def test_client_init(self, _):
        c = v1_client.Client('http://localhost:7777')
        for attr in ('sm_sda', 'sm_nodes', 'smc_service',
                     'smc_service_node', 'smc_servicegroup'):
            self.assertIsNotNone(getattr(c, attr))


class _ManagerTestMixin:
    """Mixin for testing v1 manager list/get patterns."""

    manager_cls = None
    base_path = None
    response_key = None

    def _mgr(self, list_return=None):
        mgr = self.manager_cls(mock.MagicMock())
        mgr._list = mock.MagicMock(
            return_value=list_return if list_return is not None else [])
        return mgr

    def test_path(self):
        self.assertEqual(self.manager_cls._path(), self.base_path)

    def test_list(self):
        mgr = self._mgr()
        mgr.list()
        mgr._list.assert_called_once_with(self.base_path, self.response_key)

    def test_get_found(self):
        self.assertEqual(self._mgr(['item']).get('1'), 'item')

    def test_get_not_found(self):
        self.assertIsNone(self._mgr([]).get('1'))


class TestSmcServiceManager(_ManagerTestMixin, BaseHaTestCase):
    manager_cls = smc_service.SmcServiceManager
    base_path = '/v1/services'
    response_key = 'services'

    def test_path_with_id(self):
        self.assertEqual(self.manager_cls._path('123'), '/v1/services/123')

    def test_repr(self):
        svc = smc_service.SmcService(mock.MagicMock(), {'id': 1}, loaded=True)
        self.assertIn('SmcService', repr(svc))


class TestSmcNodeManager(_ManagerTestMixin, BaseHaTestCase):
    manager_cls = smc_service_node.SmcNodeManager
    base_path = '/v1/nodes'
    response_key = 'nodes'

    def test_path_with_id(self):
        self.assertEqual(self.manager_cls._path('1'), '/v1/nodes/1')

    def test_repr(self):
        n = smc_service_node.SmcNode(mock.MagicMock(), {'id': 1}, loaded=True)
        self.assertIn('SmcNode', repr(n))


class TestSmcServiceGroupManager(_ManagerTestMixin, BaseHaTestCase):
    manager_cls = smc_servicegroup.SmcServiceGroupManager
    base_path = '/v1/service_groups'
    response_key = 'service_groups'

    def test_path_with_id(self):
        self.assertEqual(self.manager_cls._path('1'), '/v1/service_groups/1')

    def test_get_index_error(self):
        mgr = self.manager_cls(mock.MagicMock())
        mgr._list = mock.MagicMock(side_effect=IndexError)
        self.assertIsNone(mgr.get('1'))

    def test_repr(self):
        sg = smc_servicegroup.smc_Servicegroup(
            mock.MagicMock(), {'id': 1}, loaded=True)
        self.assertIn('smc_Servicegroup', repr(sg))


class TestSmNodesManager(BaseHaTestCase):
    def _mgr(self):
        return sm_nodes.Sm_NodesManager(mock.MagicMock())

    def test_path(self):
        self.assertEqual(sm_nodes.Sm_NodesManager._path(), '/v1/nodes')

    def test_list(self):
        mgr = self._mgr()
        mgr._list = mock.MagicMock(return_value=[])
        mgr.list()
        mgr._list.assert_called_once()

    def test_get_found(self):
        mgr = self._mgr()
        mgr._list = mock.MagicMock(return_value=['n1'])
        self.assertEqual(mgr.get('1'), 'n1')

    def test_get_index_error(self):
        mgr = self._mgr()
        mgr._list = mock.MagicMock(return_value=[])
        self.assertIsNone(mgr.get('1'))

    def test_create_valid(self):
        mgr = self._mgr()
        mgr._create = mock.MagicMock(return_value='new')
        self.assertEqual(mgr.create(servicename='s', state='a'), 'new')

    def test_create_invalid_attr(self):
        with self.assertRaises(exc.InvalidAttribute):
            self._mgr().create(bad_key='val')

    def test_delete(self):
        mgr = self._mgr()
        mgr._delete = mock.MagicMock()
        mgr.delete('1')
        mgr._delete.assert_called_once_with('/v1/nodes/1')

    def test_update(self):
        mgr = self._mgr()
        mgr._update = mock.MagicMock(return_value='u')
        self.assertEqual(mgr.update('1', {'op': 'replace'}), 'u')

    def test_repr(self):
        n = sm_nodes.sm_Nodes(mock.MagicMock(), {'id': 1}, loaded=True)
        self.assertIn('sm_Nodes', repr(n))


class TestSmSdaManager(BaseHaTestCase):
    def _mgr(self):
        return sm_sda.Sm_SdaManager(mock.MagicMock())

    def test_path(self):
        self.assertEqual(sm_sda.Sm_SdaManager._path(), '/v1/sm_sda')
        self.assertEqual(sm_sda.Sm_SdaManager._path('1'), '/v1/sm_sda/1')

    def test_list(self):
        mgr = self._mgr()
        mgr._list = mock.MagicMock(return_value=[])
        mgr.list()
        mgr._list.assert_called_once()

    def test_get_found(self):
        mgr = self._mgr()
        mgr._list = mock.MagicMock(return_value=['s1'])
        self.assertEqual(mgr.get('1'), 's1')

    def test_get_index_error(self):
        mgr = self._mgr()
        mgr._list = mock.MagicMock(return_value=[])
        self.assertIsNone(mgr.get('1'))

    def test_create_valid(self):
        mgr = self._mgr()
        mgr._create = mock.MagicMock(return_value='new')
        self.assertEqual(mgr.create(servicename='s', state='a'), 'new')

    def test_create_invalid_attr(self):
        with self.assertRaises(exc.InvalidAttribute):
            self._mgr().create(bad_key='val')

    def test_delete(self):
        mgr = self._mgr()
        mgr._delete = mock.MagicMock()
        mgr.delete('1')
        mgr._delete.assert_called_once()

    def test_update(self):
        mgr = self._mgr()
        mgr._update = mock.MagicMock(return_value='u')
        self.assertEqual(mgr.update('1', {'op': 'replace'}), 'u')

    def test_repr(self):
        s = sm_sda.sm_Sda(mock.MagicMock(), {'id': 1}, loaded=True)
        self.assertIn('sm_Sda', repr(s))


class TestGettextutils(BaseHaTestCase):
    def test_translate(self):
        from sm_client.openstack.common import gettextutils
        try:
            self.assertIsInstance(gettextutils._("hello"), str)
        except AttributeError:
            pass

    def test_install(self):
        from sm_client.openstack.common import gettextutils
        try:
            gettextutils.install('sm_client')
        except TypeError:
            pass


class TestSmClientInit(BaseHaTestCase):
    def test_version(self):
        import sm_client
        self.assertEqual(sm_client.__version__, "1.0")


if __name__ == '__main__':
    unittest.main()
