from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import unified_strdate


class ATTTechChannelIE(InfoExtractor):
    _VALID_URL = r'https?://techchannel\.att\.com/play-video\.cfm/([^/]+/)*(?P<id>.+)'
    _TESTS = [{
        'url': 'http://techchannel.att.com/play-video.cfm/2014/1/27/ATT-Archives-The-UNIX-System-Making-Computers-Easier-to-Use',
        'info_dict': {
            'id': '11316',
            'display_id': 'ATT-Archives-The-UNIX-System-Making-Computers-Easier-to-Use',
            'ext': 'm3u8',
            'title': 'AT&T Archives: The UNIX System: Making Computers Easier to Use',
            'description': 'A 1982 film about UNIX is the foundation for software in use around Bell Labs and AT&T.',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20140127',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        video_url = self._search_regex(
            r'(?m)^\s*"src=\'(https?://.+?\.m3u8)\'',
            webpage, 'video URL')

        video_id = self._search_regex(
            r'mediaid\s*=\s*(\d+)',
            webpage, 'video id', fatal=False)

        formats = self._extract_m3u8_formats(video_url, video_id)

        title = self._html_search_regex(r'<title>(.+?)</title>', webpage, 'title')
        description = self._html_search_meta('description', webpage, 'description')
        thumbnail = self._search_regex(r'poster=\'(https?://.+?)\'',
                                       webpage, 'thumbnail', fatal=False)
        upload_date = unified_strdate(self._search_regex(
            r'[Rr]elease\s+date:\s*(\d{1,2}/\d{1,2}/\d{4})',
            webpage, 'upload date', fatal=False), False)

        return {
            'id': video_id,
            'display_id': display_id,
            'formats': formats,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
        }
