# coding: utf-8

from .common import InfoExtractor

import datetime


class SenatPlArchivalIE(InfoExtractor):
    _VALID_URL = r'https://av8\.senat\.pl/(?P<id>\d+[a-zA-Z\d]+)'
    IE_NAME = 'senat.pl:archival'

    _TESTS = [{
        'url': 'https://av8.senat.pl/10Sen221',
        'info_dict': {
            'id': '10Sen221',
            'title': '22. posiedzenie Senatu RP X kadencji - 24.03.2021 r. - cz. 1',
        },
        'playlist_count': 2,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        vod = self._download_json(
            'https://av8.senat.pl/senat-console/side-menu/transmissions/%s/vod' % video_id,
            video_id, 'Downloading transmission metadata')
        conf = self._download_json(
            'https://av8.senat.pl/senat-console/side-menu/transmissions/%s/vod/player-configuration' % video_id,
            video_id, 'Downloading player configuration')

        def unix_milliseconds_to_wtf_atende_wants(date):
            date = datetime.datetime.fromtimestamp(date / 1000)
            # atende uses timestamp but since 2001 instead of 1970
            date = date.replace(year=date.year - 31)
            # also it's in milliseconds
            return int(date.timestamp() * 1000)

        start_time = unix_milliseconds_to_wtf_atende_wants(vod['since'])
        stop_time = unix_milliseconds_to_wtf_atende_wants(vod['till'])

        duration = (stop_time - start_time) // 1000

        entries = []

        def add_entry(player):
            entries.append({
                '_type': 'url_transparent',
                'url': f"https:{player['playlist']['flv']}?startTime={start_time}&stopTime={stop_time}",
                'ie_key': 'SejmPlVideo',
            })

        add_entry(conf['player'])

        # PJM translator
        if conf.get('sliPlayer'):
            add_entry(conf['sliPlayer'])

        return {
            '_type': 'multi_video',
            'entries': entries,
            'id': video_id,
            'title': vod['title'],
            'duration': duration,
        }
