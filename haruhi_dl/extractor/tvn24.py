# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    extract_attributes,
    ExtractorError,
    int_or_none,
    NO_DEFAULT,
    unescapeHTML,
)
from ..playwright import PlaywrightHelper


class TVN24IE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?P<domain>(?:(?:[^/]+)\.)?tvn24\.pl)/(?:[^/]+/)*[^/?#\s]+[,-](?P<id>\d+)(?:\.html)?'
    _TESTS = [{
        'url': 'https://tvn24.pl/polska/edyta-gorniak-napisala-o-statystach-w-szpitalach-udajacych-chorych-na-covid-19-jerzy-polaczek-i-marek-posobkiewicz-odpowiadaja-zapraszamy-4747899',
        'info_dict': {
            'id': '4744453',
            'ext': 'm3u8',
            'title': '"Nie wszyscy \'statyści\' wychodzą na własnych nogach". Chorzy na COVID-19 odpowiadają Edycie Górniak',
            'description': 'md5:aa98c393df243a69203cfb6769b8db51',
        }
    }, {
        # different layout
        'url': 'https://tvnmeteo.tvn24.pl/magazyny/maja-w-ogrodzie,13/odcinki-online,1,4,1,0/pnacza-ptaki-i-iglaki-odc-691-hgtv-odc-29,1771763.html',
        'info_dict': {
            'id': '1771763',
            'ext': 'mp4',
            'title': 'Pnącza, ptaki i iglaki (odc. 691 /HGTV odc. 29)',
            'thumbnail': 're:https?://.*',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://tvn24.pl/magazyn-tvn24/zrobimy-z-ciebie-mezczyzne,242,4189',
        'info_dict': {
            'id': '4189',
            'title': 'Zrobimy z ciebie mężczyznę',
            'description': 'Milo nie miało myśli erotycznych. Tak boleśnie myślało o własnym ciele, że nie potrafiło myśleć o nim w towarzystwie innych ciał. Ale żeby zmienić ciało, m...',
        },
        'playlist_count': 2,
    }, {
        'url': 'https://fakty.tvn24.pl/ogladaj-online,60/akcja-media-bez-wyboru-i-misja-telewizji-publicznej,1048910.html',
        'info_dict': {
            'id': '1048910',
            'ext': 'mp4',
            'title': '11.02.2021 | Misja telewizji publicznej i reakcja na protest "Media bez wyboru"',
            'description': 'md5:684d2e09f57c7ed03a277bc5ce295d63',
        },
    }, {
        'url': 'http://fakty.tvn24.pl/ogladaj-online,60/53-konferencja-bezpieczenstwa-w-monachium,716431.html',
        'only_matching': True,
    }, {
        'url': 'http://sport.tvn24.pl/pilka-nozna,105/ligue-1-kamil-glik-rozcial-glowe-monaco-tylko-remisuje-z-bastia,716522.html',
        'only_matching': True,
    }, {
        'url': 'https://www.tvn24.pl/magazyn-tvn24/angie-w-jednej-czwartej-polka-od-szarej-myszki-do-cesarzowej-europy,119,2158',
        'only_matching': True,
    }]
    _REQUIRES_PLAYWRIGHT = True

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        domain, display_id = mobj.group('domain', 'id')

        if '/magazyn-tvn24/' in url:
            return self._handle_magazine_frontend(url, display_id)
        elif domain in ('tvn24.pl', ):
            return self._handle_nextjs_frontend(url, display_id)
        elif domain in ('fakty.tvn24.pl', ):
            return self._handle_fakty_frontend(url, display_id)
        else:
            return self._handle_old_frontend(url, display_id)

    def _handle_old_frontend(self, url, display_id):
        webpage = self._download_webpage(url, display_id)

        title = self._og_search_title(
            webpage, default=None) or self._search_regex(
            r'<h\d+[^>]+class=["\']magazineItemHeader[^>]+>(.+?)</h',
            webpage, 'title')

        def extract_json(attr, name, default=NO_DEFAULT, fatal=True):
            return self._parse_json(
                self._search_regex(
                    r'\b%s=(["\'])(?P<json>(?!\1).+?)\1' % attr, webpage,
                    name, group='json', default=default, fatal=fatal) or '{}',
                display_id, transform_source=unescapeHTML, fatal=fatal)

        quality_data = extract_json('data-quality', 'formats')

        formats = []
        for format_id, url in quality_data.items():
            formats.append({
                'url': url,
                'format_id': format_id,
                'height': int_or_none(format_id.rstrip('p')),
            })
        self._sort_formats(formats)

        description = self._og_search_description(webpage, default=None)
        thumbnail = self._og_search_thumbnail(
            webpage, default=None) or self._html_search_regex(
            r'\bdata-poster=(["\'])(?P<url>(?!\1).+?)\1', webpage,
            'thumbnail', group='url')

        video_id = None

        share_params = extract_json(
            'data-share-params', 'share params', default=None)
        if isinstance(share_params, dict):
            video_id = share_params.get('id')

        if not video_id:
            video_id = self._search_regex(
                r'data-vid-id=["\'](\d+)', webpage, 'video id',
                default=None) or self._search_regex(
                r',(\d+)\.html', url, 'video id', default=display_id)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
        }

    def _handle_magazine_frontend(self, url, display_id):
        webpage = self._download_webpage(url, display_id)

        entries = []
        for vid_el in re.finditer(r'(?P<video><div\b[^>]+\bdata-src=[^>]+>)\s*(?:</[^>]+>\s*)*<figcaption>(?P<title>(?:.|\s)+?)</figcaption>', webpage):
            vid = extract_attributes(vid_el.group('video'))

            formats = []
            for fmt_name, fmt_url in self._parse_json(unescapeHTML(vid['data-quality']), display_id).items():
                formats.append({
                    'format_id': fmt_name,
                    'height': int_or_none(fmt_name[:-1]),
                    'url': fmt_url,
                })

            self._sort_formats(formats)
            entries.append({
                'id': vid['data-video-id'],
                'title': clean_html(vid_el.group('title')),
                'formats': formats,
                'thumbnail': vid.get('data-poster'),
            })

        return {
            '_type': 'playlist',
            'id': display_id,
            'entries': entries,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
        }

    def _handle_nextjs_frontend(self, url, display_id):
        # make sure the GDPR consent appears, as we have to accept it so the video can play
        for cookie_name in ('OptanonAlertBoxClosed', 'OptanonConsent', 'eupubconsent-v2'):
            try:
                self._downloader.cookiejar.clear('.tvn24.pl', '/', cookie_name)
            except KeyError:
                # ignore, if cookies don't exist
                pass

        pwh = PlaywrightHelper(self)
        page = pwh.open_page(url, display_id)
        page.route(re.compile(r'(\.(png|jpg|svg|css)$)'), lambda route: route.abort())

        # GDPR consent, required to play video
        page.wait_for_selector('#onetrust-accept-btn-handler')
        page.click('#onetrust-accept-btn-handler')

        with page.expect_request(
                lambda r: re.match(r'https?://(?:www\.)?tvn24\.pl/api/[A-Za-z\d+-]+/plst', r.url),
                timeout=20000) as plst_req:
            # tip: always collect the request data before closing browser
            plst_url = plst_req.value.url
            title = page.eval_on_selector('meta[property="og:title"]', 'el => el.content')
            description = page.eval_on_selector('meta[property="og:description"]', 'el => el.content')
            pwh.browser_stop()
            data = self._download_json(plst_url, display_id)

            movie = data['movie']
            sources = movie['video']['sources']

            formats = []
            if sources.get('hls'):
                formats.extend(self._extract_m3u8_formats(sources['hls']['url'], display_id))

            self._sort_formats(formats)

            return {
                'id': movie['info']['id'],
                'formats': formats,
                'title': title,
                'description': description,
                'duration': movie['info']['total_time'],
                'is_live': movie['video']['is_live'],
            }

    def _handle_fakty_frontend(self, url, display_id):
        webpage = self._download_webpage(url, display_id)

        data = self._parse_json(
            self._search_regex(
                r"window\.VideoManager\.initVideo\('[^']+',\s*({.+?})\s*,\s*{.+?}\s*\);",
                webpage, 'video metadata'), display_id)

        video = data['movie']['video']
        info = data['movie']['info']

        if video.get('protections'):
            raise ExtractorError(
                'This video is protected by %s DRM protection' % '/'.join(video['protections'].keys()),
                expected=True)

        formats = []

        for fmt_id, fmt_data in video['sources'].items():
            if fmt_id == 'hls':
                formats.extend(self._extract_m3u8_formats(fmt_data['url'], display_id))
            elif fmt_id == 'dash':
                formats.extend(self._extract_mpd_formats(fmt_data['url'], display_id))
            elif fmt_id == 'mp4':
                for quality, mp4_url in fmt_data.items():
                    formats.append({
                        'url': mp4_url,
                        'ext': 'mp4',
                        'height': int_or_none(quality),
                    })

        self._sort_formats(formats)

        return {
            'id': display_id,
            'formats': formats,
            'title': unescapeHTML(info['episode_title']),
            'description': unescapeHTML(info.get('description')),
            'duration': int_or_none(info.get('total_time')),
            'age_limit': int_or_none(data['movie']['options'].get('parental_rating', {}).get('rating')),
        }
