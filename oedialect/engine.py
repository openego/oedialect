import json

import os
import requests
import sqlalchemy
from dateutil.parser import parse as parse_date
from shapely import wkb
from psycopg2.extensions import PYINTERVAL
from decimal import Decimal
import datetime
from oedialect import error
from sqlalchemy.dialects.postgresql.base import _DECIMAL_TYPES

def date_handler(obj):
    """
    Implements a handler to serialize dates in JSON-strings
    :param obj: An object
    :return: The str method is called (which is the default serializer for JSON) unless the object has an attribute  *isoformat*
    """
    if isinstance(obj, datetime.time):
        return {
            'type': 'value',
            'datatype': 'time',
            'value': obj.isoformat()
        }
    elif isinstance(obj, datetime.datetime):
        return {
            'type': 'value',
            'datatype': 'datetime',
            'value': obj.isoformat()
        }
    elif isinstance(obj, datetime.date):
        return {
            'type': 'value',
            'datatype': 'date',
            'value': obj.isoformat()
        }
    elif isinstance(obj, Decimal):
        return {
            'type': 'value',
            'datatype': 'Decimal',
            'value': str(obj),
        }
    else:
        return str(obj)

class OEConnection():
    """

    """

    """
        Connection methods
    """

    def __init__(self, host='localhost', port=80, user='', database='', password=''):
        self.__host = host
        self.__port = port
        self.__user = user
        self.__token = password
        response = self.post('advanced/connection/open', {})['content']
        self._id = response['connection_id']
        self.__transactions = set()
        self._cursors = set()
        self.__closed = False

    """
        TODO: Look at PGDialect in sqlalchemy.dialects.postgresql.base
    """

    def close(self, *args, **kwargs):
        #for cursor in self._cursors:
        #    cursor.close()
        response = self.post('advanced/connection/close', {},
                             requires_connection_id=True)


    def commit(self, *args, **kwargs):
        response = self.post('advanced/connection/commit', {},
                             requires_connection_id=True)

    def rollback(self, *args, **kwargs):
        response = self.post('advanced/connection/rollback', {},
                             requires_connection_id=True)

    def cursor(self, *args, **kwargs):
        cursor = OECursor(self)
        self._cursors.add(cursor)
        return cursor

    """
        Two-phase commit support methods
    """

    def xid(self, *args, **kwargs):
        raise NotImplementedError

    def tpc_begin(self, *args, **kwargs):
        raise NotImplementedError

    def tpc_commit(self, *args, **kwargs):
        raise NotImplementedError

    def tpc_prepare(self, *args, **kwargs):
        raise NotImplementedError

    def tpc_recover(self, *args, **kwargs):
        raise NotImplementedError

    def tpc_rollback(self, *args, **kwargs):
        raise NotImplementedError

    """
        DB API extension
    """

    def cancel(self, *args, **kwargs):
        raise NotImplementedError

    def reset(self, *args, **kwargs):
        raise NotImplementedError

    def set_session(self, *args, **kwargs):
        raise NotImplementedError

    def set_client_encoding(self, *args, **kwargs):
        raise NotImplementedError

    def set_isolation_level(self, *args, **kwargs):
        raise NotImplementedError

    def get_backend_pid(self, *args, **kwargs):
        raise NotImplementedError

    def get_dsn_parameters(self, *args, **kwargs):
        raise NotImplementedError

    def get_parameter_status(self, *args, **kwargs):
        raise NotImplementedError

    def get_transaction_status(self, *args, **kwargs):
        raise NotImplementedError

    def lobject(self, *args, **kwargs):
        raise NotImplementedError

    """
        Methods related to asynchronous support
    """

    def poll(self, *args, **kwargs):
        raise NotImplementedError

    def fileno(self, *args, **kwargs):
        raise NotImplementedError

    def isexecuting(self, *args, **kwargs):
        raise NotImplementedError


    def post_expect_stream(self, suffix, query, cursor_id=None):
        sender = requests.post

        header = dict(urlheaders)
        if self.__token:
            header['Authorization'] = 'Token %s' % self.__token

        data = {}
        if cursor_id:
            data['connection_id'] = self._id
            data['cursor_id'] = cursor_id

        host = self.__host
        if self.__host in ['oep.iks.cs.ovgu.de', 'oep2.iks.cs.ovgu.de',
                           'oep.iws.cs.ovgu.de', 'oep2.iws.cs.ovgu.de',
                           'openenergyplatform.org']:
            host = 'openenergy-platform.org'

        port = self.__port if self.__port != 80 else 443

        protocol = os.environ.get('OEDIALECT_PROTOCOL', 'https')
        assert protocol in ['http', 'https']

        verify = os.environ.get('OEDIALECT_VERIFY_CERTIFICATE', 'TRUE') == 'TRUE'

        response = sender(
            '{protocol}://{host}:{port}/api/v0/{suffix}'.format(
                protocol=protocol,
                host=host,
                port=port,
                suffix=suffix),
            json=json.loads(json.dumps(data)),
            headers=header, stream=True, verify=verify)

        process_returntype(response)

        try:
            i = 0
            for line in response.iter_lines():
                yield json.loads(line.decode('utf8').replace("'", '\\"'))
        except Exception as e:
            raise



    def post(self, suffix, query, cursor_id=None, requires_connection_id=False):
        sender = requests.post
        if isinstance(query, dict) and 'request_type' in query:
            if query['request_type'] == 'put':
                sender = requests.put
            if query['request_type'] == 'delete':
                sender = requests.delete
            if query['request_type'] == 'get':
                sender = requests.get

        if 'info_cache' in query:
            del query['info_cache']

        data = {'query': query}

        if requires_connection_id or cursor_id:
            data['connection_id'] = self._id

        if cursor_id:
            data['cursor_id'] = cursor_id

        header = dict(urlheaders)
        if self.__token:
            header['Authorization'] = 'Token %s'%self.__token

        host = self.__host
        if self.__host in ['oep.iks.cs.ovgu.de', 'oep2.iks.cs.ovgu.de',
                           'oep.iws.cs.ovgu.de', 'oep2.iws.cs.ovgu.de',
                           'openenergyplatform.org']:
            host = 'openenergy-platform.org'


        port = self.__port if self.__port != 80 else 443

        protocol = os.environ.get('OEDIALECT_PROTOCOL', 'https')
        assert protocol in ['http', 'https']
        verify = os.environ.get('OEDIALECT_VERIFY_CERTIFICATE', 'TRUE') == 'TRUE'
        ans = sender(
            '{protocol}://{host}:{port}/api/v0/{suffix}'.format(
                protocol=protocol,
                host=host,
                port=port,
                suffix=suffix),
            json=json.loads(json.dumps(data, default=date_handler)),
            headers=header, verify=verify)

        try:
            json_response = ans.json()
        except:
            raise ConnectionException('Answer contains no JSON: ' + repr(ans))

        process_returntype(ans, json_response)

        if isinstance(query, dict) and 'request_type' in query:
            if query['request_type'] == 'get':
                json_response = dict(content=json_response)

        return json_response

def process_returntype(response, content=None):
    if content is None:
        content = {}
    if 400 <= response.status_code < 500:
        message = content.get("reason", "")
        raise ConnectionException('HTTP %d (%s): %s'%(response.status_code,response.reason, message))
    elif 500 <= response.status_code < 600:
        raise ConnectionException('Server side error: ' + content.get('reason', 'No reason returned'))

class OECursor:
    description = None
    rowcount = -1

    def __init__(self, connection):
        self.__connection = connection
        try:
            response = self.__connection.post('advanced/cursor/open', {}, requires_connection_id=True)
            if 'content' not in response:
                raise error.CursorError('Could not open cursor: ' + str(response['reason']) if 'reason' in response else 'No reason returned')
            response = response['content']
        except:
            raise
        self.__id = response['cursor_id']


    def __replace_params(self, jsn, params):
        if jsn is None:
            return dict(type="value", value=None)
        elif type(jsn) == dict:
            for k in jsn:
                jsn[k] = self.__replace_params(jsn[k], params)
            return jsn
        elif type(jsn) == list:
            return list(map(lambda x: self.__replace_params(x, params), jsn))
        elif type(jsn) in [str, sqlalchemy.sql.elements.quoted_name,
                           sqlalchemy.sql.elements._truncated_label]:
            return (jsn % params).strip("'<>").replace('\'', '\"')
        elif isinstance(jsn, int):
            return jsn
        elif callable(jsn):
            return jsn(params)
        else:
            raise Exception("Unknown jsn type (%s) in %s" % (type(jsn), jsn))

    __cell_processors = {
        17: lambda cell: wkb.dumps(wkb.loads(cell, hex=True)),
        1114: lambda cell: parse_date(cell),
        1082: lambda cell: parse_date(cell).date(),
        1083: lambda cell: parse_date(cell).time(),
        1186: lambda cell: PYINTERVAL(cell, None),
    }

    def process_result(self,row):
        for i, x in enumerate(self.description):
            # Translate WKB-hex to binary representation
            if row[i]:
                if x[1] in self.__cell_processors:
                    row[i] = self.__cell_processors[x[1]](row[i])
                elif x[1] in _DECIMAL_TYPES:
                    if isinstance(row[i], list):
                        row[i] = [Decimal(x) for x in row[i]]
                    else:
                        row[i] = Decimal(row[i])

        return row

    def fetchone(self):
        response = self.__connection.post('advanced/cursor/fetch_one', {}, cursor_id=self.__id)[
            'content']
        if response:
            response = self.process_result(response)
        return response

    def fetchall(self):
        result = self.__connection.post_expect_stream('advanced/cursor/fetch_all', {}, cursor_id=self.__id)
        if result:
            for row in result:
                yield self.process_result(row)

    def fetchmany(self, size):
        result = self.__connection.post('advanced/cursor/fetch_many', {'size': size}, cursor_id=self.__id)[
            'content']

        if result:
            for row in result:
                yield self.process_result(row)


    def execute(self, query_obj, params=None):
        if query_obj is None:
            return
        if not isinstance(query_obj, dict):
            if isinstance(query_obj, str):
                raise Exception('Plain string commands are not supported.'
                                'Please use SQLAlchemy datastructures')
            query = query_obj.string
        else:
            query = query_obj
        query = dict(query)
        requires_connection_id = query.get('requires_connection', False)

        query['connection_id'] = self.__connection._id
        query['cursor_id'] = self.__id
        if params:
            if isinstance(params, tuple) and 'values' in query:
                query['values'] = [self.__replace_params(query['values'][0], p) for p in params]
            else:
                query = self.__replace_params(query, params)
        # query = context.compiled.string
        command = query.pop('command')
        return self.__execute_by_post(command, query,
                                  requires_connection_id=requires_connection_id)

    def executemany(self, query, params=None):
        if params is None:
            return self.execute(query)
        else:
            if query.isinsert and not (query.isdelete or query.isupdate):
                return self.execute(query, params)
            else:
                return [self.execute(query, p) for p in params]

    def close(self):
        self.__connection.post('advanced/cursor/close', {}, cursor_id=self.__id)

    def __execute_by_post(self, command, query, requires_connection_id=False):

        response = self.__connection.post(command, query, cursor_id=self.__id,
                                requires_connection_id=requires_connection_id)

        if 'content' in response:
            result = response['content']
            if result:
                if isinstance(result, dict):
                    if 'description' in result:
                        self.description = result['description']
                    if 'rowcount' in result:
                        self.rowcount = result['rowcount']
                    return result
                else:
                    return result
            else:
                return result



urlheaders = {
}


class ConnectionException(Exception):
    pass
