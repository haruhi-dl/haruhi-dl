# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
)
from ..compat import compat_urllib_parse_urlencode


class AlbiclaIE(InfoExtractor):
    _VALID_URL = r'https?://albicla\.com/[a-zA-Z\d]+/post/(?P<id>\d+)'
    _LOGIN_REQUIRED = True
    _NETRC_MACHINE = 'albicla'
    _TESTS = [{
        'url': 'https://albicla.com/PolandDailycom/post/1000270222',
        'info_dict': {
            'id': '1000270222',
            'uploader': 'PolandDailycom',
        },
        'playlist_count': 1,
        'params': {
            'username': 'albicla@haruhi.download',
            'password': 'fedupwithallthis',
            'extract_flat': True,
        },
    }]

    def _login(self):
        email, password = self._get_login_info()

        if not email:
            self.report_warning('No Albicla login data found; use --username and --password or --netrc to provide them')

        # if not self._downloader.cookiejar

        self._download_webpage('https://albicla.com/login', 'login', 'Logging in',
                               data=bytes(compat_urllib_parse_urlencode({
                                   'email': email,
                                   'pass': password,
                                   'remember': 'remember-me',
                                   'signin': 'zaloguj',
                               }).encode('utf-8')), headers={
                                   'Content-Type': 'application/x-www-form-urlencoded',
                                   'Origin': 'https://albicla.com',
                                   'Referer': 'https://albicla.com/login',
                               })

    def _real_initialize(self):
        self._login()

    def _real_extract(self, url):
        post_id = self._match_id(url)

        webpage = self._download_webpage(url, post_id)

        post = re.search(r'''(?xs)
            <div\b[^>]+\bclass="post-item">.+?
            <p\b[^>]+>@(?P<username>[a-zA-Z\d]+).+?
            <span\b[^>]+\bdata-timestamp="(?P<timestamp>\d+)".+?
            <div\b[^>]+\bclass="user-post">\s+
            <p\b[^>]*>(?P<content>[^<]*)</p>\s+
            (?:<div\b[^>]+\bclass="card-full[ ]yt"[^>]*>
            <iframe\b[^>]+\bsrc="(?P<yt_url>https?://(?:www\.)?youtube(?:-nocookie)?\.com/embed/[a-zA-Z\d_-]{11})"[^>]*>\s*</iframe>)?
            (?:.+?<i\b[^>]+\bclass="fa[ ]fa-comment[^"]*"></i>\s*(?P<comments>\d+)</button>)?
            (?:.+?<i\b[^>]+\bclass="fa[ ]fa-retweet"></i>\s*<span[^>]+>\s*(?P<forwards>\d+)</span>)?
            (?:.+?<i\b[^>]+\bclass="fa[ ]fa-heart"></i>\s*<span[^>]+>\s*(?P<likes>\d+)</span>)?
        ''', webpage)

        if not post:
            raise ExtractorError('Could not extract post content')

        content, yt_url, comment_count, repost_count, like_count, uploader, timestamp = post.group('content', 'yt_url', 'comments', 'forwards', 'likes', 'username', 'timestamp')
        if not yt_url:
            raise ExtractorError('Could not find youtube embed in the post')

        return {
            '_type': 'playlist',
            'id': post_id,
            'title': clean_html(content),
            'entries': [{
                '_type': 'url',
                'url': yt_url,
                'ie_key': 'Youtube',
            }],
            'uploader': uploader,
            'uploader_url': 'https://albicla.com/%s' % uploader,
            'comment_count': int_or_none(comment_count),
            'repost_count': int_or_none(repost_count),
            'like_count': int_or_none(like_count),
        }
