#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for sm_client.client module."""
# pylint: disable=protected-access,unused-argument
import unittest
from unittest import mock

from tests.base import BaseHaTestCase

from sm_client.client import Client

try:
    from sm_client.client import _get_ksclient
    from sm_client.client import _get_endpoint
    from sm_client.client import get_client
    HAS_KSCLIENT = True
except ImportError:
    HAS_KSCLIENT = False


@unittest.skipUnless(HAS_KSCLIENT, "keystoneclient not available")
class TestGetKsclient(BaseHaTestCase):
    @mock.patch('sm_client.client.ksclient.Client')
    def test_get_ksclient(self, mock_ks):
        _get_ksclient(
            username='admin', password='pass',
            user_domain_name='Default',
            project_domain_name='Default',
            project_name='admin',
            auth_url='http://keystone:5000/v3',
            os_cacert='/ca.pem', insecure=False)
        mock_ks.assert_called_once()


@unittest.skipUnless(HAS_KSCLIENT, "keystoneclient not available")
class TestGetEndpoint(BaseHaTestCase):
    def test_get_endpoint(self):
        mock_client = mock.MagicMock()
        mock_client.service_catalog.url_for.return_value = 'http://smapi:7777'
        self.assertEqual(_get_endpoint(mock_client), 'http://smapi:7777')

    def test_get_endpoint_custom(self):
        mock_client = mock.MagicMock()
        mock_client.service_catalog.url_for.return_value = 'url'
        _get_endpoint(mock_client, service_name='custom',
                      endpoint_type='internal', os_region_name='Region2')
        kw = mock_client.service_catalog.url_for.call_args[1]
        self.assertEqual(kw['service_type'], 'custom')


@unittest.skipUnless(HAS_KSCLIENT, "keystoneclient not available")
class TestGetClient(BaseHaTestCase):
    @mock.patch('sm_client.client.Client')
    def test_with_token(self, mock_fn):
        mock_fn.return_value = 'client_obj'
        self.assertEqual(
            get_client(1, os_auth_token='tok', smc_url='http://smc:7777'),
            'client_obj')

    @mock.patch('sm_client.client.Client')
    @mock.patch('sm_client.client._get_ksclient')
    @mock.patch('sm_client.client._get_endpoint')
    def test_with_credentials(self, mock_ep, mock_ks, mock_fn):
        mock_ks_inst = mock.MagicMock()
        mock_ks_inst.auth_ref.auth_token = 'ks_token'
        mock_ks.return_value = mock_ks_inst
        mock_ep.return_value = 'http://smapi:7777'
        mock_fn.return_value = 'client_obj'
        self.assertEqual(
            get_client(1, os_username='admin', os_password='pass',
                       os_auth_url='http://keystone:5000/v3'),
            'client_obj')

    @mock.patch('sm_client.client.Client')
    @mock.patch('sm_client.client._get_ksclient')
    @mock.patch('sm_client.client._get_endpoint')
    def test_with_smc_url_override(self, mock_ep, mock_ks, mock_fn):
        mock_ks_inst = mock.MagicMock()
        mock_ks_inst.auth_ref.auth_token = 'ks_token'
        mock_ks.return_value = mock_ks_inst
        mock_fn.return_value = 'client_obj'
        get_client(1, os_username='admin', os_password='pass',
                   os_auth_url='http://keystone:5000/v3',
                   smc_url='http://override:7777')
        mock_ep.assert_not_called()


class TestClientFunction(BaseHaTestCase):
    def test_client_returns_v1(self):
        with mock.patch('sm_client.common.http.HTTPClient.__init__',
                        return_value=None):
            self.assertIsNotNone(Client(1, 'http://localhost:7777'))


if __name__ == '__main__':
    unittest.main()
