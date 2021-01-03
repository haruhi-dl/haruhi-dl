# coding: utf-8
from __future__ import unicode_literals

import uuid

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    ExtractorError,
)


class TokFMPodcastIE(InfoExtractor):
    _VALID_URL = r'https?://audycje\.tokfm\.pl/podcast/(?P<id>\d+),'

    IE_NAME = 'tokfm:podcast'

    _TESTS = [{
        'url': 'https://audycje.tokfm.pl/podcast/91275,-Systemowy-rasizm-Czy-zamieszki-w-USA-po-morderstwie-w-Minneapolis-doprowadza-do-zmian-w-sluzbach-panstwowych',
        'info_dict': {
            'id': '91275',
            'ext': 'mp3',
            'title': '"Systemowy rasizm." Czy zamieszki w USA po morderstwie w Minneapolis doprowadzą do zmian w służbach państwowych?',
            'series': 'Analizy',
        },
    }]

    def _real_extract(self, url):
        media_id = self._match_id(url)

        metadata = self._download_json(
            # why the fuck does this start with 3??????
            # in case it breaks see this but it returns a lot of useless data
            # https://api.podcast.radioagora.pl/api4/getPodcasts?podcast_id=100091&with_guests=true&with_leaders_for_mobile=true
            'https://audycje.tokfm.pl/getp/3%s' % (media_id),
            media_id, 'Downloading podcast metadata')
        if len(metadata) == 0:
            raise ExtractorError('No such podcast')
        metadata = metadata[0]

        formats = []
        for ext in ('aac', 'mp3'):
            url_data = self._download_json(
                'https://api.podcast.radioagora.pl/api4/getSongUrl?podcast_id=%s&device_id=%s&ppre=false&audio=%s' % (media_id, uuid.uuid4(), ext),
                media_id, 'Downloading podcast %s URL' % ext)
            # prevents inserting the mp3 (default) multiple times
            if 'link_ssl' in url_data and ('.%s' % ext) in url_data['link_ssl']:
                formats.append({
                    'url': url_data['link_ssl'],
                    'ext': ext,
                })

        return {
            'id': media_id,
            'formats': formats,
            'title': metadata['podcast_name'],
            'series': metadata.get('series_name'),
            'episode': metadata['podcast_name'],
        }


class TokFMAuditionIE(InfoExtractor):
    _VALID_URL = r'https?://audycje\.tokfm\.pl/audycja/(?P<id>\d+),'

    IE_NAME = 'tokfm:audition'

    _TESTS = [{
        'url': 'https://audycje.tokfm.pl/audycja/218,Analizy',
        'info_dict': {
            'id': '218',
            'title': 'Analizy',
            'series': 'Analizy',
        },
        'playlist_count': 1635,
    }]

    def _real_extract(self, url):
        audition_id = self._match_id(url)

        data = self._download_json(
            'https://api.podcast.radioagora.pl/api4/getSeries?series_id=%s' % (audition_id),
            audition_id, 'Downloading audition metadata')
        self.to_screen(data)
        if len(data) == 0:
            raise ExtractorError('No such audition')
        data = data[0]
        entries = []
        for page in range(0, (int(data['total_podcasts']) // 30) + 1):
            podcast_page = self._download_json(
                'https://api.podcast.radioagora.pl/api4/getPodcasts?series_id=%s&limit=30&offset=%d&with_guests=true&with_leaders_for_mobile=true' % (audition_id, page),
                audition_id, 'Downloading podcast list (page #%d)' % (page + 1))
            for podcast in podcast_page:
                entries.append({
                    '_type': 'url_transparent',
                    'url': podcast['podcast_sharing_url'],
                    'title': podcast['podcast_name'],
                    'episode': podcast['podcast_name'],
                    'description': podcast.get('podcast_description'),
                    'timestamp': int_or_none(podcast.get('podcast_timestamp')),
                    'series': data['series_name'],
                })

        return {
            '_type': 'playlist',
            'id': audition_id,
            'title': data['series_name'],
            'series': data['series_name'],
            'entries': entries,
        }
