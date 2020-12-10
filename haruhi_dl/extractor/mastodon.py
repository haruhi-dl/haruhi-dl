# coding: utf-8
from __future__ import unicode_literals

from .common import SelfhostedInfoExtractor

from ..utils import (
    clean_html,
    str_or_none,
    ExtractorError,
)

import re


class MastodonSHIE(SelfhostedInfoExtractor):
    """
    This extractor is for services implementing the Mastodon API, not just Mastodon
    Supported services (possibly more already work or could):
    - Mastodon - https://github.com/tootsuite/mastodon
    - Glitch (a fork of Mastodon) - https://github.com/glitch-soc/mastodon
    - Pleroma - https://git.pleroma.social/pleroma/pleroma
    - Gab Social (a fork of Mastodon) - https://code.gab.com/gab/social/gab-social/
    """
    IE_NAME = 'mastodon'
    _VALID_URL = r'mastodon:(?P<host>[^:]+):(?P<id>.+)'
    _SH_VALID_URL = r'''(?x)
        https?://
            (?P<host>[^/\s]+)/
                (?:
                    # mastodon
                    @[a-zA-Z0-9_]+
                    # gab social
                    |[a-zA-Z0-9_]+/posts
                    # mastodon legacy (?)
                    |users/[a-zA-Z0-9_]+/statuses
                    # pleroma
                    |notice
                    # pleroma (OStatus standard?) - https://git.pleroma.social/pleroma/pleroma/-/blob/e9859b68fcb9c38b2ec27a45ffe0921e8d78b5e1/lib/pleroma/web/router.ex#L607
                    |objects
                    |activities
                )/(?P<id>[0-9a-zA-Z-]+)
    '''
    _SH_VALID_CONTENT_STRINGS = (
        ',"settings":{"known_fediverse":',  # Mastodon initial-state
        '<li><a href="https://docs.joinmastodon.org/">Documentation</a></li>',
        '<title>Pleroma</title>',
        '<noscript>To use Pleroma, please enable JavaScript.</noscript>',
        'Alternatively, try one of the <a href="https://apps.gab.com">native apps</a> for Gab Social for your platform.',
    )
    _SH_VALID_CONTENT_REGEXES = (
        # double quotes on Mastodon, single quotes on Gab Social
        r'<script id=[\'"]initial-state[\'"] type=[\'"]application/json[\'"]>{"meta":{"streaming_api_base_url":"wss://',
    )

    _TESTS = [{
        # mastodon, video description
        'url': 'https://mastodon.technology/@BadAtNames/104254332187004304',
        'info_dict': {
            'id': '104254332187004304',
            'title': 're:.+ - Mfw trump supporters complain about twitter',
            'ext': 'mp4',
        },
    }, {
        # pleroma, /objects/ redirect, empty content
        'url': 'https://fedi.valkyrie.world/objects/386d2d68-090f-492e-81bd-8d32a3a65627',
        'info_dict': {
            'id': '9xLMO1BcEEbaM54LBI',
            'title': 're:.+ - ',
            'ext': 'mp4',
        },
    }, {
        # pleroma, multiple videos in single post
        'url': 'https://donotsta.re/notice/9xN1v6yM7WhzE7aIIC',
        'info_dict': {
            'id': '9xN1v6yM7WhzE7aIIC',
            'title': 're:.+ - ',
        },
        'playlist': [{
            'info_dict': {
                'id': '1264363435',
                'title': 'Cherry Gold💭 - French is one interesting language but this is so funny 🤣🤣🤣🤣-1258667021920845824.mp4',
                'ext': 'mp4',
            },
        }, {
            'info_dict': {
                'id': '825092418',
                'title': 'Santi 🇨🇴 - @mhizgoldbedding same guy but i liked this one better-1259242534557167617.mp4',
                'ext': 'mp4',
            },
        }]
    }, {
        # gab social
        'url': 'https://gab.com/ACT1TV/posts/104450493441154721',
        'info_dict': {
            'id': '104450493441154721',
            'title': 're:.+ - He shoots, he scores and the crowd went wild.... #Animal #Sports',
            'ext': 'mp4',
        },
    }]

    def _selfhosted_extract(self, url, webpage=None):
        mobj = re.match(self._VALID_URL, url)
        if not mobj:
            mobj = re.match(self._SH_VALID_URL, url)
        host, id = mobj.group('host', 'id')

        if any(frag in url for frag in ('/objects/', '/activities/')):
            if not webpage:
                webpage = self._download_webpage(url, '%s:%s' % (host, id), expected_status=302)
            real_url = self._og_search_property('url', webpage, default=None)
            if real_url:
                return self.url_result(real_url, ie='MastodonSH')

        metadata = self._download_json('https://%s/api/v1/statuses/%s' % (host, id), '%s:%s' % (host, id))

        if not metadata['media_attachments']:
            raise ExtractorError('No attached medias')

        entries = []
        for media in metadata['media_attachments']:
            if media['type'] == 'video':
                entries.append({
                    'id': media['id'],
                    'title': str_or_none(media['description']),
                    'url': str_or_none(media['url']),
                    'thumbnail': str_or_none(media['preview_url']),
                })
        if len(entries) == 0:
            raise ExtractorError('No audio/video attachments')

        title = '%s - %s' % (str_or_none(metadata['account'].get('display_name') or metadata['account']['acct']), clean_html(str_or_none(metadata['content'])))

        info_dict = {
            "id": id,
            "title": title,
        }
        if len(entries) == 1:
            info_dict.update(entries[0])
            info_dict.update({
                'id': id,
                'title': title,
            })
        else:
            info_dict.update({
                "_type": "playlist",
                "entries": entries,
            })

        return info_dict
