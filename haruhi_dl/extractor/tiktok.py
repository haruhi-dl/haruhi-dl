# coding: utf-8
from __future__ import unicode_literals

import re

from ..playwright import PlaywrightHelper
from .common import InfoExtractor
from ..utils import (
    int_or_none,
    str_or_none,
    try_get,
    url_or_none,
    ExtractorError,
)


class TikTokBaseIE(InfoExtractor):
    _DATA_RE = r'<script id="__NEXT_DATA__"[^>]+>(.+?)</script>'

    def _extract_headers(self, data, url):
        return {
            'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
            'Referer': data['query']['$initialProps']['$fullUrl'] if data else url,
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

    def _extract_video(self, item, data, url):
        video = item['video']
        stats = item['stats']
        description = str_or_none(item['desc'])
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

        timestamp = int_or_none(item.get('createTime'))
        view_count = int_or_none(stats.get('playCount'))
        like_count = int_or_none(stats.get('diggCount'))
        comment_count = int_or_none(stats.get('commentCount'))
        repost_count = int_or_none(stats.get('shareCount'))

        author = self._extract_author_data(item['author'])
        http_headers = self._extract_headers(data, url)

        return {
            'id': item['id'],
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
        data = self._search_nextjs_data(webpage, video_id)
        # https://github.com/ytdl-org/youtube-dl/issues/28453
        if data['props']['pageProps'].get('statusCode') == 10216:
            raise ExtractorError('This video is private', expected=True)
        return self._extract_video(data['props']['pageProps']['itemInfo']['itemStruct'], data, url)


class TikTokPlaywrightBaseIE(TikTokBaseIE):
    def _dedup_by_ids(self, items):
        deduped = []
        dedids = []
        for item in deduped:
            if item['id'] in dedids:
                continue
            dedids.append(item['id'])
            deduped.append(item)
        return deduped

    def _scroll_the_page(self, page, item_list_re, display_id):
        if page.title() == 'tiktok-verify-page':
            raise ExtractorError('TikTok requires captcha, use --cookies')
        items = []
        more = True
        pages = 0
        while more:
            # if pages > 0:
            page.evaluate('() => window.scrollTo(0, document.body.scrollHeight)')
            with page.expect_response(
                    lambda r: re.match(item_list_re, r.url)) as item_list_res:
                item_list = item_list_res.value.json()
                status_code = try_get(item_list, (
                    lambda x: x['code'],
                    lambda x: x['statusCode']
                ))
                if status_code is None:
                    raise ExtractorError('Unknown error returned by TikTok')
                status_code = int(status_code)
                if status_code == 10000:
                    raise ExtractorError('Captcha required by TikTok', expected=True)
                if status_code != 0:
                    raise ExtractorError('Unknown error code (%s) returned by TikTok' % str(item_list['code']))
                if 'itemList' not in item_list:
                    # TikTok returns invalid .hasMore value
                    more = False
                    continue
                items.extend(item_list['itemList'])
                more = item_list['hasMore'] is True
                if not self._downloader.params.get('quiet', False):
                    self.to_screen('%s: Fetched video list page %d' % (display_id, pages))
                pages += 1
        return items


class TikTokUserIE(TikTokPlaywrightBaseIE):
    IE_NAME = 'tiktok:user'
    _VALID_URL = r'https?://(?:www\.)?tiktok\.com/@(?P<id>[\w.]+)/?(?:\?.+)?$'
    _TESTS = [{
        'url': 'https://www.tiktok.com/@puczirajot',
        'info_dict': {
            'id': '6797754125703693317',
            'title': 'Marta Puczyńska',
            'description': '🏳️‍🌈🏴\nactivist\nInsta: Puczirajot',
            'uploader_id': '6797754125703693317',
            'uploader': 'Marta Puczyńska',
        },
        'playlist_mincount': 60,
    }]
    _REQUIRES_PLAYWRIGHT = True

    def _real_extract(self, url):
        display_id = self._match_id(url)

        pwh = PlaywrightHelper(self)
        page = pwh.open_page(url, display_id)

        item_list_re = re.compile(r'^https?://(?:[^/]+\.)?tiktok\.com/api/post/item_list/?\?')

        items = self._scroll_the_page(page, item_list_re, display_id)

        data = page.eval_on_selector('script#__NEXT_DATA__', 'el => JSON.parse(el.textContent)')
        pwh.browser_stop()

        page_props = data['props']['pageProps']
        next_data_items = try_get(page_props, lambda x: x['items'], expected_type=list)
        if next_data_items:
            items = next_data_items + items
        items = self._dedup_by_ids(items)

        info_dict = {
            '_type': 'playlist',
            'id': page_props['userInfo']['user']['id'],
            'title': page_props['userInfo']['user']['nickname'],
            'description': page_props['userInfo']['user']['signature'],
            'entries': [self._extract_video(item, data, url) for item in items],
        }
        info_dict.update(self._extract_author_data(page_props['userInfo']['user']))
        return info_dict


class TikTokHashtagIE(TikTokPlaywrightBaseIE):
    IE_NAME = 'tiktok:tag'
    _VALID_URL = r'https?://(?:www\.)?tiktok\.com/tag/(?P<id>[\w.]+)/?(?:\?.+)?$'
    _TESTS = [{
        'url': 'https://www.tiktok.com/tag/mlodzirazem',
        'info_dict': {
            'id': '1649821463999493',
            'title': 'mlodzirazem',
        },
        'playlist_mincount': 10,
    }]
    _REQUIRES_PLAYWRIGHT = True

    def _real_extract(self, url):
        display_id = self._match_id(url)

        pwh = PlaywrightHelper(self)
        page = pwh.open_page(url, display_id)

        item_list_re = re.compile(r'^https?://(?:[^/]+\.)?tiktok\.com/api/challenge/item_list/?\?')

        items = self._scroll_the_page(page, item_list_re, display_id)

        data = page.eval_on_selector('script#__NEXT_DATA__', 'el => JSON.parse(el.textContent)')
        pwh.browser_stop()

        page_props = data['props']['pageProps']
        next_data_items = try_get(page_props, lambda x: x['items'], expected_type=list)
        if next_data_items:
            items = next_data_items + items
        items = self._dedup_by_ids(items)

        return {
            '_type': 'playlist',
            'id': page_props['challengeInfo']['challenge']['id'],
            'title': page_props['challengeInfo']['challenge']['title'],
            'description': page_props['challengeInfo']['challenge']['desc'],
            'entries': [self._extract_video(item, data, url) for item in items],
        }


class TikTokMusicIE(TikTokPlaywrightBaseIE):
    IE_NAME = 'tiktok:music'
    _VALID_URL = r'https?://(?:www\.)?tiktok\.com/music/[^/\?#]+-(?P<id>\d+)/?(?:\?.+)?$'
    _TESTS = [{
        'url': 'https://www.tiktok.com/music/Anime-Vibes-6858829832269171462',
        'info_dict': {
            'id': '6858829832269171462',
            'title': 'Anime Vibes',
            'uploader': 'San 🇲🇲🇬🇧',
            'uploader_id': '108936360073281536',
        },
        'playlist_mincount': 84,
    }, {
        'url': 'https://www.tiktok.com/music/dźwięk-oryginalny-6840124395780934405?',
        'info_dict': {
            'id': '6840124395780934405',
            'ext': 'mp3',
            'title': 'dźwięk oryginalny',
            'uploader': 'jwhsbdh j',
            'uploader_id': '6776617973493203973',
        },
        'params': {
            'noplaylist': True,
        },
    }]
    _REQUIRES_PLAYWRIGHT = True

    def _real_extract(self, url):
        display_id = self._match_id(url)

        if self._downloader.params.get('noplaylist'):
            # extract just the music file
            webpage = self._download_webpage(url, display_id)
            data = self._search_nextjs_data(webpage, display_id)
            page_props = data['props']['pageProps']
            info_dict = {
                'url': page_props['musicInfo']['music']['playUrl'],
                'id': page_props['musicInfo']['music']['id'],
                'title': page_props['musicInfo']['music']['title'],
                'duration': page_props['musicInfo']['music']['duration'],
            }
            info_dict.update(self._extract_author_data(page_props['musicInfo']['author']))
            return info_dict

        pwh = PlaywrightHelper(self)
        page = pwh.open_page(url, display_id)

        item_list_re = re.compile(r'^https?://(?:[^/]+\.)?tiktok\.com/api/music/item_list/?\?')

        items = self._scroll_the_page(page, item_list_re, display_id)

        data = page.eval_on_selector('script#__NEXT_DATA__', 'el => JSON.parse(el.textContent)')
        pwh.browser_stop()

        page_props = data['props']['pageProps']
        next_data_items = try_get(page_props, lambda x: x['items'], expected_type=list)
        if next_data_items:
            items = next_data_items + items
        items = self._dedup_by_ids(items)

        info_dict = {
            '_type': 'playlist',
            'id': page_props['musicInfo']['music']['id'],
            'title': page_props['musicInfo']['music']['title'],
            'entries': [self._extract_video(item, data, url) for item in items],
        }
        info_dict.update(self._extract_author_data(page_props['musicInfo']['author']))
        return info_dict
