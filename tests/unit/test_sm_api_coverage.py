#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

"""Coverage-focused tests for sm_api timeutils and extended validation."""
import datetime
import unittest

from tests.base import BaseHaTestCase


class TestTimeutils(BaseHaTestCase):
    def test_utcnow(self):
        from sm_api.openstack.common import timeutils
        r = timeutils.utcnow()
        self.assertIsInstance(r, datetime.datetime)

    def test_isotime(self):
        from sm_api.openstack.common import timeutils
        r = timeutils.isotime()
        self.assertIsInstance(r, str)

    def test_isotime_with_dt(self):
        from sm_api.openstack.common import timeutils
        dt = datetime.datetime(2024, 1, 1, 12, 0, 0)
        r = timeutils.isotime(dt)
        self.assertIn('2024', r)

    def test_parse_isotime(self):
        from sm_api.openstack.common import timeutils
        r = timeutils.parse_isotime('2024-01-01T12:00:00Z')
        self.assertIsInstance(r, datetime.datetime)

    def test_strtime(self):
        from sm_api.openstack.common import timeutils
        r = timeutils.strtime()
        self.assertIsInstance(r, str)

    def test_parse_strtime(self):
        from sm_api.openstack.common import timeutils
        s = timeutils.strtime()
        r = timeutils.parse_strtime(s)
        self.assertIsInstance(r, datetime.datetime)

    def test_normalize_time(self):
        from sm_api.openstack.common import timeutils
        import iso8601
        try:
            tz = iso8601.iso8601.Utc()
        except AttributeError:
            tz = iso8601.UTC
        dt = datetime.datetime(2024, 1, 1, tzinfo=tz)
        r = timeutils.normalize_time(dt)
        self.assertIsNone(r.tzinfo)

    def test_is_older_than(self):
        from sm_api.openstack.common import timeutils
        old = datetime.datetime(2020, 1, 1)
        self.assertTrue(timeutils.is_older_than(old, 1))

    def test_is_newer_than(self):
        from sm_api.openstack.common import timeutils
        now = timeutils.utcnow()
        self.assertIsInstance(
            timeutils.is_newer_than(now, 999999), bool)

    def test_utcnow_ts(self):
        from sm_api.openstack.common import timeutils
        r = timeutils.utcnow_ts()
        self.assertIsInstance(r, (int, float))

    def test_delta_seconds(self):
        from sm_api.openstack.common import timeutils
        a = datetime.datetime(2024, 1, 1)
        b = datetime.datetime(2024, 1, 2)
        r = timeutils.delta_seconds(a, b)
        self.assertAlmostEqual(r, 86400.0)

    def test_set_and_clear_override(self):
        from sm_api.openstack.common import timeutils
        fixed = datetime.datetime(2024, 6, 15)
        timeutils.set_time_override(fixed)
        timeutils.clear_time_override()

    def test_advance_time_delta(self):
        from sm_api.openstack.common import timeutils
        fixed = datetime.datetime(2024, 6, 15)
        timeutils.set_time_override(fixed)
        timeutils.advance_time_delta(
            datetime.timedelta(hours=1))
        r = timeutils.utcnow()
        self.assertEqual(r.hour, 1)
        timeutils.clear_time_override()

    def test_advance_time_seconds(self):
        from sm_api.openstack.common import timeutils
        fixed = datetime.datetime(2024, 6, 15)
        timeutils.set_time_override(fixed)
        timeutils.advance_time_seconds(3600)
        r = timeutils.utcnow()
        self.assertEqual(r.hour, 1)
        timeutils.clear_time_override()

    def test_marshall_unmarshall(self):
        from sm_api.openstack.common import timeutils
        m = timeutils.marshall_now()
        self.assertIn('day', m)
        r = timeutils.unmarshall_time(m)
        self.assertIsInstance(r, datetime.datetime)


class TestCommonUtilsValidation(BaseHaTestCase):
    """Extended validation tests unique to this file."""

    def test_is_valid_mac_invalid(self):
        from sm_api.common.utils import is_valid_mac
        self.assertFalse(is_valid_mac('invalid'))

    def test_is_valid_ipv4_invalid(self):
        from sm_api.common.utils import is_valid_ipv4
        self.assertFalse(is_valid_ipv4('999.999.999.999'))

    def test_is_valid_ipv6_invalid(self):
        from sm_api.common.utils import is_valid_ipv6
        self.assertFalse(is_valid_ipv6('not-ipv6'))

    def test_is_valid_cidr_invalid(self):
        from sm_api.common.utils import is_valid_cidr
        self.assertFalse(is_valid_cidr('bad'))

    def test_is_valid_ipv6_cidr_invalid(self):
        from sm_api.common.utils import is_valid_ipv6_cidr
        self.assertFalse(is_valid_ipv6_cidr('bad'))

    def test_safe_rstrip_not_string(self):
        from sm_api.common.utils import safe_rstrip
        self.assertEqual(safe_rstrip(123), 123)

    def test_get_shortened_ipv6_full(self):
        from sm_api.common.utils import get_shortened_ipv6
        r = get_shortened_ipv6(
            '0000:0000:0000:0000:0000:0000:0000:0001')
        self.assertEqual(r, '::1')


class TestObjectsBaseExtended(BaseHaTestCase):
    """Extended objects.base tests unique to this file."""

    def test_iteritems(self):
        from sm_api.objects.base import Sm_apiObject
        obj = Sm_apiObject()
        items = list(obj.iteritems())
        self.assertIsInstance(items, list)

    def test_contains(self):
        from sm_api.objects.base import Sm_apiObject
        obj = Sm_apiObject()
        obj._test = 'val'
        self.assertIn('test', obj)
        self.assertNotIn('nonexistent', obj)

    def test_obj_class_from_name_not_found(self):
        from sm_api.objects.base import Sm_apiObject
        from sm_api.common.exception import (
            UnsupportedObjectError)
        with self.assertRaises(UnsupportedObjectError):
            Sm_apiObject.obj_class_from_name(
                'NonExistentObj', '1.0')

    def test_attr_from_primitive(self):
        from sm_api.objects.base import Sm_apiObject
        obj = Sm_apiObject()
        r = obj._attr_from_primitive('test', 'value')
        self.assertEqual(r, 'value')

    def test_attr_to_primitive(self):
        from sm_api.objects.base import Sm_apiObject
        obj = Sm_apiObject()
        obj._context = 'ctx'
        r = obj._attr_to_primitive('_context')
        self.assertEqual(r, 'ctx')


class TestExceptionExtended(BaseHaTestCase):
    """Extended exception tests unique to this file."""

    def test_exception_kwargs_format(self):
        from sm_api.common.exception import SmApiException
        e = SmApiException(code=500)
        self.assertIsNotNone(str(e))

    def test_process_execution_error_defaults(self):
        from sm_api.common.exception import (
            ProcessExecutionError)
        e = ProcessExecutionError()
        self.assertIn('Unexpected', str(e))

    def test_image_exceptions(self):
        from sm_api.common import exception
        for cls_name in [
            'ImageNotFound', 'ImageUnacceptable',
            'ImageConvertFailed', 'InvalidImageRef',
            'ImageNotAuthorized',
            'GlanceConnectionFailed',
        ]:
            cls = getattr(exception, cls_name)
            self.assertTrue(issubclass(cls, Exception))


if __name__ == '__main__':
    unittest.main()
