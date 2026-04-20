#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Base test class for ha project tests."""
import os
import sys
import unittest
from unittest import mock

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))

# Ensure sub-packages are importable
for _sub in (
    'service-mgmt-tools/sm-tools',
    'service-mgmt-client/sm-client',
    'service-mgmt-api/sm-api',
):
    _path = os.path.join(PROJECT_ROOT, _sub)
    if _path not in sys.path:
        sys.path.insert(0, _path)


class BaseHaTestCase(unittest.TestCase):
    """Base test class with common setup.

    Provides project path setup and shared
    imports for all ha test classes.
    """

    project_root = PROJECT_ROOT

    @classmethod
    def setUpClass(cls):
        """Set up class-level test fixtures."""
        super().setUpClass()

    def import_or_skip(self, module_path):
        """Import module or skip test if unavailable.

        :param module_path: dotted module path
        :returns: imported module
        """
        try:
            return __import__(
                module_path, fromlist=[''])
        except (ImportError, Exception):
            self.skipTest(
                f'{module_path} not importable')


class KombuConnectionMixin:
    """Mixin providing kombu connection factory."""

    def _make_kombu_connection(self):
        """Create mocked kombu connection.

        :returns: tuple of (module, connection)
        """
        from tests.test_helpers import make_mock_rabbit_conf
        from sm_api.openstack.common.rpc import impl_kombu
        conf = make_mock_rabbit_conf()
        with mock.patch.object(
                impl_kombu.Connection, 'reconnect'):
            c = impl_kombu.Connection(conf)
        c.connection = mock.MagicMock()
        c.channel = mock.MagicMock()
        c.producer = mock.MagicMock()
        c.consumers = []
        c.memory_transport = False
        c.consumer_num = __import__(
            'itertools').count(1)
        return impl_kombu, c


class QpidConnectionMixin:
    """Mixin providing qpid connection factory."""

    def _make_qpid_connection(self):
        """Create mocked qpid connection.

        :returns: tuple of (module, connection)
        """
        from tests.test_helpers import make_mock_qpid_conf
        from sm_api.openstack.common.rpc import impl_qpid
        conf = make_mock_qpid_conf()
        with mock.patch.object(
                impl_qpid.Connection, 'reconnect'):
            c = impl_qpid.Connection(conf)
        c.connection = mock.MagicMock()
        c.session = mock.MagicMock()
        c.consumers = {}
        c.consumer_thread = None
        return impl_qpid, c


class AmqpPoolMixin:
    """Mixin providing amqp pool mock factory."""

    def _make_amqp_pool(self):
        """Create mocked amqp pool and context.

        :returns: tuple of (pool, ctx)
        """
        pool = mock.MagicMock()
        conn = mock.MagicMock()
        pool.get.return_value = conn
        pool.connection_cls = mock.MagicMock()
        ctx = mock.MagicMock()
        ctx.to_dict.return_value = {}
        return pool, ctx


class SmToolsDbMixin:
    """Mixin providing sm_tools DB setup."""

    def _setup_sm_db(self):
        """Create temp SM database.

        :returns: str path to database
        """
        from tests.test_helpers import make_sm_db
        return make_sm_db()
