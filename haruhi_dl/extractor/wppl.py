# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
)


class WpPlIE(InfoExtractor):
    _VALID_URL = r'https://(?:[^/]+\.)?wp\.pl/[^/]+-(?P<id>\d+v)'
    IE_NAME = 'wp.pl'
    IE_DESC = 'Wirtualna Polska'
    _TESTS = [{
        'url': 'https://wiadomosci.wp.pl/piotr-wawrzyk-na-rpo-dzieki-psl-to-byloby-trzesienie-ziemi-w-polskiej-polityce-6600013103609985v',
        'info_dict': {
            'id': '2062884',
            'ext': 'mp4',
            'title': 'Piotr Wawrzyk na RPO dzięki PSL? "To byłoby trzęsienie ziemi w polskiej polityce"',
            'description': 'md5:c9b41dce48678c605cedf3f3fe5282c5',
        },
    }]

    def _real_extract(self, url):
        page_id = self._match_id(url)

        webpage = self._download_webpage(url, page_id)
        video_id = self._search_regex(r'<div\b[^>]+\bid="video-player-(\d+)', webpage, 'video id')

        video_data = self._download_json('https://wideo.wp.pl/api/v2/embed/%s/secured' % video_id, video_id)['clip']

        formats = []
        for fmt in video_data['url']:
            ext = determine_ext(fmt['url'])
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(fmt['url'], video_id, m3u8_id=fmt['type']))
            elif ext == 'mpd':
                formats.extend(self._extract_mpd_formats(fmt['url'], video_id, mpd_id=fmt['type']))
            else:
                mobj = re.match(r'(\d+)x(\d+)', fmt['resolution'])
                width, height = mobj.group(1, 2)
                formats.append({
                    'url': fmt['url'],
                    'ext': ext,
                    'format_id': '%s-%s' % (fmt['type'], fmt['quality']),
                    'width': int(width),
                    'height': int(height),
                })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'formats': formats,
            'title': video_data['title'],
            'description': video_data.get('description'),
            'thumbnail': video_data.get('screenshot'),
            'duration': video_data.get('duration'),
            'age_limit': video_data.get('minimalAge'),
        }
