# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2011 OpenStack Foundation.
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


from six.moves import configparser
import logging
import logging.handlers
import os

from sm_api.openstack.common.rootwrap import filters


class NoFilterMatched(Exception):
    """This exception is raised when no filter matched."""
    pass


class FilterMatchNotExecutable(Exception):
    """
    This exception is raised when a filter matched but no executable was
    found.
    """

    def __init__(self, match=None, **kwargs):
        self.match = match


class RootwrapConfig(object):

    def __init__(self, config):
        # filters_path
        self.filters_path = config.get("DEFAULT", "filters_path").split(",")

        # exec_dirs
        if config.has_option("DEFAULT", "exec_dirs"):
            self.exec_dirs = config.get("DEFAULT", "exec_dirs").split(",")
        else:
            # Use system PATH if exec_dirs is not specified
            self.exec_dirs = os.environ["PATH"].split(':')

        # syslog_log_facility
        if config.has_option("DEFAULT", "syslog_log_facility"):
            v = config.get("DEFAULT", "syslog_log_facility")
            facility_names = logging.handlers.SysLogHandler.facility_names
            self.syslog_log_facility = getattr(logging.handlers.SysLogHandler,
                                               v, None)
            if self.syslog_log_facility is None and v in facility_names:
                self.syslog_log_facility = facility_names.get(v)
            if self.syslog_log_facility is None:
                raise ValueError('Unexpected syslog_log_facility: %s' % v)
        else:
            default_facility = logging.handlers.SysLogHandler.LOG_SYSLOG
            self.syslog_log_facility = default_facility

        # syslog_log_level
        if config.has_option("DEFAULT", "syslog_log_level"):
            v = config.get("DEFAULT", "syslog_log_level")
            self.syslog_log_level = logging.getLevelName(v.upper())
            if (self.syslog_log_level == "Level %s" % v.upper()):
                raise ValueError('Unexepected syslog_log_level: %s' % v)
        else:
            self.syslog_log_level = logging.ERROR

        # use_syslog
        if config.has_option("DEFAULT", "use_syslog"):
            self.use_syslog = config.getboolean("DEFAULT", "use_syslog")
        else:
            self.use_syslog = False


def setup_syslog(execname, facility, level):
    rootwrap_logger = logging.getLogger()
    rootwrap_logger.setLevel(level)
    handler = logging.handlers.SysLogHandler(address='/dev/log',
                                             facility=facility)
    handler.setFormatter(logging.Formatter(
                         os.path.basename(execname) + ': %(message)s'))
    rootwrap_logger.addHandler(handler)


def build_filter(class_name, *args):
    """Returns a filter object of class class_name."""
    if not hasattr(filters, class_name):
        logging.warning("Skipping unknown filter class (%s) specified "
                        "in filter definitions" % class_name)
        return None
    filterclass = getattr(filters, class_name)
    return filterclass(*args)


def load_filters(filters_path):
    """Load filters from a list of directories."""
    filterlist = []
    for filterdir in filters_path:
        if not os.path.isdir(filterdir):
            continue
        for filterfile in os.listdir(filterdir):
            filterconfig = configparser.RawConfigParser()
            filterconfig.read(os.path.join(filterdir, filterfile))
            for (name, value) in filterconfig.items("Filters"):
                filterdefinition = [str.strip(s) for s in value.split(',')]
                newfilter = build_filter(*filterdefinition)
                if newfilter is None:
                    continue
                newfilter.name = name
                filterlist.append(newfilter)
    return filterlist


def match_filter(filter_list, userargs, exec_dirs=None):
    """
    Checks user command and arguments through command filters and
    returns the first matching filter.
    Raises NoFilterMatched if no filter matched.
    Raises FilterMatchNotExecutable if no executable was found for the
    best filter match.
    """
    first_not_executable_filter = None
    if exec_dirs is None:
        exec_dirs = []

    for f in filter_list:
        if f.match(userargs):
            # Try other filters if executable is absent
            if not f.get_exec(exec_dirs=exec_dirs):
                if not first_not_executable_filter:
                    first_not_executable_filter = f
                continue
            # Otherwise return matching filter for execution
            return f

    if first_not_executable_filter:
        # A filter matched, but no executable was found for it
        raise FilterMatchNotExecutable(match=first_not_executable_filter)

    # No filter matched
    raise NoFilterMatched()
