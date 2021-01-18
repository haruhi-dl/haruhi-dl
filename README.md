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

haruhi-dl is available on PyPI: [![version on PyPI](https://img.shields.io/pypi/v/haruhi-dl?style=flat-square)](https://pypi.org/project/haruhi-dl/)

Install release from PyPI on Python 3.x:
```sh
$ python3 -m pip install --upgrade haruhi-dl
```
Install from master (unstable) on Python 3.x:
```sh
$ python3 -m pip install --upgrade git+https://git.sakamoto.pl/laudompat/haruhi-dl.git
```

Install release from PyPI on Python 2.x:
```sh
$ python2 -m pip install --upgrade haruhi-dl
```
Install from master (unstable) on Python 2.x:
```sh
$ python2 -m pip install --upgrade git+https://git.sakamoto.pl/laudompat/haruhi-dl.git
```

## Usage

```sh
$ haruhi-dl "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```
That's it! You just got rickrolled!

Full manual with all options:
```sh
$ haruhi-dl --help
```
## Contributing

If you want to contribute, send us a diff to <contribute@haruhi.download>, or submit a Pull Request on [our mirror at Microsoft GitHub](https://github.com/haruhi-dl/haruhi-dl).
