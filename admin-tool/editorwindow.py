#!/usr/bin/env python

#
# Copyright (C) 2005 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import gtk
import gtk.glade
import storage
import util
import aboutdialog
from config import *

def dprint (fmt, *args):
    util.debug_print (util.DEBUG_ADMINTOOL, fmt % args)

class ProfileModel (gtk.ListStore):
    (
        COLUMN_NAME,
        COLUMN_BITE_ME_GUIDO
    ) = range (2)

    def __init__ (self, storage):
        gtk.ListStore.__init__ (self, str)

        self.storage = storage
        self.reload ()

    def reload (self):
        self.clear ()
        for (source, name) in self.storage.list ():
            row = self.prepend ()
            self.set (row,
                      self.COLUMN_NAME, name)

class ProfileEditorWindow:
    def __init__ (self, profile_name, parent_window):
        self.profile_name = profile_name
        self.storage = storage.ProfileStorage (profile_name)
        
        glade_file = os.path.join (GLADEDIR, "sabayon.glade")
        self.xml = gtk.glade.XML (glade_file, "profile_editor_window")

        self.window = self.xml.get_widget ("profile_editor_window")
        self.window.set_icon_name ("sabayon")
        
        self.treeview = self.xml.get_widget ("profile_treeview")
        self.__setup_treeview ()

        self.treeview.connect ("key-press-event", self.__handle_key_press)

        self.save_item = self.xml.get_widget ("save_item")
        self.save_item.connect ("activate", self.__handle_save)
        
        self.close_item = self.xml.get_widget ("close_item")
        self.close_item.connect ("activate", self.__handle_close)

        self.delete_item = self.xml.get_widget ("delete_item")
        self.delete_item.connect ("activate", self.__handle_delete)
        self.delete_item.set_sensitive (False)

        self.clear_history_item = self.xml.get_widget ("clear_history_item")
        self.clear_history_item.connect ("activate", self.__handle_clear_history)

        self.about_item = self.xml.get_widget ("about_item")
        self.about_item.connect ("activate", self.__handle_about)

        self.window.set_transient_for (parent_window)
        self.window.show ()

    def __delete_currently_selected (self):
        (model, row) = self.treeview.get_selection ().get_selected ()
        if not row:
            return
    
        dprint ("Deleting '%s'", model[row][ProfileModel.COLUMN_NAME])

        self.storage.remove (model[row][ProfileModel.COLUMN_NAME])
        self.profile_model.reload ()

    def __handle_key_press (self, treeview, event):
        if event.keyval in (gtk.keysyms.Delete, gtk.keysyms.KP_Delete):
            self.__delete_currently_selected ()
        
    def __handle_save (self, item):
        self.storage.save ()

    def __handle_close (self, item):
        # FIXME: are you sure really, really want to close without saving ?
        self.window.destroy ()

    def __handle_delete (self, item):
        self.__delete_currently_selected ()
        
    def __handle_clear_history (self, item):
        self.storage.clear_revisions ()

    def __handle_about (self, item):
        aboutdialog.show_about_dialog (self.window)

    def __setup_treeview (self):
        self.profile_model = ProfileModel (self.storage)
        self.treeview.set_model (self.profile_model)
        
        self.treeview.get_selection ().set_mode (gtk.SELECTION_SINGLE)
        self.treeview.get_selection ().connect ("changed", self.__treeview_selection_changed)

        self.treeview.set_headers_visible (False)

        c = gtk.TreeViewColumn (_("Name"),
                                gtk.CellRendererText (),
                                text = ProfileModel.COLUMN_NAME)
        self.treeview.append_column (c)

    def __treeview_selection_changed (self, selection):
        (model, row) = selection.get_selected ()
        if not row:
            self.delete_item.set_sensitive (False)
            return

        dprint ("Selected '%s'", model[row][ProfileModel.COLUMN_NAME])

        self.delete_item.set_sensitive (True)
