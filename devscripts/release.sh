#!/bin/bash

if [[ "$(basename $(pwd))" == 'devscripts' ]]; then
	cd ..
fi

v="$(date "+%Y.%m.%d")"

if [[ "$(grep "'$v" haruhi_dl/version.py)" != '' ]]; then #' is this the first release of the day?
	if [[ "$(grep -Poh '[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]' haruhi_dl/version.py)" != '' ]]; then # so, 2nd or nth?
		v="$v.$(($(cat haruhi_dl/version.py | grep -Poh '[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]' | grep -Poh '[0-9]+$')+1))"
	else
		v="$v.1"
	fi
fi

sed "s/__version__ = '.*'/__version__ = '$v'/g" -i haruhi_dl/version.py

python3 devscripts/prerelease_codegen.py
python3 setup.py build_lazy_extractors
rm -R build dist
python3 setup.py sdist bdist_wheel
python3 -m twine upload dist/*
devscripts/wine-py2exe.sh setup.py
