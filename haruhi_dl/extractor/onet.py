# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
)
from .pulsembed import (
    PulsEmbedIE,
    PulseVideoIE,
)


class OnetPlIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^/]+\.)?(?:onet|businessinsider\.com|plejada)\.pl/(?:[^/]+/)+(?P<id>[0-9a-z]+)'
    IE_NAME = 'onet.pl'

    _TESTS = [{
        'url': 'https://wiadomosci.onet.pl/tylko-w-onecie/stoki-narciarskie-w-czasie-pandemii-koronawirusa-sprawdzilismy-jak-funkcjonuja/nyzt08c',
        'info_dict': {
            'id': '2205732.1142844759',
            'ext': 'mp4',
            'description': 'md5:0e70c7be673157c62ca183791d2b7b27',
            'title': 'Podróż służbowa z wypadem na stok? "Załatwiamy wszystko na nartach"',
            'timestamp': 1607174136,
            'upload_date': '20201205',
        }
    }, {
        # audio podcast form from libsyn.com via pulsembed
        'url': 'https://wiadomosci.onet.pl/tylko-w-onecie/milosc-w-czasach-zarazy/nbqxxwm',
        'info_dict': {
            'id': '12991166',
            'ext': 'mp3',
            'title': 'Najlepszy tekst tygodnia - Miłość w czasach zarazy',
            'upload_date': '20200203',
        },
    }, {
        # AMP thing
        'url': 'https://wiadomosci.onet.pl/kraj/koronawirus-michal-rogalski-polska-stala-sie-szara-wyspa-dostepu-do-danych/5plrwcc.amp?utm_campaign=leo_automatic',
        'info_dict': {
            'id': '2205367.1517834067',
            'ext': 'mp4',
            'title': 'Narodowy program szczepień na koronawirusa. Poznaliśmy szczegóły',
            'description': 'md5:44f34f9718714e208797f62d851b58ec',
            'timestamp': 1607108125,
            'upload_date': '20201204',
        },
    }, {
        # age limit
        'url': 'https://www.onet.pl/informacje/onetwiadomosci/krwawy-biznes-futerkowcow-film-janusza-schwertnera/82wy9vs,79cfc278',
        'info_dict': {
            'id': '2188984.870201019',
            'ext': 'mp4',
            'title': 'Szokujące nagrania. Tak się produkuje futra w Polsce. Film "Krwawy biznes futerkowców" Janusza Schwertnera',
            'description': 'Film "Krwawy biznes futerkowców" Janusza Schwertnera',
            'timestamp': 1599558803,
            'upload_date': '20200908',
            'age_limit': 18,
        },
    }, {
        'url': 'http://film.onet.pl/zwiastuny/ghost-in-the-shell-drugi-zwiastun-pl/5q6yl3',
        'only_matching': True,
    }, {
        'url': 'http://moto.onet.pl/jak-wybierane-sa-miejsca-na-fotoradary/6rs04e',
        'only_matching': True,
    }, {
        'url': 'http://businessinsider.com.pl/wideo/scenariusz-na-koniec-swiata-wedlug-nasa/dwnqptk',
        'only_matching': True,
    }, {
        'url': 'http://plejada.pl/weronika-rosati-o-swoim-domniemanym-slubie/n2bq89',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        url = url.replace('.amp', '')
        webpage = self._download_webpage(url, video_id)

        info_dict = self._search_json_ld(webpage, video_id, expected_type='NewsArticle')
        info_dict['id'] = video_id

        mvp_id = PulseVideoIE._search_mvp_id(webpage, default=None)
        if mvp_id:
            info_dict.update({
                'url': 'pulsevideo:%s' % mvp_id,
                'ie_key': PulseVideoIE.ie_key(),
            })

        p2ems = PulsEmbedIE._extract_entries(webpage)
        if len(p2ems) > 1:
            info_dict.update({
                '_type': 'playlist',
                'entries': p2ems,
            })
        if p2ems:
            info_dict.update(p2ems[0])
            return info_dict

        raise ExtractorError('PulsEmbed not found')
