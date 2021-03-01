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


class PeerTubeBaseExtractor(SelfhostedInfoExtractor):
    _UUID_RE = r'[\da-fA-F]{8}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{12}'
    _API_BASE = 'https://%s/api/v1/%s/%s/%s'
    _SH_VALID_CONTENT_STRINGS = (
        '<title>PeerTube<',
        'There will be other non JS-based clients to access PeerTube',
        '>There are other non JS-based unofficial clients to access PeerTube',
        '>We are sorry but it seems that PeerTube is not compatible with your web browser.<',
        '<meta property="og:platform" content="PeerTube"',
    )

    def _call_api(self, host, resource, resource_id, path, note=None, errnote=None, fatal=True):
        return self._download_json(
            self._API_BASE % (host, resource, resource_id, path), resource_id,
            note=note, errnote=errnote, fatal=fatal)

    def _parse_video(self, video, url):
        host, display_id = self._match_id_and_host(url)
        info_dict = {}

        formats = []
        files = video.get('files') or []
        for playlist in (video.get('streamingPlaylists') or []):
            if not isinstance(playlist, dict):
                continue
            playlist_files = playlist.get('files')
            if not (playlist_files and isinstance(playlist_files, list)):
                continue
            files.extend(playlist_files)
        for file_ in files:
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
            if format_id == '0p':
                f['vcodec'] = 'none'
            else:
                f['fps'] = int_or_none(file_.get('fps'))
            formats.append(f)
        if files:
            self._sort_formats(formats)
            info_dict['formats'] = formats
        else:
            info_dict.update({
                '_type': 'url_transparent',
                'url': 'peertube:%s:%s' % (host, video['uuid']),
                'ie_key': 'PeerTubeSH',
            })

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

        info_dict.update({
            'id': video['uuid'],
            'title': video['name'],
            'description': video.get('description'),
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
        })
        return info_dict


class PeerTubeSHIE(PeerTubeBaseExtractor):
    _VALID_URL = r'peertube:(?P<host>[^:]+):(?P<id>%s)' % (PeerTubeBaseExtractor._UUID_RE)
    _SH_VALID_URL = r'https?://(?P<host>[^/]+)/(?:videos/(?:watch|embed)|api/v\d/videos)/(?P<id>%s)' % (PeerTubeBaseExtractor._UUID_RE)

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
        # Issue #26002
        'url': 'peertube:spacepub.space:d8943b2d-8280-497b-85ec-bc282ec2afdc',
        'info_dict': {
            'id': 'd8943b2d-8280-497b-85ec-bc282ec2afdc',
            'ext': 'mp4',
            'title': 'Dot matrix printer shell demo',
            'uploader_id': '3',
            'timestamp': 1587401293,
            'upload_date': '20200420',
            'uploader': 'Drew DeVault',
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

    def _get_subtitles(self, host, video_id):
        captions = self._call_api(
            host, 'videos', video_id, 'captions', note='Downloading captions JSON',
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
        host, video_id = self._match_id_and_host(url)

        video = self._call_api(
            host, 'videos', video_id, '', note='Downloading video JSON')

        info_dict = self._parse_video(video, url)

        info_dict['subtitles'] = self.extract_subtitles(host, video_id)

        description = None
        if webpage:
            description = self._og_search_description(webpage)
        if not description:
            full_description = self._call_api(
                host, 'videos', video_id, 'description', note='Downloading description JSON',
                fatal=False)
            if isinstance(full_description, dict):
                description = str_or_none(full_description.get('description'))
        if not description:
            description = video.get('description')
        info_dict['description'] = description

        return info_dict


class PeerTubePlaylistSHIE(PeerTubeBaseExtractor):
    _VALID_URL = r'peertube:playlist:(?P<host>[^:]+):(?P<id>.+)'
    _SH_VALID_URL = r'https?://(?P<host>[^/]+)/(?:videos/(?:watch|embed)/playlist|api/v\d/video-playlists)/(?P<id>%s)' % (PeerTubeBaseExtractor._UUID_RE)

    _TESTS = [{
        'url': 'https://video.internet-czas-dzialac.pl/videos/watch/playlist/3c81b894-acde-4539-91a2-1748b208c14c?playlistPosition=1',
        'info_dict': {
            'id': '3c81b894-acde-4539-91a2-1748b208c14c',
            'title': 'Podcast Internet. Czas Działać!',
            'uploader_id': 3,
            'uploader': 'Internet. Czas działać!',
        },
        'playlist_mincount': 14,
    }]

    def _selfhosted_extract(self, url, webpage=None):
        host, display_id = self._match_id_and_host(url)

        playlist_data = self._call_api(host, 'video-playlists', display_id, '', 'Downloading playlist metadata')
        entries = []
        i = 0
        videos = {'total': 0}
        while len(entries) < videos['total'] or i == 0:
            videos = self._call_api(host, 'video-playlists', display_id,
                                    'videos?start=%d&count=25' % (i * 25),
                                    note=('Downloading playlist video list (page #%d)' % i))
            i += 1
            for video in videos['data']:
                entries.append(self._parse_video(video['video'], url))

        return {
            '_type': 'playlist',
            'entries': entries,
            'id': playlist_data['uuid'],
            'title': playlist_data['displayName'],
            'description': playlist_data.get('description'),
            'channel': playlist_data['videoChannel']['displayName'],
            'channel_id': playlist_data['videoChannel']['id'],
            'channel_url': playlist_data['videoChannel']['url'],
            'uploader': playlist_data['ownerAccount']['displayName'],
            'uploader_id': playlist_data['ownerAccount']['id'],
            'uploader_url': playlist_data['ownerAccount']['url'],
        }


class PeerTubeChannelSHIE(PeerTubeBaseExtractor):
    _VALID_URL = r'peertube:channel:(?P<host>[^:]+):(?P<id>.+)'
    _SH_VALID_URL = r'https?://(?P<host>[^/]+)/(?:api/v\d/)?video-channels/(?P<id>[^/?#]+)(?:/videos)?'

    _TESTS = [{
        'url': 'https://video.internet-czas-dzialac.pl/video-channels/internet_czas_dzialac/videos',
        'info_dict': {
            'id': '2',
            'title': 'internet_czas_dzialac',
            'description': 'md5:4d2e215ea0d9ae4501a556ef6e9a5308',
            'uploader_id': 3,
            'uploader': 'Internet. Czas działać!',
        },
        'playlist_mincount': 14,
    }]

    def _selfhosted_extract(self, url, webpage=None):
        host, display_id = self._match_id_and_host(url)

        channel_data = self._call_api(host, 'video-channels', display_id, '', 'Downloading channel metadata')
        entries = []
        i = 0
        videos = {'total': 0}
        while len(entries) < videos['total'] or i == 0:
            videos = self._call_api(host, 'video-channels', display_id,
                                    'videos?start=%d&count=25&sort=publishedAt' % (i * 25),
                                    note=('Downloading channel video list (page #%d)' % i))
            i += 1
            for video in videos['data']:
                entries.append(self._parse_video(video, url))

        return {
            '_type': 'playlist',
            'entries': entries,
            'id': str(channel_data['id']),
            'title': channel_data['displayName'],
            'display_id': channel_data['name'],
            'description': channel_data.get('description'),
            'channel': channel_data['displayName'],
            'channel_id': channel_data['id'],
            'channel_url': channel_data['url'],
            'uploader': channel_data['ownerAccount']['displayName'],
            'uploader_id': channel_data['ownerAccount']['id'],
            'uploader_url': channel_data['ownerAccount']['url'],
        }


class PeerTubeAccountSHIE(PeerTubeBaseExtractor):
    _VALID_URL = r'peertube:account:(?P<host>[^:]+):(?P<id>.+)'
    _SH_VALID_URL = r'https?://(?P<host>[^/]+)/(?:api/v\d/)?accounts/(?P<id>[^/?#]+)(?:/video(?:s|-channels))?'

    _TESTS = [{
        'url': 'https://video.internet-czas-dzialac.pl/accounts/icd/video-channels',
        'info_dict': {
            'id': '3',
            'description': 'md5:ab3c9b934dd39030eea1c9fe76079870',
            'uploader': 'Internet. Czas działać!',
            'title': 'Internet. Czas działać!',
            'uploader_id': 3,
        },
        'playlist_mincount': 14,
    }]

    def _selfhosted_extract(self, url, webpage=None):
        host, display_id = self._match_id_and_host(url)

        account_data = self._call_api(host, 'accounts', display_id, '', 'Downloading account metadata')
        entries = []
        i = 0
        videos = {'total': 0}
        while len(entries) < videos['total'] or i == 0:
            videos = self._call_api(host, 'accounts', display_id,
                                    'videos?start=%d&count=25&sort=publishedAt' % (i * 25),
                                    note=('Downloading account video list (page #%d)' % i))
            i += 1
            for video in videos['data']:
                entries.append(self._parse_video(video, url))

        return {
            '_type': 'playlist',
            'entries': entries,
            'id': str(account_data['id']),
            'title': account_data['displayName'],
            'display_id': account_data['name'],
            'description': account_data.get('description'),
            'uploader': account_data['displayName'],
            'uploader_id': account_data['id'],
            'uploader_url': account_data['url'],
        }
