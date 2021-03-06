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
import gtk
import gtk.gdk
import xlib
import util
import debuglog

def dprint (fmt, *args):
    debuglog.debug_log (False, debuglog.DEBUG_LOG_DOMAIN_SESSION_WIDGET, fmt % args)
    
def session_window_subwindow_created_cb (xid, user_data):
    self = user_data

    dprint ("subwindow got created with xid %x", xid)

    self.xephyr_window = gtk.gdk.window_foreign_new_for_display (gtk.gdk.display_get_default (), xid)
    dprint ("gdk foreign window created, %s", self.xephyr_window)

class SessionWidget (gtk.Widget):
    # FIXME:
    #   Should be able override do_size_allocate() without this
    #   See bug #308099
    __gsignals__ = { 'size-allocate' : 'override' }
    
    def __init__ (self, session_width, session_height):
        gtk.Widget.__init__ (self)
        
        self.set_flags (self.flags() | gtk.NO_WINDOW)
        self.set_property ("can-focus", True)

        self.session_width  = session_width
        self.session_height = session_height

        self.xephyr_window = None

    def do_size_request (self, requisition):
        focus_width = self.style_get_property ("focus-line-width")
        focus_pad   = self.style_get_property ("focus-padding")
        
        requisition.width  = self.session_width  + 2 * focus_width + 2 * focus_pad
        requisition.height = self.session_height + 2 * focus_width + 2 * focus_pad

    def __calculate_position (self, allocation):
        focus_width = self.style_get_property ("focus-line-width")
        focus_pad   = self.style_get_property ("focus-padding")

        x = allocation.x + focus_width + focus_pad
        y = allocation.y + focus_width + focus_pad
            
        alloc_width  = allocation.width  - 2 * focus_width - 2 * focus_pad
        alloc_height = allocation.height - 2 * focus_width - 2 * focus_pad

        x += max (0, (alloc_width  - self.session_width)  / 2)
        y += max (0, (alloc_height - self.session_height) / 2)

        return (x, y)

    def do_size_allocate (self, allocation):
        self.allocation = allocation

        if self.flags() & gtk.REALIZED:
            (x, y) = self.__calculate_position (allocation)
            
            self.session_window.move_resize (x, y, self.session_width, self.session_height)
            self.input_window.move_resize   (x, y, self.session_width, self.session_height)

    def do_realize (self):
        gtk.Widget.do_realize (self)

        (x, y) = self.__calculate_position (self.allocation)

        self.session_window = gtk.gdk.Window (parent = self.get_parent_window (),
                                              window_type = gtk.gdk.WINDOW_CHILD,
                                              x = x,
                                              y = y,
                                              width  = self.session_width,
                                              height = self.session_height,
                                              wclass = gtk.gdk.INPUT_OUTPUT,
                                              visual = self.get_visual (),
                                              colormap = self.get_colormap (),
                                              event_mask = gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.SUBSTRUCTURE_MASK)
        self.session_window.set_user_data (self)
        dprint ("session window has xid %x", self.session_window.xid)

        # We use Xephyr's "-parent" option to tell it where to create
        # its window.  However, Xephyr does not use our window
        # directly for drawing.  Instead, it creates a subwindow in
        # our parent window, and uses *that*.  So, the events that we
        # proxy to Xephyr must be sent to the window that it creates.
        #
        # To get notified when Xephyr creates its window inside ours,
        # we select for gtk.gdk.SUBSTRUCTURE_MASK above.  However,
        # there's no GDK_* event for CreateNotify events.  In an ideal
        # world, we could just install a window event filter to
        # extract that event ourselves.
        #
        # However, PyGTK is buggy and doesn't implement
        # gdk_window_add_filter() correctly (see
        # http://bugzilla.gnome.org/show_bug.cgi?id=156948).  So, we
        # use our own wrapper for that function...
        xlib.window_capture_create_notify (self.session_window, session_window_subwindow_created_cb, self)

        event_mask = gtk.gdk.BUTTON_PRESS_MASK   | \
                     gtk.gdk.BUTTON_RELEASE_MASK | \
                     gtk.gdk.POINTER_MOTION_MASK | \
                     gtk.gdk.ENTER_NOTIFY_MASK   | \
                     gtk.gdk.LEAVE_NOTIFY_MASK   | \
                     gtk.gdk.KEY_PRESS_MASK      | \
                     gtk.gdk.KEY_RELEASE_MASK

        self.input_window = gtk.gdk.Window (parent = self.get_parent_window (),
                                            window_type = gtk.gdk.WINDOW_CHILD,
                                            x = x,
                                            y = y,
                                            width  = self.session_width,
                                            height = self.session_height,
                                            wclass = gtk.gdk.INPUT_ONLY,
                                            visual = self.get_visual (),
                                            colormap = self.get_colormap (),
                                            event_mask = event_mask)
        self.input_window.set_user_data (self)
        dprint ("Created input_only window for child session")

    def do_unrealize (self):
        # FIXME:
        #   Causes a warning with pygtk 2.6.2
        #   See bug #308384
        self.input_window.set_user_data (None)
        self.input_window.destroy ()
        dprint ("Destroyed input_only window for child session")
        
        self.session_window.set_user_data (None)
        self.session_window.destroy ()
        
        gtk.Widget.do_unrealize (self)

    def do_map (self):
        gtk.Widget.do_map (self)
        self.session_window.show ()
        self.input_window.show ()
        dprint ("Showed input_only window for child session")

    def do_unmap (self):
        self.input_window.hide ()
        self.session_window.hide ()
        gtk.Widget.do_unmap (self)
        dprint ("Hid input_only window for child session")

    def do_expose_event (self, event):
        if self.flags() & gtk.HAS_FOCUS:
            focus_width = self.style_get_property ("focus-line-width")
            focus_pad   = self.style_get_property ("focus-padding")
            
            (x, y) = self.__calculate_position (self.allocation)

            self.style.paint_focus (self.window,
                                    self.state,
                                    event.area,
                                    self,
                                    "sabayon-session",
                                    x - focus_width - focus_pad,
                                    y - focus_width - focus_pad,
                                    self.session_width  + 2 * focus_width + 2 * focus_pad,
                                    self.session_height + 2 * focus_width + 2 * focus_pad)
        return False

    def __update_input_only_window (self):
        if not self.flags() & gtk.REALIZED:
            return
        
        if self.flags() & gtk.HAS_FOCUS:
            self.input_window.hide ()
            dprint ("Focus in: hiding input_only window for child session")
        else:
            self.input_window.show ()
            dprint ("Focus out: showing input_only window for child session")
            
    def do_focus_in_event (self, event):
        self.__update_input_only_window ()
        return gtk.Widget.do_focus_in_event (self, event)

    def do_focus_out_event (self, event):
        self.__update_input_only_window ()
        return gtk.Widget.do_focus_in_event (self, event)

    def do_button_press_event (self, event):
        if not self.flags() & gtk.HAS_FOCUS:
            self.grab_focus ()
            
        if not event.send_event:
            if self.xephyr_window:
                dprint ("Resending button press; button = %d, state = 0x%x", event.button, event.state)
                xlib.send_button_event (self.xephyr_window, True, event.time, event.button, event.state)
        
        return True
    
    def do_button_release_event (self, event):
        if not event.send_event:
            if self.xephyr_window:
                dprint ("Resending button release; button = %d, state = 0x%x", event.button, event.state)
                xlib.send_button_event (self.xephyr_window, False, event.time, event.button, event.state)
        
        return True

    def do_motion_notify_event (self, event):
        if not event.send_event:
            if self.xephyr_window:
                dprint ("Resending motion notify; x = %d, y = %d", event.x, event.y)
                xlib.send_motion_event (self.xephyr_window, event.time, event.x, event.y);
        
        return True
    
    def do_enter_notify_event (self, event):
        if not event.send_event:
            if self.xephyr_window:
                dprint ("Resending enter notify; x = %d, y = %d, detail = %d", event.x, event.y, event.detail)
                xlib.send_crossing_event (self.xephyr_window, False, event.time, event.x, event.y, event.detail);
        
        return True
    
    def do_leave_notify_event (self, event):
        if not event.send_event:
            if self.xephyr_window:
                dprint ("Resending leave notify; x = %d, y = %d, detail = %d", event.x, event.y, event.detail)
                xlib.send_crossing_event (self.xephyr_window, False, event.time, event.x, event.y, event.detail);
        
        return True
    
    def do_key_press_event (self, event):
        if not event.send_event:
            if self.xephyr_window:
                dprint ("Resending key press; keycode = 0x%x, state = 0x%x", event.hardware_keycode, event.state)
                xlib.send_key_event (self.xephyr_window, True, event.time, event.hardware_keycode, event.state)
        
        return True

    def do_key_release_event (self, event):
        if not event.send_event:
            if self.xephyr_window:
                dprint ("Resending key release; keycode = 0x%x, state = 0x%x", event.hardware_keycode, event.state)
                xlib.send_key_event (self.xephyr_window, False, event.time, event.hardware_keycode, event.state)
        
        return True

gobject.type_register (SessionWidget)
