# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    compat_urllib_parse_urlencode,
    int_or_none,
    std_headers,
    str_or_none,
    try_get,
    url_or_none,
)
import random


class TikTokBaseIE(InfoExtractor):
    _DATA_RE = r'<script id="__NEXT_DATA__"[^>]+>(.+?)</script>'

    def _extract_headers(self, data):
        cookie_value = data['props']['initialProps']['$wid']
        return {
            'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
            'Cookie': 'tt_webid=%s; tt_webid_v2=%s' % (cookie_value, cookie_value),
            'Referer': data['query']['$initialProps']['$fullUrl'],
        }

    def _extract_author_data(self, author):
        uploader = str_or_none(author.get('nickname')) or author.get('uniqueId')
        uploader_id = str_or_none(author.get('id'))
        uploader_url = 'https://www.tiktok.com/@%s' % author.get('uniqueId')

        return {
            'uploader': uploader,
            'uploader_id': uploader_id,
            'uploader_url': uploader_url,
        }

    def _extract_video(self, data):
        props = data['props']['pageProps']['itemInfo']['itemStruct']
        video = props['video']
        stats = props['stats']
        description = str_or_none(props['desc'])
        width = int_or_none(video['width'])
        height = int_or_none(video['height'])
        duration = int_or_none(video['duration'])

        format_urls = set()
        formats = []
        for format_id in ('playAddr', 'downloadAddr'):
            format_url = url_or_none(video[format_id])
            if not format_url:
                continue
            if format_url in format_urls:
                continue
            format_urls.add(format_url)
            formats.append({
                'url': format_url,
                'ext': 'mp4',
                'height': height,
                'width': width,
            })
        self._sort_formats(formats)

        thumbnails = []
        for key in ('originCover', 'dynamicCover', 'shareCover', 'reflowCover'):
            urls = try_get(video, lambda x: x[key])
            if isinstance(urls, str):
                urls = [urls]
            if isinstance(urls, list):
                for url in urls:
                    if isinstance(url, str) and len(url) > 0:
                        thumbnails.append({
                            'url': url,
                        })

        timestamp = int_or_none(props.get('createTime'))
        view_count = int_or_none(stats.get('playCount'))
        like_count = int_or_none(stats.get('diggCount'))
        comment_count = int_or_none(stats.get('commentCount'))
        repost_count = int_or_none(stats.get('shareCount'))

        author = self._extract_author_data(props['author'])
        http_headers = self._extract_headers(data)

        return {
            'id': props['id'],
            'title': author['uploader'],
            'description': description,
            'duration': duration,
            'thumbnails': thumbnails,
            'uploader': author['uploader'],
            'uploader_id': author['uploader_id'],
            'uploader_url': author['uploader_url'],
            'timestamp': timestamp,
            'view_count': view_count,
            'like_count': like_count,
            'comment_count': comment_count,
            'repost_count': repost_count,
            'formats': formats,
            'http_headers': http_headers,
        }


class TikTokIE(TikTokBaseIE):
    IE_NAME = 'tiktok'
    _VALID_URL = r'''(?x)
                        (?:
                            https?://
                                (?:
                                    (?:m\.)?tiktok\.com/v|
                                    (?:www\.)?tiktok\.com/(?:share|@[\w.]+)/video
                                )/
                            |tiktok:
                            )(?P<id>\d+)
                    '''
    _TESTS = [{
        'url': 'https://www.tiktok.com/@puczirajot/video/6878766755280440578',
        'info_dict': {
            'id': '6878766755280440578',
            'ext': 'mp4',
            'title': 'Marta Puczyńska',
            'upload_date': '20201001',
            'uploader_id': '6797754125703693317',
            'description': '#lgbt #lgbtq #lgbtqmatter #poland #polska #warszawa #warsaw',
            'timestamp': 1601587695,
            'uploader': 'Marta Puczyńska',
        },
    }, {
        'url': 'https://m.tiktok.com/v/6606727368545406213.html',
        'md5': '163ceff303bb52de60e6887fe399e6cd',
        'info_dict': {
            'id': '6606727368545406213',
            'ext': 'mp4',
            'title': 'Zureeal',
            'description': '#bowsette#mario#cosplay#uk#lgbt#gaming#asian#bowsettecosplay',
            'thumbnail': r're:^https?://.*\.jpeg\?x-expires=.*&x-signature=.*',
            'uploader': 'Zureeal',
            'uploader_id': '188294915489964032',
            'timestamp': 1538248586,
            'upload_date': '20180929',
            'comment_count': int,
            'repost_count': int,
        }
    }, {
        'url': 'https://www.tiktok.com/share/video/6606727368545406213',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage('https://www.tiktok.com/share/video/%s' % video_id, video_id)
        data = self._parse_json(self._search_regex(
            self._DATA_RE, webpage, 'data'), video_id)
        return self._extract_video(data)


class TikTokUserIE(TikTokBaseIE):
    _WORKING = False
    IE_NAME = 'tiktok:user'
    _VALID_URL = r'https?://(?:www\.)?tiktok\.com/@(?P<id>[\w.]+)/?(?:\?.+)?$'
    _TESTS = [{
        'url': 'https://www.tiktok.com/@puczirajot',
        'info_dict': {
            'id': '6797754125703693317'
        },
        'playlist_mincount': 60,
    }]

    def _get_item_list_page(self, data, page=0, max_cursor=0):
        initial_props = data['query']['$initialProps']
        page_props = data['props']['pageProps']
        screen_resolution = random.choice((
            (1280, 720),
            (1366, 768),
            (1920, 1080),
        ))
        url = 'https://%s/api/item_list/?%s' % (
            try_get(initial_props, lambda x: x['$baseURL'], str) or 'm.tiktok.com',
            compat_urllib_parse_urlencode({
                'aid': '1988',
                'app_name': 'tiktok_web',
                'referer': '',
                'user_agent': std_headers['User-Agent'],
                'cookie_enabled': 'true',
                'screen_width': screen_resolution[0],
                'screen_height': screen_resolution[1],
                'browser_language': 'en-US',
                'browser_platform': 'Win32',
                'browser_name': 'Mozilla',
                'browser_version': std_headers['User-Agent'][8:],
                'browser_online': 'true',
                'ac': '',
                'timezone_name': 'Europe/Warsaw',
                'priority_region': '',
                'verifyFp': 'verify_',  # needs investigation
                'appId': initial_props['$appId'],
                'region': initial_props['$region'],
                'appType': initial_props['$appType'],
                'isAndroid': initial_props['$isAndroid'],
                'isMobile': initial_props['$isMobile'],
                'isIOS': initial_props['$isIOS'],
                'OS': initial_props['$os'],
                'did': '0',  # '6892477327352038917',
                'count': 30,
                'id': page_props['feedConfig']['id'],
                'secUid': page_props['feedConfig']['secUid'],
                'maxCursor': max_cursor,
                'minCursor': '0',
                'sourceType': '8',
                'language': 'en',
                '_signature': '',  # needs investigation
            }))
        return self._download_json(url, page_props['feedConfig']['id'], 'Downloading video list (page #%d)' % page)

    def _real_extract(self, url):
        username = self._match_id(url)
        webpage = self._download_webpage(
            url, username)
        data = self._parse_json(self._search_regex(
            self._DATA_RE, webpage, 'data'), username)
        user = self._extract_author_data(data['props']['pageProps']['userInfo']['user'])

        entries = []
        videos_page = self._get_item_list_page(data)
        self.to_screen(str(videos_page))

        return {
            '_type': 'playlist',
            'id': user['uploader_id'],
            'title': user['uploader'] or user['uploader_id'],
            'entries': entries,
        }
