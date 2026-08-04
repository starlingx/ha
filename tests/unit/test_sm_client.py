#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

"""Unit tests for sm_client modules: exc, common.base, common.utils."""
# pylint: disable=protected-access,unused-argument
import os
import unittest
from unittest import mock

from tests.base import BaseHaTestCase

from sm_client import exc
from sm_client.common import base
from sm_client.common import utils as client_utils


class TestExcBaseException(BaseHaTestCase):
    """Tests for sm_client.exc.BaseException."""

    def test_with_message(self):
        self.assertEqual(str(exc.BaseException("test error")), "test error")

    def test_no_message(self):
        self.assertIsNotNone(str(exc.BaseException()))

    def test_command_error(self):
        err = exc.CommandError("bad command")
        self.assertIsInstance(err, exc.BaseException)
        self.assertEqual(str(err), "bad command")

    def test_invalid_endpoint(self):
        self.assertIsInstance(exc.InvalidEndpoint("bad"), exc.BaseException)

    def test_communication_error(self):
        self.assertIsInstance(exc.CommunicationError("t"), exc.BaseException)


class TestExcHTTPExceptions(BaseHaTestCase):
    """Tests for HTTP exception classes."""

    def test_http_exception_str(self):
        self.assertIn("something", str(exc.HTTPException("something")))
        self.assertIsNotNone(str(exc.HTTPException()))

    def test_http_multiple_choices(self):
        err = exc.HTTPMultipleChoices()
        self.assertEqual(err.code, 300)
        self.assertIn("300", str(err))

    def test_http_codes(self):
        codes = {
            'BadRequest': 400, 'Unauthorized': 401, 'Forbidden': 403,
            'NotFound': 404, 'Conflict': 409, 'OverLimit': 413,
            'HTTPInternalServerError': 500, 'HTTPNotImplemented': 501,
            'HTTPBadGateway': 502, 'ServiceUnavailable': 503,
        }
        for name, code in codes.items():
            self.assertEqual(getattr(exc, name).code, code)

    def test_http_subclasses(self):
        aliases = {
            'HTTPBadRequest': 400, 'HTTPUnauthorized': 401,
            'HTTPForbidden': 403, 'HTTPNotFound': 404,
            'HTTPConflict': 409, 'HTTPOverLimit': 413,
            'HTTPServiceUnavailable': 503,
        }
        for name, code in aliases.items():
            self.assertEqual(getattr(exc, name).code, code)


class TestExcFromResponse(BaseHaTestCase):
    """Tests for from_response function."""

    def test_known_code(self):
        resp = mock.MagicMock()
        resp.status = 404
        self.assertIsInstance(exc.from_response(resp, "nf"), exc.HTTPNotFound)

    def test_unknown_code(self):
        resp = mock.MagicMock()
        resp.status = 999
        self.assertIsInstance(exc.from_response(resp), exc.HTTPException)


class TestExcCodeMap(BaseHaTestCase):
    def test_code_map_populated(self):
        for code in (400, 404, 500):
            self.assertIn(code, exc._code_map)


class TestExcMiscExceptions(BaseHaTestCase):
    def test_misc_exception_classes(self):
        self.assertTrue(issubclass(exc.NoTokenLookupException, Exception))
        self.assertTrue(issubclass(exc.EndpointNotFound, Exception))
        self.assertTrue(
            issubclass(exc.AmbiguousAuthSystem, exc.ClientException))
        self.assertIs(exc.AmbigiousAuthSystem, exc.AmbiguousAuthSystem)
        self.assertTrue(issubclass(exc.InvalidAttribute, exc.ClientException))
        self.assertTrue(
            issubclass(exc.InvalidAttributeValue, exc.ClientException))


class TestBaseGetid(BaseHaTestCase):
    def test_with_id_attr(self):
        obj = mock.MagicMock()
        obj.id = "uuid-123"
        self.assertEqual(base.getid(obj), "uuid-123")

    def test_without_id_attr(self):
        self.assertEqual(base.getid("plain-string"), "plain-string")


class _FakeResource(base.Resource):
    """Fake resource for testing."""


class TestBaseManager(BaseHaTestCase):
    """Tests for Manager class."""

    def _make_mgr(self, json_return):
        api = mock.MagicMock()
        api.json_request.return_value = json_return
        mgr = base.Manager(api)
        mgr.resource_class = _FakeResource
        return mgr

    def test_init(self):
        api = mock.MagicMock()
        self.assertIs(base.Manager(api).api, api)

    def test_create(self):
        mgr = self._make_mgr((None, {'id': 1, 'name': 'test'}))
        result = mgr._create('/url', {'name': 'test'})
        self.assertIsInstance(result, _FakeResource)

    def test_list(self):
        mgr = self._make_mgr((None, [{'id': 1}, {'id': 2}]))
        self.assertEqual(len(mgr._list('/url')), 2)

    def test_list_with_response_key(self):
        mgr = self._make_mgr((None, {'items': [{'id': 1}]}))
        self.assertEqual(len(mgr._list('/url', response_key='items')), 1)

    def test_list_missing_key(self):
        mgr = self._make_mgr((None, {'other': []}))
        self.assertEqual(mgr._list('/url', response_key='items'), [])

    def test_delete(self):
        api = mock.MagicMock()
        base.Manager(api)._delete('/url')
        api.raw_request.assert_called_once_with('DELETE', '/url')

    def test_update(self):
        mgr = self._make_mgr((None, {'id': 1, 'name': 'updated'}))
        result = mgr._update('/url', {'name': 'u'})
        self.assertIsInstance(result, _FakeResource)

    def test_update_no_body(self):
        mgr = self._make_mgr((None, None))
        self.assertIsNone(mgr._update('/url', {}))


class TestBaseResource(BaseHaTestCase):
    """Tests for Resource class."""

    def _res(self, info, loaded=True):
        return base.Resource(mock.MagicMock(), info, loaded=loaded)

    def test_add_details(self):
        res = self._res({'id': 1, 'name': 'test'})
        self.assertEqual(res.id, 1)
        self.assertEqual(res.name, 'test')

    def test_repr(self):
        r = repr(self._res({'id': 1, 'name': 'test'}))
        self.assertIn('Resource', r)
        self.assertIn('id=1', r)

    def test_eq(self):
        self.assertEqual(self._res({'id': 1}), self._res({'id': 1}))

    def test_neq_different_class(self):
        self.assertNotEqual(self._res({'id': 1}), "not a resource")

    def test_is_loaded(self):
        r = self._res({'id': 1}, loaded=False)
        self.assertFalse(r.is_loaded())
        r.set_loaded(True)
        self.assertTrue(r.is_loaded())

    def test_to_dict(self):
        info = {'id': 1, 'name': 'test'}
        res = self._res(info)
        d = res.to_dict()
        self.assertEqual(d, info)
        d['id'] = 999
        self.assertEqual(res._info['id'], 1)


class TestClientUtilsStringToBool(BaseHaTestCase):
    def test_true_values(self):
        for val in ('t', 'True', 'yes', '1', ' YES '):
            self.assertTrue(client_utils.string_to_bool(val), msg=val)

    def test_false_values(self):
        for val in ('f', 'False', 'no', '0', 'random'):
            self.assertFalse(client_utils.string_to_bool(val), msg=val)


class TestClientUtilsEnv(BaseHaTestCase):
    def test_returns_set_var(self):
        os.environ['_TEST_HA_VAR'] = 'hello'
        try:
            self.assertEqual(client_utils.env('_TEST_HA_VAR'), 'hello')
        finally:
            del os.environ['_TEST_HA_VAR']

    def test_returns_default(self):
        self.assertEqual(
            client_utils.env('_NONEXISTENT_12345', default='fb'), 'fb')

    def test_multiple_vars(self):
        os.environ['_TEST_HA_B'] = 'found'
        try:
            self.assertEqual(
                client_utils.env('_TEST_HA_A', '_TEST_HA_B', default='no'),
                'found')
        finally:
            del os.environ['_TEST_HA_B']


class TestClientUtilsImportVersionedModule(BaseHaTestCase):
    def test_import_v1_client(self):
        mod = client_utils.import_versioned_module(1, 'client')
        self.assertTrue(hasattr(mod, 'Client'))


class TestClientUtilsArgsArrayToDict(BaseHaTestCase):
    def test_converts(self):
        kwargs = {'params': ['key1=val1', 'key2=val2']}
        result = client_utils.args_array_to_dict(kwargs, 'params')
        self.assertEqual(result['params'], {'key1': 'val1', 'key2': 'val2'})

    def test_invalid_format_raises(self):
        with self.assertRaises(exc.CommandError):
            client_utils.args_array_to_dict({'params': ['noeq']}, 'params')

    def test_missing_key_noop(self):
        kwargs = {'other': 'val'}
        self.assertEqual(client_utils.args_array_to_dict(kwargs, 'p'), kwargs)


class TestClientUtilsArgsArrayToPatch(BaseHaTestCase):
    def test_add(self):
        p = client_utils.args_array_to_patch('add', ['name=test'])
        self.assertEqual(p[0], {'op': 'add', 'path': '/name', 'value': 'test'})

    def test_replace(self):
        p = client_utils.args_array_to_patch('replace', ['/name=new'])
        self.assertEqual(p[0]['op'], 'replace')

    def test_remove(self):
        p = client_utils.args_array_to_patch('remove', ['/name'])
        self.assertEqual(p[0]['op'], 'remove')
        self.assertNotIn('value', p[0])

    def test_unknown_op_raises(self):
        with self.assertRaises(exc.CommandError):
            client_utils.args_array_to_patch('unknown', ['/name'])

    def test_add_missing_value_raises(self):
        with self.assertRaises(exc.CommandError):
            client_utils.args_array_to_patch('add', ['/name'])


class TestClientUtilsPrettyChoiceList(BaseHaTestCase):
    def test_formats(self):
        self.assertEqual(
            client_utils.pretty_choice_list(['a', 'b', 'c']),
            "'a', 'b', 'c'")


class TestClientUtilsFindResource(BaseHaTestCase):
    def test_find_by_integer_id(self):
        mgr = mock.MagicMock()
        mgr.get.return_value = 'found'
        self.assertEqual(client_utils.find_resource(mgr, '123'), 'found')
        mgr.get.assert_called_with(123)

    def test_find_by_uuid(self):
        mgr = mock.MagicMock()
        mgr.get.return_value = 'found'
        self.assertEqual(
            client_utils.find_resource(
                mgr, '12345678-1234-5678-1234-567812345678'), 'found')

    def test_find_by_name(self):
        mgr = mock.MagicMock()
        mgr.resource_class.__name__ = 'Service'
        mgr.get.side_effect = exc.NotFound()
        mgr.find.return_value = 'found-by-name'
        self.assertEqual(
            client_utils.find_resource(mgr, 'my-svc'), 'found-by-name')

    def test_not_found_raises(self):
        mgr = mock.MagicMock()
        mgr.resource_class.__name__ = 'Service'
        mgr.get.side_effect = exc.NotFound()
        mgr.find.side_effect = exc.NotFound()
        with self.assertRaises(exc.CommandError):
            client_utils.find_resource(mgr, 'nonexistent')


if __name__ == '__main__':
    unittest.main()
