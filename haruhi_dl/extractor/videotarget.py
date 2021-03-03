# coding: utf-8

import base64
import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    js_to_json,
)


class VideoTargetIE(InfoExtractor):
    _VALID_URL = r'https?://videotarget\.pl/player/v1/content/(?P<id>[a-zA-Z\d_-]+={0,3})'

    _TESTS = [{
        'url': 'https://videotarget.pl/player/v1/content/eyJzaXRlIjoxMDMzLCJwbGFjZW1lbnQiOjEwNzksInRlbXBsYXRlIjoyLCJjb250ZXh0IjoxNjA2NiwidHlwZSI6ImNvbnRlbnQifQ==?type=content',
        'info_dict': {
            'id': '16066',
            'ext': 'mp4',
            'title': 'Inflacja straszy rynki finansowe, niepokoją zwłaszcza rosnące ceny namu mieszkań',
        },
    }]

    @staticmethod
    def _extract_urls(webpage, **kw):
        return [mobj.group('url')
                for mobj in re.finditer(
                    r'<iframe\b[^>]+\bsrc=(["\'])(?P<url>%s(?:\?[^#]+)?(?:\#.+?)?)\1' % VideoTargetIE._VALID_URL,
                    webpage)
                ] + ['https://videotarget.pl/player/v1/content/' + mobj.group('vtid')
                     for mobj in re.finditer(
                         r'<div\b[^>]+?data-vt=(["\'])(?P<vtid>[a-zA-Z\d_-]+={0,3})\1',
                         webpage)]

    def _real_extract(self, url):
        b64_json_ident = self._match_id(url)
        ident = self._parse_json(
            base64.urlsafe_b64decode(b64_json_ident), b64_json_ident)
        video_id = str(ident['context'])

        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(r'<title>(.+?) - videotarget</title>', webpage, 'video title')

        formats = []
        for qual in re.finditer(r'(?s)videoQualities\.push\(({.+?})\);', webpage):
            qual = self._parse_json(qual.group(1), video_id, js_to_json)
            formats.append({
                'height': int_or_none(qual['label'][:-1]),
                'url': qual['src'].replace('{ext}', 'mp4'),
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
        }
