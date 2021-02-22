#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function

import os.path
import warnings
import sys

try:
    from setuptools import setup, Command
    setuptools_available = True
except ImportError:
    from distutils.core import setup, Command
    setuptools_available = False
from distutils.spawn import spawn

try:
    # This will create an exe that needs Microsoft Visual C++ 2008
    # Redistributable Package
    import py2exe
except ImportError:
    if len(sys.argv) >= 2 and sys.argv[1] == 'py2exe':
        print('Cannot import py2exe', file=sys.stderr)
        exit(1)

py2exe_options = {
    'bundle_files': 1,
    'compressed': 1,
    'optimize': 2,
    'dist_dir': '.',
    'dll_excludes': ['w9xpopen.exe', 'crypt32.dll'],
}

# Get the version from haruhi_dl/version.py without importing the package
exec(compile(open('haruhi_dl/version.py').read(),
             'haruhi_dl/version.py', 'exec'))

DESCRIPTION = 'Online video downloader'
LONG_DESCRIPTION = 'Command-line program to download videos from almost any website without DRM'

py2exe_console = [{
    'script': './haruhi_dl/__main__.py',
    'dest_base': 'haruhi-dl',
    'version': __version__,
    'description': DESCRIPTION,
    'comments': LONG_DESCRIPTION,
    'product_name': 'haruhi-dl',
    'product_version': __version__,
}]

py2exe_params = {
    'console': py2exe_console,
    'options': {'py2exe': py2exe_options},
    'zipfile': None
}

if len(sys.argv) >= 2 and sys.argv[1] == 'py2exe':
    params = py2exe_params
else:
    files_spec = [
        ('etc/bash_completion.d', ['haruhi-dl.bash-completion']),
        ('etc/fish/completions', ['haruhi-dl.fish']),
        ('share/doc/haruhi_dl', ['README.txt']),
        ('share/man/man1', ['haruhi-dl.1'])
    ]
    root = os.path.dirname(os.path.abspath(__file__))
    data_files = []
    for dirname, files in files_spec:
        resfiles = []
        for fn in files:
            if not os.path.exists(fn):
                warnings.warn('Skipping file %s since it is not present. Type  make  to build all automatically generated files.' % fn)
            else:
                resfiles.append(fn)
        data_files.append((dirname, resfiles))

    params = {
        'data_files': data_files,
    }
    if setuptools_available:
        params['entry_points'] = {'console_scripts': ['haruhi-dl = haruhi_dl:main']}
    else:
        params['scripts'] = ['bin/haruhi-dl']


class build_lazy_extractors(Command):
    description = 'Build the extractor lazy loading module'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        spawn(
            [sys.executable, 'devscripts/make_lazy_extractors.py', 'haruhi_dl/extractor/lazy_extractors.py'],
            dry_run=self.dry_run,
        )


setup(
    name='haruhi_dl',
    version=__version__,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    url='https://git.sakamoto.pl/laudom/haruhi-dl',
    author='Laura Liberda | Dominika Liberda | Patrycja Liberda',
    author_email='hdl@haruhi.download',
    maintainer='Dominika Liberda',
    maintainer_email='ja@sdomi.pl',
    license='LGPL-3.0-or-later',
    packages=[
        'haruhi_dl',
        'haruhi_dl.extractor', 'haruhi_dl.downloader',
        'haruhi_dl.postprocessor'],

    # Provokes warning on most systems (why?!)
    # test_suite = 'nose.collector',
    # test_requires = ['nosetest'],

    classifiers=[
        'Topic :: Multimedia :: Video',
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: Implementation',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],

    cmdclass={'build_lazy_extractors': build_lazy_extractors},
    **params
)
