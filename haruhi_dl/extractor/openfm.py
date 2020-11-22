# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    compat_str,
    ExtractorError,
    try_get,
)


class OpenFMIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?open\.fm/stacja/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://open.fm/stacja/radio-nowy-swiat',
        'info_dict': {
            'id': '368',
            'title': 'Radio Nowy Świat',
            # we don't know it until we download
            'ext': 'unknown_video',
        },
        'params': {
            # endless stream
            'skip_download': True,
        }
    }]

    def _real_extract(self, url):
        slug = self._match_id(url)
        stations = self._download_json('https://open.fm/radio/api/v2/ofm/stations_slug.json', slug)
        station = None
        for channel in stations['channels']:
            if channel.get('slug') == slug:
                station = channel
                break
        if not station:
            raise ExtractorError('Station not found')
        id = try_get(station, [
            lambda x: x['instance_id'],
            lambda x: x['id'],
            lambda x: x['mnt'],
        ], expected_type=compat_str)
        if not id:
            raise ExtractorError('Could not find channel id')
        return {
            'id': id,
            'display_id': slug,
            'title': station['name'],
            'url': 'https://stream.open.fm/%s' % id,
            'thumbnail': try_get(station, lambda x: x['logo']['url']),
        }
