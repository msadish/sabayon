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

if __name__ == '__main__':
    import os
    import sys
    import gtk

    if os.geteuid () != 0:
        errordialog = gtk.MessageDialog (None,
                                         gtk.DIALOG_DESTROY_WITH_PARENT,
                                         gtk.MESSAGE_ERROR,
                                         gtk.BUTTONS_CLOSE,
                                         "Your account does not have permissions to run %s" % "sabayon")
        errordialog.format_secondary_text ("Administrator level permissions are needed to run "
                                           "this program because it can modify system files.")
        errordialog.run ()
        errordialog.destroy ()
        sys.exit (1)
                        
    import profilesdialog
    
    dialog = profilesdialog.ProfilesDialog ()

    gtk.main ()
