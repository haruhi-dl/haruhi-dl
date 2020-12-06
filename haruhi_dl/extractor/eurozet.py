# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class EurozetArticleIE(InfoExtractor):
    IE_NAME = 'eurozet:article'
    _VALID_URL = r'https?://(?:[a-z]+\.)*(?<!player\.)(?:radiozet|chillizet|antyradio|planeta|meloradio)\.pl/[^/\s]+/(?P<id>[^/\s]+)'

    _DATA_RE = r'data-%s="(?P<content>.+?)"'

    _TESTS = [{
        'url': 'https://wiadomosci.radiozet.pl/Gosc-Radia-ZET/Margot-Trzeba-uzywac-mocnych-srodkow-zeby-byc-irytujacym-dla-wladzy',
        'info_dict': {
            'id': '131014',
            'ext': 'm3u8',
            'upload_date': '20200902',
            'title': 'Margot: Trzeba używać mocnych środków, żeby być irytującym dla władzy',
            'timestamp': 1599021420,
            'description': 'md5:d01ba0a7f10c84ed0c7921720411a886',
        },
    }]

    def _real_extract(self, url):
        page_slug = self._match_id(url)
        webpage = self._download_webpage(url, page_slug)

        video_id = self._html_search_regex(self._DATA_RE % 'storage-id', webpage, 'video id', group='content')
        info_dict = self._search_json_ld(webpage, video_id)

        formats = []
        for streaming_std in ('ss', 'dash', 'hls'):
            stream_url = self._html_search_regex(self._DATA_RE % ('source-%s' % streaming_std), webpage,
                                                 '%s manifest url' % streaming_std, group='content', fatal=False)
            if stream_url:
                if streaming_std == 'ss':
                    formats.extend(self._extract_ism_formats(stream_url, video_id))
                elif streaming_std == 'dash':
                    formats.extend(self._extract_mpd_formats(stream_url, video_id))
                elif streaming_std == 'hls':
                    formats.extend(self._extract_m3u8_formats(stream_url, video_id))

        self._sort_formats(formats)

        info_dict.update({
            'id': video_id,
            'formats': formats,
        })

        return info_dict
