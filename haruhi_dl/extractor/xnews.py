# encoding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    js_to_json,
    parse_duration,
    smuggle_url,
    unsmuggle_url,
)


class XLinkIE(InfoExtractor):
    IE_NAME = 'x-link'
    IE_DESC = 'x-news.pl embeds'
    _VALID_URL = r'https?://get\.x-link\.pl/(?:[a-f\d]{8}-(?:[a-f\d]{4}-){3}[a-f\d]{12}),(?P<id>[a-f\d]{8}-(?:[a-f\d]{4}-){3}[a-f\d]{12}),embed\.html'
    _TESTS = [{
        'url': 'https://get.x-link.pl/6fc656ab-ee92-d813-6afd-59863a7ccbdd,7186de52-4c89-5d64-7508-fca6a4f2d3b9,embed.html#__youtubedl_smuggle=%7B%22referer%22%3A+%22https%3A%2F%2Fgazetawroclawska.pl%2Fsklepy-w-galeriach-handlowych-otwarte-od-poniedzialku-w-rezimie-sanitarnym-co-trzeba-wiedziec%2Far%2Fc3-15417477%22%7D',
        'info_dict': {
            'id': '7186de52-4c89-5d64-7508-fca6a4f2d3b9',
            'ext': 'mp4',
            'title': 'Luzowanie obostrzeń: Od 1 lutego otwarte galerie handlowe i muzea, nie będzie też godzin dla seniorów',
        },
    }]

    @staticmethod
    def _extract_urls(webpage, url=None):
        return [smuggle_url(mobj.group('url'), {'referer': url}) for mobj
                in re.finditer(r'<(?:(?:script|div)\b[^>]+\bdata-url|iframe\b[^>]*\ssrc)=(["\']?)(?P<url>https?://get\.x-link\.pl/(?:[a-f\d]{8}-(?:[a-f\d]{4}-){3}[a-f\d]{12},){2}embed\.html)[^"\' ]*?\1', webpage)]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        headers = {}
        _, smugged = unsmuggle_url(url, default={})
        referer = smugged.get("referer")
        if referer is None:
            self.report_warning("Referer not smuggled, will probably fail")
        else:
            headers["Referer"] = referer.encode('utf-8')

        webpage = self._download_webpage(url, video_id, headers=headers)

        data = self._search_regex(r'initConsent\(\[({.+?})],', webpage, 'video data')
        data = js_to_json(data)
        data = self._parse_json(data, video_id)

        thumbnails = []
        if data.get('thumbnail'):
            thumbnails.append({
                'url': 'https:' + data.get('thumbnail'),
            })
        if data.get('poster'):
            thumbnails.append({
                'url': 'https:' + data.get('poster'),
            })

        return {
            'id': video_id,
            'url': 'https:' + data['src'],
            'title': data['title'],
            'thumbnails': thumbnails,
            'duration': parse_duration(data.get('videoDuration')),
        }
