# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
)
from .pulsembed import PulseVideoIE, PulsEmbedIE


class ClipRsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?clip\.rs/(?P<id>[^/]+)/\d+'
    _TESTS = [{
        'url': 'https://www.clip.rs/premijera-frajle-predstavljaju-novi-spot-za-pesmu-moli-me-moli/3732',
        'info_dict': {
            'id': '1488842.1399140381',
            'ext': 'mp4',
            'title': 'PREMIJERA Frajle predstavljaju novi spot za pesmu Moli me, moli',
            'description': 'md5:56ce2c3b4ab31c5a2e0b17cb9a453026',
            'duration': 229,
            'timestamp': 1459850243,
            'upload_date': '20160405',
        }
    }, {
        'url': 'https://www.clip.rs/u-novom-sadu-se-sinoc-desio-jedan-zimski-neum-svi-su-zaboravili-na-koronu-uhvatili-se-u-kolo-i-nastao-je-hit-video/15686',
        'info_dict': {
            'id': '2210721.1689293351',
            'ext': 'mp4',
            'title': 'U Novom Sadu se sinoć desio jedan zimski Neum: Svi su zaboravili na koronu, uhvatili se u kolo i nastao je HIT VIDEO',
            'description': 'md5:b1d7d6c0b029b922f06a2a08c9761852',
            'timestamp': 1609405068,
            'upload_date': '20201231',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)
        info_dict = {}

        mvp_id = PulseVideoIE._search_mvp_id(webpage, default=None)
        if mvp_id:
            info_dict.update({
                'url': 'pulsevideo:%s' % PulseVideoIE._search_mvp_id(webpage),
                'ie_key': PulseVideoIE.ie_key(),
            })
        else:
            entries = PulsEmbedIE._extract_entries(webpage)
            if not entries:
                raise ExtractorError('Video ID not found on webpage')
            if len(entries) > 1:
                raise ExtractorError('More than 1 PulsEmbed')
            info_dict.update(entries[0])

        info_dict.update({
            '_type': 'url_transparent',
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'display_id': display_id,
        })
        return info_dict
