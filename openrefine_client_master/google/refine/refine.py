#!/usr/bin/env python
"""
Client library to communicate with a OpenRefine server.
"""

# Copyright (c) 2011 Paul Makepeace, Real Programmers. All rights reserved.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import csv
import json
import gzip
import os
import re
import StringIO
import time
import urllib
import urllib2_file
import urllib2
import urlparse

import facet
import history

REFINE_HOST = os.environ.get('OPENREFINE_HOST', os.environ.get('GOOGLE_REFINE_HOST', '127.0.0.1'))
REFINE_PORT = os.environ.get('OPENREFINE_PORT', os.environ.get('GOOGLE_REFINE_PORT', '3337'))


class RefineServer(object):
    """Communicate with a OpenRefine server."""

    @staticmethod
    def url(refine_port,refine_host):
        """Return the URL to the OpenRefine server."""
        server = 'http://' + refine_host
        if REFINE_PORT != '80':
            server += ':' + refine_port
        return server

    def __init__(self, refine_port=None, refine_host=None,server=None):
        #  server='http://'+refine_host+refine_host
        #print(server,refine_port,refine_host)
        if server is None:
            if refine_port is None and refine_host is None:
                server = self.url(REFINE_PORT,REFINE_HOST)
            elif refine_host is None:
                server=self.url(refine_port,REFINE_HOST)
            elif refine_port is None:
                server=self.url(REFINE_PORT,refine_host)
            else:
                server = self.url(refine_port, refine_host)
        #print(server)
        self.server = server[:-1] if server.endswith('/') else server
        self.__version = None  # see version @property below

    def urlopen(self, command, data=None, params=None, project_id=None):
        """Open a OpenRefine URL and with optional query params and POST data.
        data: POST data dict
        param: query params dict
        project_id: project ID as string
        Returns urllib2.urlopen iterable."""
        url = self.server + '/command/core/' + command
        if data is None:
            data = {}
        if params is None:
            params = {}
        if project_id:
            # XXX haven't figured out pattern on qs v body
            if 'delete' in command or data:
                data['project'] = project_id
            else:
                params['project'] = project_id
        if params:
            url += '?' + urllib.urlencode(params)
        req = urllib2.Request(url)
        if data:
            req.add_data(data)  # data = urllib.urlencode(data)
        #req.add_header('Accept-Encoding', 'gzip')
        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            raise Exception('HTTP %d "%s" for %s\n\t%s' % (e.code, e.msg, e.geturl(), data))
        except urllib2.URLError as e:
            raise urllib2.URLError(
                '%s for %s. No OpenRefine server reachable/running; ENV set?' %
                (e.reason, self.server))
        if response.info().get('Content-Encoding', None) == 'gzip':
            # Need a seekable filestream for gzip
            gzip_fp = gzip.GzipFile(fileobj=StringIO.StringIO(response.read()))
            # XXX Monkey patch response's filehandle. Better way?
            urllib.addbase.__init__(response, gzip_fp)
        return response

    def urlopen_json(self, *args, **kwargs):
        """Open a OpenRefine URL, optionally POST data, and return parsed JSON."""
        response = json.loads(self.urlopen(*args, **kwargs).read())
        if 'code' in response and response['code'] not in ('ok', 'pending'):
            error_message = ('server ' + response['code'] + ': ' +
                             response.get('message', response.get('stack', response)))
            raise Exception(error_message)
        return response

    def get_version(self):
        """Return version data.
        {"revision":"r1836","full_version":"2.0 [r1836]",
         "full_name":"Google Refine 2.0 [r1836]","version":"2.0"}"""
        return self.urlopen_json('get-version')

    @property
    def version(self):
        if self.__version is None:
            self.__version = self.get_version()['version']
        return self.__version


class Refine:
    """Class representing a connection to a OpenRefine server."""
    def __init__(self, server,refine_port=None,refine_host=None):
        self.refine_port = refine_port
        self.refine_host=refine_host
        if isinstance(server, RefineServer):
            self.server = server
        else:
            self.server = RefineServer(server)

    def list_projects(self):
        """Return a dict of projects indexed by id.
        {u'1877818633188': {
            'id': u'1877818633188', u'name': u'akg',
            u'modified': u'2011-04-07T12:30:07Z',
            u'created': u'2011-04-07T12:30:07Z'
        },
        """
        # It's tempting to add in an index by name but there can be
        # projects with the same name.
        return self.server.urlopen_json('get-all-project-metadata')['projects']

    def get_project_name(self, project_id):
        """Returns project name given project_id."""
        projects = self.list_projects()
        return projects[project_id]['name']

    def open_project(self, project_id):
        """Open a OpenRefine project."""
        return RefineProject(self.server, project_id)

    def new_project(self, project_file=None, project_name=None,
                    project_format='',**kwargs):
        """Create a OpenRefine project."""
        defaults = {'guessCellValueTypes': False, 'headerLines': 1, 'ignoreLines': -1, 'includeFileSources': False,
                    'limit': -1, 'linesPerRow': 1, 'processQuotes': True, 'separator': ',', 'skipDataLines': 0,
                    'storeBlankCellsAsNulls': True, 'storeBlankRows': True, 'storeEmptyStrings': True,
                    'trimStrings': False}

        # options
        options = {'format': project_format}
        if project_file is not None:
            options['project-file'] = {
                'fd': open(project_file),
                'filename': project_file,
            }
        if project_name is None:
            # make a name for itself by stripping extension and directories
            project_name = (project_file or 'New project').rsplit('.', 1)[0]
            project_name = os.path.basename(project_name)
        options['project-name'] = project_name

        # params (the API requires a json in the 'option' POST argument)
        params = defaults
        params.update(kwargs)
        params = {'options': json.dumps(params)}

        # submit
        response = self.server.urlopen(
            'create-project-from-upload', options, params
        )
        # expecting a redirect to the new project containing the id in the url
        url_params = urlparse.parse_qs(
            urlparse.urlparse(response.geturl()).query)
        if 'project' in url_params:
            project_id = url_params['project'][0]

            # check number of rows
            rows = RefineProject(RefineServer(refine_port=self.refine_port,refine_host=self.refine_host),refine_port=self.refine_port,refine_host=self.refine_host,project_id=project_id).do_json('get-rows')['total']
            if rows > 0:
                print('{0}: {1}'.format('id', project_id))
                print('{0}: {1}'.format('rows', rows))
                return RefineProject(self.server, refine_port=self.refine_port,refine_host=self.refine_host,project_id=project_id), project_id, rows
            else:
                raise Exception(
                    'Project contains 0 rows. Please check --help for mandatory arguments for xml, json, xlsx and ods')
        else:
            raise Exception('Project not created')


def RowsResponseFactory(column_index):
    """Factory for the parsing the output from get_rows().
    Uses the project's model's row cell index so that a row can be used
    as a dict by column name."""

    class RowsResponse(object):
        class RefineRows(object):
            class RefineRow(object):
                def __init__(self, row_response):
                    self.flagged = row_response['flagged']
                    self.starred = row_response['starred']
                    self.index = row_response['i']
                    self.row = [c['v'] if c else None
                                for c in row_response['cells']]

                def __getitem__(self, column):
                    # Trailing nulls seem to be stripped from row data
                    try:
                        return self.row[column_index[column]]
                    except IndexError:
                        return None

            def __init__(self, rows_response):
                self.rows_response = rows_response

            def __iter__(self):
                for row_response in self.rows_response:
                    yield self.RefineRow(row_response)

            def __getitem__(self, index):
                return self.RefineRow(self.rows_response[index])

            def __len__(self):
                return len(self.rows_response)

        def __init__(self, response):
            self.mode = response['mode']
            self.filtered = response['filtered']
            self.start = response['start']
            self.limit = response['limit']
            self.total = response['total']
            self.rows = self.RefineRows(response['rows'])

    return RowsResponse


class RefineProject:
    """An OpenRefine project."""

    def __init__(self, server, refine_port=None, refine_host=None,project_id=None):
        if not isinstance(server, RefineServer):
            if '/project?project=' in server:
                server, project_id = server.split('/project?project=')
                server = RefineServer(server)
            elif re.match(r'\d+$', server):     # just digits => project ID
                server, project_id = RefineServer(refine_port,refine_host), server
            else:
                server = RefineServer(server)
        self.server = server
        if refine_port is None:
            self.refine_port=REFINE_PORT
        else:
            self.refine_port=refine_port
        if refine_host is None:
            self.refine_host=REFINE_HOST
        else:
            self.refine_host= refine_host
        if not project_id:
            raise Exception('Missing OpenRefine project ID')
        self.project_id = project_id
        self.engine = facet.Engine()
        self.sorting = facet.Sorting()
        self.history_entry = None
        # following filled in by get_models()
        self.key_column = None
        self.has_records = False
        self.columns = None
        self.column_order = {}  # map of column names to order in UI
        self.rows_response_factory = None   # for parsing get_rows()
        self.get_models()
        # following filled in by get_reconciliation_services
        self.recon_services = None

    def project_name(self):
        return Refine(self.server).get_project_name(self.project_id)

    def project_url(self):
        """Return a URL to the project."""
        return '%s/project?project=%s' % (self.server.server, self.project_id)

    def do_raw(self, command, data):
        """Issue a command to the server & return a response object."""
        return self.server.urlopen(command, project_id=self.project_id,
                                   data=data)

    def do_json(self, command, data=None, include_engine=True):
        """Issue a command to the server, parse & return decoded JSON."""
        if include_engine:
            if data is None:
                data = {}
            data['engine'] = self.engine.as_json()
        response = self.server.urlopen_json(command,
                                            project_id=self.project_id,
                                            data=data)
        if 'historyEntry' in response:
            # **response['historyEntry'] won't work as keys are unicode :-/
            he = response['historyEntry']
            self.history_entry = history.HistoryEntry(he['id'], he['time'],
                                                      he['description'])
        return response

    def get_models(self):
        """Fill out column metadata.
        Column structure is a list of columns in their order.
        The cellIndex is an index for that column's data into the list returned
        from get_rows()."""
        response = self.do_json('get-models', include_engine=False)
        column_model = response['columnModel']
        column_index = {}   # map of column name to index into get_rows() data
        self.columns = [column['name'] for column in column_model['columns']]
        for i, column in enumerate(column_model['columns']):
            name = column['name']
            self.column_order[name] = i
            column_index[name] = column['cellIndex']
        self.key_column = column_model['keyColumnName']
        self.has_records = response['recordModel'].get('hasRecords', False)
        self.rows_response_factory = RowsResponseFactory(column_index)
        # TODO: implement rest
        return response

    def get_preference(self, name):
        """Returns the (JSON) value of a given preference setting."""
        response = self.server.urlopen_json('get-preference',
                                            params={'name': name})
        return json.loads(response['value'])

    def wait_until_idle(self, polling_delay=0.5):
        while True:
            response = self.do_json('get-processes', include_engine=False)
            if 'processes' in response and len(response['processes']) > 0:
                time.sleep(polling_delay)
            else:
                return

    def get_operations(self):
        #response_json = self.do_json('get-operations?project={}'.format(self.project_id))
        response_json = urllib2.urlopen("http://{}:{}/command/core/get-operations?project={}".format(self.refine_host,self.refine_port,self.project_id))
        return response_json  # can be 'ok' or 'pending'

    def apply_operations(self, file_path, wait=True):
        json_data = open(file_path).read()
        response_json = self.do_json('apply-operations', {'operations': json_data})
        if response_json['code'] == 'pending' and wait:
            self.wait_until_idle()
            return 'ok'
        return response_json['code']  # can be 'ok' or 'pending'

    def export(self, export_format='tsv'):
        """Return a fileobject of a project's data."""
        url = ('export-rows/' + urllib.quote(self.project_name()) + '.' +
               export_format)
        return self.do_raw(url, data={'format': export_format})

    def export_templating(self, export_format='txt', engine='', prefix='', template='', rowSeparator='', suffix=''):
        """Return a fileobject of a project's data."""
        url = ('export-rows/' + urllib.quote(self.project_name()) + '.' +
               export_format)
        return self.do_raw(url, data={'format': 'template', 'template': template, 'engine': engine, 'prefix': prefix, 'suffix': suffix, 'separator': rowSeparator } )

    def export_rows(self, **kwargs):
        """Return an iterable of parsed rows of a project's data."""
        return csv.reader(self.export(**kwargs), dialect='excel-tab')

    def delete(self):
        response_json = self.do_json('delete-project', include_engine=False)
        return 'code' in response_json and response_json['code'] == 'ok'

    def compute_facets(self, facets=None):
        """Compute facets as per the project's engine.
        The response object has two attributes, mode & facets. mode is one of
        'row-based' or 'record-based'. facets is a magic list of facets in the
        same order as they were specified in the Engine. Magic allows the
        original Engine's facet as index into the response, e.g.,
        name_facet = TextFacet('name')
        response = project.compute_facets(name_facet)
        response.facets[name_facet]     # same as response.facets[0]
        """
        if facets:
            self.engine.set_facets(facets)
        response = self.do_json('compute-facets')
        return self.engine.facets_response(response)

    def get_rows(self, facets=None, sort_by=None, start=0, limit=10):
        if facets:
            self.engine.set_facets(facets)
        if sort_by is not None:
            self.sorting = facet.Sorting(sort_by)
        response = self.do_json('get-rows', {'sorting': self.sorting.as_json(),
                                             'start': start, 'limit': limit})
        return self.rows_response_factory(response)

    def reorder_rows(self, sort_by=None):
        if sort_by is not None:
            self.sorting = facet.Sorting(sort_by)
        response = self.do_json('reorder-rows',
                                {'sorting': self.sorting.as_json()})
        # clear sorting
        self.sorting = facet.Sorting()
        return response

    def remove_rows(self, facets=None):
        if facets:
            self.engine.set_facets(facets)
        return self.do_json('remove-rows')

    def text_transform(self, column, expression, on_error='set-to-blank',
                       repeat=False, repeat_count=10):
        response = self.do_json('text-transform', {
            'columnName': column, 'expression': expression,
            'onError': on_error, 'repeat': repeat,
            'repeatCount': repeat_count})
        return response

    def edit(self, column, edit_from, edit_to):
        edits = [{'from': [edit_from], 'to': edit_to}]
        return self.mass_edit(column, edits)

    def mass_edit(self, column, edits, expression='value'):
        """edits is [{'from': ['foo'], 'to': 'bar'}, {...}]"""
        edits = json.dumps(edits)
        response = self.do_json('mass-edit', {
            'columnName': column, 'expression': expression, 'edits': edits})
        return response

    clusterer_defaults = {
        'binning': {
            'type': 'binning',
            'function': 'fingerprint',
            'params': {},
        },
        'knn': {
            'type': 'knn',
            'function': 'levenshtein',
            'params': {
                'radius': 1,
                'blocking-ngram-size': 6,
            },
        },
    }

    def compute_clusters(self, column, clusterer_type='binning',
                         function=None, params=None):
        """Returns a list of clusters of {'value': ..., 'count': ...}."""
        clusterer = self.clusterer_defaults[clusterer_type]
        if params is not None:
            clusterer['params'] = params
        if function is not None:
            clusterer['function'] = function
        clusterer['column'] = column
        response = self.do_json('compute-clusters', {
            'clusterer': json.dumps(clusterer)})
        return [[{'value': x['v'], 'count': x['c']} for x in cluster]
                for cluster in response]

    def annotate_one_row(self, row, annotation, state=True):
        if annotation not in ('starred', 'flagged'):
            raise ValueError('annotation must be one of starred or flagged')
        state = 'true' if state is True else 'false'
        return self.do_json('annotate-one-row', {'row': row.index,
                                                 annotation: state})

    def flag_row(self, row, flagged=True):
        return self.annotate_one_row(row, 'flagged', flagged)

    def star_row(self, row, starred=True):
        return self.annotate_one_row(row, 'starred', starred)

    def add_column(self, column, new_column, expression='value',
                   column_insert_index=None, on_error='set-to-blank'):
        if column_insert_index is None:
            column_insert_index = self.column_order[column] + 1
        response = self.do_json('add-column', {
            'baseColumnName': column, 'newColumnName': new_column,
            'expression': expression, 'columnInsertIndex': column_insert_index,
            'onError': on_error})
        self.get_models()
        return response

    def split_column(self, column, separator=',', mode='separator',
                     regex=False, guess_cell_type=True,
                     remove_original_column=True):
        response = self.do_json('split-column', {
            'columnName': column, 'separator': separator, 'mode': mode,
            'regex': regex, 'guessCellType': guess_cell_type,
            'removeOriginalColumn': remove_original_column})
        self.get_models()
        return response

    def rename_column(self, column, new_column):
        response = self.do_json('rename-column', {'oldColumnName': column,
                                                  'newColumnName': new_column})
        self.get_models()
        return response

    def reorder_columns(self, new_column_order):
        """Takes an array of column names in the new order."""
        response = self.do_json('reorder-columns', {
            'columnNames': new_column_order})
        self.get_models()
        return response

    def move_column(self, column, index):
        """Move column to a new position."""
        if index == 'end':
            index = len(self.columns) - 1
        response = self.do_json('move-column', {'columnName': column,
                                                'index': index})
        self.get_models()
        return response

    def blank_down(self, column):
        response = self.do_json('blank-down', {'columnName': column})
        self.get_models()
        return response

    def fill_down(self, column):
        response = self.do_json('fill-down', {'columnName': column})
        self.get_models()
        return response

    def transpose_columns_into_rows(
            self, start_column, column_count,
            combined_column_name, separator=':', prepend_column_name=True,
            ignore_blank_cells=True):

        response = self.do_json('transpose-columns-into-rows', {
            'startColumnName': start_column, 'columnCount': column_count,
            'combinedColumnName': combined_column_name,
            'prependColumnName': prepend_column_name,
            'separator': separator, 'ignoreBlankCells': ignore_blank_cells})
        self.get_models()
        return response

    def transpose_rows_into_columns(self, column, row_count):
        response = self.do_json('transpose-rows-into-columns', {
            'columnName': column, 'rowCount': row_count})
        self.get_models()
        return response

    # Reconciliation
    # http://code.google.com/p/google-refine/wiki/ReconciliationServiceApi
    def guess_types_of_column(self, column, service):
        """Query the reconciliation service for what it thinks this column is.
        service: reconciliation endpoint URL
        Returns [
           {"id":"/domain/type","name":"Type Name","score":10.2,"count":18},
           ...
        ]
        """
        response = self.do_json('guess-types-of-column', {
            'columnName': column, 'service': service}, include_engine=False)
        return response['types']

    def get_reconciliation_services(self):
        response = self.get_preference('reconciliation.standardServices')
        self.recon_services = response
        return response

    def get_reconciliation_service_by_name_or_url(self, name):
        recon_services = self.get_reconciliation_services()
        for recon_service in recon_services:
            if recon_service['name'] == name or recon_service['url'] == name:
                return recon_service
        return None

    def reconcile(self, column, service, reconciliation_type=None,
                  reconciliation_config=None):
        """Perform a reconciliation asynchronously.
        config: {
            "mode": "standard-service",
            "service": "http://.../reconcile/",
            "identifierSpace": "http://.../ns/authority",
            "schemaSpace": "http://.../ns/type",
            "type": {
                "id": "/domain/type",
                "name": "Type Name"
            },
            "autoMatch": true,
            "columnDetails": []
        }
        Returns typically {'code': 'pending'}; call wait_until_idle() to wait
        for reconciliation to complete.
        """
        # Create a reconciliation config by looking up recon service info
        if reconciliation_config is None:
            service = self.get_reconciliation_service_by_name_or_url(service)
            if reconciliation_type is None:
                raise ValueError('Must have at least one of config or type')
            reconciliation_config = {
                'mode': 'standard-service',
                'service': service['url'],
                'identifierSpace': service['identifierSpace'],
                'schemaSpace': service['schemaSpace'],
                'type': {
                    'id': reconciliation_type['id'],
                    'name': reconciliation_type['name'],
                },
                'autoMatch': True,
                'columnDetails': [],
            }
        return self.do_json('reconcile', {
            'columnName': column, 'config': json.dumps(reconciliation_config)})