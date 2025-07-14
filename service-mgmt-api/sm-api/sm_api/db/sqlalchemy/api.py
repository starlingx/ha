# vim: tabstop=4 shiftwidth=4 softtabstop=4
# -*- encoding: utf-8 -*-
#
# Copyright 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# Copyright (c) 2013-2018, 2025 Wind River Systems, Inc.
#


"""SQLAlchemy storage backend."""

import functools
import sys

import eventlet
from oslo_config import cfg

# TODO(deva): import MultipleResultsFound and handle it appropriately
from sqlalchemy.orm.exc import NoResultFound

from sm_api.common import exception
from sm_api.common import utils
from sm_api.db import api
from sm_api.db.sqlalchemy import models
from sm_api import objects
from sm_api.openstack.common.db.sqlalchemy import session as db_session
from sm_api.openstack.common.db.sqlalchemy import utils as db_utils
from sm_api.openstack.common import log
from sm_api.openstack.common import uuidutils

CONF = cfg.CONF
CONF.import_opt('connection',
                'sm_api.openstack.common.db.sqlalchemy.session',
                group='database')

LOG = log.getLogger(__name__)

get_engine = db_session.get_engine
get_session_manager = db_session.get_session_manager


def _paginate_query(model, limit=None, marker=None, sort_key=None,
                    sort_dir=None, query=None):
    if not query:
        query = model_query(model)
    sort_keys = ['id']
    if sort_key and sort_key not in sort_keys:
        sort_keys.insert(0, sort_key)
    query = db_utils.paginate_query(query, model, limit, sort_keys,
                                    marker=marker, sort_dir=sort_dir)
    return query.all()


def get_backend():
    """The backend is this module itself."""
    return Connection()


def db_session_cleanup(cls):
    """Class decorator that automatically adds session cleanup to all non-special methods."""

    def method_decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            _context = eventlet.greenthread.getcurrent()
            exc_info = (None, None, None)

            try:
                return method(self, *args, **kwargs)
            except Exception:
                exc_info = sys.exc_info()
                raise
            finally:
                if (
                    hasattr(_context, "_db_session_context") and
                    _context._db_session_context is not None
                ):
                    try:
                        _context._db_session_context.__exit__(*exc_info)
                    except Exception as e:
                        LOG.warning(f"Error closing database session: {e}")

                    # Clear the session
                    _context._db_session = None
                    _context._db_session_context = None

        return wrapper

    for attr_name in dir(cls):
        # Skip special methods
        if not attr_name.startswith("__"):
            attr = getattr(cls, attr_name)
            if callable(attr):
                setattr(cls, attr_name, method_decorator(attr))

    return cls


def model_query(model, *args, **kwargs):
    """Query helper for simpler session usage.

    If the session is already provided in the kwargs, use it. Otherwise,
    try to get it from thread context. If it's not there, create a new one.

    :param session: if present, the session to use
    """
    session = kwargs.get('session')
    if not session:
        _context = eventlet.greenthread.getcurrent()
        if hasattr(_context, '_db_session') and _context._db_session is not None:
            session = _context._db_session
        else:
            session_context = get_session_manager()
            session = session_context.__enter__()
            _context._db_session = session
            # Need to store the session context to call __exit__ method later
            _context._db_session_context = session_context

        query = session.query(model, *args)

    return session.query(model, *args)


def add_identity_filter(query, value, model, use_name=False):
    """Adds an identity filter to a query.

    Filters results by ID, if supplied value is a valid integer.
    Otherwise attempts to filter results by UUID.

    :param query: Initial query to add filter to.
    :param value: Value for filtering results by.
    :return: Modified query.
    """
    if utils.is_int_like(value) and hasattr(model, "id"):
        return query.filter_by(id=value)
    elif uuidutils.is_uuid_like(value) and hasattr(model, "uuid"):
        return query.filter_by(uuid=value)
    else:
        if use_name:
            return query.filter_by(name=value)
        else:
            # JKUNG raise exception
            return query.filter_by(hostname=value)


def add_filter_by_many_identities(query, model, values):
    """Adds an identity filter to a query for values list.

    Filters results by ID, if supplied values contain a valid integer.
    Otherwise attempts to filter results by UUID.

    :param query: Initial query to add filter to.
    :param model: Model for filter.
    :param values: Values for filtering results by.
    :return: tuple (Modified query, filter field name).
    """
    if not values:
        raise exception.InvalidIdentity(identity=values)
    value = values[0]
    if utils.is_int_like(value):
        return query.filter(getattr(model, 'id').in_(values)), 'id'
    elif uuidutils.is_uuid_like(value):
        return query.filter(getattr(model, 'uuid').in_(values)), 'uuid'
    else:
        raise exception.InvalidIdentity(identity=value)


@db_session_cleanup
class Connection(api.Connection):
    """SqlAlchemy connection."""

    def __init__(self):
        pass

    @objects.objectify(objects.service_groups)
    def iservicegroup_get(self, server):
        query = model_query(models.iservicegroup)
        query = add_identity_filter(
            query, server, models.iservicegroup, use_name=True)

        try:
            result = query.one()
        except NoResultFound:
            raise exception.ServerNotFound(server=server)

        return result

    @objects.objectify(objects.service_groups)
    def iservicegroup_get_list(self, limit=None, marker=None,
                               sort_key=None, sort_dir=None):
        return _paginate_query(models.iservicegroup, limit, marker,
                               sort_key, sort_dir)

    @objects.objectify(objects.service)
    def iservice_get(self, server):
        # server may be passed as a string. It may be uuid or Int.
        # server = int(server)
        query = model_query(models.service)
        query = add_identity_filter(
            query, server, models.service, use_name=True)

        try:
            result = query.one()
        except NoResultFound:
            raise exception.ServerNotFound(server=server)

        return result

    @objects.objectify(objects.service)
    def iservice_get_list(self, limit=None, marker=None,
                          sort_key=None, sort_dir=None):
        return _paginate_query(models.service, limit, marker,
                               sort_key, sort_dir)

    @objects.objectify(objects.service)
    def iservice_get_by_name(self, name):
        result = model_query(models.service, read_deleted="no").\
            filter_by(name=name)

        if not result:
            raise exception.NodeNotFound(node=name)

        return result

    @objects.objectify(objects.sm_sdm)
    def sm_sdm_get(self, server, service_group_name):
        query = model_query(models.sm_sdm)
        query = query.filter_by(name=server)
        query = query.filter_by(service_group_name=service_group_name)

        try:
            result = query.one()
        except NoResultFound:
            raise exception.ServerNotFound(server=server)

        return result

    @objects.objectify(objects.sm_sda)
    def sm_sda_get(self, server):
        query = model_query(models.sm_sda)
        query = add_identity_filter(
            query, server, models.sm_sda, use_name=True)

        try:
            result = query.one()
        except NoResultFound:
            raise exception.ServerNotFound(server=server)

        return result

    @objects.objectify(objects.sm_sda)
    def sm_sda_get_list(self, limit=None, marker=None, sort_key=None,
                        sort_dir=None):
        return _paginate_query(models.sm_sda, limit, marker,
                               sort_key, sort_dir)

    @objects.objectify(objects.sm_node)
    def sm_node_get_list(self, limit=None, marker=None,
                         sort_key=None, sort_dir=None):
        return _paginate_query(models.sm_node, limit, marker,
                               sort_key, sort_dir)

    @objects.objectify(objects.sm_node)
    def sm_node_get(self, server):
        query = model_query(models.sm_node)
        query = add_identity_filter(
            query, server, models.sm_node, use_name=True)

        try:
            result = query.one()
        except NoResultFound:
            raise exception.ServerNotFound(server=server)

        return result

    @objects.objectify(objects.sm_node)
    def sm_node_get_by_name(self, name):
        result = model_query(models.sm_node, read_deleted="no").\
            filter_by(name=name)

        if not result:
            raise exception.NodeNotFound(node=name)

        return result

    @objects.objectify(objects.service)
    def sm_service_get(self, server):
        # server may be passed as a string. It may be uuid or Int.
        # server = int(server)
        query = model_query(models.service)
        query = add_identity_filter(
            query, server, models.service, use_name=True)

        try:
            result = query.one()
        except NoResultFound:
            raise exception.ServerNotFound(server=server)

        return result

    @objects.objectify(objects.service)
    def sm_service_get_list(self, limit=None, marker=None,
                            sort_key=None, sort_dir=None):
        return _paginate_query(models.service, limit, marker,
                               sort_key, sort_dir)

    @objects.objectify(objects.service)
    def sm_service_get_by_name(self, name):
        result = model_query(models.service, read_deleted="no").\
            filter_by(name=name)

        if not result:
            raise exception.ServiceNotFound(service=name)

        return result

    @objects.objectify(objects.service_group_member)
    def sm_service_group_members_get_list(self, service_group_name):
        result = model_query(models.sm_service_group_member,
                             read_deleted="no").\
            filter_by(provisioned='yes').\
            filter_by(name=service_group_name)

        return result
