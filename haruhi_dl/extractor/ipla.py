# coding: utf-8
from __future__ import unicode_literals

from uuid import uuid4
import json

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    url_or_none,
)


class IplaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ipla\.tv/.+/(?P<id>[0-9a-fA-F]+)'
    _TESTS = [{
        'url': 'https://www.ipla.tv/wideo/serial/Swiat-wedlug-Kiepskich/759/Sezon-1/760/Swiat-wedlug-Kiepskich-Odcinek-88/4121?seasonId=760',
        'info_dict': {
            'id': '4121',
            'ext': 'mp4',
            'title': 'Świat według Kiepskich - Odcinek 88',  # I love when my code works so well
            'age_limit': 12,
        },
    }]

    user_agent_data = {
        'deviceType': 'mobile',
        'application': 'native',
        'os': 'android',
        'build': 41002,
        'widevine': False,
        'portal': 'ipla',
        'player': 'flexi',
    }
    device_id = {
        'type': 'other',
        'value': str(uuid4()),
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        media = self.get_info(video_id)

        formats = []

        for ptrciscute in media['playback']['mediaSources']:
            formats.append({
                "url": url_or_none(self.get_url(video_id, ptrciscute['id'])),
                "height": int_or_none(ptrciscute["quality"][:-1])
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': media["displayInfo"]["title"],
            'formats': formats,
            'age_limit': int_or_none(media["displayInfo"]["ageGroup"])
        }

    def rpc(self, method, params):
        params['userAgentData'] = self.user_agent_data
        params['deviceId'] = self.device_id
        params['clientId'] = params['deviceId']['value']
        params['cpid'] = 1
        return bytes(json.dumps({
            'method': method,
            'id': '2137',
            'jsonrpc': '2.0',
            'params': params,
        }), encoding='utf-8')

    def get_info(self, media_id):
        req = self.rpc('prePlayData', {
            'mediaId': media_id
        })

        headers = {
            'Content-type': 'application/json'
        }

        res = self._download_json('http://b2c-mobile.redefine.pl/rpc/navigation/', media_id, data=req, headers=headers)
        return res['result']['mediaItem']

    def get_url(self, media_id, source_id):
        req = self.rpc('getPseudoLicense', {
            'mediaId': media_id,
            'sourceId': source_id
        })

        headers = {
            'Content-type': 'application/json'
        }

        res = self._download_json('https://b2c-mobile.redefine.pl/rpc/drm/', media_id, data=req, headers=headers)
        return res['result']['url']
