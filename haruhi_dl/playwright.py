# coding: utf-8
from __future__ import unicode_literals

from .utils import (
    ExtractorError,
)


class PlaywrightHelper():
    _pw = None
    _pw_version = None

    @classmethod
    def _real_import_pw(cls):
        from playwright import sync_playwright, _repo_version
        cls._pw = sync_playwright
        cls._pw_version = _repo_version.version

    @classmethod
    def _import_pw(cls, fatal=True):
        try:
            cls._real_import_pw()
        except ImportError as err:
            if fatal is True:
                raise ExtractorError('Playwright could not be imported: %s' % err.msg if 'msg' in err else '[no err.msg]',
                                     expected=True)

    @classmethod
    def _version(cls):
        if not cls._pw_version:
            cls._import_pw(fatal=False)
        return cls._pw_version
