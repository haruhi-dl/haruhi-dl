# coding: utf-8
from __future__ import unicode_literals

import json
import re

from .common import InfoExtractor
from ..compat import (
    compat_str,
)
from ..utils import (
    try_get,
    smuggle_url,
    unescapeHTML,
    unsmuggle_url,
    ExtractorError,
)
from .libsyn import LibsynIE
from .xnews import XLinkIE
from .tvp import TVPEmbedIE
from .onet import OnetMVPIE


class PulsEmbedIE(InfoExtractor):
    _VALID_URL = r'(?:(?:https?:)?//pulsembed\.eu/p2em/|pulsembed:)(?P<id>[\da-zA-Z_-]+)'
    _TESTS = [{
        # Libsyn
        'url': 'https://pulsembed.eu/p2em/dxURkuh_-/',
        'info_dict': {
            'id': '12991166',
            'ext': 'mp3',
            'upload_date': '20200203',
            'title': 'Najlepszy tekst tygodnia - Miłość w czasach zarazy',
        },
    }, {
        # x-link in a weird nested iframe
        'url': 'https://pulsembed.eu/p2em/RToX36jpW/',
        'info_dict': {
            'id': '40a496d1-b112-d96a-adff-3207f7cec046',
            'ext': 'mp4',
            'title': 'Nowe życie Kuby Rzeźniczaka i Magdy Stępień. Para wkrótce powita na świecie syna',
        },
    }, {
        # TVP embed
        'url': 'pulsembed:Tqgp477g4',
        'info_dict': {
            'id': '52204505',
            'ext': 'mp4',
            'title': 'Ekspertka z RCB o pogodzie',
            'description': 'md5:48329ce9a42ea46b5f3747f86b0b912b',
        },
    }, {
        # Onet MVP
        'url': '//pulsembed.eu/p2em/0CbWQPleh/',
        'info_dict': {
            'id': '2205732.1142844759',
            'ext': 'mp4',
            'title': 'Podróż służbowa z wypadem na stok? "Załatwiamy wszystko na nartach"',
            'description': 'md5:0e70c7be673157c62ca183791d2b7b27',
            'timestamp': 1607174136,
            'upload_date': '20201205',
        },
    }]

    @staticmethod
    def _get_external_ie_key(ext_url):
        if '//get.x-link.pl/' in ext_url:
            return 'XLink'
        if '//www.tvp.pl/' in ext_url:
            if 'object_id=' in ext_url:
                return 'TVPEmbed'
            return 'TVP'
        if '//html5-player.libsyn.com/' in ext_url:
            return 'Libsyn'
        return None

    @staticmethod
    def _extract_entries(webpage, url=None):
        htmls = [webpage]
        entries = []
        # not sure if this is an Infor-specific (dziennik.pl) thing
        paramss = re.finditer(r'<div\b[^>]+data-params="([^"]+pulsembed[^"]+)"', webpage)
        if paramss:
            for params in paramss:
                params = json.loads(unescapeHTML(params.group(1)))
                ext_url = try_get(params, lambda x: x['parameters']['url'], expected_type=compat_str)
                if ext_url:
                    ext_ie = PulsEmbedIE._get_external_ie_key(ext_url)
                    entries.append({
                        '_type': 'url',
                        'url': ext_url,
                        'ie_key': ext_ie,
                    })
                else:
                    p2em_id = try_get(params, lambda x: x['publicationId']['pulsembed']['id'], expected_type=compat_str)
                    if p2em_id:
                        entries.append({
                            '_type': 'url',
                            'url': smuggle_url('pulsembed:%s' % p2em_id, {'referer': url}),
                            'ie_key': 'PulsEmbed',
                        })
                    else:
                        htmls.append(params['parameters']['embedCode'])
        for html in htmls:
            for embed in re.finditer(r'<div[^>]*\sdata-src="//pulsembed\.eu/p2em/(?P<id>[\da-zA-Z_-]+)', webpage):
                entries.append({
                    '_type': 'url',
                    'url': smuggle_url('pulsembed:%s' % embed.group('id'), {'referer': url}),
                    'ie_key': 'PulsEmbed',
                })
        return entries

    def _real_extract(self, url):
        video_id = self._match_id(url)
        puls_url = 'https://pulsembed.eu/p2em/%s/' % video_id
        smug = unsmuggle_url(url)
        referer = None
        if smug and 'referer' in smug:
            referer = smug['referer']
        webpage = self._download_webpage(puls_url, video_id, headers={
            'Referer': referer or 'https://google.com/',
        })
        info_dict = self._search_json_ld(webpage, video_id, default={})
        info_dict['_type'] = 'url_transparent'

        new_page = True
        referer = puls_url
        while new_page:
            new_page = False
            for embie in (
                LibsynIE,
                XLinkIE,
                TVPEmbedIE,
                OnetMVPIE,
            ):
                embie_urls = embie._extract_urls(webpage, url=referer)
                if embie_urls:
                    if len(embie_urls) > 1:
                        raise ExtractorError('More than one embed inside PulsEmbed (why?)')
                    info_dict.update({
                        'url': embie_urls[0],
                        'ie_key': embie.ie_key(),
                    })
                    return info_dict

            # thanks for nothing, Infor
            unknown_iframe = self._html_search_regex(r'<iframe[^>]*\ssrc=(["\'])(?P<url>[^\1]+)\1',
                                                     webpage, 'unknown iframe', group='url', default=None)
            if unknown_iframe:
                webpage = self._download_webpage(unknown_iframe, video_id, 'Downloading unknown nested iframe')
                referer = unknown_iframe
                new_page = True

        raise ExtractorError('Unknown external media in PulsEmbed')
