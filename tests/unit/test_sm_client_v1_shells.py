#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for v1 shell command functions and sm_client"""
# pylint: disable=protected-access,unused-argument
import argparse
import unittest
from unittest import mock

import tests.constants as tc
from tests.base import BaseHaTestCase

from sm_client import exc
from sm_client.common import utils as client_utils
from sm_client.v1 import smc_service_shell as ss
from sm_client.v1 import smc_service_node_shell as sns
from sm_client.v1 import smc_servicegroup_shell as sgs


class TestSmcServiceShellList(BaseHaTestCase):
    @mock.patch('sm_client.common.utils.print_list')
    def test_do_service_list(self, mock_pl):
        cc = mock.MagicMock()
        svc = mock.MagicMock()
        svc.state = 'active'
        svc.status = 'none'
        svc.node_name = 'ctrl'
        cc.smc_service.list.return_value = [svc]
        ss.do_service_list(cc, mock.MagicMock())
        mock_pl.assert_called_once()

    @mock.patch('sm_client.common.utils.print_list')
    def test_do_service_list_filters_initial(self, mock_pl):
        cc = mock.MagicMock()
        svc1 = mock.MagicMock(state='initial', status='')
        svc2 = mock.MagicMock(state='active', status='', node_name='h')
        cc.smc_service.list.return_value = [svc1, svc2]
        ss.do_service_list(cc, mock.MagicMock())
        self.assertEqual(len(mock_pl.call_args[0][0]), 1)

    def test_do_service_list_forbidden(self):
        cc = mock.MagicMock()
        cc.smc_service.list.side_effect = exc.Forbidden()
        with self.assertRaises(exc.CommandError):
            ss.do_service_list(cc, mock.MagicMock())

    @mock.patch('sm_client.common.utils.print_dict')
    def test_do_service_show(self, mock_pd):
        cc = mock.MagicMock()
        svc = mock.MagicMock(status='warn', state='active',
                             name=tc.SM_SERVICE_NAME, node_name='h')
        cc.smc_service.get.return_value = svc
        args = mock.MagicMock(service='1')
        ss.do_service_show(cc, args)
        mock_pd.assert_called_once()

    @mock.patch('builtins.print')
    def test_do_service_show_none(self, mock_pr):
        cc = mock.MagicMock()
        cc.smc_service.get.return_value = None
        ss.do_service_show(cc, mock.MagicMock(service='1'))
        mock_pr.assert_called_once()

    def test_do_service_show_not_found(self):
        cc = mock.MagicMock()
        cc.smc_service.get.side_effect = exc.HTTPNotFound()
        with self.assertRaises(exc.CommandError):
            ss.do_service_show(cc, mock.MagicMock(service='1'))

    @mock.patch('sm_client.common.utils.print_dict')
    def test_do_service_show_no_node_name(self, mock_pd):
        cc = mock.MagicMock()
        svc = mock.MagicMock(spec=['status', 'state', 'name'])
        svc.status = ''
        svc.state = 'active'
        svc.name = tc.SM_SERVICE_NAME
        type(svc).node_name = mock.PropertyMock(return_value=None)
        cc.smc_service.get.return_value = svc
        ss.do_service_show(cc, mock.MagicMock(service='1'))


class TestSmcServiceNodeShell(BaseHaTestCase):
    @mock.patch('sm_client.common.utils.print_list')
    def test_do_servicenode_list(self, mock_pl):
        cc = mock.MagicMock()
        cc.smc_service_node.list.return_value = []
        sns.do_servicenode_list(cc, mock.MagicMock())
        mock_pl.assert_called_once()

    def test_do_servicenode_list_forbidden(self):
        cc = mock.MagicMock()
        cc.smc_service_node.list.side_effect = exc.Forbidden()
        with self.assertRaises(exc.CommandError):
            sns.do_servicenode_list(cc, mock.MagicMock())

    @mock.patch('sm_client.common.utils.print_mapping')
    def test_do_servicenode_show(self, mock_pm):
        cc = mock.MagicMock()
        cc.smc_service_node.get.return_value = mock.MagicMock()
        sns.do_servicenode_show(cc, mock.MagicMock(node='1'))
        mock_pm.assert_called_once()

    @mock.patch('builtins.print')
    def test_do_servicenode_show_none(self, mock_pr):
        cc = mock.MagicMock()
        cc.smc_service_node.get.return_value = None
        sns.do_servicenode_show(cc, mock.MagicMock(node='1'))
        mock_pr.assert_called_once()

    def test_do_servicenode_show_not_found(self):
        cc = mock.MagicMock()
        cc.smc_service_node.get.side_effect = exc.HTTPNotFound()
        with self.assertRaises(exc.CommandError):
            sns.do_servicenode_show(cc, mock.MagicMock(node='1'))


class TestSmcServicegroupShell(BaseHaTestCase):
    @mock.patch('sm_client.common.utils.print_list')
    def test_do_servicegroup_list(self, mock_pl):
        cc = mock.MagicMock()
        sg = mock.MagicMock(status='warn', state='active')
        cc.smc_servicegroup.list.return_value = [sg]
        sgs.do_servicegroup_list(cc, mock.MagicMock())
        mock_pl.assert_called_once()

    def test_do_servicegroup_list_forbidden(self):
        cc = mock.MagicMock()
        cc.smc_servicegroup.list.side_effect = exc.Forbidden()
        with self.assertRaises(exc.CommandError):
            sgs.do_servicegroup_list(cc, mock.MagicMock())

    @mock.patch('sm_client.common.utils.print_mapping')
    def test_do_servicegroup_show(self, mock_pm):
        cc = mock.MagicMock()
        sg = mock.MagicMock(status='warn', state='active', node_name='h')
        cc.smc_servicegroup.get.return_value = sg
        sgs.do_servicegroup_show(cc, mock.MagicMock(servicegroup='1'))
        mock_pm.assert_called_once()

    @mock.patch('builtins.print')
    def test_do_servicegroup_show_none(self, mock_pr):
        cc = mock.MagicMock()
        cc.smc_servicegroup.get.return_value = None
        sgs.do_servicegroup_show(cc, mock.MagicMock(servicegroup='1'))
        mock_pr.assert_called_once()

    def test_do_servicegroup_show_not_found(self):
        cc = mock.MagicMock()
        cc.smc_servicegroup.get.side_effect = exc.HTTPNotFound()
        with self.assertRaises(exc.CommandError):
            sgs.do_servicegroup_show(cc, mock.MagicMock(servicegroup='1'))


class TestUtilsPrintFunctions(BaseHaTestCase):
    @mock.patch('builtins.print')
    def test_print_list(self, _):
        obj = mock.MagicMock(name='test', id=1)
        client_utils.print_list([obj], ['id', 'name'], ['ID', 'Name'])

    @mock.patch('builtins.print')
    def test_print_tuple_list(self, _):
        client_utils.print_tuple_list([('key', 'val')])

    @mock.patch('builtins.print')
    def test_print_tuple_list_with_labels(self, _):
        client_utils.print_tuple_list([('key', 'val')], ['Label'])

    @mock.patch('builtins.print')
    def test_print_mapping(self, _):
        client_utils.print_mapping(mock.MagicMock(name='test'), ['name'])

    @mock.patch('builtins.print')
    def test_print_mapping_with_wrap(self, _):
        obj = mock.MagicMock()
        obj.name = 'a' * 100
        client_utils.print_mapping(obj, ['name'], wrap=40)

    @mock.patch('builtins.print')
    def test_print_mapping_missing_attr(self, _):
        client_utils.print_mapping(mock.MagicMock(spec=[]), ['missing_field'])

    @mock.patch('builtins.print')
    def test_print_dict(self, _):
        client_utils.print_dict({'name': 'test', 'id': 1}, ['name', 'id'])

    @mock.patch('builtins.print')
    def test_print_dict_with_newline(self, _):
        client_utils.print_dict({'name': r'line1\nline2'}, ['name'])

    @mock.patch('builtins.print')
    def test_print_dict_missing_key(self, _):
        client_utils.print_dict({}, ['missing'])

    @mock.patch('builtins.print')
    def test_print_mapping_dict_value(self, _):
        obj = mock.MagicMock()
        obj.data = {'nested': 'val'}
        client_utils.print_mapping(obj, ['data'])

    @mock.patch('builtins.print')
    def test_print_mapping_newline_value(self, _):
        obj = mock.MagicMock()
        obj.trace = r'line1\nline2'
        client_utils.print_mapping(obj, ['trace'])


class TestUtilsDefineCommand(BaseHaTestCase):
    def test_define_command(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        cmd_mapper = {}

        def callback(cc, args):
            pass

        client_utils.define_command(subparsers, 'test-cmd',
                                    callback, cmd_mapper)
        self.assertIn('test-cmd', cmd_mapper)


class TestUtilsExit(BaseHaTestCase):
    def test_exit_with_msg(self):
        with self.assertRaises(SystemExit):
            client_utils.exit('error')

    def test_exit_no_msg(self):
        with self.assertRaises(SystemExit):
            client_utils.exit()


if __name__ == '__main__':
    unittest.main()
