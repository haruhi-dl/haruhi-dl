# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    compat_str,
    int_or_none,
    parse_iso8601,
    str_or_none,
    unescapeHTML,
    ExtractorError,
)


class TVNPlayerIE(InfoExtractor):
    _VALID_URL = r'https?://player\.pl/(?:programy|seriale)-online/[^/,]+,([0-9]+)/(?:[^/,]+,){2}(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://player.pl/seriale-online/kasia-i-tomek-odcinki,1/odcinek-1,S01E01,1',
        'info_dict': {
            'id': '1',
            'ext': 'mp4',
            'title': 'Kasia i Tomek - ',  # I love when my code works so well
            'age_limit': 12,
        },
    }, {
        'url': 'https://player.pl/programy-online/w-roli-glownej-odcinki,41/odcinek-3,S07E03,2137',
        'info_dict': {
            'id': '2137',
            'ext': 'mp4',
            'title': 'W roli głównej - Magda Gessler',
            'age_limit': 12,
        }
    }]
    IE_NAME = 'tvnplayer'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        res = self._download_json('http://api.tvnplayer.pl/api/?platform=ConnectedTV&terminal=Panasonic&format=json&authKey=064fda5ab26dc1dd936f5c6e84b7d3c2&v=3.1&m=getItem&id=' + video_id, video_id)

        formats = []

        for ptrciscute in res["item"]["videos"]["main"]["video_content"]:
            formats.append({
                "url": ptrciscute["url"],
                "format_note": ptrciscute["profile_name"],
                "tbr": int_or_none(self._search_regex(r'tv_mp4_([0-9]+)\.mp4', ptrciscute["url"], video_id))
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': res["item"]["serie_title"] + " - " + res["item"]["title"],
            'formats': formats,
            'series': str_or_none(res["item"]["serie_title"]),
            'episode': str_or_none(res["item"]["title"]),
            'episode_number': int_or_none(res["item"]["episode"]),
            'season_number': int_or_none(res["item"]["season"]),
            'age_limit': int_or_none(res["item"]["rating"])
        }


class TVNPlayerSeriesIE(InfoExtractor):
    _VALID_URL = r'https?://player\.pl/(?:programy|seriale)-online/[^/,]+,(?P<id>[0-9]+)/?(?:\?.+)?(?:#.+)?$'
    _TESTS = [{
        'url': 'https://player.pl/seriale-online/brzydula-odcinki,52',
        'info_dict': {
            'id': '55359',
            'title': 'Brzydula',
            'age_limit': 12,
        },
        'playlist_mincount': 290,
        'expected_warnings': [
            'Some of the videos are not available yet, you may want to know about the --ignore-errors option.',
            'Some of the videos are behind the paywall for now, you may want to know about the --ignore-errors option.',
        ],
    }]
    IE_NAME = 'tvnplayer:series'

    def _real_extract(self, url):
        series_id = self._match_id(url)

        internal_id = self._download_json(
            'https://player.pl/playerapi/item/translate?programId=%s&4K=true&platform=BROWSER' % series_id,
            series_id, 'Downloading internal series ID')
        if 'id' not in internal_id:
            raise ExtractorError('Unable to get the internal series ID: %s' % internal_id.get('code'))
        internal_id = compat_str(internal_id['id'])

        series_meta = self._download_json(
            'https://player.pl/playerapi/product/vod/serial/%s?4K=true&platform=BROWSER' % internal_id,
            internal_id, 'Downloading internal series ID')

        season_list = self._download_json(
            'https://player.pl/playerapi/product/vod/serial/%s/season/list?4K=true&platform=BROWSER' % internal_id,
            internal_id, 'Downloading season list')

        entries = []
        prapremiere_warning = False
        paywall_warning = False
        for season in season_list:
            season_id = compat_str(season['id'])
            season_episodes = self._download_json(
                'https://player.pl/playerapi/product/vod/serial/%s/season/%s/episode/list?4K=true&platform=BROWSER' % (internal_id, season_id),
                season_id, 'Downloading season %s episode list' % season['display'])
            for episode in season_episodes:
                entries.append({
                    '_type': 'url_transparent',
                    'url': episode['shareUrl'],
                    'ie_key': 'TVNPlayer',
                    'id': str_or_none(episode['id']),
                    'title': episode['title'],
                    'description': unescapeHTML(episode.get('lead')),
                    'timestamp': parse_iso8601(episode.get('since')),
                    'age_limit': episode.get('rating'),
                    'series': series_meta['title'],
                    'season': season['title'],
                    'season_number': season['number'],
                    'season_id': season['display'],
                    'episode': episode['title'],
                    'episode_number': episode['episode'],
                })
                if not prapremiere_warning:
                    if any(schedule['type'] == 'SOON' and schedule['active'] is True
                           for schedule in episode['displaySchedules']):
                        prapremiere_warning = True
                if not paywall_warning and episode.get('payable') is True:
                    paywall_warning = True

        if prapremiere_warning:
            self.report_warning('Some of the videos are not available yet, you may want to know about the --ignore-errors option.')
        if paywall_warning:
            self.report_warning('Some of the videos are behind the paywall for now, you may want to know about the --ignore-errors option.')

        return {
            '_type': 'playlist',
            'id': internal_id,
            'title': series_meta['title'],
            'series': series_meta['title'],
            'age_limit': series_meta.get('rating'),
            'entries': entries,
        }
