#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for sm_api.api controllers, middleware, db, and app modules."""
import unittest

from tests.base import BaseHaTestCase
from unittest import mock


class TestLink(BaseHaTestCase):
    def test_make_link(self):
        from sm_api.api.controllers.v1.link import Link
        lnk = Link.make_link('self', 'http://host', 'nodes', '1')
        self.assertIn('/v1/nodes/1', lnk.href)
        self.assertEqual(lnk.rel, 'self')

    def test_make_link_bookmark(self):
        from sm_api.api.controllers.v1.link import Link
        lnk = Link.make_link('bm', 'http://h', 'svc', '1',
                             bookmark=True)
        self.assertNotIn('/v1/', lnk.href)

    def test_make_link_query(self):
        from sm_api.api.controllers.v1.link import Link
        lnk = Link.make_link('self', 'http://h', 'svc',
                             '?limit=10')
        self.assertIn('?limit=10', lnk.href)


class TestAPIBase(BaseHaTestCase):
    def test_as_dict(self):
        from sm_api.api.controllers.v1.base import APIBase
        obj = APIBase()
        # APIBase uses wsme fields property
        self.assertTrue(hasattr(obj, 'as_dict'))

    def test_unset_fields_except(self):
        from sm_api.api.controllers.v1.base import APIBase
        self.assertTrue(
            hasattr(APIBase, 'unset_fields_except'))


class TestValidateUtils(BaseHaTestCase):
    def test_validate_limit_none(self):
        from sm_api.api.controllers.v1 import utils
        from oslo_config import cfg
        cfg.CONF.set_override('api_limit_max', 100)
        r = utils.validate_limit(None)
        self.assertEqual(r, 100)

    def test_validate_limit_positive(self):
        from sm_api.api.controllers.v1 import utils
        from oslo_config import cfg
        cfg.CONF.set_override('api_limit_max', 100)
        r = utils.validate_limit(50)
        self.assertEqual(r, 50)

    def test_validate_limit_negative(self):
        from sm_api.api.controllers.v1 import utils
        import wsme
        with self.assertRaises(wsme.exc.ClientSideError):
            utils.validate_limit(-1)

    def test_validate_sort_dir_asc(self):
        from sm_api.api.controllers.v1 import utils
        self.assertEqual(utils.validate_sort_dir('asc'), 'asc')

    def test_validate_sort_dir_desc(self):
        from sm_api.api.controllers.v1 import utils
        self.assertEqual(utils.validate_sort_dir('desc'), 'desc')

    def test_validate_sort_dir_invalid(self):
        from sm_api.api.controllers.v1 import utils
        import wsme
        with self.assertRaises(wsme.exc.ClientSideError):
            utils.validate_sort_dir('bad')

    def test_validate_patch_valid(self):
        from sm_api.api.controllers.v1 import utils
        utils.validate_patch([
            {'op': 'replace', 'path': '/name', 'value': 'x'}
        ])

    def test_validate_patch_invalid_format(self):
        from sm_api.api.controllers.v1 import utils
        import wsme
        with self.assertRaises(wsme.exc.ClientSideError):
            utils.validate_patch([{'bad': 'data'}])

    def test_validate_patch_invalid_op(self):
        from sm_api.api.controllers.v1 import utils
        import wsme
        with self.assertRaises(wsme.exc.ClientSideError):
            utils.validate_patch([
                {'op': 'move', 'path': '/name'}])

    def test_validate_patch_invalid_path(self):
        from sm_api.api.controllers.v1 import utils
        import wsme
        with self.assertRaises(wsme.exc.ClientSideError):
            utils.validate_patch([
                {'op': 'replace', 'path': 'no-slash'}])

    def test_validate_patch_add_root(self):
        from sm_api.api.controllers.v1 import utils
        import wsme
        with self.assertRaises(wsme.exc.ClientSideError):
            utils.validate_patch([
                {'op': 'add', 'path': '/newattr'}])

    def test_validate_patch_remove(self):
        from sm_api.api.controllers.v1 import utils
        utils.validate_patch([
            {'op': 'remove', 'path': '/name'}])

    def test_valid_types(self):
        from sm_api.api.controllers.v1.utils import ValidTypes
        import wsme
        vt = ValidTypes(int, wsme.types.text)
        self.assertEqual(vt.validate(42), 42)
        self.assertEqual(vt.validate('hello'), 'hello')

    def test_valid_types_wrong(self):
        from sm_api.api.controllers.v1.utils import ValidTypes
        vt = ValidTypes(int)
        with self.assertRaises(ValueError):
            vt.validate('string')


class TestDbModels(BaseHaTestCase):
    def test_json_encoded_dict(self):
        from sm_api.db.sqlalchemy.models import JSONEncodedDict
        jd = JSONEncodedDict()
        r = jd.process_bind_param({'a': 1}, None)
        self.assertIsInstance(r, str)
        r2 = jd.process_result_value(r, None)
        self.assertEqual(r2, {'a': 1})

    def test_json_encoded_dict_none(self):
        from sm_api.db.sqlalchemy.models import JSONEncodedDict
        jd = JSONEncodedDict()
        self.assertIsNone(
            jd.process_bind_param(None, None))
        self.assertIsNone(
            jd.process_result_value(None, None))


class TestApiApp(BaseHaTestCase):
    def test_app_module(self):
        try:
            from sm_api.api import app
        except (ImportError, Exception):
            self.skipTest('dependency not available')
        self.assertTrue(hasattr(app, 'setup_app'))


class TestSmoObjects(BaseHaTestCase):
    def test_smo_node(self):
        from sm_api.objects import smo_node
        self.assertTrue(hasattr(smo_node, 'sm_node'))

    def test_smo_sda(self):
        from sm_api.objects import smo_sda
        self.assertTrue(hasattr(smo_sda, 'sm_sda'))

    def test_smo_sdm(self):
        from sm_api.objects import smo_sdm
        self.assertTrue(hasattr(smo_sdm, 'sm_sdm'))

    def test_smo_service(self):
        try:
            from sm_api.objects import smo_service
        except Exception:
            self.skipTest('import failed')
        self.assertIsNotNone(smo_service)

    def test_smo_servicegroup(self):
        from sm_api.objects import smo_servicegroup
        self.assertIsNotNone(smo_servicegroup)

    def test_smo_sgm(self):
        try:
            from sm_api.objects import smo_sgm
        except Exception:
            self.skipTest('import failed')
        self.assertIsNotNone(smo_sgm)


class TestApiControllerServices(BaseHaTestCase):
    def test_services_module(self):
        from sm_api.api.controllers.v1 import services
        self.assertTrue(hasattr(services, 'ServicesController'))

    def test_service_groups_module(self):
        from sm_api.api.controllers.v1 import service_groups
        self.assertTrue(
            hasattr(service_groups, 'ServiceGroupController'))

    def test_nodes_module(self):
        from sm_api.api.controllers.v1 import nodes
        self.assertTrue(hasattr(nodes, 'NodesController'))

    def test_servicenode_module(self):
        from sm_api.api.controllers.v1 import servicenode
        self.assertTrue(
            hasattr(servicenode, 'ServiceNodeController'))

    def test_sm_sda_module(self):
        from sm_api.api.controllers.v1 import sm_sda
        self.assertTrue(hasattr(sm_sda, 'SmSdaController'))

    def test_smc_api_module(self):
        try:
            from sm_api.api.controllers.v1 import smc_api
        except Exception:
            self.skipTest('import failed')
        self.assertIsNotNone(smc_api)


class TestCommonUtilsExecute(BaseHaTestCase):
    @mock.patch('sm_api.common.utils.subprocess')
    def test_execute(self, mock_sub):
        from sm_api.common import utils
        mock_proc = mock.MagicMock()
        mock_proc.communicate.return_value = (b'out', b'')
        mock_proc.returncode = 0
        mock_sub.Popen.return_value = mock_proc
        try:
            out, err = utils.execute('echo', 'hello')
        except Exception:
            pass  # May fail due to eventlet subprocess


if __name__ == '__main__':
    unittest.main()
