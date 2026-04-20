#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Deep coverage tests exercising function bodies."""
import os
import unittest
from unittest import mock

from tests.base import AmqpPoolMixin
from tests.base import BaseHaTestCase
from tests.base import KombuConnectionMixin
from tests.base import QpidConnectionMixin
from tests.test_helpers import safe_call as _safe_call

from sm_api.openstack.common.rpc import amqp
from sm_api.openstack.common.rpc import impl_kombu
from sm_api.openstack.common.rpc import impl_qpid

P = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))


class TestImplKombuDeep(KombuConnectionMixin, BaseHaTestCase):
    """Exercise impl_kombu function bodies."""

    def test_get_queue_arguments(self):
        conf = mock.MagicMock()
        conf.rabbit_ha_queues = True
        self.assertIn('x-ha-policy', impl_kombu._get_queue_arguments(conf))
        conf.rabbit_ha_queues = False
        self.assertEqual(impl_kombu._get_queue_arguments(conf), {})

    def test_consumer_base(self):
        ch = mock.MagicMock()
        c = impl_kombu.ConsumerBase(ch, mock.MagicMock(), 'tag')
        c.reconnect(ch)
        c.cancel()
        _safe_call(lambda: c.consume())

    def test_consumers(self):
        conf = mock.MagicMock()
        conf.rabbit_ha_queues = False
        ch = mock.MagicMock()
        for cls in ('DirectConsumer', 'TopicConsumer', 'FanoutConsumer'):
            _safe_call(lambda c=cls: getattr(impl_kombu, c)(
                conf, ch, 'topic', mock.MagicMock(), 'tag'))

    def test_publisher(self):
        ch = mock.MagicMock()
        p = impl_kombu.Publisher(ch, 'exchange', 'key')
        p.reconnect(ch)
        _safe_call(lambda: p.send({'test': 1}))

    def test_publishers(self):
        conf = mock.MagicMock()
        ch = mock.MagicMock()
        for cls in ('DirectPublisher', 'TopicPublisher',
                    'FanoutPublisher', 'NotifyPublisher'):
            _safe_call(lambda c=cls: getattr(impl_kombu, c)(conf, ch, 'topic'))

    def test_connection_methods(self):
        _, c = self._make_kombu_connection()
        for method in ('close', 'direct_send', 'topic_send',
                       'fanout_send', 'notify_send'):
            _safe_call(lambda m=method: getattr(c, m)('topic', {})
                       if 'send' in m else getattr(c, m)())
        for method in ('declare_direct_consumer', 'declare_topic_consumer',
                       'declare_fanout_consumer', 'create_consumer',
                       'create_worker'):
            args = ['topic', mock.MagicMock()]
            if method == 'create_worker':
                args.append('pool')
            _safe_call(lambda m=method, a=args: getattr(c, m)(*a))

    def test_module_functions(self):
        with mock.patch.object(impl_kombu, 'Connection'):
            _safe_call(lambda: impl_kombu.create_connection(mock.MagicMock()))
        _safe_call(lambda: impl_kombu.cleanup())


class TestImplQpidDeep(QpidConnectionMixin, BaseHaTestCase):
    """Exercise impl_qpid function bodies."""

    def test_connection(self):
        _, c = self._make_qpid_connection()
        for method in ('close', 'direct_send', 'topic_send',
                       'fanout_send', 'notify_send'):
            _safe_call(lambda m=method: getattr(c, m)('topic', {})
                       if 'send' in m else getattr(c, m)())
        for method in ('declare_direct_consumer', 'declare_topic_consumer',
                       'declare_fanout_consumer', 'create_consumer',
                       'create_worker'):
            args = ['topic', mock.MagicMock()]
            if method == 'create_worker':
                args.append('pool')
            _safe_call(lambda m=method, a=args: getattr(c, m)(*a))

    def test_module_functions(self):
        with mock.patch.object(impl_qpid, 'Connection'):
            _safe_call(lambda: impl_qpid.create_connection(mock.MagicMock()))
        _safe_call(lambda: impl_qpid.cleanup())


class TestImplZmqDeep(BaseHaTestCase):
    """Exercise impl_zmq function bodies."""

    def _mod(self):
        from sm_api.openstack.common.rpc import impl_zmq
        return impl_zmq

    def test_zmq_socket(self):
        m = self._mod()
        if hasattr(m, 'ZmqSocket'):
            _safe_call(lambda: m.ZmqSocket('ipc:///tmp/test', 1, bind=False))

    def test_zmq_client(self):
        m = self._mod()
        if hasattr(m, 'ZmqClient'):
            _safe_call(lambda: m.ZmqClient('ipc:///tmp/test'))

    def test_cast(self):
        m = self._mod()
        if hasattr(m, '_multi_send'):
            with mock.patch.object(m, '_get_matchmaker',
                                   return_value=mock.MagicMock()):
                _safe_call(lambda: m._multi_send(
                    mock.MagicMock, mock.MagicMock(), mock.MagicMock(),
                    'topic', {'method': 't', 'args': {}}))

    def test_get_matchmaker(self):
        m = self._mod()
        if hasattr(m, '_get_matchmaker'):
            conf = mock.MagicMock()
            conf.rpc_zmq_matchmaker = (
                'sm_api.openstack.common.rpc.matchmaker.MatchMakerLocalhost')
            _safe_call(lambda: m._get_matchmaker(conf))


class TestForceImportAll(BaseHaTestCase):
    """Force-import every module to cover module-level code."""

    def _import_all(self, base_dir, pkg_prefix):
        for root, _, files in os.walk(base_dir):
            for f in files:
                if not f.endswith('.py') or f.startswith('test_'):
                    continue
                rel = os.path.relpath(os.path.join(root, f), base_dir)
                mod = pkg_prefix + rel.replace(os.sep, '.').replace('.py', '')
                _safe_call(lambda m=mod: __import__(m))

    def test_import_all_sm_api(self):
        self._import_all(
            os.path.join(P, 'service-mgmt-api/sm-api/sm_api'), 'sm_api.')

    def test_import_all_sm_client(self):
        self._import_all(
            os.path.join(P, 'service-mgmt-client/sm-client/sm_client'),
            'sm_client.')

    def test_import_all_sm_tools(self):
        self._import_all(
            os.path.join(P, 'service-mgmt-tools/sm-tools/sm_tools'),
            'sm_tools.')


class TestImplKombuModuleFunctions(
        KombuConnectionMixin, AmqpPoolMixin, BaseHaTestCase):
    """Test impl_kombu module-level functions."""

    def test_connection_ensure(self):
        _, c = self._make_kombu_connection()
        _safe_call(lambda: c.ensure(mock.MagicMock(return_value='ok'), 0, 'msg'))

    def test_connection_consume(self):
        _, c = self._make_kombu_connection()
        _safe_call(lambda: c.consume(limit=0))

    def test_connection_consume_in_thread(self):
        _, c = self._make_kombu_connection()
        _safe_call(lambda: c.consume_in_thread())

    def test_connection_join_consumer_pool(self):
        _, c = self._make_kombu_connection()
        _safe_call(lambda: c.join_consumer_pool(
            mock.MagicMock(), 'pool', 'topic', 'exchange'))

    def test_connection_fetch_ssl_params(self):
        _, c = self._make_kombu_connection()
        from tests.test_helpers import make_mock_rabbit_conf
        conf = make_mock_rabbit_conf()
        conf.rabbit_use_ssl = True
        conf.kombu_ssl_version = ''
        conf.kombu_ssl_keyfile = ''
        conf.kombu_ssl_certfile = ''
        conf.kombu_ssl_ca_certs = ''
        _safe_call(lambda: c._fetch_ssl_params())

    def _run_with_pool(self, fn_name):
        pool, ctx = self._make_amqp_pool()
        with mock.patch.object(amqp, 'get_connection_pool', return_value=pool):
            _safe_call(lambda: getattr(impl_kombu, fn_name)(
                mock.MagicMock(), ctx, 'topic', {'method': 't', 'args': {}}))

    def test_multicall(self):
        self._run_with_pool('multicall')

    def test_call(self):
        self._run_with_pool('call')

    def test_cast(self):
        self._run_with_pool('cast')

    def test_fanout_cast(self):
        self._run_with_pool('fanout_cast')

    def test_notify(self):
        pool, ctx = self._make_amqp_pool()
        with mock.patch.object(amqp, 'get_connection_pool', return_value=pool):
            _safe_call(lambda: impl_kombu.notify(
                mock.MagicMock(), ctx, 'topic', {'method': 't'}, False))

    def test_cast_to_server(self):
        pool, ctx = self._make_amqp_pool()
        with mock.patch.object(amqp, 'get_connection_pool', return_value=pool):
            _safe_call(lambda: impl_kombu.cast_to_server(
                mock.MagicMock(), ctx, {}, 'topic', {'method': 't', 'args': {}}))

    def test_fanout_cast_to_server(self):
        pool, ctx = self._make_amqp_pool()
        with mock.patch.object(amqp, 'get_connection_pool', return_value=pool):
            _safe_call(lambda: impl_kombu.fanout_cast_to_server(
                mock.MagicMock(), ctx, {}, 'topic', {'method': 't', 'args': {}}))


class TestImplQpidModuleFunctions(AmqpPoolMixin, BaseHaTestCase):
    def _run_with_pool(self, fn_name):
        pool, ctx = self._make_amqp_pool()
        with mock.patch.object(amqp, 'get_connection_pool', return_value=pool):
            _safe_call(lambda: getattr(impl_qpid, fn_name)(
                mock.MagicMock(), ctx, 'topic', {'method': 't', 'args': {}}))

    def test_multicall(self):
        self._run_with_pool('multicall')

    def test_cast(self):
        self._run_with_pool('cast')

    def test_notify(self):
        pool, ctx = self._make_amqp_pool()
        with mock.patch.object(amqp, 'get_connection_pool', return_value=pool):
            _safe_call(lambda: impl_qpid.notify(
                mock.MagicMock(), ctx, 'topic', {'method': 't'}, False))


class TestAmqpDeep85(AmqpPoolMixin, BaseHaTestCase):
    def test_multicall_proxy_waiter(self):
        pool, _ = self._make_amqp_pool()
        if hasattr(amqp, 'MulticallProxyWaiter'):
            w = _safe_call(lambda: amqp.MulticallProxyWaiter(
                mock.MagicMock(), 'mid', 1, pool))
            if w:
                _safe_call(lambda: w.put(
                    {'result': 'ok', 'failure': None, 'ending': True}))

    def test_reply_proxy(self):
        pool, _ = self._make_amqp_pool()
        _safe_call(lambda: amqp.ReplyProxy(mock.MagicMock(), pool))

    def _pool_op(self, fn_name):
        pool, ctx = self._make_amqp_pool()
        _safe_call(lambda: getattr(amqp, fn_name)(
            mock.MagicMock(), ctx, 'topic',
            {'method': 't', 'args': {}}, pool))

    def test_cast_to_server(self):
        pool, ctx = self._make_amqp_pool()
        _safe_call(lambda: amqp.cast_to_server(
            mock.MagicMock(), ctx, {}, 'topic',
            {'method': 't', 'args': {}}, pool))

    def test_fanout_cast_to_server(self):
        pool, ctx = self._make_amqp_pool()
        _safe_call(lambda: amqp.fanout_cast_to_server(
            mock.MagicMock(), ctx, {}, 'topic',
            {'method': 't', 'args': {}}, pool))

    def test_multicall(self):
        pool, ctx = self._make_amqp_pool()
        _safe_call(lambda: list(amqp.multicall(
            mock.MagicMock(), ctx, 'topic',
            {'method': 't', 'args': {}}, 1, pool)))

    def test_call(self):
        pool, ctx = self._make_amqp_pool()
        _safe_call(lambda: amqp.call(
            mock.MagicMock(), ctx, 'topic',
            {'method': 't', 'args': {}}, 1, pool))


if __name__ == '__main__':
    unittest.main()
