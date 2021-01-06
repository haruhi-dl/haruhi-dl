# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import (
    compat_str,
)
from ..utils import (
    JSON_LD_RE,
    parse_iso8601,
    unescapeHTML,
)


class RMFonStreamIE(InfoExtractor):
    IE_NAME = 'rmfon:stream'
    _VALID_URL = r'https?://(?:www\.)?rmfon\.pl/play,(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.rmfon.pl/play,5#p',
        'info_dict': {
            'id': '5',
            'ext': 'mp3',
            'title': 'RMF FM',
        },
    }]

    def _real_extract(self, url):
        stream_id = self._match_id(url)

        streams = self._download_xml('https://rmfon.pl/stacje/flash_aac_%s.xml.txt' % stream_id,
                                     stream_id, 'Downloading station stream list')

        formats = []
        for stream in streams.iter('item'):
            formats.append({
                'url': stream.text,
                'ext': 'aac',
            })
        for stream in streams.iter('item_mp3'):
            formats.append({
                'url': stream.text,
                'ext': 'mp3',
            })

        # seems to have lower size than /json/app.txt and the website
        stream_list = self._download_xml('https://www.rmfon.pl/xml/stations.txt',
                                         stream_id, 'Downloading station list for metadata')

        stream_meta = None
        for meta in stream_list.iter('station'):
            if meta.attrib.get('id') == stream_id:
                stream_meta = meta.attrib
                break

        return {
            'id': stream_id,
            'formats': formats,
            'title': stream_meta['name'],
            'is_live': True,
        }


# there doesn't seem to be a way to link to a specific podcast episode...
class RMFonPodcastsIE(InfoExtractor):
    IE_NAME = 'rmfon:podcasts'
    _VALID_URL = r'https?://(?:www\.)?rmfon\.pl/podcasty/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.rmfon.pl/podcasty/poranna-rozmowa',
        'info_dict': {
            'id': 'poranna-rozmowa',
            'title': 'Poranna rozmowa w\xa0RMF\xa0FM',
            'description': 'Na poranną publicystykę zaprasza Robert Mazurek. Codziennie, od poniedziałku do piątku o 8:02 polecamy Poranną rozmowę w RMF FM. Gośćmi są nie tylko politycy, ale i ludzie ze świata kultury czy sportu.',
        },
        'playlist_mincount': 30,
    }]

    def _real_extract(self, url):
        podcast_slug = self._match_id(url)

        meta = self._download_json('https://www.rmfon.pl/json/podcasts.php?c=%s' % (podcast_slug),
                                   podcast_slug)

        entries = []
        for ep in meta['episodes']:
            entries.append({
                'id': 'id? on rmfon? haha, next joke please',
                'url': ep['url'],
                'title': ep['t'],
                'description': ep['desc'],
                'duration': ep.get('sec'),
                'timestamp': parse_iso8601(ep.get('d')),
                'thumbnail': ep.get('img'),
            })

        return {
            '_type': 'playlist',
            'id': podcast_slug,
            'title': unescapeHTML(meta['title']),
            'description': unescapeHTML(meta.get('description')),
            'thumbnail': meta.get('img'),
            'entries': entries,
        }


class RMF24IE(InfoExtractor):
    IE_NAME = 'rmf24'
    _VALID_URL = r'https?://(?:www\.)?rmf24\.pl(?:/[^/?#,]+)+,nId,(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.rmf24.pl/tylko-w-rmf24/poranna-rozmowa/news-marek-suski-chyba-sie-zaszczepie-chociaz-pewne-obawy-mam,nId,4942865',
        'info_dict': {
            'id': '4942865',
            'title': 'Marek Suski: Chyba się zaszczepię, chociaż pewne obawy mam ',
            'description': 'md5:1cee8cb54827b5aa9eb39ab1333d4b24',
        },
        'playlist_count': 3,
    }]

    def _real_extract(self, url):
        page_id = self._match_id(url)

        webpage = self._download_webpage(url, page_id)

        entries = []
        for jsonstr in re.finditer(JSON_LD_RE, webpage):
            entry = self._json_ld(self._parse_json(jsonstr.group('json_ld'), page_id), page_id, expected_type='VideoObject')
            if isinstance(entry, dict) and isinstance(entry.get('url'), compat_str):
                self.to_screen(entry.get('url'))
                entry.update({
                    'id': re.match(r'https?://[^/]+/-/([^/-]+)', entry.get('url')).group(1),
                })
                entries.append(entry)

        return {
            '_type': 'playlist',
            'id': page_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'entries': entries,
        }
