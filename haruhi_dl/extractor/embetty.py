# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
)


class EmbettyIE(InfoExtractor):
    @staticmethod
    def _extract_entries(webpage, **kw):
        results = []

        twitter_matches = re.finditer(r'<embetty-tweet\s+[^>]*\bstatus="(\d{18})"[^>]*>', webpage)
        for match in twitter_matches:
            results.append({
                '_type': 'url',
                'url': 'https://twitter.com/i/web/status/%s' % match.group(1),
                'ie_key': 'Twitter',
            })

        video_matches = re.findall(r'<embetty-video\s+[^>]+>', webpage)
        for match in video_matches:
            attr = extract_attributes(match)
            if any(key not in attr for key in ('type', 'video-id')):
                continue    # invalid
            service = attr['type'].lower()
            if service == 'youtube':
                results.append({
                    '_type': 'url',
                    'url': 'https://www.youtube.com/watch?v=%s&t=%s' % (attr['video-id'], attr.get('start-at', '0')),
                    'ie_key': 'Youtube',
                })
            elif service == 'vimeo':
                results.append({
                    '_type': 'url',
                    'url': 'https://vimeo.com/%s#t=%s' % (attr['video-id'], attr.get('start-at', '0')),
                    'ie_key': 'Vimeo',
                })
            elif service == 'facebook':
                results.append({
                    '_type': 'url',
                    'url': 'https://www.facebook.com/video.php?v=%s' % (attr['video-id']),
                    'ie_key': 'Facebook',
                })

        return results

        @staticmethod
        def _extract_urls(webpage, **kw):
            return [embed['url'] for embed in EmbettyIE._extract_entries(webpage, **kw)]
