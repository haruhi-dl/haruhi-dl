# coding: utf-8
from __future__ import unicode_literals

import itertools
import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    ExtractorError,
    get_element_by_attribute,
    int_or_none,
    orderedSet,
    str_or_none,
)


class TVPIE(InfoExtractor):
    IE_NAME = 'tvp'
    IE_DESC = 'Telewizja Polska'
    _VALID_URL = r'https?://(?:[^/]+\.)?(?:tvp(?:parlament)?\.(?:pl|info)|polandin\.com)/(?:video/(?:[^,\s]*,)*|(?:(?!\d+/)[^/]+/)*)(?P<id>\d+)'

    _TESTS = [{
        # TVPlayer 2 in js wrapper
        'url': 'https://vod.tvp.pl/video/czas-honoru,i-seria-odc-13,194536',
        'md5': 'a21eb0aa862f25414430f15fdfb9e76c',
        'info_dict': {
            'id': '194536',
            'ext': 'mp4',
            'title': 'Czas honoru, odc. 13 – Władek',
            'description': 'md5:437f48b93558370b031740546b696e24',
        },
    }, {
        # TVPlayer legacy
        'url': 'http://www.tvp.pl/there-can-be-anything-so-i-shortened-it/17916176',
        'md5': 'b0005b542e5b4de643a9690326ab1257',
        'info_dict': {
            'id': '17916176',
            'ext': 'mp4',
            'title': 'TVP Gorzów pokaże filmy studentów z podroży dookoła świata',
            'description': 'TVP Gorzów pokaże filmy studentów z podroży dookoła świata',
        },
    }, {
        # TVPlayer 2 in iframe
        'url': 'https://wiadomosci.tvp.pl/50725617/dzieci-na-sprzedaz-dla-homoseksualistow',
        'md5': '624b78643e3cd039011fe23d76f0416e',
        'info_dict': {
            'id': '50725617',
            'ext': 'mp4',
            'title': 'Wiadomości, Dzieci na sprzedaż dla homoseksualistów',
            'description': 'md5:7d318eef04e55ddd9f87a8488ac7d590',
        },
    }, {
        # TVPlayer 2 in client-side rendered website (regional)
        'url': 'https://warszawa.tvp.pl/25804446/studio-yayo',
        'md5': '883c409691c6610bdc8f464fab45a9a9',
        'info_dict': {
            'id': '25804446',
            'ext': 'mp4',
            'title': 'Studio Yayo',
            'upload_date': '20160616',
            'timestamp': 1466075700,
        }
    }, {
        # client-side rendered (regional) program (playlist) page
        'url': 'https://opole.tvp.pl/9660819/rozmowa-dnia',
        'info_dict': {
            'id': '9660819',
            'description': 'Od poniedziałku do piątku o 18:55',
            'title': 'Rozmowa dnia',
        },
        'playlist_mincount': 1800,
        'params': {
            'skip_download': True,
        }
    }, {
        'url': 'http://vod.tvp.pl/seriale/obyczajowe/na-sygnale/sezon-2-27-/odc-39/17834272',
        'only_matching': True,
    }, {
        'url': 'http://wiadomosci.tvp.pl/25169746/24052016-1200',
        'only_matching': True,
    }, {
        'url': 'http://krakow.tvp.pl/25511623/25lecie-mck-wyjatkowe-miejsce-na-mapie-krakowa',
        'only_matching': True,
    }, {
        'url': 'http://teleexpress.tvp.pl/25522307/wierni-wzieli-udzial-w-procesjach',
        'only_matching': True,
    }, {
        'url': 'http://sport.tvp.pl/25522165/krychowiak-uspokaja-w-sprawie-kontuzji-dwa-tygodnie-to-maksimum',
        'only_matching': True,
    }, {
        'url': 'http://www.tvp.info/25511919/trwa-rewolucja-wladza-zdecydowala-sie-na-pogwalcenie-konstytucji',
        'only_matching': True,
    }, {
        'url': 'https://tvp.info/49193823/teczowe-flagi-na-pomnikach-prokuratura-wszczela-postepowanie-wieszwiecej',
        'only_matching': True,
    }, {
        'url': 'https://www.tvpparlament.pl/retransmisje-vod/inne/wizyta-premiera-mateusza-morawieckiego-w-firmie-berotu-sp-z-oo/48857277',
        'only_matching': True,
    }, {
        'url': 'https://polandin.com/47942651/pln-10-billion-in-subsidies-transferred-to-companies-pm',
        'only_matching': True,
    }]

    def _parse_vue_website_data(self, webpage, page_id):
        website_data = self._search_regex([
            r'window\.__websiteData\s*=\s*({(?:.|\s)+?});',
        ], webpage, 'website data')
        if not website_data:
            return None
        # "sanitize" "JSON" trailing comma before parsing
        website_data = re.sub(r',\s+}$', '}', website_data)
        # replace JSON string with parsed dict
        website_data = self._parse_json(website_data, page_id)
        return website_data

    def _extract_vue_video(self, video_data, page_id=None):
        thumbnails = []
        image = video_data.get('image')
        if image:
            for thumb in (image if isinstance(image, list) else [image]):
                thmb_url = str_or_none(thumb.get('url'))
                if thmb_url:
                    thumbnails.append({
                        'url': thmb_url,
                    })
        return {
            '_type': 'url_transparent',
            'id': str_or_none(video_data.get('_id') or page_id),
            'url': 'tvp:' + str_or_none(video_data.get('_id') or page_id),
            'ie_key': 'TVPEmbed',
            'title': str_or_none(video_data.get('title')),
            'description': str_or_none(video_data.get('lead')),
            'timestamp': int_or_none(video_data.get('release_date_long')),
            'duration': int_or_none(video_data.get('duration')),
            'thumbnails': thumbnails,
        }

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(url, page_id)
        if '//s.tvp.pl/files/portale-v4/regiony-tvp-pl' in webpage:
            # vue client-side rendered sites (all regional pages)
            video_data = self._search_regex([
                r'window\.__newsData\s*=\s*({(?:.|\s)+?});',
            ], webpage, 'video data', default=None)
            if video_data:
                return self._extract_vue_video(
                    self._parse_json(video_data, page_id),
                    page_id=page_id)
            # paged playlists
            website_data = self._parse_vue_website_data(webpage, page_id)
            if website_data:
                entries = []
                if website_data.get('latestVideo'):
                    entries.append(self._extract_vue_video(website_data['latestVideo']))
                for video in website_data.get('videos') or []:
                    entries.append(self._extract_vue_video(video))
                items_total_count = int_or_none(website_data.get('items_total_count'))
                items_per_page = int_or_none(website_data.get('items_per_page'))
                if items_total_count > len(entries) - 1:
                    pages = items_total_count / items_per_page
                    if pages != int(pages):
                        pages = int(pages) + 1
                    for page in range(2, pages):
                        page_website_data = self._parse_vue_website_data(
                            # seriously, this thing is rendered on the client and requires to reload page
                            # when flipping the page, instead of just loading new pages with xhr or sth
                            # (they already even import axios!)
                            self._download_webpage(url, page_id, note='Downloading page #%d' % page,
                                                   query={'page': page}),
                            page_id)
                        for video in page_website_data.get('videos') or []:
                            entries.append(self._extract_vue_video(video))

                return {
                    '_type': 'playlist',
                    'id': page_id,
                    'title': str_or_none(website_data.get('title')),
                    'description': str_or_none(website_data.get('lead')),
                    'entries': entries,
                }
            raise ExtractorError('Could not extract video/website data')
        else:
            # classic server-site rendered sites
            video_id = self._search_regex([
                r'<iframe[^>]+src="[^"]*?embed\.php\?(?:[^&]+&)*ID=(\d+)',
                r'<iframe[^>]+src="[^"]*?object_id=(\d+)',
                r"object_id\s*:\s*'(\d+)'",
                r'data-video-id="(\d+)"'], webpage, 'video id', default=page_id)
            return {
                '_type': 'url_transparent',
                'url': 'tvp:' + video_id,
                'description': self._og_search_description(
                    webpage, default=None) or self._html_search_meta(
                    'description', webpage, default=None),
                'thumbnail': self._og_search_thumbnail(webpage, default=None),
                'ie_key': 'TVPEmbed',
            }


class TVPStreamIE(InfoExtractor):
    IE_NAME = 'tvp:stream'
    _VALID_URL = r'(?:tvpstream:|https?://tvpstream\.vod\.tvp\.pl/(?:\?(?:[^&]+[&;])*channel_id=)?)(?P<id>\d*)'
    _TESTS = [{
        # untestable as "video" id changes many times across a day
        'url': 'https://tvpstream.vod.tvp.pl/?channel_id=1455',
        'only_matching': True,
    }, {
        'url': 'tvpstream:39821455',
        'only_matching': True,
    }, {
        # the default stream when you provide no channel_id, most probably TVP Info
        'url': 'tvpstream:',
        'only_matching': True,
    }, {
        'url': 'https://tvpstream.vod.tvp.pl/',
        'only_matching': True,
    }]

    _PLAYER_BOX_RE = r'<div\s[^>]*id\s*=\s*["\']?tvp_player_box["\']?[^>]+data-%s-id\s*=\s*["\']?(\d+)'
    _BUTTON_RE = r'<div\s[^>]*data-channel-id=["\']?%s["\']?[^>]*\sdata-title=(?:"([^"]*)"|\'([^\']*)\')[^>]*\sdata-stationname=(?:"([^"]*)"|\'([^\']*)\')'

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        channel_id = mobj.group('id')
        channel_url = 'http%s://tvpstream.vod.tvp.pl/?channel_id=%s' % (
            '' if self._downloader.params.get('prefer_insecure', False) else 's',
            channel_id or 'default')
        webpage = self._download_webpage(channel_url, channel_id, 'Downloading channel webpage')
        if not channel_id:
            channel_id = self._search_regex(self._PLAYER_BOX_RE % 'channel',
                                            webpage, 'default channel id')
        video_id = self._search_regex(self._PLAYER_BOX_RE % 'video',
                                      webpage, 'video id')
        mobj = re.search(self._BUTTON_RE % (re.escape(channel_id)), webpage)
        if mobj:
            audition_title, station_name = mobj.group(1, 2)
        else:
            self.report_warning('Could not extract audition title and station name')
            audition_title = station_name = ''
        return {
            '_type': 'url_transparent',
            'id': channel_id,
            'url': 'tvp:%s' % video_id,
            'title': audition_title,
            'alt_title': station_name,
            'is_live': True,
            'ie_key': 'TVPEmbed',
        }


class TVPEmbedIE(InfoExtractor):
    IE_NAME = 'tvp:embed'
    IE_DESC = 'Telewizja Polska'
    _VALID_URL = r'(?:tvp:|https?://(?:[^/]+\.)?tvp(?:parlament)?\.(?:pl|info)/sess/(?:tvplayer\.php\?.*?object_id|TVPlayer2/embed\.php\?.*ID)=)(?P<id>\d+)'

    _TESTS = [{
        'url': 'tvp:194536',
        'md5': 'a21eb0aa862f25414430f15fdfb9e76c',
        'info_dict': {
            'id': '194536',
            'ext': 'mp4',
            'title': 'Czas honoru, odc. 13 – Władek',
        },
    }, {
        # not available
        'url': 'http://www.tvp.pl/sess/tvplayer.php?object_id=22670268',
        'md5': '8c9cd59d16edabf39331f93bf8a766c7',
        'info_dict': {
            'id': '22670268',
            'ext': 'mp4',
            'title': 'Panorama, 07.12.2015, 15:40',
        },
        'skip': 'Transmisja została zakończona lub materiał niedostępny',
    }, {
        # TVPlayer2 (new) URL
        'url': 'https://tvp.info/sess/TVPlayer2/embed.php?ID=50595757',
        'only_matching': True,
    }, {
        'url': 'tvp:22670268',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            'http://www.tvp.pl/sess/tvplayer.php?object_id=%s' % video_id, video_id)

        error = self._html_search_regex(
            r'(?s)<p[^>]+\bclass=["\']notAvailable__text["\'][^>]*>(.+?)</p>',
            webpage, 'error', default=None) or clean_html(
            get_element_by_attribute('class', 'msg error', webpage))
        if error:
            raise ExtractorError('%s said: %s' % (
                self.IE_NAME, clean_html(error)), expected=True)

        title = self._search_regex(
            r'name\s*:\s*([\'"])Title\1\s*,\s*value\s*:\s*\1(?P<title>.+?)\1',
            webpage, 'title', group='title')
        series_title = self._search_regex(
            r'name\s*:\s*([\'"])SeriesTitle\1\s*,\s*value\s*:\s*\1(?P<series>.+?)\1',
            webpage, 'series', group='series', default=None)
        if series_title:
            title = '%s, %s' % (series_title, title)

        thumbnail = self._search_regex(
            r"poster\s*:\s*'([^']+)'", webpage, 'thumbnail', default=None)

        video_url = self._search_regex(
            r'0:{src:([\'"])(?P<url>.*?)\1', webpage,
            'formats', group='url', default=None)
        if not video_url or 'material_niedostepny.mp4' in video_url:
            video_url = self._download_json(
                'http://www.tvp.pl/pub/stat/videofileinfo?video_id=%s' % video_id,
                video_id)['video_url']

        formats = []
        video_url_base = self._search_regex(
            r'(https?://.+?/video)(?:\.(?:ism|f4m|m3u8)|-\d+\.mp4)',
            video_url, 'video base url', default=None)
        if video_url_base:
            # TODO: <Group> found instead of <AdaptationSet> in MPD manifest.
            # It's not mentioned in MPEG-DASH standard. Figure that out.
            # formats.extend(self._extract_mpd_formats(
            #     video_url_base + '.ism/video.mpd',
            #     video_id, mpd_id='dash', fatal=False))
            formats.extend(self._extract_ism_formats(
                video_url_base + '.ism/Manifest',
                video_id, 'mss', fatal=False))
            formats.extend(self._extract_f4m_formats(
                video_url_base + '.ism/video.f4m',
                video_id, f4m_id='hds', fatal=False))
            m3u8_formats = self._extract_m3u8_formats(
                video_url_base + '.ism/video.m3u8', video_id,
                'mp4', 'm3u8_native', m3u8_id='hls', fatal=False)
            self._sort_formats(m3u8_formats)
            m3u8_formats = list(filter(
                lambda f: f.get('vcodec') != 'none', m3u8_formats))
            formats.extend(m3u8_formats)
            for i, m3u8_format in enumerate(m3u8_formats, 2):
                http_url = '%s-%d.mp4' % (video_url_base, i)
                if self._is_valid_url(http_url, video_id):
                    f = m3u8_format.copy()
                    f.update({
                        'url': http_url,
                        'format_id': f['format_id'].replace('hls', 'http'),
                        'protocol': 'http',
                    })
                    formats.append(f)
        else:
            formats = [{
                'format_id': 'direct',
                'url': video_url,
                'ext': determine_ext(video_url, 'mp4'),
            }]

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'formats': formats,
        }


class TVPWebsiteIE(InfoExtractor):
    IE_NAME = 'tvp:series'
    _VALID_URL = r'https?://vod\.tvp\.pl/website/(?P<display_id>[^,]+),(?P<id>\d+)'

    _TESTS = [{
        # series
        'url': 'https://vod.tvp.pl/website/lzy-cennet,38678312/video',
        'info_dict': {
            'id': '38678312',
        },
        'playlist_count': 115,
    }, {
        # film
        'url': 'https://vod.tvp.pl/website/gloria,35139666',
        'info_dict': {
            'id': '36637049',
            'ext': 'mp4',
            'title': 'Gloria, Gloria',
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': ['TVPEmbed'],
    }, {
        'url': 'https://vod.tvp.pl/website/lzy-cennet,38678312',
        'only_matching': True,
    }]

    def _entries(self, display_id, playlist_id):
        url = 'https://vod.tvp.pl/website/%s,%s/video' % (display_id, playlist_id)
        for page_num in itertools.count(1):
            page = self._download_webpage(
                url, display_id, 'Downloading page %d' % page_num,
                query={'page': page_num})

            video_ids = orderedSet(re.findall(
                r'<a[^>]+\bhref=["\']/video/%s,[^,]+,(\d+)' % display_id,
                page))

            if not video_ids:
                break

            for video_id in video_ids:
                yield self.url_result(
                    'tvp:%s' % video_id, ie=TVPEmbedIE.ie_key(),
                    video_id=video_id)

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        display_id, playlist_id = mobj.group('display_id', 'id')
        return self.playlist_result(
            self._entries(display_id, playlist_id), playlist_id)
