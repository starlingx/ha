# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Red Hat, Inc.
# All Rights Reserved.
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
# Copyright (c) 2013-2014 Wind River Systems, Inc.
#


"""
gettext for openstack-common modules.

Usual usage in an openstack.common module:

    from sm_api.openstack.common.gettextutils import _
"""

import gettext
import os

import six

_localedir = os.environ.get('sm_api'.upper() + '_LOCALEDIR')
_t = gettext.translation('sm_api', localedir=_localedir, fallback=True)


def _(msg):
    if six.PY2:
        return _t.ugettext(msg)
    if six.PY3:
        return _t.gettext(msg)


def install(domain):
    """Install a _() function using the given translation domain.

    Given a translation domain, install a _() function using gettext's
    install() function.

    The main difference from gettext.install() is that we allow
    overriding the default localedir (e.g. /usr/share/locale) using
    a translation-domain-specific environment variable (e.g.
    NOVA_LOCALEDIR).
    """
    if six.PY2:
        gettext.install(domain,
                        localedir=os.environ.get(domain.upper() + '_LOCALEDIR'),
                        unicode=True)
    if six.PY3:
        gettext.install(domain,
                        localedir=os.environ.get(domain.upper() + '_LOCALEDIR'))
