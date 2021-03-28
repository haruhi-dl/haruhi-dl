# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    smuggle_url,
    unified_strdate,
    unsmuggle_url,
    ExtractorError,
)


class DWVideoIE(InfoExtractor):
    IE_NAME = 'dw:video'
    _VALID_URL = r'dw:(?P<id>\d+)'

    def _get_dw_formats(self, media_id, hidden_inputs):
        if hidden_inputs.get('player_type') == 'video':
            # https://www.dw.com/smil/v-{video_id} returns more formats,
            # but they are all RTMP. ytdl used to do this:
            #   url.replace('rtmp://tv-od.dw.de/flash/', 'http://tv-download.dw.de/dwtv_video/flv/')
            # this returns formats, but it's completely random if they work or not.
            formats = [{
                'url': fmt['file'],
                'format_code': fmt['label'],
                'height': int_or_none(fmt['label']),
            } for fmt in self._download_json(
                'https://www.dw.com/playersources/v-%s' % media_id,
                media_id, 'Downloading JSON formats')]
            self._sort_formats(formats)
        else:
            formats = [{'url': hidden_inputs['file_name']}]
        return {
            'id': media_id,
            'title': hidden_inputs['media_title'],
            'formats': formats,
            'duration': int_or_none(hidden_inputs.get('file_duration')),
            'upload_date': hidden_inputs.get('display_date'),
            'thumbnail': hidden_inputs.get('preview_image'),
            'is_live': hidden_inputs.get('isLiveVideo'),
        }

    def _real_extract(self, url):
        media_id = self._match_id(url)
        _, hidden_inputs = unsmuggle_url(url)
        if not hidden_inputs:
            return self.url_result('https://www.dw.com/en/av-%s' % media_id, 'DW', media_id)
        return self._get_dw_formats(media_id, hidden_inputs)


class DWIE(DWVideoIE):
    IE_NAME = 'dw'
    _VALID_URL = r'https?://(?:www\.)?dw\.com/(?:[^/]+/)+(?:av|e)-(?P<id>\d+)'
    _TESTS = [{
        # video
        'url': 'http://www.dw.com/en/intelligent-light/av-19112290',
        'md5': '7372046e1815c5a534b43f3c3c36e6e9',
        'info_dict': {
            'id': '19112290',
            'ext': 'mp4',
            'title': 'Intelligent light',
            'description': 'md5:90e00d5881719f2a6a5827cb74985af1',
            'upload_date': '20160605',
        }
    }, {
        # audio
        'url': 'http://www.dw.com/en/worldlink-my-business/av-19111941',
        'md5': '2814c9a1321c3a51f8a7aeb067a360dd',
        'info_dict': {
            'id': '19111941',
            'ext': 'mp3',
            'title': 'WorldLink: My business',
            'description': 'md5:bc9ca6e4e063361e21c920c53af12405',
            'upload_date': '20160311',
        }
    }, {
        # DW documentaries, only last for one or two weeks
        'url': 'http://www.dw.com/en/documentaries-welcome-to-the-90s-2016-05-21/e-19220158-9798',
        'md5': '56b6214ef463bfb9a3b71aeb886f3cf1',
        'info_dict': {
            'id': '19274438',
            'ext': 'mp4',
            'title': 'Welcome to the 90s – Hip Hop',
            'description': 'Welcome to the 90s - The Golden Decade of Hip Hop',
            'upload_date': '20160521',
        },
        'skip': 'Video removed',
    }]

    def _real_extract(self, url):
        media_id = self._match_id(url)
        webpage = self._download_webpage(url, media_id)
        hidden_inputs = self._hidden_inputs(webpage)
        media_id = hidden_inputs.get('media_id') or media_id

        info_dict = {
            'description': self._og_search_description(webpage),
        }
        info_dict.update(self._get_dw_formats(media_id, hidden_inputs))

        if info_dict.get('upload_date') is None:
            upload_date = self._html_search_regex(
                r'<span[^>]+class="date">([0-9.]+)\s*\|', webpage,
                'upload date', default=None)
            info_dict['upload_date'] = unified_strdate(upload_date)

        return info_dict


class DWArticleIE(DWVideoIE):
    IE_NAME = 'dw:article'
    _VALID_URL = r'https?://(?:www\.)?dw\.com/(?:[^/]+/)+a-(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.dw.com/pl/zalecenie-ema-szczepmy-si%C4%99-astrazenec%C4%85/a-56919770',
        'info_dict': {
            'id': '56911196',
            'ext': 'mp4',
            'title': 'Czy AstraZeneca jest bezpieczna?',
            'upload_date': '20210318',
        },
    }

    def _real_extract(self, url):
        article_id = self._match_id(url)
        webpage = self._download_webpage(url, article_id)
        videos = re.finditer(
            r'<div class="mediaItem" data-media-id="(?P<id>\d+)">(?P<hidden_inputs>.+?)<div',
            webpage)
        if not videos:
            raise ExtractorError('No videos found')
        entries = []
        for video in videos:
            video_id, hidden_inputs = video.group('id', 'hidden_inputs')
            hidden_inputs = self._hidden_inputs(hidden_inputs)
            entries.append({
                '_type': 'url_transparent',
                'title': hidden_inputs['media_title'],
                'url': smuggle_url('dw:%s' % video_id, hidden_inputs),
                'ie_key': 'DWVideo',
            })
        return {
            '_type': 'playlist',
            'entries': entries,
            'id': article_id,
            'title': self._html_search_regex(r'<h1>([^>]+)</h1>', webpage, 'article title'),
            'description': self._og_search_description(webpage),
        }
