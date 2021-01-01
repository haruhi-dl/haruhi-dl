# coding: utf-8
from __future__ import unicode_literals

import re

from .common import SelfhostedInfoExtractor
from ..compat import compat_str
from ..utils import (
    int_or_none,
    parse_resolution,
    str_or_none,
    try_get,
    unified_timestamp,
    url_or_none,
    urljoin,
)


class PeerTubeSHIE(SelfhostedInfoExtractor):
    _UUID_RE = r'[\da-fA-F]{8}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{12}'
    _API_BASE = 'https://%s/api/v1/videos/%s/%s'
    _VALID_URL = r'peertube:(?P<host>[^:]+):(?P<id>%s)' % (_UUID_RE)
    _SH_VALID_URL = r'https?://(?P<host>[^/]+)/(?:videos/(?:watch|embed)|api/v\d/videos)/(?P<id>%s)' % _UUID_RE
    _SH_VALID_CONTENT_STRINGS = (
        '<title>PeerTube<',
        'There will be other non JS-based clients to access PeerTube',
        '>We are sorry but it seems that PeerTube is not compatible with your web browser.<',
    )

    _TESTS = [{
        'url': 'https://framatube.org/videos/watch/9c9de5e8-0a1e-484a-b099-e80766180a6d',
        'md5': '9bed8c0137913e17b86334e5885aacff',
        'info_dict': {
            'id': '9c9de5e8-0a1e-484a-b099-e80766180a6d',
            'ext': 'mp4',
            'title': 'What is PeerTube?',
            'description': 'md5:3fefb8dde2b189186ce0719fda6f7b10',
            'thumbnail': r're:https?://.*\.(?:jpg|png)',
            'timestamp': 1538391166,
            'upload_date': '20181001',
            'uploader': 'Framasoft',
            'uploader_id': '3',
            'uploader_url': 'https://framatube.org/accounts/framasoft',
            'channel': 'Les vidéos de Framasoft',
            'channel_id': '2',
            'channel_url': 'https://framatube.org/video-channels/bf54d359-cfad-4935-9d45-9d6be93f63e8',
            'language': 'en',
            'license': 'Attribution - Share Alike',
            'duration': 113,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'tags': ['framasoft', 'peertube'],
            'categories': ['Science & Technology'],
        }
    }, {
        'url': 'https://peertube.tamanoir.foucry.net/videos/watch/0b04f13d-1e18-4f1d-814e-4979aa7c9c44',
        'only_matching': True,
    }, {
        # nsfw
        'url': 'https://tube.22decembre.eu/videos/watch/9bb88cd3-9959-46d9-9ab9-33d2bb704c39',
        'only_matching': True,
    }, {
        'url': 'https://tube.22decembre.eu/videos/embed/fed67262-6edb-4d1c-833b-daa9085c71d7',
        'only_matching': True,
    }, {
        'url': 'https://tube.openalgeria.org/api/v1/videos/c1875674-97d0-4c94-a058-3f7e64c962e8',
        'only_matching': True,
    }, {
        'url': 'peertube:video.blender.org:b37a5b9f-e6b5-415c-b700-04a5cd6ec205',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_urls(webpage, **kwargs):
        entries = re.finditer(
            r'''(?x)<iframe[^>]+\bsrc=["\'](?:https?:)?//(?P<host>[^/]+)/videos/embed/(?P<video_id>%s)'''
            % (PeerTubeSHIE._UUID_RE), webpage)
        return ['peertube:%s:%s' % (mobj.group('host'), mobj.group('video_id'))
                for mobj in entries]

    def _call_api(self, host, video_id, path, note=None, errnote=None, fatal=True):
        return self._download_json(
            self._API_BASE % (host, video_id, path), video_id,
            note=note, errnote=errnote, fatal=fatal)

    def _get_subtitles(self, host, video_id):
        captions = self._call_api(
            host, video_id, 'captions', note='Downloading captions JSON',
            fatal=False)
        if not isinstance(captions, dict):
            return
        data = captions.get('data')
        if not isinstance(data, list):
            return
        subtitles = {}
        for e in data:
            language_id = try_get(e, lambda x: x['language']['id'], compat_str)
            caption_url = urljoin('https://%s' % host, e.get('captionPath'))
            if not caption_url:
                continue
            subtitles.setdefault(language_id or 'en', []).append({
                'url': caption_url,
            })
        return subtitles

    def _selfhosted_extract(self, url, webpage=None):
        mobj = re.match(self._VALID_URL, url)
        if not mobj:
            mobj = re.match(self._SH_VALID_URL, url)
        host = mobj.group('host')
        video_id = mobj.group('id')

        video = self._call_api(
            host, video_id, '', note='Downloading video JSON')

        title = video['name']

        formats = []
        for file_ in video['files']:
            if not isinstance(file_, dict):
                continue
            file_url = url_or_none(file_.get('fileUrl'))
            if not file_url:
                continue
            file_size = int_or_none(file_.get('size'))
            format_id = try_get(
                file_, lambda x: x['resolution']['label'], compat_str)
            f = parse_resolution(format_id)
            f.update({
                'url': file_url,
                'format_id': format_id,
                'filesize': file_size,
            })
            formats.append(f)
        self._sort_formats(formats)

        full_description = self._call_api(
            host, video_id, 'description', note='Downloading description JSON',
            fatal=False)

        description = None
        if isinstance(full_description, dict):
            description = str_or_none(full_description.get('description'))
        if not description:
            description = video.get('description')

        subtitles = self.extract_subtitles(host, video_id)

        def data(section, field, type_):
            return try_get(video, lambda x: x[section][field], type_)

        def account_data(field, type_):
            return data('account', field, type_)

        def channel_data(field, type_):
            return data('channel', field, type_)

        category = data('category', 'label', compat_str)
        categories = [category] if category else None

        nsfw = video.get('nsfw')
        if nsfw is bool:
            age_limit = 18 if nsfw else 0
        else:
            age_limit = None

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': urljoin(url, video.get('thumbnailPath')),
            'timestamp': unified_timestamp(video.get('publishedAt')),
            'uploader': account_data('displayName', compat_str),
            'uploader_id': str_or_none(account_data('id', int)),
            'uploader_url': url_or_none(account_data('url', compat_str)),
            'channel': channel_data('displayName', compat_str),
            'channel_id': str_or_none(channel_data('id', int)),
            'channel_url': url_or_none(channel_data('url', compat_str)),
            'language': data('language', 'id', compat_str),
            'license': data('licence', 'label', compat_str),
            'duration': int_or_none(video.get('duration')),
            'view_count': int_or_none(video.get('views')),
            'like_count': int_or_none(video.get('likes')),
            'dislike_count': int_or_none(video.get('dislikes')),
            'age_limit': age_limit,
            'tags': try_get(video, lambda x: x['tags'], list),
            'categories': categories,
            'formats': formats,
            'subtitles': subtitles
        }
