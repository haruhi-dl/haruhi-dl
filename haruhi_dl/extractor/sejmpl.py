# coding: utf-8

from .common import InfoExtractor
from ..utils import (
    clean_html,
)

import datetime
import re


class SejmPlArchivalIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?sejm\.gov\.pl/Sejm(?P<term>\d+)\.nsf/transmisje_arch\.xsp(?:\?(?:[^&\s]+(?:&[^&\s]+)*)?)?(?:#|unid=)(?P<id>[\dA-F]+)'
    IE_NAME = 'sejm.pl:archival'

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        term, video_id = mobj.group('term', 'id')
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
        stop_time = iso_date_to_wtf_atende_wants(params['stop'])
        time_query = 'startTime=%d&stopTime=%d' % (start_time, stop_time)

        file = params['file'].replace('http:', 'https:')
        formats = [{
            'url': file + '?' + time_query,
            'ext': 'flv',
            'format_id': 'direct-0',
            'preference': -1,   # VERY slow to download (~200 KiB/s, compared to ~10-15 MiB/s by DASH/HLS)
        }]
        formats.extend(self._extract_mpd_formats(
            file.replace('/nvr/', '/livedash/') + '?indexMode=true&' + time_query,
            video_id, mpd_id='dash'))
        formats.extend(self._extract_m3u8_formats(
            file.replace('/nvr/', '/livehls/') + '/playlist.m3u8?indexMode=true&' + time_query,
            video_id, m3u8_id='hls'))

        self._sort_formats(formats)

        duration = stop_time - start_time

        return {
            'formats': formats,
            'id': video_id,
            'title': data['title'],
            'description': clean_html(data['desc']),
            'duration': duration,
        }
