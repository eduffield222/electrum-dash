#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2015 Thomas Voegtlin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import webbrowser

from util import *
from electrum_dash.i18n import _
from electrum_dash.plugins import run_hook


class FriendWidget(MyTreeWidget):

    def __init__(self, parent=None):
        MyTreeWidget.__init__(self, parent, self.create_menu, [_('Stars'), _('Username') , _('Addresses'), _('TLIP Support')], 2)
        self.config = self.parent.config
        self.setSortingEnabled(False)
        self.header().setResizeMode(1,2)
        self.header().setResizeMode(3,2)
        self.setIconSize(QSize(115,20))
        self.setIndentation(5)

    def update(self, items):
        self.clear()

        # desc = "  Stars: " + str(obj["stars"]) + "   |   Addresses In Stock:   " + str(len(obj["addresses"]))
        # item = QTreeWidgetItem([obj["username"], desc, _type])
        # item.setData(0, Qt.UserRole, key)
        # l.addTopLevelItem(item)

        for i in items:
            icon = QIcon(":icons/" + str(i["stars"]) + "_stars.png")

            item = QTreeWidgetItem( [ '', i["username"], str(len(i["addresses"])), "101,102,103"] )
            ## item.setFont(1, QFont(MONOSPACE_FONT)) ## this font is ugly
            ## item.setFont(2, QFont(MONOSPACE_FONT))
            ## item.setFont(3, QFont(MONOSPACE_FONT))

            if len(i["addresses"]) < 1:
                item.setForeground(3, QBrush(QColor("#BC1E1E")))
            else:
                item.setForeground(3, QBrush(QColor("#1EBC1E")))

            item.setIcon(0, icon)
            self.insertTopLevelItem(0, item)
            if i['current']:
                self.setCurrentItem(item)

        run_hook('contacts_tab_update')

    def create_menu(self, position):
        self.selectedIndexes()
        item = self.currentItem()
        if not item:
            return

        menu = QMenu()
        menu.addAction(_("Request More Addresses"), lambda: self.parent.request_more_addresses(str(item.data(1,0).toString())))
        menu.exec_(self.viewport().mapToGlobal(position))

