# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''


from resources.lib.tools import action, query, url, source
from resources.lib.addon import Search, Download

########################################################################################################################

if action in [None, 'search']:
    Search().run()

elif action == 'manualsearch':
    Search().run(query)

elif action == 'download':
    Download().run(url, source)

########################################################################################################################
