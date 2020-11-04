from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    int_or_none,
)

import re
import datetime


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
    def _extract_urls(webpage):
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
    _VALID_URL = r'https?://video\.onnetwork\.tv/frame84\.php\?(?:[^&]+&)*?mid=(?P<mid>[^&]+)&(?:[^&]+&)*?id=(?P<vid>[^&]+)'
    _TESTS = [{
        'url': 'https://video.onnetwork.tv/frame84.php?mid=MCwxNng5LDAsMCwxNzU1LDM3MjksMSwwLDEsMzYsNSwwLDIsMCw0LDEsMCwxLDEsMiwwLDAsMSwwLDAsMCwwLC0xOy0xOzIwOzIwLDAsNTAsMA==&preview=0&iid=0&e=1&widget=524&id=ffEXS991c5f8f4dbb502b540687287098d2d8',
        'only_matching': True,
    }]

    _BASE_OBJECT_RE = r'''var onplayer\s*=\s*new tUIPlayer\(\s*{\s*videos\s*:\s*\[\s*{.*?'''

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        vid = mobj.group('vid')
        webpage = self._download_webpage(url, vid, 'Downloading video frame')

        video_id = self._search_regex(
            self._BASE_OBJECT_RE + r'id\s*:\s*(\d+)',
            webpage, 'video id')
        m3u_url = self._search_regex(
            self._BASE_OBJECT_RE + r'(?:urls\s*:\[{[^}]+}\],)?url\s*:"([^"]+)"',
            webpage, 'm3u url')
        title = self._search_regex(
            self._BASE_OBJECT_RE + r"(?<!p)title\s*:\s*'([^']+)'",
            webpage, 'title')
        thumbnail = self._search_regex(
            self._BASE_OBJECT_RE + r"""(?<![a-z])poster\s*:\s*'([^']+)'""",
            webpage, 'thumbnail', fatal=False)
        duration = self._search_regex(
            self._BASE_OBJECT_RE + r'duration\s*:\s*(\d+)',
            webpage, 'duration', fatal=False)
        age_limit = self._search_regex(
            self._BASE_OBJECT_RE + r'ageallow\s*:\s*(\d+)',
            webpage, 'age limit', fatal=False)
        upload_date_unix = self._search_regex(
            self._BASE_OBJECT_RE + r'adddate\s*:\s*(\d+)',
            webpage, 'upload date', fatal=False)
        if upload_date_unix:
            upload_date = datetime.datetime.fromtimestamp(int(upload_date_unix)).strftime('%Y%m%d')

        m3u_content = self._download_webpage(m3u_url, video_id, 'Downloading format list')
        base_m3u_url = re.sub(r'/[^/]+\.m3u8$', '/', m3u_url)
        formats = []
        for match in re.finditer(
            r'#EXT-X-STREAM-INF:BANDWIDTH=(?P<bandwidth>\d+),RESOLUTION=(?P<width>\d+)x(?P<height>\d+),NAME=(?P<format_name>[^\n]+)\n(?P<filename>[^\n]+)',
                m3u_content):

            formats.append({
                'url': base_m3u_url + match.group('filename'),
                'format_id': match.group('format_name'),
                'width': int(match.group('width')),
                'height': int(match.group('height')),
                'ext': 'mp4',
                'protocol': 'm3u8',
            })
        subtitles = {}
        for match in re.finditer(
            r'#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="(?P<id>[^"]+)",NAME="(?P<name>[^"]+)",URI="(?P<filename>[^"]+)",LANGUAGE="(?P<lang>[^"]+)"',
                m3u_content):

            subtitles[match.group('lang')] = []
            sub_list = self._download_webpage(base_m3u_url + match.group('filename'), video_id, 'Downloading subtitle list')
            for sub_file in re.findall(r'(?<=\n)[^#\s]+', sub_list):
                subtitles[match.group('lang')].append({
                    'url': base_m3u_url + sub_file,
                })

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': thumbnail,
            'duration': int_or_none(duration),
            'age_limit': int_or_none(age_limit),
            'upload_date': upload_date,
        }
