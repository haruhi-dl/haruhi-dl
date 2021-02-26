#!/usr/bin/env python3
from __future__ import unicode_literals

# Execute with
# $ python haruhi_dl/__main__.py (2.6+)
# $ python -m haruhi_dl          (2.7+)

import sys

if sys.version_info[0] == 2:
    sys.exit('haruhi-dl no longer works on Python 2, use Python 3 instead')

if __package__ is None and not hasattr(sys, 'frozen'):
    # direct call of __main__.py
    import os.path
    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

import haruhi_dl

if __name__ == '__main__':
    haruhi_dl.main()
