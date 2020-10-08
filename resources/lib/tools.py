# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import sys
from random import choice
from os.path import split as os_split
from tulip import control
from tulip.compat import parse_qsl

syshandle = int(sys.argv[1])
sysaddon = sys.argv[0]
params = dict(parse_qsl(sys.argv[2].replace('?', '')))

action = params.get('action')
source = params.get('source')
url = params.get('url')
query = params.get('searchstring')
langs = params.get('languages')


def multichoice(filenames):

    if filenames is None or len(filenames) == 0:

        return

    elif len(filenames) >= 1:

        if len(filenames) == 1:
            return filenames[0]

        choices = [os_split(i)[1] for i in filenames]

        choices.insert(0, control.lang(32215))

        _choice = control.selectDialog(heading=control.lang(32214), list=choices)

        if _choice == 0:
            filename = choice(filenames)
        elif _choice != -1 and _choice <= len(filenames) + 1:
            filename = filenames[_choice - 1]
        else:
            filename = choice(filenames)

        return filename

    else:

        return
