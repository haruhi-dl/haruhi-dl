# [Haruhi-DL](https://haruhi.download/)

[![build status](https://img.shields.io/gitlab/pipeline/laudom/haruhi-dl/master?gitlab_url=https%3A%2F%2Fgit.sakamoto.pl&style=flat-square)](https://git.sakamoto.pl/laudom/haruhi-dl/-/pipelines)
[![PyPI Downloads](https://img.shields.io/pypi/dm/haruhi-dl?style=flat-square)](https://pypi.org/project/haruhi-dl/)
[![License: LGPL 3.0 or later](https://img.shields.io/pypi/l/haruhi-dl?style=flat-square)](https://git.sakamoto.pl/laudom/haruhi-dl/-/blob/master/README.md)
[![Sasin stole 70 million PLN](https://img.shields.io/badge/Sasin-stole%2070%20million%20PLN-orange?style=flat-square)](https://www.planeta.pl/Wiadomosci/Polityka/Ile-kosztowaly-karty-wyborcze-Sasin-do-wiezienia-Wybory-odwolane)
[![Trans rights!](https://img.shields.io/badge/Trans-rights!-5BCEFA?style=flat-square)](http://transfuzja.org/en/artykuly/trans_people_in_poland/situation.htm)

This is a fork of [youtube-dl](https://yt-dl.org/), focused on bringing a fast, steady stream of updates. We'll do our best to merge patches to any site, not only youtube.

Our main repository is on our GitLab: https://git.sakamoto.pl/laudompat/haruhi-dl

A Microsoft GitHub mirror exists as well: https://github.com/haruhi-dl/haruhi-dl

## Installing

System-specific ways:

- [Windows .exe files](https://git.sakamoto.pl/laudompat/haruhi-dl/-/releases) ([mirror](https://github.com/haruhi-dl/haruhi-dl/releases)) - just unpack and run the exe file in cmd/powershell! (ffmpeg/rtmpdump not included, playwright extractors won't work)
- [Arch Linux (AUR)](https://aur.archlinux.org/packages/haruhi-dl/) - `yay -S haruhi-dl` (managed by mlunax)
- [macOS (homebrew)](https://formulae.brew.sh/formula/haruhi-dl) - `brew install haruhi-dl` (managed by Homebrew)

haruhi-dl is also available on PyPI: [![version on PyPI](https://img.shields.io/pypi/v/haruhi-dl?style=flat-square)](https://pypi.org/project/haruhi-dl/)

Install release from PyPI on Python 3.x:

```sh
$ python3 -m pip install --upgrade haruhi-dl
```

Install from master (unstable) on Python 3.x:

```sh
$ python3 -m pip install --upgrade git+https://git.sakamoto.pl/laudompat/haruhi-dl.git
```

**Python 2 support is dropped, use Python 3.**

## Usage

```sh
$ haruhi-dl "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

That's it! You just got rickrolled!

Full manual with all options:

```sh
$ haruhi-dl --help
```

## Differences from youtube-dl

_This is not a complete list._

- Changed license from Unlicense to LGPL 3.0
- Extracting and downloading video with subtitles from m3u8 (HLS) - this also includes subtitles from Twitter and some other services
- Support for BitTorrent protocol (only used when explicitly enabled by user with `--allow-p2p` or `--prefer-p2p`; aria2c required)
- Specific way to handle selfhosted services (untied to specific providers/domains, like PeerTube, Funkwhale, Mastodon)
- Specific way to handle content proxy sites (like Nitter for Twitter)
- Merging formats by codecs instead of file extensions, if possible (you'd rather like your AV1+opus downloads from YouTube to be .webm, than .mkv, don't you?)
- New/improved/fixed extractors:
  - PeerTube (extracting playlists, channels and user accounts, optionally downloading with BitTorrent)
  - Funkwhale
  - TikTok (extractors for user profiles, hashtags and music - all except single video and music with `--no-playlist` require Playwright)
  - cda.pl
  - Ipla
  - Weibo (DASH formats)
  - LinkedIn (videos from user posts)
  - Acast
  - Mastodon (including Pleroma, Gab Social, Soapbox)
  - Ring Publishing (aka PulsEmbed, PulseVideo, OnetMVP; Ringier Axel Springer)
  - TVP (support for TVPlayer2, client-rendered sites and TVP ABC, refactored some extractors to use mobile JSON API)
  - TVN24 (support for main page, Fakty and magazine frontend)
  - PolskieRadio
  - Agora (wyborcza.pl video, wyborcza.pl/wysokieobcasy.pl/audycje.tokfm.pl podcasts, tuba.fm)
  - sejm.gov.pl/senat.gov.pl
- Some improvements with handling JSON-LD

## Bug reports

Please send the bug details to <bug@haruhi.download> or on [Microsoft GitHub](https://github.com/haruhi-dl/haruhi-dl/issues).

## Contributing

If you want to contribute, send us a diff to <contribute@haruhi.download>, or submit a Pull Request on [our mirror at Microsoft GitHub](https://github.com/haruhi-dl/haruhi-dl).

Why contribute to this fork, and not youtube-dl?

- You make sure your contributions will always be free - under Unlicense, anyone can take your code, modify it, and close the source. LGPL 3.0 makes it clear, that any contributions must be published.

## Donations

If my contributions helped you, please consider sending me a small tip.

[![Buy Me a Coffee at ko-fi.com](https://cdn.ko-fi.com/cdn/kofi1.png?v=2)](https://ko-fi.com/selfisekai)
