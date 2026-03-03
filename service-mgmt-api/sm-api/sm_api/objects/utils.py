#    Copyright 2013 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# Copyright (c) 2013-2014,2026 Wind River Systems, Inc.
#


"""Utility methods for objects"""

import ast
import datetime
import iso8601
import netaddr
import six

from functools import lru_cache
from sm_api.common import constants
from sm_api.openstack.common import timeutils


@lru_cache(maxsize=None)
def get_debian_codename():
    """Returns the Debian codename, e.g., 'bullseye', 'trixie'."""
    try:
        with open(constants.OS_RELEASE_FILE) as f:
            for line in f:
                if line.startswith("VERSION_CODENAME="):
                    return line.strip().split("=")[1]
    except FileNotFoundError:
        return None
    return None


def is_debian_bullseye():
    """Returns True if the current OS is Debian Bullseye."""
    return get_debian_codename() == constants.OS_DEBIAN_BULLSEYE


def datetime_or_none(dt):
    """Validate a datetime or None value."""
    if dt is None:
        return None
    elif isinstance(dt, datetime.datetime):
        if dt.utcoffset() is None:
            # NOTE(danms): Legacy objects from sqlalchemy are stored in UTC,
            # but are returned without a timezone attached.
            # As a transitional aid, assume a tz-naive object is in UTC.
            return dt.replace(tzinfo=iso8601.iso8601.Utc())
        else:
            return dt
    raise ValueError('A datetime.datetime is required here')


def datetime_or_str_or_none(val):
    if isinstance(val, six.string_types):
        return timeutils.parse_isotime(val)
    return datetime_or_none(val)


def int_or_none(val):
    """Attempt to parse an integer value, or None."""
    if val is None:
        return val
    else:
        return int(val)


def int_or_zero(val):
    """Attempt to parse an integer value, if None return zero."""
    if val is None:
        return int(0)
    else:
        return int(val)


def str_or_none(val):
    """Attempt to stringify a value, or None."""
    if val is None:
        return val
    else:
        return str(val)


def dict_or_none(val):
    """Attempt to dictify a value, or None."""
    if val is None:
        return {}
    elif isinstance(val, str):
        return dict(ast.literal_eval(val))
    else:
        try:
            return dict(val)
        except ValueError:
            return {}


def ip_or_none(version):
    """Return a version-specific IP address validator."""
    def validator(val, version=version):
        if val is None:
            return val
        else:
            return netaddr.IPAddress(val, version=version)
    return validator


def nested_object_or_none(objclass):
    def validator(val, objclass=objclass):
        if val is None or isinstance(val, objclass):
            return val
        raise ValueError('An object of class %s is required here' % objclass)
    return validator


_ISO8601_TIME_FORMAT_SUBSECOND = '%Y-%m-%dT%H:%M:%S.%f'
_ISO8601_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'


def isotime(at=None, subsecond=False):
    """Stringify time in ISO 8601 format."""
    if not at:
        at = timeutils.utcnow()
    st = at.strftime(_ISO8601_TIME_FORMAT
                     if not subsecond
                     else _ISO8601_TIME_FORMAT_SUBSECOND)
    tz = at.tzinfo.tzname(None) if at.tzinfo else 'UTC'
    st += ('Z' if (tz == 'UTC' or tz == 'UTC+00:00') else tz)
    return st


def dt_serializer(name):
    """Return a datetime serializer for a named attribute."""

    def serializer(self, name=name):
        value = getattr(self, name)
        if value is None:
            return None

        if is_debian_bullseye():
            return timeutils.isotime(value)
        return isotime(at=value, subsecond=True)

    return serializer


def dt_deserializer(instance, val):
    """A deserializer method for datetime attributes."""
    if val is None:
        return None
    else:
        return timeutils.parse_isotime(val)


def obj_serializer(name):
    def serializer(self, name=name):
        if getattr(self, name) is not None:
            return getattr(self, name).obj_to_primitive()
        else:
            return None
    return serializer
