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

from xbmcvfs import File as openFile
from random import choice
from os.path import split
import zipfile, re, os, shutil
from tulip import control, client
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

        except:
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

            except:

                pass

        return self.list

    def _rating(self, downloads):

        try:
            rating = int(downloads)
        except:
            rating = 0

        if rating < 100:
            rating = 1
        elif rating >= 100 and rating < 200:
            rating = 2
        elif rating >= 200 and rating < 300:
            rating = 3
        elif rating >= 300 and rating < 400:
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
            srt = [i for i in files if any(i.endswith(x) for x in ['.srt', '.sub'])]
            rar = [i for i in files if any(i.endswith(x) for x in ['.rar', '.zip'])]

            if len(srt) > 0:

                result = zip_file.open(srt[0]).read()

                subtitle = os.path.basename(srt[0])

                try:
                    subtitle = control.join(path, subtitle.decode('utf-8'))
                except Exception:
                    subtitle = control.join(path, subtitle)

                with open(subtitle, 'wb') as subFile:
                    subFile.write(result)

                return subtitle

            elif len(rar) > 0:

                result = zip_file.open(rar[0]).read()

                # f = os.path.splitext(urlparse.urlparse(url).path)[1][1:]
                f = control.join(path, url.rpartition('/')[2])

                with open(f, 'wb') as subFile:
                    subFile.write(result)

                dirs, files = control.listDir(path)

                if len(files) == 0:
                    return

                if not f.lower().endswith('.rar'):
                    control.execute('Extract("{0}","{0}")'.format(f, path))

                if f.lower().endswith('.rar'):

                    if control.infoLabel('System.Platform.Windows'):
                        uri = "rar://{0}/".format(quote(f))
                    else:
                        uri = "rar://{0}/".format(quote_plus(f))

                    dirs, files = control.listDir(uri)

                else:

                    dirs, files = control.listDir(path)

                if dirs:

                    for dir in dirs:

                        _dirs, _files = control.listDir(control.join(uri if f.lower().endswith('.rar') else path, dir))

                        [files.append(control.join(dir, i)) for i in _files]

                        if _dirs:

                            for _dir in _dirs:
                                _dir += dir

                                __dirs, __files = control.listDir(
                                    control.join(uri if f.lower().endswith('.rar') else path, _dir))

                                [files.append(control.join(dir, i)) for i in __files]

                filenames = [i for i in files if i.endswith(('.srt', '.sub'))]

                if len(filenames) == 1:

                    filename = filenames[0]

                else:

                    choices = [split(i)[1] for i in filenames]

                    choices.insert(0, control.lang(32215))

                    _choice = control.selectDialog(heading=control.lang(32214), list=choices)

                    if _choice == 0:
                        filename = choice(filenames)
                    elif _choice != -1 and _choice <= len(filenames) + 1:
                        filename = filenames[_choice - 1]
                    else:
                        filename = choice(filenames)

                try:

                    filename = filename.decode('utf-8')

                except Exception:

                    pass

                if not control.exists(control.join(path, split(filename)[0])):
                    control.makeFiles(control.join(path, split(filename)[0]))

                subtitle = control.join(path, filename)

                if f.lower().endswith('.rar'):

                    content = openFile(uri + filename).read()

                    with open(subtitle, 'wb') as subFile:
                        subFile.write(content)

                    output = control.transPath(control.join('special://temp', split(filename)[1]))

                    shutil.move(subtitle, output)

                    shutil.rmtree(control.join(control.dataPath, 'temp'))

                    return output

                else:

                    output = control.transPath(control.join('special://temp', filename))

                    shutil.move(subtitle, output)

                    shutil.rmtree(control.join(control.dataPath, 'temp'))

                    return subtitle

        except:

            pass
