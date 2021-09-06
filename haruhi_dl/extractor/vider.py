from .common import InfoExtractor


class ViderIE(InfoExtractor):
    _VALID_URL = r'https?://vider\.(?:pl|info)/(?:vid/\+f|embed/video/)(?P<id>[a-z\d]+)'
    _TESTS = [{
        'url': 'https://vider.info/vid/+fsx51se',
        'info_dict': {
            'id': 'sx51se',
            'ext': 'mp4',
            'title': 'Big Buck Bunny',
            'upload_date': '20210906',
            'timestamp': 1630927351,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(f'https://vider.info/vid/+f{video_id}', video_id)

        json_ld = self._parse_json(
            self._search_regex(
                r'(?s)<script type="application/ld\+json">(.+?)</script>',
                webpage, 'JSON-LD'), video_id)
        info_dict = self._json_ld(json_ld, video_id)
        # generated SEO junk
        info_dict['description'] = None
        info_dict['id'] = video_id
        info_dict['formats'] = [{
            'url': self._search_regex(r'\?file=(.+)', json_ld['embedUrl'], 'video url'),
            'http_headers': {
                'Referer': 'https://vider.info/',
            },
        }]

        return info_dict
