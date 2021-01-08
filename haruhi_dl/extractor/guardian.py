# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    int_or_none,
    parse_duration,
    url_or_none,
)


class GuardianVideoIE(InfoExtractor):
    IE_NAME = 'guardian:video'
    _VALID_URL = r'https?://(?:www\.)?theguardian\.com/[^/]+/video/\d{4}/[a-z]{3}/\d{2}/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.theguardian.com/global/video/2020/dec/29/covid-from-space-the-humans-furthest-from-the-pandemic-video',
        'info_dict': {
            'id': 'nmehcVJm3Y0',
            'ext': 'mp4',
            'title': 'Covid from space: the humans furthest from the pandemic – video',
            'description': 'md5:6b6ea15d4efc75b887c3e9e8fb3cd803',
            'upload_date': '20201229',
            'uploader_id': 'TheGuardian',
            'uploader': 'The Guardian',
        },
    }]

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(url, page_id)

        release_date = self._html_search_meta('datePublished', webpage)
        if release_date:
            release_date = release_date[:4] + release_date[5:7] + release_date[8:10]
        return {
            '_type': 'url_transparent',
            'url': 'https://www.youtube.com/watch?v=%s' % (self._search_regex(
                r'<div id="youtube-[^"]*" data-asset-id="([^"]{11})"', webpage, 'youtube video id')),
            'title': self._html_search_meta('name', webpage, fatal=True),
            'description': self._html_search_meta('description', webpage),
            'thumbnail': url_or_none(self._html_search_meta('thumbnail', webpage)),
            'duration': parse_duration(self._html_search_meta('duration', webpage)),
            'release_date': release_date,
        }


class GuardianAudioIE(InfoExtractor):
    IE_NAME = 'guardian:audio'
    _VALID_URL = r'https?://(?:www\.)?theguardian\.com/[^/]+/audio/\d{4}/[a-z]{3}/\d{2}/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.theguardian.com/news/audio/2021/jan/08/the-storming-of-the-capitol-and-the-end-of-the-trump-era',
        'info_dict': {
            'id': 'the-storming-of-the-capitol-and-the-end-of-the-trump-era',
            'ext': 'mp3',
            'title': 'The storming of the Capitol and the end of the Trump era',
            'description': 'When rioters stormed into the Capitol building in Washington DC this week, it marked a new low for the Trump presidency. David Smith and Lauren Gambino describe a week in US politics like no other',
        },
    }]

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(url, page_id)

        figure = self._search_regex(r'(<figure [^>]*id="audio-component-container"[^>]*>)',
                                    webpage, 'figure element')
        figure_attrs = extract_attributes(figure)
        return {
            'id': page_id,
            'url': figure_attrs['data-source'],
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'duration': int_or_none(figure_attrs.get('data-duration')),
            'thumbnail': self._og_search_thumbnail(webpage),
        }
