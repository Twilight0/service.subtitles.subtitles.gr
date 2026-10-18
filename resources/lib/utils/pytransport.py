# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    Pure-Python transport fallback (stdlib only: ssl, http.client).

    Used when script.module.curlcffi cannot be imported - notably on Android,
    where addon-dir .so files sit on a noexec mount and can never dlopen.
    curl_cffi stays the first choice wherever it loads; this only runs when
    impersonate.session() would otherwise return None and every caller would
    skip.

    What it is: a modernized handshake as far as stock ssl allows, which is
    what already passes Cloudflare's bar on new stacks (Kodi 22 ships Python
    3.14 + OpenSSL 3.x and resolves DoodStream with plain urllib, per Gujal00
    on ResolveURL#1509). Same idea, backported by hand to old stacks:
    Chrome150-ordered TLS 1.2 ciphers, ALPN, no legacy protocols, Chrome-ish
    header order - plus the non-JS User-Agent, which walks past Anubis on its
    own regardless of TLS.

    What it is not: impersonation. These cannot be expressed from Python and
    are accepted gaps: GREASE, curve/group order (stuck on the linked
    OpenSSL's defaults - 1.1.1 has no post-quantum KeyShare), TLS extension
    order, ECH, and HTTP/2 (http.client speaks 1.1, so ALPN offers http/1.1
    only - offering h2 without speaking it would break the handshake). If a
    host allowlists exact Chrome JA3 instead of just requiring a modern
    client, this fails and the log will say exactly where.

    Mirrors the curl_cffi session surface the providers use: get/post with
    .text/.content/.status_code, cookie seeding and persistence, redirects.

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

import gzip
import http.client as _http
import ssl as _ssl
import urllib.parse as _urlparse
import zlib as _zlib

try:
    from tulip.log import log as log_debug
except Exception:
    def log_debug(message):
        pass

# Chrome150's TLS 1.2 cipher order, in OpenSSL names (curl-impersonate v2.2.3).
# TLS 1.3 suites stay at the linked OpenSSL's defaults: Python exposes no
# set_ciphersuites, and the defaults are already the modern three.
CHROME150_CIPHERS = (
    'ECDHE-ECDSA-AES128-GCM-SHA256:'
    'ECDHE-RSA-AES128-GCM-SHA256:'
    'ECDHE-ECDSA-AES256-GCM-SHA384:'
    'ECDHE-RSA-AES256-GCM-SHA384:'
    'ECDHE-ECDSA-CHACHA20-POLY1305:'
    'ECDHE-RSA-CHACHA20-POLY1305:'
    'ECDHE-RSA-AES128-SHA:'
    'ECDHE-RSA-AES256-SHA:'
    'AES128-GCM-SHA256:'
    'AES256-GCM-SHA384:'
    'AES128-SHA:'
    'AES256-SHA'
)

MAX_REDIRECTS = 5


def _context():

    ctx = _ssl.SSLContext(_ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = True
    ctx.verify_mode = _ssl.CERT_REQUIRED

    try:
        ctx.load_default_certs()
    except Exception:
        pass

    try:
        ctx.set_ciphers(CHROME150_CIPHERS)
    except Exception as error:
        log_debug('Pytransport: cipher order refused ({0}), defaults kept'.format(error))

    try:
        ctx.set_alpn_protocols(['http/1.1'])
    except Exception:
        pass

    for flag in ('OP_NO_SSLv2', 'OP_NO_SSLv3', 'OP_NO_TLSv1',
                 'OP_NO_TLSv1_1', 'OP_NO_COMPRESSION'):
        try:
            ctx.options |= getattr(_ssl, flag)
        except Exception:
            pass

    try:
        ctx.minimum_version = _ssl.TLSVersion.TLSv1_2
    except Exception:
        pass

    try:
        import certifi

        ctx.load_verify_locations(cafile=certifi.where())
    except Exception:
        pass

    return ctx


class Response(object):

    def __init__(self, status_code, content, headers, url):
        self.status_code = status_code
        self.content = content
        self.headers = headers
        self.url = url

    @property
    def text(self):

        charset = 'utf-8'

        for key, value in self.headers:
            if key.lower() == 'content-type' and 'charset=' in value:
                charset = value.split('charset=')[-1].split(';')[0].strip() or charset
                break

        try:
            return self.content.decode(charset, errors='replace')
        except Exception:
            return self.content.decode('utf-8', errors='replace')


class Session(object):

    def __init__(self, cookie=None, user_agent=None, timeout=25):

        self.timeout = timeout
        self.headers = {'User-Agent': user_agent or 'Mozilla/5.0'}
        self.cookies = {}
        self._context = _context()

        if cookie:
            self.seed(cookie)

    def seed(self, cookie):

        for part in str(cookie).split(';'):
            part = part.strip()

            if '=' not in part:
                continue

            name, value = part.split('=', 1)
            name, value = name.strip(), value.strip()

            if name and value:
                self.cookies[name] = value

    def _store(self, headers):

        for key, value in headers:
            if key.lower() != 'set-cookie':
                continue

            first = value.split(';', 1)[0]

            if '=' in first:
                name, val = first.split('=', 1)
                name = name.strip()

                if name:
                    self.cookies[name.strip()] = val.strip()

    def _request(self, method, url, data=None, headers=None, timeout=None,
                 redirects=MAX_REDIRECTS):

        parts = _urlparse.urlsplit(url)
        timeout = timeout or self.timeout

        body = None

        if isinstance(data, dict):
            body = _urlparse.urlencode(data).encode('utf-8')
        elif isinstance(data, str):
            body = data.encode('utf-8')
        elif data is not None:
            body = data

        merged = {'User-Agent': self.headers.get('User-Agent', 'Mozilla/5.0')}

        if self.cookies:
            merged['Cookie'] = '; '.join(
                '{0}={1}'.format(k, v) for k, v in self.cookies.items()
            )

        if body is not None and method == 'POST':
            merged.setdefault('Content-Type', 'application/x-www-form-urlencoded')
            merged.setdefault('Content-Length', str(len(body)))

        merged.setdefault('Accept-Encoding', 'gzip, deflate')

        for key, value in (headers or {}).items():
            merged[key] = value

        if parts.scheme == 'https':
            connection = _http.HTTPSConnection(
                parts.hostname, parts.port or 443,
                context=self._context, timeout=timeout
            )
        else:
            connection = _http.HTTPConnection(
                parts.hostname, parts.port or 80, timeout=timeout
            )

        try:
            path = _urlparse.urlunsplit(('', '', parts.path or '/', parts.query, ''))
            connection.putrequest(method, path, skip_accept_encoding=True)

            for key, value in merged.items():
                connection.putheader(key, value)

            connection.endheaders(body)

            raw = connection.getresponse()
            content = raw.read()
            response_headers = raw.getheaders()
            status = raw.status

            encoding = (raw.getheader('Content-Encoding') or '').lower()

            if encoding == 'gzip' and content[:2] == b'\x1f\x8b':
                try:
                    content = gzip.decompress(content)
                except Exception:
                    pass
            elif encoding == 'deflate':
                try:
                    content = _zlib.decompress(content)
                except Exception:
                    try:
                        content = _zlib.decompress(content, -15)
                    except Exception:
                        pass

            self._store(response_headers)

            if status in (301, 302, 303, 307, 308) and redirects > 0:
                location = raw.getheader('Location')

                if location:
                    next_url = _urlparse.urljoin(url, location)

                    if status == 303 or (status in (301, 302) and method == 'POST'):
                        return self._request('GET', next_url, None, headers,
                                             timeout, redirects - 1)

                    return self._request(method, next_url, data, headers,
                                         timeout, redirects - 1)

            return Response(status, content, response_headers, url)
        finally:
            try:
                connection.close()
            except Exception:
                pass

    def get(self, url, headers=None, timeout=None):

        return self._request('GET', url, None, headers, timeout)

    def post(self, url, data=None, headers=None, timeout=None):

        return self._request('POST', url, data, headers, timeout)

    def close(self):

        pass


def session(cookie=None, user_agent=None, timeout=25):

    return Session(cookie=cookie, user_agent=user_agent, timeout=timeout)
