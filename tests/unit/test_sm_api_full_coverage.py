#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Full coverage tests for amqp pack/unpack and impl modules."""

from tests.base import BaseHaTestCase
from unittest import mock


class TestAmqpPackUnpack(BaseHaTestCase):
    """Test amqp pack/unpack context (canonical location)."""

    def test_pack_context(self):
        from sm_api.openstack.common.rpc import amqp
        ctx = mock.MagicMock()
        ctx.to_dict.return_value = {'user': 'u'}
        msg = {}
        amqp.pack_context(msg, ctx)
        self.assertIn('_context_user', msg)

    def test_unpack_context(self):
        from sm_api.openstack.common.rpc import amqp
        msg = {'_context_user': 'u', '_context_tenant': 't',
               '_msg_id': 'mid', '_reply_q': 'rq'}
        ctx = amqp.unpack_context(mock.MagicMock(), msg)
        self.assertEqual(ctx.user, 'u')


class TestImplModulesLoad(BaseHaTestCase):
    """Verify rpc impl modules are importable."""

    def test_impl_kombu_loads(self):
        from sm_api.openstack.common.rpc import impl_kombu
        self.assertTrue(hasattr(impl_kombu, 'Connection'))

    def test_impl_qpid_loads(self):
        from sm_api.openstack.common.rpc import impl_qpid
        self.assertTrue(hasattr(impl_qpid, 'Connection'))

    def test_impl_zmq_loads(self):
        from sm_api.openstack.common.rpc import impl_zmq
        self.assertIsNotNone(impl_zmq)


class TestCollectionController(BaseHaTestCase):
    """Test collection controller (unique to this file)."""

    def test_collection(self):
        from sm_api.api.controllers.v1 import collection
        self.assertTrue(hasattr(collection, 'Collection'))


if __name__ == '__main__':
    import unittest
    unittest.main()
