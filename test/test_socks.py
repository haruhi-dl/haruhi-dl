#!/usr/bin/env python
# coding: utf-8
from __future__ import unicode_literals

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
import subprocess

from test.helper import (
    FakeHDL,
    get_params,
)
from haruhi_dl.compat import (
    compat_str,
    compat_urllib_request,
)


class TestMultipleSocks(unittest.TestCase):
    @staticmethod
    def _check_params(attrs):
        params = get_params()
        for attr in attrs:
            if attr not in params:
                print('Missing %s. Skipping.' % attr)
                return
        return params

    def test_proxy_http(self):
        params = self._check_params(['primary_proxy', 'primary_server_ip'])
        if params is None:
            return
        hdl = FakeHDL({
            'proxy': params['primary_proxy']
        })
        self.assertEqual(
            hdl.urlopen('http://ifconfig.me/ip').read().decode('utf-8'),
            params['primary_server_ip'])

    def test_proxy_https(self):
        params = self._check_params(['primary_proxy', 'primary_server_ip'])
        if params is None:
            return
        hdl = FakeHDL({
            'proxy': params['primary_proxy']
        })
        self.assertEqual(
            hdl.urlopen('https://ifconfig.me/ip').read().decode('utf-8'),
            params['primary_server_ip'])

    def test_secondary_proxy_http(self):
        params = self._check_params(['secondary_proxy', 'secondary_server_ip'])
        if params is None:
            return
        hdl = FakeHDL()
        req = compat_urllib_request.Request('http://ifconfig.me/ip')
        req.add_header('Ytdl-request-proxy', params['secondary_proxy'])
        self.assertEqual(
            hdl.urlopen(req).read().decode('utf-8'),
            params['secondary_server_ip'])

    def test_secondary_proxy_https(self):
        params = self._check_params(['secondary_proxy', 'secondary_server_ip'])
        if params is None:
            return
        hdl = FakeHDL()
        req = compat_urllib_request.Request('https://ifconfig.me/ip')
        req.add_header('Ytdl-request-proxy', params['secondary_proxy'])
        self.assertEqual(
            hdl.urlopen(req).read().decode('utf-8'),
            params['secondary_server_ip'])


class TestSocks(unittest.TestCase):
    _SKIP_SOCKS_TEST = True

    def setUp(self):
        if self._SKIP_SOCKS_TEST:
            return

        self.port = random.randint(20000, 30000)
        self.server_process = subprocess.Popen([
            'srelay', '-f', '-i', '127.0.0.1:%d' % self.port],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def tearDown(self):
        if self._SKIP_SOCKS_TEST:
            return

        self.server_process.terminate()
        self.server_process.communicate()

    def _get_ip(self, protocol):
        if self._SKIP_SOCKS_TEST:
            return '127.0.0.1'

        hdl = FakeHDL({
            'proxy': '%s://127.0.0.1:%d' % (protocol, self.port),
        })
        return hdl.urlopen('http://ifconfig.me/ip').read().decode('utf-8')

    def test_socks4(self):
        self.assertTrue(isinstance(self._get_ip('socks4'), compat_str))

    def test_socks4a(self):
        self.assertTrue(isinstance(self._get_ip('socks4a'), compat_str))

    def test_socks5(self):
        self.assertTrue(isinstance(self._get_ip('socks5'), compat_str))


if __name__ == '__main__':
    unittest.main()
