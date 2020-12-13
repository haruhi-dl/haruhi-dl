# coding: utf-8
from __future__ import unicode_literals

from .common import SelfhostedInfoExtractor
from ..utils import (
    compat_str,
    compat_urllib_parse_urlencode,
    float_or_none,
    int_or_none,
    try_get,
    parse_iso8601,
    str_or_none,
)


class FunkwhaleBaseExtractor(SelfhostedInfoExtractor):
    _SH_VALID_CONTENT_STRINGS = (
        "<noscript><strong>We're sorry but Funkwhale doesn't work",
        "<meta name=generator content=Funkwhale>",
    )

    def _call_api(self, host, method, params, vis_id, note='Downloading JSON metadata'):
        # basic querystring handling
        qs = ''
        if isinstance(params, dict):
            qs = compat_urllib_parse_urlencode(params)
        return self._download_json('https://%s/api/v1/%s?%s' % (host, method, qs), vis_id, note)

    def _cover_to_thumbnails(self, cover_data):
        if cover_data is None:
            return cover_data

        thumbnails = [{
            'url': cover_data['urls']['original'],
            'filesize': cover_data['size'],
            'preference': 500,
        }]
        for quality in ('large_square_crop', 'medium_square_crop'):
            if cover_data['urls'].get(quality):
                thumbnails.append({
                    'url': cover_data['urls'][quality],
                })
        return thumbnails

    def _track_data_to_entry(self, track_data, host):
        formats = []
        for upload in track_data.get('uploads') or ():
            formats.append({
                'url': 'https://%s%s' % (host, upload['listen_url']),
                'ext': upload['extension'],
                'abr': upload['bitrate'],
                'filesize': upload['size'],
            })

        channel_data = track_data.get('artist', {})

        info_dict = {
            'id': compat_str(track_data['id']),
            'formats': formats,
            'title': track_data['title'],
            'description': try_get(track_data, lambda x: x['description']['text'], compat_str),
            'channel': channel_data.get('name'),
            'channel_url': 'https://%s/library/artists/%d/' % (host, channel_data.get('id'))
            if isinstance(channel_data.get('id'), int) else None,

            'thumbnails': self._cover_to_thumbnails(try_get(track_data, (
                lambda x: x['cover'],
                lambda x: x['album']['cover'],
            ), dict)),
            'duration': float_or_none(try_get(track_data, lambda x: x['uploads'][0]['duration'])),
            'timestamp': parse_iso8601(track_data.get('creation_date')),
            'view_count': track_data.get('downloads_count'),
            'license': track_data.get('license'),
            'tags': track_data.get('tags'),
        }
        info_dict.update(self._uploader_data_to_info_dict(track_data.get('attributed_to')))
        info_dict.update(self._album_to_info_dict(track_data.get('album'), track_data))
        return info_dict

    def _uploader_data_to_info_dict(self, uploader_data):
        if uploader_data is None:
            return {}

        return {
            'uploader': uploader_data.get('name'),
            'uploader_url': 'https://%s/@%s' % (uploader_data.get('domain'), uploader_data.get('preferred_username')),
        }

    def _album_to_info_dict(self, album_data, track_data={}):
        if album_data is None:
            return {}
        return {
            'track': str_or_none(track_data.get('title')),
            'track_number': int_or_none(track_data.get('position')),
            'album': str_or_none(album_data.get('title')),
            'artist': str_or_none(track_data.get('artist', {}).get('name')),
            'album_artist': str_or_none(album_data.get('artist', {}).get('name')),
            'release_year': int_or_none((album_data.get('release_date') or '')[:4]),
        }


class FunkwhaleTrackSHIE(FunkwhaleBaseExtractor):
    IE_NAME = 'funkwhale:track'

    _VALID_URL = r'funkwhale:track:(?P<host>[^:]+):(?P<id>.+)'
    _SH_VALID_URL = r'https?://(?P<host>[^/]+)/library/tracks/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://podcast.midline.pl/library/tracks/10/',
        'info_dict': {
            'id': '10',
            'ext': 'mp3',
            'uploader': 'Internet. Czas działać!',
            'title': '#0 - Podcast "Internet. Czas działać! | Trailer',
            'description': '"Internet. Czas działać!" to podcast, z którego dowiecie się, jak internetowe technologie wpływają na społeczeństwo i jak być ich świadomym konsumentem.',
            'upload_date': '20201207',
            'timestamp': 1607301944,
        },
    }]

    def _selfhosted_extract(self, url, webpage=None):
        host, vis_id = self._match_id_and_host(url)

        track_data = self._call_api(host, 'tracks/%s' % vis_id, None, vis_id)

        info_dict = self._track_data_to_entry(track_data, host)
        info_dict.update({
            'webpage_url': 'funkwhale:track:%s:%s' % (host, vis_id),
        })
        return info_dict


class FunkwhaleArtistSHIE(FunkwhaleBaseExtractor):
    IE_NAME = 'funkwhale:artist'

    _VALID_URL = r'funkwhale:artist:(?P<host>[^:]+):(?P<id>.+)'
    _SH_VALID_URL = r'https?://(?P<host>[^/]+)/library/artists/(?P<id>[\w-]+)'

    _TESTS = [{
        'url': 'https://open.audio/library/artists/13556/',
        'info_dict': {
            'id': '13556',
            'title': 'Violons_Populaires_en_Nouvelle_Aquitaine',
            'uploader': 'Violons_Populaires_en_Nouvelle_Aquitaine',
        },
        'playlist_mincount': 38,    # 77 tracks, but just 38 of them are playable 🤷‍♀️
    }]

    def _selfhosted_extract(self, url, webpage=None):
        host, vis_id = self._match_id_and_host(url)

        artist_data = self._call_api(host, 'artists/%s' % vis_id, None, vis_id)

        # the same is done on the frontend
        # https://dev.funkwhale.audio/funkwhale/funkwhale/-/blob/89037a76/front/src/components/library/ArtistBase.vue#L189
        if artist_data.get('channel'):
            return self.url_result('funkwhale:channel:%s:%s' % (host, artist_data['channel']['uuid']), ie='FunkwhaleChannelSH')

        tracks_data = self._call_api(host, 'tracks', {
            'artist': vis_id,
            'hidden': '',
            'playable': 'true',
        }, vis_id, 'Downloading track list')
        tracks = tracks_data['results']
        page = 1
        while tracks_data.get('next') is not None:
            page += 1
            tracks_data = tracks_data = self._call_api(host, 'tracks', {
                'artist': vis_id,
                'hidden': '',
                'playable': 'true',
                'page': page,
            }, vis_id, 'Downloading track list (page #%d)' % page)
            tracks.extend(tracks_data['results'])
        entries = [self._track_data_to_entry(track, host) for track in tracks]

        info_dict = {
            '_type': 'playlist',
            'id': vis_id,
            'entries': entries,
            'title': artist_data['attributed_to'].get('name'),
            'webpage_url': 'funkwhale:artist:%s:%s' % (host, vis_id),
        }
        info_dict.update(self._uploader_data_to_info_dict(artist_data['attributed_to']))

        return info_dict


class FunkwhaleChannelSHIE(FunkwhaleBaseExtractor):
    IE_NAME = 'funkwhale:channel'

    _VALID_URL = r'funkwhale:channel:(?P<host>[^:]+):(?P<id>.+)'
    _SH_VALID_URL = r'https?://(?P<host>[^/]+)/channels/(?P<id>[\w-]+)'

    _TESTS = [{
        'url': 'https://podcast.midline.pl/channels/Midline/',
        'info_dict': {
            'id': 'd98ae7a5-5bd5-48c8-a178-a9a12e84cfc7',
            'title': 'Internet. Czas działać!',
            'uploader': 'Internet. Czas działać!',
        },
        'playlist_mincount': 9,
    }, {
        'url': 'https://podcast.midline.pl/channels/d98ae7a5-5bd5-48c8-a178-a9a12e84cfc7/',
        'only_matching': True,
    }]

    def _selfhosted_extract(self, url, webpage=None):
        host, vis_id = self._match_id_and_host(url)

        channel_data = self._call_api(host, 'channels/%s' % vis_id, None, vis_id)
        uuid = channel_data['uuid']
        tracks_data = self._call_api(host, 'tracks', {
            'channel': uuid,
            'include_channels': 'true',
            'playable': 'true',
        }, uuid, 'Downloading track list')
        tracks = tracks_data['results']
        page = 1
        while tracks_data.get('next') is not None:
            page += 1
            tracks_data = tracks_data = self._call_api(host, 'tracks', {
                'channel': uuid,
                'include_channels': 'true',
                'playable': 'true',
                'page': page,
            }, vis_id, 'Downloading track list (page #%d)' % page)
            tracks.extend(tracks_data['results'])
        entries = [self._track_data_to_entry(track, host) for track in tracks]

        info_dict = {
            '_type': 'playlist',
            'id': uuid,
            'title': channel_data['attributed_to'].get('name'),
            'entries': entries,
            'webpage_url': 'funkwhale:channel:%s:%s' % (host, vis_id),
        }
        info_dict.update(self._uploader_data_to_info_dict(channel_data['attributed_to']))
        return info_dict


class FunkwhalePlaylistSHIE(FunkwhaleBaseExtractor):
    IE_NAME = 'funkwhale:playlist'

    _VALID_URL = r'funkwhale:playlist:(?P<host>[^:]+):(?P<id>.+)'
    _SH_VALID_URL = r'https?://(?P<host>[^/]+)/library/playlists/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://open.audio/library/playlists/268',
        'info_dict': {
            'id': '268',
            'title': 'Cleaning',
            'uploader': 'trash',
        },
        'playlist_mincount': 180,
    }]

    def _selfhosted_extract(self, url, webpage=None):
        host, vis_id = self._match_id_and_host(url)

        playlist_data = self._call_api(host, 'playlists/%s' % vis_id, None, vis_id)
        tracks_data = self._call_api(host, 'playlists/%s/tracks' % vis_id, {
            'playable': 'true',
        }, vis_id, 'Downloading track list')
        entries = [self._track_data_to_entry(track.get('track'), host) for track in tracks_data['results']]

        info_dict = {
            '_type': 'playlist',
            'id': vis_id,
            'title': playlist_data['name'],
            'entries': entries,
            'webpage_url': 'funkwhale:playlist:%s:%s' % (host, vis_id),
        }
        info_dict.update(self._uploader_data_to_info_dict(playlist_data.get('actor')))
        return info_dict


class FunkwhaleAlbumSHIE(FunkwhaleBaseExtractor):
    IE_NAME = 'funkwhale:album'

    _VALID_URL = r'funkwhale:album:(?P<host>[^:]+):(?P<id>.+)'
    _SH_VALID_URL = r'https?://(?P<host>[^/]+)/library/albums/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://open.audio/library/albums/5623/',
        'info_dict': {
            'id': '5623',
            'title': 'Volume 5',
        },
        'playlist_mincount': 115,
    }]

    def _selfhosted_extract(self, url, webpage=None):
        host, vis_id = self._match_id_and_host(url)

        album_data = self._call_api(host, 'albums/%s' % vis_id, None, vis_id)
        tracks_data = self._call_api(host, 'tracks', {
            'ordering': 'disc_number,position',
            'album': vis_id,
            'include_channels': 'true',
            'playable': 'true',
        }, vis_id, 'Downloading track list')
        tracks = tracks_data['results']
        page = 1
        while tracks_data.get('next') is not None:
            page += 1
            tracks_data = tracks_data = self._call_api(host, 'tracks', {
                'ordering': 'disc_number,position',
                'album': vis_id,
                'include_channels': 'true',
                'playable': 'true',
                'page': page,
            }, vis_id, 'Downloading track list (page #%d)' % page)
            tracks.extend(tracks_data['results'])
        entries = [self._track_data_to_entry(track, host) for track in tracks]

        thumbnails = self._cover_to_thumbnails(album_data.get('cover'))

        info_dict = {
            '_type': 'playlist',
            'id': vis_id,
            'title': album_data['title'],
            'entries': entries,
            'thumbnails': thumbnails,
            'webpage_url': 'funkwhale:album:%s:%s' % (host, vis_id),
        }
        info_dict.update(self._album_to_info_dict(album_data))
        return info_dict


class FunkwhaleRadioSHIE(FunkwhaleBaseExtractor):
    IE_NAME = 'funkwhale:radio'

    _VALID_URL = r'funkwhale:radio:(?P<host>[^:]+):(?P<id>.+)'
    _SH_VALID_URL = r'https?://(?P<host>[^/]+)/library/radios/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://open.audio/library/radios/4',
        'info_dict': {
            'id': '4',
            'title': 'FLOSS super radio',
        },
        'playlist_mincount': 77,
    }]

    def _selfhosted_extract(self, url, webpage=None):
        host, vis_id = self._match_id_and_host(url)

        radio_data = self._call_api(host, 'radios/radios/%s' % vis_id, None, vis_id)
        tracks_data = self._call_api(host, 'radios/radios/%s/tracks' % vis_id, {
            'playable': 'true',
        }, vis_id, 'Downloading track list')
        tracks = tracks_data['results']
        page = 1
        while tracks_data.get('next') is not None:
            page += 1
            tracks_data = tracks_data = self._call_api(host, 'radios/radios/%s/tracks' % vis_id, {
                'playable': 'true',
                'page': page,
            }, vis_id, 'Downloading track list (page #%d)' % page)
            tracks.extend(tracks_data['results'])
        entries = [self._track_data_to_entry(track, host) for track in tracks]

        thumbnails = self._cover_to_thumbnails(radio_data.get('user', {}).get('avatar'))

        info_dict = {
            '_type': 'playlist',
            'id': vis_id,
            'title': radio_data['name'],
            'entries': entries,
            'thumbnails': thumbnails,
            'webpage_url': 'funkwhale:radio:%s:%s' % (host, vis_id),
        }
        return info_dict
