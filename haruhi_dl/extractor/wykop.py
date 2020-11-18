# coding: utf-8

from __future__ import unicode_literals

from .common import (
    InfoExtractor,
    ExtractorError,
)
from ..utils import (
    clean_html,
    int_or_none,
    str_or_none,
    url_or_none,
)

import re


class WykopIE(InfoExtractor):
    IE_NAME = 'wykop'
    _VALID_URL = r'https?://(?:www\.)?wykop\.pl/(?P<type>link|wpis)/(?P<id>\d+)(?:/comment/\d+|/[^#/\s]+|/#comment-(?P<comment_id>\d+))*'
    _TESTS = [{
        'url': 'https://www.wykop.pl/link/5789155',
        'info_dict': {
            'id': '7b27ly',  # streamable id
            'title': 'Wypadek pijanych(prawdopodobnie) idiotów widziany z wnętrza samochodu.',
            'ext': 'mp4',
            'uploader': 'errorek95',
            'timestamp': 1604847466.56506,
            'upload_date': '20201108',
        },
    }, {
        'url': 'https://www.wykop.pl/link/5787937/#comment-84100287',
        'info_dict': {
            'id': '2uz8kj',
            'title': 'RETROWIRUS - ',
            'ext': 'mp4',
            'timestamp': 1604668080.99827,
            'uploader': 'RETROWIRUS',
            'upload_date': '20201107',
        },
    }, {
        'url': 'https://www.wykop.pl/wpis/53405999',
        'info_dict': {
            'id': 'yeujjq',  # streamable
            'title': 'Potat - Chłop przerabia krzyż #heheszki #niewiemjaktootagowac',
            'ext': 'mp4',
            'uploader': 'Potat',
            'upload_date': '20201108',
            'timestamp': 1604825368.86073,
        }
    }, {
        'url': 'https://www.wykop.pl/wpis/53415243/m00d-neuropa-bekazprawakow/#comment-189438995',
        'info_dict': {
            'id': 'jtxd8d',
            'title': 'Nox_ - ( ͡° ͜ʖ ͡°)',
            'ext': 'mp4',
            'upload_date': '20201108',
            'uploader': 'Nox_',
            'timestamp': 1603830140.88605,
        }
    }, {
        'url': 'https://wykop.pl/wpis/53404647/pokaz-spoiler/',
        'only_matching': True,
    }, {
        'url': 'http://www.wykop.pl/wpis/53415243/#comment-189438995',
        'only_matching': True,
    }, {
        'url': 'https://www.wykop.pl/link/5789155/wypadek-pijanych-prawdopodobnie-idiotow-widziany-z-wnetrza-samochodu/',
        'only_matching': True,
    }, {
        'url': 'https://www.wykop.pl/link/5785947/comment/84053103/#comment-84053103',
        'only_matching': True,
    }]

    def _real_extract(self, source_url):
        mobj = re.match(self._VALID_URL, source_url)
        id, comment_id = mobj.group('id', 'comment_id')
        method_1 = 'links' if mobj.group('type') == 'link' else 'entries'
        method_2 = 'comment' if comment_id \
            else 'link' if method_1 == 'links' \
            else 'entry'

        meta = self._download_json(
            'https://a2.wykop.pl/%s/%s/%s/appkey/aNd401dAPp' % (method_1, method_2, comment_id if comment_id else id),
            comment_id or id)

        if meta.get('error'):
            error = meta['error']
            raise ExtractorError('Wykop.pl said: "%s" (%d)' % (error['message_en'], error['code']))

        data = meta['data']

        uploader = uploader_url = alt_title = upload_date = None
        # author can be null, just wypiek api things - https://www.wykop.pl/wpis/36527259/
        if 'author' in data:
            author = data['author']
            uploader = author['login']
            uploader_url = 'https://www.wykop.pl/ludzie/%s' % uploader if '.' not in uploader else None

        if method_1 == 'entries' or method_2 == 'comment':
            # links/link, entries/entry, entries/comment
            if 'embed' not in data:
                raise ExtractorError('No embed found in the %s' % method_2)
            embed = data['embed']
            if not embed['type'] == 'video':
                raise ExtractorError('No video found in the %s' % method_2)
            url = embed['url']

            title = '%s - %s' % (uploader, clean_html(data.get('body') or ''))
        else:
            # links/comment
            url = data['source_url']
            title = clean_html(data['title'])
            alt_title = clean_html(data['description'])

        embed_or_data = data.get('embed') or data
        age_limit = 18 if embed_or_data.get('plus18') else 0
        thumbnail = url_or_none(embed_or_data.get('preview'))
        like_count = int_or_none(data.get('vote_count'))
        dislike_count = int_or_none(data.get('bury_count'))
        comment_count = int_or_none(data.get('comments_count'))
        date = str_or_none(data.get('date'))
        if date:
            upload_date = date[:4] + date[5:7] + date[8:10]

        return {
            '_type': 'url_transparent',
            'url': url,
            'title': title,
            'alt_title': alt_title or None,
            'uploader': uploader,
            'uploader_url': uploader_url,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'age_limit': age_limit,
            'like_count': like_count,
            'dislike_count': dislike_count,
            'comment_count': comment_count,
        }
