# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    Machine-translation fallback. Downloads an English subtitle and translates
    it to Greek through Google's keyless endpoint, in batches, with progress
    and cancellation.

    Only ever runs at download time for entries explicitly tagged [TR], and
    only when the user enabled the translate toggle.

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import re
import json
import urllib.parse

from resources.lib.utils import impersonate
from resources.lib.utils.tools import Cancelled
from tulip.log import log as log_debug


# Cues per request. Verified: 20 cues come back complete in under a second;
# repeated q params do NOT batch (the server answers only the first).
BATCH = 20

# Joins cue texts inside one request. Split on the same marker afterwards.
SEP = '\n<<<>>>\n'

GTX = 'https://translate.googleapis.com/translate_a/single'

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)


def decode_bytes(raw):

    '''Best-effort text out of a subtitle file of unknown encoding.'''

    for encoding in ('utf-8', 'cp1253', 'latin-1'):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, ValueError):
            continue

    return raw.decode('utf-8', errors='replace')


def parse_srt(text):

    '''
    Returns [(index, start, end, text)] cues. Timestamps are kept verbatim;
    only cue text is ever translated.
    '''

    text = text.replace('\r\n', '\n').replace('\r', '\n')

    cues = []

    for block in re.split(r'\n\s*\n', text.strip()):
        lines = block.strip().split('\n')

        if len(lines) < 3 or '-->' not in lines[1]:
            continue

        try:
            index = int(lines[0].strip())
        except (TypeError, ValueError):
            continue

        start, _, end = lines[1].partition('-->')

        cues.append((index, start.strip(), end.strip(), '\n'.join(lines[2:])))

    return cues


def assemble_srt(cues):

    '''Serialises cues back to UTF-8 SRT bytes.'''

    out = []

    for index, start, end, text in cues:
        out.append('{0}\n{1} --> {2}\n{3}'.format(index, start, end, text))

    return ('\n\n'.join(out) + '\n').encode('utf-8')


def _translate_batch(session, texts, target):

    '''
    One request for up to BATCH cue texts, joined with a marker and split
    afterwards. Repeated q params do NOT batch (the server answers only the
    first), hence the delimiter.
    '''

    joined = SEP.join(texts)

    params = 'sl=en&tl={0}&dt=t&q={1}'.format(target, urllib.parse.quote(joined))

    response = session.get('{0}?client=gtx&{1}'.format(GTX, params), timeout=30)

    if response.status_code == 429:
        raise Exception('translation rate limited (HTTP 429)')

    if response.status_code != 200:
        raise Exception('translation failed (HTTP {0})'.format(response.status_code))

    data = json.loads(response.text)

    full = ''.join((seg[0] or '') for seg in (data[0] or []) if seg)

    return [part.strip() for part in full.split('<<<>>>')]


def translate_texts(texts, target='el', on_progress=None, is_cancelled=None):

    '''
    Translates cue texts, honouring cancellation between batches.

    Raises Cancelled when the user aborts, so Download.run treats it like
    dismissing the subtitle picker: quiet, no traceback.
    '''

    if not texts:
        return []

    sess = impersonate.session(timeout=30)

    if sess is None:
        raise Exception('translation needs script.module.curlcffi')

    translated = []

    try:

        batches = [texts[i:i + BATCH] for i in range(0, len(texts), BATCH)]

        for done, batch in enumerate(batches):

            if is_cancelled is not None and is_cancelled():
                raise Cancelled

            parts = _translate_batch(sess, batch, target)

            if len(parts) != len(batch):
                # Never silently misalign cues with translations: a partial
                # batch would shift every later subtitle out of sync.
                raise Exception(
                    'translation batch returned {0} parts for {1} cues'.format(
                        len(parts), len(batch)
                    )
                )

            translated.extend(parts)

            if on_progress is not None:
                on_progress(done + 1, len(batches))

    finally:

        impersonate.close(sess)

    return translated


def translate_srt(data, target='el', on_progress=None, is_cancelled=None):

    '''End to end: SRT bytes in one language, UTF-8 SRT bytes out in Greek.'''

    cues = parse_srt(decode_bytes(data))

    if not cues:
        raise Exception('no cues found in subtitle file')

    log_debug('Translator: {0} cues to translate'.format(len(cues)))

    translated = translate_texts(
        [cue[3] for cue in cues], target=target,
        on_progress=on_progress, is_cancelled=is_cancelled
    )

    return assemble_srt(
        [(cue[0], cue[1], cue[2], text) for cue, text in zip(cues, translated)]
    )
