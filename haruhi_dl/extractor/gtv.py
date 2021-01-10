# coding: utf-8
from __future__ import unicode_literals

import base64
import re

from .common import InfoExtractor
from ..utils import (
    NO_DEFAULT,
)


class GtvIE(InfoExtractor):
    IE_NAME = 'gtv'
    IE_DESC = 'GTV.org'
    _VALID_URL = r'https?://(?:www\.)?gtv\.org/video/id=(?P<id>[a-f\d]+)'
    _TESTS = [{
        'url': 'https://gtv.org/video/id=5edc48b087564418749581c0',
        'info_dict': {
            'id': '5edc48b087564418749581c0',
            'ext': 'm3u8',
            'title': 'Hongkongers Commemorate Tiananmen Square Massacre',
        },
    }, {
        'url': 'https://www.gtv.org/video/id=5ed91fb759b1dc11aa3d99db',
        'info_dict': {
            'id': '5ed91fb759b1dc11aa3d99db',
            'ext': 'm3u8',
            'title': 'Tiananmen : à Taïwan et en Corée du Sud, des cérémonies',
        },
    }]
    # this code is based on a terrible idea to "parse" gRPC data with regexes
    # that randomly may or may not work, depending on a specific video
    _WORKING = False

    def _real_extract(self, url):
        video_id = self._match_id(url)
        headers = {
            'Content-Type': 'application/grpc-web-text',
            'Accept': 'application/grpc-web-text',
        }
        data = self._download_webpage(
            'https://app.gtv.org/grpc.video.VideoService/video',
            video_id, 'Downloading video metadata',
            data=base64.b64encode(b'\x00\x00\x00\x00\x1a\x0a\x18' + bytes(video_id.encode('utf-8'))),
            headers=headers)
        # decoding base64-encoded gRPC data
        data = base64.b64decode(bytes(data.encode('utf-8')))
        self.to_screen(data)

        def search(regex, name, default=NO_DEFAULT):
            val = self._search_regex(re.compile(regex), data, name, default=default)
            if val:
                return val.decode('utf-8')

        formats = []

        m3u_url = search(br'\xaa\x01>(/.+?\.m3u8)\xfa', 'm3u8 url')
        if m3u_url:
            formats.extend(self._extract_m3u8_formats('https://filegroup.gtv.org' + m3u_url, video_id))

        mp4_url = search(br'\".(/.+?\.mp4)\*A', 'mp4 url')
        if mp4_url:
            formats.append({
                'url': 'https://filegroup.gtv.org' + mp4_url,
                'ext': 'mp4',
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'formats': formats,
            'title': search(br':.([^\n]+)\n?P.X', 'video title'),
        }
