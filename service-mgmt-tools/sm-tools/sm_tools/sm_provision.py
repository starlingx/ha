#
# Copyright (c) 2015-2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import print_function

import os
import sys
import argparse
import sqlite3
from sm_tools.sm_api_msg_utils import provision_service
from sm_tools.sm_api_msg_utils import deprovision_service
from sm_tools.sm_api_msg_utils import provision_service_domain_interface
from sm_tools.sm_api_msg_utils import deprovision_service_domain_interface

database_name = "/var/lib/sm/sm.db"
runtime_db_name = "/var/run/sm/sm.db"


def update_db(db, sqls):
    database = sqlite3.connect(db)

    cursor = database.cursor()

    for sql in sqls:
        cursor.execute(sql)

    database.commit()
    database.close()


def main():
    file_name = os.path.basename(sys.argv[0])
    if "sm-provision" == file_name:
        provision_str = "yes"
    else:
        provision_str = "no"

    try:
        parser = argparse.ArgumentParser(description='SM Provision ')
        subparsers = parser.add_subparsers(help='types')

        # Domain
        sd = subparsers.add_parser('service-domain',
                                   help='Provision Service Domain')
        sd.set_defaults(which='service_domain')
        sd.add_argument('service_domain', help='service domain name')

        # Domain Member
        sd_member_parser = subparsers.add_parser('service-domain-member',
                                                 help='Provision Service '
                                                 'Domain Member')
        sd_member_parser.set_defaults(which='service_domain_member')
        sd_member_parser.add_argument('service_domain',
                                      help='service domain name')
        sd_member_parser.add_argument('service_group',
                                      help='service group name')

        # Domain Interface
        sd_member_parser = subparsers.add_parser('service-domain-interface',
                                                 help='Provision Service '
                                                 'Domain Interface')
        sd_member_parser.set_defaults(which='service_domain_interface')
        sd_member_parser.add_argument('service_domain',
                                      help='service domain name')
        sd_member_parser.add_argument('service_domain_interface',
                                      help='service domain interface name')
        sd_member_parser.add_argument("--apply",
                                      help="Apply the new configuration "
                                           "immediately",
                                      action="store_true")

        # Service-Group
        sg = subparsers.add_parser('service-group',
                                   help='Provision Service Group')
        sg.set_defaults(which='service_group')
        sg.add_argument('service_group', help='service group name')

        # Service-Group-Member
        sg_member_parser = subparsers.add_parser('service-group-member',
                                                 help='Provision Service Group '
                                                 'Member')
        sg_member_parser.set_defaults(which='service_group_member')
        sg_member_parser.add_argument('service_group',
                                      help='service group name')
        sg_member_parser.add_argument('service_group_member',
                                      help='service group member name')

        sg_member_parser.add_argument("--apply",
                                      help="Apply the new configuration "
                                           "immediately\n",
                                      action="store_true")
        # Service
        service_parser = subparsers.add_parser('service',
                                               help='Provision Service')
        service_parser.set_defaults(which='service')
        service_parser.add_argument('service', help='service name')

        args = parser.parse_args()

        if args.which == 'service_domain':
            database = sqlite3.connect(database_name)

            cursor = database.cursor()

            cursor.execute("UPDATE SERVICE_DOMAINS SET "
                           "PROVISIONED = '%s' WHERE NAME = '%s';"
                           % (provision_str, args.service_domain))

            database.commit()
            database.close()

        elif args.which == 'service_domain_member':
            database = sqlite3.connect(database_name)

            cursor = database.cursor()

            cursor.execute("UPDATE SERVICE_DOMAIN_MEMBERS SET "
                           "PROVISIONED = '%s' WHERE NAME = '%s' and "
                           "SERVICE_GROUP_NAME = '%s';"
                           % (provision_str, args.service_domain,
                              args.service_group))

            database.commit()
            database.close()

        elif args.which == 'service_domain_interface':
            sql_update = "UPDATE SERVICE_DOMAIN_INTERFACES SET " \
                         "PROVISIONED = '%s' WHERE SERVICE_DOMAIN = '%s' and " \
                         "SERVICE_DOMAIN_INTERFACE = '%s';" \
                         % (provision_str, args.service_domain,
                            args.service_domain_interface)
            sqls = [sql_update]
            update_db(database_name, sqls)

            if args.apply and os.path.isfile(runtime_db_name):
                # update runtime configuration
                update_db(runtime_db_name, sqls)

                # tell SM to apply changes
                if "yes" == provision_str:
                    provision_service_domain_interface(args.service_domain,
                                                       args.service_domain_interface)
                elif "no" == provision_str:
                    deprovision_service_domain_interface(args.service_domain,
                                                         args.service_domain_interface)

        elif args.which == 'service_group':
            database = sqlite3.connect(database_name)

            cursor = database.cursor()

            cursor.execute("UPDATE SERVICE_GROUPS SET "
                           "PROVISIONED = '%s' WHERE NAME = '%s';"
                           % (provision_str, args.service_group))

            database.commit()
            database.close()

        elif args.which == 'service_group_member':
            sql_update_sgm = "UPDATE SERVICE_GROUP_MEMBERS SET " \
                             "PROVISIONED = '%s' WHERE NAME = '%s' and " \
                             "SERVICE_NAME = '%s';" \
                             % (provision_str, args.service_group,
                                args.service_group_member)
            sql_update_svc = "UPDATE SERVICES SET " \
                             "PROVISIONED = '%s' WHERE NAME = '%s';" \
                             % (provision_str, args.service_group_member)

            sqls = [sql_update_sgm, sql_update_svc]
            update_db(database_name, sqls)

            if args.apply and os.path.isfile(runtime_db_name):
                # update runtime configuration
                update_db(runtime_db_name, sqls)

                # tell SM to apply changes
                if "yes" == provision_str:
                    provision_service(args.service_group_member,
                                      args.service_group)
                elif "no" == provision_str:
                    deprovision_service(args.service_group_member,
                                        args.service_group)

        elif args.which == 'service':
            print('%s service <service_name>\nhas been deprecated and '
                  'it is supported for backward compatibility.\n'
                  'Please use %s service-group-member <service_group> '
                  '<service_group_member>' % (file_name, file_name))

            database = sqlite3.connect(database_name)

            cursor = database.cursor()

            cursor.execute("UPDATE SERVICES SET "
                           "PROVISIONED = '%s' WHERE NAME = '%s';"
                           % (provision_str, args.service))

            database.commit()
            database.close()

        sys.exit(0)

    except KeyboardInterrupt:
        sys.exit()

    except Exception as e:
        print(e)
        sys.exit(-1)
