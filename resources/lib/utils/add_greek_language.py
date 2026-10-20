# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    Adds Greek to Kodi's own subtitle language list
    (Player -> Language -> Preferred subtitle language), keeping whatever the
    user already has. A service module can only write its own settings, so the
    system setting is updated through JSON-RPC on localhost - no webserver
    credentials involved, the call never leaves the box.

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

import json

import xbmcaddon

try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen

try:
    from xbmcgui import Dialog
except ImportError:
    Dialog = None

ADDON_ID = 'service.subtitles.subtitles.gr'
SETTING = 'subtitles.languages'
GREEK = 'Greek'
RPC_URL = 'http://127.0.0.1:8080/jsonrpc'


def lang(string_id):

    # RunScript(path) carries no addon id, so it must be passed explicitly
    return xbmcaddon.Addon(ADDON_ID).getLocalizedString(string_id)


def rpc(method, params=None, call_id=1):

    payload = {'jsonrpc': '2.0', 'id': call_id, 'method': method}

    if params is not None:
        payload['params'] = params

    request = Request(
        RPC_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )

    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode('utf-8'))


def action():

    try:
        current = rpc('Settings.GetSettingValue', {'setting': SETTING})
        languages = current.get('result', {}).get('value', []) or []
    except Exception:
        return False, 'error'

    if GREEK in languages:
        return True, 'present'

    try:
        done = rpc('Settings.SetSettingValue',
                   {'setting': SETTING, 'value': languages + [GREEK]})
    except Exception:
        return False, 'error'

    if isinstance(done, dict) and done.get('result') is True:
        return True, 'added'

    return False, 'error'


if __name__ == '__main__':

    _ok, _state = action()

    message = {
        'present': lang(30385),
        'added': lang(30386),
        'error': lang(30387),
    }[_state]

    if Dialog is not None:
        Dialog().notification('Subtitles.gr', message, time=3000, sound=False)
