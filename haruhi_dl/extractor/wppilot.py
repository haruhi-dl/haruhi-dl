# coding: utf-8

from .common import InfoExtractor
from ..utils import (
    std_headers,
    try_get,
    ExtractorError,
)

import json
import random
import re


class WPPilotBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'wppilot'
    _LOGGED_IN = False

    _VIDEO_URL = 'https://pilot.wp.pl/api/v1/channel/%s'
    _VIDEO_GUEST_URL = 'https://pilot.wp.pl/api/v1/guest/channel/%s'
    _VIDEO_LIST_URL = 'https://pilot.wp.pl/api/v1/channels/list'
    _VIDEO_CLOSE_URL = 'https://pilot.wp.pl/api/v1/channels/close'
    _LOGIN_URL = 'https://pilot.wp.pl/api/v1/user_auth/login'

    _HEADERS_ATV = {
        'User-Agent': 'ExoMedia 4.3.0 (43000) / Android 8.0.0 / foster_e',
        'Accept': 'application/json',
        'X-Version': 'pl.videostar|3.25.0|Android|26|foster_e',
        'Content-Type': 'application/json; charset=UTF-8',
    }
    _HEADERS_WEB = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Referer': 'https://pilot.wp.pl/tv/',
    }
    _STREAM_HEADERS_WEB = {
        'Referer': 'https://pilot.wp.pl/',
        'Origin': 'https://pilot.wp.pl',
    }

    def _real_initialize(self):
        self._login()

    def _login(self):
        if any(cookie.domain == '.wp.pl' and cookie.name == 'netviapisessid'
               for cookie in self._downloader.cookiejar):
            # session exists, already logged in
            self._LOGGED_IN = True
            return None

        username, password = self._get_login_info()
        if not username:
            return None

        login = self._download_json(
            self._LOGIN_URL, None, 'Logging in', 'Unable to log in',
            headers=self._HEADERS_ATV,
            data=bytes(json.dumps({
                'device': 'android_tv',
                'login': username,
                'password': password,
            }).encode('utf-8')))

        error = try_get(login, lambda x: x['_meta']['error']['name'])
        if error:
            raise ExtractorError(f'WP login error: "{error}"')
        self._LOGGED_IN = True

    def _get_channel_list(self, cache=True):
        if cache is True:
            cache_res = self._downloader.cache.load('wppilot', 'channel-list')
            if cache_res:
                cache_res['_hdl_cached'] = True
                return cache_res
        res = self._download_json(
            self._VIDEO_LIST_URL, None, 'Downloading channel list')
        self._downloader.cache.store('wppilot', 'channel-list', res)
        return res

    def _parse_channel(self, chan, categories):
        thumbnails = []
        for key in ('thumbnail', 'thumbnail_mobile', 'thumbnail_mobile_bg', 'icon'):
            if chan.get(key):
                thumbnails.append({
                    'id': key,
                    'url': chan[key],
                })
        return {
            'id': str(chan['id']),
            'title': chan['name'],
            'categories': [categories[str(i)] for i in chan['categories']],
        }


class WPPilotIE(WPPilotBaseIE):
    _VALID_URL = r'(?:https?://pilot\.wp\.pl/tv/?#|wppilot:)(?P<id>[a-z\d-]+)'
    IE_NAME = 'wppilot'

    _TESTS = [{
        'url': 'https://pilot.wp.pl/tv/#telewizja-wp-hd',
        'info_dict': {
            'id': '158',
            'ext': 'm3u8',
            'title': 'Telewizja WP HD',
        },
        'params': {
            'format': 'bestvideo',
        },
    }, {
        # audio only
        'url': 'https://pilot.wp.pl/tv/#radio-nowy-swiat',
        'info_dict': {
            'id': '238',
            'ext': 'm3u8',
            'title': 'Radio Nowy Świat',
        },
        'params': {
            'format': 'bestaudio',
        },
    }, {
        'url': 'wppilot:9',
        'only_matching': True,
    }]

    def _get_channel(self, id_or_slug):
        video_list = self._get_channel_list(cache=True)
        key = 'id' if re.match(r'^\d+$', id_or_slug) else 'slug'
        for video in video_list['data']:
            if video.get(key) == id_or_slug:
                return self._parse_channel(video, video_list['_meta']['categories'])
        # if cached channel not found, download and retry
        if video_list.get('_hdl_cached') is True:
            video_list = self._get_channel_list(cache=False)
            for video in video_list['data']:
                if video.get(key) == id_or_slug:
                    return self._parse_channel(video, video_list['_meta']['categories'])
        raise ExtractorError('Channel not found')

    def _real_extract(self, url):
        video_id = self._match_id(url)

        channel = self._get_channel(video_id)
        video_id = str(channel['id'])
        if self._LOGGED_IN:
            video = self._download_json(
                self._VIDEO_URL % video_id, video_id, query={
                    'format_id': '2',
                    'device_type': 'android',
                }, headers=self._HEADERS_ATV, expected_status=(200, 422))
        else:
            video = self._download_json(
                self._VIDEO_GUEST_URL % video_id, video_id, query={
                    'device_type': 'web',
                }, headers=self._HEADERS_WEB, expected_status=(200))

        stream_token = try_get(video, lambda x: x['_meta']['error']['info']['stream_token'])
        if stream_token:
            close = self._download_json(
                self._VIDEO_CLOSE_URL, video_id, 'Invalidating previous stream session',
                headers=self._HEADERS_ATV,
                data=bytes(json.dumps({
                    'channelId': video_id,
                    't': stream_token,
                }).encode('utf-8')))
            if try_get(close, lambda x: x['data']['status']) == 'ok':
                return self.url_result('wppilot:%s' % video_id, ie=WPPilotIE.ie_key())

        error = try_get(video, lambda x: x['_meta']['error'])
        if error:
            raise ExtractorError(f"WP said: \"{error['name']}\" ({error['code']})")

        formats = []
        stream_headers = {}
        if self._LOGGED_IN:
            ua = self._HEADERS_ATV['User-Agent']
        else:
            ua = std_headers['User-Agent']
        stream_headers['User-Agent'] = ua

        for fmt in video['data']['stream_channel']['streams']:
            # MPD does not work for some reason
            # if fmt['type'] == 'dash@live:abr':
            #     formats.extend(
            #         self._extract_mpd_formats(
            #             random.choice(fmt['url']), video_id))
            if fmt['type'] == 'hls@live:abr':
                formats.extend(
                    self._extract_m3u8_formats(
                        random.choice(fmt['url']),
                        video_id, headers=stream_headers))
        for i in range(len(formats)):
            formats[i]['http_headers'] = stream_headers

        self._sort_formats(formats)

        channel['formats'] = formats
        return channel


class WPPilotChannelsIE(WPPilotBaseIE):
    _VALID_URL = r'(?:https?://pilot\.wp\.pl/(?:tv/?)?(?:\?[^#]*)?#?|wppilot:)$'
    IE_NAME = 'wppilot:channels'

    _TESTS = [{
        'url': 'wppilot:',
        'info_dict': {
            'id': 'wppilot',
            'title': 'WP Pilot',
        },
        'playlist_mincount': 100,
    }, {
        'url': 'https://pilot.wp.pl/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        channel_list = self._get_channel_list()
        categories = channel_list['_meta']['categories']
        entries = []
        for chan in channel_list['data']:
            entry = self._parse_channel(chan, categories)
            entry.update({
                '_type': 'url_transparent',
                'url': f'wppilot:{chan["id"]}',
                'ie_key': WPPilotIE.ie_key(),
            })
            entries.append(entry)
        return {
            '_type': 'playlist',
            'id': 'wppilot',
            'entries': entries,
            'title': 'WP Pilot',
        }
