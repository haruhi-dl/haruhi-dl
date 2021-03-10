from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    js_to_json,
)

import re


class OnNetworkLoaderIE(InfoExtractor):
    IE_NAME = 'onnetwork:loader'
    _TESTS = [{
        'url': 'https://video.onnetwork.tv/embed.php?sid=eVgsMWM3UCww&cId=onn-cid-199058',
        'only_matching': True,
    }, {
        'url': 'https://video.onnetwork.tv/embed.php?sid=MTI5LDFYaTIsMA==',
        'only_matching': True,
    }, {
        'url': 'https://video.onnetwork.tv/embed.php?mid=MCwxNng5LDAsMCwxNzU1LDM3MjksMSwwLDEsMzYsNSwwLDIsMCw0LDEsMCwxLDEsMiwwLDAsMSwwLDAsMCwwLC0xOy0xOzIwOzIwLDAsNTAsMA==&cId=p2f95a6a83ab9a3e55759256bec0be777&widget=524',
        'only_matching': True,
    }]
    _VALID_URL = r'''https?://video\.onnetwork\.tv/embed\.php\?(?:mid=(?P<mid>[^&]+))?(?:&?sid=(?P<sid>[^&\s]+))?(?:&?cId=onn-cid-(?P<cid>\d+))?(?:.+)?'''

    @staticmethod
    def _extract_urls(webpage, **kwargs):
        matches = re.finditer(
            r'''<script\s+[^>]*src=["'](%s.*?)["']''' % OnNetworkLoaderIE._VALID_URL,
            webpage)
        if matches:
            matches = [match.group(1) for match in matches]
            return matches

    def _real_extract(self, url):
        url_mobj = re.match(self._VALID_URL, url)
        cid, sid, mid = url_mobj.group('cid', 'sid', 'mid')
        js_loader = self._download_webpage(url, cid or sid or mid, 'Downloading js player loader')
        return {
            '_type': 'url',
            'url': self._search_regex(r'frameSrc\s*:\s*"(.+?)"', js_loader, 'frame url'),
            'ie_key': 'OnNetworkFrame',
        }


class OnNetworkFrameIE(InfoExtractor):
    IE_NAME = 'onnetwork:frame'
    _VALID_URL = r'https?://video\.onnetwork\.tv/frame\d+\.php\?(?:[^&]+&)*?mid=(?P<mid>[^&]+)&(?:[^&]+&)*?id=(?P<vid>[^&]+)'
    _TESTS = [{
        'url': 'https://video.onnetwork.tv/frame84.php?mid=MCwxNng5LDAsMCwxNzU1LDM3MjksMSwwLDEsMzYsNSwwLDIsMCw0LDEsMCwxLDEsMiwwLDAsMSwwLDAsMCwwLC0xOy0xOzIwOzIwLDAsNTAsMA==&preview=0&iid=0&e=1&widget=524&id=ffEXS991c5f8f4dbb502b540687287098d2d8',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        vid = mobj.group('vid')
        webpage = self._download_webpage(url, vid, 'Downloading video frame')

        data = self._search_regex(
            r'(?s)var onplayer\s*=\s*new tUIPlayer\(\s*({\s*videos\s*:\s*\[\s*{.*?})\s*,\s*OnPlayerUI',
            webpage, 'video data')
        data = js_to_json(data)
        data = re.sub(
            r'\((?P<value>\d+(?:\.\d+)?|(["\']).+?\2)(?:\s*\|\|\s*.+?)?\)',
            lambda x: x.group('value'), data)
        data = re.sub(r'"\s*\+\s*"', '', data)
        data = self._parse_json(data, vid)

        entries = []
        for video in data['videos']:
            video_id = str(video['id'])

            formats = self._extract_m3u8_formats(video['url'], video_id)
            self._sort_formats(formats)

            entries.append({
                'id': video_id,
                'title': video['title'],
                'formats': formats,
                'thumbnail': video.get('poster'),
                'duration': int_or_none(video.get('duration')),
                'age_limit': int_or_none(video.get('ageallow')),
                'timestamp': int_or_none(video.get('adddate')),
            })

        return {
            '_type': 'playlist',
            'entries': entries,
            'id': vid,
        }
