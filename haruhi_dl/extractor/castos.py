# coding: utf-8

from .common import InfoExtractor
from ..utils import (
    parse_duration,
)

import re


class CastosHostedIE(InfoExtractor):
    _VALID_URL = r'https?://[^/.]+\.castos\.com/(?:player|episodes)/(?P<id>[\da-zA-Z-]+)'
    IE_NAME = 'castos:hosted'

    _TESTS = [{
        'url': 'https://audience.castos.com/player/408278',
        'info_dict': {
            'id': '408278',
            'ext': 'mp3',
        },
    }, {
        'url': 'https://audience.castos.com/episodes/improve-your-podcast-production',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_urls(webpage, **kw):
        return [mobj.group(1) for mobj
                in re.finditer(
                    r'<iframe\b[^>]+(?<!-)src="(https?://[^/.]+\.castos\.com/player/\d+)',
                    webpage)]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        series = self._html_search_regex(
            r'<div class="show">\s+<strong>([^<]+)</strong>', webpage, 'series name')
        title = self._html_search_regex(
            r'<div class="episode-title">([^<]+)</div>', webpage, 'episode title')

        audio_url = self._html_search_regex(
            r'<audio class="clip">\s+<source\b[^>]+src="(https?://[^"]+)"', webpage, 'audio url')
        duration = parse_duration(self._search_regex(
            r'<time id="duration">(\d\d(?::\d\d)+)</time>', webpage, 'duration'))

        return {
            'id': video_id,
            'title': title,
            'url': audio_url,
            'duration': duration,
            'series': series,
            'episode': title,
        }


class CastosSSPIE(InfoExtractor):
    @classmethod
    def _extract_entries(self, webpage, **kw):
        entries = []
        for found in re.finditer(
                r'(?s)<div class="castos-player[^"]*"[^>]*data-episode="(\d+)-[a-z\d]+">(.+?</nav>)\s*</div>',
                webpage):
            video_id, entry = found.group(1, 2)

            def search_entry(regex):
                res = re.search(regex, entry)
                if res:
                    return res.group(1)

            series = search_entry(r'<div class="show">\s+<strong>([^<]+)</strong>')
            title = search_entry(r'<div class="episode-title">([^<]+)</div>')

            audio_url = search_entry(
                r'<audio class="clip[^"]*">\s+<source\b[^>]+src="(https?://[^"]+)"')
            duration = parse_duration(
                search_entry(r'<time id="duration[^"]*">(\d\d(?::\d\d)+)</time>'))

            if not title or not audio_url:
                continue

            entries.append({
                'id': video_id,
                'title': title,
                'url': audio_url,
                'duration': duration,
                'series': series,
                'episode': title,
            })
        return entries
