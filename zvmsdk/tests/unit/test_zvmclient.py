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
import os
import shutil
import tarfile
import xml


from zvmsdk import client as zvmclient
from zvmsdk import constants as const
from zvmsdk import exception
from zvmsdk import utils as zvmutils
from zvmsdk import config
from zvmsdk.tests.unit import base

CONF = config.CONF


class SDKZVMClientTestCase(base.SDKTestCase):
    def setUp(self):
        super(SDKZVMClientTestCase, self).setUp()
        self._zvmclient = zvmclient.get_zvmclient()
        self._xcat_url = zvmutils.get_xcat_url()

    def test_get_zvmclient(self):
        if CONF.zvm.client_type == 'xcat':
            self.assertTrue(isinstance(self._zvmclient, zvmclient.XCATClient))


class SDKXCATCientTestCases(SDKZVMClientTestCase):
    """Test cases for xcat zvm client."""

    def setUp(self):
        super(SDKXCATCientTestCases, self).setUp()

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_power_state(self, xrequest):
        fake_userid = 'fake_userid'
        fake_url = self._xcat_url.rpower('/' + fake_userid)
        fake_body = ['on']
        self._zvmclient._power_state(fake_userid, 'PUT', 'on')
        xrequest.assert_called_once_with('PUT', fake_url, fake_body)

    @mock.patch.object(zvmclient.XCATClient, '_power_state')
    def test_guest_start(self, power_state):
        fake_userid = 'fake_userid'
        self._zvmclient.guest_start(fake_userid)
        power_state.assert_called_once_with(fake_userid, 'PUT', 'on')

    @mock.patch.object(zvmclient.XCATClient, '_power_state')
    def test_guest_stop(self, power_state):
        fake_userid = 'fakeuser'
        self._zvmclient.guest_stop(fake_userid)
        power_state.assert_called_once_with(fake_userid, 'PUT', 'off')

    @mock.patch.object(zvmclient.XCATClient, '_power_state')
    def test_get_power_state(self, power_state):
        fake_userid = 'fake_userid'
        fake_ret = {'info': [[fake_userid + ': on\n']],
                    'node': [],
                    'errocode': [],
                    'data': []}
        power_state.return_value = fake_ret
        ret = self._zvmclient.get_power_state(fake_userid)

        power_state.assert_called_once_with(fake_userid, 'GET', 'stat')
        self.assertEqual('on', ret)

    def _fake_host_rinv_info(self):
        fake_host_rinv_info = ["fakenode: z/VM Host: FAKENODE\n"
                               "fakenode: zHCP: fakehcp.fake.com\n"
                               "fakenode: CEC Vendor: FAKE\n"
                               "fakenode: CEC Model: 2097\n"
                               "fakenode: Hypervisor OS: z/VM 6.1.0\n"
                               "fakenode: Hypervisor Name: fakenode\n"
                               "fakenode: Architecture: s390x\n"
                               "fakenode: LPAR CPU Total: 10\n"
                               "fakenode: LPAR CPU Used: 10\n"
                               "fakenode: LPAR Memory Total: 16G\n"
                               "fakenode: LPAR Memory Offline: 0\n"
                               "fakenode: LPAR Memory Used: 16.0G\n"
                               "fakenode: IPL Time:"
                               "IPL at 03/13/14 21:43:12 EDT\n"]
        return {'info': [fake_host_rinv_info, ]}

    def _fake_disk_info(self):
        fake_disk_info = ["fakenode: FAKEDP Total: 406105.3 G\n"
                          "fakenode: FAKEDP Used: 367262.6 G\n"
                          "fakenode: FAKEDP Free: 38842.7 G\n"]
        return {'info': [fake_disk_info, ]}

    @mock.patch.object(zvmclient.XCATClient, '_construct_zhcp_info')
    @mock.patch.object(zvmutils, 'xcat_request')
    def test_get_host_info(self, xrequest, _construct_zhcp_info):
        xrequest.return_value = self._fake_host_rinv_info()
        fake_zhcp_info = {'hostname': 'fakehcp.fake.com',
                          'nodename': 'fakehcp',
                          'userid': 'fakehcp'}
        _construct_zhcp_info.return_value = fake_zhcp_info
        host_info = self._zvmclient.get_host_info()
        self.assertEqual(host_info['zvm_host'], "FAKENODE")
        self.assertEqual(self._zvmclient._zhcp_info, fake_zhcp_info)
        url = "/xcatws/nodes/" + CONF.zvm.host +\
                "/inventory?userName=" + CONF.xcat.username +\
                "&password=" + CONF.xcat.password +\
                "&format=json"
        xrequest.assert_called_once_with('GET', url)
        _construct_zhcp_info.assert_called_once_with("fakehcp.fake.com")

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_get_diskpool_info(self, xrequest):
        xrequest.return_value = self._fake_disk_info()
        dp_info = self._zvmclient.get_diskpool_info('FAKEDP')
        url = "/xcatws/nodes/" + CONF.zvm.host +\
                "/inventory?userName=" + CONF.xcat.username +\
                "&password=" + CONF.xcat.password +\
                "&format=json&field=--diskpoolspace&field=FAKEDP"
        xrequest.assert_called_once_with('GET', url)
        self.assertEqual(dp_info['disk_total'], "406105.3 G")
        self.assertEqual(dp_info['disk_used'], "367262.6 G")
        self.assertEqual(dp_info['disk_available'], "38842.7 G")

    @mock.patch.object(zvmclient.XCATClient, 'get_host_info')
    @mock.patch.object(zvmclient.XCATClient, '_construct_zhcp_info')
    def test_get_hcp_info(self, _construct_zhcp_info, get_host_info):
        self._zvmclient._get_hcp_info()
        get_host_info.assert_called_once_with()
        self._zvmclient._get_hcp_info("fakehcp.fake.com")
        _construct_zhcp_info.assert_called_once_with("fakehcp.fake.com")

    @mock.patch.object(zvmutils, 'get_userid')
    def test_construct_zhcp_info(self, get_userid):
        get_userid.return_value = "fkuserid"
        hcp_info = self._zvmclient._construct_zhcp_info("fakehcp.fake.com")
        get_userid.assert_called_once_with("fakehcp")
        self.assertEqual(hcp_info['hostname'], "fakehcp.fake.com")
        self.assertEqual(hcp_info['nodename'], "fakehcp")
        self.assertEqual(hcp_info['userid'], "fkuserid")

    def _fake_vm_list(self):
        vm_list = ['#node,hcp,userid,nodetype,parent,comments,disable',
                     '"fakehcp","fakehcp.fake.com","HCP","vm","fakenode"',
                     '"fakenode","fakehcp.fake.com",,,,,',
                     '"os000001","fakehcp.fake.com","OS000001",,,,']
        return vm_list

    @mock.patch.object(zvmutils, 'xcat_request')
    @mock.patch.object(zvmclient.XCATClient, '_get_hcp_info')
    def test_get_vm_list(self, _get_hcp_info, xrequest):
        _get_hcp_info.return_value = {'hostname': "fakehcp.fake.com",
                                     'nodename': "fakehcp",
                                     'userid': "fakeuserid"}
        fake_vm_list = self._fake_vm_list()
        fake_vm_list.append('"xcat","fakexcat.fake.com",,,,,')
        xrequest.return_value = {'data': [fake_vm_list, ]}
        vm_list = self._zvmclient.get_vm_list()
        self.assertIn("os000001", vm_list)
        self.assertNotIn("xcat", vm_list)
        self.assertNotIn("fakehcp", vm_list)
        url = "/xcatws/tables/zvm?userName=" +\
                CONF.xcat.username + "&password=" +\
                CONF.xcat.password + "&format=json"
        xrequest.assert_called_once_with("GET", url)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_delete_mac(self, xrequest):
        xrequest.return_value = {"data": ["fakereturn"]}
        url = "/xcatws/tables/mac?userName=" +\
                CONF.xcat.username + "&password=" +\
                CONF.xcat.password + "&format=json"
        commands = "-d node=fakenode mac"
        body = [commands]

        info = self._zvmclient._delete_mac("fakenode")
        xrequest.assert_called_once_with("PUT", url, body)
        self.assertEqual(info[0], "fakereturn")

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_delete_mac_fail(self, xrequest):
        xrequest.side_effect = exception.ZVMNetworkError(msg='msg')
        self.assertRaises(exception.ZVMNetworkError,
                          self._zvmclient._delete_mac, 'fakenode')

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_delete_switch(self, xrequest):
        xrequest.return_value = {"data": ["fakereturn"]}
        url = "/xcatws/tables/switch?userName=" +\
                CONF.xcat.username + "&password=" +\
                CONF.xcat.password + "&format=json"
        commands = "-d node=fakenode switch"
        body = [commands]

        info = self._zvmclient._delete_switch("fakenode")
        xrequest.assert_called_once_with("PUT", url, body)
        self.assertEqual(info[0], "fakereturn")

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_delete_switch_fail(self, xrequest):
        xrequest.side_effect = exception.ZVMNetworkError(msg='msg')
        self.assertRaises(exception.ZVMNetworkError,
                          self._zvmclient._delete_switch, 'fakenode')

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_delete_host(self, xrequest):
        xrequest.return_value = {"data": ["fakereturn"]}
        url = "/xcatws/tables/hosts?userName=" +\
                CONF.xcat.username + "&password=" +\
                CONF.xcat.password + "&format=json"
        commands = "-d node=fakenode hosts"
        body = [commands]

        info = self._zvmclient._delete_host("fakenode")
        xrequest.assert_called_once_with("PUT", url, body)
        self.assertEqual(info[0], "fakereturn")

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_delete_host_fail(self, xrequest):
        xrequest.side_effect = exception.ZVMNetworkError(msg='msg')
        self.assertRaises(exception.ZVMNetworkError,
                          self._zvmclient._delete_host, 'fakenode')

    @mock.patch('zvmsdk.client.XCATClient.image_performance_query')
    def test_get_image_performance_info(self, ipq):
        ipq.return_value = {
            u'FAKEVM': {
                'used_memory': u'5222192 KB',
                'used_cpu_time': u'25640530229 uS',
                'guest_cpus': u'2',
                'userid': u'FKAEVM',
                'max_memory': u'8388608 KB'}}
        info = self._zvmclient.get_image_performance_info('fakevm')
        self.assertEqual(info['used_memory'], '5222192 KB')

    @mock.patch('zvmsdk.client.XCATClient.image_performance_query')
    def test_get_image_performance_info_not_exist(self, ipq):
        ipq.return_value = {}
        info = self._zvmclient.get_image_performance_info('fakevm')
        self.assertEqual(info, None)

    @mock.patch('zvmsdk.utils.xdsh')
    def test_image_performance_query_single(self, dsh):
        dsh.return_value = {
            'info': [], 'node': [], 'errorcode': [[u'0']],
            'data': [['zhcp2: Number of virtual server IDs: 1 \n'
                      'zhcp2: Virtual server ID: fakevm\n'
                      'zhcp2: Record version: "1"\n'
                      'zhcp2: Guest flags: "0"\n'
                      'zhcp2: Used CPU time: "26238001893 uS"\n'
                      'zhcp2: Elapsed time: "89185770400 uS"\n'
                      'zhcp2: Minimum memory: "0 KB"\n'
                      'zhcp2: Max memory: "8388608 KB"\n'
                      'zhcp2: Shared memory: "5222192 KB"\n'
                      'zhcp2: Used memory: "5222184 KB"\n'
                      'zhcp2: Active CPUs in CEC: "44"\n'
                      'zhcp2: Logical CPUs in VM: "6"\n'
                      'zhcp2: Guest CPUs: "2"\nz'
                      'hcp2: Minimum CPU count: "2"\n'
                      'zhcp2: Max CPU limit: "10000"\n'
                      'zhcp2: Processor share: "100"\n'
                      'zhcp2: Samples CPU in use: "16659"\n'
                      'zhcp2: ,Samples CPU delay: "638"\n'
                      'zhcp2: Samples page wait: "0"\n'
                      'zhcp2: Samples idle: "71550"\n'
                      'zhcp2: Samples other: "337"\n'
                      'zhcp2: Samples total: "89184"\n'
                      'zhcp2: Guest name: "FAKEVM  "', None]], 'error': []}
        pi_info = self._zvmclient.image_performance_query('fakevm')
        self.assertEqual(pi_info['FAKEVM']['used_memory'], "5222184 KB")
        self.assertEqual(pi_info['FAKEVM']['used_cpu_time'], "26238001893 uS")
        self.assertEqual(pi_info['FAKEVM']['elapsed_cpu_time'],
                         "89185770400 uS")
        self.assertEqual(pi_info['FAKEVM']['min_cpu_count'], "2")
        self.assertEqual(pi_info['FAKEVM']['max_cpu_limit'], "10000")
        self.assertEqual(pi_info['FAKEVM']['samples_cpu_in_use'], "16659")
        self.assertEqual(pi_info['FAKEVM']['samples_cpu_delay'], "638")
        self.assertEqual(pi_info['FAKEVM']['guest_cpus'], "2")
        self.assertEqual(pi_info['FAKEVM']['userid'], "FAKEVM")
        self.assertEqual(pi_info['FAKEVM']['max_memory'], "8388608 KB")

    @mock.patch('zvmsdk.utils.xdsh')
    def test_image_performance_query_multiple(self, dsh):
        dsh.return_value = {
            'info': [], 'node': [], 'errorcode': [[u'0']],
            'data': [['zhcp2: Number of virtual server IDs: 2 \n'
                      'zhcp2: Virtual server ID: fakevm\n'
                      'zhcp2: Record version: "1"\n'
                      'zhcp2: Guest flags: "0"\n'
                      'zhcp2: Used CPU time: "26238001893 uS"\n'
                      'zhcp2: Elapsed time: "89185770400 uS"\n'
                      'zhcp2: Minimum memory: "0 KB"\n'
                      'zhcp2: Max memory: "8388608 KB"\n'
                      'zhcp2: Shared memory: "5222192 KB"\n'
                      'zhcp2: Used memory: "5222184 KB"\n'
                      'zhcp2: Active CPUs in CEC: "44"\n'
                      'zhcp2: Logical CPUs in VM: "6"\n'
                      'zhcp2: Guest CPUs: "2"\nz'
                      'hcp2: Minimum CPU count: "2"\n'
                      'zhcp2: Max CPU limit: "10000"\n'
                      'zhcp2: Processor share: "100"\n'
                      'zhcp2: Samples CPU in use: "16659"\n'
                      'zhcp2: ,Samples CPU delay: "638"\n'
                      'zhcp2: Samples page wait: "0"\n'
                      'zhcp2: Samples idle: "71550"\n'
                      'zhcp2: Samples other: "337"\n'
                      'zhcp2: Samples total: "89184"\n'
                      'zhcp2: Guest name: "FAKEVM  "\n'
                      'zhcp2: \n'
                      'zhcp2: Virtual server ID: fakevm2\n'
                      'zhcp2: Record version: "1"\n'
                      'zhcp2: Guest flags: "0"\n'
                      'zhcp2: Used CPU time: "26238001893 uS"\n'
                      'zhcp2: Elapsed time: "89185770400 uS"\n'
                      'zhcp2: Minimum memory: "0 KB"\n'
                      'zhcp2: Max memory: "8388608 KB"\n'
                      'zhcp2: Shared memory: "5222192 KB"\n'
                      'zhcp2: Used memory: "5222184 KB"\n'
                      'zhcp2: Active CPUs in CEC: "44"\n'
                      'zhcp2: Logical CPUs in VM: "6"\n'
                      'zhcp2: Guest CPUs: "1"\nz'
                      'hcp2: Minimum CPU count: "1"\n'
                      'zhcp2: Max CPU limit: "10000"\n'
                      'zhcp2: Processor share: "100"\n'
                      'zhcp2: Samples CPU in use: "16659"\n'
                      'zhcp2: ,Samples CPU delay: "638"\n'
                      'zhcp2: Samples page wait: "0"\n'
                      'zhcp2: Samples idle: "71550"\n'
                      'zhcp2: Samples other: "337"\n'
                      'zhcp2: Samples total: "89184"\n'
                      'zhcp2: Guest name: "FAKEVM2 "\n', None]], 'error': []}
        pi_info = self._zvmclient.image_performance_query(['fakevm',
                                                            'fakevm2'])
        self.assertEqual(pi_info['FAKEVM']['used_memory'], "5222184 KB")
        self.assertEqual(pi_info['FAKEVM']['used_cpu_time'], "26238001893 uS")
        self.assertEqual(pi_info['FAKEVM']['elapsed_cpu_time'],
                         "89185770400 uS")
        self.assertEqual(pi_info['FAKEVM']['min_cpu_count'], "2")
        self.assertEqual(pi_info['FAKEVM']['max_cpu_limit'], "10000")
        self.assertEqual(pi_info['FAKEVM']['samples_cpu_in_use'], "16659")
        self.assertEqual(pi_info['FAKEVM']['samples_cpu_delay'], "638")
        self.assertEqual(pi_info['FAKEVM']['guest_cpus'], "2")
        self.assertEqual(pi_info['FAKEVM']['userid'], "FAKEVM")
        self.assertEqual(pi_info['FAKEVM']['max_memory'], "8388608 KB")
        self.assertEqual(pi_info['FAKEVM2']['used_memory'], "5222184 KB")
        self.assertEqual(pi_info['FAKEVM2']['used_cpu_time'], "26238001893 uS")
        self.assertEqual(pi_info['FAKEVM2']['elapsed_cpu_time'],
                         "89185770400 uS")
        self.assertEqual(pi_info['FAKEVM2']['min_cpu_count'], "1")
        self.assertEqual(pi_info['FAKEVM2']['max_cpu_limit'], "10000")
        self.assertEqual(pi_info['FAKEVM2']['samples_cpu_in_use'], "16659")
        self.assertEqual(pi_info['FAKEVM2']['samples_cpu_delay'], "638")
        self.assertEqual(pi_info['FAKEVM2']['guest_cpus'], "1")
        self.assertEqual(pi_info['FAKEVM2']['userid'], "FAKEVM2")
        self.assertEqual(pi_info['FAKEVM2']['max_memory'], "8388608 KB")

    @mock.patch('zvmsdk.utils.xdsh')
    def test_image_performance_query_err1(self, dsh):
        dsh.return_value = {}
        self.assertRaises(exception.ZVMInvalidXCATResponseDataError,
                          self._zvmclient.image_performance_query, 'fakevm')

    @mock.patch('zvmsdk.utils.xdsh')
    def test_image_performance_query_err2(self, dsh):
        dsh.return_value = {'data': [[]]}
        self.assertRaises(exception.ZVMInvalidXCATResponseDataError,
                          self._zvmclient.image_performance_query, 'fakevm')

    @mock.patch('zvmsdk.utils.xdsh')
    def test_image_performance_query_err3(self, dsh):
        dsh.return_value = {
            'info': [], 'node': [], 'errorcode': [[u'0']],
            'data': [['zhcp2: Number of virtual server IDs: 1 ', None]],
            'error': []}
        pi_info = self._zvmclient.image_performance_query('fakevm')
        self.assertEqual(pi_info, {})

    @mock.patch.object(zvmclient.XCATClient, '_add_switch_table_record')
    @mock.patch.object(zvmclient.XCATClient, '_add_mac_table_record')
    @mock.patch.object(zvmclient.XCATClient, '_delete_mac')
    @mock.patch.object(zvmutils, 'xcat_request')
    def test_create_nic(self, xrequest, _delete_mac,
                         _add_mac, _add_switch):
        self._zvmclient._create_nic("fakenode", "fake_nic",
                                    "00:00:00:12:34:56", "fake_vdev",
                                    "fakehcp")
        _delete_mac.assert_called_once_with("fakenode")
        _add_mac.assert_called_once_with("fakenode", "fake_vdev",
                                         "00:00:00:12:34:56", "fakehcp")
        _add_switch.assert_called_once_with("fakenode", "fake_nic",
                                            "fake_vdev", "fakehcp")

        url = self._xcat_url.chvm('/fakenode')
        commands = ' '.join((
            'Image_Definition_Update_DM -T %userid%',
            '-k \'NICDEF=VDEV=fake_vdev TYPE=QDIO',
            'MACID=123456\''))
        body = ['--smcli', commands]

        xrequest.assert_called_once_with("PUT", url, body)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_add_mac_table_record(self, xrequest):
        xrequest.return_value = {"data": ["fakereturn"]}
        url = "/xcatws/tables/mac?userName=" +\
                CONF.xcat.username + "&password=" +\
                CONF.xcat.password + "&format=json"
        commands = "mac.node=fakenode" + " mac.mac=00:00:00:00:00:00"
        commands += " mac.interface=fake"
        commands += " mac.comments=fakezhcp"
        body = [commands]

        info = self._zvmclient._add_mac_table_record("fakenode", "fake",
                                                     "00:00:00:00:00:00",
                                                     "fakezhcp")
        xrequest.assert_called_once_with("PUT", url, body)
        self.assertEqual(info[0], "fakereturn")

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_add_mac_table_record_fail(self, xrequest):
        xrequest.side_effect = exception.ZVMNetworkError(msg='msg')
        self.assertRaises(exception.ZVMNetworkError,
                          self._zvmclient._add_mac_table_record,
                          "fakenode", "fake",
                          "00:00:00:00:00:00", "fakezhcp")

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_add_switch_table_record(self, xrequest):
        xrequest.return_value = {"data": ["fakereturn"]}
        url = "/xcatws/tables/switch?userName=" +\
                CONF.xcat.username + "&password=" +\
                CONF.xcat.password + "&format=json"
        commands = "switch.node=fakenode" + " switch.port=fake-port"
        commands += " switch.interface=fake"
        commands += " switch.comments=fakezhcp"
        body = [commands]

        info = self._zvmclient._add_switch_table_record("fakenode",
                                                        "fake-port",
                                                        "fake",
                                                        "fakezhcp")
        xrequest.assert_called_once_with("PUT", url, body)
        self.assertEqual(info[0], "fakereturn")

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_add_switch_table_record_fail(self, xrequest):
        xrequest.side_effect = exception.ZVMNetworkError(msg='msg')
        self.assertRaises(exception.ZVMNetworkError,
                          self._zvmclient._add_switch_table_record,
                          "fakenode", "fake-port",
                          "fake", "fakezhcp")

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_update_vm_info(self, xrequest):
        node = 'fakenode'
        node_info = ['sles12', 's390x', 'netboot',
                     '0a0c576a_157f_42c8_2a254d8b77f']
        url = "/xcatws/nodes/fakenode?userName=" + CONF.xcat.username +\
              "&password=" + CONF.xcat.password +\
              "&format=json"
        self._zvmclient._update_vm_info(node, node_info)
        xrequest.assert_called_with('PUT', url,
                ['noderes.netboot=zvm',
                 'nodetype.os=sles12',
                 'nodetype.arch=s390x',
                 'nodetype.provmethod=netboot',
                 'nodetype.profile=0a0c576a_157f_42c8_2a254d8b77f'])

    @mock.patch.object(zvmutils, 'xcat_request')
    @mock.patch.object(zvmclient.XCATClient, '_update_vm_info')
    def test_guest_deploy(self, _update_vm_info, xrequest):
        node = "testnode"
        image_name = "sles12-s390x-netboot-0a0c576a_157f_42c8_2a254d8b77fc"
        transportfiles = '/tmp/transport.tgz'

        url = "/xcatws/nodes/testnode/bootstate?userName=" +\
                CONF.xcat.username +\
               "&password=" + CONF.xcat.password +\
               "&format=json"
        self._zvmclient.guest_deploy(node, image_name, transportfiles)
        _update_vm_info.assert_called_with('testnode',
            ['sles12', 's390x', 'netboot', '0a0c576a_157f_42c8_2a254d8b77fc'])

        xrequest.assert_called_with('PUT', url,
            ['netboot', 'device=0100',
             'osimage=sles12-s390x-netboot-0a0c576a_157f_42c8_2a254d8b77fc',
             'transport=/tmp/transport.tgz'])

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_private_power_state(self, xreq):
        expt = {'info': [[u'fakeid: on\n']]}
        expt_url = ('/xcatws/nodes/fakeid/power?userName=%(uid)s&password='
                    '%(pwd)s&format=json' % {'uid': CONF.xcat.username,
                                             'pwd': CONF.xcat.password})
        xreq.return_value = expt
        resp = self._zvmclient._power_state('fakeid', 'GET', 'state')
        xreq.assert_called_once_with('GET', expt_url, ['state'])
        self.assertEqual(resp, expt)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_private_power_state_invalid_node(self, xreq):
        xreq.side_effect = exception.ZVMXCATRequestFailed(xcatserver='xcat',
            msg='error: Invalid nodes and/or groups: fakenode')
        self.assertRaises(exception.ZVMVirtualMachineNotExist,
            self._zvmclient._power_state, 'fakeid', 'GET', ['state'])

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_lsdef(self, xrequest):
        fake_userid = 'fake_userid'
        fake_url = self._xcat_url.lsdef_node('/' + fake_userid)
        self._zvmclient._lsdef(fake_userid)
        xrequest.assert_called_once_with('GET', fake_url)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_lsvm(self, xrequest):
        fake_userid = 'fake_userid'
        fake_resp = {'info': [[fake_userid]],
                    'node': [],
                    'errocode': [],
                    'data': []}
        xrequest.return_value = fake_resp
        ret = self._zvmclient._lsvm(fake_userid)
        self.assertEqual(ret[0], fake_userid)

    def test_get_node_status(self):
        # TODO:moving to vmops and change name to ''
        pass

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_create_xcat_node(self, xrequest):
        fake_userid = 'userid'
        fake_url = self._xcat_url.mkdef('/' + fake_userid)
        fake_body = ['userid=%s' % fake_userid,
                'hcp=%s' % CONF.xcat.zhcp,
                'mgt=zvm',
                'groups=%s' % const.ZVM_XCAT_GROUP]

        self._zvmclient.create_xcat_node(fake_userid)
        xrequest.assert_called_once_with("POST", fake_url, fake_body)

    def test_prepare_for_spawn(self):
        pass

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_remove_image_file(self, xrequest):
        fake_image_name = 'fake_image_name'
        fake_url = self._xcat_url.rmimage('/' + fake_image_name)
        self._zvmclient.remove_image_file(fake_image_name)

        xrequest.assert_called_once_with('DELETE', fake_url)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_remove_image_definition(self, xrequest):
        fake_image_name = 'fake_image_name'
        fake_url = self._xcat_url.rmobject('/' + fake_image_name)

        self._zvmclient.remove_image_definition(fake_image_name)
        xrequest.assert_called_once_with('DELETE', fake_url)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_change_vm_ipl_state(self, xrequest):
        fake_userid = 'fake_userid'
        fake_state = 0100
        fake_body = ['--setipl %s' % fake_state]
        fake_url = self._xcat_url.chvm('/' + fake_userid)

        self._zvmclient.change_vm_ipl_state(fake_userid, fake_state)
        xrequest.assert_called_once_with('PUT', fake_url, fake_body)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_change_vm_fmt(self, xrequest):
        fake_userid = 'fake_userid'
        fmt = False
        action = ''
        diskpool = ''
        vdev = ''
        size = '1000M'
        fake_url = self._xcat_url.chvm('/' + fake_userid)
        fake_body = [" ".join([action, diskpool, vdev, size])]

        self._zvmclient.change_vm_fmt(fake_userid, fmt, action,
                                      diskpool, vdev, size)
        xrequest.assert_called_once_with('PUT', fake_url, fake_body)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_get_tabdum_info(self, xrequest):
        fake_url = self._xcat_url.tabdump('/zvm')

        self._zvmclient.get_tabdump_info()
        xrequest.assert_called_once_with('GET', fake_url)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_do_capture(self, xrequest):
        fake_url = self._xcat_url.capture()
        fake_nodename = 'nodename'
        fake_profile = 'profiiiillle'
        fake_body = ['nodename=' + fake_nodename,
                     'profile=' + fake_profile]

        self._zvmclient.do_capture(fake_nodename, fake_profile)
        xrequest.assert_called_once_with('POST', fake_url, fake_body)

    def test_check_space_imgimport_xcat(self):
        pass

    def test_export_image(self):
        pass

    @mock.patch.object(zvmutils, 'xcat_request')
    @mock.patch.object(zvmutils, 'get_host')
    @mock.patch.object(os, 'remove')
    def test_image_import(self, remove_file, get_host, xrequest):
        image_bundle_package = 'asdfe'
        image_profile = 'imagep_prooooffffille'
        remote_host_info = {}
        get_host.return_value = remote_host_info
        fake_url = self._xcat_url.imgimport()
        fake_body = ['osimage=%s' % image_bundle_package,
                     'profile=%s' % image_profile,
                     'remotehost=%s' % remote_host_info,
                     'nozip']
        remove_file.return_value = None

        self._zvmclient.image_import(image_bundle_package, image_profile)
        xrequest.assert_called_once_with('POST', fake_url, fake_body)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_get_vm_nic_switch_info(self, xrequest):
        url = "/xcatws/tables/switch?userName=" +\
                CONF.xcat.username +\
               "&password=" + CONF.xcat.password +\
               "&format=json"
        self._zvmclient.get_vm_nic_switch_info("fakenode")
        xrequest.assert_called_with('GET', url)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_add_host_table_record(self, xrequest):
        commands = "node=fakeid" + " hosts.ip=fakeip"
        commands += " hosts.hostnames=fakehost"
        body = [commands]
        url = "/xcatws/tables/hosts?userName=" +\
                CONF.xcat.username + "&password=" +\
                CONF.xcat.password + "&format=json"

        self._zvmclient._add_host_table_record("fakeid", "fakeip", "fakehost")
        xrequest.assert_called_once_with("PUT", url, body)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_add_host_table_record_fail(self, xrequest):
        xrequest.side_effect = exception.ZVMNetworkError(msg='msg')
        self.assertRaises(exception.ZVMNetworkError,
                          self._zvmclient._add_host_table_record,
                          "fakeid", "fakeip", "fakehost")

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_makehost(self, xrequest):
        url = "/xcatws/networks/makehosts?userName=" +\
                CONF.xcat.username + "&password=" +\
                CONF.xcat.password + "&format=json"

        self._zvmclient._makehost()
        xrequest.assert_called_once_with("PUT", url)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_makehost_fail(self, xrequest):
        xrequest.side_effect = exception.ZVMNetworkError(msg='msg')
        self.assertRaises(exception.ZVMNetworkError,
                          self._zvmclient._makehost)

    @mock.patch.object(zvmclient.XCATClient, '_makehost')
    @mock.patch.object(zvmclient.XCATClient, '_add_host_table_record')
    @mock.patch.object(zvmclient.XCATClient, '_config_xcat_mac')
    def test_preset_vm_network(self, config_mac, add_host, makehost):
        self._zvmclient._preset_vm_network("fakeid", "fakeip")
        config_mac.assert_called_with("fakeid")
        add_host.assert_called_with("fakeid", "fakeip", "fakeid")
        makehost.assert_called_with()

    @mock.patch.object(zvmclient.XCATClient, '_add_mac_table_record')
    def test_config_xcat_mac(self, add_mac):
        self._zvmclient._config_xcat_mac("fakeid")
        add_mac.assert_called_with("fakeid", "fake", "00:00:00:00:00:00")

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_get_nic_ids(self, xrequest):
        xrequest.return_value = {"data": [["test1", "test2"]]}
        url = "/xcatws/tables/switch?userName=" +\
                CONF.xcat.username +\
               "&password=" + CONF.xcat.password +\
               "&format=json"
        info = self._zvmclient._get_nic_ids()
        xrequest.assert_called_with('GET', url)
        self.assertEqual(info[0], "test2")

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_get_userid_from_node(self, xrequest):
        xrequest.return_value = {"data": ["fake"]}
        url = "/xcatws/tables/zvm?userName=" +\
                CONF.xcat.username +\
               "&password=" + CONF.xcat.password +\
               "&format=json" +\
               "&col=node&value=fakenode&attribute=userid"
        info = self._zvmclient._get_userid_from_node("fakenode")
        xrequest.assert_called_with('GET', url)
        self.assertEqual(info, xrequest.return_value['data'][0][0])

    @mock.patch.object(zvmclient.XCATClient, '_get_userid_from_node')
    @mock.patch.object(zvmutils, 'xcat_request')
    def test_get_nic_settings(self, xrequest, get_userid_from_node):
        xrequest.return_value = {"data": [["fake"]]}
        url = "/xcatws/tables/switch?userName=" +\
                CONF.xcat.username +\
               "&password=" + CONF.xcat.password +\
               "&format=json" +\
               "&col=port&value=fakeport&attribute=node"
        self._zvmclient._get_nic_settings("fakeport")
        xrequest.assert_called_once_with('GET', url)
        get_userid_from_node.assert_called_once_with("fake")

    @mock.patch.object(zvmclient.XCATClient, '_get_nic_settings')
    def test_get_node_from_port(self, get_nic_settings):
        self._zvmclient._get_node_from_port("fakeport")
        get_nic_settings.assert_called_with("fakeport", get_node=True)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_grant_user_to_vswitch(self, xrequest):
        url = "/xcatws/nodes/" + CONF.xcat.zhcp_node +\
              "/dsh?userName=" + CONF.xcat.username +\
              "&password=" + CONF.xcat.password +\
              "&format=json"
        commands = '/opt/zhcp/bin/smcli Virtual_Network_Vswitch_Set_Extended'
        commands += " -T fakeuserid"
        commands += " -k switch_name=fakevs"
        commands += " -k grant_userid=fakeuserid"
        commands += " -k persist=YES"
        xdsh_commands = 'command=%s' % commands
        body = [xdsh_commands]

        self._zvmclient.grant_user_to_vswitch("fakevs", "fakeuserid")
        xrequest.assert_called_once_with("PUT", url, body)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_revoke_user_from_vswitch(self, xrequest):
        url = "/xcatws/nodes/" + CONF.xcat.zhcp_node +\
              "/dsh?userName=" + CONF.xcat.username +\
              "&password=" + CONF.xcat.password +\
              "&format=json"
        commands = '/opt/zhcp/bin/smcli Virtual_Network_Vswitch_Set_Extended'
        commands += " -T fakeuserid"
        commands += " -k switch_name=fakevs"
        commands += " -k revoke_userid=fakeuserid"
        commands += " -k persist=YES"
        xdsh_commands = 'command=%s' % commands
        body = [xdsh_commands]

        self._zvmclient.revoke_user_from_vswitch("fakevs", "fakeuserid")
        xrequest.assert_called_once_with("PUT", url, body)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_couple_nic(self, xrequest):
        url = "/xcatws/nodes/" + CONF.xcat.zhcp_node +\
              "/dsh?userName=" + CONF.xcat.username +\
               "&password=" + CONF.xcat.password +\
               "&format=json"
        commands = '/opt/zhcp/bin/smcli'
        commands += ' Virtual_Network_Adapter_Connect_Vswitch_DM'
        commands += " -T fakeuserid " + "-v fakecdev"
        commands += " -n fakevs"
        xdsh_commands = 'command=%s' % commands
        body1 = [xdsh_commands]

        commands = '/opt/zhcp/bin/smcli'
        commands += ' Virtual_Network_Adapter_Connect_Vswitch'
        commands += " -T fakeuserid " + "-v fakecdev"
        commands += " -n fakevs"
        xdsh_commands = 'command=%s' % commands
        body2 = [xdsh_commands]

        self._zvmclient._couple_nic("fakevs",
                                    "fakeuserid", "fakecdev", True)
        xrequest.assert_any_call("PUT", url, body1)
        xrequest.assert_any_call("PUT", url, body2)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_uncouple_nic(self, xrequest):
        url = "/xcatws/nodes/" + CONF.xcat.zhcp_node +\
              "/dsh?userName=" + CONF.xcat.username +\
               "&password=" + CONF.xcat.password +\
               "&format=json"
        commands = '/opt/zhcp/bin/smcli'
        commands += ' Virtual_Network_Adapter_Disconnect_DM'
        commands += " -T fakeuserid " + "-v fakecdev"
        xdsh_commands = 'command=%s' % commands
        body1 = [xdsh_commands]

        commands = '/opt/zhcp/bin/smcli'
        commands += ' Virtual_Network_Adapter_Disconnect'
        commands += " -T fakeuserid " + "-v fakecdev"
        xdsh_commands = 'command=%s' % commands
        body2 = [xdsh_commands]

        self._zvmclient._uncouple_nic("fakeuserid",
                                      "fakecdev", True)
        xrequest.assert_any_call("PUT", url, body1)
        xrequest.assert_any_call("PUT", url, body2)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_get_xcat_node_ip(self, xrequest):
        xrequest.return_value = {"data": [["fakeip"]]}
        url = "/xcatws/tables/site?userName=" +\
                CONF.xcat.username +\
               "&password=" + CONF.xcat.password +\
               "&format=json" +\
               "&col=key&value=master&attribute=value"

        info = self._zvmclient._get_xcat_node_ip()
        xrequest.assert_called_with("GET", url)
        self.assertEqual(info, "fakeip")

    @mock.patch.object(zvmclient.XCATClient, '_get_xcat_node_ip')
    @mock.patch.object(zvmutils, 'xcat_request')
    def test_get_xcat_node_name(self, xrequest, get_ip):
        get_ip.return_value = "fakeip"
        xrequest.return_value = {"data": [["fakename"]]}
        url = "/xcatws/tables/hosts?userName=" +\
              CONF.xcat.username +\
              "&password=" + CONF.xcat.password +\
              "&format=json" +\
              "&col=ip&value=fakeip&attribute=node"

        info = self._zvmclient._get_xcat_node_name()
        get_ip.assert_called_with()
        xrequest.assert_called_with("GET", url)
        self.assertEqual(info, "fakename")

    @mock.patch.object(zvmclient.XCATClient, '_get_zhcp_userid')
    @mock.patch.object(zvmutils, 'xcat_request')
    def test_get_vswitch_list(self, xrequest, get_userid):
        get_userid.return_value = "fakenode"
        xrequest.return_value = {
            "data": [[u"VSWITCH:  Name: TEST", u"VSWITCH:  Name: TEST2"]],
            "errorcode": [['0']]
                            }
        url = "/xcatws/nodes/" + CONF.xcat.zhcp_node +\
              "/dsh?userName=" + CONF.xcat.username +\
              "&password=" + CONF.xcat.password +\
              "&format=json"
        commands = ' '.join((
            '/opt/zhcp/bin/smcli Virtual_Network_Vswitch_Query',
            "-T fakenode",
            "-s \'*\'"))
        xdsh_commands = 'command=%s' % commands
        body = [xdsh_commands]
        info = self._zvmclient.get_vswitch_list()
        get_userid.assert_called_with()
        xrequest.assert_called_with("PUT", url, body)
        self.assertEqual(info[0], "TEST")
        self.assertEqual(info[1], "TEST2")

    @mock.patch.object(zvmclient.XCATClient, '_couple_nic')
    def test_couple_nic_to_vswitch(self, couple_nic):
        self._zvmclient.couple_nic_to_vswitch("fake_VS_name",
                                              "fakevdev",
                                              "fake_userid",
                                              True)
        couple_nic.assert_called_with("fake_VS_name",
                                      "fake_userid",
                                      "fakevdev", True)

    @mock.patch.object(zvmclient.XCATClient, '_uncouple_nic')
    def test_uncouple_nic_from_vswitch(self, uncouple_nic):
        self._zvmclient.uncouple_nic_from_vswitch("fake_VS_name",
                                                  "fakevdev",
                                                  "fake_userid",
                                                  True)
        uncouple_nic.assert_called_with("fake_userid",
                                        "fakevdev", True)

    @mock.patch.object(zvmclient.XCATClient, '_get_userid_from_node')
    def test_get_zhcp_userid(self, get_userid_from_node):
        self._zvmclient._get_zhcp_userid()
        get_userid_from_node.assert_called_with(CONF.xcat.zhcp_node)

    @mock.patch.object(zvmclient.XCATClient, '_get_zhcp_userid')
    @mock.patch.object(zvmutils, 'xcat_request')
    def test_check_vswitch_status(self, xrequest, get_zhcp_userid):
        get_zhcp_userid.return_value = "fakeuserid"
        xrequest.return_value = {
            "data": [["0"]],
            "errorcode": [['0']]
                            }
        url = "/xcatws/nodes/" + CONF.xcat.zhcp_node +\
              "/dsh?userName=" + CONF.xcat.username +\
              "&password=" + CONF.xcat.password +\
              "&format=json"

        commands = '/opt/zhcp/bin/smcli Virtual_Network_Vswitch_Query'
        commands += " -T fakeuserid"
        commands += " -s fakevsw"
        xdsh_commands = 'command=%s' % commands
        body = [xdsh_commands]

        self._zvmclient._check_vswitch_status("fakevsw")
        get_zhcp_userid.assert_called_with()
        xrequest.assert_called_with("PUT", url, body)

    @mock.patch.object(zvmclient.XCATClient, '_get_zhcp_userid')
    @mock.patch.object(zvmutils, 'xcat_request')
    def test_set_vswitch_rdev(self, xrequest, get_zhcp_userid):
        get_zhcp_userid.return_value = "fakeuserid"
        xrequest.return_value = {
            "data": [["0"]],
            "errorcode": [['0']]
                            }
        url = "/xcatws/nodes/" + CONF.xcat.zhcp_node +\
              "/dsh?userName=" + CONF.xcat.username +\
              "&password=" + CONF.xcat.password +\
              "&format=json"
        commands = '/opt/zhcp/bin/smcli Virtual_Network_Vswitch_Set_Extended'
        commands += ' -T fakeuserid'
        commands += ' -k switch_name=fakevsw'
        commands += ' -k real_device_address=fakerdev'
        xdsh_commands = 'command=%s' % commands
        body = [xdsh_commands]

        self._zvmclient._set_vswitch_rdev("fakevsw", "fakerdev")
        get_zhcp_userid.assert_called_with()
        xrequest.assert_called_with("PUT", url, body)

    @mock.patch.object(zvmclient.XCATClient, '_set_vswitch_rdev')
    @mock.patch.object(zvmclient.XCATClient, '_check_vswitch_status')
    @mock.patch.object(zvmclient.XCATClient, '_get_zhcp_userid')
    @mock.patch.object(zvmutils, 'xcat_request')
    def test_add_vswitch(self, xrequest, get_zhcp_userid,
                         check_vswitch_status, set_vswitch_rdev):
        check_vswitch_status.return_value = None
        get_zhcp_userid.return_value = "fakeuserid"
        xrequest.return_value = {
            "data": [["0"]],
            "errorcode": [['0']]
                            }
        url = "/xcatws/nodes/" + CONF.xcat.zhcp_node +\
              "/dsh?userName=" + CONF.xcat.username +\
              "&password=" + CONF.xcat.password +\
              "&format=json"
        commands = '/opt/zhcp/bin/smcli Virtual_Network_Vswitch_Create'
        commands += " -T fakeuserid"
        commands += ' -n fakename'
        commands += " -r fakerdev"
        commands += " -c 1"
        commands += " -q 8"
        commands += " -e 0"
        commands += " -t 2"
        commands += " -v 1"
        commands += " -p 1"
        commands += " -u 1"
        commands += " -G 2"
        commands += " -V 1"
        xdsh_commands = 'command=%s' % commands
        body = [xdsh_commands]

        self.assertRaises(exception.ZVMException,
                          self._zvmclient.add_vswitch,
                          "fakename", "fakerdev",
                          '*', 1, 8, 0, 2, 1, 1, 1, 2, 1)
        check_vswitch_status.assert_called_with("fakename")
        xrequest.assert_called_with("PUT", url, body)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_image_query_with_keyword(self, xrequest):
        xrequest.return_value = {'info':
            [[u'sles12-s390x-netboot-0a0c576a_157f_42c8_bde5  (osimage)']],
            'node': [],
            'errorcode': [],
            'data': [],
            'error': []}

        imagekeyword = '0a0c576a-157f-42c8-bde5'
        url = "/xcatws/images?userName=" + CONF.xcat.username +\
              "&password=" + CONF.xcat.password +\
              "&format=json&criteria=profile=~" + imagekeyword.replace('-',
                                                                       '_')
        image_list = [u'sles12-s390x-netboot-0a0c576a_157f_42c8_bde5']
        ret = self._zvmclient.image_query(imagekeyword)
        xrequest.assert_called_once_with("GET", url)
        self.assertEqual(ret, image_list)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_image_query_without_keyword(self, xrequest):
        xrequest.return_value = {'info':
            [[u'rhel7.2-s390x-netboot-eae09a9f_7958_4024_a58c  (osimage)',
              u'sles12-s390x-netboot-0a0c576a_157f_42c8_bde5  (osimage)']],
            'node': [],
            'errorcode': [],
            'data': [],
            'error': []}
        image_list = [u'rhel7.2-s390x-netboot-eae09a9f_7958_4024_a58c',
                      u'sles12-s390x-netboot-0a0c576a_157f_42c8_bde5']
        url = "/xcatws/images?userName=" + CONF.xcat.username +\
              "&password=" + CONF.xcat.password +\
              "&format=json"
        ret = self._zvmclient.image_query()
        xrequest.assert_called_once_with("GET", url)
        self.assertEqual(ret, image_list)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_get_user_console_output(self, xreq):
        log_str = 'fakeid: this is console log for fakeid\n'
        xreq.return_value = {'info': [[log_str]]}
        clog = self._zvmclient.get_user_console_output('fakeid', 100)
        self.assertEqual(clog, 'this is console log for fakeid\n')

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_get_user_console_output_invalid_output(self, xreq):
        xreq.return_value = {}
        self.assertRaises(exception.ZVMInvalidXCATResponseDataError,
                        self._zvmclient.get_user_console_output, 'fakeid', 100)

    def test_generate_vdev(self):
        base = '0100'
        idx = 1
        vdev = self._zvmclient._generate_vdev(base, idx)
        self.assertEqual(vdev, '0101')

    @mock.patch.object(zvmclient.XCATClient, 'aemod_handler')
    def test_process_additional_minidisks(self, aemod_handler):
        userid = 'inst001'
        disk_list = [{'vdev': '0101',
                      'format': 'ext3',
                      'mntdir': '/mnt/0101'}]
        vdev = '0101'
        fmt = 'ext3'
        mntdir = '/mnt/0101'
        func_name = 'setupDisk'
        parms = ' '.join([
                          'action=addMdisk',
                          'vaddr=' + vdev,
                          'filesys=' + fmt,
                          'mntdir=' + mntdir
                        ])
        parmline = ''.join(parms)
        self._zvmclient.process_additional_minidisks(userid, disk_list)
        aemod_handler.assert_called_with(userid, func_name, parmline)

    @mock.patch.object(zvmutils, 'xdsh')
    def test_unlock_userid(self, xdsh):
        userid = 'fakeuser'
        cmd = "/opt/zhcp/bin/smcli Image_Unlock_DM -T %s" % userid
        self._zvmclient.unlock_userid(userid)
        xdsh.assert_called_once_with(CONF.xcat.zhcp_node, cmd)

    @mock.patch.object(zvmutils, 'xdsh')
    def test_unlock_device(self, xdsh):
        userid = 'fakeuser'
        resp = {'data': [['Locked type: DEVICE\nDevice address: 0100\n'
                'Device locked by: fake\nDevice address: 0101\n'
                'Device locked by: fake']]}
        xdsh.side_effect = [resp, None, None]
        self._zvmclient.unlock_devices(userid)

        xdsh.assert_any_call(CONF.xcat.zhcp_node,
            '/opt/zhcp/bin/smcli Image_Lock_Query_DM -T fakeuser')
        xdsh.assert_any_call(CONF.xcat.zhcp_node,
            '/opt/zhcp/bin/smcli Image_Unlock_DM -T fakeuser -v 0100')
        xdsh.assert_any_call(CONF.xcat.zhcp_node,
            '/opt/zhcp/bin/smcli Image_Unlock_DM -T fakeuser -v 0101')

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_delete_xcat_node(self, xrequest):
        fake_userid = 'fakeuser'
        fake_url = self._xcat_url.rmdef('/' + fake_userid)

        self._zvmclient.delete_xcat_node(fake_userid)
        xrequest.assert_called_once_with('DELETE', fake_url)

    @mock.patch.object(zvmutils, 'xcat_request')
    @mock.patch.object(zvmclient.XCATClient, 'delete_xcat_node')
    def test_delete_userid_not_exist(self, delete_xcat_node, xrequest):
        fake_userid = 'fakeuser'
        fake_url = self._xcat_url.rmvm('/' + fake_userid)
        xrequest.side_effect = exception.ZVMXCATInternalError(
            'Return Code: 400\nReason Code: 4\n')

        self._zvmclient.delete_userid(fake_userid)
        xrequest.assert_called_once_with('DELETE', fake_url)
        delete_xcat_node.assert_called_once_with(fake_userid)

    @mock.patch.object(zvmclient.XCATClient, '_clean_network_resource')
    @mock.patch.object(zvmclient.XCATClient, 'delete_userid')
    def test_delete_vm(self, delete_userid, clean_net):
        fake_userid = 'fakeuser'
        self._zvmclient.delete_vm(fake_userid)
        delete_userid.assert_called_once_with(fake_userid)
        clean_net.assert_called_once_with(fake_userid)

    @mock.patch.object(zvmclient.XCATClient, '_clean_network_resource')
    @mock.patch.object(zvmclient.XCATClient, 'unlock_devices')
    @mock.patch.object(zvmclient.XCATClient, 'delete_userid')
    def test_delete_vm_with_locked_device(self, delete_userid, unlock_devices,
                                          clean_net):
        fake_userid = 'fakeuser'
        delete_userid.side_effect = [exception.ZVMXCATInternalError(
        'Return Code: 408\n Reason Code: 12\n'), None]

        self._zvmclient.delete_vm(fake_userid)
        delete_userid.assert_called_with(fake_userid)
        unlock_devices.assert_called_with(fake_userid)

    @mock.patch.object(zvmclient.XCATClient, '_clean_network_resource')
    @mock.patch.object(zvmclient.XCATClient, 'delete_userid')
    def test_delete_vm_node_not_exist(self, delete_userid, clean_net):
        fake_userid = 'fakeuser'
        delete_userid.side_effect = exception.ZVMXCATRequestFailed('msg')

        self.assertRaises(exception.ZVMXCATRequestFailed,
                          self._zvmclient.delete_vm, fake_userid)

    @mock.patch.object(xml.dom.minidom, 'Document')
    @mock.patch.object(xml.dom.minidom.Document, 'createElement')
    def test_generate_manifest_file(self, create_element, document):
        """
        image_meta = {
                u'id': 'image_uuid_123',
                u'properties': {u'image_type_xcat': u'linux',
                               u'os_version': u'rhel7.2',
                               u'os_name': u'Linux',
                               u'architecture': u's390x',
                             u'provision_metuot'}
                }
        image_name = 'image_name_123'
        tmp_date_dir = 'tmp_date_dir'
        disk_file_name = 'asdf'
        manifest_path = os.getcwd()
        manifest_path = manifest_path + '/' + tmp_date_dir
        """
        pass

    @mock.patch.object(os.path, 'exists')
    @mock.patch.object(tarfile, 'open')
    @mock.patch.object(tarfile.TarFile, 'add')
    @mock.patch.object(tarfile.TarFile, 'close')
    @mock.patch.object(shutil, 'copyfile')
    @mock.patch.object(os, 'chdir')
    def test_generate_image_bundle(self, change_dir,
                                   copy_file, close_file,
                                   add_file, tarfile_open,
                                   file_exist):
        time_stamp_dir = 'tmp_date_dir'
        image_name = 'test'
        spawn_path = '.'
        spawn_path = spawn_path + '/' + time_stamp_dir
        image_file_path = spawn_path + '/images/test.img'
        change_dir.return_value = None
        copy_file.return_value = None
        close_file.return_value = None
        add_file.return_value = None
        tarfile_open.return_value = tarfile.TarFile
        file_exist.return_value = True

        self._zvmclient.generate_image_bundle(
                                    spawn_path, time_stamp_dir,
                                    image_name, image_file_path)
        tarfile_open.assert_called_once_with(spawn_path +
                                             '/tmp_date_dir_test.tar',
                                             mode='w')

    @mock.patch.object(zvmclient.XCATClient, 'add_mdisks')
    @mock.patch.object(zvmutils, 'xcat_request')
    @mock.patch.object(zvmclient.XCATClient, 'prepare_for_spawn')
    def test_create_vm(self, prepare_for_spawn, xrequest, add_mdisks):
        user_id = 'fakeuser'
        cpu = 2
        memory = 1024
        disk_list = [{'size': '1g',
                      'is_boot_disk': True,
                      'disk_pool': 'ECKD:eckdpool1'}]
        profile = 'dfltprof'
        url = "/xcatws/vms/fakeuser?userName=" + CONF.xcat.username +\
            "&password=" + CONF.xcat.password +\
            "&format=json"
        body = ['profile=dfltprof',
                'password=%s' % CONF.zvm.user_default_password, 'cpu=2',
                'memory=1024m', 'privilege=G', 'ipl=0100']
        self._zvmclient.create_vm(user_id, cpu, memory, disk_list, profile)
        prepare_for_spawn.assert_called_once_with(user_id)
        xrequest.assert_called_once_with('POST', url, body)
        add_mdisks.assert_called_once_with(user_id, disk_list)

    @mock.patch.object(zvmclient.XCATClient, '_add_mdisk')
    def test_add_mdisks(self, add_mdisk):
        userid = 'fakeuser'
        disk_list = [{'size': '1g',
                      'is_boot_disk': True,
                      'disk_pool': 'ECKD:eckdpool1'},
                     {'size': '200000',
                      'disk_pool': 'FBA:fbapool1',
                      'format': 'ext3'}]
        self._zvmclient.add_mdisks(userid, disk_list)
        add_mdisk.assert_any_call(userid, disk_list[0], '0100')
        add_mdisk.assert_any_call(userid, disk_list[1], '0101')

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_add_mdisk(self, xrequest):
        userid = 'fakeuser'
        disk = {'size': '1g',
                'disk_pool': 'ECKD:eckdpool1',
                'format': 'ext3'}
        vdev = '0101'
        url = "/xcatws/vms/fakeuser?" + \
            "userName=" + CONF.xcat.username +\
            "&password=" + CONF.xcat.password + "&format=json"
        body = [" ".join(['--add3390', 'eckdpool1', vdev, '1g', "MR", "''",
                "''", "''", 'ext3'])]

        self._zvmclient._add_mdisk(userid, disk, vdev),
        xrequest.assert_called_once_with('PUT', url, body)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_set_vswitch_port_vlan_id(self, xrequest):
        url = "/xcatws/nodes/" + CONF.xcat.zhcp_node +\
              "/dsh?userName=" + CONF.xcat.username +\
              "&password=" + CONF.xcat.password +\
              "&format=json"
        commands = '/opt/zhcp/bin/smcli Virtual_Network_Vswitch_Set_Extended'
        commands += " -T userid"
        commands += ' -k grant_userid=userid'
        commands += " -k switch_name=vswitch_name"
        commands += " -k user_vlan_id=vlan_id"
        commands += " -k persist=YES"
        xdsh_commands = 'command=%s' % commands
        body = [xdsh_commands]

        self._zvmclient.set_vswitch_port_vlan_id("vswitch_name",
                                                 "userid",
                                                 "vlan_id")
        xrequest.assert_called_once_with("PUT", url, body)

    @mock.patch.object(zvmutils, 'xcat_request')
    def test_update_nic_definition(self, xrequest):
        url = "/xcatws/vms/node?userName=" + CONF.xcat.username +\
              "&password=" + CONF.xcat.password +\
              "&format=json"

        command = 'Image_Definition_Update_DM -T %userid%'
        command += ' -k \'NICDEF=VDEV=vdev TYPE=QDIO '
        command += 'MACID=mac '
        command += 'LAN=SYSTEM '
        command += 'SWITCHNAME=vswitch\''
        body = ['--smcli', command]

        self._zvmclient.update_nic_definition("node", "vdev",
                                              "mac", "vswitch")
        xrequest.assert_called_with("PUT", url, body)
