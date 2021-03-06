# Copyright 2017 IBM Corp.
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

import mock
import unittest
import webob.exc

from zvmsdk.sdkwsgi import handler
from zvmsdk.sdkwsgi.handlers import tokens


env = {'SERVER_SOFTWARE': 'WSGIServer/0.1 Python/2.7.3',
       'SCRIPT_NAME': '',
       'REQUEST_METHOD': 'GET',
       'SERVER_PROTOCOL': 'HTTP/1.1',
       'SERVER_PORT': '8001',
       'HTTP_HOST': '127.0.0.1:8001',
       'wsgi.version': (1, 0),
       'HTTP_ACCEPT': '*/*',
       'LESSCLOSE': '/usr/bin/lesspipe %s %s',
       'wsgi.run_once': False,
       'wsgi.multiprocess': False,
       'SERVER_NAME': 'localhost',
       'REMOTE_ADDR': '127.0.0.1',
       'wsgi.url_scheme': 'http',
       'CONTENT_LENGTH': '',
       'wsgi.multithread': True,
       'CONTENT_TYPE': 'text/plain',
       'REMOTE_HOST': 'localhost'}


def dummy(status, headerlist):
    pass


class GuestHandlerNegativeTest(unittest.TestCase):

    def setUp(self):
        self.env = env

    def test_guest_invalid_resource(self):
        self.env['PATH_INFO'] = '/gueba'
        self.env['REQUEST_METHOD'] = 'GET'
        h = handler.SdkHandler()
        self.assertRaises(webob.exc.HTTPNotFound,
                          h, self.env, dummy)

    def test_guest_list_invalid(self):
        self.env['PATH_INFO'] = '/guest'
        self.env['REQUEST_METHOD'] = 'PUT'
        h = handler.SdkHandler()
        self.assertRaises(webob.exc.HTTPMethodNotAllowed,
                          h, self.env, dummy)

    def test_guest_get_info_method_invalid(self):
        self.env['PATH_INFO'] = '/guest/1/info'
        self.env['REQUEST_METHOD'] = 'PUT'
        h = handler.SdkHandler()
        self.assertRaises(webob.exc.HTTPMethodNotAllowed,
                          h, self.env, dummy)

    def test_guest_get_info_resource_invalid(self):
        self.env['PATH_INFO'] = '/guest/1/info1'
        self.env['REQUEST_METHOD'] = 'PUT'
        h = handler.SdkHandler()
        self.assertRaises(webob.exc.HTTPNotFound,
                          h, self.env, dummy)


class GuestHandlerTest(unittest.TestCase):

    def setUp(self):
        self.env = env

    @mock.patch.object(tokens, 'validate')
    def test_guest_get_info(self, mock_validate):
        self.env['PATH_INFO'] = '/guest/1/info'
        self.env['REQUEST_METHOD'] = 'GET'
        h = handler.SdkHandler()
        with mock.patch('zvmsdk.sdkwsgi.handlers.guest.VMHandler.get_info') \
            as get_info:
            h(self.env, dummy)

            get_info.assert_called_once_with('1')

    @mock.patch.object(tokens, 'validate')
    def test_guest_get_nic_info(self, mock_validate):
        self.env['PATH_INFO'] = '/guest/1/nic'
        self.env['REQUEST_METHOD'] = 'GET'
        h = handler.SdkHandler()
        func = 'zvmsdk.sdkwsgi.handlers.guest.VMHandler.get_nic_info'
        with mock.patch(func) as get_nic_info:
            h(self.env, dummy)

            get_nic_info.assert_called_once_with('1')

    @mock.patch.object(tokens, 'validate')
    def test_guest_get_power_state(self, mock_validate):
        self.env['PATH_INFO'] = '/guest/1/power_state'
        self.env['REQUEST_METHOD'] = 'GET'
        h = handler.SdkHandler()
        function = 'zvmsdk.sdkwsgi.handlers.guest.VMHandler'\
                   '.get_power_state'
        with mock.patch(function) as get_power:
            h(self.env, dummy)

            get_power.assert_called_once_with('1')

    @mock.patch('zvmsdk.sdkwsgi.util.extract_json')
    @mock.patch.object(tokens, 'validate')
    def test_guest_create(self, mock_validate, mock_json):
        mock_json.return_value = {}
        self.env['PATH_INFO'] = '/guest'
        self.env['REQUEST_METHOD'] = 'POST'
        h = handler.SdkHandler()
        function = 'zvmsdk.sdkwsgi.handlers.guest.VMHandler.create'
        with mock.patch(function) as create:
            h(self.env, dummy)

            self.assertTrue(create.called)

    @mock.patch('zvmsdk.sdkwsgi.util.extract_json')
    @mock.patch.object(tokens, 'validate')
    def test_guest_delete(self, mock_validate, mock_json):
        mock_json.return_value = {}
        self.env['PATH_INFO'] = '/guest/1'
        self.env['REQUEST_METHOD'] = 'DELETE'
        h = handler.SdkHandler()
        function = 'zvmsdk.sdkwsgi.handlers.guest.VMHandler.delete'
        with mock.patch(function) as delete:
            h(self.env, dummy)
            delete.assert_called_once_with('1')

    @mock.patch('zvmsdk.sdkwsgi.util.extract_json')
    @mock.patch.object(tokens, 'validate')
    def test_guest_create_nic(self, mock_validate, mock_json):
        mock_json.return_value = {}
        self.env['PATH_INFO'] = '/guest/1/nic'
        self.env['REQUEST_METHOD'] = 'POST'
        h = handler.SdkHandler()
        function = 'zvmsdk.sdkwsgi.handlers.guest.VMHandler.create_nic'
        with mock.patch(function) as create_nic:
            h(self.env, dummy)

            self.assertTrue(create_nic.called)

    @mock.patch('zvmsdk.sdkwsgi.util.extract_json')
    @mock.patch.object(tokens, 'validate')
    def test_guest_update_nic(self, mock_validate, mock_json):
        mock_json.return_value = {}
        self.env['PATH_INFO'] = '/guest/1/nic'
        self.env['REQUEST_METHOD'] = 'PUT'
        h = handler.SdkHandler()
        func = 'zvmsdk.sdkwsgi.handlers.guest.VMHandler.couple_uncouple_nic'
        with mock.patch(func) as update_nic:
            h(self.env, dummy)

            self.assertTrue(update_nic.called)


class ImageHandlerNegativeTest(unittest.TestCase):

    def setUp(self):
        self.env = env

    def test_image_create_invalid_method(self):
        self.env['PATH_INFO'] = '/image'
        self.env['REQUEST_METHOD'] = 'PUT'
        h = handler.SdkHandler()
        self.assertRaises(webob.exc.HTTPMethodNotAllowed,
                          h, self.env, dummy)

    def test_image_get_root_disk_size_invalid(self):
        self.env['PATH_INFO'] = '/image/image1/root_size'
        self.env['REQUEST_METHOD'] = 'GET'
        h = handler.SdkHandler()
        self.assertRaises(webob.exc.HTTPNotFound,
                          h, self.env, dummy)


class ImageHandlerTest(unittest.TestCase):

    def setUp(self):
        self.env = env

    @mock.patch.object(tokens, 'validate')
    def test_image_root_disk_size(self, mock_validate):
        self.env['PATH_INFO'] = '/image/image1/root_disk_size'
        self.env['REQUEST_METHOD'] = 'GET'
        h = handler.SdkHandler()
        function = 'zvmsdk.sdkwsgi.handlers.image.ImageAction'\
                   '.get_root_disk_size'
        with mock.patch(function) as get_size:
            h(self.env, dummy)

            get_size.assert_called_once_with('image1')

    @mock.patch('zvmsdk.sdkwsgi.util.extract_json')
    @mock.patch.object(tokens, 'validate')
    def test_image_create(self, mock_validate, mock_json):
        mock_json.return_value = {}
        self.env['PATH_INFO'] = '/image'
        self.env['REQUEST_METHOD'] = 'POST'
        h = handler.SdkHandler()
        function = 'zvmsdk.sdkwsgi.handlers.image.ImageAction.create'
        with mock.patch(function) as create:
            h(self.env, dummy)

            self.assertTrue(create.called)


class HostHandlerNegativeTest(unittest.TestCase):

    def setUp(self):
        self.env = env

    def test_host_get_resource_invalid(self):
        self.env['PATH_INFO'] = '/host1'
        self.env['REQUEST_METHOD'] = 'GET'
        h = handler.SdkHandler()
        self.assertRaises(webob.exc.HTTPNotFound,
                          h, self.env, dummy)

    def test_host_put_method_invalid(self):
        self.env['PATH_INFO'] = '/host/guests'
        self.env['REQUEST_METHOD'] = 'PUT'
        h = handler.SdkHandler()
        self.assertRaises(webob.exc.HTTPMethodNotAllowed,
                          h, self.env, dummy)

    def test_host_get_info_invalid(self):
        self.env['PATH_INFO'] = '/host/inf'
        self.env['REQUEST_METHOD'] = 'GET'
        h = handler.SdkHandler()
        self.assertRaises(webob.exc.HTTPNotFound,
                          h, self.env, dummy)

    def test_host_get_disk_size_invalid(self):
        self.env['PATH_INFO'] = '/host/disk_inf/d1'
        self.env['REQUEST_METHOD'] = 'GET'
        h = handler.SdkHandler()
        self.assertRaises(webob.exc.HTTPNotFound,
                          h, self.env, dummy)


class HostHandlerTest(unittest.TestCase):

    def setUp(self):
        self.env = env

    @mock.patch.object(tokens, 'validate')
    def test_host_list(self, mock_validate):
        self.env['PATH_INFO'] = '/host/guests'
        self.env['REQUEST_METHOD'] = 'GET'
        h = handler.SdkHandler()
        function = 'zvmsdk.sdkwsgi.handlers.host.HostAction.list'
        with mock.patch(function) as list:
            list.return_value = ''
            h(self.env, dummy)

            self.assertTrue(list.called)

    @mock.patch.object(tokens, 'validate')
    def test_host_get_info(self, mock_validate):
        self.env['PATH_INFO'] = '/host/info'
        self.env['REQUEST_METHOD'] = 'GET'
        h = handler.SdkHandler()
        function = 'zvmsdk.sdkwsgi.handlers.host.HostAction.get_info'
        with mock.patch(function) as get_info:
            get_info.return_value = ''
            h(self.env, dummy)

            self.assertTrue(get_info.called)

    @mock.patch.object(tokens, 'validate')
    def test_host_get_disk_info(self, mock_validate):
        self.env['PATH_INFO'] = '/host/disk_info/disk1'
        self.env['REQUEST_METHOD'] = 'GET'
        h = handler.SdkHandler()
        function = 'zvmsdk.sdkwsgi.handlers.host.HostAction.get_disk_info'
        with mock.patch(function) as get_disk_info:
            get_disk_info.return_value = ''
            h(self.env, dummy)

            get_disk_info.assert_called_once_with('disk1')


class VswitchHandlerNegativeTest(unittest.TestCase):

    def setUp(self):
        self.env = env

    def test_vswitch_put_method_invalid(self):
        self.env['PATH_INFO'] = '/vswitch'
        self.env['REQUEST_METHOD'] = 'PUT'
        h = handler.SdkHandler()
        self.assertRaises(webob.exc.HTTPMethodNotAllowed,
                          h, self.env, dummy)


class VswitchHandlerTest(unittest.TestCase):
    def setUp(self):
        self.env = env

    @mock.patch.object(tokens, 'validate')
    def test_vswitch_list(self, mock_validate):
        self.env['PATH_INFO'] = '/vswitch'
        self.env['REQUEST_METHOD'] = 'GET'
        h = handler.SdkHandler()
        function = 'zvmsdk.sdkwsgi.handlers.vswitch.VswitchAction.list'
        with mock.patch(function) as list:
            list.return_value = ''
            h(self.env, dummy)

            self.assertTrue(list.called)

    @mock.patch('zvmsdk.sdkwsgi.util.extract_json')
    @mock.patch.object(tokens, 'validate')
    def test_vswitch_create(self, mock_validate, mock_json):
        mock_json.return_value = {}
        self.env['PATH_INFO'] = '/vswitch'
        self.env['REQUEST_METHOD'] = 'POST'
        h = handler.SdkHandler()
        function = 'zvmsdk.sdkwsgi.handlers.vswitch.VswitchAction.create'
        with mock.patch(function) as create:
            h(self.env, dummy)

            self.assertTrue(create.called)
