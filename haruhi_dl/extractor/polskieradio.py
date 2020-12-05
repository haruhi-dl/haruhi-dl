# coding: utf-8
from __future__ import unicode_literals

import itertools
import re

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urllib_parse_unquote,
    compat_urlparse
)
from ..utils import (
    extract_attributes,
    ExtractorError,
    int_or_none,
    strip_or_none,
    unescapeHTML,
    unified_timestamp,
)


class PolskieRadioIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?polskieradio(?:24)?\.pl/\d+/\d+/Artykul/(?P<id>[0-9]+)'
    _TESTS = [{
        # like data-media={"type":"muzyka"}
        'url': 'http://www.polskieradio.pl/7/5102/Artykul/1587943,Prof-Andrzej-Nowak-o-historii-nie-da-sie-myslec-beznamietnie',
        'info_dict': {
            'id': '1587943',
            'title': 'Prof. Andrzej Nowak: o historii nie da się myśleć beznamiętnie',
            'description': 'md5:12f954edbf3120c5e7075e17bf9fc5c5',
        },
        'playlist': [{
            'md5': '2984ee6ce9046d91fc233bc1a864a09a',
            'info_dict': {
                'id': '1540576',
                'ext': 'mp3',
                'title': 'md5:d4623290d4ac983bf924061c75c23a0d',
                'timestamp': 1456594200,
                'upload_date': '20160227',
                'duration': 2364,
                'thumbnail': r're:^https?://static\.prsa\.pl/images/.*\.jpg$'
            },
        }],
    }, {
        # like data-media="{&quot;type&quot;:&quot;muzyka&quot;}"
        'url': 'https://www.polskieradio.pl/7/178/Artykul/2621155,Premiera-na-kanale-Radiobook-Krzyzacy-Henryka-Sienkiewicza',
        'info_dict': {
            'id': '2621155',
            'title': 'Premiera na kanale "Radiobook"! "Krzyżacy" Henryka Sienkiewicza',
            'description': 'md5:428acedfdafb09ce2a2665e0662d0771',
        },
        'playlist': [{
            'info_dict': {
                'id': '2611641',
                'ext': 'mp3',
                'title': 'Premiera na kanale "Radiobook": "Krzyżacy" Henryka Sienkiewicza (Kulturalna Jedynka)',
                'timestamp': 1605513000,
                'upload_date': '20201116',
            },
        }]
    }, {
        'url': 'http://polskieradio.pl/9/305/Artykul/1632955,Bardzo-popularne-slowo-remis',
        'only_matching': True,
    }, {
        'url': 'http://www.polskieradio.pl/7/5102/Artykul/1587943',
        'only_matching': True,
    }, {
        # with mp4 video
        'url': 'http://www.polskieradio.pl/9/299/Artykul/1634903,Brexit-Leszek-Miller-swiat-sie-nie-zawali-Europa-bedzie-trwac-dalej',
        'only_matching': True,
    }, {
        'url': 'https://polskieradio24.pl/130/4503/Artykul/2621876,Narusza-nasza-suwerennosc-Publicysci-o-uzaleznieniu-funduszy-UE-od-praworzadnosci',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)

        content = self._search_regex(
            r'(?s)<div[^>]+class="\s*this-article\s*"[^>]*>(.+?)<div[^>]+class="tags"[^>]*>',
            webpage, 'content')

        timestamp = unified_timestamp(self._html_search_regex(
            r'(?s)<span[^>]+id="datetime2"[^>]*>(.+?)</span>',
            webpage, 'timestamp', fatal=False))

        thumbnail_url = self._og_search_thumbnail(webpage)

        entries = []

        media_urls = set()

        title = self._og_search_title(webpage).strip()

        for data_media in re.findall(r'<[^>]+data-media=(["\']?)({[^>]+})\1', content):
            media = self._parse_json(unescapeHTML(data_media[1]), playlist_id, fatal=False)
            if not media.get('file'):
                continue
            media_url = self._proto_relative_url(media['file'], 'http:')
            if media_url in media_urls:
                continue
            media_urls.add(media_url)
            entries.append({
                'id': compat_str(media['id']),
                'url': media_url,
                'title': compat_urllib_parse_unquote(media['desc']) or title,
                'duration': int_or_none(media.get('length')),
                'vcodec': 'none' if media.get('provider') == 'audio' else None,
                'timestamp': timestamp,
                'thumbnail': thumbnail_url
            })

        description = strip_or_none(self._og_search_description(webpage))

        return self.playlist_result(entries, playlist_id, title, description)


class PolskieRadioCategoryIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?polskieradio\.pl/\d+(?:,[^/]+)?/(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.polskieradio.pl/7/5102,HISTORIA-ZYWA',
        'info_dict': {
            'id': '5102',
            'title': 'HISTORIA ŻYWA',
        },
        'playlist_mincount': 38,
    }, {
        'url': 'http://www.polskieradio.pl/7/4807',
        'info_dict': {
            'id': '4807',
            'title': 'Vademecum 1050. rocznicy Chrztu Polski'
        },
        'playlist_mincount': 5
    }, {
        'url': 'http://www.polskieradio.pl/7/129,Sygnaly-dnia?ref=source',
        'only_matching': True
    }, {
        'url': 'http://www.polskieradio.pl/37,RedakcjaKatolicka/4143,Kierunek-Krakow',
        'info_dict': {
            'id': '4143',
            'title': 'Kierunek Kraków',
        },
        'playlist_mincount': 61
    }, {
        'url': 'http://www.polskieradio.pl/10,czworka/214,muzyka',
        'info_dict': {
            'id': '214',
            'title': 'Muzyka',
        },
        'playlist_mincount': 61
    }, {
        'url': 'http://www.polskieradio.pl/7,Jedynka/5102,HISTORIA-ZYWA',
        'only_matching': True,
    }, {
        'url': 'http://www.polskieradio.pl/8,Dwojka/196,Publicystyka',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if PolskieRadioIE.suitable(url) else super(PolskieRadioCategoryIE, cls).suitable(url)

    def _entries(self, url, page, category_id):
        content = page
        for page_num in itertools.count(2):
            for a_entry, entry_id in re.findall(
                    r'(?s)<article[^>]+>.*?(<a[^>]+href=["\']/\d+/\d+/Artykul/(\d+)[^>]+>).*?</article>',
                    content):
                entry = extract_attributes(a_entry)
                href = entry.get('href')
                if not href:
                    continue
                yield self.url_result(
                    compat_urlparse.urljoin(url, href), PolskieRadioIE.ie_key(),
                    entry_id, entry.get('title'))
            mobj = re.search(
                r'<div[^>]+class=["\']next["\'][^>]*>\s*<a[^>]+href=(["\'])(?P<url>(?:(?!\1).)+)\1',
                content)
            if not mobj:
                break
            next_url = compat_urlparse.urljoin(url, mobj.group('url'))
            content = self._download_webpage(
                next_url, category_id, 'Downloading page %s' % page_num)

    def _real_extract(self, url):
        category_id = self._match_id(url)
        webpage = self._download_webpage(url, category_id)
        title = self._html_search_regex(
            r'<title>([^<]+) - [^<]+ - [^<]+</title>',
            webpage, 'title', fatal=False)
        return self.playlist_result(
            self._entries(url, webpage, category_id),
            category_id, title)


class PolskieRadioPlayerIE(InfoExtractor):
    IE_NAME = 'polskieradio:player'
    _VALID_URL = r'https?://player\.polskieradio\.pl/anteny/(?P<id>[^/]+)'

    _BASE_URL = 'https://player.polskieradio.pl'
    _PLAYER_URL = 'https://player.polskieradio.pl/main.bundle.js'
    _STATIONS_API_URL = 'https://apipr.polskieradio.pl/api/stacje'

    _TESTS = [{
        'url': 'https://player.polskieradio.pl/anteny/trojka',
        'info_dict': {
            'id': '3',
            'ext': 'm3u8',
            'title': 'Trójka',
        },
        'params': {
            'format': 'bestaudio',
            # endless stream
            'skip_download': True,
        },
    }]

    def _get_channel_list(self, channel_url='no_channel'):
        player_code = self._download_webpage(
            self._PLAYER_URL, channel_url,
            note='Downloading js player')
        channel_list = self._search_regex(
            r';var r="anteny",a=(\[.+?\])},', player_code, 'channel list')
        # weird regex replaces to hopefully make it a valid JSON string to parse

        # insert keys inside quotemarks ("key")
        channel_list = re.sub(r'([{,])(\w+):', r'\1"\2":', channel_list)
        # replace shortened booleans (!0, !1, !-0.1)
        channel_list = re.sub(r':\s*!-?(?:[1-9]\d*(?:\.\d+)?|0\.\d+)', r':true', channel_list)
        channel_list = re.sub(r':\s*!0', r':false', channel_list)

        return self._parse_json(channel_list, channel_url)

    def _real_extract(self, url):
        channel_url = self._match_id(url)
        channel_list = self._get_channel_list(channel_url)

        channel = None
        for f_channel in channel_list:
            if f_channel.get('url') == channel_url:
                channel = f_channel
                break

        if not channel:
            raise ExtractorError('Channel not found')

        station_list = self._download_json(self._STATIONS_API_URL, channel_url,
                                           note='Downloading stream url list',
                                           headers={
                                               'Accept': 'application/json',
                                               'Referer': url,
                                               'Origin': self._BASE_URL,
                                           })
        station = None
        for f_station in station_list:
            if f_station.get('Name') == (channel.get('streamName') or channel.get('name')):
                station = f_station
                break
        if not station:
            raise ExtractorError('Station not found even though we extracted channel (this is crazy)')

        formats = []
        # I have no idea who thought providing just a list of undescribed URLs is ok
        for stream_url in station['Streams']:
            if stream_url.startswith('//'):
                # assume https on protocol independent URLs
                stream_url = 'https:' + stream_url
            if stream_url.endswith('/playlist.m3u8'):
                formats.extend(self._extract_m3u8_formats(stream_url, channel_url, preference=500, live=True))
            elif stream_url.endswith('/manifest.f4m'):
                formats.extend(self._extract_mpd_formats(stream_url, channel_url))
            elif stream_url.endswith('/Manifest'):
                formats.extend(self._extract_ism_formats(stream_url, channel_url))
            elif stream_url.startswith('rtmp://') \
                    or stream_url.startswith('rtsp://') \
                    or stream_url.startswith('mms://'):
                formats.append({
                    'url': stream_url,
                    'preference': -1000,
                })
            else:
                formats.append({
                    'url': stream_url,
                    'preference': -500,
                })

        self._sort_formats(formats)

        return {
            'id': compat_str(channel['id']),
            'formats': formats,
            'title': channel.get('name') or channel.get('streamName'),
            'display_id': channel_url,
            'thumbnail': '%s/images/%s-color-logo.png' % (self._BASE_URL, channel_url),
            'is_live': True,
        }
