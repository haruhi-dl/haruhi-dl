# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from .pulsembed import PulseVideoIE


class ClipRsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?clip\.rs/(?P<id>[^/]+)/\d+'
    _TESTS = [{
        'url': 'http://www.clip.rs/premijera-frajle-predstavljaju-novi-spot-za-pesmu-moli-me-moli/3732',
        'md5': 'c412d57815ba07b56f9edc7b5d6a14e5',
        'info_dict': {
            'id': '1488842.1399140381',
            'ext': 'mp4',
            'title': 'PREMIJERA Frajle predstavljaju novi spot za pesmu Moli me, moli',
            'description': 'md5:56ce2c3b4ab31c5a2e0b17cb9a453026',
            'duration': 229,
            'timestamp': 1459850243,
            'upload_date': '20160405',
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        return {
            '_type': 'url_transparent',
            'url': 'pulsevideo:%s' % PulseVideoIE._search_mvp_id(webpage),
            'ie_key': PulseVideoIE.ie_key(),
            'display_id': display_id,
        }
