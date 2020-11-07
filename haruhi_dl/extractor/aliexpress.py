# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    float_or_none,
    try_get,
)


class AliExpressLiveIE(InfoExtractor):
    IE_NAME = 'aliexpress:live'
    _VALID_URL = r'https?://live\.aliexpress\.com/live/(?P<id>\d+)'
    _TEST = {
        'url': 'https://live.aliexpress.com/live/2800002704436634',
        'md5': 'e729e25d47c5e557f2630eaf99b740a5',
        'info_dict': {
            'id': '2800002704436634',
            'ext': 'mp4',
            'title': 'CASIMA7.22',
            'thumbnail': r're:http://.*\.jpg',
            'uploader': 'CASIMA Official Store',
            'timestamp': 1500717600,
            'upload_date': '20170722',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        data = self._parse_json(
            self._search_regex(
                r'(?s)runParams\s*=\s*({.+?})\s*;?\s*var',
                webpage, 'runParams'),
            video_id)

        title = data['title']

        formats = self._extract_m3u8_formats(
            data['replyStreamUrl'], video_id, 'mp4',
            entry_protocol='m3u8_native', m3u8_id='hls')

        return {
            'id': video_id,
            'title': title,
            'thumbnail': data.get('coverUrl'),
            'uploader': try_get(
                data, lambda x: x['followBar']['name'], compat_str),
            'timestamp': float_or_none(data.get('startTimeLong'), scale=1000),
            'formats': formats,
        }


class AliExpressProductIE(InfoExtractor):
    IE_NAME = 'aliexpress:product'

    _TESTS = [{
        'url': 'https://pl.aliexpress.com/item/4000570726711.html',
        'info_dict': {
            'id': '249591332087',
            'title': str,  # depends on IP location
            'ext': 'mp4',
        },
    }, {
        'url': 'https://www.aliexpress.com/item/4000813110155.html',
        'info_dict': {
            'id': '274294663774',
            'title': str,  # depends on IP location
            'ext': 'mp4',
        },
    }]

    _VALID_URL = r'https?://(?:(?:www|[a-z]{2})\.)?aliexpress\.(?:com|ru)/item/(?P<id>\d+)\.html'

    def _real_extract(self, url):
        pid = self._match_id(url)
        webpage = self._download_webpage(url, pid, 'Downloading product page')

        vid = self._search_regex(
            r'"videoId"\s*:\s*"?(\d+)"?',
            webpage, 'video id')
        uid = self._search_regex(
            r'"videoUid"\s*:\s*"?(?P<uid>\d+)"?',
            webpage, 'video uid')

        og_title = self._og_search_title(webpage)
        title = self._search_regex(r'^.*?\|(.+?)\|', og_title, 'product title', default=og_title)

        return {
            # I have no idea what these params mean but it at least seems to work
            'url': 'https://cloud.video.taobao.com/play/u/%s/p/1/e/6/t/10301/%s.mp4' % (uid, vid),
            'id': vid,
            'title': title,
        }
