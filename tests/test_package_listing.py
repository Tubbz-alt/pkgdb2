# -*- coding: utf-8 -*-
#
# Copyright © 2013  Red Hat, Inc.
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
pkgdb tests for the Package object.
'''

__requires__ = ['SQLAlchemy >= 0.7']
import pkg_resources

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

from pkgdb.lib import model
from tests import Modeltests, create_package_listing


class PackageListingtests(Modeltests):
    """ PackageListing tests. """

    def test_init_package_listing(self):
        """ Test the __init__ function of PackageListing. """
        create_package_listing(self.session)
        pkg = model.Package.by_name(self.session, 'Guake')
        self.assertEqual(2, 
                         len(model.PackageListing.by_pkg_id(self.session,
                                                        pkg.id))
                         )

    def test_repr_package_listing(self):
        """ Test the __repr__ function of PackageListing. """
        create_package_listing(self.session)
        pkg = model.Package.by_name(self.session, 'Guake')
        packages = model.PackageListing.by_pkg_id(self.session,
                                                        pkg.id)
        self.assertEqual("PackageListing(10, u'Approved', packageid=1, "
                         "collectionid=1, qacontact=None)",
                         packages[0].__repr__())


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(PackageListingtests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)