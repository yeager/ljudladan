"""Ljudlådan — Sound sensitivity tool."""

import gettext
import json
import locale
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from ljudladan import __version__
from ljudladan.export import show_export_dialog

try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass
for d in [Path(__file__).parent.parent / "po", Path("/usr/share/locale")]:
    if d.is_dir():
        locale.bindtextdomain("ljudladan", str(d))
        gettext.bindtextdomain("ljudladan", str(d))
        break
gettext.textdomain("ljudladan")
_ = gettext.gettext

APP_ID = "se.danielnylander.ljudladan"

SOUND_LEVELS = [
    ("🔇", "Silent", "No sound at all — completely quiet"),
    ("🔈", "Whisper", "Very quiet, like whispering"),
    ("🔉", "Normal", "Regular talking volume"),
    ("🔊", "Loud", "Loud sounds — TV, music"),
    ("📢", "Very loud", "Very loud — crowds, machines"),
    ("💥", "Overwhelming", "Too loud! Need to leave or use protection"),
]

SAFE_SOUNDS = [
    ("🌊", "Ocean waves", "Calm and repetitive"),
    ("🌧️", "Rain", "Gentle and soothing"),
    ("🎵", "Soft music", "Calm instrumental music"),
    ("🌲", "Forest", "Birds and wind in trees"),
    ("⏰", "White noise", "Steady background sound"),
    ("🫧", "Bubbles", "Soft popping sounds"),
]


def _config_dir():
    p = Path(GLib.get_user_config_dir()) / "ljudladan"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _load_log():
    path = _config_dir() / "log.json"
    if path.exists():
        try: return json.loads(path.read_text())
        except Exception: pass
    return []

def _save_log(log):
    (_config_dir() / "log.json").write_text(json.dumps(log[-200:], indent=2, ensure_ascii=False))


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=_("Sound Box"))
        self.set_default_size(450, 650)
        self.log = _load_log()

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        header = Adw.HeaderBar()
        main_box.append(header)

        export_btn = Gtk.Button(icon_name="document-save-symbolic", tooltip_text=_("Export (Ctrl+E)"))
        export_btn.connect("clicked", lambda *_: self._on_export())
        header.pack_end(export_btn)

        menu = Gio.Menu()
        menu.append(_("Export Log"), "win.export")
        menu.append(_("About Sound Box"), "app.about")
        menu.append(_("Quit"), "app.quit")
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        header.pack_end(menu_btn)

        ea = Gio.SimpleAction.new("export", None)
        ea.connect("activate", lambda *_: self._on_export())
        self.add_action(ea)

        ctrl = Gtk.EventControllerKey()
        ctrl.connect("key-pressed", self._on_key)
        self.add_controller(ctrl)

        stack = Adw.ViewStack()
        switcher = Adw.ViewSwitcherBar()
        switcher.set_stack(stack)
        switcher.set_reveal(True)

        # Sound level page
        level_page = self._build_level_page()
        stack.add_titled(level_page, "level", _("Sound Level"))
        stack.get_page(level_page).set_icon_name("audio-volume-high-symbolic")

        # Safe sounds page
        safe_page = self._build_safe_page()
        stack.add_titled(safe_page, "safe", _("Safe Sounds"))
        stack.get_page(safe_page).set_icon_name("audio-headphones-symbolic")

        main_box.append(stack)
        main_box.append(switcher)

        self.status = Gtk.Label(label="", xalign=0)
        self.status.add_css_class("dim-label")
        self.status.set_margin_start(12)
        self.status.set_margin_bottom(4)
        main_box.append(self.status)
        GLib.timeout_add_seconds(1, lambda: (self.status.set_label(GLib.DateTime.new_now_local().format("%Y-%m-%d %H:%M:%S")), True)[-1])

    def _on_key(self, ctrl, keyval, keycode, state):
        if state & Gdk.ModifierType.CONTROL_MASK and keyval in (Gdk.KEY_e, Gdk.KEY_E):
            self._on_export()
            return True
        return False

    def _on_export(self):
        show_export_dialog(self, self.log, _("Sound Box"), lambda m: self.status.set_label(m))

    def _build_level_page(self):
        scroll = Gtk.ScrolledWindow(vexpand=True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(16); box.set_margin_start(16); box.set_margin_end(16); box.set_margin_bottom(16)

        title = Gtk.Label(label=_("How loud is it right now?"))
        title.add_css_class("title-2")
        box.append(title)

        listbox = Gtk.ListBox()
        listbox.add_css_class("boxed-list")
        for emoji, name, desc in SOUND_LEVELS:
            row = Adw.ActionRow()
            row.set_title(f"{emoji} {_(name)}")
            row.set_subtitle(_(desc))
            row.set_activatable(True)
            row.connect("activated", self._on_level_select, name, emoji)
            listbox.append(row)
        box.append(listbox)
        scroll.set_child(box)
        return scroll

    def _on_level_select(self, row, name, emoji):
        from datetime import datetime
        self.log.append({"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "level": _(name), "emoji": emoji})
        _save_log(self.log)
        self.status.set_label(_("Logged: %s %s") % (emoji, _(name)))

    def _build_safe_page(self):
        scroll = Gtk.ScrolledWindow(vexpand=True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(16); box.set_margin_start(16); box.set_margin_end(16); box.set_margin_bottom(16)

        title = Gtk.Label(label=_("Sounds that help you feel calm"))
        title.add_css_class("title-2")
        box.append(title)

        listbox = Gtk.ListBox()
        listbox.add_css_class("boxed-list")
        for emoji, name, desc in SAFE_SOUNDS:
            row = Adw.ActionRow()
            row.set_title(f"{emoji} {_(name)}")
            row.set_subtitle(_(desc))
            listbox.append(row)
        box.append(listbox)
        scroll.set_child(box)
        return scroll


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.connect("activate", self._on_activate)

    def _on_activate(self, *_args):
        win = self.props.active_window or MainWindow(self)
        a = Gio.SimpleAction(name="about"); a.connect("activate", self._on_about); self.add_action(a)
        qa = Gio.SimpleAction(name="quit"); qa.connect("activate", lambda *_: self.quit()); self.add_action(qa)
        self.set_accels_for_action("app.quit", ["<Control>q"])
        win.present()

    def _on_about(self, *_args):
        dialog = Adw.AboutDialog(
            application_name=_("Sound Box"), application_icon=APP_ID, version=__version__,
            developer_name="Daniel Nylander", license_type=Gtk.License.GPL_3_0,
            website="https://www.autismappar.se",
            developers=["Daniel Nylander <daniel@danielnylander.se>"],
            comments=_("Sound sensitivity tool with custom sound profiles"),
        )
        dialog.present(self.props.active_window)


def main():
    app = App()
    return app.run()
