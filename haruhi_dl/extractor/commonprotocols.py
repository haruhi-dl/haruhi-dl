from __future__ import unicode_literals

from urllib.parse import parse_qs

from .common import InfoExtractor
from ..compat import (
    compat_urlparse,
)
from ..utils import (
    try_get,
    ExtractorError,
)


class RtmpIE(InfoExtractor):
    IE_DESC = False  # Do not list
    _VALID_URL = r'(?i)rtmp[est]?://.+'

    _TESTS = [{
        'url': 'rtmp://cp44293.edgefcs.net/ondemand?auth=daEcTdydfdqcsb8cZcDbAaCbhamacbbawaS-bw7dBb-bWG-GqpGFqCpNCnGoyL&aifp=v001&slist=public/unsecure/audio/2c97899446428e4301471a8cb72b4b97--audio--pmg-20110908-0900a_flv_aac_med_int.mp4',
        'only_matching': True,
    }, {
        'url': 'rtmp://edge.live.hitbox.tv/live/dimak',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._generic_id(url)
        title = self._generic_title(url)
        return {
            'id': video_id,
            'title': title,
            'formats': [{
                'url': url,
                'ext': 'flv',
                'format_id': compat_urlparse.urlparse(url).scheme,
            }],
        }


class MmsIE(InfoExtractor):
    IE_DESC = False  # Do not list
    _VALID_URL = r'(?i)mms://.+'

    _TEST = {
        # Direct MMS link
        'url': 'mms://kentro.kaist.ac.kr/200907/MilesReid(0709).wmv',
        'info_dict': {
            'id': 'MilesReid(0709)',
            'ext': 'wmv',
            'title': 'MilesReid(0709)',
        },
        'params': {
            'skip_download': True,  # rtsp downloads, requiring mplayer or mpv
        },
    }

    def _real_extract(self, url):
        video_id = self._generic_id(url)
        title = self._generic_title(url)

        return {
            'id': video_id,
            'title': title,
            'url': url,
        }


class BitTorrentMagnetIE(InfoExtractor):
    IE_DESC = False
    _VALID_URL = r'(?i)magnet:\?.+'

    _TESTS = [{
        'url': 'magnet:?xs=https%3A%2F%2Fvideo.internet-czas-dzialac.pl%2Fstatic%2Ftorrents%2F9085aa69-90c2-40c6-a707-3472b92cafc8-0.torrent&xt=urn:btih:0ae4cc8cb0e098a1a40b3224aa578bb4210a8cff&dn=Podcast+Internet.+Czas+dzia%C5%82a%C4%87!+-+Trailer&tr=wss%3A%2F%2Fvideo.internet-czas-dzialac.pl%3A443%2Ftracker%2Fsocket&tr=https%3A%2F%2Fvideo.internet-czas-dzialac.pl%2Ftracker%2Fannounce&ws=https%3A%2F%2Fvideo.internet-czas-dzialac.pl%2Fstatic%2Fwebseed%2F9085aa69-90c2-40c6-a707-3472b92cafc8-0.mp4',
        'info_dict': {
            'id': 'urn:btih:0ae4cc8cb0e098a1a40b3224aa578bb4210a8cff',
            'ext': 'torrent',
            'title': 'Podcast Internet. Czas działać! - Trailer',
        },
        'params': {
            'allow_p2p': True,
            'prefer_p2p': True,
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        qs = parse_qs(url[len('magnet:?'):])

        # eXact Topic
        video_id = qs['xt'][0]
        if not video_id.startswith('urn:btih:'):
            raise ExtractorError('Not a BitTorrent magnet')
        # Display Name
        title = try_get(qs, lambda x: x['dn'][0], str) or video_id[len('urn:btih:'):]

        formats = [{
            'url': url,
            'protocol': 'bittorrent',
        }]
        # Web Seed
        if qs.get('ws'):
            for ws in qs['ws']:
                formats.append({
                    'url': ws,
                })
        # Acceptable Source
        if qs.get('as'):
            for as_ in qs['as']:
                formats.append({
                    'url': as_,
                    'preference': -2,
                })
        # eXact Source
        if qs.get('xs'):
            for xs in qs['xs']:
                formats.append({
                    'url': xs,
                    'protocol': 'bittorrent',
                })

        self._sort_formats(formats)

        # eXact Length
        if qs.get('xl'):
            xl = int(qs['xl'][0])
            for i in range(0, len(formats)):
                formats[i]['filesize'] = xl

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
        }
