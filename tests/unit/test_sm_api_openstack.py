#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for sm_api.openstack.common modules."""
from tests.base import BaseHaTestCase

from sm_api.openstack.common import gettextutils
from sm_api.openstack.common import uuidutils
from sm_api.openstack.common import importutils
from sm_api.openstack.common import context as os_context
from sm_api.openstack.common.network_utils import parse_host_port
from sm_api.openstack.common.excutils import save_and_reraise_exception
from sm_api.openstack.common.version import VersionInfo


class TestGettextutils(BaseHaTestCase):
    def test_translate(self):
        self.assertEqual(gettextutils._("hello"), "hello")

    def test_install(self):
        gettextutils.install('sm_api')


class TestUuidutils(BaseHaTestCase):
    def test_generate_uuid(self):
        self.assertEqual(len(uuidutils.generate_uuid()), 36)

    def test_is_uuid_like_valid(self):
        self.assertTrue(uuidutils.is_uuid_like(uuidutils.generate_uuid()))

    def test_is_uuid_like_invalid(self):
        self.assertFalse(uuidutils.is_uuid_like('not-uuid'))
        self.assertFalse(uuidutils.is_uuid_like(None))


class TestImportutils(BaseHaTestCase):
    def test_import_class(self):
        cls = importutils.import_class('unittest.TestCase')
        self.assertIs(cls, __import__("unittest").TestCase)

    def test_import_class_fail(self):
        with self.assertRaises(ImportError):
            importutils.import_class('nonexistent.module.Class')

    def test_import_object(self):
        self.assertIsNotNone(
            importutils.import_object('collections.OrderedDict'))

    def test_import_module(self):
        self.assertTrue(hasattr(importutils.import_module('os.path'), 'join'))

    def test_try_import_success(self):
        self.assertIsNotNone(importutils.try_import('os'))

    def test_try_import_fail(self):
        self.assertEqual(
            importutils.try_import('nonexistent_module_xyz', default='fb'),
            'fb')

    def test_import_object_ns(self):
        self.assertIsNotNone(
            importutils.import_object_ns('collections', 'OrderedDict'))

    def test_import_object_ns_fallback(self):
        self.assertIsNotNone(
            importutils.import_object_ns(
                'nonexistent_ns', 'collections.OrderedDict'))


class TestContext(BaseHaTestCase):
    def test_request_context(self):
        ctx = os_context.RequestContext(
            auth_token='tok', user='u', tenant='t', is_admin=True)
        d = ctx.to_dict()
        self.assertEqual(d['user'], 'u')
        self.assertTrue(d['is_admin'])

    def test_request_context_auto_request_id(self):
        ctx = os_context.RequestContext()
        self.assertTrue(ctx.request_id.startswith('req-'))

    def test_generate_request_id(self):
        self.assertTrue(os_context.generate_request_id().startswith('req-'))

    def test_get_admin_context(self):
        self.assertTrue(os_context.get_admin_context().is_admin)

    def test_get_context_from_function_and_args(self):
        ctx = os_context.RequestContext()
        r = os_context.get_context_from_function_and_args(None, [ctx], {})
        self.assertIs(r, ctx)

    def test_get_context_from_function_and_args_none(self):
        r = os_context.get_context_from_function_and_args(
            None, ['not_ctx'], {})
        self.assertIsNone(r)


class TestNetworkUtils(BaseHaTestCase):
    def test_parse_host_port(self):
        self.assertEqual(parse_host_port('server:80'), ('server', 80))

    def test_parse_host_port_no_port(self):
        self.assertEqual(parse_host_port('server'), ('server', None))

    def test_parse_host_port_default(self):
        self.assertEqual(
            parse_host_port('server', default_port=443), ('server', 443))

    def test_parse_host_port_ipv6(self):
        self.assertEqual(parse_host_port('[::1]:80'), ('::1', 80))

    def test_parse_host_port_ipv6_no_port(self):
        self.assertEqual(parse_host_port('[::1]'), ('::1', None))

    def test_parse_host_port_ipv6_unescaped(self):
        _, p = parse_host_port('2001:db8::1', default_port=1234)
        self.assertEqual(p, 1234)


class TestExcutils(BaseHaTestCase):
    def test_save_and_reraise(self):
        with self.assertRaises(ValueError):
            try:
                raise ValueError("orig")
            except ValueError:
                with save_and_reraise_exception():
                    pass


class TestVersion(BaseHaTestCase):
    def test_version_info(self):
        v = VersionInfo('pip')
        self.assertIsNotNone(str(v))

    def test_version_repr(self):
        self.assertIn('VersionInfo', repr(VersionInfo('pip')))

    def test_cached_version(self):
        v = VersionInfo('pip')
        self.assertTrue(v.cached_version_string(prefix='v').startswith('v'))


if __name__ == '__main__':
    import unittest
    unittest.main()
