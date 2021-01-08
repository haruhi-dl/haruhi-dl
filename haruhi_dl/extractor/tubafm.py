# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    unescapeHTML,
)


class TubaFMIE(InfoExtractor):
    IE_NAME = 'tubafm:stream'
    _VALID_URL = r'https?://fm\.tuba\.pl/play/(?P<id>\d+/\d+)/'
    _TESTS = [{
        'url': 'https://fm.tuba.pl/play/38/2/radio-0',
        'info_dict': {
            'id': '38/2',
            'ext': 'mp3',
            'title': 'Radio Pogoda',
            'description': 'md5:cdbc59138cfc21d5e8b0f66183455b2b',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        stream_id = self._match_id(url)
        meta = self._download_json('https://fm.tuba.pl/getp/%s' % stream_id, stream_id)

        info = meta['info']

        thumbnails = []
        if info.get('full_img_big'):
            thumbnails.append({
                'url': info.get('full_img_big'),
            })
        if info.get('full_img'):
            thumbnails.append({
                'url': info.get('full_img'),
            })

        info_dict = {
            'id': stream_id,
            'title': info['name'],
            'description': unescapeHTML(info.get('description')),
            'thumbnails': thumbnails,
        }

        if len(meta['playlist']) == 0:
            raise ExtractorError('No audio playlists')
        elif len(meta['playlist']) == 1:
            # live radio stream (FM restreams)
            stream_url = meta['playlist'][0][6]

            # home.pl sells TLS certificates that AREN'T FUCKING TRUSTED
            # by almost anything except the newest stable Firefox and Chromium
            # this is a workaround for this shitty product
            stream_url = stream_url.replace('https://radiostream.pl/', 'http://radiostream.pl/')

            info_dict.update({
                'url': stream_url,
                'ext': 'mp3',
                'is_live': True,
            })
        else:
            # basically music playlists, but they require more additional work - MRs accepted
            #
            # if you need this:
            # curl https://ssl.fm.tuba.pl/service3/getConfig\?password\=ea1aefc624\&device_id\=[insert an uuidv4 here]\&device_platform\=android\&device_type\=Xiaomi\&login\=android_test\&lang\=en | jq .sessionid -r
            # curl https://fm.tuba.pl/service3/getSongUrl\?filename\=%2F00%2F00%2F15%2F94%2F58.aac\&id\=159458\&sessionid\=[see above] | jq .link -r
            raise ExtractorError('Unsupported playlist type')

        return info_dict


class TubaFMPageIE(InfoExtractor):
    IE_NAME = 'tubafm:page'
    _VALID_URL = r'https://fm\.tuba\.pl/radio/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://fm.tuba.pl/radio/Rock+Radio+Polska',
        'info_dict': {
            'id': '8/2',
            'ext': 'mp3',
            'title': 'Rock Radio Polska',
            'description': 'md5:bde7dc45e0eca5ce916a4680b7db19a3',
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': ['TubaFM'],
    }]

    def _real_extract(self, url):
        slug = self._match_id(url)
        webpage = self._download_webpage(url, slug)
        return {
            '_type': 'url',
            'url': self._search_regex(r'<div class=managing-panel><div class=switcher><a href="(https://fm\.tuba\.pl/play/\d+/\d+/[^"]*)"',
                                      webpage, 'stream url'),
            'ie_key': 'TubaFM',
        }
