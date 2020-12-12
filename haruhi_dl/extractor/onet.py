# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    ExtractorError,
    float_or_none,
    int_or_none,
    NO_DEFAULT,
    parse_iso8601,
)


class OnetBaseIE(InfoExtractor):
    def _search_mvp_id(self, webpage):
        return self._search_regex(
            r'id=(["\'])mvp:(?P<id>.+?)\1', webpage, 'mvp id', group='id')

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

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'duration': duration,
            'timestamp': timestamp,
            'formats': formats,
        }


class OnetMVPIE(OnetBaseIE):
    _VALID_URL = r'onetmvp:(?P<id>\d+\.\d+)'

    _TEST = {
        'url': 'onetmvp:381027.1509591944',
        'only_matching': True,
    }

    def _real_extract(self, url):
        return self._extract_from_id(self._match_id(url))


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
            'timestamp': 1607177736,
            'upload_date': '20201205',
        }
    }, {
        # audio podcast form from libsyn.com via pulsembed.eu (2 iframes fucking nested in each other, who the fuck did this?)
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
            'timestamp': 1607111725,
            'upload_date': '20201204',
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

    def _search_mvp_id(self, webpage, default=NO_DEFAULT):
        return self._search_regex(
            r'data-(?:params-)?mvp=["\'](\d+\.\d+)', webpage, 'mvp id',
            default=default)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        url = url.replace('.amp', '')
        webpage = self._download_webpage(url, video_id)

        mvp_id = self._search_mvp_id(webpage, default=None)

        if not mvp_id:
            pulsembed_url = self._search_regex(
                r'data-src=(["\'])(?P<url>(?:https?:)?//pulsembed\.eu/.+?)\1',
                webpage, 'pulsembed url', group='url')
            webpage = self._download_webpage(
                pulsembed_url, video_id, 'Downloading pulsembed webpage')
            mvp_id = self._search_mvp_id(webpage, default=None)
            if not mvp_id:
                libsyn_url = self._search_regex(r'src=(["\'])(?P<url>(?:https?:)?//html5-player\.libsyn\.com/.+?)\1',
                                                webpage, 'libsyn url', group='url')
                if libsyn_url:
                    return self.url_result(libsyn_url, 'Libsyn')

        return self.url_result(
            'onetmvp:%s' % mvp_id, OnetMVPIE.ie_key(), video_id=mvp_id)
