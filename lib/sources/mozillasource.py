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

import gobject
import userprofile
import exceptions, sys, os.path, ConfigParser, re, cPickle
import tempfile, types
import dirmonitor
import util

def dprint(fmt, *args):
    util.debug_print(util.DEBUG_MOZILLASOURCE, fmt % args)

class MozillaChange (userprofile.ProfileChange):
    (
        CREATED,
        DELETED,
        CHANGED
    ) = range (3)
    
    def __init__ (self, module, key, value, event):
        userprofile.ProfileChange.__init__ (self, module)
        
        assert self.event == CREATED or \
               self.event == DELETED or \
               self.event == CHANGED
        
        self.key   = key
        self.value = value
        self.event = event

    def get_id (self):
        return self.key

    def get_short_description (self):
        if self.event == CREATED:
            return "Mozilla key '%s' set to '%s'" % (self.key, self.value)
        elif self.event == DELETED:
            return "Mozilla key '%s' unset" % self.key
        else:
            return "Mozilla key '%s' changed to '%s'" % (self.key, self.value)

gobject.type_register (MozillaChange)

class MozillaSource (userprofile.ProfileSource):
    def __init__ (self, profile_storage):
        userprofile.ProfileSource.__init__ (self, "Mozilla")
        self.profile_storage = profile_storage

        self.ini_file = GetProfileIniFile()
        dprint("ini file = %s" % self.ini_file)

        # -----------------

    def commit_change (self, change):
        pass
    def start_monitoring (self):
        self.up = UserProfile(self.ini_file)
        self.up.open()
        self.up.get_profiles()
        self.default_path = self.up.get_default_path()
        dprint("start_monitoring: default_path = %s" % self.default_path)

        self.prefs_path = "%s/%s" % (self.default_path, "prefs.js")

        self.pref = JavascriptPrefsFile(self.prefs_path)
        self.pref.open()
        self.pref.kill_comments()
        self.pref.parse()
        self.prev_prefs = self.pref.get_prefs()
    
        # XXX - should this be in contructor instead?
        self.monitor = dirmonitor.DirectoryMonitor(
            os.path.dirname(self.prefs_path), self.__handle_monitor_event)
        self.monitor.start ()


    def __handle_monitor_event (self, path, event):
        if path == self.prefs_path:
            self.pref_file_changed()

    def pref_file_changed(self):
        pref = JavascriptPrefsFile(self.prefs_path)
        pref.open()
        pref.kill_comments()
        pref.parse()
        cur_prefs = pref.get_prefs()

        dc = DictCompare(self.prev_prefs, cur_prefs)
        dc.compare()
        cs = dc.get_change_set('a', 'b')
        #dump_change_set(cs)
        _add = cs['add']
        _del = cs['del']
        _mod = cs['mod']

        def emit_changes (self, items, event):
            for key, value in items:
                self.emit_change (MozillaChange (self, key, value, event))

        emit_changes (self, _add.items (), MozillaChange.CREATED)
        emit_changes (self, _del.items (), MozillaChange.DELETED)
        emit_changes (self, _mod.items (), MozillaChange.CHANGED)

        self.prev_prefs = cur_prefs

    def stop_monitoring (self):
        self.monitor.stop ()

    def sync_changes (self):
        pass
    def apply (self):
        pass

    def get_test_change (self, key, value):
        ret = MozillaChange (self, key, value)
        return ret

gobject.type_register (MozillaSource)
    
def get_source (profile_storage):
    return MozillaSource (profile_storage)

#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------

# ------ Globals ------

# XXX - Warning: this regular expression is not perfectly robust
# the 1st parameter is expected to be a double quoted string without
# commas in it nor escaped double quotes. The parsing of the 2nd parameter
# should be robust. For our expected input it should be fine. Really
# robust parsing would require tokeninzing the expression.
pref_re = re.compile("user_pref\s*\(\s*\"([^,\"]+)\s*\"\s*,\s*(.+?)\)\s*;\s*$", re.MULTILINE)

# ------ Excpetions ------

class FileNotFoundError(Exception):
    def __init__(self, filename):
        self.filename = filename
    def __str__(self):
        return "File Not Found (%s)" % self.filename
    
class BadIniFileError(Exception):
    def __init__(self, problem):
        self.problem = problem
    def __str__(self):
        return self.problem
    

# ------ Class DictCompare ------

class DictCompare:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def compare(self):
        ''' Given two dictionaries a,b analyze them for their
        differences and similarities.

        intersection - keys shared between a and b
        only_a       - keys only present in a
        only_b       - keys only present in b
        equal        - keys present in both a and b whole values are equal
        not_equal    - keys present in both a and b whole values are not equal'''

        self.keys_a = self.a.keys()
        self.keys_b = self.b.keys()
        
        self.intersection = []
        self.only_a = []
        self.only_b = []
        self.equal = []
        self.not_equal = []
        self._add = {}
        self._del = {}
        self._mod = {}

        for k in self.keys_a:
            if self.b.has_key(k):
                self.intersection.append(k)
            else:
                self.only_a.append(k)

        for k in self.keys_b:
            if not self.a.has_key(k):
                self.only_b.append(k)
                
        for k in self.intersection:
            if self.a[k] == self.b[k]:
                self.equal.append(k)
            else:
                self.not_equal.append(k)
                
    def intersection(self):
        'return list of keys shared between a and b'
        return self.intersection

    def only_a(self):
        'return list of keys only present in a'
        return self.only_a

    def only_b(self):
        'return list of keys only present in b'
        return self.only_b

    def equal(self):
        'return list of keys present in both a and b whole values are equal'
        return self.equal

    def not_equal(self):
        'return list of keys present in both a and b whole values are not equal'
        return self.not_equal

    def get_change_set(self, dict_lhs, dict_rhs):
        '''Return changes necessary to make dict_lhs equivalent to dict_rhs,
        (e.g. lhs = rhs), the two dictionary parameters are specified as
        either the string 'a' or the string 'b' corresponding to the parameters
        this class was created with.
        
        Return value is a dictionary with 3 keys (add, del, mod) whose values
        are dictionaries containing containing (key,value) pairs to add,
        delete, or modify respectively in dict_lhs.'''

        if dict_lhs == dict_rhs or dict_lhs not in "ab" or dict_rhs not in "ab":
            raise ValueError

        if dict_lhs == 'a':
            a = self.a
            b = self.b
            only_a = self.only_a
            only_b = self.only_b
        elif dict_lhs == 'b':
            a = self.b
            b = self.a
            only_a = self.only_b
            only_b = self.only_a
        else:
            raise ValueError

        self._add = {}
        for k in only_b:
            self._add[k] = b[k]

        self._del = {}
        for k in only_a:
            self._del[k] = a[k]

        self._mod = {}
        for k in self.not_equal:
            self._mod[k] = b[k]

        change_set = {'add':self._add, 'del':self._del, 'mod':self._mod}
        return change_set


    def is_equal(self):
        if len(self.only_a) == 0 and len(self.only_b) == 0 and len(self.not_equal) == 0:
            return True
        else:
            return False

    def dump(self):
        'Print the results of the dictionary comparision'
        dprint("intersection = %s" % ",".join(self.intersection))
        dprint("only a = %s" % ",".join(self.only_a))
        dprint("only b = %s" % ",".join(self.only_b))
        dprint("equal = %s" % ",".join(self.equal))
        dprint("not equal = %s" % ",".join(self.not_equal))


# ------ Class JavascriptPrefsFile ------

class JavascriptPrefsFile:
    def __init__(self, filepath):
        self.filepath = filepath

    def open(self):
        '''Constructors shouldn't do heavy processing or anything that might
        raise exceptions, its bad practice, so put the real work here in open.'''
        fd = open(self.filepath)
        self.filebuf = fd.read()
        fd.close()
        #dprint(self.filebuf)

    def kill_comments(self):
        slash_comment_re = re.compile("//.*$", re.MULTILINE)
        hash_comment_re = re.compile("#.*$", re.MULTILINE)
        c_comment_re = re.compile("/\*.*?\*/", re.MULTILINE | re.DOTALL)

        self.filebuf = slash_comment_re.sub("", self.filebuf)
        self.filebuf = hash_comment_re.sub("", self.filebuf)
        self.filebuf = c_comment_re.sub("", self.filebuf)

    def parse(self):
        start = 0;
        self.prefs = {}

        while 1:
            match = pref_re.search(self.filebuf, start)
            if match:
                key   = match.group(1)
                value = match.group(2)
                dprint("(%d:%d) key='%s' value='%s'" % (match.start(), match.end(), key, value))
                self.prefs[key] = value
                start = match.end()
            else:
                break

    def get_prefs(self):
        return self.prefs.copy()

    def dump_prefs(self):
        keys = self.prefs.keys()
        keys.sort()
        for key in keys:
            dprint("%s=%s" % (key, self.prefs[key]))


# ------ Class UserProfile ------

class UserProfile:
    def __init__(self, ini_file_path):
        self.ini_file_path = ini_file_path

    def open(self):
        '''Constructors shouldn't do heavy processing or anything that might
        raise exceptions, its bad practice, so put the real work here in open.'''
        self.ini = ConfigParser.ConfigParser()
        self.ini.read(self.ini_file_path)
        self.profiles = {}
        self.default = None

    def get_profiles(self):
        profile_re = re.compile("^Profile(\d+)$")

        nummatches = 0
        lastmatch_name = None
        
        for section in self.ini.sections():
            match = profile_re.match(section)
            if match:
                name = self.ini.get(section, "Name")
                path = self.ini.get(section, "Path")
                try:
                    default = self.ini.get(section, "default")
                except ConfigParser.NoOptionError:
                    default = None
                
                if name in self.profiles:
                    raise BadIniFileError("duplicate name (%s) in section %s" % (name, section))
                profile = {}
                self.profiles[name] = profile
                profile["section"] = section
                profile["path"] = path
                if default:
                    if self.default:
                        raise BadIniFileError("redundant default in section %s" % section)
                    self.default = name

                lastmatch_name = name
                nummatches = nummatches + 1

        if self.default == None and nummatches == 1:
            # If there's only one profile, its the default even if it doesn't have the Default=1 flag
            # (by default Firefox's auto-generated profile doesn't have the Default= flag)
            self.default = lastmatch_name
            dprint("defaulting to the only choice")
            
        
    def get_default_path(self):
        if not self.default:
            raise BadIniFileError("no default profile")
        path = self.profiles[self.default]["path"]
        fullpath = "%s/%s" % (os.path.dirname(self.ini_file_path), path)
        if not os.path.exists(fullpath):
            raise BadIniFileError("default path (%s) does not exist" % fullpath)
        if not os.path.isdir(fullpath):
            raise BadIniFileError("default path (%s) is not a directory" % fullpath)
        return fullpath


# ------ Utility Functions ------

# XXX - this needs more logic to distinquish mozilla, firefox, versions, etc.
# basically its just hardcoded at the moment.
def GetProfileIniFile():
    filename = os.path.expanduser("~/.mozilla/firefox/profiles.ini")

    # XXX - should caller thow error instead?
    if not os.path.exists(filename):
        raise FileNotFoundError(filename)

    return(filename)

def write_dict(dict, filepath):
    fd = open(filepath, 'w')
    cPickle.dump(dict, fd, True)
    fd.close()

def read_dict(filepath):
    fd = open(filepath)
    dict = cPickle.load(fd)
    fd.close()
    return dict

def insert_prefs_into_file(filepath, prefs):
    (wfd, tmppath) = tempfile.mkstemp(dir=os.path.dirname(filepath))

    for line in open(filepath):
        wfd.write(line)

    for key, value in prefs.items():
        wfd.write("user_pref(\"%s\", %s);\n" % (key, value))

    wfd.close()
    os.rename(tmppath, filepath)

# XXX - this does not deal with comments
def remove_prefs_from_file(filepath, prefs):
    (wfd, tmppath) = tempfile.mkstemp(dir=os.path.dirname(filepath))

    for line in open(filepath):
        match = pref_re.search(line)
        if match:
            key = match.group(1)
            if type(prefs) is types.DictType:
                if not prefs.has_key(key):
                    wfd.write(line)
            elif type(prefs) is types.ListType:
                if not key in prefs:
                    wfd.write(line)
            else:
                raise ValueError
        else:
            wfd.write(line)

    wfd.close()
    os.rename(tmppath, filepath)


def dump_change_set(cs):
    _add = cs['add']
    _del = cs['del']
    _mod = cs['mod']

    if len(_add.keys()):
        drint("Key/Values to ADD")
        for k in _add.keys():
            dprint("    %s=%s" % (k, _add[k]))

    if len(_del.keys()):
        dprint("Keys to DELETE")
        for k in _del.keys():
            dprint("    %s=%s" % (k, _del[k]))

    if len(_mod.keys()):
        dpprint("Key/Values to Modify")
        for k in _mod.keys():
            dprint("    %s=%s" % (k, _mod[k]))

#-----------------------------------------------------------------------------

#
# Unit tests
#
def run_unit_tests ():
    test_prefs = {'foo':'"bar"', 'uno':'1'}

    dprint("In mozillaprofile tests")

    try:
        profile_ini_file = GetProfileIniFile()
    except FileNotFoundError, e:
        print "No such profile ini file: %s" % e.filename
        return

    dprint("ini file = %s" % profile_ini_file)

    up = UserProfile(profile_ini_file)
    up.open()
    up.get_profiles()
    default_path = up.get_default_path()
    dprint("default_path = %s" % default_path)

    prefs_path = "%s/%s" % (default_path, "prefs.js")

    # make sure we're working with a clean file copy
    remove_prefs_from_file(prefs_path, test_prefs)

    pref = JavascriptPrefsFile(prefs_path)
    pref.open()
    pref.kill_comments()
    pref.parse()
    prev_prefs = pref.get_prefs()
    
    insert_prefs_into_file(prefs_path, test_prefs)

    pref = JavascriptPrefsFile(prefs_path)
    pref.open()
    pref.kill_comments()
    pref.parse()
    cur_prefs = pref.get_prefs()

    dc = DictCompare(prev_prefs, cur_prefs)
    dc.compare()

    cs = dc.get_change_set('a', 'b')
    dprint("a <-- b")
    dump_change_set(cs)

    dc = DictCompare(test_prefs, cs['add'])
    dc.compare()
    assert dc.is_equal() == True

    test_prefs['newkey'] = 'new'
    dc = DictCompare(test_prefs, cs['add'])
    dc.compare()
    assert dc.is_equal() == False

    del test_prefs['newkey']
    dc = DictCompare(test_prefs, cs['add'])
    dc.compare()
    assert dc.is_equal() == True

    test_prefs['uno'] = '2'
    dc = DictCompare(test_prefs, cs['add'])
    dc.compare()
    assert dc.is_equal() == False

    remove_prefs_from_file(prefs_path, test_prefs)


