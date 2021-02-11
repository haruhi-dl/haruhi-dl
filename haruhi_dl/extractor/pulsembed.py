# coding: utf-8
from __future__ import unicode_literals

import json
import re

from .common import InfoExtractor
from ..compat import (
    compat_str,
)
from ..utils import (
    determine_ext,
    float_or_none,
    int_or_none,
    parse_iso8601,
    smuggle_url,
    try_get,
    unescapeHTML,
    unsmuggle_url,
    ExtractorError,
    NO_DEFAULT,
)
from .libsyn import LibsynIE
from .xnews import XLinkIE
from .tvp import TVPEmbedIE


class PulseVideoIE(InfoExtractor):
    """
    PulseVideo is a name used now by Ringier Axel Springer Tech.
    Onet MVP is a name used previously by Onet's DreamLab,
    before Onet became a part of Ringier Axel Springer Polska.
    """
    _VALID_URL = r'(?:pulsevideo|onetmvp):(?P<id>\d+\.\d+)'
    _TESTS = [{
        'url': 'onetmvp:381027.1509591944',
        'only_matching': True,
    }]

    @staticmethod
    def _search_mvp_id(webpage, default=NO_DEFAULT):
        mvp = re.search(
            r'data-(?:params-)?mvp=["\'](\d+\.\d+)', webpage)
        if mvp:
            return mvp.group(1)
        mvp = re.search(
            r'\sid=(["\']?)mvp:(\d+\.\d+)\1', webpage)
        if mvp:
            return mvp.group(2)
        if default != NO_DEFAULT:
            return default
        raise ExtractorError('Could not extract mvp')

    def _extract_from_id(self, video_id, webpage=None):
        response = self._download_json(
            'http://qi.ckm.onetapi.pl/', video_id,
            query={
                'body[id]': video_id,
                'body[jsonrpc]': '2.0',
                'body[method]': 'get_asset_detail',
                'body[params][ID_Publikacji]': video_id,
                'body[params][Service]': 'www.onet.pl',
                'content-type': 'application/jsonp',
                'x-onet-app': 'player.front.onetapi.pl',
            })

        error = response.get('error')
        if error:
            raise ExtractorError(
                '%s said: %s' % (self.IE_NAME, error['message']), expected=True)

        video = response['result'].get('0')

        formats = []
        for format_type, formats_dict in video['formats'].items():
            if not isinstance(formats_dict, dict):
                continue
            for format_id, format_list in formats_dict.items():
                if not isinstance(format_list, list):
                    continue
                for f in format_list:
                    video_url = f.get('url')
                    if not video_url:
                        continue
                    ext = determine_ext(video_url)
                    if format_id.startswith('ism'):
                        formats.extend(self._extract_ism_formats(
                            video_url, video_id, 'mss', fatal=False))
                    elif ext == 'mpd':
                        formats.extend(self._extract_mpd_formats(
                            video_url, video_id, mpd_id='dash', fatal=False))
                    elif format_id.startswith('hls'):
                        formats.extend(self._extract_m3u8_formats(
                            video_url, video_id, 'mp4', 'm3u8_native',
                            m3u8_id='hls', fatal=False))
                    else:
                        http_f = {
                            'url': video_url,
                            'format_id': format_id,
                            'abr': float_or_none(f.get('audio_bitrate')),
                        }
                        if format_type == 'audio':
                            http_f['vcodec'] = 'none'
                        else:
                            http_f.update({
                                'height': int_or_none(f.get('vertical_resolution')),
                                'width': int_or_none(f.get('horizontal_resolution')),
                                'vbr': float_or_none(f.get('video_bitrate')),
                            })
                        formats.append(http_f)
        self._sort_formats(formats)

        meta = video.get('meta', {})

        title = (self._og_search_title(
            webpage, default=None) if webpage else None) or meta['title']
        description = (self._og_search_description(
            webpage, default=None) if webpage else None) or meta.get('description')
        duration = meta.get('length') or meta.get('lenght')
        timestamp = parse_iso8601(meta.get('addDate'), ' ')
        age_limit = int_or_none(video['license'].get('rating', '')[len('rating_'):])

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'duration': duration,
            'timestamp': timestamp,
            'formats': formats,
            'age_limit': age_limit,
        }

    def _real_extract(self, url):
        return self._extract_from_id(self._match_id(url))

    @staticmethod
    def _extract_urls(webpage, **kw):
        mvp = PulseVideoIE._search_mvp_id(webpage, default=None)
        if mvp:
            return ['onetmvp:%s' % mvp]
        return []


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

        ids = []

        def dedupe(entry):
            if entry['url'] not in ids:
                ids.append(entry['url'])
                return True
            return False

        return list(filter(dedupe, entries))

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
                PulseVideoIE,
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
                if any((s in unknown_iframe for s in (
                    # feel free to extend the list
                    '//forms.freshmail.io/',
                ))):
                    return
                webpage = self._download_webpage(unknown_iframe, video_id, 'Downloading unknown nested iframe')
                referer = unknown_iframe
                new_page = True

        raise ExtractorError('Unknown external media in PulsEmbed')
