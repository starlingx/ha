#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2013 Hewlett-Packard Development Company, L.P.
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
# Copyright (c) 2013-2018 Wind River Systems, Inc.
#


"""The Service Management API."""

import logging
import os.path
import sys
import time
import socket


from oslo_config import cfg
from wsgiref import simple_server

from sm_api.api import app
from sm_api.common import service as sm_api_service
from sm_api.openstack.common import log

CONF = cfg.CONF

# Bounded retry parameters for resolving the API bind address before the
# WSGI server is started. Node configuration can take up to ~5 minutes to
# complete, during which the bind hostname (resolved via dnsmasq) may not be
# resolvable yet. ADDR_RESOLVE_MAX_RETRIES x ADDR_RESOLVE_RETRY_INTERVAL
# (60 x 5s = ~5 min) sets the total time waited before giving up.
ADDR_RESOLVE_RETRY_INTERVAL = 5
ADDR_RESOLVE_MAX_RETRIES = 60

# Throttle the "waiting" log so it is emitted once every N attempts instead
# of on every attempt. With a 5s interval, N=2 logs every 10s; set to 6 to
# log every 30s.
ADDR_RESOLVE_LOG_EVERY = 2

# Process name prefixed to the resolve/retry log lines. This startup path
# does not get the "sm-api" identifier that the normal log format supplies,
# so include it explicitly. Learned from the invoked program
# (/usr/bin/sm-api -> "sm-api") rather than hard-coded; falls back to
# "sm-api" if argv[0] is unavailable.
PROCESS_NAME = os.path.basename(sys.argv[0]) or "sm-api"


def resolve_bind_address(host, port, logger):
    """Resolve the API bind address, tolerating transient DNS failures.

    The configured host is often a hostname (e.g. "controller") resolved via
    dnsmasq. While node configuration is completing (which can take several
    minutes), dnsmasq may not be answering yet and socket.getaddrinfo()
    raises socket.gaierror. Retry up to ADDR_RESOLVE_MAX_RETRIES times at
    ADDR_RESOLVE_RETRY_INTERVAL second intervals, logging progress once every
    ADDR_RESOLVE_LOG_EVERY attempts. Returns the addrinfo list on success;
    re-raises the last socket.gaierror if resolution never succeeds.

    getaddrinfo() is used (rather than an external probe such as dig) so the
    readiness check exercises the same resolution path the bind will use:
    the OS resolver stack (nsswitch -> /etc/hosts and dnsmasq). A literal IP
    or 0.0.0.0 resolves immediately, so the wait is a no-op unless the bind
    address genuinely requires name resolution.
    """
    last_error = None
    for attempt in range(1, ADDR_RESOLVE_MAX_RETRIES + 1):
        try:
            return socket.getaddrinfo(host, port)
        except socket.gaierror as e:
            last_error = e
            is_last = attempt == ADDR_RESOLVE_MAX_RETRIES
            # Throttle: log the first attempt, every Nth attempt, and always
            # the final attempt. The "retry in" tail is omitted on the final
            # attempt since no further retry follows.
            if is_last or (attempt - 1) % ADDR_RESOLVE_LOG_EVERY == 0:
                msg = ("%(proc)s Unable to bind to '%(host)s' (attempt "
                       "%(attempt)s/%(max)s): (errno:%(errno)s). dns name "
                       "resolution may not be ready - check dnsmasq running "
                       "state" %
                       {'proc': PROCESS_NAME, 'host': host,
                        'attempt': attempt,
                        'max': ADDR_RESOLVE_MAX_RETRIES, 'errno': e.errno})
                if not is_last:
                    msg += " - retry in %ss" % ADDR_RESOLVE_RETRY_INTERVAL
                logger.warning(msg)
            if not is_last:
                time.sleep(ADDR_RESOLVE_RETRY_INTERVAL)

    raise last_error


def get_handler_cls():
    cls = simple_server.WSGIRequestHandler

    # old-style class doesn't support super
    class MyHandler(cls, object):
        def address_string(self):
            # In the future, we could provide a config option to allow reverse DNS lookup
            return self.client_address[0]

    return MyHandler


def get_ipv6_server_cls():
    cls = simple_server.WSGIServer

    class MyServerClassIPv6(cls, object):
        address_family = socket.AF_INET6

    return MyServerClassIPv6


def main():
    LOG = log.getLogger(__name__)
    LOG.info("Wait for sm to start...")
    # wait until sm start configuring before starting
    while not os.path.exists("/var/run/sm/sm.db"):
        time.sleep(5)

    sm_api_service.prepare_service(sys.argv)

    # Build and start the WSGI app
    host = CONF.sm_api_bind_ip or socket.gethostname()
    port = CONF.sm_api_port

    # Resolve the bind address, waiting for name resolution to become
    # available. The configured host is often a hostname (e.g. "controller")
    # resolved via dnsmasq, which may not be answering until node
    # configuration completes (up to ~5 min). resolve_bind_address() retries
    # on a bounded schedule instead of letting socket.gaierror crash the
    # process on startup.
    addrinfo_list = resolve_bind_address(host, port, LOG)
    addrinfo = addrinfo_list[0]
    socket_family = addrinfo[0]

    server_cls = simple_server.WSGIServer
    if socket.AF_INET6 == socket_family:
        server_cls = get_ipv6_server_cls()

    wsgi = simple_server.make_server(host, port,
                                     app.VersionSelectorApplication(),
                                     server_class=server_cls,
                                     handler_class=get_handler_cls())

    LOG.info("Serving on http://%(host)s:%(port)s" %
             {'host': host, 'port': port})
    LOG.info("Configuration:")
    CONF.log_opt_values(LOG, logging.INFO)

    try:
        wsgi.serve_forever()
    except KeyboardInterrupt:
        pass
