# coding: utf-8
from __future__ import unicode_literals

import re
import uuid

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_duration,
    ExtractorError,
)


# this id is not an article id, it has to be extracted from the article
class WyborczaVideoIE(InfoExtractor):
    _VALID_URL = r'wyborcza:video:(?P<id>\d+)'
    IE_NAME = 'wyborcza:video'
    _TESTS = [{
        'url': 'wyborcza:video:26207634',
        'info_dict': {
            'id': '26207634',
            'ext': 'mp4',
            'title': '- Polska w 2020 r. jest innym państwem niż w 2015 r. Nie zmieniła się konstytucja, ale jest to już inny ustrój - mówi Adam Bodnar',
            'description': ' ',
            'uploader': 'Dorota Roman',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        meta = self._download_json('https://wyborcza.pl/api-video/%s' % video_id, video_id)

        formats = []
        base_url = meta['redirector'].replace('http://', 'https://') + meta['basePath']
        for quality in ('standard', 'high'):
            if not meta['files'].get(quality):
                continue
            formats.append({
                'url': base_url + meta['files'][quality],
                'height': int_or_none(
                    self._search_regex(
                        r'p(\d+)[a-z]+\.mp4$', meta['files'][quality],
                        'mp4 video height', default=None)),
                'format_id': quality,
            })
        if meta['files'].get('dash'):
            formats.extend(
                self._extract_mpd_formats(
                    base_url + meta['files']['dash'], video_id))

        self._sort_formats(formats)

        return {
            'id': video_id,
            'formats': formats,
            'title': meta['title'],
            'description': meta.get('lead'),
            'uploader': meta.get('signature'),
            'thumbnail': meta.get('imageUrl'),
            'duration': meta.get('duration'),
        }


class WyborczaPodcastIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?
            (?:wyborcza\.pl/podcast(?:/0,172673\.html)?
            |wysokieobcasy\.pl/wysokie-obcasy/0,176631\.html)
        (?:\?(?:[^&]+?&)*?podcast=(?P<episode_id>\d+))?
    '''
    _TESTS = [{
        'url': 'https://wyborcza.pl/podcast/0,172673.html?podcast=100720#S.main_topic-K.C-B.6-L.1.podcast',
        'info_dict': {
            'id': '100720',
            'ext': 'mp3',
            'title': 'Cyfrodziewczyny. Kim były pionierki polskiej informatyki ',
            'uploader': 'Michał Nogaś ',
            'upload_date': '20210117',
            'description': 'md5:49f0a06ffc4c1931210d3ab1416a651d',
        },
    }, {
        'url': 'https://www.wysokieobcasy.pl/wysokie-obcasy/0,176631.html?podcast=100673',
        'info_dict': {
            'id': '100673',
            'ext': 'mp3',
            'title': 'Czym jest ubóstwo menstruacyjne i dlaczego dotyczy każdej i każdego z nas?',
            'uploader': 'Agnieszka Urazińska ',
            'upload_date': '20210115',
            'description': 'md5:c161dc035f8dbb60077011fc41274899',
        },
    }, {
        'url': 'https://wyborcza.pl/podcast',
        'info_dict': {
            'id': '334',
            'title': 'Gościnnie w TOK FM: Wyborcza, 8:10',
        },
        'playlist_mincount': 370,
    }, {
        'url': 'https://www.wysokieobcasy.pl/wysokie-obcasy/0,176631.html',
        'info_dict': {
            'id': '395',
            'title': 'Gościnnie w TOK FM: Wysokie Obcasy',
        },
        'playlist_mincount': 12,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        podcast_id = mobj.group('episode_id')
        # linking to the playlist and not specific episode
        if not podcast_id:
            return {
                '_type': 'url',
                'url': 'tokfm:audition:%s' % ('395' if 'wysokieobcasy.pl/' in url else '334'),
                'ie_key': 'TokFMAudition',
            }
        meta = self._download_json('https://wyborcza.pl/api/podcast?guid=%s%s' % (podcast_id,
                                                                                  '&type=wo' if 'wysokieobcasy.pl/' in url else ''),
                                   podcast_id)
        published_date = meta['publishedDate'].split(' ')
        upload_date = '%s%s%s' % (published_date[2], {
            'stycznia': '01',
            'lutego': '02',
            'marca': '03',
            'kwietnia': '04',
            'maja': '05',
            'czerwca': '06',
            'lipca': '07',
            'sierpnia': '08',
            'września': '09',
            'października': '10',
            'listopada': '11',
            'grudnia': '12',
        }.get(published_date[1]), ('0' + published_date[0])[-2:])
        return {
            'id': podcast_id,
            'title': meta['title'],
            'url': meta['url'],
            'description': meta.get('description'),
            'thumbnail': meta.get('imageUrl'),
            'duration': parse_duration(meta.get('duration')),
            'uploader': meta.get('author'),
            'upload_date': upload_date,
        }


class TokFMPodcastIE(InfoExtractor):
    _VALID_URL = r'(?:https?://audycje\.tokfm\.pl/podcast/|tokfm:podcast:)(?P<id>\d+),?'
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
    _VALID_URL = r'(?:https?://audycje\.tokfm\.pl/audycja/|tokfm:audition:)(?P<id>\d+),?'
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

        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 9; Redmi 3S Build/PQ3A.190801.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/87.0.4280.101 Mobile Safari/537.36',
        }

        data = self._download_json(
            'https://api.podcast.radioagora.pl/api4/getSeries?series_id=%s' % (audition_id),
            audition_id, 'Downloading audition metadata', headers=headers)

        if len(data) == 0:
            raise ExtractorError('No such audition')
        data = data[0]
        entries = []
        for page in range(0, (int(data['total_podcasts']) // 30) + 1):
            podcast_page = False
            retries = 0
            while retries <= 5 and podcast_page is False:
                podcast_page = self._download_json(
                    'https://api.podcast.radioagora.pl/api4/getPodcasts?series_id=%s&limit=30&offset=%d&with_guests=true&with_leaders_for_mobile=true' % (audition_id, page),
                    audition_id, 'Downloading podcast list (page #%d%s)' % (
                        page + 1,
                        (', try %d' % retries) if retries > 0 else ''),
                    headers=headers)
                retries += 1
            if podcast_page is False:
                raise ExtractorError('Agora returned shit 5 times in a row', expected=True)
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
