# -*- coding: utf-8 -*-

'''
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

from xbmcvfs import rename, File as openFile
from os.path import basename, split as os_split
from resources.lib.tools import multichoice
import zipfile, re
from tulip import control, client, log
from tulip.compat import unquote_plus, quote_plus, StringIO, urlopen, quote


class subtitlesgr:

    def __init__(self):

        self.list = []

    def get(self, query):

        try:

            filtered = ['freeprojectx', 'subs4series', u'Εργαστήρι Υποτίτλων']

            query = ' '.join(unquote_plus(re.sub('%\w\w', ' ', quote_plus(query))).split())

            url = 'http://www.subtitles.gr/search.php?name={0}&sort=downloads+desc'.format(quote_plus(query))

            result = client.request(url)

            result = result.decode('utf-8')

            items = client.parseDOM(result, 'tr', attrs={'on.+?': '.+?'})

        except Exception as e:

            log.log('Subtitles.gr failed at get function, reason: ' + str(e))

            return

        for item in items:

            try:

                if not 'flags/el.gif' in item:
                    raise Exception()

                try:
                    uploader = client.parseDOM(item, 'a', attrs={'class': 'link_from'})[0].strip()
                except:
                    uploader = 'other'

                if uploader in filtered:
                    raise Exception()

                if uploader == '':
                    uploader = 'other'

                try:
                    downloads = client.parseDOM(item, 'td', attrs={'class': 'latest_downloads'})[0]
                except:
                    downloads = '0'

                downloads = re.sub('[^0-9]', '', downloads)

                name = client.parseDOM(item, 'a', attrs={'onclick': 'runme.+?'})[0]
                name = ' '.join(re.sub('<.+?>', '', name).split())
                name = '[{0}] {1} [{2} DLs]'.format(uploader, name, downloads)
                name = client.replaceHTMLCodes(name)
                name = name.encode('utf-8')

                url = client.parseDOM(item, 'a', ret='href', attrs={'onclick': 'runme.+?'})[0]
                url = url.split('"')[0].split('\'')[0].split(' ')[0]
                url = client.replaceHTMLCodes(url)
                url = url.encode('utf-8')

                rating = self._rating(downloads)

                self.list.append({'name': name, 'url': url, 'source': 'subtitlesgr', 'rating': rating})

            except Exception as e:

                log.log('Subtitles.gr failed at self.list formation function, reason: ' + str(e))

                return

        return self.list

    def _rating(self, downloads):

        try:

            rating = int(downloads)

        except:

            rating = 0

        if rating < 100:
            rating = 1
        elif 100 <= rating < 200:
            rating = 2
        elif 200 <= rating < 300:
            rating = 3
        elif 300 <= rating < 400:
            rating = 4
        elif rating >= 400:
            rating = 5

        return rating

    def download(self, path, url):

        try:

            url = re.findall('/(\d+)/', url + '/', re.I)[-1]
            url = 'http://www.greeksubtitles.info/getp.php?id={0}'.format(url)
            url = client.request(url, output='geturl')

            data = urlopen(url, timeout=10).read()
            zip_file = zipfile.ZipFile(StringIO(data))
            files = zip_file.namelist()
            files = [i for i in files if i.startswith('subs/')]

            srt = [i for i in files if i.endswith(('.srt', '.sub'))]
            archive = [i for i in files if i.endswith(('.rar', '.zip'))]

            if len(srt) > 0:

                if len(srt) > 1:
                    srt = multichoice(srt)
                else:
                    srt = srt[0]

                result = zip_file.open(srt).read()

                subtitle = basename(srt)

                try:
                    subtitle = control.join(path, subtitle.decode('utf-8'))
                except Exception:
                    subtitle = control.join(path, subtitle)

                with open(subtitle, 'wb') as subFile:
                    subFile.write(result)

                return subtitle

            elif len(archive) > 0:

                if len(archive) > 1:
                    archive = multichoice(archive)
                else:
                    archive = archive[0]

                result = zip_file.open(archive).read()

                f = control.join(path, os_split(url)[1])

                with open(f, 'wb') as subFile:
                    subFile.write(result)

                dirs, files = control.listDir(path)

                if len(files) == 0:
                    return

                if zipfile.is_zipfile(f):

                    control.execute('Extract("{0}","{0}")'.format(f, path))

                if not zipfile.is_zipfile(f):

                    if control.infoLabel('System.Platform.Windows'):
                        uri = "rar://{0}/".format(quote(f))
                    else:
                        uri = "rar://{0}/".format(quote_plus(f))

                    dirs, files = control.listDir(uri)

                else:

                    dirs, files = control.listDir(path)

                if dirs and not zipfile.is_zipfile(f):

                    for dir in dirs:

                        _dirs, _files = control.listDir(control.join(uri, dir))

                        [files.append(control.join(dir, i)) for i in _files]

                        if _dirs:

                            for _dir in _dirs:
                                _dir = control.join(_dir, dir)

                                __dirs, __files = control.listDir(
                                    control.join(uri, _dir)
                                )

                                [files.append(control.join(_dir, i)) for i in __files]

                filenames = [i for i in files if i.endswith(('.srt', '.sub'))]

                filename = multichoice(filenames)

                try:

                    filename = filename.decode('utf-8')

                except Exception:

                    pass

                if not control.exists(control.join(path, os_split(filename)[0])) and not zipfile.is_zipfile(f):
                    control.makeFiles(control.join(path, os_split(filename)[0]))

                subtitle = control.join(path, filename)

                if not zipfile.is_zipfile(f):

                    content = openFile(uri + filename).read()

                    with open(subtitle, 'wb') as subFile:
                        subFile.write(content)

                result = control.join(os_split(subtitle)[0], 'subtitles.' + os_split(subtitle)[1].split('.')[1])

                rename(subtitle, result)

                return result

        except Exception as e:

            log.log('Subtitles.gr subtitle download failed for the following reason: ' + str(e))

            return