#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Tests for sm_api.openstack.common.rpc modules."""
import unittest
from unittest import mock

from tests.base import BaseHaTestCase

from sm_api.openstack.common.rpc import common as rpc_common
from sm_api.openstack.common.rpc import dispatcher as rpc_dispatcher
from sm_api.openstack.common.rpc import impl_fake
from sm_api.openstack.common.rpc import matchmaker
from sm_api.openstack.common.rpc import proxy as rpc_proxy
from sm_api.openstack.common.rpc import serializer as rpc_serializer
from sm_api.openstack.common.rpc import service as rpc_service


class TestRpcCommon(BaseHaTestCase):

    def test_rpc_exception(self):
        self.assertIn("test", str(rpc_common.RPCException("test")))

    def test_remote_error(self):
        self.assertIn("Exc", str(rpc_common.RemoteError("Exc", "msg", "tb")))

    def test_timeout(self):
        self.assertIsNotNone(
            str(rpc_common.Timeout(info="i", topic="t", method="m")))

    def test_duplicate_message_error(self):
        self.assertTrue(issubclass(
            rpc_common.DuplicateMessageError, rpc_common.RPCException))

    def test_common_rpc_context(self):
        ctx = rpc_common.CommonRpcContext(user='u', tenant='t')
        self.assertEqual(ctx.to_dict()['user'], 'u')

    def test_common_rpc_context_deepcopy(self):
        ctx = rpc_common.CommonRpcContext(user='u')
        self.assertEqual(ctx.deepcopy().user, 'u')

    def test_common_rpc_context_elevated(self):
        ctx = rpc_common.CommonRpcContext(user='u')
        self.assertTrue(ctx.elevated().is_admin)

    def test_safe_log(self):
        rpc_common._safe_log(mock.MagicMock(), "msg %s", {"_msg": "data"})

    def test_version_is_compatible(self):
        self.assertTrue(rpc_common.version_is_compatible('1.5', '1.3'))
        self.assertFalse(rpc_common.version_is_compatible('1.0', '2.0'))
        self.assertFalse(rpc_common.version_is_compatible('1.0', '1.5'))

    def test_serialize_deserialize_msg(self):
        r = rpc_common.serialize_msg({'key': 'val'})
        self.assertEqual(rpc_common.deserialize_msg(r)['key'], 'val')

    def test_deserialize_msg_no_envelope(self):
        self.assertEqual(
            rpc_common.deserialize_msg({'key': 'val'})['key'], 'val')

    def test_serialize_remote_exception(self):
        import sys
        try:
            raise ValueError("test error")
        except ValueError:
            data = rpc_common.serialize_remote_exception(sys.exc_info())
        self.assertIn('class', data)

    def test_client_exception(self):
        self.assertIsInstance(rpc_common.ClientException(), Exception)

    def test_catch_client_exception(self):
        self.assertEqual(
            rpc_common.catch_client_exception([ValueError], lambda: 'ok'),
            'ok')

    def test_catch_client_exception_raises(self):

        def bad():
            raise ValueError("fail")
        with self.assertRaises(rpc_common.ClientException):
            rpc_common.catch_client_exception([ValueError], bad)

    def test_client_exceptions_decorator(self):
        @rpc_common.client_exceptions(ValueError)
        def fn():
            return 'ok'
        self.assertEqual(fn(), 'ok')

    def test_connection_class(self):
        self.assertTrue(hasattr(rpc_common.Connection, 'close'))


class TestRpcSerializer(BaseHaTestCase):

    def test_no_op_serializer(self):
        s = rpc_serializer.NoOpSerializer()
        self.assertEqual(s.serialize_entity(None, 'val'), 'val')
        self.assertEqual(s.deserialize_entity(None, 'val'), 'val')


class TestRpcDispatcher(BaseHaTestCase):

    def test_dispatcher_init(self):
        self.assertIsNotNone(rpc_dispatcher.RpcDispatcher([mock.MagicMock()]))


class TestRpcProxy(BaseHaTestCase):

    def test_proxy_init(self):
        p = rpc_proxy.RpcProxy('topic', '1.0')
        self.assertEqual(p.topic, 'topic')

    def test_make_namespaced_msg(self):
        p = rpc_proxy.RpcProxy('topic', '1.0')
        msg = p.make_namespaced_msg('test', None, arg1='val')
        self.assertEqual(msg['method'], 'test')
        self.assertIn('arg1', msg['args'])

    def test_make_msg(self):
        msg = rpc_proxy.RpcProxy('topic', '1.0').make_msg('test', arg1='val')
        self.assertEqual(msg['method'], 'test')


class TestRpcImplFake(BaseHaTestCase):

    def test_create_connection(self):
        self.assertIsNotNone(impl_fake.create_connection(mock.MagicMock()))

    def test_connection_ops(self):
        conn = impl_fake.Connection()
        conn.create_consumer('topic', mock.MagicMock(), fanout=False)
        conn.close()

    def test_cast(self):
        impl_fake.cast(mock.MagicMock(), mock.MagicMock(),
                       'topic', {'method': 'test', 'args': {}})

    def test_cleanup(self):
        impl_fake.cleanup()

    def test_check_serialize(self):
        impl_fake.check_serialize({'key': 'val'})

    def test_fanout_cast(self):
        impl_fake.fanout_cast(mock.MagicMock(), mock.MagicMock(),
                              'topic', {'method': 'test', 'args': {}})

    def test_multicall(self):
        impl_fake.CONSUMERS.clear()
        self.assertIsNotNone(impl_fake.multicall(
            mock.MagicMock(), mock.MagicMock(),
            'topic', {'method': 'test', 'args': {}}))


class TestRpcMatchmaker(BaseHaTestCase):

    def test_matchmaker_base(self):
        self.assertIsNotNone(matchmaker.MatchMakerBase())

    def test_direct_exchange(self):
        self.assertIsNotNone(matchmaker.DirectExchange())

    def test_stub_exchange(self):
        self.assertEqual(matchmaker.StubExchange().run('key'), [('key', None)])

    def test_localhost_exchange(self):
        self.assertIsNotNone(matchmaker.MatchMakerLocalhost())


class TestRpcService(BaseHaTestCase):

    def test_service_module(self):
        self.assertTrue(hasattr(rpc_service, 'Service'))


class TestRpcZmqReceiver(BaseHaTestCase):

    def test_module(self):
        try:
            from sm_api.openstack.common.rpc import zmq_receiver
            self.assertIsNotNone(zmq_receiver)
        except ImportError:
            self.skipTest('zmq not available')


if __name__ == '__main__':
    unittest.main()
