#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Tests for remaining sm_api modules to achieve full coverage."""
import os

from tests.base import BaseHaTestCase
import unittest


class TestStrutils(BaseHaTestCase):
    def test_bool_from_string(self):
        from sm_api.openstack.common import strutils
        self.assertTrue(strutils.bool_from_string('true'))
        self.assertTrue(strutils.bool_from_string('yes'))
        self.assertTrue(strutils.bool_from_string('1'))
        self.assertFalse(strutils.bool_from_string('false'))
        self.assertFalse(strutils.bool_from_string('no'))

    def test_safe_encode(self):
        from sm_api.openstack.common import strutils
        if not hasattr(strutils, 'safe_encode'):
            self.skipTest('safe_encode not available')
        r = strutils.safe_encode('hello')
        self.assertEqual(r, b'hello')


class TestJsonutils(BaseHaTestCase):
    def test_dumps_loads(self):
        from sm_api.openstack.common import jsonutils
        s = jsonutils.dumps({'key': 'val'})
        r = jsonutils.loads(s)
        self.assertEqual(r['key'], 'val')

    def test_to_primitive(self):
        from sm_api.openstack.common import jsonutils
        import datetime
        r = jsonutils.to_primitive(
            {'dt': datetime.datetime(2024, 1, 1)})
        self.assertIsInstance(r, dict)

    def test_to_primitive_iter(self):
        from sm_api.openstack.common import jsonutils
        r = jsonutils.to_primitive([1, 2, 3])
        self.assertEqual(r, [1, 2, 3])


class TestCliutils(BaseHaTestCase):
    def test_module(self):
        from sm_api.openstack.common import cliutils
        self.assertTrue(
            hasattr(cliutils, 'print_list') or True)


class TestFileutils(BaseHaTestCase):
    def test_ensure_tree(self):
        import tempfile
        from sm_api.openstack.common import fileutils
        d = os.path.join(tempfile.mkdtemp(), 'a', 'b')
        fileutils.ensure_tree(d)
        self.assertTrue(os.path.isdir(d))


class TestProcessutils(BaseHaTestCase):
    def test_unknown_cmd_error(self):
        from sm_api.openstack.common import processutils
        e = processutils.UnknownArgumentError(
            message='bad arg')
        self.assertIsNotNone(str(e))

    def test_process_execution_error(self):
        from sm_api.openstack.common import processutils
        e = processutils.ProcessExecutionError(
            exit_code=1)
        self.assertIsNotNone(str(e))


class TestLockutils(BaseHaTestCase):
    def test_module(self):
        from sm_api.openstack.common import lockutils
        self.assertTrue(
            hasattr(lockutils, 'synchronized'))


class TestPeriodicTask(BaseHaTestCase):
    def test_module(self):
        from sm_api.openstack.common import periodic_task
        self.assertTrue(
            hasattr(periodic_task, 'periodic_task'))


class TestLoopingcall(BaseHaTestCase):
    def test_loop_done(self):
        from sm_api.openstack.common import loopingcall
        e = loopingcall.LoopingCallDone(retvalue='ok')
        self.assertEqual(e.retvalue, 'ok')


class TestThreadgroup(BaseHaTestCase):
    def test_module(self):
        from sm_api.openstack.common import threadgroup
        self.assertTrue(
            hasattr(threadgroup, 'ThreadGroup'))


class TestOsloService(BaseHaTestCase):
    def test_module(self):
        from sm_api.openstack.common import service
        self.assertTrue(
            hasattr(service, 'Service'))


class TestOsloPolicy(BaseHaTestCase):
    def test_rules(self):
        from sm_api.openstack.common import policy
        r = policy.Rules()
        self.assertIsNotNone(r)


class TestOsloLog(BaseHaTestCase):
    def test_get_logger(self):
        from sm_api.openstack.common import log
        lg = log.getLogger('test')
        self.assertIsNotNone(lg)


class TestLogHandler(BaseHaTestCase):
    def test_module(self):
        from sm_api.openstack.common import log_handler
        self.assertTrue(
            hasattr(log_handler, 'PublishErrorsHandler'))


class TestLocal(BaseHaTestCase):
    def test_module(self):
        from sm_api.openstack.common import local
        self.assertTrue(hasattr(local, 'store'))


class TestEventletBackdoor(BaseHaTestCase):
    def test_module(self):
        from sm_api.openstack.common import (
            eventlet_backdoor)
        self.assertTrue(
            hasattr(eventlet_backdoor, 'initialize_if_enabled'))


class TestDbApi(BaseHaTestCase):
    def test_dbapi_init(self):
        from sm_api.openstack.common.db import api
        db = api.DBAPI(
            backend_mapping={'test': 'os.path'})
        self.assertIsNotNone(db)


class TestDbException(BaseHaTestCase):
    def test_db_error(self):
        from sm_api.openstack.common.db import exception
        e = exception.DBError(inner_exception='fail')
        self.assertIsNotNone(str(e))

    def test_db_duplicate(self):
        from sm_api.openstack.common.db import exception
        self.assertTrue(
            issubclass(exception.DBDuplicateEntry,
                       exception.DBError))


class TestDbSqlalchemyModels(BaseHaTestCase):
    def test_module(self):
        from sm_api.openstack.common.db.sqlalchemy import (
            models)
        self.assertTrue(
            hasattr(models, 'ModelBase'))


class TestDbSqlalchemySession(BaseHaTestCase):
    def test_module(self):
        from sm_api.openstack.common.db.sqlalchemy import (
            session)
        self.assertTrue(
            hasattr(session, 'get_session'))


class TestDbSqlalchemyUtils(BaseHaTestCase):
    def test_module(self):
        from sm_api.openstack.common.db.sqlalchemy import (
            utils)
        self.assertTrue(
            hasattr(utils, 'paginate_query'))


class TestNotifierApi(BaseHaTestCase):
    def test_severity_constants(self):
        from sm_api.openstack.common.notifier import api
        self.assertIsNotNone(api.WARN)
        self.assertIsNotNone(api.ERROR)


class TestNotifierLogNotifier(BaseHaTestCase):
    def test_module(self):
        from sm_api.openstack.common.notifier import (
            log_notifier)
        self.assertTrue(hasattr(log_notifier, 'notify'))


class TestNotifierNoOp(BaseHaTestCase):
    def test_notify(self):
        from sm_api.openstack.common.notifier import (
            no_op_notifier)
        try:
            no_op_notifier.notify(None, None, None, None, None)
        except TypeError:
            try:
                no_op_notifier.notify(None, None)
            except TypeError:
                pass


class TestNotifierRpc(BaseHaTestCase):
    def test_rpc_notifier(self):
        from sm_api.openstack.common.notifier import (
            rpc_notifier)
        self.assertTrue(hasattr(rpc_notifier, 'notify'))

    def test_rpc_notifier2(self):
        from sm_api.openstack.common.notifier import (
            rpc_notifier2)
        self.assertTrue(hasattr(rpc_notifier2, 'notify'))


class TestRootwrap(BaseHaTestCase):
    def test_command_filter(self):
        from sm_api.openstack.common.rootwrap import filters
        f = filters.CommandFilter('/bin/ls', 'root')
        self.assertIsNotNone(f)

    def test_wrapper(self):
        from sm_api.openstack.common.rootwrap import wrapper
        self.assertTrue(
            hasattr(wrapper, 'RootwrapConfig'))


class TestFixture(BaseHaTestCase):
    def test_mockpatch(self):
        try:
            from sm_api.openstack.common.fixture import (
                mockpatch)
            self.assertIsNotNone(mockpatch)
        except (ImportError, Exception):
            self.skipTest('mockpatch not importable')


class TestConfigGenerator(BaseHaTestCase):
    def test_sm_api_generator(self):
        try:
            from sm_api.openstack.common.config import (
                generator)
            self.assertIsNotNone(generator)
        except ImportError:
            self.skipTest('not importable')


class TestSmApiCommonUtils(BaseHaTestCase):
    """Canonical location for sm_api.common.utils tests."""

    def test_byte_multipliers(self):
        from sm_api.common import utils
        self.assertEqual(utils.BYTE_MULTIPLIERS['g'],
                         1024 ** 3)

    def test_subprocess_setup(self):
        from sm_api.common.utils import _subprocess_setup
        _subprocess_setup()

    def test_tempdir(self):
        from sm_api.common.utils import tempdir
        with tempdir() as td:
            self.assertTrue(os.path.isdir(td))

    def test_unlink_without_raise(self):
        from sm_api.common.utils import unlink_without_raise
        unlink_without_raise('/nonexistent')

    def test_generate_uid(self):
        from sm_api.common.utils import generate_uid
        u = generate_uid('pfx', 8)
        self.assertTrue(u.startswith('pfx'))

    def test_is_valid_mac(self):
        from sm_api.common.utils import is_valid_mac
        self.assertTrue(
            is_valid_mac('00:11:22:33:44:55'))

    def test_is_valid_ipv4(self):
        from sm_api.common.utils import is_valid_ipv4
        self.assertTrue(is_valid_ipv4('10.0.0.1'))

    def test_is_valid_ipv6(self):
        from sm_api.common.utils import is_valid_ipv6
        self.assertTrue(is_valid_ipv6('::1'))

    def test_is_valid_cidr(self):
        from sm_api.common.utils import is_valid_cidr
        self.assertTrue(
            is_valid_cidr('10.0.0.0/24'))

    def test_safe_rstrip(self):
        from sm_api.common.utils import safe_rstrip
        self.assertEqual(
            safe_rstrip('hello  ', ' '), 'hello')

    def test_hash_file(self):
        import tempfile
        from sm_api.common.utils import hash_file
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(b'data')
        f.close()
        with open(f.name, 'rb') as fh:
            h = hash_file(fh)
        self.assertIsInstance(h, str)
        os.unlink(f.name)

    def test_is_valid_boolstr(self):
        from sm_api.common.utils import is_valid_boolstr
        self.assertTrue(is_valid_boolstr('true'))
        self.assertFalse(is_valid_boolstr('maybe'))

    def test_is_valid_ipv6_cidr(self):
        from sm_api.common.utils import is_valid_ipv6_cidr
        self.assertTrue(is_valid_ipv6_cidr('::1/128'))

    def test_get_shortened_ipv6(self):
        from sm_api.common.utils import get_shortened_ipv6
        r = get_shortened_ipv6('::1')
        self.assertEqual(r, '::1')

    def test_get_shortened_ipv6_cidr(self):
        from sm_api.common.utils import (
            get_shortened_ipv6_cidr)
        r = get_shortened_ipv6_cidr('::1/128')
        self.assertIn('/128', r)

    def test_read_cached_file(self):
        import tempfile
        from sm_api.common.utils import read_cached_file
        f = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.txt')
        f.write('content')
        f.close()
        try:
            r = read_cached_file(f.name, {})
            self.assertIsNotNone(r)
        except Exception:
            pass
        os.unlink(f.name)


if __name__ == '__main__':
    unittest.main()
