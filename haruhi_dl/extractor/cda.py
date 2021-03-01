# coding: utf-8
from __future__ import unicode_literals

import base64
import datetime
import hashlib
import hmac

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    try_get,
)


class CDABaseExtractor(InfoExtractor):
    _BASE_URL = 'https://api.cda.pl'
    _BASE_HEADERS = {
        'Accept': 'application/vnd.cda.public+json',
        'User-Agent': 'pl.cda 1.0 (version 1.2.88 build 15306; Android 9; Xiaomi Redmi 3S)',
        # gets replaced with Bearer token after the login request
        # apparently the token is hardcoded in the app
        'Authorization': 'Basic YzU3YzBlZDUtYTIzOC00MWQwLWI2NjQtNmZmMWMxY2Y2YzVlOklBTm95QlhRRVR6U09MV1hnV3MwMW0xT2VyNWJNZzV4clRNTXhpNGZJUGVGZ0lWUlo5UGVYTDhtUGZaR1U1U3Q',
    }
    _NETRC_MACHINE = 'cda'
    _bearer = None

    # logs into cda.pl and returns _BASE_HEADERS with the Bearer token
    def _get_headers(self, video_id):
        headers = self._BASE_HEADERS

        if self._bearer and self._bearer['valid_until'] > datetime.datetime.now().timestamp() + 5:
            headers.update({
                'Authorization': 'Bearer %s' % self._bearer['token'],
            })
            return headers

        username, password = self._get_login_info()
        if username is None or password is None:
            username = 'niezesrajciesiecda'
            password_hash = 'VD3QbYWSb_uwAShBZKN7F1DwEg_tRTdb4Xd3JvFsx6Y'
            account_type = 'shared'
        else:
            pwd_md5 = ""
            for byte in hashlib.md5(password.encode('utf-8')).digest():
                # bytes() param must be iterable of ints and not int
                hexik = bytes((byte & 255, )).hex()
                while len(hexik) < 2:
                    hexik = "0" + hexik
                pwd_md5 += hexik
            digest = hmac.new(
                's01m1Oer5IANoyBXQETzSOLWXgWs01m1Oer5bMg5xrTMMxRZ9Pi4fIPeFgIVRZ9PeXL8mPfXQETZGUAN5StRZ9P'.encode('utf-8'),
                pwd_md5.encode('utf-8'), hashlib.sha256).digest()
            password_hash = base64.urlsafe_b64encode(digest).decode('utf-8').replace('=', '')
            account_type = 'user'

        token_res = self._download_json('%s/oauth/token?grant_type=password&login=%s&password=%s' % (self._BASE_URL, username, password_hash),
                                        video_id, 'Logging into cda.pl with a %s account' % account_type, headers=headers, data=bytes(''.encode('utf-8')))

        self._bearer = {
            'token': token_res['access_token'],
            'valid_until': token_res['expires_in'] + datetime.datetime.now().timestamp(),
        }

        headers.update({
            'Authorization': 'Bearer %s' % token_res['access_token'],
        })
        return headers


class CDAIE(CDABaseExtractor):
    _VALID_URL = r'https?://(?:(?:www\.)?cda\.pl/video|ebd\.cda\.pl/[0-9]+x[0-9]+)/(?P<id>[0-9a-z]+)'
    _TESTS = [{
        'url': 'http://www.cda.pl/video/5749950c',
        'md5': '6f844bf51b15f31fae165365707ae970',
        'info_dict': {
            'id': '5749950c',
            'ext': 'mp4',
            'height': 720,
            'title': 'Oto dlaczego przed zakrętem należy zwolnić.',
            'description': 'md5:269ccd135d550da90d1662651fcb9772',
            'thumbnail': r're:^https?://.*\.jpg(?:\?t=\d+)?$',
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
            'thumbnail': r're:^https?://.*\.jpg(?:\?t=\d+)?$',
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
            'thumbnail': r're:^https?://.*\.jpg(?:\?t=\d+)?$',
            'duration': 6,
            'age_limit': 18,
            'average_rating': float,
        },
    }, {
        'url': 'http://ebd.cda.pl/0x0/5749950c',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        headers = self._get_headers(video_id)

        metadata = self._download_json(
            self._BASE_URL + '/video/' + video_id, video_id, headers=headers)['video']

        if metadata.get('premium') is True and metadata.get('premium_free') is not True:
            raise ExtractorError('This video is only available for premium users.', expected=True)

        uploader = try_get(metadata, lambda x: x['author']['login'])
        # anonymous uploader
        if uploader == 'anonim':
            uploader = None

        formats = []
        for quality in metadata['qualities']:
            formats.append({
                'url': quality['file'],
                'format': quality['title'],
                'resolution': quality['name'],
                'height': int_or_none(quality['name'][:-1]),    # for the format sorting
                'filesize': quality.get('length'),
            })

        return {
            'id': video_id,
            'title': metadata['title'],
            'description': metadata.get('description'),
            'uploader': uploader,
            'average_rating': float_or_none(metadata.get('rating')),
            'thumbnail': metadata.get('thumb'),
            'formats': formats,
            'duration': metadata.get('duration'),
            'age_limit': 18 if metadata.get('for_adults') else 0,
            'view_count': metadata.get('views'),
        }
