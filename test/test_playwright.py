# coding: utf-8
from __future__ import unicode_literals

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from haruhi_dl.compat import compat_str

from haruhi_dl.playwright import PlaywrightHelper


class TestPlaywright(unittest.TestCase):

    def test_import_nonfatal(self):
        PlaywrightHelper._import_pw(fatal=False)

    def test_import_fatal(self):
        helper = PlaywrightHelper
        try:
            helper._import_pw(fatal=True)
            self.assertIsNotNone(helper._pw)
            self.assertIsInstance(helper._pw_version, compat_str)
        except ImportError:
            self.assertIsNone(helper._pw)
            self.assertIsNone(helper._pw_version)

    def test_checking_version(self):
        version = PlaywrightHelper._version()
        self.assertIsInstance(version, (compat_str, None))


if __name__ == '__main__':
    unittest.main()
