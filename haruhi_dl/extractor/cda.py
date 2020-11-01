# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    compat_urllib_parse_unquote_plus,
    ExtractorError,
    float_or_none,
    multipart_encode,
    parse_duration,
    random_birthday,
    rot47,
    urljoin,
)


class CDAIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www\.)?cda\.pl/video|ebd\.cda\.pl/[0-9]+x[0-9]+)/(?P<id>[0-9a-z]+)'
    _BASE_URL = 'http://www.cda.pl/'
    _TESTS = [{
        'url': 'http://www.cda.pl/video/5749950c',
        'md5': '6f844bf51b15f31fae165365707ae970',
        'info_dict': {
            'id': '5749950c',
            'ext': 'mp4',
            'height': 720,
            'title': 'Oto dlaczego przed zakrętem należy zwolnić.',
            'description': 'md5:269ccd135d550da90d1662651fcb9772',
            'thumbnail': r're:^https?://.*\.jpg$',
            'average_rating': float,
            'duration': 39,
            'age_limit': 0,
        }
    }, {
        'url': 'http://www.cda.pl/video/57413289',
        'md5': 'a88828770a8310fc00be6c95faf7f4d5',
        'info_dict': {
            'id': '57413289',
            'ext': 'mp4',
            'title': 'Lądowanie na lotnisku na Maderze',
            'description': 'md5:60d76b71186dcce4e0ba6d4bbdb13e1a',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'crash404',
            'average_rating': float,
            'duration': 137,
            'age_limit': 0,
        }
    }, {
        # Age-restricted
        'url': 'https://www.cda.pl/video/225836e',
        'info_dict': {
            'id': '225836e',
            'ext': 'mp4',
            'title': 'Cycki',
            'description': 'cycki cycuszki fajne ciekawe azja ajzatka',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 6,
            'age_limit': 18,
            'average_rating': float,
        },
    }, {
        'url': 'http://ebd.cda.pl/0x0/5749950c',
        'only_matching': True,
    }]

    def _download_age_confirm_page(self, url, video_id, *args, **kwargs):
        form_data = random_birthday('rok', 'miesiac', 'dzien')
        form_data.update({'return': url, 'module': 'video', 'module_id': video_id})
        data, content_type = multipart_encode(form_data)
        return self._download_webpage(
            urljoin(url, '/a/validatebirth'), video_id, *args,
            data=data, headers={
                'Referer': url,
                'Content-Type': content_type,
            }, **kwargs)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        self._set_cookie('cda.pl', 'cda.player', 'html5')
        webpage = self._download_webpage(
            self._BASE_URL + '/video/' + video_id, video_id)

        if 'Ten film jest dostępny dla użytkowników premium' in webpage:
            raise ExtractorError('This video is only available for premium users.', expected=True)

        need_confirm_age = False
        if self._html_search_regex(r'(<form[^>]+action="[^>]*/a/validatebirth")',
                                   webpage, 'birthday validate form', default=None):
            webpage = self._download_age_confirm_page(
                url, video_id, note='Confirming age')
            need_confirm_age = True

        formats = []

        uploader = self._search_regex(r'"author":\s*{[^}]*"name":\s*"([^"]+)"',
                                      webpage, 'uploader', default=None)
        average_rating = self._search_regex(
            r'<span class="rating">\s*([\d.]+)',
            webpage, 'rating', fatal=False)

        info_dict = {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'uploader': uploader,
            'average_rating': float_or_none(average_rating),
            'thumbnail': self._og_search_thumbnail(webpage),
            'formats': formats,
            'duration': None,
            'age_limit': 18 if need_confirm_age else 0,
        }

        def extract_format(page, version):
            json_str = self._html_search_regex(
                r'player_data=(\\?["\'])(?P<player_data>.+?)\1', page,
                '%s player_json' % version, fatal=False, group='player_data')
            if not json_str:
                return
            player_data = self._parse_json(
                json_str, '%s player_data' % version, fatal=False)
            if not player_data:
                return
            video = player_data.get('video')
            if not video or 'file' not in video:
                self.report_warning('Unable to extract %s version information' % version)
                return
            video['file'] = rot47(compat_urllib_parse_unquote_plus(video['file']))
            if not video['file'].startswith('http'):
                video['file'] = 'https://' + video['file']
            video['file'] = video['file'].replace('.3cda.pl', '.cda.pl')
            if video['file'].endswith('adc.mp4'):
                video['file'] = video['file'].replace('adc.mp4', '.mp4')
            if not video['file'].endswith('.mp4'):
                video['file'] = video['file'][:-3] + '.mp4'
            f = {
                'url': video['file'],
            }
            m = re.search(
                r'<a[^>]+data-quality="(?P<format_id>[^"]+)"[^>]+href="[^"]+"[^>]+class="[^"]*quality-btn-active[^"]*">(?P<height>[0-9]+)p',
                page)
            if m:
                f.update({
                    'format_id': m.group('format_id'),
                    'height': int(m.group('height')),
                })
            info_dict['formats'].append(f)
            if not info_dict['duration']:
                info_dict['duration'] = parse_duration(video.get('duration'))

        extract_format(webpage, 'default')

        for href, resolution in re.findall(
                r'<a[^>]+data-quality="[^"]+"[^>]+href="([^"]+)"[^>]+class="quality-btn"[^>]*>([0-9]+p)',
                webpage):
            if need_confirm_age:
                handler = self._download_age_confirm_page
            else:
                handler = self._download_webpage

            webpage = handler(
                href if href.startswith('http') else self._BASE_URL + href, video_id,
                'Downloading %s version information' % resolution, fatal=False)
            if not webpage:
                # Manually report warning because empty page is returned when
                # invalid version is requested.
                self.report_warning('Unable to download %s version information' % resolution)
                continue

            extract_format(webpage, resolution)

        self._sort_formats(formats)

        return info_dict
