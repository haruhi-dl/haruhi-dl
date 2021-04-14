# coding: utf-8

from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    js_to_json,
    try_get,
)

import datetime
import re
from urllib.parse import parse_qs


class SejmPlIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?sejm\.gov\.pl/Sejm(?P<term>\d+)\.nsf/transmisje(?:_arch)?\.xsp(?:\?(?:[^&\s]+(?:&[^&\s]+)*)?)?(?:#|unid=)(?P<id>[\dA-F]+)'
    IE_NAME = 'sejm.gov.pl'

    _TESTS = [{
        # multiple cameras, PJM translator
        'url': 'https://www.sejm.gov.pl/Sejm9.nsf/transmisje_arch.xsp#9587D63364A355A1C1258562004DCF21',
        'info_dict': {
            'id': '9587D63364A355A1C1258562004DCF21',
            'title': '11. posiedzenie Sejmu IX kadencji',
        },
        'playlist_count': 10,
    }, {
        # live stream
        'url': 'https://www.sejm.gov.pl/Sejm9.nsf/transmisje.xsp?unid=DF7D229E316BBC5AC12586A8003E90AC#',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        term, video_id = mobj.group('term', 'id')
        frame = self._download_webpage(
            'https://sejm-embed.redcdn.pl/Sejm%s.nsf/VideoFrame.xsp/%s' % (term, video_id),
            video_id, headers={
                'Referer': 'https://www.sejm.gov.pl/Sejm%s.nsf/transmisje_arch.xsp' % (term),
            })
        # despite it says "transmisje_arch", it works for live streams too!
        data = self._download_json(
            'https://www.sejm.gov.pl/Sejm%s.nsf/transmisje_arch.xsp/json/%s' % (term, video_id),
            video_id, headers={
                'Referer': 'https://www.sejm.gov.pl/Sejm%s.nsf/transmisje_arch.xsp' % (term),
            })
        params = data['params']

        def iso_date_to_wtf_atende_wants(date):
            date = datetime.datetime.fromisoformat(date)
            # atende uses timestamp but since 2001 instead of 1970
            date = date.replace(year=date.year - 31)
            # also it's in milliseconds
            return int(date.timestamp() * 1000)

        start_time = iso_date_to_wtf_atende_wants(params['start'])
        if 'transmisje_arch.xsp' in url:
            stop_time = iso_date_to_wtf_atende_wants(params['stop'])
        else:
            stop_time = None

        duration = (stop_time - start_time) if stop_time else None

        entries = []

        def add_entry(file):
            if not file:
                return
            file = 'https:%s?startTime=%d' % (file, start_time)
            # live streams don't use stopTime
            if stop_time:
                file += '&stopTime=%d' % stop_time
            stream_id = self._search_regex(r'/o2/sejm/([^/]+)/[^./]+\.livx', file, 'stream id')
            entries.append({
                '_type': 'url_transparent',
                'url': file,
                'ie_key': 'SejmPlVideo',
                'id': stream_id,
                'title': stream_id,
                'duration': duration,
            })

        cameras = self._parse_json(
            self._search_regex(r'(?s)var cameras = (\[.+?\]);', frame, 'camera list'),
            video_id, js_to_json)
        for camera in cameras:
            add_entry(camera['file']['flv'])

        if params.get('mig'):
            add_entry(self._search_regex(r"var sliUrl = '(.+?)';", frame, 'migacz url', fatal=False))

        return {
            '_type': 'multi_video',
            'entries': entries,
            'id': video_id,
            'title': data['title'],
            'description': clean_html(data['desc']),
            'duration': duration,
            'is_live': 'transmisje.xsp' in url,
        }


# actually, this is common between Sejm and Senat, the 2 houses of PL parliament
class SejmPlVideoIE(InfoExtractor):
    _VALID_URL = r'https?://[^.]+\.dcs\.redcdn\.pl/[^/]+/o2/(?P<house>sejm|senat)/(?P<id>[^/]+)/(?P<filename>[^./]+)\.livx\?(?P<qs>.+)'
    IE_NAME = 'parlament-pl:video'

    _TESTS = [{
        'url': 'https://r.dcs.redcdn.pl/livedash/o2/senat/ENC02/channel.livx?indexMode=true&startTime=638272860000&stopTime=638292544000',
        'info_dict': {
            'id': 'ENC02-638272860000-638292544000',
            'ext': 'mp4',
            'title': 'ENC02',
        },
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        house, camera, filename, qs = mobj.group('house', 'id', 'filename', 'qs')
        qs = parse_qs(qs)
        start_time = int(qs["startTime"][0])
        stop_time = int_or_none(try_get(qs, lambda x: x["stopTime"][0]))

        file = f'https://r.dcs.redcdn.pl/%s/o2/{house}/{camera}/{filename}.livx?startTime={start_time}'
        if stop_time:
            file += f'&stopTime={stop_time}'
        file_index = file + '&indexMode=true'

        # sejm videos don't have an id, just a camera (pov) id and time range
        video_id = '%s-%d-%d' % (camera, start_time, stop_time)

        formats = [{
            'url': file % 'nvr',
            'ext': 'flv',
            'format_id': 'direct-0',
            'preference': -1,   # VERY slow to download (~200 KiB/s, compared to ~10-15 MiB/s by DASH/HLS)
        }]
        formats.extend(self._extract_mpd_formats(file_index % 'livedash', video_id, mpd_id='dash'))
        formats.extend(self._extract_m3u8_formats(
            file_index.replace('?', '/playlist.m3u8?') % 'livehls', video_id, m3u8_id='hls', ext='mp4'))
        formats.extend(self._extract_ism_formats(
            file_index.replace('?', '/manifest?') % 'livess', video_id, ism_id='ss'))

        self._sort_formats(formats)

        duration = (stop_time - start_time) // 1000

        return {
            'id': video_id,
            'title': camera,
            'formats': formats,
            'duration': duration,
            # if there's no stop, it's live
            'is_live': stop_time is None,
        }
