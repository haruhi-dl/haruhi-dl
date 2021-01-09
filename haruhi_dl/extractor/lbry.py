# coding: utf-8
from __future__ import unicode_literals

import json
import random

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    mimetype2ext,
)


class LBRYIE(InfoExtractor):
    _VALID_URL = r'lbry://(?:@[^#]+#[^/]+/)?(?P<id>[^@][^#]*)#[a-z0-9]+'
    _TESTS = [{
        'url': 'lbry://@tuxfoo#e/Take-Back-Control-of-Your-Computing----Fediverse#6',
        'info_dict': {
            'id': '6cee9212656cc196806de249720a3e440c1186fb',
            'ext': 'mp4',
            'title': 'Take Back Control of Your Computing: Fediverse',
            'description': 'I talk about the fediverse and give a demonstration of mastodon.\n\nFollow me on mastodon\nhttps://social.librem.one/@tuxfoo',
            'upload_date': '20200116',
            'timestamp': 1579151121,
        },
    }]

    @classmethod
    def _jsonrpc_wrapper(cls, method, params):
        return bytes(json.dumps({
            'id': random.randint(10 ** 13, (10 ** 14) - 1),
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
        }).encode('utf-8'))

    def _download_api(self, method, params, video_id, note='Downloading JSON metadata'):
        return self._download_json(
            'https://api.lbry.tv/api/v1/proxy?m=%s' % method, video_id,
            note=note,
            data=self._jsonrpc_wrapper(method, params),
            headers={
                'Content-Type': 'application/json-rpc',
            }).get('result')

    def _real_extract(self, url):
        video_id = self._match_id(url)
        metadata = self._download_api('resolve', {
            'urls': [url],
        }, video_id, 'Downloading video metadata')[url]
        streaming_data = self._download_api('get', {
            'save_file': False,
            'uri': url,
        }, video_id, 'Downloading video streaming url')

        value = metadata['value']
        source = value['source']
        video = value['video']

        formats = [{
            'url': streaming_data['streaming_url'],
            'ext': mimetype2ext(source.get('media_type')),
            'width': int_or_none(video.get('width')),
            'height': int_or_none(video.get('height')),
            'filesize': int_or_none(source.get('size')),
        }]

        return {
            'id': metadata['claim_id'],
            'formats': formats,
            'title': value['title'],
            'description': value['description'],
            'duration': int_or_none(video.get('duration')),
            'timestamp': int_or_none(value.get('release_time')),
            'thumbnail': value['thumbnail'].get('url'),
            'tags': value.get('tags'),
        }
