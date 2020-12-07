# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class EskaGoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?eskago\.pl/radio/(?P<id>[^/\s?#]+)'

    _TESTS = [{
        'url': 'https://www.eskago.pl/radio/eska-rock',
        'info_dict': {
            'id': 'eska-rock',
            'ext': 'aac',
            'title': 'Eska ROCK',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.eskago.pl/radio/disco-polo-top',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        station_slug = self._match_id(url)
        webpage = self._download_webpage(url, station_slug, headers={
            'Referer': url,
            'X-Requested-With': 'XHLHttpRequest',
        })

        stream_url = self._html_search_regex(r"{\s*var streamUrl\s*=\s*'(https?://.+?)';",
                                             webpage, 'stream url')
        icsu = self._html_search_regex(r'<input[^>]+id="icsu"[^>]+value="(.+?)"',
                                       webpage, 'some weird token thing')

        formats = []
        # used by zpr as a fallback to support /(Windows NT 6\.(1|2).*Trident)/
        if '.aac' in stream_url:
            formats.append({
                'url': stream_url.replace('.aac', '.mp3') + icsu,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko',
                },
            })
        formats.append({
            'url': stream_url + icsu,
        })

        title = self._html_search_regex([
            r"\$\('#radio-controller \.(?:playlist_small strong|radioline span|player-category \.category)'\)\.html\('(.+?)'\);",
            r"'programName':\s*'(.+?)',",
        ], webpage, 'stream title')

        return {
            'id': station_slug,
            'title': title,
            'formats': formats,
        }
