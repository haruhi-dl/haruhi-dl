# coding: utf-8
from __future__ import unicode_literals

import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    compat_str,
    parse_iso8601,
)


class LurkerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?lurker\.(?:pl|land)/post/(?P<id>[A-Za-z\d]{9})'
    _TESTS = [{
        # no title (microblog/comment)
        'url': 'https://www.lurker.pl/post/HMPQwlZrm',
        'info_dict': {
            'id': 'HMPQwlZrm',
            'title': 'md5:0cb2f2e431ad7c604017a3dcdc1c3dcd',
            'timestamp': 1610548036,
            'uploader': 'paladyn',
            'uploader_id': 'paladyn',
            'age_limit': 18,
        },
        'playlist_count': 1,
    }, {
        # with title
        'url': 'https://www.lurker.pl/post/Aqump8Lbm',
        'info_dict': {
            'id': 'Aqump8Lbm',
            'title': 'Trzech mężczyzn trzymało się za ręce, tworząc ludzki łańcuch,, aby dotrzeć do bezpańskiego psa uwięzionego w zamarzniętym jeziorze.',
            'timestamp': 1610805850,
            'description': 'https://www.liveleak.com/view?t=al95a_1610628122\n#ludzie #pomocy #ratunek #zwierzeta #psy #pies',
            'uploader': 'R20_swap',
            'uploader_id': 'r20_swap',
            'age_limit': 0,
        },
        'playlist_count': 1,
    }]

    def _real_extract(self, url):
        post_id = self._match_id(url)

        meta = self._download_json('https://lurker.land/api/v3?action=POST_GET', post_id,
                                   data=bytes(compat_str(json.dumps({
                                       'id': post_id,
                                       'subsort': 'best',
                                   })).encode('utf-8')),
                                   headers={
                                       'Accept': 'application/json',
                                       'Content-Type': 'application/json',
                                       'Origin': 'https://www.lurker.land',
                                       'Referer': 'https://www.lurker.land/post/%s' % post_id,
                                   })

        post = None
        for post_i in meta['posts']:
            if post_i.get('id') == post_id:
                post = post_i
                break
        if not post:
            raise ExtractorError('Post not found')

        entries = []
        for link in post['links']:
            entries.append({
                '_type': 'url',
                'url': link['url'],
            })

        # ids are username-like but lowercased, possibly because of nickname changes - https://www.wykop.pl/link/5895209/
        uploader = post.get('userId')
        for user_i in meta['users']:
            if user_i.get('id') == uploader:
                uploader = user_i['username']
                break

        return {
            '_type': 'playlist',
            'entries': entries,
            'id': post_id,
            'title': post['title'] if post['hasTitle'] else clean_html(post.get('body')),
            'description': clean_html(post.get('body')) if post['hasTitle'] else None,
            'uploader': uploader,
            'uploader_id': post.get('userId'),
            'uploader_url': 'https://lurker.land/user/%s' % uploader,
            'timestamp': parse_iso8601(post.get('createdAt')),
            'like_count': post.get('upvotes'),
            'dislike_count': post.get('downvotes'),
            'average_rating': post.get('value'),
            'age_limit': 18 if 'nsfw' in (post.get('tags') or ()) else 0,
        }
