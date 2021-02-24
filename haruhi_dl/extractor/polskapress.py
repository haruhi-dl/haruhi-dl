# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
)
from .xnews import XLinkIE
from .youtube import YoutubeIE


class PolskaPressIE(InfoExtractor):
    _DOMAINS = (
        # https://polskapress.pl/pl/portfolio
        # [...document.querySelectorAll('.bigTilesEntryWrapper > a')].map(a => a.href).join('\n')
        # cat pp | while read line; do curl -s "$line" | grep '<h2 class="documentSecondHeading">' | sed -E 's/<h2 class="documentSecondHeading">/\"/g;s/,/\", "/g;s/<\/h2>/\", /g;s/\s+//g;s/www\.//g'; done
        "dziennikbaltycki.pl",
        "dzienniklodzki.pl",
        "dziennikpolski24.pl",
        "dziennikzachodni.pl",
        "echodnia.eu",
        "expressbydgoski.pl",
        "expressilustrowany.pl",
        "faktyjasielskie.pl",
        "nowiny24.pl",
        "gazetakrakowska.pl",
        "gazetalubuska.pl",
        "pomorska.pl",
        "gazetawroclawska.pl",
        "wspolczesna.pl",
        "gp24.pl", "gs24.pl", "gk24.pl",
        "gloswielkopolski.pl",
        "gol24.pl",
        "jarmark.com.pl",
        "kurierlubelski.pl",
        "poranny.pl",
        "motosalon.motofakty.pl",
        "motofakty.pl",
        "jarmark.com.pl",
        "naszahistoria.pl",
        "naszemiasto.pl",
        "nto.pl",
        "polskatimes.pl",
        "strefaAGRO.pl",
        "Strefabiznesu.pl",
        "telemagazyn.pl",
        "to.com.pl",
    )
    _VALID_URL = r'(?i)https?://(?:[^/]+\.)?(?:%s)/[^/]+/ar/c\d+-(?P<id>\d+)' % '|'.join(re.escape(dom) for dom in _DOMAINS)

    _TESTS = [{
        # x-news
        'url': 'https://gs24.pl/nie-zyje-aleksander-doba-zmarl-smiercia-podroznika/ar/c1-15457462',
        'info_dict': {
            'id': 'cc18d8c3-ea5d-486e-2d2b-63a0ff60f832',
            'ext': 'mp4',
            'title': 'Nie żyje Aleksander Doba. "Zmarł śmiercią podróżnika"',
            'timestamp': 1614082800,
            'upload_date': '20210223',
        },
    }, {
        # youtube
        'url': 'https://polskatimes.pl/koniec-daft-punk-duet-konczy-kariere-w-sieci-wymowne-nagranie-tak-polski-internet-widzial-ten-francuski-duet-memy/ar/c13-15456928',
        'info_dict': {
            'id': 'DuDX6wNfjqc',
            'ext': 'mp4',
            'title': 'Koniec Daft Punk, duet kończy karierę. W sieci wymowne nagranie! Tak polski internet widział ten francuski due',
            'description': '#DaftPunk #Epilogue',
            'uploader_id': 'daftpunkalive',
            'uploader': 'Daft Punk',
            'upload_date': '20210222',
            'timestamp': 1614073680,
        },
    }, {
        # x-news+youtube combo
        'url': 'https://polskatimes.pl/wybuch-wulkanu-etna-z-krateru-buchnely-chmury-gestego-dymu-poplynely-strumienie-lawy-zdjecia-video/ar/c1-15447115',
        'playlist_count': 2,
        'info_dict': {
            'id': '15447115',
            'title': 'Wybuch wulkanu Etna. Z krateru buchnęły chmury gęstego dymu, popłynęły strumienie lawy [ZDJĘCIA] [VIDEO]',
            'timestamp': 1613553540,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        vids = []
        for embie in (
            XLinkIE,
            YoutubeIE,
        ):
            embie_urls = embie._extract_urls(webpage, url=url)
            if embie_urls:
                vids.append({
                    '_type': 'url_transparent',
                    'url': embie_urls[0],
                    'ie_key': embie.ie_key(),
                })

        info_dict = self._search_json_ld(webpage, video_id)
        info_dict['id'] = video_id

        if not vids:
            raise ExtractorError('No videos found')
        if len(vids) > 1:
            info_dict.update({
                '_type': 'playlist',
                'entries': vids,
            })
            return info_dict

        info_dict.update(vids[0])
        return info_dict
