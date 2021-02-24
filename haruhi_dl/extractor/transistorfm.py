# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
)


class TransistorFMIE(InfoExtractor):
    _VALID_URL = r'https://[^/]+\.transistor\.fm/episodes/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://makingcents.transistor.fm/episodes/the-tech-stock-bubble',
        'info_dict': {
            'id': 'the-tech-stock-bubble',
            'ext': 'mp3',
            'title': 'A little bit of Coin',
            'description': 'Today we chat about the CRYPTOCURRENCY',
            'uploader': 'Making Cent$',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        return {
            'url': self._html_search_regex(r'<body\b[^>]+\bdata-default-episode-url="([^"]+)"', webpage, 'media url'),
            'id': video_id,
            'title': self._html_search_regex(r'<body\b[^>]+\bdata-default-episode-title="([^"]+)"', webpage, 'episode title'),
            'description': self._html_search_meta('description', webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'uploader': self._og_search_property('site_name', webpage),
        }


class TransistorFMShareIE(InfoExtractor):
    _VALID_URL = r'https://share\.transistor\.fm/s/(?P<id>[0-9a-f]{8})'
    _TESTS = [{
        'url': 'https://share.transistor.fm/s/e9d040c0',
        'info_dict': {
            'id': 'e9d040c0',
            'ext': 'mp3',
            'duration': 1132,
            'artist': 'Батенька, да вы трансформер',
            'title': 'Эпизод 19. Люди и фанатики',
            'description': 'md5:cc2561a69442b97d7ea5c3d6351a3dd6',
            'thumbnail': 'https://images.transistor.fm/file/transistor/images/episode/373966/medium_1602593993-artwork.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        data = self._parse_json(self._html_search_regex(
            r'<div id="embed-app" data-episodes="([^"]+)"',
            webpage, 'JSON data block'), video_id)

        if not data:
            raise ExtractorError('No episode found')

        data = data[0]

        return {
            'url': data['trackable_media_url'],
            'id': video_id,
            'title': data['title'],
            'description': data.get('formatted_summary'),
            'thumbnail': data.get('artwork'),
            'duration': data.get('duration'),
            'artist': data.get('author'),
        }
