#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2014  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions
# of the GNU General Public License v.2, or (at your option) any later
# version.  This program is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY expressed or implied, including the
# implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.  You
# should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Any Red Hat trademarks that are incorporated in the source
# code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission
# of Red Hat, Inc.
#

'''
Script to run to branch packages from the `devel` collection into the new,
specified collection.
'''

## These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources

import argparse
import os

from sqlalchemy.exc import SQLAlchemyError


if 'PKGDB2_CONFIG' not in os.environ \
        and os.path.exists('/etc/pkgdb2/pkgdb2.cfg'):
    print 'Using configuration file `/etc/pkgdb2/pkgdb2.cfg`'
    os.environ['PKGDB2_CONFIG'] = '/etc/pkgdb2/pkgdb2.cfg'


try:
    import pkgdb2
except ImportError:
    import sys
    sys.path.insert(
        0, os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
    import pkgdb2

import pkgdb2.lib
import pkgdb2.lib.notifications as notify


class FakeFasUser(object):
    ''' Fake FAS user sent to pkgdb2 to behave as if we had logged in
    normally.
    We can do that since we are running directly from the host and thus
    calling directly the internal method.
    '''

    def __init__(self, username, groups=[]):
        ''' Instantiate a FakeFasUser object.

        :arg username: the username of the user in FAS.
        :type username: str
        :kwarg groups: the FAS groups in which the user is.
        :type groups: list

        '''

        self.username = username
        self.groups = []
        if groups:
            self.groups = groups
        self.cla_done = True


def get_arguments():
    ''' Set the command line parser and retrieve the arguments provided
    by the command line.
    '''
    parser = argparse.ArgumentParser(
        description='pkgdb2_branch')
    parser.add_argument(
        'new_branch',
        help='Name of the new collection in which to branch `master`')
    parser.add_argument(
        '--user', dest='user', nargs='+',
        help='FAS username of the user performing the action')
    parser.add_argument(
        '--groups', dest='groups', action='append',
        help='FAS groups in which the user performing the action is')
    parser.add_argument(
        '--nomail', dest='nomail', action='store_true', default=False,
        help='Print the repo instead of sending it by email')
    parser.add_argument(
        '--nocreate', dest='nocreate', action='store_true', default=False,
        help='Do not update rawhide nor create the new collection in the db')

    return parser.parse_args()


def main():
    ''' Retrieve all the package associated to the collection `devel` and
    branch them into the specified collection.

    :arg collection_name: the name of the collection in which to branch the
        ACL of the packages present in `master`.

    '''
    # Retrieve arguments
    args = get_arguments()

    user = FakeFasUser(username=args.user, groups=args.groups)
    collection = pkgdb2.lib.search_collection(
            pkgdb2.SESSION,
            'master',
        )

    if not args.nocreate and collection:
        collection = collection[0]
        print "Updating rawhide's dist-tag"
        dist_tag = collection.dist_tag
        version = dist_tag.replace('.fc', '')
        error = False
        try:
            version = int(version) + 1
        except:
            error = True
            pass

        if error:
            version = raw_input('Enter the new version to create: ').strip()
            version = int(version) + 1

        answer = raw_input(
            'New dist-tag: `.fc%s` [Y/n]: ' % (version))
        if answer.strip().lower() in ['y', '']:
            new_dist_tag = '.fc%s' % (version)
        else:
            new_dist_tag = raw_input(
                'Enter the new dist-tag for rawhide '
                '(current dist-tag: %s): ' % dist_tag).strip()
        collection.dist_tag = new_dist_tag
        pkgdb2.SESSION.add(collection)
        pkgdb2.SESSION.commit()

        # new collection
        version = args.new_branch
        version = version.replace('f', '')
        version = int(version)
        print "Create the new collection"
        print "  name:          %s" % collection.name
        print "  version:       %s" % version
        print "  status:        %s" % collection.status
        print "  branchname:    f%s" % version
        print "  disttag:       .fc%s" % version
        print "  koji:          f%s" % version
        print "  allow_retire:  True"
        answer = raw_input('Save this new collection? [Y/n]: ')
        if answer.lower() in ['', 'y']:
            pkgdb2.lib.add_collection(
                pkgdb2.SESSION,
                clt_name=collection.name,
                clt_version=version,
                clt_status=collection.status,
                clt_branchname='f%s' % version,
                clt_disttag='.fc%s' % version,
                clt_koji_name='f%s' % version,
                clt_allow_retire=True,
                user=user,
            )
            pkgdb2.SESSION.commit()

    print "Branching for %s..." % args.new_branch
    try:
        pkgdblist = pkgdb2.lib.add_branch(
            pkgdb2.SESSION,
            clt_from='master',
            clt_to=args.new_branch,
            user=user,
        )
    except pkgdb2.lib.PkgdbException, err:
        print err
        return 1

    try:
        pkgdb2.SESSION.commit()
    except SQLAlchemyError. err:
        print err
        return 1

    message = 'Nothing happened'
    if pkgdblist:
        message = 'Output from the branching:\n\n%s' % ('\n'.join(pkgdblist))

    if args.nomail:
        print message
    else:
        to_email = pkgdb2.APP.config.get('MAIL_ADMIN')
        print 'Sending report by email to: %s' % to_email
        notify.email_publish(
            user=user,
            package=None,
            message=message,
            subject='Report: branching to %s' % args.new_branch,
            to_email=to_email,
        )

    return 0


if __name__ == '__main__':
    main()
