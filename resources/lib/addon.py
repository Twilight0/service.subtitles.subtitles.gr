# -*- coding: utf-8 -*-

'''
    Subtitles.gr
    Author Twilight0

        License summary below, for more details please read license.txt file

        This program is free software: you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 2 of the License, or
        (at your option) any later version.
        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.
        You should have received a copy of the GNU General Public License
        along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

from xbmc import getCleanMovieTitle

import re
from resources.lib import subtitlesgr, xsubstv, subzxyz
from resources.lib.tools import syshandle, sysaddon, langs

from tulip import control, workers
from tulip.compat import urlencode


class Search:

    def __init__(self):

        self.query = None
        self.list = []

    def run(self, query=None, rerun=False):

        if not 'Greek' in str(langs).split(','):

            control.directory(syshandle)
            control.infoDialog(control.lang(32002))

            return

        if query is None:

            if control.condVisibility('Player.HasVideo'):
                infolabel_prefix = 'VideoPlayer'
            else:
                infolabel_prefix = 'ListItem'

            title = control.infoLabel('{0}.Title'.format(infolabel_prefix))

            if re.search(r'[^\x00-\x7F]+', title) is not None:

                title = control.infoLabel('{0}.OriginalTitle'.format(infolabel_prefix))

            year = control.infoLabel('{0}.Year'.format(infolabel_prefix))

            tvshowtitle = control.infoLabel('{0}.TVshowtitle'.format(infolabel_prefix))

            season = control.infoLabel('{0}.Season'.format(infolabel_prefix))

            if len(season) == 1:
                season = '0' + season

            episode = control.infoLabel('{0}.Episode'.format(infolabel_prefix))

            if len(episode) == 1:
                episode = '0' + episode

            if 's' in episode.lower():
                season, episode = '0', episode[-1:]

            if tvshowtitle != '':  # episode
                if title and not rerun:
                    query = '{0} {1}'.format(tvshowtitle, title)
                else:
                    query = '{0} S{1} E{2}'.format(tvshowtitle, season, episode)
            elif year != '':  # movie
                query = '{0} ({1})'.format(title, year)
            else:  # file
                query, year = getCleanMovieTitle(title)
                if year != '':
                    query = '{0} ({1})'.format(query, year)

        self.query = query

        threads = [workers.Thread(self.xsubstv), workers.Thread(self.subzxyz), workers.Thread(self.subtitlesgr)]

        [i.start() for i in threads]

        for i in range(0, 10 * 2):
            try:
                is_alive = [x.is_alive() for x in threads]
                if all(x is False for x in is_alive):
                    break
                if control.aborted is True:
                    break
                control.sleep(500)
            except:
                pass

        if not self.list and not rerun:
            self.run(rerun=True)

        if len(self.list) == 0:
            control.directory(syshandle)
            return

        f = []

        f += [i for i in self.list if i['source'] == 'xsubstv']
        f += [i for i in self.list if i['source'] == 'subzxyz']
        f += [i for i in self.list if i['source'] == 'subtitlesgr']

        self.list = f

        for i in self.list:

            try:
                if i['source'] == 'subzxyz':
                    i['name'] = '[subzxyz] {0}'.format(i['name'])
                elif i['source'] == 'xsubstv':
                    i['name'] = '[xsubstv] {0}'.format(i['name'])
            except:
                pass

        for i in self.list:

            try:

                name, url, source, rating = i['name'], i['url'], i['source'], i['rating']

                u = {'action': 'download', 'url': url, 'source': source}
                u = '{0}?{1}'.format(sysaddon, urlencode(u))

                item = control.item(label='Greek', label2=name, iconImage=str(rating), thumbnailImage='el')
                item.setProperty('sync', 'false')
                item.setProperty('hearing_imp', 'false')

                control.addItem(handle=syshandle, url=u, listitem=item, isFolder=False)

            except Exception:

                pass

        control.directory(syshandle)

    def subtitlesgr(self):

        try:
            self.list.extend(subtitlesgr.subtitlesgr().get(self.query))
        except TypeError:
            pass

    def xsubstv(self):

        try:
            self.list.extend(xsubstv.xsubstv().get(self.query))
        except TypeError:
            pass

    def subzxyz(self):

        try:
            self.list.extend(subzxyz.subzxyz().get(self.query))
        except TypeError:
            pass


class Download:

    def __init__(self):

        pass

    def run(self, url, source):

        path = control.join(control.dataPath, 'temp')

        try:
            path = path.decode('utf-8')
        except Exception:
            pass

        control.deleteDir(control.join(path, ''), force=True)

        control.makeFile(control.dataPath)

        control.makeFile(path)

        if source == 'subtitlesgr':

            subtitle = subtitlesgr.subtitlesgr().download(path, url)

        elif source == 'xsubstv':

            subtitle = xsubstv.xsubstv().download(path, url)

        elif source == 'subzxyz':

            subtitle = subzxyz.subzxyz().download(path, url)

        elif source == 'tvsubtitlesgr':

            subtitle = None

        else:

            subtitle = None

        if subtitle is not None:

            item = control.item(label=subtitle)
            control.addItem(handle=syshandle, url=subtitle, listitem=item, isFolder=False)

        control.directory(syshandle)
