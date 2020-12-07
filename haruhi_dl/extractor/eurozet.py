# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    compat_str,
    ExtractorError,
    int_or_none,
    str_or_none,
    url_or_none,
)
import re


class EurozetArticleIE(InfoExtractor):
    IE_NAME = 'eurozet:article'
    _VALID_URL = r'https?://(?:[a-z]+\.)*(?<!player\.)(?:radiozet|chillizet|antyradio|planeta|meloradio)\.pl/[^/\s]+/(?P<id>[^/\s]+)'

    _DATA_RE = r'data-%s="(?P<content>.+?)"'

    _TESTS = [{
        'url': 'https://wiadomosci.radiozet.pl/Gosc-Radia-ZET/Margot-Trzeba-uzywac-mocnych-srodkow-zeby-byc-irytujacym-dla-wladzy',
        'info_dict': {
            'id': '131014',
            'ext': 'm3u8',
            'upload_date': '20200902',
            'title': 'Margot: Trzeba używać mocnych środków, żeby być irytującym dla władzy',
            'timestamp': 1599021420,
            'description': 'md5:d01ba0a7f10c84ed0c7921720411a886',
        },
    }]

    def _real_extract(self, url):
        page_slug = self._match_id(url)
        webpage = self._download_webpage(url, page_slug)

        video_id = self._html_search_regex(self._DATA_RE % 'storage-id', webpage, 'video id', group='content')
        info_dict = self._search_json_ld(webpage, video_id)

        formats = []
        for streaming_std in ('ss', 'dash', 'hls'):
            stream_url = self._html_search_regex(self._DATA_RE % ('source-%s' % streaming_std), webpage,
                                                 '%s manifest url' % streaming_std, group='content', fatal=False)
            if stream_url:
                if streaming_std == 'ss':
                    formats.extend(self._extract_ism_formats(stream_url, video_id))
                elif streaming_std == 'dash':
                    formats.extend(self._extract_mpd_formats(stream_url, video_id))
                elif streaming_std == 'hls':
                    formats.extend(self._extract_m3u8_formats(stream_url, video_id))

        self._sort_formats(formats)

        info_dict.update({
            'id': video_id,
            'formats': formats,
        })

        return info_dict


class EurozetPlayerStreamIE(InfoExtractor):
    IE_NAME = 'eurozet:player:stream'
    _VALID_URL = r'https?://player\.(?P<id>radiozet|chillizet|antyradio|meloradio)\.pl/?(?:\?[^#]*)?(?:#.*)?$'

    # this endpoint is on each player.[station].pl domain but it's always THE SAME FUCKING JSON WITH ALL STATIONS
    _STREAM_LIST = 'https://player.radiozet.pl/api/stations'

    _TESTS = [{
        'url': 'https://player.antyradio.pl/',
        'info_dict': {
            'id': '11662',
            'ext': 'livx',
            'title': 'Antyradio',
        },
    }, {
        'url': 'https://player.radiozet.pl/?fbclid=aoeu',
        'only_matching': True,
    }, {
        'url': 'https://player.chillizet.pl/#',
        'only_matching': True,
    }, {
        'url': 'https://player.meloradio.pl',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        station_codename = self._match_id(url)
        station_list = self._download_json(self._STREAM_LIST, station_codename, 'Downloading station list')

        station = None
        for f_station in station_list:
            if f_station.get('station') == station_codename:
                station = f_station
                break
        if not station:
            raise ExtractorError('Station not found')

        return {
            'id': str_or_none(station.get('node_id')),
            'title': station.get('title')[len('Player '):],
            'url': station['player']['stream'],
            'is_live': True,
        }


class EurozetPlayerPodcastIE(InfoExtractor):
    IE_NAME = 'eurozet:player:podcast'
    _VALID_URL = r'https?://player\.(?P<station>radiozet|chillizet|antyradio|meloradio)\.pl/Podcasty/(?P<series>[^/\s#\?]+/)?(?P<id>[^/\s#\?]+)'

    _PODCAST_LIST_URL_TPL = 'https://player.%(station)s.pl/api/podcasts/getPodcastListByProgram/(node)/%(podcast_node)s/(station)/%(station)s'

    _TESTS = [{
        'url': 'https://player.meloradio.pl/Podcasty/Horoskop-wrozbity-Macieja',
        'info_dict': {
            'id': '14501',
            'title': 'Horoskop wróżbity Macieja',
            'description': 'Wróżbita Maciej Skrzątek od poniedziałku do piątku o 9:15 w Meloradiu prezentuje starannie przygotowany horoskop dla wszystkich znaków zodiaku.',
        },
        'playlist_mincount': 300,
    }, {
        'url': 'https://player.antyradio.pl/Podcasty/Historia-niejednej-piosenki/Imagine-Johna-Lennona-w-zaskakujacej-wersji',
        'info_dict': {
            'id': '60358',
            'ext': 'mp3',
            'description': 'Tomasz Kasprzyk przedstawia ciekawostki i nieznane historie na temat powstania wielkich rockowych przebojów, ich coverów, autorów i wykonawców.',
            'upload_date': '20201203',
            'timestamp': 1606989840,
            'title': 'Imagine Johna Lennona w zaskakującej wersji',
        },
    }, {
        'url': 'https://player.radiozet.pl/Podcasty/Listy-do-redakcji-Radia-ZET-audycja-nie-do-konca-powazna/',
        'only_matching': True,
    }, {
        'url': 'https://player.chillizet.pl/Podcasty/Tylko-dla-doroslych/Przypadek-Elliota-Page-a-rozmowa-o-transplciowosci-z-Emilia-Wisniewska',
        'only_matching': True,
    }]

    def _podcast_to_info_dict(self, podcast_dict, station):
        return {
            'id': compat_str(podcast_dict['node_id']),
            'title': str_or_none(podcast_dict.get('title', '')),
            'url': url_or_none(podcast_dict['player']['stream']),
            'duration': int_or_none(podcast_dict['player']['duration']),
            'timestamp': int_or_none(podcast_dict.get('published_date')),
            'webpage_url': 'https://player.%s.pl%s' % (station, podcast_dict.get('url')),
        }

    def _download_podcast_list(self, station, podcast_node, offset=0):
        list_url = self._PODCAST_LIST_URL_TPL % {'station': station, 'podcast_node': podcast_node}
        if offset > 0:
            list_url += '/(offset)/%d' % offset
        return self._download_json(list_url, podcast_node,
                                   'Downloading podcast list%s' % (' (page #%d)' % (offset + 1) if offset > 0 else ''))

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        station_codename, series_slug, page_slug = mobj.group('station', 'series', 'id')

        no_playlist = False if not series_slug else self._downloader.params.get('noplaylist', True)

        webpage = self._download_webpage(url, page_slug)
        podcast_node = self._html_search_regex(r'<div id="player"[^>]+data-program="(\d+)"', webpage, 'podcast list id')
        podcast_id = self._html_search_regex(r'<div id="player"[^>]+data-id="(\d+)"', webpage, 'podcast id')

        podcast_list = self._download_podcast_list(station_codename, podcast_node)

        program = podcast_list['data'][0]['program']
        info_dict = {
            'id': podcast_node,
            'title': program.get('title', '').strip(),
            'description': program.get('desc', '').strip(),
        }

        if no_playlist:
            for f_podcast in podcast_list['data']:
                if str_or_none(f_podcast.get('node_id')) == podcast_id:
                    info_dict.update(self._podcast_to_info_dict(f_podcast, station_codename))
                    return info_dict
        podcasts = podcast_list['data']

        if len(podcasts) < podcast_list['info']['number_of_podcasts']:
            pages = (podcast_list['info']['number_of_podcasts'] - len(podcasts)) / len(podcasts)
            pages = int(pages) + 2 if int(pages) != pages else int(pages) + 1
            for page in range(1, pages):
                podcast_list = self._download_podcast_list(station_codename, podcast_node, offset=page)
                if no_playlist:
                    for f_podcast in podcast_list['data']:
                        if str_or_none(f_podcast.get('node_id')) == podcast_id:
                            info_dict.update(self._podcast_to_info_dict(f_podcast, station_codename))
                            return info_dict
                else:
                    podcasts.extend(podcast_list['data'])

        if no_playlist:
            raise ExtractorError('Podcast episode not found')

        info_dict.update({
            '_type': 'playlist',
            'entries': [self._podcast_to_info_dict(x, station_codename) for x in podcasts],
        })
        return info_dict


class EurozetPlayerMusicStreamIE(InfoExtractor):
    IE_NAME = 'eurozet:player:musicstream'
    _VALID_URL = r'https?://player\.(?P<station>radiozet|chillizet|antyradio|meloradio)\.pl/Kanaly-muzyczne/(?P<id>[^/\s#\?]+)'

    _TESTS = [{
        'url': 'https://player.radiozet.pl/Kanaly-muzyczne/Radio-ZET-Party',
        'info_dict': {
            'id': '12356',
            'ext': 'mp3',
            'title': 'Radio ZET Party',
            'description': 'Imprezowe klasyki i nowości do dobrej zabawy',
        },
    }, {
        'url': 'https://player.antyradio.pl/Kanaly-muzyczne/Antyradio-Hard',
        'info_dict': {
            'id': '13908',
            'ext': 'mp3',
            'title': 'Antyradio Hard',
            'description': 'Muzyka dla fanów ostrych brzmień',
        },
    }, {
        'url': 'https://player.meloradio.pl/Kanaly-muzyczne/Meloradio-Acoustic',
        'only_matching': True,
    }, {
        'url': 'https://player.chillizet.pl/Kanaly-muzyczne/Chillizet-Covers',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        station_codename, page_slug = mobj.group('station', 'id')

        webpage = self._download_webpage(url, page_slug)
        stream_id = self._html_search_regex(r'<div id="player"[^>]+data-id="(\d+)"', webpage, 'stream id')

        data = self._download_json('https://player.chillizet.pl/api/channels/(channel)/%s' % stream_id, stream_id)[0]

        return {
            'id': stream_id,
            'url': data['player']['stream'],
            'title': data['title'],
            'alt_title': data.get('short_desc'),
            'description': data.get('desc'),
            'is_live': True,
        }
