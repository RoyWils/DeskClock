from datetime import datetime

import gi

gi.require_versions({"Gdk": "4.0", "Gtk": "4.0", "Pango": "1.0"})
from gi.repository import Gdk, GLib, Gtk, Pango


class DeskClockWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application):
        super().__init__(application=app)
        self.set_title("DeskClock")
        self.set_default_size(1, -1)
        self.set_resizable(False)
        self.set_decorated(True)
        self.connect("close-request", self.on_close_request)

        self.is_locked = False
        self._install_css()

        header_bar = Gtk.HeaderBar()
        header_bar.set_show_title_buttons(True)
        header_bar.set_decoration_layout(":close")

        self.header_bar = header_bar

        self.lock_button = Gtk.Button()
        self.lock_button.set_icon_name("object-unlocked-symbolic")
        self.lock_button.set_tooltip_text("Lock window")
        self.lock_button.connect("clicked", self.on_lock_clicked)
        header_bar.pack_end(self.lock_button)

        self.set_titlebar(header_bar)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        box.set_margin_top(3)
        box.set_margin_bottom(3)
        box.set_margin_start(3)
        box.set_margin_end(3)

        # Keep the clock/date block visually centered inside the circular lock view.
        top_spacer = Gtk.Box()
        top_spacer.set_vexpand(True)

        bottom_spacer = Gtk.Box()
        bottom_spacer.set_vexpand(True)

        self.clock_label = Gtk.Label()
        self.clock_label.add_css_class("title-1")
        self.clock_label.set_halign(Gtk.Align.CENTER)
        self.clock_label.set_tooltip_text("Double-click to unlock when locked")
        clock_attributes = Pango.AttrList()
        clock_attributes.insert(Pango.attr_scale_new(1.125))
        self.clock_label.set_attributes(clock_attributes)

        self.date_label = Gtk.Label()
        self.date_label.add_css_class("title-1")
        self.date_label.set_halign(Gtk.Align.CENTER)
        date_attributes = Pango.AttrList()
        date_attributes.insert(Pango.attr_scale_new(0.5625))
        self.date_label.set_attributes(date_attributes)

        click = Gtk.GestureClick.new()
        click.connect("released", self.on_clock_released)
        self.clock_label.add_controller(click)

        box.append(top_spacer)
        box.append(self.clock_label)
        box.append(self.date_label)
        box.append(bottom_spacer)

        self.content_box = box
        self.set_child(box)
        self.set_opacity(0.615)

        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_controller)

        self.update_clock()
        GLib.timeout_add_seconds(1, self.update_clock)

    def _install_css(self) -> None:
        # Lock mode uses a transparent window layer plus one circular content surface.
        css = Gtk.CssProvider()
        css.load_from_data(
            b"""
            .lock-window {
                background-color: transparent;
                border: none;
                outline: none;
                box-shadow: none;
            }

            .locked-circle {
                border-radius: 9999px;
                background-color: alpha(@theme_fg_color, 0.16);
                padding: 16px;
            }
            """
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def update_clock(self) -> bool:
        now = datetime.now()
        self.clock_label.set_label(now.strftime("%H:%M:%S"))
        self.date_label.set_label(now.strftime("%-d %b %Y"))
        return True

    def on_close_request(self, _window: Gtk.ApplicationWindow) -> bool:
        self.get_application().quit()
        return False

    def on_lock_clicked(self, _button: Gtk.Button) -> None:
        self.set_locked(not self.is_locked)

    def set_locked(self, locked: bool) -> None:
        self.is_locked = locked
        # Hide app chrome while locked without toggling decorations,
        # which can trigger compositor-driven window re-positioning.
        self.header_bar.set_visible(not locked)
        if locked:
            # Draw only the circular lock surface.
            self.set_opacity(1.0)
            self.add_css_class("lock-window")
            self.content_box.add_css_class("locked-circle")
            self.content_box.set_size_request(188, 188)
            self.content_box.set_overflow(Gtk.Overflow.HIDDEN)
        else:
            # Restore normal compact window presentation.
            self.set_opacity(0.615)
            self.remove_css_class("lock-window")
            self.content_box.remove_css_class("locked-circle")
            self.content_box.set_size_request(-1, -1)
            self.content_box.set_overflow(Gtk.Overflow.VISIBLE)
        self.lock_button.set_icon_name(
            "object-locked-symbolic" if locked else "object-unlocked-symbolic"
        )
        self.lock_button.set_tooltip_text("Unlock window" if locked else "Lock window")

    def on_clock_released(
        self, _gesture: Gtk.GestureClick, n_press: int, _x: float, _y: float
    ) -> None:
        if self.is_locked and n_press == 2:
            self.set_locked(False)

    def on_key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        state: Gdk.ModifierType,
    ) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.get_application().quit()
            return True

        if keyval == Gdk.KEY_l and state & Gdk.ModifierType.CONTROL_MASK:
            self.set_locked(not self.is_locked)
            return True

        return False


class DeskClockApplication(Gtk.Application):
    def __init__(self):
        # Use a stable application ID so desktop integration remains consistent.
        super().__init__(application_id="com.rwadmin.DeskClock")

    def do_activate(self):
        window = self.props.active_window
        if not window:
            window = DeskClockWindow(self)
        window.present()
