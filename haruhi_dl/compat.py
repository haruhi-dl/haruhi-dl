# coding: utf-8
from __future__ import unicode_literals

# this file used to help with handling various Python versions and implementations.
# we dropped support for Python <3.6 (and by this, for Jython and IronPython)
# so it's not needed anymore, but a lot of code is still referencing to these compat imports.

import base64
import ctypes
import getpass
import itertools
import os
import re
import shlex
import shutil
import socket
import struct
import sys
import xml.etree.ElementTree


import urllib.request as compat_urllib_request
import urllib.error as compat_urllib_error
import urllib.parse as compat_urllib_parse
from urllib.parse import urlparse as compat_urllib_parse_urlparse
import urllib.parse as compat_urlparse
import urllib.response as compat_urllib_response
import http.cookiejar as compat_cookiejar
compat_cookiejar_Cookie = compat_cookiejar.Cookie
import http.cookies as compat_cookies
compat_cookies_SimpleCookie = compat_cookies.SimpleCookie
import html.entities as compat_html_entities
compat_html_entities_html5 = compat_html_entities.html5
import http.client as compat_http_client
from urllib.error import HTTPError as compat_HTTPError
from urllib.request import urlretrieve as compat_urlretrieve
from html.parser import HTMLParser as compat_HTMLParser

# HTMLParseError has been deprecated in Python 3.3 and removed in
# Python 3.5. Introducing dummy exception for Python >3.5 for compatible
# and uniform cross-version exceptiong handling


class compat_HTMLParseError(Exception):
    pass


from subprocess import DEVNULL
compat_subprocess_get_DEVNULL = lambda: DEVNULL

import http.server as compat_http_server
compat_str = str
from urllib.parse import unquote_to_bytes as compat_urllib_parse_unquote_to_bytes
from urllib.parse import unquote as compat_urllib_parse_unquote
from urllib.parse import unquote_plus as compat_urllib_parse_unquote_plus
from urllib.parse import urlencode as compat_urllib_parse_urlencode
from urllib.request import DataHandler as compat_urllib_request_DataHandler
compat_basestring = str
compat_chr = chr
from xml.etree.ElementTree import ParseError as compat_xml_parse_error
etree = xml.etree.ElementTree


class _TreeBuilder(etree.TreeBuilder):
    def doctype(self, name, pubid, system):
        pass


from xml.etree.ElementTree import Element as compat_etree_Element


def compat_etree_fromstring(text):
    return etree.XML(text, parser=etree.XMLParser(target=_TreeBuilder()))


compat_etree_register_namespace = etree.register_namespace
compat_xpath = lambda xpath: xpath
from urllib.parse import parse_qs as compat_parse_qs
compat_os_name = os.name


if compat_os_name == 'nt':
    def compat_shlex_quote(s):
        return s if re.match(r'^[-_\w./]+$', s) else '"%s"' % s.replace('"', '\\"')
else:
    from shlex import quote as compat_shlex_quote

compat_shlex_split = shlex.split


def compat_ord(c):
    if type(c) is int:
        return c
    else:
        return ord(c)


compat_getenv = os.getenv
compat_expanduser = os.path.expanduser


def compat_setenv(key, value, env=os.environ):
    env[key] = value


if compat_os_name == 'nt' and sys.version_info < (3, 8):
    # os.path.realpath on Windows does not follow symbolic links
    # prior to Python 3.8 (see https://bugs.python.org/issue9949)
    def compat_realpath(path):
        while os.path.islink(path):
            path = os.path.abspath(os.readlink(path))
        return path
else:
    compat_realpath = os.path.realpath


def compat_print(s):
    assert isinstance(s, compat_str)
    print(s)


compat_getpass = getpass.getpass
compat_input = input
compat_kwargs = lambda kwargs: kwargs
compat_numeric_types = (int, float, complex)
compat_integer_types = (int, )
compat_socket_create_connection = socket.create_connection


def workaround_optparse_bug9161():
    pass


compat_get_terminal_size = shutil.get_terminal_size
compat_itertools_count = itertools.count
from tokenize import tokenize as compat_tokenize_tokenize
compat_struct_pack = struct.pack
compat_struct_unpack = struct.unpack
compat_Struct = struct.Struct
compat_zip = zip
compat_b64decode = base64.b64decode


def compat_ctypes_WINFUNCTYPE(*args, **kwargs):
    return ctypes.WINFUNCTYPE(*args, **kwargs)


__all__ = [
    'compat_HTMLParseError',
    'compat_HTMLParser',
    'compat_HTTPError',
    'compat_Struct',
    'compat_b64decode',
    'compat_basestring',
    'compat_chr',
    'compat_cookiejar',
    'compat_cookiejar_Cookie',
    'compat_cookies',
    'compat_cookies_SimpleCookie',
    'compat_ctypes_WINFUNCTYPE',
    'compat_etree_Element',
    'compat_etree_fromstring',
    'compat_etree_register_namespace',
    'compat_expanduser',
    'compat_get_terminal_size',
    'compat_getenv',
    'compat_getpass',
    'compat_html_entities',
    'compat_html_entities_html5',
    'compat_http_client',
    'compat_http_server',
    'compat_input',
    'compat_integer_types',
    'compat_itertools_count',
    'compat_kwargs',
    'compat_numeric_types',
    'compat_ord',
    'compat_os_name',
    'compat_parse_qs',
    'compat_print',
    'compat_realpath',
    'compat_setenv',
    'compat_shlex_quote',
    'compat_shlex_split',
    'compat_socket_create_connection',
    'compat_str',
    'compat_struct_pack',
    'compat_struct_unpack',
    'compat_subprocess_get_DEVNULL',
    'compat_tokenize_tokenize',
    'compat_urllib_error',
    'compat_urllib_parse',
    'compat_urllib_parse_unquote',
    'compat_urllib_parse_unquote_plus',
    'compat_urllib_parse_unquote_to_bytes',
    'compat_urllib_parse_urlencode',
    'compat_urllib_parse_urlparse',
    'compat_urllib_request',
    'compat_urllib_request_DataHandler',
    'compat_urllib_response',
    'compat_urlparse',
    'compat_urlretrieve',
    'compat_xml_parse_error',
    'compat_xpath',
    'compat_zip',
    'workaround_optparse_bug9161',
]
