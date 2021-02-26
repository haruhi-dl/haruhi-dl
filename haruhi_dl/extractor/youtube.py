# coding: utf-8
from __future__ import unicode_literals

from datetime import datetime
import json
import hashlib
import os.path
import random
import re
import time

from .common import InfoExtractor, SearchInfoExtractor
from ..compat import (
    compat_chr,
    compat_kwargs,
    compat_parse_qs,
    compat_urllib_parse_unquote,
    compat_urllib_parse_unquote_plus,
    compat_urllib_parse_urlencode,
    compat_urllib_parse_urlparse,
    compat_urlparse,
    compat_str,
)
from ..utils import (
    bool_or_none,
    clean_html,
    error_to_compat_str,
    ExtractorError,
    float_or_none,
    get_element_by_id,
    int_or_none,
    mimetype2ext,
    parse_codecs,
    parse_duration,
    remove_quotes,
    remove_start,
    smuggle_url,
    str_or_none,
    str_to_int,
    try_get,
    unescapeHTML,
    unified_strdate,
    unsmuggle_url,
    uppercase_escape,
    url_or_none,
    urlencode_postdata,
)


class YoutubeBaseInfoExtractor(InfoExtractor):
    """Provide base functions for Youtube extractors"""
    _LOGIN_URL = 'https://accounts.google.com/ServiceLogin'
    _TWOFACTOR_URL = 'https://accounts.google.com/signin/challenge'

    _LOOKUP_URL = 'https://accounts.google.com/_/signin/sl/lookup'
    _CHALLENGE_URL = 'https://accounts.google.com/_/signin/sl/challenge'
    _TFA_URL = 'https://accounts.google.com/_/signin/challenge?hl=en&TL={0}'

    _NETRC_MACHINE = 'youtube'
    # If True it will raise an error if no login info is provided
    _LOGIN_REQUIRED = False

    _PLAYLIST_ID_RE = r'(?:LL|WL|(?:PL|EC|UU|FL|RD|UL|TL|PU|OLAK5uy_)[0-9A-Za-z-_]{10,})'

    _YOUTUBE_CLIENT_HEADERS = {
        'x-youtube-client-name': '1',
        'x-youtube-client-version': '2.20201112.04.01',
    }

    _YOUTUBE_API_KEY = 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'

    def _set_language(self):
        self._set_cookie(
            '.youtube.com', 'PREF', 'f1=50000000&f6=8&hl=en',
            # YouTube sets the expire time to about two months
            expire_time=time.time() + 2 * 30 * 24 * 3600)

    def _ids_to_results(self, ids):
        return [
            self.url_result(vid_id, 'Youtube', video_id=vid_id)
            for vid_id in ids]

    def _login(self):
        """
        Attempt to log in to YouTube.
        True is returned if successful or skipped.
        False is returned if login failed.

        If _LOGIN_REQUIRED is set and no authentication was provided, an error is raised.
        """
        username, password = self._get_login_info()
        # No authentication to be performed
        if username is None:
            if self._LOGIN_REQUIRED and self._downloader.params.get('cookiefile') is None:
                raise ExtractorError('No login info available, needed for using %s.' % self.IE_NAME, expected=True)
            return True

        login_page = self._download_webpage(
            self._LOGIN_URL, None,
            note='Downloading login page',
            errnote='unable to fetch login page', fatal=False)
        if login_page is False:
            return

        login_form = self._hidden_inputs(login_page)

        def req(url, f_req, note, errnote):
            data = login_form.copy()
            data.update({
                'pstMsg': 1,
                'checkConnection': 'youtube',
                'checkedDomains': 'youtube',
                'hl': 'en',
                'deviceinfo': '[null,null,null,[],null,"US",null,null,[],"GlifWebSignIn",null,[null,null,[]]]',
                'f.req': json.dumps(f_req),
                'flowName': 'GlifWebSignIn',
                'flowEntry': 'ServiceLogin',
                # TODO: reverse actual botguard identifier generation algo
                'bgRequest': '["identifier",""]',
            })
            return self._download_json(
                url, None, note=note, errnote=errnote,
                transform_source=lambda s: re.sub(r'^[^[]*', '', s),
                fatal=False,
                data=urlencode_postdata(data), headers={
                    'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
                    'Google-Accounts-XSRF': 1,
                })

        def warn(message):
            self._downloader.report_warning(message)

        lookup_req = [
            username,
            None, [], None, 'US', None, None, 2, False, True,
            [
                None, None,
                [2, 1, None, 1,
                 'https://accounts.google.com/ServiceLogin?passive=true&continue=https%3A%2F%2Fwww.youtube.com%2Fsignin%3Fnext%3D%252F%26action_handle_signin%3Dtrue%26hl%3Den%26app%3Ddesktop%26feature%3Dsign_in_button&hl=en&service=youtube&uilel=3&requestPath=%2FServiceLogin&Page=PasswordSeparationSignIn',
                 None, [], 4],
                1, [None, None, []], None, None, None, True
            ],
            username,
        ]

        lookup_results = req(
            self._LOOKUP_URL, lookup_req,
            'Looking up account info', 'Unable to look up account info')

        if lookup_results is False:
            return False

        user_hash = try_get(lookup_results, lambda x: x[0][2], compat_str)
        if not user_hash:
            warn('Unable to extract user hash')
            return False

        challenge_req = [
            user_hash,
            None, 1, None, [1, None, None, None, [password, None, True]],
            [
                None, None, [2, 1, None, 1, 'https://accounts.google.com/ServiceLogin?passive=true&continue=https%3A%2F%2Fwww.youtube.com%2Fsignin%3Fnext%3D%252F%26action_handle_signin%3Dtrue%26hl%3Den%26app%3Ddesktop%26feature%3Dsign_in_button&hl=en&service=youtube&uilel=3&requestPath=%2FServiceLogin&Page=PasswordSeparationSignIn', None, [], 4],
                1, [None, None, []], None, None, None, True
            ]]

        challenge_results = req(
            self._CHALLENGE_URL, challenge_req,
            'Logging in', 'Unable to log in')

        if challenge_results is False:
            return

        login_res = try_get(challenge_results, lambda x: x[0][5], list)
        if login_res:
            login_msg = try_get(login_res, lambda x: x[5], compat_str)
            warn(
                'Unable to login: %s' % 'Invalid password'
                if login_msg == 'INCORRECT_ANSWER_ENTERED' else login_msg)
            return False

        res = try_get(challenge_results, lambda x: x[0][-1], list)
        if not res:
            warn('Unable to extract result entry')
            return False

        login_challenge = try_get(res, lambda x: x[0][0], list)
        if login_challenge:
            challenge_str = try_get(login_challenge, lambda x: x[2], compat_str)
            if challenge_str == 'TWO_STEP_VERIFICATION':
                # SEND_SUCCESS - TFA code has been successfully sent to phone
                # QUOTA_EXCEEDED - reached the limit of TFA codes
                status = try_get(login_challenge, lambda x: x[5], compat_str)
                if status == 'QUOTA_EXCEEDED':
                    warn('Exceeded the limit of TFA codes, try later')
                    return False

                tl = try_get(challenge_results, lambda x: x[1][2], compat_str)
                if not tl:
                    warn('Unable to extract TL')
                    return False

                tfa_code = self._get_tfa_info('2-step verification code')

                if not tfa_code:
                    warn(
                        'Two-factor authentication required. Provide it either interactively or with --twofactor <code>'
                        '(Note that only TOTP (Google Authenticator App) codes work at this time.)')
                    return False

                tfa_code = remove_start(tfa_code, 'G-')

                tfa_req = [
                    user_hash, None, 2, None,
                    [
                        9, None, None, None, None, None, None, None,
                        [None, tfa_code, True, 2]
                    ]]

                tfa_results = req(
                    self._TFA_URL.format(tl), tfa_req,
                    'Submitting TFA code', 'Unable to submit TFA code')

                if tfa_results is False:
                    return False

                tfa_res = try_get(tfa_results, lambda x: x[0][5], list)
                if tfa_res:
                    tfa_msg = try_get(tfa_res, lambda x: x[5], compat_str)
                    warn(
                        'Unable to finish TFA: %s' % 'Invalid TFA code'
                        if tfa_msg == 'INCORRECT_ANSWER_ENTERED' else tfa_msg)
                    return False

                check_cookie_url = try_get(
                    tfa_results, lambda x: x[0][-1][2], compat_str)
            else:
                CHALLENGES = {
                    'LOGIN_CHALLENGE': "This device isn't recognized. For your security, Google wants to make sure it's really you.",
                    'USERNAME_RECOVERY': 'Please provide additional information to aid in the recovery process.',
                    'REAUTH': "There is something unusual about your activity. For your security, Google wants to make sure it's really you.",
                }
                challenge = CHALLENGES.get(
                    challenge_str,
                    '%s returned error %s.' % (self.IE_NAME, challenge_str))
                warn('%s\nGo to https://accounts.google.com/, login and solve a challenge.' % challenge)
                return False
        else:
            check_cookie_url = try_get(res, lambda x: x[2], compat_str)

        if not check_cookie_url:
            warn('Unable to extract CheckCookie URL')
            return False

        check_cookie_results = self._download_webpage(
            check_cookie_url, None, 'Checking cookie', fatal=False)

        if check_cookie_results is False:
            return False

        if 'https://myaccount.google.com/' not in check_cookie_results:
            warn('Unable to log in')
            return False

        return True

    def _download_webpage_handle(self, *args, **kwargs):
        return super(YoutubeBaseInfoExtractor, self)._download_webpage_handle(
            *args, **compat_kwargs(kwargs))

    def _real_initialize(self):
        if self._downloader is None:
            return
        self._set_language()
        if not self._login():
            return


class YoutubeIE(YoutubeBaseInfoExtractor):
    IE_DESC = 'YouTube.com'
    _VALID_URL = r"""(?x)^
                     (
                         (?:https?://|//)                                    # http(s):// or protocol-independent URL
                         (?:(?:(?:(?:\w+\.)?[yY][oO][uU][tT][uU][bB][eE](?:-nocookie|kids)?\.com/|
                            (?:www\.)?deturl\.com/www\.youtube\.com/|
                            (?:www\.)?pwnyoutube\.com/|
                            (?:www\.)?hooktube\.com/|
                            (?:www\.)?yourepeat\.com/|
                            tube\.majestyc\.net/|
                            # Invidious instances taken from https://github.com/omarroth/invidious/wiki/Invidious-Instances
                            (?:(?:www|dev)\.)?invidio\.us/|
                            (?:(?:www|no)\.)?invidiou\.sh/|
                            (?:(?:www|fi)\.)?invidious\.snopyta\.org/|
                            (?:www\.)?invidious\.kabi\.tk/|
                            (?:www\.)?invidious\.13ad\.de/|
                            (?:www\.)?invidious\.mastodon\.host/|
                            (?:www\.)?invidious\.zapashcanon\.fr/|
                            (?:www\.)?invidious\.kavin\.rocks/|
                            (?:www\.)?invidious\.tube/|
                            (?:www\.)?invidiou\.site/|
                            (?:www\.)?invidious\.site/|
                            (?:www\.)?invidious\.xyz/|
                            (?:www\.)?invidious\.nixnet\.xyz/|
                            (?:www\.)?invidious\.drycat\.fr/|
                            (?:www\.)?tube\.poal\.co/|
                            (?:www\.)?tube\.connect\.cafe/|
                            (?:www\.)?vid\.wxzm\.sx/|
                            (?:www\.)?vid\.mint\.lgbt/|
                            (?:www\.)?yewtu\.be/|
                            (?:www\.)?yt\.elukerio\.org/|
                            (?:www\.)?yt\.lelux\.fi/|
                            (?:www\.)?invidious\.ggc-project\.de/|
                            (?:www\.)?yt\.maisputain\.ovh/|
                            (?:www\.)?invidious\.13ad\.de/|
                            (?:www\.)?invidious\.toot\.koeln/|
                            (?:www\.)?invidious\.fdn\.fr/|
                            (?:www\.)?watch\.nettohikari\.com/|
                            (?:www\.)?kgg2m7yk5aybusll\.onion/|
                            (?:www\.)?qklhadlycap4cnod\.onion/|
                            (?:www\.)?axqzx4s6s54s32yentfqojs3x5i7faxza6xo3ehd4bzzsg2ii4fv2iid\.onion/|
                            (?:www\.)?c7hqkpkpemu6e7emz5b4vyz7idjgdvgaaa3dyimmeojqbgpea3xqjoid\.onion/|
                            (?:www\.)?fz253lmuao3strwbfbmx46yu7acac2jz27iwtorgmbqlkurlclmancad\.onion/|
                            (?:www\.)?invidious\.l4qlywnpwqsluw65ts7md3khrivpirse744un3x7mlskqauz5pyuzgqd\.onion/|
                            (?:www\.)?owxfohz4kjyv25fvlqilyxast7inivgiktls3th44jhk3ej3i7ya\.b32\.i2p/|
                            (?:www\.)?4l2dgddgsrkf2ous66i6seeyi6etzfgrue332grh2n7madpwopotugyd\.onion/|
                            youtube\.googleapis\.com/)                        # the various hostnames, with wildcard subdomains
                         (?:.*?\#/)?                                          # handle anchor (#/) redirect urls
                         (?:                                                  # the various things that can precede the ID:
                             (?:(?:v|embed|e)/(?!videoseries))                # v/ or embed/ or e/
                             |(?:                                             # or the v= param in all its forms
                                 (?:(?:watch|movie)(?:_popup)?(?:\.php)?/?)?  # preceding watch(_popup|.php) or nothing (like /?v=xxxx)
                                 (?:\?|\#!?)                                  # the params delimiter ? or # or #!
                                 (?:.*?[&;])??                                # any other preceding param (like /?s=tuff&v=xxxx or ?s=tuff&amp;v=V36LpHqtcDY)
                                 v=
                             )
                         ))
                         |(?:
                            youtu\.be|                                        # just youtu.be/xxxx
                            (?:www\.)?youtube\.com/(?:
                                shorts|                                       # or youtube.com/shorts/xxx
                                video                                         # or youtube.com/video/xxx
                            )|
                            vid\.plus|                                        # or vid.plus/xxxx
                            zwearz\.com/watch|                                # or zwearz.com/watch/xxxx
                         )/
                         |(?:www\.)?cleanvideosearch\.com/media/action/yt/watch\?videoId=
                         )
                     )?                                                       # all until now is optional -> you can pass the naked ID
                     ([0-9A-Za-z_-]{11})                                      # here is it! the YouTube video ID
                     (?!.*?\blist=
                        (?:
                            %(playlist_id)s|                                  # combined list/video URLs are handled by the playlist IE
                            WL                                                # WL are handled by the watch later IE
                        )
                     )
                     (?(1).+)?                                                # if we found the ID, everything can follow
                     $""" % {'playlist_id': YoutubeBaseInfoExtractor._PLAYLIST_ID_RE}
    _NEXT_URL_RE = r'[\?&]next_url=([^&]+)'
    _PLAYER_INFO_RE = (
        r'/(?P<id>[a-zA-Z0-9_-]{8,})/player_ias\.vflset(?:/[a-zA-Z]{2,3}_[a-zA-Z]{2,3})?/base\.(?P<ext>[a-z]+)$',
        r'\b(?P<id>vfl[a-zA-Z0-9_-]+)\b.*?\.(?P<ext>[a-z]+)$',
    )
    _formats = {
        # '5': {'ext': 'flv', 'width': 400, 'height': 240, 'acodec': 'mp3', 'abr': 64, 'vcodec': 'h263'},
        # '6': {'ext': 'flv', 'width': 450, 'height': 270, 'acodec': 'mp3', 'abr': 64, 'vcodec': 'h263'},
        # '13': {'ext': '3gp', 'acodec': 'aac', 'vcodec': 'mp4v'},
        # '17': {'ext': '3gp', 'width': 176, 'height': 144, 'acodec': 'aac', 'abr': 24, 'vcodec': 'mp4v'},
        '18': {'ext': 'mp4', 'width': 640, 'height': 360, 'acodec': 'aac', 'abr': 96, 'vcodec': 'h264'},
        # '22': {'ext': 'mp4', 'width': 1280, 'height': 720, 'acodec': 'aac', 'abr': 192, 'vcodec': 'h264'},
        # '34': {'ext': 'flv', 'width': 640, 'height': 360, 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264'},
        # '35': {'ext': 'flv', 'width': 854, 'height': 480, 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264'},
        # itag 36 videos are either 320x180 (BaW_jenozKc) or 320x240 (__2ABJjxzNo), abr varies as well
        # '36': {'ext': '3gp', 'width': 320, 'acodec': 'aac', 'vcodec': 'mp4v'},
        # '37': {'ext': 'mp4', 'width': 1920, 'height': 1080, 'acodec': 'aac', 'abr': 192, 'vcodec': 'h264'},
        # '38': {'ext': 'mp4', 'width': 4096, 'height': 3072, 'acodec': 'aac', 'abr': 192, 'vcodec': 'h264'},
        # '43': {'ext': 'webm', 'width': 640, 'height': 360, 'acodec': 'vorbis', 'abr': 128, 'vcodec': 'vp8'},
        # '44': {'ext': 'webm', 'width': 854, 'height': 480, 'acodec': 'vorbis', 'abr': 128, 'vcodec': 'vp8'},
        # '45': {'ext': 'webm', 'width': 1280, 'height': 720, 'acodec': 'vorbis', 'abr': 192, 'vcodec': 'vp8'},
        # '46': {'ext': 'webm', 'width': 1920, 'height': 1080, 'acodec': 'vorbis', 'abr': 192, 'vcodec': 'vp8'},
        # '59': {'ext': 'mp4', 'width': 854, 'height': 480, 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264'},
        # '78': {'ext': 'mp4', 'width': 854, 'height': 480, 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264'},


        # 3D videos
        '82': {'ext': 'mp4', 'height': 360, 'format_note': '3D', 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264', 'preference': -20},
        '83': {'ext': 'mp4', 'height': 480, 'format_note': '3D', 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264', 'preference': -20},
        '84': {'ext': 'mp4', 'height': 720, 'format_note': '3D', 'acodec': 'aac', 'abr': 192, 'vcodec': 'h264', 'preference': -20},
        '85': {'ext': 'mp4', 'height': 1080, 'format_note': '3D', 'acodec': 'aac', 'abr': 192, 'vcodec': 'h264', 'preference': -20},
        '100': {'ext': 'webm', 'height': 360, 'format_note': '3D', 'acodec': 'vorbis', 'abr': 128, 'vcodec': 'vp8', 'preference': -20},
        '101': {'ext': 'webm', 'height': 480, 'format_note': '3D', 'acodec': 'vorbis', 'abr': 192, 'vcodec': 'vp8', 'preference': -20},
        '102': {'ext': 'webm', 'height': 720, 'format_note': '3D', 'acodec': 'vorbis', 'abr': 192, 'vcodec': 'vp8', 'preference': -20},

        # Apple HTTP Live Streaming
        '91': {'ext': 'mp4', 'height': 144, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 48, 'vcodec': 'h264', 'preference': -10},
        '92': {'ext': 'mp4', 'height': 240, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 48, 'vcodec': 'h264', 'preference': -10},
        '93': {'ext': 'mp4', 'height': 360, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264', 'preference': -10},
        '94': {'ext': 'mp4', 'height': 480, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 128, 'vcodec': 'h264', 'preference': -10},
        '95': {'ext': 'mp4', 'height': 720, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 256, 'vcodec': 'h264', 'preference': -10},
        '96': {'ext': 'mp4', 'height': 1080, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 256, 'vcodec': 'h264', 'preference': -10},
        '132': {'ext': 'mp4', 'height': 240, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 48, 'vcodec': 'h264', 'preference': -10},
        '151': {'ext': 'mp4', 'height': 72, 'format_note': 'HLS', 'acodec': 'aac', 'abr': 24, 'vcodec': 'h264', 'preference': -10},

        # DASH mp4 video
        '133': {'ext': 'mp4', 'height': 240, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '134': {'ext': 'mp4', 'height': 360, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '135': {'ext': 'mp4', 'height': 480, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '136': {'ext': 'mp4', 'height': 720, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '137': {'ext': 'mp4', 'height': 1080, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '138': {'ext': 'mp4', 'format_note': 'DASH video', 'vcodec': 'h264'},  # Height can vary (https://github.com/ytdl-org/youtube-dl/issues/4559)
        '160': {'ext': 'mp4', 'height': 144, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '212': {'ext': 'mp4', 'height': 480, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '264': {'ext': 'mp4', 'height': 1440, 'format_note': 'DASH video', 'vcodec': 'h264'},
        '298': {'ext': 'mp4', 'height': 720, 'format_note': 'DASH video', 'vcodec': 'h264', 'fps': 60},
        '299': {'ext': 'mp4', 'height': 1080, 'format_note': 'DASH video', 'vcodec': 'h264', 'fps': 60},
        '266': {'ext': 'mp4', 'height': 2160, 'format_note': 'DASH video', 'vcodec': 'h264'},

        # Dash mp4 audio
        '139': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'aac', 'abr': 48, 'container': 'm4a_dash'},
        '140': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'aac', 'abr': 128, 'container': 'm4a_dash'},
        '141': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'aac', 'abr': 256, 'container': 'm4a_dash'},
        '256': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'aac', 'container': 'm4a_dash'},
        '258': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'aac', 'container': 'm4a_dash'},
        '325': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'dtse', 'container': 'm4a_dash'},
        '328': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'ec-3', 'container': 'm4a_dash'},

        # Dash webm
        '167': {'ext': 'webm', 'height': 360, 'width': 640, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp8'},
        '168': {'ext': 'webm', 'height': 480, 'width': 854, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp8'},
        '169': {'ext': 'webm', 'height': 720, 'width': 1280, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp8'},
        '170': {'ext': 'webm', 'height': 1080, 'width': 1920, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp8'},
        '218': {'ext': 'webm', 'height': 480, 'width': 854, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp8'},
        '219': {'ext': 'webm', 'height': 480, 'width': 854, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp8'},
        '278': {'ext': 'webm', 'height': 144, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'vp9'},
        '242': {'ext': 'webm', 'height': 240, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '243': {'ext': 'webm', 'height': 360, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '244': {'ext': 'webm', 'height': 480, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '245': {'ext': 'webm', 'height': 480, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '246': {'ext': 'webm', 'height': 480, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '247': {'ext': 'webm', 'height': 720, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '248': {'ext': 'webm', 'height': 1080, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '271': {'ext': 'webm', 'height': 1440, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        # itag 272 videos are either 3840x2160 (e.g. RtoitU2A-3E) or 7680x4320 (sLprVF6d7Ug)
        '272': {'ext': 'webm', 'height': 2160, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '302': {'ext': 'webm', 'height': 720, 'format_note': 'DASH video', 'vcodec': 'vp9', 'fps': 60},
        '303': {'ext': 'webm', 'height': 1080, 'format_note': 'DASH video', 'vcodec': 'vp9', 'fps': 60},
        '308': {'ext': 'webm', 'height': 1440, 'format_note': 'DASH video', 'vcodec': 'vp9', 'fps': 60},
        '313': {'ext': 'webm', 'height': 2160, 'format_note': 'DASH video', 'vcodec': 'vp9'},
        '315': {'ext': 'webm', 'height': 2160, 'format_note': 'DASH video', 'vcodec': 'vp9', 'fps': 60},

        # Dash webm audio
        '171': {'ext': 'webm', 'acodec': 'vorbis', 'format_note': 'DASH audio', 'abr': 128},
        '172': {'ext': 'webm', 'acodec': 'vorbis', 'format_note': 'DASH audio', 'abr': 256},

        # Dash webm audio with opus inside
        '249': {'ext': 'webm', 'format_note': 'DASH audio', 'acodec': 'opus', 'abr': 50},
        '250': {'ext': 'webm', 'format_note': 'DASH audio', 'acodec': 'opus', 'abr': 70},
        '251': {'ext': 'webm', 'format_note': 'DASH audio', 'acodec': 'opus', 'abr': 160},

        # RTMP (unnamed)
        # '_rtmp': {'protocol': 'rtmp'},

        # av01 video only formats sometimes served with "unknown" codecs
        '394': {'acodec': 'none', 'vcodec': 'av01.0.05M.08'},
        '395': {'acodec': 'none', 'vcodec': 'av01.0.05M.08'},
        '396': {'acodec': 'none', 'vcodec': 'av01.0.05M.08'},
        '397': {'acodec': 'none', 'vcodec': 'av01.0.05M.08'},
    }
    _SUBTITLE_FORMATS = ('srv1', 'srv2', 'srv3', 'ttml', 'vtt')

    _GEO_BYPASS = False

    IE_NAME = 'youtube'
    _TESTS = [
        {
            'url': 'https://www.youtube.com/watch?v=BaW_jenozKc&t=1s&end=9',
            'info_dict': {
                'id': 'BaW_jenozKc',
                'ext': 'mp4',
                'title': 'youtube-dl test video "\'/\\ä↭𝕐',
                'uploader': 'Philipp Hagemeister',
                'uploader_id': 'phihag',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/phihag',
                'channel_id': 'UCLqxVugv74EIW3VWh2NOa3Q',
                'channel_url': r're:https?://(?:www\.)?youtube\.com/channel/UCLqxVugv74EIW3VWh2NOa3Q',
                'upload_date': '20121002',
                'description': 'test chars:  "\'/\\ä↭𝕐\ntest URL: https://github.com/rg3/youtube-dl/issues/1892\n\nThis is a test video for youtube-dl.\n\nFor more information, contact phihag@phihag.de .',
                'categories': ['Science & Technology'],
                'tags': ['youtube-dl'],
                'duration': 10,
                'view_count': int,
                'like_count': int,
                'dislike_count': int,
                'start_time': 1,
                'end_time': 9,
            }
        },
        {
            'url': 'https://www.youtube.com/watch?v=MURua52_YPg',
            'note': 'cipher "encrypted" signature',
            'info_dict': {
                'id': 'MURua52_YPg',
                'ext': 'mp4',
                'upload_date': '20200418',
                'title': 'My Ordinary Life',
                'description': 'Provided to YouTube by Fandalism\n\nMy Ordinary Life · The Living Tombstone\n\nMy Ordinary Life\n\n℗ The Living Tombstone\n\nReleased on: 2017-11-23\n\nAuto-generated by YouTube.',
                'duration': 231,
                'uploader': 'The Living Tombstone - Topic',
                'uploader_id': 'UC5EH9egdct4dmAo3AHwzPBA',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/channel/UC5EH9egdct4dmAo3AHwzPBA',
                'creator': 'The Living Tombstone',
                'track': 'My Ordinary Life',
                'artist': 'The Living Tombstone',
            }
        },
        {
            'url': 'https://www.youtube.com/watch?v=07FYdnEawAQ',
            'note': 'Test VEVO video with age protection (#956)',
            'info_dict': {
                'id': '07FYdnEawAQ',
                'ext': 'mp4',
                'upload_date': '20130703',
                'title': 'Justin Timberlake - Tunnel Vision (Official Music Video) (Explicit)',
                'description': 'md5:fc2016d319b50b68c5541c3fd66ffd16',
                'duration': 419,
                'uploader': 'justintimberlakeVEVO',
                'uploader_id': 'justintimberlakeVEVO',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/justintimberlakeVEVO',
                'age_limit': 18,
            }
        },
        {
            'url': 'https://www.youtube.com/watch?v=BaW_jenozKc&v=UxxajLWwzqY',
            'note': 'Use the first video ID in the URL',
            'info_dict': {
                'id': 'BaW_jenozKc',
                'ext': 'mp4',
                'title': 'youtube-dl test video "\'/\\ä↭𝕐',
                'uploader': 'Philipp Hagemeister',
                'uploader_id': 'phihag',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/phihag',
                'upload_date': '20121002',
                'description': 'test chars:  "\'/\\ä↭𝕐\ntest URL: https://github.com/rg3/youtube-dl/issues/1892\n\nThis is a test video for youtube-dl.\n\nFor more information, contact phihag@phihag.de .',
                'categories': ['Science & Technology'],
                'tags': ['youtube-dl'],
                'duration': 10,
                'view_count': int,
                'like_count': int,
                'dislike_count': int,
            },
            'params': {
                'skip_download': True,
            },
        },
        # DASH manifest with encrypted signature
        {
            'url': 'https://www.youtube.com/watch?v=IB3lcPjvWLA',
            'info_dict': {
                'id': 'IB3lcPjvWLA',
                'ext': 'm4a',
                'title': 'Afrojack, Spree Wilson - The Spark (Official Music Video) ft. Spree Wilson',
                'description': 'md5:8f5e2b82460520b619ccac1f509d43bf',
                'duration': 244,
                'uploader': 'AfrojackVEVO',
                'uploader_id': 'AfrojackVEVO',
                'upload_date': '20131011',
            },
            'params': {
                'youtube_include_dash_manifest': True,
                'format': '141/bestaudio[ext=m4a]',
            },
        },
        # JS player signature function name containing $
        {
            'url': 'https://www.youtube.com/watch?v=nfWlot6h_JM',
            'info_dict': {
                'id': 'nfWlot6h_JM',
                'ext': 'm4a',
                'title': 'Taylor Swift - Shake It Off',
                'description': 'md5:9dc0bd58efe700594b54f7d82bed0bac',
                'duration': 242,
                'uploader': 'TaylorSwiftVEVO',
                'uploader_id': 'TaylorSwiftVEVO',
                'upload_date': '20140818',
            },
            'params': {
                'youtube_include_dash_manifest': True,
                'format': '141/bestaudio[ext=m4a]',
            },
        },
        # Normal age-gate video (No vevo, embed allowed)
        {
            'url': 'https://youtube.com/watch?v=HtVdAasjOgU',
            'info_dict': {
                'id': 'HtVdAasjOgU',
                'ext': 'mp4',
                'title': 'The Witcher 3: Wild Hunt - The Sword Of Destiny Trailer',
                'description': r're:(?s).{100,}About the Game\n.*?The Witcher 3: Wild Hunt.{100,}',
                'duration': 142,
                'uploader': 'The Witcher',
                'uploader_id': 'WitcherGame',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/WitcherGame',
                'upload_date': '20140605',
                'age_limit': 18,
            },
        },
        # Age-gate video with encrypted signature
        {
            'url': 'https://www.youtube.com/watch?v=6kLq3WMV1nU',
            'info_dict': {
                'id': '6kLq3WMV1nU',
                'ext': 'mp4',
                'title': 'Dedication To My Ex (Miss That) (Lyric Video)',
                'description': 'md5:33765bb339e1b47e7e72b5490139bb41',
                'duration': 246,
                'uploader': 'LloydVEVO',
                'uploader_id': 'LloydVEVO',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/LloydVEVO',
                'upload_date': '20110629',
                'age_limit': 18,
            },
        },
        # video_info is None (https://github.com/ytdl-org/youtube-dl/issues/4421)
        # YouTube Red ad is not captured for creator
        {
            'url': '__2ABJjxzNo',
            'info_dict': {
                'id': '__2ABJjxzNo',
                'ext': 'mp4',
                'duration': 266,
                'upload_date': '20100430',
                'uploader_id': 'deadmau5',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/deadmau5',
                'description': 'md5:6cbcd3a92ce1bc676fc4d6ab4ace2336',
                'uploader': 'deadmau5',
                'title': 'Deadmau5 - Some Chords (HD)',
            },
            'expected_warnings': [
                'DASH manifest missing',
            ]
        },
        # Olympics (https://github.com/ytdl-org/youtube-dl/issues/4431)
        {
            'url': 'lqQg6PlCWgI',
            'info_dict': {
                'id': 'lqQg6PlCWgI',
                'ext': 'mp4',
                'duration': 6085,
                'upload_date': '20150827',
                'uploader_id': 'olympic',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/olympic',
                'description': 'HO09  - Women -  GER-AUS - Hockey - 31 July 2012 - London 2012 Olympic Games',
                'uploader': 'Olympic',
                'title': 'Hockey - Women -  GER-AUS - London 2012 Olympic Games',
            },
            'params': {
                'skip_download': 'requires avconv',
            }
        },
        # Non-square pixels
        {
            'url': 'https://www.youtube.com/watch?v=_b-2C3KPAM0',
            'info_dict': {
                'id': '_b-2C3KPAM0',
                'ext': 'mp4',
                'stretched_ratio': 16 / 9.,
                'duration': 85,
                'upload_date': '20110310',
                'uploader_id': 'AllenMeow',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/AllenMeow',
                'description': 'made by Wacom from Korea | 字幕&加油添醋 by TY\'s Allen | 感謝heylisa00cavey1001同學熱情提供梗及翻譯',
                'uploader': '孫ᄋᄅ',
                'title': '[A-made] 變態妍字幕版 太妍 我就是這樣的人',
            },
        },
        {
            'url': 'https://vid.plus/FlRa-iH7PGw',
            'only_matching': True,
        },
        {
            'url': 'https://zwearz.com/watch/9lWxNJF-ufM/electra-woman-dyna-girl-official-trailer-grace-helbig.html',
            'only_matching': True,
        },
        {
            # Title with JS-like syntax "};" (see https://github.com/ytdl-org/youtube-dl/issues/7468)
            # Also tests cut-off URL expansion in video description (see
            # https://github.com/ytdl-org/youtube-dl/issues/1892,
            # https://github.com/ytdl-org/youtube-dl/issues/8164)
            'url': 'https://www.youtube.com/watch?v=lsguqyKfVQg',
            'info_dict': {
                'id': 'lsguqyKfVQg',
                'ext': 'mp4',
                'title': '{dark walk}; Loki/AC/Dishonored; collab w/Elflover21',
                'description': 'md5:8085699c11dc3f597ce0410b0dcbb34a',
                'duration': 133,
                'upload_date': '20151119',
                'uploader_id': 'IronSoulElf',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/IronSoulElf',
                'uploader': 'IronSoulElf',
                'creator': 'Todd Haberman,  Daniel Law Heath and Aaron Kaplan',
                'track': 'Dark Walk - Position Music',
                'artist': 'Todd Haberman,  Daniel Law Heath and Aaron Kaplan',
                'album': 'Position Music - Production Music Vol. 143 - Dark Walk',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # Tags with '};' (see https://github.com/ytdl-org/youtube-dl/issues/7468)
            'url': 'https://www.youtube.com/watch?v=Ms7iBXnlUO8',
            'only_matching': True,
        },
        {
            # Video licensed under Creative Commons
            'url': 'https://www.youtube.com/watch?v=M4gD1WSo5mA',
            'info_dict': {
                'id': 'M4gD1WSo5mA',
                'ext': 'mp4',
                'title': 'md5:e41008789470fc2533a3252216f1c1d1',
                'description': 'md5:a677553cf0840649b731a3024aeff4cc',
                'duration': 721,
                'upload_date': '20150127',
                'uploader_id': 'BerkmanCenter',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/BerkmanCenter',
                'uploader': 'The Berkman Klein Center for Internet & Society',
                'license': 'Creative Commons Attribution license (reuse allowed)',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # Channel-like uploader_url
            'url': 'https://www.youtube.com/watch?v=eQcmzGIKrzg',
            'info_dict': {
                'id': 'eQcmzGIKrzg',
                'ext': 'mp4',
                'title': 'Democratic Socialism and Foreign Policy | Bernie Sanders',
                'description': 'md5:dda0d780d5a6e120758d1711d062a867',
                'duration': 4060,
                'upload_date': '20151119',
                'uploader': 'Bernie Sanders',
                'uploader_id': 'UCH1dpzjCEiGAt8CXkryhkZg',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/channel/UCH1dpzjCEiGAt8CXkryhkZg',
                'license': 'Creative Commons Attribution license (reuse allowed)',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'https://www.youtube.com/watch?feature=player_embedded&amp;amp;v=V36LpHqtcDY',
            'only_matching': True,
        },
        {
            # YouTube Red paid video (https://github.com/ytdl-org/youtube-dl/issues/10059)
            'url': 'https://www.youtube.com/watch?v=i1Ko8UG-Tdo',
            'only_matching': True,
        },
        {
            # YouTube Red video with episode data
            'url': 'https://www.youtube.com/watch?v=iqKdEhx-dD4',
            'info_dict': {
                'id': 'iqKdEhx-dD4',
                'ext': 'mp4',
                'title': 'Isolation - Mind Field (Ep 1)',
                'description': 'md5:46a29be4ceffa65b92d277b93f463c0f',
                'duration': 2085,
                'upload_date': '20170118',
                'uploader': 'Vsauce',
                'uploader_id': 'Vsauce',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/Vsauce',
                'series': 'Mind Field',
                'season_number': 1,
                'episode_number': 1,
            },
            'params': {
                'skip_download': True,
            },
            'expected_warnings': [
                'Skipping DASH manifest',
            ],
        },
        {
            'url': 'https://www.youtube.com/watch?v=MuAGGZNfUkU&list=RDMM',
            'only_matching': True,
        },
        {
            'url': 'https://invidio.us/watch?v=BaW_jenozKc',
            'only_matching': True,
        },
        {
            # Youtube Music Auto-generated description
            'url': 'https://music.youtube.com/watch?v=MgNrAu2pzNs',
            'info_dict': {
                'id': 'MgNrAu2pzNs',
                'ext': 'mp4',
                'title': 'Voyeur Girl',
                'description': 'md5:7ae382a65843d6df2685993e90a8628f',
                'upload_date': '20190312',
                'uploader': 'Stephen - Topic',
                'uploader_id': 'UC-pWHpBjdGG69N9mM2auIAA',
                'artist': 'Stephen',
                'track': 'Voyeur Girl',
                'album': 'it\'s too much love to know my dear',
                'release_date': '20190313',
                'release_year': 2019,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # Youtube Music Auto-generated description
            # Retrieve 'artist' field from 'Artist:' in video description
            # when it is present on youtube music video
            'url': 'https://www.youtube.com/watch?v=k0jLE7tTwjY',
            'info_dict': {
                'id': 'k0jLE7tTwjY',
                'ext': 'mp4',
                'title': 'Latch Feat. Sam Smith',
                'description': 'md5:3cb1e8101a7c85fcba9b4fb41b951335',
                'upload_date': '20150110',
                'uploader': 'Various Artists - Topic',
                'uploader_id': 'UCNkEcmYdjrH4RqtNgh7BZ9w',
                'artist': 'Disclosure',
                'track': 'Latch Feat. Sam Smith',
                'album': 'Latch Featuring Sam Smith',
                'release_date': '20121008',
                'release_year': 2012,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # Youtube Music Auto-generated description
            # handle multiple artists on youtube music video
            'url': 'https://www.youtube.com/watch?v=74qn0eJSjpA',
            'info_dict': {
                'id': '74qn0eJSjpA',
                'ext': 'mp4',
                'title': 'Eastside',
                'description': 'md5:290516bb73dcbfab0dcc4efe6c3de5f2',
                'upload_date': '20180710',
                'uploader': 'Benny Blanco - Topic',
                'uploader_id': 'UCzqz_ksRu_WkIzmivMdIS7A',
                'artist': 'benny blanco, Halsey, Khalid',
                'track': 'Eastside',
                'album': 'Eastside',
                'release_date': '20180713',
                'release_year': 2018,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # Youtube Music Auto-generated description
            # handle youtube music video with release_year and no release_date
            'url': 'https://www.youtube.com/watch?v=-hcAI0g-f5M',
            'info_dict': {
                'id': '-hcAI0g-f5M',
                'ext': 'mp4',
                'title': 'Put It On Me',
                'description': 'md5:f6422397c07c4c907c6638e1fee380a5',
                'upload_date': '20180426',
                'uploader': 'Matt Maeson - Topic',
                'uploader_id': 'UCnEkIGqtGcQMLk73Kp-Q5LQ',
                'artist': 'Matt Maeson',
                'track': 'Put It On Me',
                'album': 'The Hearse',
                'release_date': None,
                'release_year': 2018,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'https://www.youtubekids.com/watch?v=BnC-cpUCdns',
            'only_matching': True,
        },
        {
            # invalid -> valid video id redirection
            'url': 'DJztXj2GPfl',
            'info_dict': {
                'id': 'DJztXj2GPfk',
                'ext': 'mp4',
                'title': 'Panjabi MC - Mundian To Bach Ke (The Dictator Soundtrack)',
                'description': 'md5:bf577a41da97918e94fa9798d9228825',
                'upload_date': '20090125',
                'uploader': 'Prochorowka',
                'uploader_id': 'Prochorowka',
                'uploader_url': r're:https?://(?:www\.)?youtube\.com/user/Prochorowka',
                'artist': 'Panjabi MC',
                'track': 'Beware of the Boys (Mundian to Bach Ke) - Motivo Hi-Lectro Remix',
                'album': 'Beware of the Boys (Mundian To Bach Ke)',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # empty description results in an empty string
            'url': 'https://www.youtube.com/watch?v=x41yOUIvK2k',
            'info_dict': {
                'id': 'x41yOUIvK2k',
                'ext': 'mp4',
                'title': 'IMG 3456',
                'description': '',
                'upload_date': '20170613',
                'uploader_id': 'ElevageOrVert',
                'uploader': 'ElevageOrVert',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'https://youtube.com/shorts/7awd-y_DTQY',
            'only_matching': True,
        },
    ]

    _VALID_SIG_VALUE_RE = r'^AO[a-zA-Z0-9_-]+=*$'

    def __init__(self, *args, **kwargs):
        super(YoutubeIE, self).__init__(*args, **kwargs)
        self._player_cache = {}

    def report_video_info_webpage_download(self, video_id):
        """Report attempt to download video info webpage."""
        self.to_screen('%s: Downloading video info webpage' % video_id)

    def report_information_extraction(self, video_id):
        """Report attempt to extract video information."""
        self.to_screen('%s: Extracting video information' % video_id)

    def report_unavailable_format(self, video_id, format):
        """Report extracted video URL."""
        self.to_screen('%s: Format %s not available' % (video_id, format))

    def _signature_cache_id(self, example_sig):
        """ Return a string representation of a signature """
        return '.'.join(compat_str(len(part)) for part in example_sig.split('.'))

    @classmethod
    def _extract_player_info(cls, player_url):
        for player_re in cls._PLAYER_INFO_RE:
            id_m = re.search(player_re, player_url)
            if id_m:
                break
        else:
            raise ExtractorError('Cannot identify player %r' % player_url)
        return id_m.group('id')

    def _extract_signature_function(self, video_id, player_url, example_sig):
        player_id = self._extract_player_info(player_url)

        # Read from filesystem cache
        func_id = '%s_%s' % (
            player_id, self._signature_cache_id(example_sig))
        assert os.path.basename(func_id) == func_id

        """
        cache_spec = self._downloader.cache.load('youtube-sigfuncs', func_id)
        if cache_spec is not None:
            return lambda s: ''.join(s[i] for i in cache_spec)
        """

        if not player_url.startswith('http'):
            player_url = 'https://www.youtube.com' + player_url
        download_note = (
            'Downloading player %s' % player_url
            if self._downloader.params.get('verbose') else
            'Downloading js player %s' % player_id
        )
        code = self._download_webpage(
            player_url, video_id,
            note=download_note,
            errnote='Download of js player %s failed' % player_url)
        res = self._parse_sig_js(code)

        """
        test_string = ''.join(map(compat_chr, range(len(example_sig))))
        cache_res = self._do_decrypt_signature(test_string, res)
        cache_spec = [ord(c) for c in cache_res]

        self._downloader.cache.store('youtube-sigfuncs', func_id, cache_spec)
        """
        return res

    def _parse_sig_js(self, js_player):
        shit_parser = re.search(r'[a-z]\=a\.split\((?:""|\'\')\);(([a-zA-Z_][a-zA-Z\d_]+).*);return a\.join', js_player)
        if not shit_parser:
            raise ExtractorError('Signature decryption code not found')
        func, obfuscated_name = shit_parser.group(1, 2)
        obfuscated_func = re.search(r'%s\s*=\s*{([\s\w(){}[\].,:;=%s"\']*?})};' % (re.escape(obfuscated_name), '%'),
                                    js_player)
        if not obfuscated_func:
            raise ExtractorError('Signature decrypting deobfuscated functions not found')
        obfuscated_stack = obfuscated_func.group(1)
        obf_map = {}
        for obffun in re.finditer(r'(?P<kp>["\'`]?)([a-zA-Z_][a-zA-Z\d_]+)(?P=kp):function\(a(?:,b)?\){(.*?)}', obfuscated_stack):
            obfname, obfval = obffun.group(2, 3)
            if 'splice' in obfval:
                obf_map[obfname] = 'splice'
            elif 'reverse' in obfval:
                obf_map[obfname] = 'reverse'
            elif 'var' in obfval and 'length' in obfval:
                obf_map[obfname] = 'mess'
            else:
                self.to_screen(obfval)
                raise ExtractorError('Unknown obfuscation function type: %s.%s' % (obfuscated_name, obfname))
        decryptor_stack = []
        for instruction in re.finditer(r'%s(?:\.|\[["\'`])([a-zA-Z_][a-zA-Z\d_]+)(?:["\'`]\])?\(a,(\d+)\);?' % re.escape(obfuscated_name),
                                       func):
            obf_name, obf_arg = instruction.group(1, 2)
            inst = obf_map.get(obf_name)
            if self._downloader.params.get('verbose', True):
                self.to_screen('sig %s %s %s' % (obf_name, inst, obf_arg))
            if inst:
                decryptor_stack.append((inst, int(obf_arg) if inst != 'reverse' else None))
            else:
                raise ExtractorError('Unknown obfuscation function: %s.%s' % (obfuscated_name, obf_name))
        return decryptor_stack

    def _do_decrypt_signature(self, sig, stack):
        a = list(sig)
        for fun in stack:
            if fun[0] == 'splice':
                a = a[fun[1]:]
            elif fun[0] == 'reverse':
                a.reverse()
            elif fun[0] == 'mess':
                a = self.mess(a, fun[1])
            else:
                raise ExtractorError('Unknown stack action: %s' % (fun[0]))
        return ''.join(a)

    def _print_sig_code(self, func, example_sig):
        def gen_sig_code(idxs):
            def _genslice(start, end, step):
                starts = '' if start == 0 else str(start)
                ends = (':%d' % (end + step)) if end + step >= 0 else ':'
                steps = '' if step == 1 else (':%d' % step)
                return 's[%s%s%s]' % (starts, ends, steps)

            step = None
            # Quelch pyflakes warnings - start will be set when step is set
            start = '(Never used)'
            for i, prev in zip(idxs[1:], idxs[:-1]):
                if step is not None:
                    if i - prev == step:
                        continue
                    yield _genslice(start, prev, step)
                    step = None
                    continue
                if i - prev in [-1, 1]:
                    step = i - prev
                    start = prev
                    continue
                else:
                    yield 's[%d]' % prev
            if step is None:
                yield 's[%d]' % i
            else:
                yield _genslice(start, i, step)

        test_string = ''.join(map(compat_chr, range(len(example_sig))))
        cache_res = func(test_string)
        cache_spec = [ord(c) for c in cache_res]
        expr_code = ' + '.join(gen_sig_code(cache_spec))
        signature_id_tuple = '(%s)' % (
            ', '.join(compat_str(len(p)) for p in example_sig.split('.')))
        code = ('if tuple(len(p) for p in s.split(\'.\')) == %s:\n'
                '    return %s\n') % (signature_id_tuple, expr_code)
        self.to_screen('Extracted signature function:\n' + code)

    def mess(self, a, b):
        c = a[0]
        a[0] = a[b % len(a)]
        a[b % len(a)] = c
        return a

    def _decrypt_signature_protected(self, s):
        a = list(s)
        a = self.mess(a, 20)
        a = a[2:]
        a = self.mess(a, 13)
        a.reverse()
        a = a[3:]
        return "".join(a)

    def _get_subtitles(self, video_id, webpage):
        try:
            subs_doc = self._download_xml(
                'https://video.google.com/timedtext?hl=en&type=list&v=%s' % video_id,
                video_id, note=False)
        except ExtractorError as err:
            self._downloader.report_warning('unable to download video subtitles: %s' % error_to_compat_str(err))
            return {}

        sub_lang_list = {}
        for track in subs_doc.findall('track'):
            lang = track.attrib['lang_code']
            if lang in sub_lang_list:
                continue
            sub_formats = []
            for ext in self._SUBTITLE_FORMATS:
                params = compat_urllib_parse_urlencode({
                    'lang': lang,
                    'v': video_id,
                    'fmt': ext,
                    'name': track.attrib['name'].encode('utf-8'),
                })
                sub_formats.append({
                    'url': 'https://www.youtube.com/api/timedtext?' + params,
                    'ext': ext,
                })
            sub_lang_list[lang] = sub_formats
        if not sub_lang_list:
            self._downloader.report_warning('video doesn\'t have subtitles')
            return {}
        return sub_lang_list

    def _get_ytplayer_config(self, video_id, webpage):
        patterns = (
            # User data may contain arbitrary character sequences that may affect
            # JSON extraction with regex, e.g. when '};' is contained the second
            # regex won't capture the whole JSON. Yet working around by trying more
            # concrete regex first keeping in mind proper quoted string handling
            # to be implemented in future that will replace this workaround (see
            # https://github.com/ytdl-org/youtube-dl/issues/7468,
            # https://github.com/ytdl-org/youtube-dl/pull/7599)
            r';ytplayer\.config\s*=\s*({.+?});ytplayer',
            r';ytplayer\.config\s*=\s*({.+?});',
        )
        config = self._search_regex(
            patterns, webpage, 'ytplayer.config', default=None)
        if config:
            return self._parse_json(
                uppercase_escape(config), video_id, fatal=False)

    def _get_automatic_captions(self, video_id, webpage):
        """We need the webpage for getting the captions url, pass it as an
           argument to speed up the process."""
        self.to_screen('%s: Looking for automatic captions' % video_id)
        player_config = self._get_ytplayer_config(video_id, webpage)
        err_msg = 'Couldn\'t find automatic captions for %s' % video_id
        if not player_config:
            self._downloader.report_warning(err_msg)
            return {}
        try:
            args = player_config['args']
            caption_url = args.get('ttsurl')
            if caption_url:
                timestamp = args['timestamp']
                # We get the available subtitles
                list_params = compat_urllib_parse_urlencode({
                    'type': 'list',
                    'tlangs': 1,
                    'asrs': 1,
                })
                list_url = caption_url + '&' + list_params
                caption_list = self._download_xml(list_url, video_id)
                original_lang_node = caption_list.find('track')
                if original_lang_node is None:
                    self._downloader.report_warning('Video doesn\'t have automatic captions')
                    return {}
                original_lang = original_lang_node.attrib['lang_code']
                caption_kind = original_lang_node.attrib.get('kind', '')

                sub_lang_list = {}
                for lang_node in caption_list.findall('target'):
                    sub_lang = lang_node.attrib['lang_code']
                    sub_formats = []
                    for ext in self._SUBTITLE_FORMATS:
                        params = compat_urllib_parse_urlencode({
                            'lang': original_lang,
                            'tlang': sub_lang,
                            'fmt': ext,
                            'ts': timestamp,
                            'kind': caption_kind,
                        })
                        sub_formats.append({
                            'url': caption_url + '&' + params,
                            'ext': ext,
                        })
                    sub_lang_list[sub_lang] = sub_formats
                return sub_lang_list

            def make_captions(sub_url, sub_langs):
                parsed_sub_url = compat_urllib_parse_urlparse(sub_url)
                caption_qs = compat_parse_qs(parsed_sub_url.query)
                captions = {}
                for sub_lang in sub_langs:
                    sub_formats = []
                    for ext in self._SUBTITLE_FORMATS:
                        caption_qs.update({
                            'tlang': [sub_lang],
                            'fmt': [ext],
                        })
                        sub_url = compat_urlparse.urlunparse(parsed_sub_url._replace(
                            query=compat_urllib_parse_urlencode(caption_qs, True)))
                        sub_formats.append({
                            'url': sub_url,
                            'ext': ext,
                        })
                    captions[sub_lang] = sub_formats
                return captions

            # New captions format as of 22.06.2017
            player_response = args.get('player_response')
            if player_response and isinstance(player_response, compat_str):
                player_response = self._parse_json(
                    player_response, video_id, fatal=False)
                if player_response:
                    renderer = player_response['captions']['playerCaptionsTracklistRenderer']
                    base_url = renderer['captionTracks'][0]['baseUrl']
                    sub_lang_list = []
                    for lang in renderer['translationLanguages']:
                        lang_code = lang.get('languageCode')
                        if lang_code:
                            sub_lang_list.append(lang_code)
                    return make_captions(base_url, sub_lang_list)

            # Some videos don't provide ttsurl but rather caption_tracks and
            # caption_translation_languages (e.g. 20LmZk1hakA)
            # Does not used anymore as of 22.06.2017
            caption_tracks = args['caption_tracks']
            caption_translation_languages = args['caption_translation_languages']
            caption_url = compat_parse_qs(caption_tracks.split(',')[0])['u'][0]
            sub_lang_list = []
            for lang in caption_translation_languages.split(','):
                lang_qs = compat_parse_qs(compat_urllib_parse_unquote_plus(lang))
                sub_lang = lang_qs.get('lc', [None])[0]
                if sub_lang:
                    sub_lang_list.append(sub_lang)
            return make_captions(caption_url, sub_lang_list)
        # An extractor error can be raise by the download process if there are
        # no automatic captions but there are subtitles
        except (KeyError, IndexError, ExtractorError):
            self._downloader.report_warning(err_msg)
            return {}

    def _mark_watched(self, video_id, video_info, player_response):
        playback_url = url_or_none(try_get(
            player_response,
            lambda x: x['playbackTracking']['videostatsPlaybackUrl']['baseUrl']) or try_get(
            video_info, lambda x: x['videostats_playback_base_url'][0]))
        if not playback_url:
            return
        parsed_playback_url = compat_urlparse.urlparse(playback_url)
        qs = compat_urlparse.parse_qs(parsed_playback_url.query)

        # cpn generation algorithm is reverse engineered from base.js.
        # In fact it works even with dummy cpn.
        CPN_ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
        cpn = ''.join((CPN_ALPHABET[random.randint(0, 256) & 63] for _ in range(0, 16)))

        qs.update({
            'ver': ['2'],
            'cpn': [cpn],
        })
        playback_url = compat_urlparse.urlunparse(
            parsed_playback_url._replace(query=compat_urllib_parse_urlencode(qs, True)))

        self._download_webpage(
            playback_url, video_id, 'Marking watched',
            'Unable to mark watched', fatal=False)

    @staticmethod
    def _extract_urls(webpage, **kwargs):
        # Embedded YouTube player
        entries = [
            unescapeHTML(mobj.group('url'))
            for mobj in re.finditer(r'''(?x)
            (?:
                <iframe[^>]+?src=|
                data-video-url=|
                <embed[^>]+?src=|
                embedSWF\(?:\s*|
                <object[^>]+data=|
                new\s+SWFObject\(
            )
            (["\'])
                (?P<url>(?:https?:)?//(?:www\.)?youtube(?:-nocookie)?\.com/
                (?:embed|v|p)/[0-9A-Za-z_-]{11}.*?)
            \1''', webpage)]

        # lazyYT YouTube embed
        entries.extend(list(map(
            unescapeHTML,
            re.findall(r'class="lazyYT" data-youtube-id="([^"]+)"', webpage))))

        # Wordpress "YouTube Video Importer" plugin
        matches = re.findall(r'''(?x)<div[^>]+
            class=(?P<q1>[\'"])[^\'"]*\byvii_single_video_player\b[^\'"]*(?P=q1)[^>]+
            data-video_id=(?P<q2>[\'"])([^\'"]+)(?P=q2)''', webpage)
        entries.extend(m[-1] for m in matches)

        return entries

    @staticmethod
    def _extract_url(webpage):
        urls = YoutubeIE._extract_urls(webpage)
        return urls[0] if urls else None

    @classmethod
    def extract_id(cls, url):
        mobj = re.match(cls._VALID_URL, url, re.VERBOSE)
        if mobj is None:
            raise ExtractorError('Invalid URL: %s' % url)
        video_id = mobj.group(2)
        return video_id

    def _extract_chapters_from_json(self, webpage, video_id, duration):
        if not webpage:
            return
        player = self._parse_json(
            self._search_regex(
                r'RELATED_PLAYER_ARGS["\']\s*:\s*({.+})\s*,?\s*\n', webpage,
                'player args', default='{}'),
            video_id, fatal=False)
        if not player or not isinstance(player, dict):
            return
        watch_next_response = player.get('watch_next_response')
        if not isinstance(watch_next_response, compat_str):
            return
        response = self._parse_json(watch_next_response, video_id, fatal=False)
        if not response or not isinstance(response, dict):
            return
        chapters_list = try_get(
            response,
            lambda x: x['playerOverlays']
                       ['playerOverlayRenderer']
                       ['decoratedPlayerBarRenderer']
                       ['decoratedPlayerBarRenderer']
                       ['playerBar']
                       ['chapteredPlayerBarRenderer']
                       ['chapters'],
            list)
        if not chapters_list:
            return

        def chapter_time(chapter):
            return float_or_none(
                try_get(
                    chapter,
                    lambda x: x['chapterRenderer']['timeRangeStartMillis'],
                    int),
                scale=1000)
        chapters = []
        for next_num, chapter in enumerate(chapters_list, start=1):
            start_time = chapter_time(chapter)
            if start_time is None:
                continue
            end_time = (chapter_time(chapters_list[next_num])
                        if next_num < len(chapters_list) else duration)
            if end_time is None:
                continue
            title = try_get(
                chapter, lambda x: x['chapterRenderer']['title']['simpleText'],
                compat_str)
            chapters.append({
                'start_time': start_time,
                'end_time': end_time,
                'title': title,
            })
        return chapters

    @staticmethod
    def _extract_chapters_from_description(description, duration):
        if not description:
            return None
        chapter_lines = re.findall(
            r'(?:^|<br\s*/>)([^<]*<a[^>]+onclick=["\']yt\.www\.watch\.player\.seekTo[^>]+>(\d{1,2}:\d{1,2}(?::\d{1,2})?)</a>[^>]*)(?=$|<br\s*/>)',
            description)
        if not chapter_lines:
            return None
        chapters = []
        for next_num, (chapter_line, time_point) in enumerate(
                chapter_lines, start=1):
            start_time = parse_duration(time_point)
            if start_time is None:
                continue
            if start_time > duration:
                break
            end_time = (duration if next_num == len(chapter_lines)
                        else parse_duration(chapter_lines[next_num][1]))
            if end_time is None:
                continue
            if end_time > duration:
                end_time = duration
            if start_time > end_time:
                break
            chapter_title = re.sub(
                r'<a[^>]+>[^<]+</a>', '', chapter_line).strip(' \t-')
            chapter_title = re.sub(r'\s+', ' ', chapter_title)
            chapters.append({
                'start_time': start_time,
                'end_time': end_time,
                'title': chapter_title,
            })
        return chapters

    def _extract_chapters(self, webpage, description, video_id, duration):
        return (self._extract_chapters_from_json(webpage, video_id, duration)
                or self._extract_chapters_from_description(description, duration))

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})

        proto = (
            'http' if self._downloader.params.get('prefer_insecure', False)
            else 'https')

        start_time = None
        end_time = None
        parsed_url = compat_urllib_parse_urlparse(url)
        for component in [parsed_url.fragment, parsed_url.query]:
            query = compat_parse_qs(component)
            if start_time is None and 't' in query:
                start_time = parse_duration(query['t'][0])
            if start_time is None and 'start' in query:
                start_time = parse_duration(query['start'][0])
            if end_time is None and 'end' in query:
                end_time = parse_duration(query['end'][0])

        # Extract original video URL from URL with redirection, like age verification, using next_url parameter
        mobj = re.search(self._NEXT_URL_RE, url)
        if mobj:
            url = proto + '://www.youtube.com/' + compat_urllib_parse_unquote(mobj.group(1)).lstrip('/')
        video_id = self.extract_id(url)

        # Get video webpage
        url = proto + '://www.youtube.com/watch?v=%s&gl=US&hl=en&has_verified=1&bpctr=9999999999' % video_id
        video_webpage, urlh = self._download_webpage_handle(url, video_id)

        qs = compat_parse_qs(compat_urllib_parse_urlparse(urlh.geturl()).query)
        video_id = qs.get('v', [None])[0] or video_id

        dash_mpds = []

        def add_dash_mpd(video_info):
            dash_mpd = video_info.get('dashmpd')
            if dash_mpd and dash_mpd[0] not in dash_mpds:
                dash_mpds.append(dash_mpd[0])

        def add_dash_mpd_pr(pl_response):
            dash_mpd = url_or_none(try_get(
                pl_response, lambda x: x['streamingData']['dashManifestUrl'],
                compat_str))
            if dash_mpd and dash_mpd not in dash_mpds:
                dash_mpds.append(dash_mpd)

        is_live = None
        view_count = None

        def extract_view_count(v_info):
            return int_or_none(try_get(v_info, lambda x: x['view_count'][0]))

        def extract_player_response(player_response, video_id):
            pl_response = str_or_none(player_response)
            if not pl_response:
                return
            pl_response = self._parse_json(pl_response, video_id, fatal=False)
            if isinstance(pl_response, dict):
                add_dash_mpd_pr(pl_response)
                return pl_response

        player_response = {}

        # Get video info
        video_info = {}
        embed_webpage = None
        if (self._og_search_property('restrictions:age', video_webpage, default=None) == '18+'
                or re.search(r'player-age-gate-content">', video_webpage) is not None):
            age_gate = True
            # We simulate the access to the video from www.youtube.com/v/{video_id}
            # this can be viewed without login into Youtube
            url = proto + '://www.youtube.com/embed/%s' % video_id
            embed_webpage = self._download_webpage(url, video_id, 'Downloading embed webpage')
            data = compat_urllib_parse_urlencode({
                'video_id': video_id,
                'eurl': 'https://youtube.googleapis.com/v/' + video_id,
                #                'sts': self._search_regex(
                #                   r'"sts"\s*:\s*(\d+)', embed_webpage, 'sts', default=''),
            })
            video_info_url = proto + '://www.youtube.com/get_video_info?' + data
            try:
                video_info_webpage = self._download_webpage(
                    video_info_url, video_id,
                    note='Refetching age-gated info webpage',
                    errnote='unable to download video info webpage')
            except ExtractorError:
                video_info_webpage = None
            if video_info_webpage:
                video_info = compat_parse_qs(video_info_webpage)
                pl_response = video_info.get('player_response', [None])[0]
                player_response = extract_player_response(pl_response, video_id)
                add_dash_mpd(video_info)
                view_count = extract_view_count(video_info)
        else:
            age_gate = False
            # Try looking directly into the video webpage
            ytplayer_config = self._get_ytplayer_config(video_id, video_webpage)
            if ytplayer_config:
                args = ytplayer_config['args']
                if args.get('url_encoded_fmt_stream_map') or args.get('hlsvp'):
                    # Convert to the same format returned by compat_parse_qs
                    video_info = dict((k, [v]) for k, v in args.items())
                    add_dash_mpd(video_info)
                # Rental video is not rented but preview is available (e.g.
                # https://www.youtube.com/watch?v=yYr8q0y5Jfg,
                # https://github.com/ytdl-org/youtube-dl/issues/10532)
                if not video_info and args.get('ypc_vid'):
                    return self.url_result(
                        args['ypc_vid'], YoutubeIE.ie_key(), video_id=args['ypc_vid'])
                if args.get('livestream') == '1' or args.get('live_playback') == 1:
                    is_live = True
                if not player_response:
                    player_response = extract_player_response(args.get('player_response'), video_id)
            if not player_response:
                player_response = extract_player_response(
                    self._search_regex(
                        r'(?:window(?:\["|\.)|var )ytInitialPlayerResponse(?:"])?\s*=\s*({.+?(?!\\)});',
                        video_webpage, 'ytInitialPlayerResponse', fatal=False), video_id)
            if not video_info or self._downloader.params.get('youtube_include_dash_manifest', True):
                add_dash_mpd_pr(player_response)

        def extract_unavailable_message():
            messages = []
            for tag, kind in (('h1', 'message'), ('div', 'submessage')):
                msg = self._html_search_regex(
                    r'(?s)<{tag}[^>]+id=["\']unavailable-{kind}["\'][^>]*>(.+?)</{tag}>'.format(tag=tag, kind=kind),
                    video_webpage, 'unavailable %s' % kind, default=None)
                if msg:
                    messages.append(msg)
            if messages:
                return '\n'.join(messages)

        if not video_info and not player_response:
            unavailable_message = extract_unavailable_message()
            if not unavailable_message:
                unavailable_message = 'Unable to extract video data'
            raise ExtractorError(
                'YouTube said: %s' % unavailable_message, expected=True, video_id=video_id)

        if not isinstance(video_info, dict):
            video_info = {}

        video_details = try_get(
            player_response, lambda x: x['videoDetails'], dict) or {}

        microformat = try_get(
            player_response, lambda x: x['microformat']['playerMicroformatRenderer'], dict) or {}

        video_title = video_info.get('title', [None])[0] or video_details.get('title')

        if not video_title:
            self._downloader.report_warning('Unable to extract video title')
            video_title = '_'

        description_original = video_description = get_element_by_id("eow-description", video_webpage)
        if video_description:

            def replace_url(m):
                redir_url = compat_urlparse.urljoin(url, m.group(1))
                parsed_redir_url = compat_urllib_parse_urlparse(redir_url)
                if re.search(r'^(?:www\.)?(?:youtube(?:-nocookie)?\.com|youtu\.be)$', parsed_redir_url.netloc) and parsed_redir_url.path == '/redirect':
                    qs = compat_parse_qs(parsed_redir_url.query)
                    q = qs.get('q')
                    if q and q[0]:
                        return q[0]
                return redir_url

            description_original = video_description = re.sub(r'''(?x)
                <a\s+
                    (?:[a-zA-Z-]+="[^"]*"\s+)*?
                    (?:title|href)="([^"]+)"\s+
                    (?:[a-zA-Z-]+="[^"]*"\s+)*?
                    class="[^"]*"[^>]*>
                [^<]+\.{3}\s*
                </a>
            ''', replace_url, video_description)
            video_description = clean_html(video_description)
        else:
            video_description = video_details.get('shortDescription')
            if video_description is None:
                video_description = self._html_search_meta('description', video_webpage)

        # title in English, if differs from the original one
        video_alt_title = try_get(microformat, lambda x: x['title']['simpleText'], compat_str)
        if video_alt_title == video_title:
            video_alt_title = None

        if not smuggled_data.get('force_singlefeed', False):
            if not self._downloader.params.get('noplaylist'):
                multifeed_metadata_list = try_get(
                    player_response,
                    lambda x: x['multicamera']['playerLegacyMulticameraRenderer']['metadataList'],
                    compat_str) or try_get(
                    video_info, lambda x: x['multifeed_metadata_list'][0], compat_str)
                if multifeed_metadata_list:
                    entries = []
                    feed_ids = []
                    for feed in multifeed_metadata_list.split(','):
                        # Unquote should take place before split on comma (,) since textual
                        # fields may contain comma as well (see
                        # https://github.com/ytdl-org/youtube-dl/issues/8536)
                        feed_data = compat_parse_qs(compat_urllib_parse_unquote_plus(feed))

                        def feed_entry(name):
                            return try_get(feed_data, lambda x: x[name][0], compat_str)

                        feed_id = feed_entry('id')
                        if not feed_id:
                            continue
                        feed_title = feed_entry('title')
                        title = video_title
                        if feed_title:
                            title += ' (%s)' % feed_title
                        entries.append({
                            '_type': 'url_transparent',
                            'ie_key': 'Youtube',
                            'url': smuggle_url(
                                '%s://www.youtube.com/watch?v=%s' % (proto, feed_data['id'][0]),
                                {'force_singlefeed': True}),
                            'title': title,
                        })
                        feed_ids.append(feed_id)
                    self.to_screen(
                        'Downloading multifeed video (%s) - add --no-playlist to just download video %s'
                        % (', '.join(feed_ids), video_id))
                    return self.playlist_result(entries, video_id, video_title, video_description)
            else:
                self.to_screen('Downloading just video %s because of --no-playlist' % video_id)

        if view_count is None:
            view_count = extract_view_count(video_info)
        if view_count is None and video_details:
            view_count = int_or_none(video_details.get('viewCount'))
        if view_count is None and microformat:
            view_count = int_or_none(microformat.get('viewCount'))

        if is_live is None:
            is_live = bool_or_none(video_details.get('isLive'))

        # Check for "rental" videos
        if 'ypc_video_rental_bar_text' in video_info and 'author' not in video_info:
            raise ExtractorError('"rental" videos not supported. See https://github.com/ytdl-org/youtube-dl/issues/359 for more information.', expected=True)

        def _extract_filesize(media_url):
            return int_or_none(self._search_regex(
                r'\bclen[=/](\d+)', media_url, 'filesize', default=None))

        streaming_formats = try_get(player_response, lambda x: x['streamingData']['formats'], list) or []
        streaming_formats.extend(try_get(player_response, lambda x: x['streamingData']['adaptiveFormats'], list) or [])

        player_url = None
        if not is_live and (streaming_formats or len(video_info.get('url_encoded_fmt_stream_map', [''])[0]) >= 1 or len(video_info.get('adaptive_fmts', [''])[0]) >= 1):
            formats = []
            formats_spec = {}
            fmt_list = video_info.get('fmt_list', [''])[0]
            if fmt_list:
                for fmt in fmt_list.split(','):
                    spec = fmt.split('/')
                    if len(spec) > 1:
                        width_height = spec[1].split('x')
                        if len(width_height) == 2:
                            formats_spec[spec[0]] = {
                                'resolution': spec[1],
                                'width': int_or_none(width_height[0]),
                                'height': int_or_none(width_height[1]),
                            }
            for fmt in streaming_formats:
                itag = str_or_none(fmt.get('itag'))
                if not itag:
                    continue
                quality = fmt.get('quality')
                quality_label = fmt.get('qualityLabel') or quality
                formats_spec[itag] = {
                    'asr': int_or_none(fmt.get('audioSampleRate')),
                    'filesize': int_or_none(fmt.get('contentLength')),
                    'format_note': quality_label,
                    'fps': int_or_none(fmt.get('fps')),
                    'height': int_or_none(fmt.get('height')),
                    # bitrate for itag 43 is always 2147483647
                    'tbr': float_or_none(fmt.get('averageBitrate') or fmt.get('bitrate'), 1000) if itag != '43' else None,
                    'width': int_or_none(fmt.get('width')),
                }

            sig_decrypt_stack = None
            for fmt in streaming_formats:
                if fmt.get('drmFamilies') or fmt.get('drm_families'):
                    continue
                url = url_or_none(fmt.get('url'))

                if not url:
                    cipher = fmt.get('cipher') or fmt.get('signatureCipher')
                    if not cipher:
                        continue
                    url_data = compat_parse_qs(cipher)
                    url = url_or_none(try_get(url_data, lambda x: x['url'][0], compat_str))
                    if not url:
                        continue
                else:
                    cipher = None
                    url_data = compat_parse_qs(compat_urllib_parse_urlparse(url).query)

                stream_type = int_or_none(try_get(url_data, lambda x: x['stream_type'][0]))
                # Unsupported FORMAT_STREAM_TYPE_OTF
                if stream_type == 3:
                    continue

                format_id = fmt.get('itag') or url_data['itag'][0]
                if not format_id:
                    continue
                format_id = compat_str(format_id)

                if cipher:
                    if 's' in url_data or self._downloader.params.get('youtube_include_dash_manifest', True):
                        ASSETS_RE = r'"jsUrl":"(/s/player/.*?/player_ias.vflset/.*?/base.js)'

                        player_url = self._search_regex(
                            ASSETS_RE,
                            embed_webpage if age_gate else video_webpage, '', default=player_url)

                        if not player_url and not age_gate:
                            # We need the embed website after all
                            if embed_webpage is None:
                                embed_url = proto + '://www.youtube.com/embed/%s' % video_id
                                embed_webpage = self._download_webpage(
                                    embed_url, video_id, 'Downloading embed webpage')
                            player_url = self._search_regex(
                                ASSETS_RE, embed_webpage, 'JS player URL')

                        # if player_url is None:
                        #    player_url_json = self._search_regex(
                        #        r'ytplayer\.config.*?"url"\s*:\s*("[^"]+")',
                        #        video_webpage, 'age gate player URL')
                        #    player_url = json.loads(player_url_json)

                    if 'sig' in url_data:
                        url += '&signature=' + url_data['sig'][0]
                    elif 's' in url_data:
                        encrypted_sig = url_data['s'][0]

                        if self._downloader.params.get('verbose'):
                            if player_url is None:
                                player_desc = 'unknown'
                            else:
                                player_version = self._extract_player_info(player_url)
                                player_desc = 'html5 player %s' % player_version
                            parts_sizes = self._signature_cache_id(encrypted_sig)
                            self.to_screen('{%s} signature length %s, %s' %
                                           (format_id, parts_sizes, player_desc))

                        signature = self._decrypt_signature_protected(encrypted_sig)
                        if not re.match(self._VALID_SIG_VALUE_RE, signature):
                            if not sig_decrypt_stack:
                                if self._downloader.params.get('verbose'):
                                    self.to_screen("Built-in signature decryption failed, trying dynamic")
                                sig_decrypt_stack = self._extract_signature_function(video_id, player_url, encrypted_sig)
                            signature = self._do_decrypt_signature(encrypted_sig, sig_decrypt_stack)

                        sp = try_get(url_data, lambda x: x['sp'][0], compat_str) or 'signature'
                        url += '&%s=%s' % (sp, signature)
                if 'ratebypass' not in url:
                    url += '&ratebypass=yes'

                dct = {
                    'format_id': format_id,
                    'url': url,
                    'player_url': player_url,
                }
                if format_id in self._formats:
                    dct.update(self._formats[format_id])
                if format_id in formats_spec:
                    dct.update(formats_spec[format_id])

                # Some itags are not included in DASH manifest thus corresponding formats will
                # lack metadata (see https://github.com/ytdl-org/youtube-dl/pull/5993).
                # Trying to extract metadata from url_encoded_fmt_stream_map entry.
                mobj = re.search(r'^(?P<width>\d+)[xX](?P<height>\d+)$', url_data.get('size', [''])[0])
                width, height = (int(mobj.group('width')), int(mobj.group('height'))) if mobj else (None, None)

                if width is None:
                    width = int_or_none(fmt.get('width'))
                if height is None:
                    height = int_or_none(fmt.get('height'))

                filesize = int_or_none(url_data.get(
                    'clen', [None])[0]) or _extract_filesize(url)

                quality = url_data.get('quality', [None])[0] or fmt.get('quality')
                quality_label = url_data.get('quality_label', [None])[0] or fmt.get('qualityLabel')

                tbr = (float_or_none(url_data.get('bitrate', [None])[0], 1000)
                       or float_or_none(fmt.get('bitrate'), 1000)) if format_id != '43' else None
                fps = int_or_none(url_data.get('fps', [None])[0]) or int_or_none(fmt.get('fps'))

                more_fields = {
                    'filesize': filesize,
                    'tbr': tbr,
                    'width': width,
                    'height': height,
                    'fps': fps,
                    'format_note': quality_label or quality,
                }
                for key, value in more_fields.items():
                    if value:
                        dct[key] = value
                type_ = url_data.get('type', [None])[0] or fmt.get('mimeType')
                if type_:
                    type_split = type_.split(';')
                    kind_ext = type_split[0].split('/')
                    if len(kind_ext) == 2:
                        kind, _ = kind_ext
                        dct['ext'] = mimetype2ext(type_split[0])
                        if kind in ('audio', 'video'):
                            codecs = None
                            for mobj in re.finditer(
                                    r'(?P<key>[a-zA-Z_-]+)=(?P<quote>["\']?)(?P<val>.+?)(?P=quote)(?:;|$)', type_):
                                if mobj.group('key') == 'codecs':
                                    codecs = mobj.group('val')
                                    break
                            if codecs:
                                dct.update(parse_codecs(codecs))
                if dct.get('acodec') == 'none' or dct.get('vcodec') == 'none':
                    dct['downloader_options'] = {
                        # Youtube throttles chunks >~10M
                        'http_chunk_size': 10485760,
                    }
                formats.append(dct)
        else:
            manifest_url = (
                url_or_none(try_get(
                    player_response,
                    lambda x: x['streamingData']['hlsManifestUrl'],
                    compat_str))
                or url_or_none(try_get(
                    video_info, lambda x: x['hlsvp'][0], compat_str)))
            if manifest_url:
                formats = []
                m3u8_formats = self._extract_m3u8_formats(
                    manifest_url, video_id, 'mp4', fatal=False)
                for a_format in m3u8_formats:
                    itag = self._search_regex(
                        r'/itag/(\d+)/', a_format['url'], 'itag', default=None)
                    if itag:
                        a_format['format_id'] = itag
                        if itag in self._formats:
                            dct = self._formats[itag].copy()
                            dct.update(a_format)
                            a_format = dct
                    a_format['player_url'] = player_url
                    # Accept-Encoding header causes failures in live streams on Youtube and Youtube Gaming
                    a_format.setdefault('http_headers', {})['Youtubedl-no-compression'] = 'True'
                    formats.append(a_format)
            else:
                error_message = extract_unavailable_message()
                if not error_message:
                    error_message = clean_html(try_get(
                        player_response, lambda x: x['playabilityStatus']['reason'],
                        compat_str))
                if not error_message:
                    error_message = clean_html(
                        try_get(video_info, lambda x: x['reason'][0], compat_str))
                if error_message:
                    raise ExtractorError(error_message, expected=True)
                raise ExtractorError('no conn, hlsvp, hlsManifestUrl or url_encoded_fmt_stream_map information found in video info')

        # uploader
        video_uploader = try_get(
            video_info, lambda x: x['author'][0],
            compat_str) or str_or_none(video_details.get('author'))
        if video_uploader:
            video_uploader = compat_urllib_parse_unquote_plus(video_uploader)
        else:
            self._downloader.report_warning('unable to extract uploader name')

        # uploader_id
        video_uploader_id = None
        video_uploader_url = None
        mobj = re.search(
            r'<link itemprop="url" href="(?P<uploader_url>https?://www\.youtube\.com/(?:user|channel)/(?P<uploader_id>[^"]+))">',
            video_webpage)
        if mobj is not None:
            video_uploader_id = mobj.group('uploader_id')
            video_uploader_url = mobj.group('uploader_url')
        else:
            owner_profile_url = url_or_none(microformat.get('ownerProfileUrl'))
            if owner_profile_url:
                video_uploader_id = self._search_regex(
                    r'(?:user|channel)/([^/]+)', owner_profile_url, 'uploader id',
                    default=None)
                video_uploader_url = owner_profile_url

        channel_id = (
            str_or_none(video_details.get('channelId'))
            or self._html_search_meta(
                'channelId', video_webpage, 'channel id', default=None)
            or self._search_regex(
                r'data-channel-external-id=(["\'])(?P<id>(?:(?!\1).)+)\1',
                video_webpage, 'channel id', default=None, group='id'))
        channel_url = 'http://www.youtube.com/channel/%s' % channel_id if channel_id else None

        thumbnails = []
        thumbnails_list = try_get(
            video_details, lambda x: x['thumbnail']['thumbnails'], list) or []
        for t in thumbnails_list:
            if not isinstance(t, dict):
                continue
            thumbnail_url = url_or_none(t.get('url'))
            if not thumbnail_url:
                continue
            thumbnails.append({
                'url': thumbnail_url,
                'width': int_or_none(t.get('width')),
                'height': int_or_none(t.get('height')),
            })

        if not thumbnails:
            video_thumbnail = None
            # We try first to get a high quality image:
            m_thumb = re.search(r'<span itemprop="thumbnail".*?href="(.*?)">',
                                video_webpage, re.DOTALL)
            if m_thumb is not None:
                video_thumbnail = m_thumb.group(1)
            thumbnail_url = try_get(video_info, lambda x: x['thumbnail_url'][0], compat_str)
            if thumbnail_url:
                video_thumbnail = compat_urllib_parse_unquote_plus(thumbnail_url)
            if video_thumbnail:
                thumbnails.append({'url': video_thumbnail})

        # upload date
        upload_date = self._html_search_meta(
            'datePublished', video_webpage, 'upload date', default=None)
        if not upload_date:
            upload_date = self._search_regex(
                [r'(?s)id="eow-date.*?>(.*?)</span>',
                 r'(?:id="watch-uploader-info".*?>.*?|["\']simpleText["\']\s*:\s*["\'])(?:Published|Uploaded|Streamed live|Started) on (.+?)[<"\']'],
                video_webpage, 'upload date', default=None)
        if not upload_date:
            upload_date = microformat.get('publishDate') or microformat.get('uploadDate')
        upload_date = unified_strdate(upload_date)

        video_license = self._html_search_regex(
            r'<h4[^>]+class="title"[^>]*>\s*License\s*</h4>\s*<ul[^>]*>\s*<li>(.+?)</li',
            video_webpage, 'license', default=None)

        m_music = re.search(
            r'''(?x)
                <h4[^>]+class="title"[^>]*>\s*Music\s*</h4>\s*
                <ul[^>]*>\s*
                <li>(?P<title>.+?)
                by (?P<creator>.+?)
                (?:
                    \(.+?\)|
                    <a[^>]*
                        (?:
                            \bhref=["\']/red[^>]*>|             # drop possible
                            >\s*Listen ad-free with YouTube Red # YouTube Red ad
                        )
                    .*?
                )?</li
            ''',
            video_webpage)
        if m_music:
            video_alt_title = remove_quotes(unescapeHTML(m_music.group('title')))
            video_creator = clean_html(m_music.group('creator'))
        else:
            video_creator = None

        def extract_meta(field):
            return self._html_search_regex(
                r'<h4[^>]+class="title"[^>]*>\s*%s\s*</h4>\s*<ul[^>]*>\s*<li>(.+?)</li>\s*' % field,
                video_webpage, field, default=None)

        track = extract_meta('Song')
        artist = extract_meta('Artist')
        album = extract_meta('Album')

        # Youtube Music Auto-generated description
        release_date = release_year = None
        if video_description:
            mobj = re.search(r'(?s)Provided to YouTube by [^\n]+\n+(?P<track>[^·]+)·(?P<artist>[^\n]+)\n+(?P<album>[^\n]+)(?:.+?℗\s*(?P<release_year>\d{4})(?!\d))?(?:.+?Released on\s*:\s*(?P<release_date>\d{4}-\d{2}-\d{2}))?(.+?\nArtist\s*:\s*(?P<clean_artist>[^\n]+))?', video_description)
            if mobj:
                if not track:
                    track = mobj.group('track').strip()
                if not artist:
                    artist = mobj.group('clean_artist') or ', '.join(a.strip() for a in mobj.group('artist').split('·'))
                if not album:
                    album = mobj.group('album'.strip())
                release_year = mobj.group('release_year')
                release_date = mobj.group('release_date')
                if release_date:
                    release_date = release_date.replace('-', '')
                    if not release_year:
                        release_year = int(release_date[:4])
                if release_year:
                    release_year = int(release_year)

        m_episode = re.search(
            r'<div[^>]+id="watch7-headline"[^>]*>\s*<span[^>]*>.*?>(?P<series>[^<]+)</a></b>\s*S(?P<season>\d+)\s*•\s*E(?P<episode>\d+)</span>',
            video_webpage)
        if m_episode:
            series = unescapeHTML(m_episode.group('series'))
            season_number = int(m_episode.group('season'))
            episode_number = int(m_episode.group('episode'))
        else:
            series = season_number = episode_number = None

        m_cat_container = self._search_regex(
            r'(?s)<h4[^>]*>\s*Category\s*</h4>\s*<ul[^>]*>(.*?)</ul>',
            video_webpage, 'categories', default=None)
        category = None
        if m_cat_container:
            category = self._html_search_regex(
                r'(?s)<a[^<]+>(.*?)</a>', m_cat_container, 'category',
                default=None)
        if not category:
            category = try_get(
                microformat, lambda x: x['category'], compat_str)
        video_categories = None if category is None else [category]

        video_tags = [
            unescapeHTML(m.group('content'))
            for m in re.finditer(self._meta_regex('og:video:tag'), video_webpage)]
        if not video_tags:
            video_tags = try_get(video_details, lambda x: x['keywords'], list)

        def _extract_count(count_name):
            cnt = self._search_regex(
                r'"label":"([0-9,]+|No) %s'
                % re.escape(count_name),
                video_webpage, count_name, default=None)
            if cnt:
                cnt = cnt.replace('No', '0')
                return str_to_int(cnt)

        like_count = _extract_count('likes')
        dislike_count = _extract_count('dislikes')

        if view_count is None:
            view_count = str_to_int(self._search_regex(
                r'<[^>]+class=["\']watch-view-count[^>]+>\s*([\d,\s]+)', video_webpage,
                'view count', default=None))

        average_rating = (
            float_or_none(video_details.get('averageRating'))
            or try_get(video_info, lambda x: float_or_none(x['avg_rating'][0])))

        # subtitles
        video_subtitles = self.extract_subtitles(video_id, video_webpage)
        automatic_captions = self.extract_automatic_captions(video_id, video_webpage)

        video_duration = try_get(
            video_info, lambda x: int_or_none(x['length_seconds'][0]))
        if not video_duration:
            video_duration = int_or_none(video_details.get('lengthSeconds'))
        if not video_duration:
            video_duration = parse_duration(self._html_search_meta(
                'duration', video_webpage, 'video duration'))

        # annotations
        video_annotations = None
        if self._downloader.params.get('writeannotations', False):
            xsrf_token = self._search_regex(
                r'([\'"])XSRF_TOKEN\1\s*:\s*([\'"])(?P<xsrf_token>[A-Za-z0-9+/=]+)\2',
                video_webpage, 'xsrf token', group='xsrf_token', fatal=False)
            invideo_url = try_get(
                player_response, lambda x: x['annotations'][0]['playerAnnotationsUrlsRenderer']['invideoUrl'], compat_str)
            if xsrf_token and invideo_url:
                xsrf_field_name = self._search_regex(
                    r'([\'"])XSRF_FIELD_NAME\1\s*:\s*([\'"])(?P<xsrf_field_name>\w+)\2',
                    video_webpage, 'xsrf field name',
                    group='xsrf_field_name', default='session_token')
                video_annotations = self._download_webpage(
                    self._proto_relative_url(invideo_url),
                    video_id, note='Downloading annotations',
                    errnote='Unable to download video annotations', fatal=False,
                    data=urlencode_postdata({xsrf_field_name: xsrf_token}))

        chapters = self._extract_chapters(video_webpage, description_original, video_id, video_duration)

        # Look for the DASH manifest
        if self._downloader.params.get('youtube_include_dash_manifest', True):
            dash_mpd_fatal = True
            for mpd_url in dash_mpds:
                dash_formats = {}
                try:
                    def decrypt_sig(mobj):
                        s = mobj.group(1)
                        dec_s = self._decrypt_signature_protected(s)
                        return '/signature/%s' % dec_s

                    mpd_url = re.sub(r'/s/([a-fA-F0-9\.]+)', decrypt_sig, mpd_url)

                    for df in self._extract_mpd_formats(
                            mpd_url, video_id, fatal=dash_mpd_fatal,
                            formats_dict=self._formats):
                        if not df.get('filesize'):
                            df['filesize'] = _extract_filesize(df['url'])
                        # Do not overwrite DASH format found in some previous DASH manifest
                        if df['format_id'] not in dash_formats:
                            dash_formats[df['format_id']] = df
                        # Additional DASH manifests may end up in HTTP Error 403 therefore
                        # allow them to fail without bug report message if we already have
                        # some DASH manifest succeeded. This is temporary workaround to reduce
                        # burst of bug reports until we figure out the reason and whether it
                        # can be fixed at all.
                        dash_mpd_fatal = False
                except (ExtractorError, KeyError) as e:
                    self.report_warning(
                        'Skipping DASH manifest: %r' % e, video_id)
                if dash_formats:
                    # Remove the formats we found through non-DASH, they
                    # contain less info and it can be wrong, because we use
                    # fixed values (for example the resolution). See
                    # https://github.com/ytdl-org/youtube-dl/issues/5774 for an
                    # example.
                    formats = [f for f in formats if f['format_id'] not in dash_formats.keys()]
                    formats.extend(dash_formats.values())

        # Check for malformed aspect ratio
        stretched_m = re.search(
            r'<meta\s+property="og:video:tag".*?content="yt:stretch=(?P<w>[0-9]+):(?P<h>[0-9]+)">',
            video_webpage)
        if stretched_m:
            w = float(stretched_m.group('w'))
            h = float(stretched_m.group('h'))
            # yt:stretch may hold invalid ratio data (e.g. for Q39EVAstoRM ratio is 17:0).
            # We will only process correct ratios.
            if w > 0 and h > 0:
                ratio = w / h
                for f in formats:
                    if f.get('vcodec') != 'none':
                        f['stretched_ratio'] = ratio

        if not formats:
            if 'reason' in video_info:
                if 'The uploader has not made this video available in your country.' in video_info['reason']:
                    regions_allowed = self._html_search_meta(
                        'regionsAllowed', video_webpage, default=None)
                    countries = regions_allowed.split(',') if regions_allowed else None
                    self.raise_geo_restricted(
                        msg=video_info['reason'][0], countries=countries)
                reason = video_info['reason'][0]
                if 'Invalid parameters' in reason:
                    unavailable_message = extract_unavailable_message()
                    if unavailable_message:
                        reason = unavailable_message
                raise ExtractorError(
                    'YouTube said: %s' % reason,
                    expected=True, video_id=video_id)
            if video_info.get('license_info') or try_get(player_response, lambda x: x['streamingData']['licenseInfos']):
                raise ExtractorError('This video is DRM protected.', expected=True)

        self._sort_formats(formats)

        self.mark_watched(video_id, video_info, player_response)

        return {
            'id': video_id,
            'uploader': video_uploader,
            'uploader_id': video_uploader_id,
            'uploader_url': video_uploader_url,
            'channel_id': channel_id,
            'channel_url': channel_url,
            'upload_date': upload_date,
            'license': video_license,
            'creator': video_creator or artist,
            'title': video_title,
            'alt_title': video_alt_title or track,
            'thumbnails': thumbnails,
            'description': video_description,
            'categories': video_categories,
            'tags': video_tags,
            'subtitles': video_subtitles,
            'automatic_captions': automatic_captions,
            'duration': video_duration,
            'age_limit': 18 if age_gate else 0,
            'annotations': video_annotations,
            'chapters': chapters,
            'webpage_url': proto + '://www.youtube.com/watch?v=%s' % video_id,
            'view_count': view_count,
            'like_count': like_count,
            'dislike_count': dislike_count,
            'average_rating': average_rating,
            'formats': formats,
            'is_live': is_live,
            'start_time': start_time,
            'end_time': end_time,
            'series': series,
            'season_number': season_number,
            'episode_number': episode_number,
            'track': track,
            'artist': artist,
            'album': album,
            'release_date': release_date,
            'release_year': release_year,
        }


class YoutubeBaseListInfoExtractor(YoutubeBaseInfoExtractor):
    _ENTRY_URL_TPL = 'https://www.youtube.com/watch?v=%s'
    _ENTRY_IE_KEY = 'Youtube'
    _LIST_NAME = '[unknown list type]'

    _parse_continuation_video_list = None
    _handle_url = None

    def _parse_video(self, entry, full_data=None, entry_key=None):
        if entry_key:
            entry = try_get(entry, lambda x: x[entry_key])
        if not entry:
            return None
        return {
            'id': try_get(entry, [
                lambda x: x['videoId'],
                lambda x: x['navigationEndpoint']['watchEndpoint']['videoId'],
            ], expected_type=compat_str),
            'title': try_get(entry, [
                lambda x: x['title']['runs'][0]['text'],
            ], expected_type=compat_str),
            # compatible with hdl thumbnails format!
            'thumbnails': try_get(entry, [
                lambda x: x['thumbnail']['thumbnails'],
            ], expected_type=list),
            'duration': try_get(entry, [
                lambda x: parse_duration(x['lengthText']['simpleText']),
                lambda x: parse_duration(x['thumbnailOverlays'][0]['thumbnailOverlayTimeStatusRenderer']['text']['simpleText']),
            ], expected_type=float),
            'view_count': try_get(entry, [
                lambda x: int_or_none(x['viewCountText']['simpleText'][:-len(' views')].replace(',', '').replace('No', '0')),
            ], expected_type=int),
            'channel': try_get(entry, [
                lambda x: x['shortBylineText']['runs'][0]['text'],
            ], expected_type=compat_str) or try_get(full_data, [
                lambda x: x['metadata']['channelMetadataRenderer']['title'],
            ], expected_type=compat_str),
            'channel_id': try_get(entry, [
                lambda x: x['shortBylineText']['runs'][0]['navigationEndpoint']['browseEndpoint']['browseId'],
            ], expected_type=compat_str) or try_get(full_data, [
                lambda x: x['metadata']['channelMetadataRenderer']['externalId'],
            ], expected_type=compat_str),
            'channel_url': try_get(entry, [
                lambda x: 'https://www.youtube.com' + x['shortBylineText']['runs'][0]['navigationEndpoint']['browseEndpoint']['canonicalBaseUrl'],
                lambda x: 'https://www.youtube.com/channel/' + x['shortBylineText']['runs'][0]['navigationEndpoint']['browseEndpoint']['browseId'],
            ], expected_type=compat_str) or try_get(full_data, [
                lambda x: x['metadata']['channelMetadataRenderer']['ownerUrls'][0],
                lambda x: x['metadata']['channelMetadataRenderer']['vanityChannelUrl'],
                lambda x: x['metadata']['channelMetadataRenderer']['channelUrl'],
            ]),
        }

    def _download_first_data(self, url, list_id, query=None):
        webpage = self._download_webpage(url, list_id,
                                         note='Downloading %s page #1 (webpage)' % (self._LIST_NAME))
        return self._parse_json(
            self._search_regex(
                r'(?:window(?:\["|\.)|var )ytInitialData(?:"])?\s*=\s*({.+});',
                webpage, 'initial data JSON'), 'initial data JSON'), webpage

    def _real_extract(self, url, results=None, query=None):
        is_search = True if query else False
        list_id = query or self._match_id(url)
        if self._handle_url:
            url = self._handle_url(url)
        data, webpage = self._download_first_data(url, list_id, query=query)
        if '/channel/' in url and '- Topic - YouTube</title>' in webpage:
            return {
                '_type': 'url',
                'url': 'youtube_topic_channel_workaround:%s' % list_id,
                'ie_key': 'YoutubeTopicChannelWorkaround',
            }
        alert = try_get(data, lambda x: x['alerts'][0]['alertRenderer'])
        if alert:
            alert_msg = ''.join((run['text'] for run in alert['text']['runs']))
            if alert.get('type') == 'ERROR':
                raise ExtractorError('YouTube said: %s' % alert_msg, expected=True)
            else:
                self.report_warning(alert_msg, video_id=list_id)
        videos = self._parse_init_video_list(data)
        entries = videos['entries']
        continuation_token = videos['continuation']
        if continuation_token and (not is_search or results):
            session_id = self._search_regex(r'ytcfg\.set\({.*?"DELEGATED_SESSION_ID":"(\d+)"',
                                            webpage, 'session id', default=None)
            page_no = 2
            while continuation_token is not None and (len(entries) < results if results else True):
                cont_res = self._download_continuation(continuation_token, list_id, page_no, session_id=session_id)
                cont_parser = self._parse_continuation_video_list
                if not cont_parser:
                    cont_parser = self._parse_init_video_list
                cont = cont_parser(cont_res)
                continuation_token = cont['continuation']
                if len(cont['entries']) == 0:
                    break
                entries.extend(cont['entries'])
                page_no += 1

        info_dict = {
            '_type': 'playlist',
            'id': list_id,
            'entries': [],
        }
        if 'info_dict' in videos:
            info_dict.update(videos['info_dict'])
        if 'title' not in info_dict:
            if is_search:
                info_dict['title'] = list_id
            else:
                info_dict['title'] = self._og_search_title(webpage)

        for _entry in entries:
            if _entry:
                entry = {
                    '_type': 'url',
                    'url': self._ENTRY_URL_TPL % (_entry['id']),
                    'ie_key': self._ENTRY_IE_KEY,
                }
                entry.update(_entry)
                info_dict['entries'].append(entry)
                if results and len(info_dict['entries']) >= results:
                    break

        return info_dict


class YoutubeAjaxListInfoExtractor(YoutubeBaseListInfoExtractor):
    def _download_continuation(self, continuation, list_id, page_no, session_id=None):
        return self._download_json('https://www.youtube.com/browse_ajax', list_id,
                                   note='Downloading %s page #%d (ajax)' % (self._LIST_NAME, page_no),
                                   headers=self._YOUTUBE_CLIENT_HEADERS, query={
                                       'continuation': continuation,
                                   })


class YoutubeYti1ListInfoExtractor(YoutubeBaseListInfoExtractor):
    # /youtubei/v1/[action]
    _ACTION_URL = 'https://www.youtube.com/youtubei/v1/%s?key=%s' % ('%s', YoutubeBaseInfoExtractor._YOUTUBE_API_KEY)
    _ACTION_NAME = 'browse'

    _YTI_CONTEXT = {
        "client": {
            "hl": "en-US",
            "clientName": "WEB",
            "clientVersion": "2.20201112.04.01",
        },
    }

    def _download_continuation(self, continuation, list_id, page_no, session_id=None):
        data = {
            'context': self._YTI_CONTEXT,
            'continuation': continuation,
        }
        headers = {
            'Content-Type': 'application/json',
            'Origin': 'https://www.youtube.com',
        }
        if session_id:
            data['context'].setdefault('user', {})['onBehalfOfUser'] = session_id
            sapisid = self._get_cookies('https://www.youtube.com').get('SAPISID').value
            if sapisid:
                timestamp = str(int(datetime.now().timestamp()))
                sapisidhash = '%s_%s' % (
                    timestamp,
                    hashlib.sha1(' '.join((timestamp, sapisid, 'https://www.youtube.com')).encode('utf-8')).hexdigest(),
                )
                headers['Authorization'] = 'SAPISIDHASH %s' % sapisidhash
        return self._download_json(self._ACTION_URL % (self._ACTION_NAME), list_id,
                                   note='Downloading %s page #%d (yti1)' % (self._LIST_NAME, page_no),
                                   headers=headers,
                                   data=bytes(json.dumps(data), encoding='utf-8'))


class YoutubeChannelIE(YoutubeAjaxListInfoExtractor):
    IE_NAME = 'youtube:channel'
    _VALID_URL = r'https?://(?:www\.|music\.)?youtube\.com/(?P<type>user|channel|c)/(?P<id>[\w-]+)(?!/live)'
    _LIST_NAME = 'channel'

    _TESTS = [{
        'url': 'https://www.youtube.com/user/reolch/videos',
        'info_dict': {
            'id': 'reolch',
            'title': 'Reol Official',
        },
        'playlist_mincount': 110,
    }, {
        # Topic channel - no /videos; requires a workaround
        'url': 'https://music.youtube.com/channel/UCyGv29emV8sGWSCle5-atLA',
        'info_dict': {
            'id': 'UCyGv29emV8sGWSCle5-atLA',
            'title': '100 Gecs',
        },
        'playlist_mincount': 10,
    }, {
        'url': 'https://www.youtube.com/channel/UCVdlcqbM4oh0xJIQAxiaV5Q',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/c/Redspl/featured',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/user/Dem3000',
        'only_matching': True,
    }]

    def _handle_url(self, url):
        parsed = re.match(self._VALID_URL, url)
        chan_type, id = parsed.group('type', 'id')
        return 'https://www.youtube.com/%s/%s/videos' % (chan_type or 'user', id)

    def _parse_init_video_list(self, data):
        grid_renderer = try_get(data, [
            # initial
            lambda x: x['contents']['twoColumnBrowseResultsRenderer']['tabs'][1]['tabRenderer']['content']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents'][0]['gridRenderer'],
            # continuation ajax
            lambda x: x[1]['response']['continuationContents']['gridContinuation'],
        ])
        if not grid_renderer:
            raise ExtractorError('Could not extract gridRenderer')
        return {
            'entries': [self._parse_video(item, entry_key='gridVideoRenderer', full_data=data)
                        for item in grid_renderer['items']],
            'continuation': try_get(grid_renderer,
                                    lambda x: x['continuations'][0]['nextContinuationData']['continuation'],
                                    expected_type=compat_str),
            'info_dict': {
                'title': try_get(data, lambda x: x['header']['c4TabbedHeaderRenderer']['title'], expected_type=compat_str),
            },
        }


class YoutubeTopicChannelWorkaroundIE(YoutubeBaseListInfoExtractor):
    IE_NAME = 'youtube:channel:topic'
    IE_DESC = False
    _VALID_URL = r'youtube_topic_channel_workaround:(?P<id>.+)'

    def _real_extract(self, url):
        channel_id = self._match_id(url)

        webpage = self._download_webpage('https://www.youtube.com/channel/%s/playlists' % channel_id, channel_id)

        initial_data = self._parse_json(
            self._search_regex(
                r'(?:window(?:\["|\.)|var )ytInitialData(?:"])?\s*=\s*({.+});',
                webpage, 'initial data JSON'), 'initial data JSON')

        # self.to_screen(json.dumps(initial_data))
        entries = []
        for shelf in initial_data['contents']['twoColumnBrowseResultsRenderer']['tabs'][1]['tabRenderer']['content']['sectionListRenderer']['contents'][1]['itemSectionRenderer']['contents']:
            if shelf['shelfRenderer']['title']['runs'][0]['text'] == 'Albums & Singles':
                items = shelf['shelfRenderer']['content']['horizontalListRenderer']['items']
                for item in items:
                    playlist = self._parse_video(item['gridPlaylistRenderer'])
                    playlist.update({
                        '_type': 'url',
                        'url': 'https://www.youtube.com/playlist?list=%s' % (item['gridPlaylistRenderer']['playlistId']),
                        'ie_key': 'YoutubePlaylist',
                    })
                    entries.append(playlist)

        return {
            '_type': 'playlist',
            'entries': entries,
            'id': channel_id,
            'title': initial_data['metadata']['channelMetadataRenderer']['musicArtistName'],
        }


class YoutubePlaylistIE(YoutubeYti1ListInfoExtractor):
    IE_NAME = 'youtube:playlist'
    _VALID_URL = r'(?:https?://(?:www\.|music\.)?youtube\.com/(?:playlist\?(?:[^&;]+[&;])*|watch\?(?:[^&;]+[&;])*)list=|ytplaylist:)?(?P<id>%(playlist_id)s)' % {'playlist_id': YoutubeBaseInfoExtractor._PLAYLIST_ID_RE}
    _LIST_NAME = 'playlist'

    _TESTS = [{
        # contains deleted/cipher-required/unicode-title videos
        'url': 'https://www.youtube.com/playlist?list=PLCjDnXEsxzUTkHuSM5KCTgaUCR4yUySq8',
        'info_dict': {
            'id': 'PLCjDnXEsxzUTkHuSM5KCTgaUCR4yUySq8',
            'title': 'coolstuff',
        },
        'playlist_mincount': 58,
    }, {
        # a lot of pages, good for checking continuity
        'url': 'https://www.youtube.com/playlist?list=PLv3TTBr1W_9tppikBxAE_G6qjWdBljBHJ',
        'info_dict': {
            'id': 'PLv3TTBr1W_9tppikBxAE_G6qjWdBljBHJ',
            'title': 'Instant Regret Clicking this Playlist',
        },
        'playlist_mincount': 3000,
        'params': {
            'skip_download': True,
        }
    }, {
        'url': 'https://music.youtube.com/playlist?list=RDCLAK5uy_muUSLNHUW02KEaoEwQJmUjVPFMFSc1BEY',
        'only_matching': True,
    }]

    def _handle_url(self, url):
        return 'https://www.youtube.com/playlist?list=%s' % self._match_id(url)

    def _parse_init_video_list(self, data):
        renderer = try_get(data, [
            # initial
            lambda x: x['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents'][0]['playlistVideoListRenderer'],
            # continuation yti1
            lambda x: x['onResponseReceivedActions'][0]['appendContinuationItemsAction'],
        ])
        if not renderer:
            raise ExtractorError('Could not extract %s item list renderer' % self._LIST_NAME)
        rend_items = try_get(renderer, [
            # initial
            lambda x: x['contents'],
            # continuation ajax
            lambda x: x['continuationItems'],
        ])
        if not rend_items:
            raise ExtractorError('Could not extract %s renderer item list' % self._LIST_NAME)
        entries = []
        for item in rend_items:
            entries.append(self._parse_video(item, entry_key='playlistVideoRenderer'))
        return {
            'entries': entries,
            'continuation': try_get(rend_items, [
                lambda x: x[-1]['continuationItemRenderer']['continuationEndpoint']['continuationCommand']['token'],
            ], expected_type=compat_str),
            'info_dict': {
                'title': try_get(data, lambda x: x['metadata']['playlistMetadataRenderer']['title'], expected_type=compat_str),
                'channel': try_get(data,
                                   lambda x: x['sidebar']['playlistSidebarRenderer']['items'][1]['playlistSidebarSecondaryInfoRenderer']['videoOwner']['videoOwnerRenderer']['title']['runs'][0]['text'],
                                   expected_type=compat_str),
                'channel_url': try_get(data,
                                       lambda x: 'https://www.youtube.com' + x['sidebar']['playlistSidebarRenderer']['items'][1]['playlistSidebarSecondaryInfoRenderer']['videoOwner']['videoOwnerRenderer']['title']['runs'][0]['navigationEndpoint']['browseEndpoint']['canonicalBaseUrl'],
                                       expected_type=compat_str),
                'channel_id': try_get(data,
                                      lambda x: x['sidebar']['playlistSidebarRenderer']['items'][1]['playlistSidebarSecondaryInfoRenderer']['videoOwner']['videoOwnerRenderer']['title']['runs'][0]['navigationEndpoint']['browseEndpoint']['browseId'],
                                      expected_type=compat_str),
            },
        }


class YoutubeSearchIE(SearchInfoExtractor, YoutubeYti1ListInfoExtractor):
    IE_NAME = 'youtube:search'
    _SEARCH_KEY = 'ytsearch'
    _MAX_RESULTS = float('inf')
    _ACTION_NAME = 'search'
    _LIST_NAME = 'search results'
    _searcher = YoutubeBaseListInfoExtractor._real_extract

    def _download_first_data(self, url, list_id, query=''):
        return self._download_json(self._ACTION_URL % (self._ACTION_NAME), list_id,
                                   note='Downloading %s page #1 (yti1)' % (self._LIST_NAME),
                                   headers={
                                       'Content-Type': 'application/json',
        }, data=bytes(json.dumps({
            'context': self._YTI_CONTEXT,
            'query': query,
        }), encoding='utf-8')), ''

    def _parse_init_video_list(self, data):
        renderer = try_get(data, [
            # initial
            lambda x: x['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents'][0]['itemSectionRenderer'],
            # continuation
            lambda x: x['onResponseReceivedCommands'][0]['appendContinuationItemsAction']['continuationItems'][0]['itemSectionRenderer'],
        ])
        if not renderer:
            raise ExtractorError('Could not extract %s item list renderer' % self._LIST_NAME)
        rend_items = try_get(renderer, [
            lambda x: x['contents'],
        ])
        if not rend_items:
            raise ExtractorError('Could not extract %s renderer item list' % self._LIST_NAME)
        entries = []
        for item in rend_items:
            entries.append(self._parse_video(item, entry_key='videoRenderer'))
        return {
            'entries': entries,
            'continuation': try_get(data, [
                # initial
                lambda x: x['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents'][-1]['continuationItemRenderer']['continuationEndpoint']['continuationCommand']['token'],
                # continuation
                lambda x: x['onResponseReceivedCommands'][0]['appendContinuationItemsAction']['continuationItems'][-1]['continuationItemRenderer']['continuationEndpoint']['continuationCommand']['token'],
            ], expected_type=compat_str),
            'info_dict': {},
        }

    def _get_n_results(self, query, n):
        return self._searcher('ytsearch', results=n, query=query)


class YoutubeLikedIE(InfoExtractor):
    _VALID_URL = r':yt(?:fav(?:ourites)?|liked)'
    _LOGIN_REQUIRED = True

    def _real_extract(self, url):
        return {
            '_type': 'url',
            'url': 'ytplaylist:LL',
            'ie_key': 'YoutubePlaylist',
        }


class YoutubeWatchLaterIE(InfoExtractor):
    _VALID_URL = r':ytw(?:atchlater|l)'
    _LOGIN_REQUIRED = True

    def _real_extract(self, url):
        return {
            '_type': 'url',
            'url': 'ytplaylist:WL',
            'ie_key': 'YoutubePlaylist',
        }


class YoutubeBaseShelfInfoExtractor(YoutubeYti1ListInfoExtractor):
    def _parse_init_video_list(self, data):
        shelf_renderer = try_get(data, [
            # initial subscriptions
            lambda x: x['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents'][0]['shelfRenderer'],
            # initial history
            lambda x: x['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents'][0]['itemSectionRenderer'],
            # continuation yti1
            lambda x: x['continuationContents']['sectionListContinuation']['contents'][0]['itemSectionRenderer']['contents'][0]['shelfRenderer'],
        ])
        if not shelf_renderer:
            raise ExtractorError('Could not extract %s shelf list renderer' % self._LIST_NAME)
        entries = []
        for shelf in shelf_renderer:
            rend_items = try_get(shelf_renderer['content']['gridRenderer'], [
                # initial subscriptions
                lambda x: x['items'],
                # continuation ajax
                lambda x: x['continuationItems'],
            ])
            if not rend_items:
                raise ExtractorError('Could not extract %s renderer item list' % self._LIST_NAME)
            for item in rend_items:
                entries.append(self._parse_video(item, entry_key='gridVideoRenderer'))
        return {
            'entries': entries,
            'continuation': try_get(data, [
                # initial
                lambda x: x['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['sectionListRenderer']['continuations'][0]['nextContinuationData']['continuation'],
                # continuation yti1
                lambda x: x['continuationContents']['sectionListContinuation']['continuations'][0]['nextContinuationData']['continuation']
            ], expected_type=compat_str),
            'info_dict': {
                'title': self._LIST_NAME,
            },
        }


class YoutubeSubscriptionsIE(YoutubeBaseShelfInfoExtractor):
    _VALID_URL = r'(?:https?://(?:www\.)?youtube\.com/feed/|:yt)(?P<id>subs(?:criptions)?)'
    IE_NAME = 'youtube:subscriptions'
    _LIST_NAME = 'subscriptions'
    _LOGIN_REQUIRED = True

    def _handle_url(self, url):
        return 'https://www.youtube.com/feed/subscriptions'


class YoutubeHistoryIE(YoutubeYti1ListInfoExtractor):
    _VALID_URL = r'(?:https?://(?:www\.)?youtube\.com/feed/|:yt)(?P<id>history)'
    IE_NAME = 'youtube:history'
    _LIST_NAME = 'history'
    _LOGIN_REQUIRED = True

    def _handle_url(self, url):
        return 'https://www.youtube.com/feed/history'

    def _parse_init_video_list(self, data):
        rend_items = try_get(data, [
            # initial
            lambda x: x['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents'],
            # continuation yti1
            lambda x: x['onResponseReceivedActions'][0]['appendContinuationItemsAction']['continuationItems'][0]['itemSectionRenderer']['contents'],
        ])
        if not rend_items:
            raise ExtractorError('Could not extract %s renderer item list' % self._LIST_NAME)
        entries = []
        for item in rend_items:
            entries.append(self._parse_video(item, entry_key='videoRenderer'))
        return {
            'entries': entries,
            'continuation': try_get(data, [
                # initial
                lambda x: x['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['sectionListRenderer']['contents'][-1]['continuationItemRenderer']['continuationEndpoint']['continuationCommand']['token'],
                # continuation yti1
                lambda x: x['onResponseReceivedActions'][0]['appendContinuationItemsAction']['continuationItems'][-1]['continuationItemRenderer']['continuationEndpoint']['continuationCommand']['token'],
            ], expected_type=compat_str),
            'info_dict': {
                'title': self._LIST_NAME,
            },
        }


class YoutubeMusicAlbumIE(YoutubeBaseListInfoExtractor):
    _VALID_URL = r'https://music\.youtube\.com/browse/(?P<id>MPREb_\w{11})'
    IE_NAME = 'youtube:music:album'
    _LIST_NAME = 'album'
    _TESTS = [{
        'url': 'https://music.youtube.com/browse/MPREb_R4FiVJOusZp',
        'info_dict': {
            'id': 'MPREb_R4FiVJOusZp',
            'title': '1000 gecs',
            'description': 'md5:107a8e7bbef00df750350775ad6a2601',
            'age_limit': 18,
        },
        'playlist_count': 10,
    }]

    def _parse_video(self, video, full_data=None, entry_key=None):
        return {
            'id': video['videoId'],
            'url': 'https://www.youtube.com/watch?v=%s' % video['videoId'],
            'title': video['title'],
            'thumbnails': try_get(video, lambda x: x['thumbnailDetails']['thumbnails']),
            'age_limit': 18 if try_get(video, lambda x: x['contentRating']['explicitType']) == 'MUSIC_ENTITY_EXPLICIT_TYPE_EXPLICIT' else 0,
            'track': video['title'],
            'track_number': int_or_none(video.get('albumTrackIndex')),
            'track_id': video.get('albumTrackIndex'),
            'artist': video.get('artistNames'),
        }

    def _download_first_data(self, url, list_id, query=None):
        webpage = self._download_webpage(url, list_id)

        data = self._search_regex(
            r"initialData\.push\({path: '\\\/browse',.+, data: '([^']+)'}\);",
            webpage, 'album data')
        # prevent DeprecationWarning on the next step
        data = data.replace(r'\/', '/')
        # https://stackoverflow.com/a/16493336/8222484
        data = bytes(data.encode('utf-8')).decode('unicode_escape')
        data = self._parse_json(data, list_id)
        return data, webpage

    def _parse_init_video_list(self, data):
        item_list = try_get(data, [
            lambda x: x['frameworkUpdates']['entityBatchUpdate']['mutations'],
        ])
        if not item_list:
            raise ExtractorError('Could not extract album item list')
        entries = []
        info_dict = {}
        for item in item_list:
            if item.get('type') == 'ENTITY_MUTATION_TYPE_REPLACE':
                payload = item.get('payload', {})
                if 'musicTrack' in payload:
                    entries.append(self._parse_video(payload['musicTrack']))
                elif 'musicAlbumRelease' in payload:
                    release = payload['musicAlbumRelease']
                    info_dict.update({
                        'title': release['title'],
                        'thumbnails': try_get(release, lambda x: x['thumbnailDetails']['thumbnails']),
                        'age_limit': 18 if try_get(release, lambda x: x['contentRating']['explicitType']) == 'MUSIC_ENTITY_EXPLICIT_TYPE_EXPLICIT' else 0,
                        'album': release['title'],
                        'album_artist': release.get('artistDisplayName'),
                        'release_year': try_get(release, lambda x: x['releaseDate']['year'], int),
                    })
                elif 'musicAlbumReleaseDetail' in payload:
                    release = payload['musicAlbumReleaseDetail']
                    info_dict.update({
                        'description': release.get('description'),
                    })
        return {
            'entries': entries,
            'continuation': None,   # everything is returned on the webpage
            'info_dict': info_dict,
        }


class YoutubeTruncatedURLIE(InfoExtractor):
    IE_NAME = 'youtube:truncated_url'
    IE_DESC = False  # Do not list
    _VALID_URL = r'''(?x)
        (?:https?://)?
        (?:\w+\.)?[yY][oO][uU][tT][uU][bB][eE](?:-nocookie)?\.com/
        (?:watch\?(?:
            feature=[a-z_]+|
            annotation_id=annotation_[^&]+|
            x-yt-cl=[0-9]+|
            hl=[^&]*|
            t=[0-9]+
        )?
        |
            attribution_link\?a=[^&]+
        )
        $
    '''

    _TESTS = [{
        'url': 'https://www.youtube.com/watch?annotation_id=annotation_3951667041',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch?',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch?x-yt-cl=84503534',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch?feature=foo',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch?hl=en-GB',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch?t=2372',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        raise ExtractorError(
            'Did you forget to quote the URL? Remember that & is a meta '
            'character in most shells, so you want to put the URL in quotes, '
            'like  haruhi-dl '
            '"https://www.youtube.com/watch?feature=foo&v=BaW_jenozKc" '
            ' or simply  haruhi-dl BaW_jenozKc  .',
            expected=True)


class YoutubeTruncatedIDIE(InfoExtractor):
    IE_NAME = 'youtube:truncated_id'
    IE_DESC = False  # Do not list
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/watch\?v=(?P<id>[0-9A-Za-z_-]{1,10})$'

    _TESTS = [{
        'url': 'https://www.youtube.com/watch?v=N_708QY7Ob',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        raise ExtractorError(
            'Incomplete YouTube ID %s. URL %s looks truncated.' % (video_id, url),
            expected=True)
