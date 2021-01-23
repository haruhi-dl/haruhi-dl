# coding: utf-8
from __future__ import unicode_literals

from .compat import compat_cookiejar_Cookie
from .utils import (
    ExtractorError,
    is_outdated_version,
)


class PlaywrightHelper():
    _pw = None
    _pw_version = None
    pw_instance = None
    _required_pw_version = '1.8.0a1'
    _extractor = None

    def __init__(self, extractor):
        self._extractor = extractor

    @classmethod
    def _check_version(cls):
        if 'a' in cls._required_pw_version:
            return not is_outdated_version(cls._pw_version.split('a')[0], cls._required_pw_version.split('a')[0])
        return not is_outdated_version(cls._pw_version, cls._required_pw_version)

    @classmethod
    def _real_import_pw(cls):
        from playwright._repo_version import version
        cls._pw_version = version
        if cls._check_version() is False:
            raise ExtractorError('Playwright version %s is required (%s found)' % (cls._required_pw_version, version), expected=True)
        from playwright.sync_api import sync_playwright
        cls._pw = lambda x: sync_playwright()

    @classmethod
    def _import_pw(cls, fatal=True):
        try:
            cls._real_import_pw()
        except ImportError:
            if fatal is True:
                raise ExtractorError('Playwright could not be imported', expected=True)
        except ExtractorError as err:
            if fatal is True:
                raise err

    @classmethod
    def _version(cls):
        if not cls._pw_version:
            cls._import_pw(fatal=False)
        return cls._pw_version

    def pw(self):
        if not self._pw:
            self._import_pw(fatal=True)
        if 'pw_instance' not in self._extractor._downloader.__dict__:
            self._extractor._downloader.pw_instance = self._pw().__enter__()
        return self._extractor._downloader.pw_instance

    def pw_stop(self):
        self.pw_instance.stop()

    def browser_stop(self):
        self._set_cookies_from_browser(self.browser_context.cookies())
        self.browser.close()

    def _get_cookies_for_browser(self):
        browser_cookies = []
        for cookie in self._extractor._downloader.cookiejar:
            c = {
                'name': cookie.name,
                'value': cookie.value,
                'port': cookie.port,
                'domain': cookie.domain,
                'path': cookie.path,
                # 'expires': cookie.expires,
                'secure': cookie.secure,
            }
            # https://github.com/microsoft/playwright-python/issues/459
            if cookie.expires:
                c['expires'] = cookie.expires
            browser_cookies.append(c)
        return browser_cookies

    def _set_cookies_from_browser(self, cookies):
        for cookie in cookies:
            self._extractor._downloader.cookiejar.set_cookie(
                compat_cookiejar_Cookie(0, cookie['name'], cookie['value'], cookie.get('port'), False,
                                        cookie['domain'], False, cookie['domain'].startswith('.'),
                                        cookie['path'], cookie['path'] != '/',
                                        cookie['secure'], cookie['expires'],
                                        False, None, None, None))

    def open_page(self, url, display_id, browser_used='firefox', note='Opening page in %(browser)s', html=None):
        pw = self.pw()
        self.pw_instance = pw
        browser = {
            'firefox': pw.firefox,
            'chromium': pw.chromium,
            'webkit': pw.webkit,
        }[browser_used].launch(
            headless=self._extractor._downloader.params.get('headless_playwright', True))
        self.browser = browser
        browser_context = browser.new_context()
        self.browser_context = browser_context
        browser_context.add_cookies(self._get_cookies_for_browser())
        if not self._extractor._downloader.params.get('quiet'):
            self._extractor.to_screen('%s: %s' % (display_id, note % {'browser': browser_used}))
        page = browser_context.new_page()
        if html:
            page.set_content(html)
        page.goto(url)
        return page
