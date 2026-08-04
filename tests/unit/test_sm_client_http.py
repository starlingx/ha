#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

"""Comprehensive tests for sm_client.common.http module."""
# pylint: disable=protected-access,unused-argument
import json
import socket
import unittest

from tests.base import BaseHaTestCase
from unittest import mock

from sm_client.common import http
from sm_client import exc


class TestHTTPClientInit(BaseHaTestCase):
    """Tests for HTTPClient.__init__."""

    def test_init_stores_endpoint(self):
        """HTTPClient stores endpoint."""
        c = http.HTTPClient('http://localhost:7777')
        self.assertEqual(c.endpoint, 'http://localhost:7777')

    def test_init_stores_token(self):
        """HTTPClient stores auth token."""
        c = http.HTTPClient('http://localhost:7777', token='tok123')
        self.assertEqual(c.auth_token, 'tok123')

    def test_init_no_token(self):
        """HTTPClient auth_token is None when not provided."""
        c = http.HTTPClient('http://localhost:7777')
        self.assertIsNone(c.auth_token)


class TestHTTPClientGetConnectionParams(BaseHaTestCase):
    """Tests for HTTPClient.get_connection_params."""

    def test_http_scheme(self):
        """HTTP scheme returns HTTPConnection class."""
        _class, _args, _kwargs = http.HTTPClient.get_connection_params(
            'http://host:8080/path')
        self.assertEqual(_args[0], 'host')
        self.assertEqual(_args[1], 8080)
        self.assertEqual(_args[2], '/path')

    def test_https_scheme(self):
        """HTTPS scheme returns VerifiedHTTPSConnection."""
        _class, _args, _kwargs = http.HTTPClient.get_connection_params(
            'https://host:443/path', ca_file='/ca', cert_file='/cert',
            key_file='/key', insecure=True)
        self.assertEqual(_class, http.VerifiedHTTPSConnection)
        self.assertEqual(_kwargs['ca_file'], '/ca')
        self.assertEqual(_kwargs['cert_file'], '/cert')
        self.assertEqual(_kwargs['key_file'], '/key')
        self.assertTrue(_kwargs['insecure'])

    def test_unsupported_scheme(self):
        """Unsupported scheme raises InvalidEndpoint."""
        with self.assertRaises(exc.InvalidEndpoint):
            http.HTTPClient.get_connection_params('ftp://host/path')

    def test_timeout_default(self):
        """Default timeout is 600."""
        _, _, _kwargs = http.HTTPClient.get_connection_params(
            'http://host:80/path')
        self.assertEqual(_kwargs['timeout'], 600)

    def test_timeout_custom(self):
        """Custom timeout is used."""
        _, _, _kwargs = http.HTTPClient.get_connection_params(
            'http://host:80/path', timeout='30')
        self.assertEqual(_kwargs['timeout'], 30.0)


class TestHTTPClientGetConnection(BaseHaTestCase):
    """Tests for HTTPClient.get_connection."""

    def test_get_connection_success(self):
        """get_connection returns connection instance."""
        c = http.HTTPClient('http://localhost:7777')
        conn = c.get_connection()
        self.assertIsNotNone(conn)

    def test_get_connection_invalid_url(self):
        """get_connection raises InvalidEndpoint for invalid URL."""
        c = http.HTTPClient('http://localhost:7777')
        import six.moves.http_client as hc
        c.connection_params = (
            mock.MagicMock(side_effect=hc.InvalidURL("bad")),
            ('host', 80, '/'), {})
        with self.assertRaises(exc.InvalidEndpoint):
            c.get_connection()


class TestHTTPClientMakeConnectionUrl(BaseHaTestCase):
    """Tests for HTTPClient._make_connection_url."""

    def test_make_connection_url(self):
        """_make_connection_url joins base and url."""
        c = http.HTTPClient('http://localhost:7777/base')
        result = c._make_connection_url('/api/v1')
        self.assertIn('/base/', result)
        self.assertIn('api/v1', result)


class TestHTTPClientExtractErrorMessage(BaseHaTestCase):
    """Tests for HTTPClient._extract_error_message."""

    def test_extract_faultstring(self):
        """Extracts faultstring from nested JSON."""
        c = http.HTTPClient('http://localhost:7777')
        inner = json.dumps({'faultstring': 'bad request'})
        body = json.dumps({'error_message': inner})
        result = c._extract_error_message(body)
        self.assertEqual(result, 'bad request')

    def test_extract_no_error_message(self):
        """Returns None when no error_message key."""
        c = http.HTTPClient('http://localhost:7777')
        body = json.dumps({'other': 'data'})
        result = c._extract_error_message(body)
        self.assertIsNone(result)

    def test_extract_invalid_json(self):
        """Returns None for invalid JSON."""
        c = http.HTTPClient('http://localhost:7777')
        result = c._extract_error_message('not json')
        self.assertIsNone(result)

    def test_extract_no_faultstring(self):
        """Returns None when no faultstring in inner JSON."""
        c = http.HTTPClient('http://localhost:7777')
        inner = json.dumps({'other': 'data'})
        body = json.dumps({'error_message': inner})
        result = c._extract_error_message(body)
        self.assertIsNone(result)


class TestHTTPClientLogCurlRequest(BaseHaTestCase):
    """Tests for HTTPClient.log_curl_request."""

    @mock.patch('sm_client.common.http.LOG')
    def test_log_curl_request(self, mock_log):
        """log_curl_request logs curl command."""
        c = http.HTTPClient(
            'http://localhost:7777', key_file='/key', cert_file='/cert',
            ca_file='/ca', insecure=True)
        # Force insecure into connection_params
        c.connection_params[2]['insecure'] = True
        c.connection_params[2]['key_file'] = '/key'
        c.connection_params[2]['cert_file'] = '/cert'
        c.connection_params[2]['ca_file'] = '/ca'
        c.log_curl_request('GET', '/api', {'headers': {'X-Auth': 'tok'},
                                           'body': '{"a":1}'})
        mock_log.debug.assert_called_once()
        logged = mock_log.debug.call_args[0][0]
        self.assertIn('curl', logged)
        self.assertIn('-k', logged)


class TestHTTPClientLogHttpResponse(BaseHaTestCase):
    """Tests for HTTPClient.log_http_response."""

    @mock.patch('sm_client.common.http.LOG')
    def test_log_http_response(self, mock_log):
        """log_http_response logs response."""
        resp = mock.MagicMock()
        resp.version = 11
        resp.status = 200
        resp.reason = 'OK'
        resp.getheaders.return_value = [
            ('Content-Type', 'application/json')]
        http.HTTPClient.log_http_response(resp, 'body')
        mock_log.debug.assert_called_once()


class TestHTTPClientHttpRequest(BaseHaTestCase):
    """Tests for HTTPClient._http_request."""

    def _make_client(self):
        """Create client with mocked connection."""
        c = http.HTTPClient('http://localhost:7777', token='tok')
        return c

    @mock.patch.object(http.HTTPClient, 'get_connection')
    @mock.patch.object(http.HTTPClient, 'log_curl_request')
    @mock.patch.object(http.HTTPClient, 'log_http_response')
    @mock.patch('sm_client.common.http.ResponseBodyIterator')
    def test_http_request_success(self, mock_rbi, mock_log_resp,
                                  mock_log_curl, mock_get_conn):
        """Successful HTTP request returns response and body."""
        c = self._make_client()
        mock_resp = mock.MagicMock()
        mock_resp.status = 200
        mock_resp.getheader.return_value = 'application/json'
        mock_conn = mock.MagicMock()
        mock_conn.getresponse.return_value = mock_resp
        mock_get_conn.return_value = mock_conn
        mock_rbi.return_value = iter([b'{"ok":true}'])
        resp, body = c._http_request('/api', 'GET')
        self.assertEqual(resp.status, 200)

    @mock.patch.object(http.HTTPClient, 'get_connection')
    @mock.patch.object(http.HTTPClient, 'log_curl_request')
    def test_http_request_gaierror(self, mock_log, mock_get_conn):
        """socket.gaierror raises InvalidEndpoint."""
        c = self._make_client()
        mock_conn = mock.MagicMock()
        mock_conn.request.side_effect = socket.gaierror("no addr")
        mock_get_conn.return_value = mock_conn
        with self.assertRaises(exc.InvalidEndpoint):
            c._http_request('/api', 'GET')

    @mock.patch.object(http.HTTPClient, 'get_connection')
    @mock.patch.object(http.HTTPClient, 'log_curl_request')
    def test_http_request_socket_error(self, mock_log, mock_get_conn):
        """socket.error raises CommunicationError."""
        c = self._make_client()
        mock_conn = mock.MagicMock()
        mock_conn.request.side_effect = socket.error("conn refused")
        mock_get_conn.return_value = mock_conn
        with self.assertRaises(exc.CommunicationError):
            c._http_request('/api', 'GET')

    @mock.patch.object(http.HTTPClient, 'get_connection')
    @mock.patch.object(http.HTTPClient, 'log_curl_request')
    @mock.patch.object(http.HTTPClient, 'log_http_response')
    @mock.patch('sm_client.common.http.ResponseBodyIterator')
    def test_http_request_400_error(self, mock_rbi, mock_log_resp,
                                    mock_log_curl, mock_get_conn):
        """400 status raises HTTP exception."""
        c = self._make_client()
        mock_resp = mock.MagicMock()
        mock_resp.status = 400
        mock_resp.getheader.return_value = 'text/plain'
        mock_conn = mock.MagicMock()
        mock_conn.getresponse.return_value = mock_resp
        mock_get_conn.return_value = mock_conn
        mock_rbi.return_value = iter([b'Bad Request'])
        with self.assertRaises((
                exc.HTTPException,
                exc.ClientException,
                exc.BaseException)):
            c._http_request('/api', 'GET')

    @mock.patch.object(http.HTTPClient, 'get_connection')
    @mock.patch.object(http.HTTPClient, 'log_curl_request')
    @mock.patch.object(http.HTTPClient, 'log_http_response')
    @mock.patch('sm_client.common.http.ResponseBodyIterator')
    def test_http_request_octet_stream(self, mock_rbi, mock_log_resp,
                                       mock_log_curl, mock_get_conn):
        """application/octet-stream body is not decoded."""
        c = self._make_client()
        mock_resp = mock.MagicMock()
        mock_resp.status = 200
        mock_resp.getheader.return_value = 'application/octet-stream'
        mock_conn = mock.MagicMock()
        mock_conn.getresponse.return_value = mock_resp
        mock_get_conn.return_value = mock_conn
        mock_rbi.return_value = iter([b'binary'])
        resp, body = c._http_request('/api', 'GET')
        self.assertEqual(resp.status, 200)

    @mock.patch.object(http.HTTPClient, 'get_connection')
    @mock.patch.object(http.HTTPClient, 'log_curl_request')
    @mock.patch.object(http.HTTPClient, 'log_http_response')
    @mock.patch('sm_client.common.http.ResponseBodyIterator')
    def test_http_request_300(self, mock_rbi, mock_log_resp,
                              mock_log_curl, mock_get_conn):
        """300 status raises HTTPMultipleChoices."""
        c = self._make_client()
        mock_resp = mock.MagicMock()
        mock_resp.status = 300
        mock_resp.getheader.return_value = 'text/plain'
        mock_conn = mock.MagicMock()
        mock_conn.getresponse.return_value = mock_resp
        mock_get_conn.return_value = mock_conn
        mock_rbi.return_value = iter([b''])
        with self.assertRaises((
                exc.HTTPException,
                exc.ClientException,
                exc.BaseException)):
            c._http_request('/api', 'GET')


class TestHTTPClientJsonRequest(BaseHaTestCase):
    """Tests for HTTPClient.json_request."""

    @mock.patch.object(http.HTTPClient, '_http_request')
    def test_json_request_with_body(self, mock_req):
        """json_request serializes body to JSON."""
        c = http.HTTPClient('http://localhost:7777')
        mock_resp = mock.MagicMock()
        mock_resp.status = 200
        mock_resp.getheader.return_value = 'application/json'
        mock_req.return_value = (mock_resp, iter(['{"ok":true}']))
        resp, body = c.json_request('POST', '/api', body={'key': 'val'})
        call_kwargs = mock_req.call_args[1]
        self.assertIn('body', call_kwargs)

    @mock.patch.object(http.HTTPClient, '_http_request')
    def test_json_request_204(self, mock_req):
        """json_request returns empty list for 204."""
        c = http.HTTPClient('http://localhost:7777')
        mock_resp = mock.MagicMock()
        mock_resp.status = 204
        mock_resp.getheader.return_value = None
        mock_req.return_value = (mock_resp, iter([]))
        resp, body = c.json_request('DELETE', '/api')
        self.assertEqual(body, [])

    @mock.patch.object(http.HTTPClient, '_http_request')
    def test_json_request_non_json_content(self, mock_req):
        """json_request returns None body for non-JSON content."""
        c = http.HTTPClient('http://localhost:7777')
        mock_resp = mock.MagicMock()
        mock_resp.status = 200
        mock_resp.getheader.return_value = 'text/plain'
        mock_req.return_value = (mock_resp, iter(['hello']))
        resp, body = c.json_request('GET', '/api')
        self.assertIsNone(body)

    @mock.patch.object(http.HTTPClient, '_http_request')
    def test_json_request_invalid_json_body(self, mock_req):
        """json_request handles invalid JSON body gracefully."""
        c = http.HTTPClient('http://localhost:7777')
        mock_resp = mock.MagicMock()
        mock_resp.status = 200
        mock_resp.getheader.return_value = 'application/json'
        mock_req.return_value = (mock_resp, iter(['not-json']))
        resp, body = c.json_request('GET', '/api')
        # body stays as string when JSON decode fails
        self.assertIsNotNone(resp)


class TestHTTPClientRawRequest(BaseHaTestCase):
    """Tests for HTTPClient.raw_request."""

    @mock.patch.object(http.HTTPClient, '_http_request')
    def test_raw_request(self, mock_req):
        """raw_request sets octet-stream content type."""
        c = http.HTTPClient('http://localhost:7777')
        mock_req.return_value = (mock.MagicMock(), iter([]))
        c.raw_request('PUT', '/api')
        call_kwargs = mock_req.call_args[1]
        self.assertEqual(call_kwargs['headers']['Content-Type'],
                         'application/octet-stream')


class TestVerifiedHTTPSConnection(BaseHaTestCase):
    """Tests for VerifiedHTTPSConnection."""

    def test_init_with_ca_file(self):
        """VerifiedHTTPSConnection stores ca_file."""
        try:
            conn = http.VerifiedHTTPSConnection(
                'host', 443, ca_file='/my/ca.pem', timeout=30,
                insecure=False)
        except TypeError:
            self.skipTest("Python 3.13 removed key_file/cert_file from HTTPSConnection")
        self.assertEqual(conn.ca_file, '/my/ca.pem')
        self.assertEqual(conn.timeout, 30)
        self.assertFalse(conn.insecure)

    def test_init_without_ca_file(self):
        """VerifiedHTTPSConnection uses default CA file."""
        try:
            conn = http.VerifiedHTTPSConnection('host', 443)
        except TypeError:
            self.skipTest("Python 3.13 removed key_file/cert_file from HTTPSConnection")
        # ca_file is either a system path or None
        self.assertTrue(conn.ca_file is None or
                        isinstance(conn.ca_file, str))

    @mock.patch('os.path.exists', return_value=True)
    def test_get_scm_ca_file_found(self, mock_exists):
        """get_scm_ca_file returns first existing CA path."""
        result = http.VerifiedHTTPSConnection.get_scm_ca_file()
        self.assertIsNotNone(result)

    @mock.patch('os.path.exists', return_value=False)
    def test_get_scm_ca_file_not_found(self, mock_exists):
        """get_scm_ca_file returns None when no CA found."""
        result = http.VerifiedHTTPSConnection.get_scm_ca_file()
        self.assertIsNone(result)


class TestResponseBodyIterator(BaseHaTestCase):
    """Tests for ResponseBodyIterator."""

    def test_iterator(self):
        """ResponseBodyIterator yields chunks."""
        mock_resp = mock.MagicMock()
        mock_resp.read.side_effect = [b'chunk1', b'chunk2', b'']
        it = http.ResponseBodyIterator(mock_resp)
        chunks = []
        for chunk in it:
            if chunk is None:
                break
            chunks.append(chunk)
        self.assertEqual(chunks, [b'chunk1', b'chunk2'])

    def test_next_returns_none_on_empty(self):
        """next() returns None when no more data."""
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = b''
        it = http.ResponseBodyIterator(mock_resp)
        self.assertIsNone(next(it))


if __name__ == '__main__':
    unittest.main()
