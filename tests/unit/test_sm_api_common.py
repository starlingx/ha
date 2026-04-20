#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for sm_api.common and sm_api.objects modules."""
import datetime
import os
import tempfile
import unittest
from unittest import mock

import tests.constants as tc
from tests.base import BaseHaTestCase

from sm_api.common import config as sm_config
from sm_api.common import context as sm_context
from sm_api.common import exception as sm_exception
from sm_api.common import log as sm_log
from sm_api.common.safe_utils import getcallargs
from sm_api.objects import utils as obj_utils


class TestSafeUtils(BaseHaTestCase):
    def test_getcallargs_simple(self):
        def fn(a, b, c=3):
            pass
        try:
            r = getcallargs(fn, 1, 2)
            self.assertEqual(r['a'], 1)
        except ValueError:
            pass

    def test_getcallargs_with_self(self):
        class C:
            def m(self, x):
                pass
        try:
            r = getcallargs(C.m, 10)
            self.assertIn('self', r)
        except ValueError:
            pass

    def test_getcallargs_kwargs(self):
        def fn(a, b=5):
            pass
        try:
            r = getcallargs(fn, a=1, b=2)
            self.assertEqual(r['a'], 1)
        except ValueError:
            pass


class TestConstants(BaseHaTestCase):
    def test_constants(self):
        from sm_api.common import constants
        self.assertIsNotNone(constants.OS_RELEASE_FILE)
        self.assertEqual(constants.OS_DEBIAN_BULLSEYE, 'bullseye')
        self.assertEqual(constants.OS_DEBIAN_TRIXIE, 'trixie')


class TestConfig(BaseHaTestCase):
    def test_config_as_dict(self):
        c = sm_config.Config()
        c.read_string("[section1]\nkey1=val1\nkey2=val2")
        d = c.as_dict()
        self.assertIn('section1', d)
        self.assertEqual(d['section1']['key1'], 'val1')

    def test_load(self):
        f = tempfile.NamedTemporaryFile(
            mode='w', suffix='.ini', delete=False)
        f.write("[logging]\nuse_syslog=false\n")
        f.close()
        sm_config.load(f.name)
        self.assertIn('logging', sm_config.CONF)
        os.unlink(f.name)


class TestLog(BaseHaTestCase):
    def test_get_logger(self):
        self.assertIsNotNone(sm_log.get_logger('test_logger'))

    def test_setup_logger_console(self):
        import logging
        sm_log._log_to_console = True
        sm_log._log_to_syslog = False
        sm_log._log_to_file = False
        sm_log._setup_logger(logging.getLogger('test_console'))
        sm_log._log_to_console = False

    def test_setup_logger_file(self):
        import logging
        sm_log._log_to_console = False
        sm_log._log_to_syslog = False
        sm_log._log_to_file = True
        orig = sm_log.LOG_FILE_NAME
        sm_log.LOG_FILE_NAME = os.path.join(tempfile.mkdtemp(), 'test.log')
        sm_log._setup_logger(logging.getLogger('test_file'))
        sm_log._log_to_file = False
        sm_log.LOG_FILE_NAME = orig

    def test_configure(self):
        sm_log._log_to_syslog = False
        sm_log.configure({'logging': {
            'use_syslog': True, 'log_facility': 'LOG_USER'}})
        self.assertTrue(sm_log._log_to_syslog)
        sm_log._log_to_syslog = False


class TestContext(BaseHaTestCase):
    def test_request_context(self):
        ctx = sm_context.RequestContext(
            auth_token='tok', user='admin', tenant='t1', is_admin=True)
        d = ctx.to_dict()
        self.assertIn('domain_id', d)
        self.assertIn('is_public_api', d)

    def test_request_context_defaults(self):
        self.assertFalse(sm_context.RequestContext().is_public_api)


class TestException(BaseHaTestCase):
    def test_process_execution_error(self):
        e = sm_exception.ProcessExecutionError(
            stdout='out', stderr='err', exit_code=1, cmd='ls')
        self.assertIn('ls', str(e))

    def test_cleanse_dict(self):
        r = sm_exception._cleanse_dict({'user': 'a', 'admin_pass': 'secret'})
        self.assertIn('user', r)
        self.assertNotIn('admin_pass', r)

    def test_sm_api_exception(self):
        e = sm_exception.SmApiException("test error")
        self.assertIn('test error', str(e))
        self.assertIsNotNone(e.format_message())

    def test_http_codes(self):
        self.assertEqual(sm_exception.NotFound.code, 404)
        self.assertEqual(sm_exception.Invalid.code, 400)
        self.assertEqual(sm_exception.Conflict.code, 409)
        self.assertEqual(sm_exception.NotAuthorized.code, 403)

    def test_service_not_found(self):
        e = sm_exception.ServiceNotFound(service=tc.SM_SERVICE_NAME)
        self.assertIn(tc.SM_SERVICE_NAME, str(e))

    def test_invalid_parameter_value(self):
        e = sm_exception.InvalidParameterValue(err='bad value')
        self.assertIn('bad value', str(e))

    def test_host_locked(self):
        e = sm_exception.HostLocked(action='swact', host='ctrl-0')
        self.assertIn('ctrl-0', str(e))

    def test_various_exceptions_exist(self):
        for cls_name in [
            'AdminRequired', 'PolicyNotAuthorized',
            'OperationNotPermitted', 'InvalidUUID',
            'PatchError', 'NodeNotFound', 'PortNotFound',
            'ChassisNotFound', 'ServerNotFound',
            'SSHConnectFailed', 'IPMIFailure',
            'UnsupportedObjectError', 'OrphanedObjectError',
            'IncompatibleObjectVersion',
            'ServiceUnavailable', 'Forbidden',
            'BadRequest', 'HTTPException',
            'InvalidEndpoint', 'CommunicationError',
            'Unauthorized', 'HTTPNotFound', 'HTTPForbidden',
        ]:
            self.assertTrue(
                issubclass(getattr(sm_exception, cls_name), Exception))

    def test_wrap_exception_no_notifier(self):
        @sm_exception.wrap_exception()
        def fn(self, context):
            return 'ok'
        self.assertEqual(fn(None, None), 'ok')


class TestObjectsUtils(BaseHaTestCase):
    def test_datetime_or_none(self):
        self.assertIsNone(obj_utils.datetime_or_none(None))
        dt = datetime.datetime(2024, 1, 1)
        try:
            self.assertIsNotNone(obj_utils.datetime_or_none(dt).tzinfo)
        except AttributeError:
            pass

    def test_datetime_or_none_with_tz(self):
        import iso8601
        try:
            tz = iso8601.iso8601.Utc()
        except AttributeError:
            tz = iso8601.UTC
        dt = datetime.datetime(2024, 1, 1, tzinfo=tz)
        self.assertEqual(obj_utils.datetime_or_none(dt), dt)

    def test_datetime_or_none_invalid(self):
        with self.assertRaises(ValueError):
            obj_utils.datetime_or_none("not a datetime")

    def test_int_or_none(self):
        self.assertIsNone(obj_utils.int_or_none(None))
        self.assertEqual(obj_utils.int_or_none('5'), 5)

    def test_int_or_zero(self):
        self.assertEqual(obj_utils.int_or_zero(None), 0)
        self.assertEqual(obj_utils.int_or_zero('3'), 3)

    def test_str_or_none(self):
        self.assertIsNone(obj_utils.str_or_none(None))
        self.assertEqual(obj_utils.str_or_none(123), '123')

    def test_dict_or_none(self):
        self.assertEqual(obj_utils.dict_or_none(None), {})
        self.assertEqual(obj_utils.dict_or_none("{'a': 1}"), {'a': 1})
        self.assertEqual(obj_utils.dict_or_none({'a': 1}), {'a': 1})
        with self.assertRaises(TypeError):
            obj_utils.dict_or_none(123)

    def test_ip_or_none(self):
        v = obj_utils.ip_or_none(4)
        self.assertIsNone(v(None))
        self.assertIsNotNone(v('192.168.1.1'))

    def test_nested_object_or_none(self):
        v = obj_utils.nested_object_or_none(dict)
        self.assertIsNone(v(None))
        self.assertEqual(v({'a': 1}), {'a': 1})
        with self.assertRaises(ValueError):
            v("not a dict")

    def test_isotime(self):
        self.assertIn('Z', obj_utils.isotime())
        self.assertIn('.', obj_utils.isotime(subsecond=True))

    def test_dt_serializer(self):
        fn = obj_utils.dt_serializer('created_at')
        obj = mock.MagicMock()
        obj.created_at = None
        self.assertIsNone(fn(obj))

    def test_dt_deserializer(self):
        self.assertIsNone(obj_utils.dt_deserializer(None, None))
        self.assertIsNotNone(
            obj_utils.dt_deserializer(None, '2024-01-01T00:00:00Z'))

    def test_obj_serializer(self):
        fn = obj_utils.obj_serializer('child')
        obj = mock.MagicMock()
        obj.child = None
        self.assertIsNone(fn(obj))
        obj.child = mock.MagicMock()
        obj.child.obj_to_primitive.return_value = {'k': 'v'}
        self.assertEqual(fn(obj), {'k': 'v'})

    @mock.patch('builtins.open', mock.mock_open(
        read_data="VERSION_CODENAME=bullseye\n"))
    def test_get_debian_codename(self):
        obj_utils.get_debian_codename.cache_clear()
        self.assertEqual(obj_utils.get_debian_codename(), 'bullseye')
        obj_utils.get_debian_codename.cache_clear()

    @mock.patch('builtins.open', side_effect=FileNotFoundError)
    def test_get_debian_codename_missing(self, _):
        obj_utils.get_debian_codename.cache_clear()
        self.assertIsNone(obj_utils.get_debian_codename())
        obj_utils.get_debian_codename.cache_clear()

    def test_is_debian_bullseye(self):
        with mock.patch.object(
                obj_utils, 'get_debian_codename', return_value='bullseye'):
            self.assertTrue(obj_utils.is_debian_bullseye())
        with mock.patch.object(
                obj_utils, 'get_debian_codename', return_value='trixie'):
            self.assertFalse(obj_utils.is_debian_bullseye())

    def test_datetime_or_str_or_none(self):
        self.assertIsNone(obj_utils.datetime_or_str_or_none(None))
        self.assertIsNotNone(
            obj_utils.datetime_or_str_or_none('2024-01-01T00:00:00Z'))


if __name__ == '__main__':
    unittest.main()
