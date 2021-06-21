# this is intended to speed-up some extractors,
# which sometimes need to extract some data that doesn't change very much often,
# but it does on random times, like youtube's signature "crypto" or soundcloud's client id

import os
from os.path import dirname as dirn
import sys
sys.path.insert(0, dirn(dirn((os.path.abspath(__file__)))))

from haruhi_dl import HaruhiDL
from haruhi_dl.utils import (
    ExtractorError,
)

hdl = HaruhiDL(params={
    'quiet': True,
})
artifact_dir = os.path.join(dirn(dirn((os.path.abspath(__file__)))), 'haruhi_dl', 'extractor_artifacts')
if not os.path.exists(artifact_dir):
    os.mkdir(artifact_dir)

for ie_name in (
    'Youtube',
):
    ie = hdl.get_info_extractor(ie_name)
    try:
        file_contents = ie._generate_prerelease_file()
        with open(os.path.join(artifact_dir, ie_name.lower() + '.py'), 'w') as file:
            file.write(file_contents)
    except ExtractorError as err:
        print(err)
