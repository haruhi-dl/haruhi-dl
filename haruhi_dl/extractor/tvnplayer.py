from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    str_or_none,
)


class TVNPlayerIE(InfoExtractor):
    _VALID_URL = r'https?://player\.pl/.+,(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://player.pl/seriale-online/kasia-i-tomek-odcinki,1/odcinek-1,S01E01,1',
        'info_dict': {
            'id': '1',
            'ext': 'mp4',
            'title': 'Kasia i Tomek - ',  # I love when my code works so well
            'age_limit': 12,
        },
    }, {
        'url': 'https://player.pl/programy-online/w-roli-glownej-odcinki,41/odcinek-3,S07E03,2137',
        'info_dict': {
            'id': '2137',
            'ext': 'mp4',
            'title': 'W roli głównej - Magda Gessler',
            'age_limit': 12,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        res = self._download_json('http://api.tvnplayer.pl/api/?platform=ConnectedTV&terminal=Panasonic&format=json&authKey=064fda5ab26dc1dd936f5c6e84b7d3c2&v=3.1&m=getItem&id=' + video_id, video_id)

        formats = []

        for ptrciscute in res["item"]["videos"]["main"]["video_content"]:
            formats.append({
                "url": ptrciscute["url"],
                "format_note": ptrciscute["profile_name"],
                "tbr": int_or_none(self._search_regex(r'tv_mp4_([0-9]+)\.mp4', ptrciscute["url"], video_id))
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': res["item"]["serie_title"] + " - " + res["item"]["title"],
            'formats': formats,
            'series': str_or_none(res["item"]["serie_title"]),
            'episode': str_or_none(res["item"]["title"]),
            'episode_number': int_or_none(res["item"]["episode"]),
            'season_number': int_or_none(res["item"]["season"]),
            'age_limit': int_or_none(res["item"]["rating"])
        }
