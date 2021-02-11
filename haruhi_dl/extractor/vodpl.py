# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    parse_duration,
    parse_iso8601,
)
from .pulsembed import PulseVideoIE


class VODPlIE(InfoExtractor):
    _VALID_URL = r'https?://vod\.pl/(?:[^/]+/)+(?P<id>[0-9a-zA-Z]+)'

    _TESTS = [{
        'url': 'https://vod.pl/filmy-dokumentalne/wielce-krolewski-slub/wcl5tx0',
        'info_dict': {
            'id': '2163051.179206518',
            'ext': 'mp4',
            'title': 'Wielce królewski ślub',
            'description': 'md5:9de1b6df5dba5c44fcde37584ad13302',
            'timestamp': 1580313604,
            'upload_date': '20200129',
        },
    }, {
        'url': 'https://vod.pl/filmy/autopsja/62gx8n1',
        'info_dict': {
            'id': '1973639.1440605974',
            'ext': 'mp4',
            'title': 'Autopsja',
            'description': 'md5:94cb987a8caeecd5755e3597d4c0bd66',
            'upload_date': '20190203',
            'timestamp': 1549227901,
            'age_limit': 18,
        },
    }, {
        'url': 'https://vod.pl/seriale/belfer-na-planie-praca-kamery-online/2c10heh',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        data = self._parse_json(
            self._search_regex(r'try {\s*vodDataLayer = ({.+?});', webpage, 'vod data layer'),
            video_id)
        description = clean_html(
            self._search_regex(
                r'(?s)<div[^>]+itemprop="description"[^>]*>(.+?)</div>',
                webpage, 'description', default=None))
        age_limit = int_or_none(self._search_regex(
            r'<li class="v_AgeRating v_AgeRate_(\d+)" title="Kat\. wiekowa',
            webpage, 'age limit', default=None)) or 0   # vod.pl does not show an age limit if it's 0
        return {
            '_type': 'url_transparent',
            'url': 'pulsevideo:%s' % data['video']['mvpId'],
            'ie_key': PulseVideoIE.ie_key(),
            'title': data['published']['title'],
            'description': description,
            'duration': parse_duration(data['video'].get('duration')),
            'timestamp': parse_iso8601(data['published'].get('date')),
            'age_limit': age_limit,
        }
