# coding: utf-8

from .common import InfoExtractor
from ..utils import (
    js_to_json,
)


class PatroniteAudioIE(InfoExtractor):
    IE_NAME = 'patronite:audio'
    _VALID_URL = r'https?://patronite\.pl/(?P<id>[a-zA-Z\d-]+)'
    _TESTS = [{
        'url': 'https://patronite.pl/radionowyswiat',
        'info_dict': {
            'id': 'radionowyswiat',
            'ext': 'unknown_video',
            'title': 'Radio Nowy Świat',
            'description': 'Dobre radio tworzą nie tylko dziennikarze, realizatorzy, technicy czy reporterzy. Bez nich nie byłoby radia, ale też radia nie byłoby bez słuchaczy. Dziś każdy z Was może pójść o krok dalej - stając się współtwórcą i mecenasem Radia Nowy Świat!',
        },
    }]

    def _real_extract(self, url):
        # only works with radio streams, no podcast support
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        data = self._parse_json(self._search_regex(
            r"(?s)const player\s*=\s*new window\.PatroniteWebPlayer\('\.web-player',\s*({.+?})\);",
            webpage, 'player data'), display_id, js_to_json)
        return {
            'id': display_id,
            'url': data['url'],
            'title': data['title'],
            'description': self._og_search_description(webpage),
            'thumbnail': data.get('artwork'),
            'vcodec': 'none',
        }
