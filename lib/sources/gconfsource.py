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

import os
import os.path
import shutil
import time
import util
import errno
import gobject
import gconf
import userprofile
import storage

def dprint (fmt, *args):
    util.debug_print (util.DEBUG_GCONFSOURCE, fmt % args)

# gconf_engine_associate_schema() isn't wrapped
def associate_schema (config_source, key, schema_key):
    os.system ("gconftool-2 --config-source='%s' --apply-schema %s %s" % (config_source, schema_key, key))

# No mapping for gconf_client_recursive_unset()
def recursive_unset (client, dir):
    for entry in client.all_entries (dir):
        client.unset (entry.key)
    for subdir in client.all_dirs (dir):
        recursive_unset (client, subdir)

def get_client_and_address_for_path (path):
    try:
        os.makedirs (path)
    except OSError, err:
        if err.errno != errno.EEXIST:
            raise err
    address = "xml:readwrite:" + path
    engine = gconf.engine_get_for_address ("xml:readwrite:" + path)
    return (gconf.client_get_for_engine (engine), address)

class GConfChange (userprofile.ProfileChange):
    """Encapsulates a change to a GConf key."""
    
    def __init__ (self, source, key, value):
        """Construct a GConfChange from a GConfEntry."""
        userprofile.ProfileChange.__init__ (self, source)
        self.key   = key
        self.value = value

    def get_id (self):
        """Return the path to the GConf key which changed."""
        return self.key

    def get_short_description (self):
        """Return a short description of the GConf key change."""
        if not self.value:
            return _("GConf key '%s' unset") % self.key
        elif self.value.type == gconf.VALUE_STRING:
            return _("GConf key '%s' set to string '%s'")  % (self.key, self.value.to_string ())
        elif self.value.type == gconf.VALUE_INT:
            return _("GConf key '%s' set to integer '%s'") % (self.key, self.value.to_string ())
        elif self.value.type == gconf.VALUE_FLOAT:
            return _("GConf key '%s' set to float '%s'")   % (self.key, self.value.to_string ())
        elif self.value.type == gconf.VALUE_BOOL:
            return _("GConf key '%s' set to boolean '%s'") % (self.key, self.value.to_string ())
        elif self.value.type == gconf.VALUE_SCHEMA:
            return _("GConf key '%s' set to schema '%s'")  % (self.key, self.value.to_string ())
        elif self.value.type == gconf.VALUE_LIST:
            return _("GConf key '%s' set to list '%s'")    % (self.key, self.value.to_string ())
        elif self.value.type == gconf.VALUE_PAIR:
            return _("GConf key '%s' set to pair '%s'")    % (self.key, self.value.to_string ())
        else:
            return _("GConf key '%s' set to '%s'")         % (self.key, self.value.to_string ())

gobject.type_register (GConfChange)

class GConfSource (userprofile.ProfileSource):
    """GConf user profile source."""
    
    def __init__ (self, storage):
        """Construct a GConfSource

        @storage: storage object
        """
        userprofile.ProfileSource.__init__ (self, _("GConf"), "get_gconf_delegate")

        self.storage          = storage
        self.home_dir         = util.get_home_dir ()
        self.client           = None
        self.notify_id        = 0
        self.defaults_client  = None
        self.mandatory_client = None

    def get_committing_client_and_address (self, mandatory):
        """Get a GConfClient using either .gconf.xml.defaults or
        .gconf.xml.mandatory (in the temporary profile location)
        as its source.

        mandatory: whether to get the mandatory or defaults source
        """
        if not mandatory:
            if not self.defaults_client:
                (client, address) = get_client_and_address_for_path (os.path.join (self.home_dir, ".gconf.xml.defaults"))
                self.defaults_client = client
                self.defaults_address = address
            return (self.defaults_client, self.defaults_address)
        else:
            if not self.mandatory_client:
                (client, address) = get_client_and_address_for_path (os.path.join (self.home_dir, ".gconf.xml.mandatory"))
                self.mandatory_client = client
                self.mandatory_address = address
            return (self.mandatory_client, self.mandatory_address)

    def commit_change (self, change, mandatory = False):
        """Commit a GConf change to the profile."""
        if userprofile.ProfileSource.commit_change (self, change, mandatory):
            return
        
        (client, address) = self.get_committing_client_and_address (mandatory)

        dprint ("Committing change to '%s' to '%s'" % (change.key, address))
        
        if change.value:
            client.set (change.key, change.value)
        else:
            client.unset (change.key)
        
    def start_monitoring (self):
        """Start monitoring for GConf changes. Note that this
        is seriously resource intensive as must load the value
        of all existing keys so that we can determine whether
        a write to the database resulted in an actual change
        in the value of the key.
        """
        if self.notify_id != 0:
            return
        
        def handle_notify (client, cnx_id, entry, self):
            dprint ("Got GConf notification on '%s'" % entry.key)
            value = None
            if not entry.get_is_default ():
                value = entry.value
            self.emit_change (GConfChange (self, entry.key, value))

        self.client = gconf.client_get_default ()
        self.client.add_dir ("/", gconf.CLIENT_PRELOAD_RECURSIVE)
        self.notify_id = self.client.notify_add ("/", handle_notify, self)

    def stop_monitoring (self):
        """Stop monitoring for GConf changes."""
        if self.notify_id == 0:
            return

        self.client.notify_remove (self.notify_id)
        self.notify_id = 0
        self.client.remove_dir ("/")
        self.client = None

    def sync_changes (self):
        """Ensure that all committed changes are saved to disk."""
        
        # FIXME: it would be nicer if we just wrote directly
        #        to the defaults and mandatory sources
        dprint ("Shutting down gconfd in order to sync changes to disk")
        os.system ("gconftool-2 --shutdown")
        time.sleep (1)

        self.storage.add (".gconf.xml.defaults", self.home_dir, self.name)
        self.storage.add (".gconf.xml.mandatory", self.home_dir, self.name)

    def apply (self):
        """Apply the profile by writing the default and mandatory
        sources location to ~/.gconf.path.defaults and
        ~/.gconf.path.mandatory.

        Note that $(sysconfdir)/gconf/2/path needs to contain
        something like the following in order for this to work:

        include $(HOME)/.gconf.path.mandatory
        xml:readwrite:$(HOME)/.gconf
        include $(HOME)/.gconf.path.defaults
        """
        def write_path_file (filename, source):
            """Write a GConf path file. First try writing to a
            temporary file and move it over the original. Failing
            that, write directly to the original.
            """
            dprint ("Writing GConf path file with '%s' to '%s'" % (source, filename))
            temp = filename + ".new"
            try:
                f = file (temp, "w")
            except:
                temp = None
                f = file (filename, "w")

            try:
                f.write (source + "\n")
                f.close ()
            except:
                if temp != None:
                    os.remove (temp)
                raise

            if temp != None:
                os.rename (temp, filename)

        self.storage.extract (".gconf.xml.defaults", self.home_dir, True)
        write_path_file (os.path.join (self.home_dir, ".gconf.path.defaults"),
                         "xml:readonly:" + os.path.join (self.home_dir, ".gconf.xml.defaults"))
        self.storage.extract (".gconf.xml.mandatory", self.home_dir, True)
        write_path_file (os.path.join (self.home_dir, ".gconf.path.mandatory"),
                         "xml:readonly:" + os.path.join (self.home_dir, ".gconf.xml.mandatory"))

        # FIXME: perhaps just kill -HUP it? It would really just be better
        #        if we could guarantee that there wasn't a gconfd already
        #        running.
        dprint ("Shutting down gconfd so it kill pick up new paths")
        os.system ("gconftool-2 --shutdown")

gobject.type_register (GConfSource)

def get_source (storage):
    return GConfSource (storage)

#
# Unit tests
#
def run_unit_tests ():
    storage.running_unit_tests = True
    
    main_loop = gobject.MainLoop ()

    source = get_source (storage.ProfileStorage ("GConfTest"))

    # Remove any stale path files
    try:
        os.remove (os.path.join (util.get_home_dir (), ".gconf.path.defaults"))
        os.remove (os.path.join (util.get_home_dir (), ".gconf.path.mandatory"))
    except:
        pass

    # Need to shutdown the daemon to ensure its not using stale paths
    os.system ("gconftool-2 --shutdown")
    time.sleep (1)

    # Make sure there's no stale keys from a previous run
    # FIXME: gconf_client_recursive_unset() has no wrapping
    # source.client.recursive_unset ("/tmp/test-gconfprofile")
    os.system ("gconftool-2 --recursive-unset /tmp/test-gconfprofile")
    time.sleep (1)

    global changes
    changes = []
    def handle_changed (source, change):
        global changes
        changes.append (change)
    source.connect ("changed", handle_changed)

    source.start_monitoring ()

    # Need to run the mainloop to get notifications.
    # The notification is only dispatched once the set
    # operation has complete
    # We poll after each set because otherwise GConfClient
    # will dispatch the two notifications for the same key
    def poll (main_loop):
        while main_loop.get_context ().pending ():
            main_loop.get_context ().iteration (False)
        
    source.client.set_bool ("/tmp/test-gconfprofile/t1", True)
    poll (main_loop)
    source.client.set_bool ("/tmp/test-gconfprofile/t1", False)
    poll (main_loop)
    source.client.set_bool ("/tmp/test-gconfprofile/t2", True)
    poll (main_loop)
    source.client.set_int ("/tmp/test-gconfprofile/t3", 3)
    poll (main_loop)
    
    source.stop_monitoring ()
    source.client = gconf.client_get_default ()
    
    assert len (changes) == 4
    assert changes[3].key == "/tmp/test-gconfprofile/t3"
    source.commit_change (changes[3])
    
    assert changes[2].key == "/tmp/test-gconfprofile/t2"
    source.commit_change (changes[2], True)
    
    assert changes[1].key == "/tmp/test-gconfprofile/t1"
    assert changes[0].key == "/tmp/test-gconfprofile/t1"

    # source.client.recursive_unset ("/tmp/test-gconfprofile")
    os.system ("gconftool-2 --recursive-unset /tmp/test-gconfprofile")
    
    source.sync_changes ()
    source.apply ()

    assert os.access (os.path.join (util.get_home_dir (), ".gconf.path.defaults"), os.F_OK)
    assert os.access (os.path.join (util.get_home_dir (), ".gconf.path.mandatory"), os.F_OK)

    # We need to clear the cache because GConfClient doesn't know
    # some new sources have been added to the sources stack so it
    # won't see the value we put in the mandatory source
    source.client.clear_cache ()
    
    entry = source.client.get_entry ("/tmp/test-gconfprofile/t3", "", False)
    assert entry.value
    assert entry.value.type == gconf.VALUE_INT
    assert entry.value.get_int () == 3
    assert not entry.get_is_default ()
    assert entry.get_is_writable ()
    
    entry = source.client.get_entry ("/tmp/test-gconfprofile/t2", "", False)
    assert entry.value
    assert entry.value.type == gconf.VALUE_BOOL
    assert entry.value.get_bool () == True
    assert not entry.get_is_default ()
    assert not entry.get_is_writable ()

    # Shutdown the daemon and remove the path files so we don't screw
    # too much with the running session
    os.system ("gconftool-2 --shutdown")
    time.sleep (1)

    os.remove (os.path.join (util.get_home_dir (), ".gconf.path.defaults"))
    os.remove (os.path.join (util.get_home_dir (), ".gconf.path.mandatory"))

    storage.running_unit_tests = False
