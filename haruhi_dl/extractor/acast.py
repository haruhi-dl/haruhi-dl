# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    clean_podcast_url,
    float_or_none,
    int_or_none,
    js_to_json,
    parse_iso8601,
    urljoin,
    ExtractorError,
)


class ACastBaseIE(InfoExtractor):
    def _extract_episode(self, episode, show_info):
        title = episode['title']
        info = {
            'id': episode['id'],
            'display_id': episode.get('episodeUrl'),
            'url': clean_podcast_url(episode['url']),
            'title': title,
            'description': clean_html(episode.get('description') or episode.get('summary')),
            'thumbnail': episode.get('image'),
            'timestamp': parse_iso8601(episode.get('publishDate')),
            'duration': int_or_none(episode.get('duration')),
            'filesize': int_or_none(episode.get('contentLength')),
            'season_number': int_or_none(episode.get('season')),
            'episode': title,
            'episode_number': int_or_none(episode.get('episode')),
        }
        info.update(show_info)
        return info

    def _extract_show_info(self, show):
        return {
            'creator': show.get('author'),
            'series': show.get('title'),
        }

    def _call_api(self, path, video_id, query=None):
        return self._download_json(
            'https://feeder.acast.com/api/v1/shows/' + path, video_id, query=query)


class ACastIE(ACastBaseIE):
    IE_NAME = 'acast'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:(?:embed|www)\.)?acast\.com/|
                            play\.acast\.com/s/
                        )
                        (?P<channel>[^/]+)/(?P<id>[^/#?]+)
                    '''
    _TESTS = [{
        'url': 'https://www.acast.com/sparpodcast/2.raggarmordet-rosterurdetforflutna',
        'md5': 'f5598f3ad1e4776fed12ec1407153e4b',
        'info_dict': {
            'id': '2a92b283-1a75-4ad8-8396-499c641de0d9',
            'ext': 'mp3',
            'title': '2. Raggarmordet - Röster ur det förflutna',
            'description': 'md5:a992ae67f4d98f1c0141598f7bebbf67',
            'timestamp': 1477346700,
            'upload_date': '20161024',
            'duration': 2766,
            'creator': 'Anton Berg & Martin Johnson',
            'series': 'Spår',
            'episode': '2. Raggarmordet - Röster ur det förflutna',
        }
    }, {
        'url': 'http://embed.acast.com/adambuxton/ep.12-adam-joeschristmaspodcast2015',
        'only_matching': True,
    }, {
        'url': 'https://play.acast.com/s/rattegangspodden/s04e09styckmordetihelenelund-del2-2',
        'only_matching': True,
    }, {
        'url': 'https://play.acast.com/s/sparpodcast/2a92b283-1a75-4ad8-8396-499c641de0d9',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        channel, display_id = re.match(self._VALID_URL, url).groups()
        episode = self._call_api(
            '%s/episodes/%s' % (channel, display_id),
            display_id, {'showInfo': 'true'})
        return self._extract_episode(
            episode, self._extract_show_info(episode.get('show') or {}))


class ACastChannelIE(ACastBaseIE):
    IE_NAME = 'acast:channel'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:www\.)?acast\.com/|
                            play\.acast\.com/s/
                        )
                        (?P<id>[^/#?]+)
                    '''
    _TESTS = [{
        'url': 'https://www.acast.com/todayinfocus',
        'info_dict': {
            'id': '4efc5294-5385-4847-98bd-519799ce5786',
            'title': 'Today in Focus',
            'description': 'md5:c09ce28c91002ce4ffce71d6504abaae',
        },
        'playlist_mincount': 200,
    }, {
        'url': 'http://play.acast.com/s/ft-banking-weekly',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if ACastIE.suitable(url) else super(ACastChannelIE, cls).suitable(url)

    def _real_extract(self, url):
        show_slug = self._match_id(url)
        show = self._call_api(show_slug, show_slug)
        show_info = self._extract_show_info(show)
        entries = []
        for episode in (show.get('episodes') or []):
            entries.append(self._extract_episode(episode, show_info))
        return self.playlist_result(
            entries, show.get('id'), show.get('title'), show.get('description'))


class ACastPlayerIE(InfoExtractor):
    IE_NAME = 'acast:player'
    _VALID_URL = r'https?://player\.acast\.com/(?:[^/]+/episodes/)?(?P<id>[^/?#]+)'

    _TESTS = [{
        'url': 'https://player.acast.com/600595844cac453f8579eca0/episodes/maciej-konieczny-podatek-medialny-to-mechanizm-kontroli?theme=default&latest=1',
        'info_dict': {
            'id': '601dc897fb37095537d48e6f',
            'ext': 'mp3',
            'title': 'Maciej Konieczny: "Podatek medialny to bardziej mechanizm kontroli niż podatkowy”',
            'upload_date': '20210208',
            'timestamp': 1612764000,
        },
    }, {
        'url': 'https://player.acast.com/5d09057251a90dcf7fa8e985?theme=default&latest=1',
        'info_dict': {
            'id': '5d09057251a90dcf7fa8e985',
            'title': 'DGPtalk: Obiektywnie o biznesie',
        },
        'playlist_mincount': 5,
    }]

    @staticmethod
    def _extract_urls(webpage, **kw):
        return [mobj.group('url')
                for mobj in re.finditer(
                    r'(?x)<iframe\b[^>]+\bsrc=(["\'])(?P<url>%s(?:\?[^#]+)?(?:\#.+?)?)\1' % ACastPlayerIE._VALID_URL,
                    webpage)]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        data = self._parse_json(
            js_to_json(
                self._search_regex(
                    r'(?s)var _global\s*=\s*({.+?});',
                    webpage, 'podcast data')), display_id)

        show = data['show']

        players = [{
            'id': player['_id'],
            'title': player['title'],
            'url': player['audio'],
            'duration': float_or_none(player.get('duration')),
            'timestamp': parse_iso8601(player.get('publishDate')),
            'thumbnail': urljoin('https://player.acast.com/', player.get('cover')),
            'series': show['title'],
            'episode': player['title'],
        } for player in data['player']]

        if len(players) > 1:
            info_dict = {
                '_type': 'playlist',
                'entries': players,
                'id': show['_id'],
                'title': show['title'],
                'series': show['title'],
            }
            if show.get('cover'):
                info_dict['thumbnails'] = [{
                    'url': urljoin('https://player.acast.com/', show['cover']['url']),
                    'filesize': int_or_none(show['cover'].get('size')),
                }]
            return info_dict

        if len(players) == 1:
            return players[0]

        raise ExtractorError('No podcast episodes found')
