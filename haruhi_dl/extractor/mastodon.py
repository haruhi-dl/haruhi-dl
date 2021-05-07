# coding: utf-8
from __future__ import unicode_literals

from .common import SelfhostedInfoExtractor

from ..utils import (
    clean_html,
    float_or_none,
    int_or_none,
    str_or_none,
    try_get,
    unescapeHTML,
    url_or_none,
    ExtractorError,
)

from urllib.parse import (
    parse_qs,
    urlencode,
    urlparse,
)
import json
import re

from .peertube import PeerTubeSHIE


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
    _NETRC_MACHINE = 'mastodon'
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
        '<noscript>To use Soapbox, please enable JavaScript.</noscript>',
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
    }, {
        # Soapbox, audio file
        'url': 'https://gleasonator.com/notice/9zvJY6h7jJzwopKAIi',
        'info_dict': {
            'id': '9zvJY6h7jJzwopKAIi',
            'title': 're:.+ - #FEDIBLOCK',
            'ext': 'oga',
        },
    }, {
        # mastodon, card to youtube
        'url': 'https://mstdn.social/@polamatysiak/106183574509332910',
        'info_dict': {
            'id': 'RWDU0BjcYp0',
            'ext': 'mp4',
            'title': 'polamatysiak - Moje wczorajsze wystąpienie w Sejmie, koniecznie zobaczcie do końca 🙂 \n#pracaposłanki\n\nhttps://youtu.be/RWDU0BjcYp0',
            'description': 'md5:0c16fa11a698d5d1b171963fd6833297',
            'uploader': 'Paulina Matysiak',
            'uploader_id': 'UCLRAd9-Hw6kEI1aPBrSaF9A',
            'upload_date': '20210505',
        },
    }]

    def _determine_instance_software(self, host, webpage=None):
        if webpage:
            for i, string in enumerate(self._SH_VALID_CONTENT_STRINGS):
                if string in webpage:
                    return ['mastodon', 'mastodon', 'pleroma', 'pleroma', 'pleroma', 'gab'][i]
            if any(s in webpage for s in PeerTubeSHIE._SH_VALID_CONTENT_STRINGS):
                return 'peertube'

        nodeinfo_href = self._download_json(
            f'https://{host}/.well-known/nodeinfo', host, 'Downloading instance nodeinfo link')

        nodeinfo = self._download_json(
            nodeinfo_href['links'][-1]['href'], host, 'Downloading instance nodeinfo')

        return nodeinfo['software']['name']

    def _login(self):
        username, password = self._get_login_info()
        if not username:
            return False

        # very basic regex, but the instance domain (the one where user has an account)
        # must be separated from the user login
        mobj = re.match(r'^(?P<username>[^@]+(?:@[^@]+)?)@(?P<instance>.+)$', username)
        if not mobj:
            self.report_warning(
                'Invalid login format - must be in format [username or email]@[instance]')
        username, instance = mobj.group('username', 'instance')

        app_info = self._downloader.cache.load('mastodon-apps', instance)
        if not app_info:
            app_info = self._download_json(
                f'https://{instance}/api/v1/apps', None, 'Creating an app', headers={
                    'Content-Type': 'application/json',
                }, data=bytes(json.dumps({
                    'client_name': 'haruhi-dl',
                    'redirect_uris': 'urn:ietf:wg:oauth:2.0:oob',
                    'scopes': 'read',
                    'website': 'https://haruhi.download',
                }).encode('utf-8')))
            self._downloader.cache.store('mastodon-apps', instance, app_info)

        login_webpage = self._download_webpage(
            f'https://{instance}/oauth/authorize', None, 'Downloading login page', query={
                'client_id': app_info['client_id'],
                'scope': 'read',
                'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
                'response_type': 'code',
            })
        oauth_token = None
        # this needs to be codebase-specific, as the HTML page differs between codebases
        if 'xlink:href="#mastodon-svg-logo-full"' in login_webpage:
            # mastodon
            if '@' not in username:
                self.report_warning(
                    'Invalid login format - for Mastodon instances e-mail address is required')
            login_form = self._hidden_inputs(login_webpage)
            login_form['user[email]'] = username
            login_form['user[password]'] = password
            login_req, urlh = self._download_webpage_handle(
                f'https://{instance}/auth/sign_in', None, 'Sending login details',
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                }, data=bytes(urlencode(login_form).encode('utf-8')))
            # cached apps may already be authorized
            if '/oauth/authorize/native' in urlh.url:
                oauth_token = parse_qs(urlparse(urlh.url).query)['code'][0]
            else:
                auth_form = self._hidden_inputs(
                    self._search_regex(
                        r'(?s)(<form\b[^>]+>.+?>Authorize</.+?</form>)',
                        login_req, 'authorization form'))
                _, urlh = self._download_webpage_handle(
                    f'https://{instance}/oauth/authorize', None, 'Confirming authorization',
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded',
                    }, data=bytes(urlencode(auth_form).encode('utf-8')))
                oauth_token = parse_qs(urlparse(urlh.url).query)['code'][0]
        elif 'content: "✔\\fe0e";' in login_webpage:
            # pleroma
            login_form = self._hidden_inputs(login_webpage)
            login_form['authorization[scope][]'] = 'read'
            login_form['authorization[name]'] = username
            login_form['authorization[password]'] = password
            login_req = self._download_webpage(
                f'https://{instance}/oauth/authorize', None, 'Sending login details',
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                }, data=bytes(urlencode(login_form).encode('utf-8')))
            # TODO: 2FA, error handling
            oauth_token = self._search_regex(
                r'<h2>\s*Token code is\s*<br>\s*([a-zA-Z\d_-]+)\s*</h2>',
                login_req, 'oauth token')
        else:
            raise ExtractorError('Unknown instance type')

        actual_token = self._download_json(
            f'https://{instance}/oauth/token', None, 'Downloading the actual token',
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
            }, data=bytes(urlencode({
                'client_id': app_info['client_id'],
                'client_secret': app_info['client_secret'],
                'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
                'scope': 'read',
                'code': oauth_token,
                'grant_type': 'authorization_code',
            }).encode('utf-8')))
        return {
            'instance': instance,
            'authorization': f"{actual_token['token_type']} {actual_token['access_token']}",
        }

    def _selfhosted_extract(self, url, webpage=None):
        mobj = re.match(self._VALID_URL, url)
        ap_censorship_circuvement = False
        if not mobj:
            mobj = re.match(self._SH_VALID_URL, url)
        if not mobj and self._downloader.params.get('force_use_mastodon'):
            mobj = re.match(PeerTubeSHIE._VALID_URL, url)
            if mobj:
                ap_censorship_circuvement = 'peertube'
        if not mobj and self._downloader.params.get('force_use_mastodon'):
            mobj = re.match(PeerTubeSHIE._SH_VALID_URL, url)
            if mobj:
                ap_censorship_circuvement = 'peertube'
        if not mobj:
            raise ExtractorError('Unrecognized url type')
        host, id = mobj.group('host', 'id')

        login_info = self._login()

        if login_info and host != login_info['instance']:
            wf_url = url
            if not url.startswith('http'):
                software = ap_censorship_circuvement
                if not software:
                    software = self._determine_instance_software(host, webpage)
                url_part = None
                if software == 'pleroma':
                    if '-' in id:   # UUID
                        url_part = 'objects'
                    else:
                        url_part = 'notice'
                elif software == 'peertube':
                    url_part = 'videos/watch'
                elif software in ('mastodon', 'gab'):
                    # mastodon and gab social require usernames in the url,
                    # but we can't determine the username without fetching the post,
                    # but we can't fetch the post without determining the username...
                    raise ExtractorError(f'Use the full url with --force-use-mastodon to download from {software}', expected=True)
                else:
                    raise ExtractorError(f'Unknown software: {software}')
                wf_url = f'https://{host}/{url_part}/{id}'
            search = self._download_json(
                f"https://{login_info['instance']}/api/v2/search", '%s:%s' % (host, id),
                query={
                    'q': wf_url,
                    'type': 'statuses',
                    'resolve': True,
                }, headers={
                    'Authorization': login_info['authorization'],
                })
            assert len(search['statuses']) == 1
            metadata = search['statuses'][0]
        else:
            if not login_info and any(frag in url for frag in ('/objects/', '/activities/')):
                if not webpage:
                    webpage = self._download_webpage(url, '%s:%s' % (host, id), expected_status=302)
                real_url = self._og_search_property('url', webpage, default=None)
                if real_url:
                    return self.url_result(real_url, ie='MastodonSH')
            metadata = self._download_json(
                'https://%s/api/v1/statuses/%s' % (host, id), '%s:%s' % (host, id),
                headers={
                    'Authorization': login_info['authorization'],
                } if login_info else {})

        entries = []
        for media in metadata['media_attachments'] or ():
            if media['type'] in ('video', 'audio'):
                entries.append({
                    'id': media['id'],
                    'title': str_or_none(media['description']),
                    'url': str_or_none(media['url']),
                    'thumbnail': str_or_none(media['preview_url']) if media['type'] == 'video' else None,
                    'vcodec': 'none' if media['type'] == 'audio' else None,
                    'duration': float_or_none(try_get(media, lambda x: x['meta']['original']['duration'])),
                    'width': int_or_none(try_get(media, lambda x: x['meta']['original']['width'])),
                    'height': int_or_none(try_get(media, lambda x: x['meta']['original']['height'])),
                    'tbr': int_or_none(try_get(media, lambda x: x['meta']['original']['bitrate'])),
                })

        title = '%s - %s' % (str_or_none(metadata['account'].get('display_name') or metadata['account']['acct']), clean_html(str_or_none(metadata['content'])))
        if ap_censorship_circuvement == 'peertube':
            title = unescapeHTML(
                self._search_regex(
                    r'^<p><a href="[^"]+">(.+?)</a></p>',
                    metadata['content'], 'video title'))

        if len(entries) == 0:
            card = metadata.get('card')
            if card:
                return {
                    '_type': 'url_transparent',
                    'url': card['url'],
                    'title': title,
                    'thumbnail': url_or_none(card.get('image')),
                }
            raise ExtractorError('No audio/video attachments')

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
