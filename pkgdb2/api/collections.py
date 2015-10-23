# -*- coding: utf-8 -*-
#
# Copyright © 2013-2014  Red Hat, Inc.
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
Collections
===========

API for collection management.
'''

import flask

import pkgdb2.lib as pkgdblib
from pkgdb2 import SESSION, forms, is_admin
from pkgdb2.api import API
from pkgdb2.lib import model


## Some of the object we use here have inherited methods which apparently
## pylint does not detect.
# pylint: disable=E1101


## Collection
@API.route('/collection/new/', methods=['POST'])
@API.route('/collection/new', methods=['POST'])
@is_admin
def api_collection_new():
    '''
    New collection
    --------------
    Create a new collection.

    ::

        /api/collection/new/

    Accepts POST queries only.

    :arg clt_name: String of the collection name to be created.
    :arg version: String of the version of the collection.
    :arg clt_status: String of the name of the user owner of the collection.
    :arg summary: A summary description of the collection.
    :arg description: A description of the collection.
    :arg branchname: The short name of the collection (ie: F-18).
    :arg dist_tag: The dist tag used by rpm for this collection (ie: .fc18).
    :arg kojiname: the name of the collection in koji.
    :kwarg allow_retire: a boolean specifying if the collection should allow
        retiring a package or not.
        Defaults to ``False``.

    Sample response:

    ::

        {
          "output": "ok",
          "messages": ["Collection F-20 created"]
        }

        {
          "output": "notok",
          "error": ["You are not allowed to create collections"]
        }

    '''
    httpcode = 200
    output = {}

    clt_status = pkgdblib.get_status(SESSION, 'clt_status')['clt_status']

    form = forms.AddCollectionForm(
        csrf_enabled=False,
        clt_status=clt_status,
    )
    if form.validate_on_submit():
        clt_name = form.clt_name.data
        clt_version = form.version.data
        clt_status = form.clt_status.data
        clt_branchname = form.branchname.data
        clt_disttag = form.dist_tag.data
        clt_koji_name = form.kojiname.data
        clt_allow_retire = form.allow_retire.data or False

        try:
            message = pkgdblib.add_collection(
                SESSION,
                clt_name=clt_name,
                clt_version=clt_version,
                clt_status=clt_status,
                clt_branchname=clt_branchname,
                clt_disttag=clt_disttag,
                clt_koji_name=clt_koji_name,
                clt_allow_retire=clt_allow_retire,
                user=flask.g.fas_user,
            )
            SESSION.commit()
            output['output'] = 'ok'
            output['messages'] = [message]
        # Apparently we're pretty tight on checks and looks like we cannot
        # raise this exception in a normal situation
        except pkgdblib.PkgdbException, err:  # pragma: no cover
            SESSION.rollback()
            output['output'] = 'notok'
            output['error'] = str(err)
            httpcode = 500
    else:
        output['output'] = 'notok'
        output['error'] = 'Invalid input submitted'
        if form.errors:
            detail = []
            for error in form.errors:
                detail.append('%s: %s' % (error,
                              '; '.join(form.errors[error])))
            output['error_detail'] = detail
        httpcode = 500

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout


@API.route('/collection/<collection>/status/', methods=['POST'])
@API.route('/collection/<collection>/status', methods=['POST'])
@is_admin
def api_collection_status(collection):
    '''
    Update collection status
    ------------------------
    Update the status of collection.

    ::

        /api/collection/<collection branchname>/status/

    Accepts POST query only.

    :arg branch: String of the collection branch name to change.
    :arg clt_status: String of the status to change the collection to

    Sample response:

    ::

        {
          "output": "ok",
          "messages": ["Collection updated to \"EOL\""]
        }

        {
          "output": "notok",
          "error": ["You are not allowed to edit collections"]
        }

    '''
    httpcode = 200
    output = {}

    clt_status = pkgdblib.get_status(SESSION, 'clt_status')['clt_status']

    form = forms.CollectionStatusForm(
        csrf_enabled=False,
        clt_status=clt_status,
    )
    if form.validate_on_submit():
        clt_branchname = form.branch.data
        clt_status = form.clt_status.data

        if collection == clt_branchname:
            try:
                message = pkgdblib.update_collection_status(
                    SESSION,
                    clt_branchname,
                    clt_status,
                    user=flask.g.fas_user
                )
                SESSION.commit()
                output['output'] = 'ok'
                output['messages'] = [message]
            except pkgdblib.PkgdbException, err:
                SESSION.rollback()
                output['output'] = 'notok'
                output['error'] = str(err)
                httpcode = 500
        else:
            output['output'] = 'notok'
            output['error'] = "You're trying to update the " \
                              "wrong collection"
            httpcode = 500
    else:
        output['output'] = 'notok'
        output['error'] = 'Invalid input submitted'
        if form.errors:
            detail = []
            for error in form.errors:
                detail.append('%s: %s' % (error,
                              '; '.join(form.errors[error])))
            output['error_detail'] = detail
        httpcode = 500

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout


@API.route('/collections/')
@API.route('/collections')
@API.route('/collections/<pattern>/')
@API.route('/collections/<pattern>')
def api_collection_list(pattern=None):
    '''
    List collections
    ----------------
    List the collections based on a pattern. If no pattern is provided, it
    will return all the collection.

    ::

        /api/collections/<pattern>/

        /api/collections/?pattern=<pattern>

    Accepts GET queries only.

    :arg pattern: a pattern to which the collection searched should match.
    :arg clt_status: restrict the search to one or more collection status.

    Sample response:

    ::

        /api/collections

        {
          "collections": [
            {
              "status": "Active",
              "branchname": "f20",
              "version": "20",
              "name": "Fedora"
            },
            {
              "status": "EOL",
              "branchname": "F-17",
              "version": "17",
              "name": "Fedora"
            },
                {
              "status": "Active",
              "branchname": "EL-6",
              "version": "6",
              "name": "Fedora EPEL"
            }
          ]
        }

    ::

        /api/collections?pattern=el*

        {
          "collections": [
            {
              "status": "EOL",
              "branchname": "EL-4",
              "version": "4",
              "name": "Fedora EPEL"
            },
            {
              "status": "Active",
              "branchname": "EL-5",
              "version": "5",
              "name": "Fedora EPEL"
            },
            {
              "status": "Active",
              "branchname": "EL-6",
              "version": "6",
              "name": "Fedora EPEL"
            }
          ]
        }
    '''
    httpcode = 200
    output = {}

    pattern = flask.request.args.get('pattern', None) or pattern
    status = flask.request.args.getlist('clt_status', None)
    if pattern:
        if status:
            collections = []
            for stat in status:
                collections.extend(pkgdblib.search_collection(
                    SESSION, pattern=pattern, status=stat)
                )
        else:
            collections = pkgdblib.search_collection(
                SESSION, pattern=pattern)
    else:
        collections = model.Collection.all(SESSION)
    output = {'collections':
              [collec.to_json() for collec in collections]
              }
    output['output'] = 'ok'

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout
