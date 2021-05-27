# coding: utf-8

from .common import SelfhostedInfoExtractor
from ..utils import (
    mimetype2ext,
    parse_iso8601,
    ExtractorError,
)

import json


class MisskeySHIE(SelfhostedInfoExtractor):
    IE_NAME = 'misskey'
    _VALID_URL = r'misskey:(?P<host>[^:]+):(?P<id>[\da-z]+)'
    _SH_VALID_URL = r'https?://(?P<host>[^/]+)/notes/(?P<id>[\da-z]+)'
    _SH_VALID_CONTENT_STRINGS = (
        '<meta name="application-name" content="Misskey"',
        '<meta name="misskey:',
        '<!-- If you are reading this message... how about joining the development of Misskey? -->',
    )

    _TESTS = [{
        'url': 'https://catgirl.life/notes/8lh52dlrii',
        'info_dict': {
            'id': '8lh52dlrii',
            'ext': 'mp4',
            'timestamp': 1604387877,
            'upload_date': '20201103',
            'title': '@graf@poa.st @Moon@shitposter.club \n*kickstarts your federation*',
        },
    }]

    def _selfhosted_extract(self, url, webpage=None):
        host, video_id = self._match_id_and_host(url)

        post = self._download_json(f'https://{host}/api/notes/show', video_id,
                                   data=bytes(json.dumps({
                                       'noteId': video_id,
                                   }).encode('utf-8')),
                                   headers={
                                       'Content-Type': 'application/json',
                                   })

        entries = []
        for file in post['files']:
            if not file['type'].startswith('video/') and not file['type'].startswith('audio/'):
                continue
            entries.append({
                'id': file['id'],
                'url': file['url'],
                'ext': mimetype2ext(file.get('type')),
                'title': file.get('name'),
                'thumbnail': file.get('thumbnailUrl'),
                'timestamp': parse_iso8601(file.get('createdAt')),
                'filesize': file['size'] if file.get('size') != 0 else None,
                'age_limit': 18 if file.get('isSensitive') else 0,
            })

        if len(entries) == 0:
            raise ExtractorError('No media found in post')
        elif len(entries) == 1:
            info_dict = entries[0]
        else:
            info_dict = {
                '_type': 'playlist',
                'entries': entries,
            }

        info_dict.update({
            'id': video_id,
            'title': post.get('text') or '_',
        })
        return info_dict
