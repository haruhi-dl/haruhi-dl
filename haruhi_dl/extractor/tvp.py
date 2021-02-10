# coding: utf-8
from __future__ import unicode_literals

import random
import re

from .common import InfoExtractor
from ..utils import (
    compat_str,
    determine_ext,
    ExtractorError,
    int_or_none,
    str_or_none,
    try_get,
    unescapeHTML,
)


class TVPIE(InfoExtractor):
    IE_NAME = 'tvp'
    IE_DESC = 'Telewizja Polska'
    _VALID_URL = r'https?://(?:[^/]+\.)?(?:tvp(?:parlament)?\.(?:pl|info)|polandin\.com)/(?:video/(?:[^,\s]*,)*|(?:(?!\d+/)[^/]+/)*)(?P<id>\d+)'

    _TESTS = [{
        # TVPlayer 2 in js wrapper
        'url': 'https://vod.tvp.pl/video/czas-honoru,i-seria-odc-13,194536',
        'info_dict': {
            'id': '194536',
            'ext': 'mp4',
            'title': 'Czas honoru, odc. 13 – Władek',
            'description': 'md5:437f48b93558370b031740546b696e24',
            'age_limit': 12,
        },
    }, {
        # TVPlayer legacy
        'url': 'http://www.tvp.pl/there-can-be-anything-so-i-shortened-it/17916176',
        'info_dict': {
            'id': '17916176',
            'ext': 'mp4',
            'title': 'TVP Gorzów pokaże filmy studentów z podroży dookoła świata',
            'description': 'TVP Gorzów pokaże filmy studentów z podroży dookoła świata',
        },
    }, {
        # TVPlayer 2 in iframe
        'url': 'https://wiadomosci.tvp.pl/50725617/dzieci-na-sprzedaz-dla-homoseksualistow',
        'info_dict': {
            'id': '50725617',
            'ext': 'mp4',
            'title': 'Dzieci na sprzedaż dla homoseksualistów',
            'description': 'md5:7d318eef04e55ddd9f87a8488ac7d590',
            'age_limit': 12,
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
        # ABC-specific video embeding
        'url': 'https://abc.tvp.pl/48636269/zubry-odc-124',
        'info_dict': {
            'id': '48320456',
            'ext': 'mp4',
            'title': 'Teleranek, Żubr',
            'description': 'W tym Teleranku przedstawimy Wam największe dziko żyjącego ssaki Europy. Mowa o żubrach Ponieważ zostało już bardzo niewiele osobników, ten gatunek jest objęty ścisłą ochroną. Opowiemy Wam o specyfice tych zwierząt i pokażemy je z bliska. Dlaczego żubry są tak rzadkie i co spowodowało, że są uznawane za narodowe zwierzęta Polski?',
        },
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
                r'data-video-id="(\d+)"',

                # abc.tvp.pl - somehow there are more than one video IDs that seem to be the same video?
                # the first one is referenced to as "copyid", and seems to be unused by the website
                r'<script>\s*tvpabc\.video\.init\(\s*\d+,\s*(\d+)\s*\)\s*</script>',
            ], webpage, 'video id', default=page_id)
            return {
                '_type': 'url_transparent',
                'url': 'tvp:' + video_id,
                'description': self._og_search_description(
                    webpage, default=None) or (self._html_search_meta(
                        'description', webpage, default=None)
                        if '//s.tvp.pl/files/portal/v' in webpage else None),
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
    _VALID_URL = r'''(?x)
        (?:
            tvp:
            |https?://
                (?:[^/]+\.)?
                (?:tvp(?:parlament)?\.pl|tvp\.info|polandin\.com)/
                (?:sess/
                        (?:tvplayer\.php\?.*?object_id
                        |TVPlayer2/(?:embed|api)\.php\?.*[Ii][Dd])
                    |shared/details\.php\?.*?object_id)
                =)
        (?P<id>\d+)
    '''

    _TESTS = [{
        'url': 'tvp:194536',
        'md5': 'a21eb0aa862f25414430f15fdfb9e76c',
        'info_dict': {
            'id': '194536',
            'ext': 'mp4',
            'title': 'Czas honoru, odc. 13 – Władek',
            'description': 'Czesław prosi Marię o dostarczenie Władkowi zarazki tyfusu. Jeśli zachoruje zostanie przewieziony do szpitala skąd łatwiej będzie go odbić. Czy matka zdecyduje się zarazić syna?',
            'age_limit': 12,
        },
    }, {
        'url': 'https://www.tvp.pl/sess/tvplayer.php?object_id=51247504&amp;autoplay=false',
        'info_dict': {
            'id': '51247504',
            'ext': 'mp4',
            'title': 'Razmova 091220',
        },
    }, {
        # TVPlayer2 embed URL
        'url': 'https://tvp.info/sess/TVPlayer2/embed.php?ID=50595757',
        'only_matching': True,
    }, {
        'url': 'https://wiadomosci.tvp.pl/sess/TVPlayer2/api.php?id=51233452',
        'only_matching': True,
    }, {
        # pulsembed on dziennik.pl
        'url': 'https://www.tvp.pl/shared/details.php?copy_id=52205981&object_id=52204505&autoplay=false&is_muted=false&allowfullscreen=true&template=external-embed/video/iframe-video.html',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_urls(webpage, **kw):
        return [
            m.group('embed')
            for m
            in re.finditer(
                r'(?x)<iframe[^>]+?src=(["\'])(?P<embed>%s)' % TVPEmbedIE._VALID_URL[4:],
                webpage)]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # it could be anything that is a valid JS function name
        callback = random.choice((
            'jebac_pis',
            'jebacpis',
            'ziobro',
            'sasin70',
            'sasin_przejebal_70_milionow_PLN',
            'tvp_is_a_state_propaganda_service',
        ))

        webpage = self._download_webpage(
            ('https://www.tvp.pl/sess/TVPlayer2/api.php?id=%s'
             + '&@method=getTvpConfig&@callback=%s') % (video_id, callback), video_id)

        # stripping JSONP padding
        datastr = webpage[15 + len(callback):-3]
        if datastr.startswith('null,'):
            error = self._parse_json(datastr[5:], video_id)
            raise ExtractorError(error[0]['desc'])

        content = self._parse_json(datastr, video_id)['content']
        info = content['info']

        formats = []
        for file in content['files']:
            video_url = file['url']
            if video_url.endswith('.m3u8'):
                formats.extend(self._extract_m3u8_formats(video_url, video_id, m3u8_id='hls'))
            elif video_url.endswith('.mpd'):
                formats.extend(self._extract_mpd_formats(video_url, video_id, mpd_id='dash'))
            elif video_url.endswith('.f4m'):
                formats.extend(self._extract_f4m_formats(video_url, video_id, f4m_id='hds'))
            elif video_url.endswith('.ism/manifest'):
                formats.extend(self._extract_ism_formats(video_url, video_id, ism_id='mss'))
            else:
                # probably just mp4 versions
                quality = file.get('quality', {})
                formats.append({
                    'format_id': 'direct',
                    'url': video_url,
                    'ext': determine_ext(video_url, 'mp4'),
                    'fps': int_or_none(quality.get('fps')),
                    'tbr': int_or_none(quality.get('bitrate')),
                    'width': int_or_none(quality.get('width')),
                    'height': int_or_none(quality.get('height')),
                })

        self._sort_formats(formats)

        title = try_get(info, (
            lambda x: x['subtitle'],
            lambda x: x['title'],
            lambda x: x['seoTitle'],
        ), compat_str)
        description = try_get(info, (
            lambda x: x['description'],
            lambda x: x['seoDescription'],
        ), compat_str)
        thumbnails = []
        for thumb in content.get('posters') or ():
            thumb_url = thumb.get('src')
            # TVP, you're drunk, go home
            if '{width}' not in thumb_url and '{height}' not in thumb_url:
                thumbnails.append({
                    'url': thumb.get('src'),
                    'width': thumb.get('width'),
                    'height': thumb.get('height'),
                })
        age_limit = try_get(info, lambda x: x['ageGroup']['minAge'], int)
        if age_limit == 1:
            age_limit = 0
        is_live = try_get(info, lambda x: x['isLive'], bool)
        duration = try_get(info, lambda x: x['duration'], int) if not is_live else None

        info_dict = {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnails': thumbnails,
            'age_limit': age_limit,
            'is_live': is_live,
            'duration': duration,
            'formats': formats,
        }

        # vod.tvp.pl
        if info.get('vortalName') == 'vod':
            info_dict.update({
                'title': '%s, %s' % (info.get('title'), info.get('subtitle')),
                'series': info.get('title'),
                'season': info.get('season'),
                'episode_number': info.get('episode'),
            })

        return info_dict


class TVPWebsiteIE(InfoExtractor):
    IE_NAME = 'tvp:series'
    _VALID_URL = r'https?://vod\.tvp\.pl/website/(?P<display_id>[^,]+),(?P<id>\d+)'

    _TESTS = [{
        # series
        'url': 'https://vod.tvp.pl/website/wspaniale-stulecie,17069012/video',
        'info_dict': {
            'id': '17069012',
            'title': 'Wspaniałe stulecie',
            'description': 'md5:f10ddf01760c829274ae4e511334d53e',
        },
        'playlist_count': 312,
    }, {
        # film
        'url': 'https://vod.tvp.pl/website/krzysztof-krawczyk-cale-moje-zycie,51374466',
        'info_dict': {
            'id': '51374509',
            'ext': 'mp4',
            'title': 'Krzysztof Krawczyk – całe moje życie',
            'description': 'Dokumentalna opowieść o karierze Krzysztofa Krawczyka, jednego z najpopularniejszych wykonawców muzyki pop na polskiej scenie. Artysta ma na  swoimi koncie wiele przebojów. W filmie wykorzystano unikatowe materiały archiwalne.',
            'age_limit': 12,
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': ['TVPEmbed'],
    }, {
        'url': 'https://vod.tvp.pl/website/lzy-cennet,38678312',
        'only_matching': True,
    }]

    _API_BASE = 'https://apivod.tvp.pl'

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        display_id, playlist_id = mobj.group('display_id', 'id')

        headers = {
            'Authorization': 'Basic YXBpOnZvZA==',
            'User-Agent': 'okhttp/4.2.2',
        }
        data = self._download_json(self._API_BASE + '/tv/v2/website/%s' % playlist_id,
                                   playlist_id, 'Downloading series metadata', headers=headers)

        info_dict = {}
        entries = []
        pages_count = None
        selected_filter = 'default'
        selected_sorting = '10'  # the app does that for some reason
        for d in data['data']:
            if d['type'] == 'page':
                pages_count = d['pagesCount']
                selected_filter = d.get('selected_filter', selected_filter)
                for sorting in d.get('sortOptions', ()):
                    if sorting.get('selected') is True:
                        selected_sorting = sorting.get('value', selected_sorting)
                info_dict.update({
                    'title': d['title'],
                })
            elif d['type'] == 'website':
                info_dict.update({
                    'id': compat_str(d['id']),
                    'description': unescapeHTML(d['lead']),
                })
            elif d['type'] == 'listing' and d['title'] == 'Odcinki':
                # series
                # broken, just TVP things
                # for ep in d['elements']:
                # entries.append(self._episode_to_entry(ep))
                info_dict.update({
                    '_type': 'playlist',
                })
            elif d['type'] == 'listing' and d['title'] == 'Wideo':
                # single movie
                info_dict.update(self._episode_to_entry(d['elements'][0]))
                return info_dict

        # if pages_count > 1:
        for page in range(1, pages_count + 1):
            ep_list = self._download_json(self._API_BASE + '/tv/v2/website-videos/%s/%d/%s/%s' % (playlist_id, page, '10', selected_filter),
                                          playlist_id, 'Downloading episodes page %d' % page, headers=headers)
            for ep in ep_list['data']:
                if ep.get('type') == 'video':
                    entries.append(self._episode_to_entry(ep))

        info_dict.update({
            'entries': entries,
        })
        return info_dict

    def _episode_to_entry(self, ep):
        age_limit = None
        for label in ep.get('label', ()):
            if label.get('type') == 'PEGI':
                age_limit = int_or_none(label.get('text'))
        return {
            '_type': 'url_transparent',
            'ie_key': 'TVPEmbed',
            'url': 'tvp:' + compat_str(ep['id']),
            'id': compat_str(ep['id']),
            'title': ep['title'],
            'alt_title': ep.get('subtitle'),
            'description': unescapeHTML(ep.get('lead')),
            'is_live': ep.get('is_live', False),
            'age_limit': age_limit,
        }
