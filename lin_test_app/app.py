from datetime import datetime
import json
import math
from pathlib import Path

import gi
from PIL import Image, ImageDraw

gi.require_versions({"Gdk": "4.0", "Gtk": "4.0", "Pango": "1.0"})
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Pango


class DeskClockWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application):
        super().__init__(application=app)
        self.set_title("DeskClock")
        self.set_default_size(1, -1)
        self.set_resizable(False)
        self.set_decorated(True)
        self.connect("close-request", self.on_close_request)

        self.is_locked = False
        self.uses_analog_display = self._load_display_mode()
        self._install_css()

        header_bar = Gtk.HeaderBar()
        header_bar.set_show_title_buttons(True)
        header_bar.set_decoration_layout(":close")

        self.header_bar = header_bar

        self.display_mode_button = Gtk.Button()
        self.display_mode_button.add_css_class("mode-toggle")
        self.display_mode_button.connect("clicked", self.on_display_mode_clicked)
        header_bar.pack_end(self.display_mode_button)

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

        self.analog_clock_size = 156
        self.analog_clock = Gtk.Picture()
        self.analog_clock.set_size_request(
            self.analog_clock_size,
            self.analog_clock_size,
        )
        self.analog_clock.set_halign(Gtk.Align.CENTER)
        self.analog_clock.set_tooltip_text("Double-click to unlock when locked")

        click = Gtk.GestureClick.new()
        click.connect("released", self.on_clock_released)
        self.clock_label.add_controller(click)

        analog_click = Gtk.GestureClick.new()
        analog_click.connect("released", self.on_clock_released)
        self.analog_clock.add_controller(analog_click)

        box.append(top_spacer)
        box.append(self.clock_label)
        box.append(self.date_label)
        box.append(self.analog_clock)
        box.append(bottom_spacer)

        self.content_box = box
        self.set_child(box)
        self.set_opacity(0.615)

        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_controller)

        self._update_display_mode_button()
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

            .mode-toggle {
                font-size: 0.85em;
                min-width: 24px;
                min-height: 24px;
                padding: 0;
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
        if self.uses_analog_display:
            self.analog_clock.set_paintable(self.render_analog_clock_texture(now))
        return True

    def _state_file_path(self) -> Path:
        return Path(GLib.get_user_config_dir()) / "deskclock" / "state.json"

    def _load_display_mode(self) -> bool:
        try:
            state_path = self._state_file_path()
            if not state_path.exists():
                return False

            with state_path.open("r", encoding="utf-8") as state_file:
                state = json.load(state_file)
            return bool(state.get("uses_analog_display", False))
        except Exception:
            return False

    def _save_display_mode(self) -> None:
        try:
            state_path = self._state_file_path()
            state_path.parent.mkdir(parents=True, exist_ok=True)
            with state_path.open("w", encoding="utf-8") as state_file:
                json.dump(
                    {"uses_analog_display": self.uses_analog_display},
                    state_file,
                )
        except Exception:
            return

    def render_analog_clock_texture(self, now: datetime) -> Gdk.Texture:
        target_size = self.analog_clock_size
        scale = 2
        size = target_size * scale
        center = size / 2
        radius = (size / 2) - 16

        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        face_color = (245, 245, 245, 28)
        major_mark_color = (248, 248, 248, 220)
        minor_mark_color = (240, 240, 240, 120)
        hand_color = (248, 248, 248, 236)
        second_color = (255, 150, 150, 222)

        draw.ellipse(
            (center - radius, center - radius, center + radius, center + radius),
            outline=major_mark_color,
            width=4,
            fill=face_color,
        )
        draw.ellipse(
            (
                center - (radius - 6),
                center - (radius - 6),
                center + (radius - 6),
                center + (radius - 6),
            ),
            outline=(255, 255, 255, 36),
            width=2,
        )

        for tick in range(60):
            angle = (2 * math.pi * tick / 60) - (math.pi / 2)
            outer_x = center + math.cos(angle) * radius
            outer_y = center + math.sin(angle) * radius
            inner_radius = radius - (18 if tick % 5 == 0 else 9)
            inner_x = center + math.cos(angle) * inner_radius
            inner_y = center + math.sin(angle) * inner_radius
            draw.line(
                ((inner_x, inner_y), (outer_x, outer_y)),
                fill=major_mark_color if tick % 5 == 0 else minor_mark_color,
                width=4 if tick % 5 == 0 else 2,
            )

        second_fraction = now.second + now.microsecond / 1_000_000
        minute_fraction = now.minute + second_fraction / 60
        hour_fraction = (now.hour % 12) + minute_fraction / 60

        hour_angle = (hour_fraction * math.pi / 6) - (math.pi / 2)
        minute_angle = (minute_fraction * math.pi / 30) - (math.pi / 2)
        second_angle = (second_fraction * math.pi / 30) - (math.pi / 2)

        def hand_endpoint(angle: float, length: float) -> tuple[float, float]:
            return (
                center + math.cos(angle) * length,
                center + math.sin(angle) * length,
            )

        draw.line(
            (center, center, *hand_endpoint(hour_angle, radius * 0.5)),
            fill=hand_color,
            width=8,
        )
        draw.line(
            (center, center, *hand_endpoint(minute_angle, radius * 0.72)),
            fill=hand_color,
            width=6,
        )
        draw.line(
            (center, center, *hand_endpoint(second_angle, radius * 0.84)),
            fill=second_color,
            width=3,
        )

        draw.ellipse(
            (center - 7, center - 7, center + 7, center + 7),
            fill=hand_color,
        )

        image = image.resize(
            (target_size, target_size),
            Image.Resampling.LANCZOS,
        )

        bytes_data = GLib.Bytes.new(image.tobytes())
        pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
            bytes_data,
            GdkPixbuf.Colorspace.RGB,
            True,
            8,
            target_size,
            target_size,
            target_size * 4,
        )
        return Gdk.Texture.new_for_pixbuf(pixbuf)

    def on_close_request(self, _window: Gtk.ApplicationWindow) -> bool:
        self.get_application().quit()
        return False

    def on_lock_clicked(self, _button: Gtk.Button) -> None:
        self.set_locked(not self.is_locked)

    def on_display_mode_clicked(self, _button: Gtk.Button) -> None:
        self.uses_analog_display = not self.uses_analog_display
        self._save_display_mode()
        self._update_display_mode_button()
        if self.uses_analog_display:
            self.analog_clock.set_paintable(
                self.render_analog_clock_texture(datetime.now())
            )

    def _update_display_mode_button(self) -> None:
        if self.uses_analog_display:
            self.display_mode_button.set_label("D")
            self.display_mode_button.set_tooltip_text("Switch to digital clock")
            self.clock_label.set_visible(False)
            self.date_label.set_visible(False)
            self.analog_clock.set_visible(True)
        else:
            self.display_mode_button.set_label("A")
            self.display_mode_button.set_tooltip_text("Switch to analog clock")
            self.clock_label.set_visible(True)
            self.date_label.set_visible(True)
            self.analog_clock.set_visible(False)

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
