#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for sm_api.objects.base and sm_api.db modules."""
import unittest

from tests.base import BaseHaTestCase

from sm_api.objects.base import get_attrname
from sm_api.objects.base import ObjectListBase
from sm_api.objects.base import Sm_apiObject
from sm_api.objects.base import Sm_apiObjectSerializer
from sm_api.objects.base import check_object_version
from sm_api.objects.base import obj_to_primitive
from sm_api.objects.base import remotable_classmethod
from sm_api.common.exception import IncompatibleObjectVersion
from sm_api.common.exception import UnsupportedObjectError


class TestObjectBase(BaseHaTestCase):
    def test_get_attrname(self):
        self.assertEqual(get_attrname('foo'), '_foo')

    def test_init(self):
        obj = Sm_apiObject()
        self.assertEqual(obj._changed_fields, set())
        self.assertIsNone(obj._context)

    def test_obj_name(self):
        self.assertEqual(Sm_apiObject.obj_name(), 'Sm_apiObject')

    def test_obj_what_changed(self):
        obj = Sm_apiObject()
        obj._changed_fields.add('test')
        self.assertIn('test', obj.obj_what_changed())

    def test_obj_reset_changes(self):
        obj = Sm_apiObject()
        obj._changed_fields = {'a', 'b', 'c'}
        obj.obj_reset_changes(fields=['a'])
        self.assertNotIn('a', obj._changed_fields)
        obj.obj_reset_changes()
        self.assertEqual(len(obj._changed_fields), 0)

    def test_obj_getsetitem(self):
        obj = Sm_apiObject()
        obj._test_attr = 'val'
        self.assertIn('test_attr', obj)

    def test_obj_get(self):
        obj = Sm_apiObject()
        obj._context = 'ctx'
        self.assertEqual(obj.get('_context'), 'ctx')

    def test_update(self):
        self.assertTrue(hasattr(Sm_apiObject(), 'update'))

    def test_as_dict(self):
        self.assertIsInstance(Sm_apiObject().as_dict(), dict)

    def test_get_defaults(self):
        class TestObjDef(Sm_apiObject):
            fields = {'name': str}
        self.assertIsInstance(TestObjDef.get_defaults(), dict)

    def test_obj_load_attr_raises(self):
        with self.assertRaises(NotImplementedError):
            Sm_apiObject().obj_load_attr('test')

    def test_save_raises(self):
        with self.assertRaises(NotImplementedError):
            Sm_apiObject().save(None)

    def test_check_object_version_ok(self):
        check_object_version('1.5', '1.3')

    def test_check_object_version_major_mismatch(self):
        with self.assertRaises(IncompatibleObjectVersion):
            check_object_version('2.0', '1.0')

    def test_check_object_version_minor_too_new(self):
        with self.assertRaises(IncompatibleObjectVersion):
            check_object_version('1.0', '1.5')

    def test_remotable_classmethod(self):
        class TestObj(Sm_apiObject):
            fields = {}

            @remotable_classmethod
            def get_test(cls, context):
                return 'result'

        self.assertEqual(TestObj.get_test(None), 'result')

    def test_obj_to_primitive(self):
        class TestObj(Sm_apiObject):
            fields = {'name': str}

        obj = TestObj()
        obj._name = 'test'
        obj._changed_fields = {'name'}
        p = obj.obj_to_primitive()
        self.assertEqual(p['sm_api_object.name'], 'TestObj')
        self.assertIn('name', p['sm_api_object.data'])

    def test_obj_from_primitive(self):
        class TestObj2(Sm_apiObject):
            fields = {'name': str}

        prim = {
            'sm_api_object.name': 'TestObj2',
            'sm_api_object.namespace': 'sm_api',
            'sm_api_object.version': '1.0',
            'sm_api_object.data': {'name': 'hello'},
            'sm_api_object.changes': ['name'],
        }
        obj = Sm_apiObject.obj_from_primitive(prim)
        self.assertEqual(obj._name, 'hello')

    def test_obj_from_primitive_bad_namespace(self):
        prim = {
            'sm_api_object.name': 'X',
            'sm_api_object.namespace': 'other',
            'sm_api_object.version': '1.0',
            'sm_api_object.data': {},
        }
        with self.assertRaises(UnsupportedObjectError):
            Sm_apiObject.obj_from_primitive(prim)


class TestObjectListBase(BaseHaTestCase):
    def test_list_operations(self):
        class MyList(ObjectListBase, Sm_apiObject):
            fields = {'objects': list}

        lst = MyList()
        lst._objects = ['a', 'b', 'c']
        self.assertEqual(len(lst), 3)
        self.assertIn('b', lst)
        self.assertEqual(lst.count('a'), 1)
        self.assertEqual(lst.index('c'), 2)


class TestObjToPrimitive(BaseHaTestCase):
    def test_plain_value(self):
        self.assertEqual(obj_to_primitive(42), 42)
        self.assertEqual(obj_to_primitive('str'), 'str')


class TestSerializer(BaseHaTestCase):
    def setUp(self):
        self.s = Sm_apiObjectSerializer()

    def test_serialize_entity_plain(self):
        self.assertEqual(self.s.serialize_entity(None, 42), 42)

    def test_deserialize_entity_plain(self):
        self.assertEqual(self.s.deserialize_entity(None, 42), 42)

    def test_serialize_list(self):
        self.assertEqual(self.s.serialize_entity(None, [1, 2, 3]), [1, 2, 3])

    def test_deserialize_list(self):
        self.assertEqual(self.s.deserialize_entity(None, [1, 2]), [1, 2])


if __name__ == '__main__':
    unittest.main()
