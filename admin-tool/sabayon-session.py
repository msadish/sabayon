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
    import sys
    import gobject
    import protosession

    if os.geteuid () != 0:
        sys.stderr.write ("Your account does not have permissions to run sabayon-session.")
        sys.exit (1)

    if len (sys.argv) != 3:
        sys.stderr.write ("Usage: %s <username> <profile-file>\n" % sys.argv[0])
        sys.exit (1)
                                            
    (username, profile_file) = sys.argv[1:3]

    main_loop = gobject.MainLoop ()

    def handle_session_finished (session, main_loop):
        main_loop.quit ()

    session = protosession.ProtoSession (username, profile_file)
    session.connect ("finished", handle_session_finished, main_loop)
    session.start ()

    main_loop.run ()
