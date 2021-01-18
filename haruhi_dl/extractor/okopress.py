# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from .youtube import YoutubeIE
from .facebook import FacebookIE


class OKOPressIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?oko\.press/(?P<id>[^/?#]+)'
    IE_NAME = 'oko.press'
    _TESTS = [{
        # podcast (requires logging in, but the mp3 is linked in JSON-LD)
        'url': 'https://oko.press/wozem-strazackim-na-szczepienie-powiekszenie',
        'info_dict': {
            'id': 'wozem-strazackim-na-szczepienie-powiekszenie',
            'ext': 'mp3',
            'title': 'Wozem strażackim na szczepienie [POWIĘKSZENIE]',
        },
    }, {
        # youtube embed
        'url': 'https://oko.press/jenczyna-bylismy-za-kulisami-najnowszego-spektaklu-strzepki-i-demirskiego/',
        'info_dict': {
            'id': 'jenczyna-bylismy-za-kulisami-najnowszego-spektaklu-strzepki-i-demirskiego',
            'timestamp': 1610808205,
            'title': '„Jeńczyna”: byliśmy za kulisami najnowszego spektaklu Strzępki i Demirskiego',
        },
        'playlist_count': 1,
    }, {
        'url': 'https://oko.press/rozmowa-z-ofiara-lapanki-po-strajku-kobiet/',
        'info_dict': {
            'id': 'rozmowa-z-ofiara-lapanki-po-strajku-kobiet',
            'title': '„Teraz boję się policji bardziej niż nacjonalistów”. Rozmowa z ofiarą łapanki po Strajku Kobiet',
            'timestamp': 1609183523,
        },
        'playlist_count': 1,
    }]

    def _real_extract(self, url):
        page_slug = self._match_id(url)

        webpage = self._download_webpage(url, page_slug)

        # podcast
        if '"@type": "PodcastEpisode",' in webpage:
            self.to_screen('podcast')
            info_dict = self._search_json_ld(webpage, page_slug, 'PodcastEpisode')
            info_dict.update({
                'id': page_slug,
                'title': self._og_search_title(webpage),
            })
            return info_dict

        info_dict = self._search_json_ld(webpage, page_slug, 'NewsArticle')

        entries = []
        for embie in (YoutubeIE, FacebookIE):
            for embed_url in embie._extract_urls(webpage):
                entries.append({
                    '_type': 'url',
                    'url': embed_url,
                    'ie_key': embie.ie_key(),
                })

        info_dict.update({
            '_type': 'playlist',
            'id': page_slug,
            'entries': entries,
        })
        return info_dict
