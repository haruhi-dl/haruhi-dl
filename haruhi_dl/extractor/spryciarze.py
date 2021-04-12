# coding: utf-8

from .common import InfoExtractor
from ..utils import (
    js_to_json,
    mimetype2ext,
)


class SpryciarzePageIE(InfoExtractor):
    _VALID_URL = r'https?://[^/]+\.spryciarze\.pl/zobacz/(?P<id>[^/?#]+)'
    IE_NAME = 'spryciarze:page'

    _TESTS = [{
        'url': 'https://komputery.spryciarze.pl/zobacz/jak-jezdzic-pojazdami-pod-woda-w-gta-sa-mp',
        'info_dict': {
            'id': 'jak-jezdzic-pojazdami-pod-woda-w-gta-sa-mp',
            'ext': 'mp4',
            'title': 'Jak jeździć pojazdami pod wodą w GTA SA: MP',
            'description': 'Jest sposób na jazdę pojazdami pod wodą w GTA San Andreas w trybie multiplayer. Po wgraniu pojazdu musimy się od razu w nim znaleźć inaczej pomysł może nie zadziałać.',
            'uploader': 'Webster90804',
            'upload_date': '20091228',
            'timestamp': 1261983600,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        info_dict = self._search_json_ld(webpage, video_id, 'VideoObject')

        info_dict.update({
            '_type': 'url_transparent',
            'url': self._search_regex(r'<iframe src="(https://player\.spryciarze\.pl/embed/[^"]+)"', webpage, 'embed url'),
            'ie_key': 'Spryciarze',
        })
        return info_dict


class SpryciarzeIE(InfoExtractor):
    _VALID_URL = r'https?://player\.spryciarze\.pl/embed/(?P<id>[^/?#]+)'
    IE_NAME = 'spryciarze'

    _TESTS = [{
        'url': 'https://player.spryciarze.pl/embed/jak-sciagac-z-30-hostingow-za-darmo-i-bez-rejestracji',
        'info_dict': {
            'id': 'jak-sciagac-z-30-hostingow-za-darmo-i-bez-rejestracji',
            'ext': 'mp4',
            'title': 'Jak ściągać z 30 hostingów za darmo i bez rejestracji',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        data = self._parse_json(
            self._search_regex(
                r'(?s)const data = ({.+?});',
                webpage, 'video data'), video_id, js_to_json)

        formats = []
        for fmt in data['mediaFiles']:
            formats.append({
                'url': fmt['src'],
                'ext': mimetype2ext(fmt['type']),
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': data['title'],
            'formats': formats,
        }
