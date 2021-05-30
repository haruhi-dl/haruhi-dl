# coding: utf-8

from .common import InfoExtractor
from ..utils import (
    unescapeHTML,
)

from urllib.parse import urlencode


class RadioKapitalBaseIE(InfoExtractor):
    # offtopic: Kapitał did a great job with their frontend, which just works quickly after opening
    # this just can't be compared to any commercial radio or news services.
    # also it's the first wordpress page I don't hate.
    def _call_api(self, resource, video_id, note='Downloading JSON metadata', qs={}):
        return self._download_json(
            f'https://www.radiokapital.pl/wp-json/kapital/v1/{resource}?{urlencode(qs)}',
            video_id, note=note)

    def _parse_episode(self, ep):
        data = ep['data']
        release = '%s%s%s' % (data['published'][6:11], data['published'][3:6], data['published'][:3])
        return {
            '_type': 'url_transparent',
            'url': data['mixcloud_url'],
            'ie_key': 'Mixcloud',
            'id': str(data['id']),
            'title': unescapeHTML(data['title']),
            'description': data.get('content'),
            'tags': [tag['name'] for tag in data['tags']],
            'release_date': release,
            'series': data['show']['title'],
        }


class RadioKapitalIE(RadioKapitalBaseIE):
    IE_NAME = 'radiokapital'
    _VALID_URL = r'https?://(?:www\.)?radiokapital\.pl/shows/[a-z\d-]+/(?P<id>[a-z\d-]+)'

    _TESTS = [{
        'url': 'https://radiokapital.pl/shows/tutaj-sa-smoki/5-its-okay-to-be-immaterial',
        'info_dict': {
            'id': 'radiokapital_radio-kapitał-tutaj-są-smoki-5-its-okay-to-be-immaterial-2021-05-20',
            'ext': 'm4a',
            'title': '#5: It’s okay to be immaterial',
            'description': 'md5:2499da5fbfb0e88333b7d37ec8e9e4c4',
            'uploader': 'Radio Kapitał',
            'uploader_id': 'radiokapital',
            'timestamp': 1621640164,
            'upload_date': '20210521',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        episode = self._call_api('episodes/%s' % video_id, video_id)
        return self._parse_episode(episode)


class RadioKapitalShowIE(RadioKapitalBaseIE):
    IE_NAME = 'radiokapital:show'
    _VALID_URL = r'https?://(?:www\.)?radiokapital\.pl/shows/(?P<id>[a-z\d-]+)/?(?:$|[?#])'

    _TESTS = [{
        'url': 'https://radiokapital.pl/shows/wesz',
        'info_dict': {
            'id': '100',
            'title': 'WĘSZ',
            'description': 'md5:9046105f7eeb03b7f01240fbed245df6',
        },
        'playlist_mincount': 17,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        page_no = 1
        page_count = 1
        entries = []
        while page_no <= page_count:
            episode_list = self._call_api(
                'episodes', video_id,
                f'Downloading episode list page #{page_no}', qs={
                    'show': video_id,
                    'page': page_no,
                })
            page_no += 1
            page_count = episode_list['max']
            for ep in episode_list['items']:
                entries.append(self._parse_episode(ep))

        show = episode_list['items'][0]['data']['show']
        return {
            '_type': 'playlist',
            'entries': entries,
            'id': str(show['id']),
            'title': show['title'],
            'description': show['content'],
        }
