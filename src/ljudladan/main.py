import os
"""Ljudlådan - Sound sensitivity training."""
import sys, os, json, gettext, locale
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk
from ljudladan import __version__
from ljudladan.accessibility import apply_large_text

TEXTDOMAIN = "ljudladan"
for p in [os.path.join(os.path.dirname(__file__), "locale"), "/usr/share/locale"]:
    if os.path.isdir(p):
        gettext.bindtextdomain(TEXTDOMAIN, p)
        locale.bindtextdomain(TEXTDOMAIN, p)
        break
gettext.textdomain(TEXTDOMAIN)
_ = gettext.gettext

CONFIG_DIR = os.path.join(GLib.get_user_config_dir(), "ljudladan")
SESSIONS_FILE = os.path.join(CONFIG_DIR, "sessions.json")

SOUND_CATEGORIES = [
    {"name": _("Nature"), "emoji": "\U0001f333", "sounds": [
        _("Rain"), _("Wind"), _("Birds singing"), _("Thunder"), _("Ocean waves")]},
    {"name": _("Animals"), "emoji": "\U0001f436", "sounds": [
        _("Dog barking"), _("Cat meowing"), _("Cow mooing"), _("Horse neighing"), _("Rooster crowing")]},
    {"name": _("Music"), "emoji": "\U0001f3b5", "sounds": [
        _("Piano"), _("Guitar"), _("Drums"), _("Violin"), _("Flute")]},
    {"name": _("Everyday"), "emoji": "\U0001f3e0", "sounds": [
        _("Doorbell"), _("Vacuum cleaner"), _("Alarm clock"), _("Traffic"), _("Phone ringing")]},
]

def _load_sessions():
    try:
        with open(SESSIONS_FILE) as f: return json.load(f)
    except: return []

def _save_sessions(s):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(SESSIONS_FILE, "w") as f: json.dump(s[-200:], f, ensure_ascii=False, indent=2)



def _settings_path():
    xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    d = os.path.join(xdg, "ljudladan")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "settings.json")

def _load_settings():
    p = _settings_path()
    if os.path.exists(p):
        import json
        with open(p) as f:
            return json.load(f)
    return {}

def _save_settings(s):
    import json
    with open(_settings_path(), "w") as f:
        json.dump(s, f, indent=2)

class SoundApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="se.danielnylander.ljudladan",
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        apply_large_text()
        win = self.props.active_window or SoundWindow(application=self)
        win.present()
        if not self.settings.get("welcome_shown"):
            self._show_welcome(win)


    def do_startup(self):
        Adw.Application.do_startup(self)
        for name, cb, accel in [
            ("quit", lambda *_: self.quit(), "<Control>q"),
            ("about", self._on_about, None),
            ("export", self._on_export, "<Control>e"),
        ]:
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", cb)
            self.add_action(a)
            if accel: self.set_accels_for_action(f"app.{name}", [accel])

    def _on_about(self, *_args):
        d = Adw.AboutDialog(application_name=_("Sound Box"), application_icon="ljudladan",
            version=__version__, developer_name="Daniel Nylander", website="https://www.autismappar.se",
            license_type=Gtk.License.GPL_3_0, developers=["Daniel Nylander"],
            copyright="\u00a9 2026 Daniel Nylander")
        d.present(self.props.active_window)

    def _on_export(self, *_args):
        w = self.props.active_window
        if w: w.do_export()


class SoundWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, default_width=500, default_height=650, title=_("Sound Box"))
        self.sessions = _load_sessions()
        self.volume = 30
        self._build_ui()

    def _build_ui(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(box)
        header = Adw.HeaderBar()
        box.append(header)

        menu = Gio.Menu()
        menu.append(_("Export"), "app.export")
        menu.append(_("About Sound Box"), "app.about")
        menu.append(_("Quit"), "app.quit")
        header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu))

        theme_btn = Gtk.Button(icon_name="weather-clear-night-symbolic",
                               tooltip_text=_("Toggle dark/light theme"))
        theme_btn.connect("clicked", self._toggle_theme)
        header.pack_end(theme_btn)

        # Volume control
        vol_box = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        vol_box.set_margin_top(12)
        vol_label = Gtk.Label(label=_("Volume:"))
        vol_label.add_css_class("title-4")
        vol_box.append(vol_label)
        self.vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
        self.vol_scale.set_value(self.volume)
        self.vol_scale.set_size_request(200, -1)
        self.vol_scale.connect("value-changed", self._on_volume_change)
        vol_box.append(self.vol_scale)
        self.vol_value = Gtk.Label(label=f"{self.volume}%")
        self.vol_value.add_css_class("title-4")
        vol_box.append(self.vol_value)
        box.append(vol_box)

        # Comfort rating
        comfort_box = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        comfort_box.set_margin_top(8)
        comfort_label = Gtk.Label(label=_("How does it feel?"))
        comfort_label.add_css_class("title-4")
        comfort_box.append(comfort_label)
        for emoji, rating in [("\U0001f600", "good"), ("\U0001f610", "okay"), ("\U0001f61f", "uncomfortable")]:
            btn = Gtk.Button(label=emoji)
            btn.add_css_class("flat")
            btn.connect("clicked", self._on_comfort, rating)
            comfort_box.append(btn)
        box.append(comfort_box)

        self.comfort_label = Gtk.Label(label="")
        self.comfort_label.add_css_class("dim-label")
        self.comfort_label.set_margin_top(4)
        box.append(self.comfort_label)

        # Sound categories
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_margin_top(12)
        cat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        cat_box.set_margin_start(16)
        cat_box.set_margin_end(16)

        for cat in SOUND_CATEGORIES:
            frame = Gtk.Frame()
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

            cat_label = Gtk.Label()
            cat_label.set_markup(f'{cat["emoji"]} <b>{cat["name"]}</b>')
            cat_label.add_css_class("title-3")
            cat_label.set_margin_top(8)
            inner.append(cat_label)

            flow = Gtk.FlowBox(max_children_per_line=3, selection_mode=Gtk.SelectionMode.NONE,
                                homogeneous=True, row_spacing=4, column_spacing=4)
            flow.set_margin_start(8)
            flow.set_margin_end(8)
            flow.set_margin_bottom(8)
            for sound in cat["sounds"]:
                btn = Gtk.Button(label=sound)
                btn.add_css_class("pill")
                btn.connect("clicked", self._on_play_sound, sound, cat["name"])
                flow.append(btn)
            inner.append(flow)
            frame.set_child(inner)
            cat_box.append(frame)

        scroll.set_child(cat_box)
        box.append(scroll)

        self.status_label = Gtk.Label(label="", xalign=0)
        self.status_label.add_css_class("dim-label")
        self.status_label.set_margin_start(12)
        self.status_label.set_margin_bottom(4)
        box.append(self.status_label)
        GLib.timeout_add_seconds(1, self._update_clock)

    def _on_volume_change(self, scale):
        self.volume = int(scale.get_value())
        self.vol_value.set_label(f"{self.volume}%")

    def _on_comfort(self, btn, rating):
        labels = {"good": _("Feels good!"), "okay": _("It is okay."), "uncomfortable": _("Too much!")}
        self.comfort_label.set_label(labels.get(rating, ""))
        from datetime import datetime
        self.sessions.append({"date": datetime.now().isoformat(), "volume": self.volume,
                               "comfort": rating})
        _save_sessions(self.sessions)

    def _on_play_sound(self, btn, sound, category):
        self.status_label.set_label(_("Playing: %s (volume: %d%%)") % (sound, self.volume))
        from datetime import datetime
        self.sessions.append({"date": datetime.now().isoformat(), "sound": sound,
                               "category": category, "volume": self.volume})
        _save_sessions(self.sessions)

    def do_export(self):
        from ljudladan.export import export_csv, export_json
        os.makedirs(CONFIG_DIR, exist_ok=True)
        ts = GLib.DateTime.new_now_local().format("%Y%m%d_%H%M%S")
        data = [{"date": s.get("date", ""), "details": s.get("sound", s.get("comfort", "")),
                 "result": f'vol:{s.get("volume", "")}'} for s in self.sessions]
        export_csv(data, os.path.join(CONFIG_DIR, f"export_{ts}.csv"))
        export_json(data, os.path.join(CONFIG_DIR, f"export_{ts}.json"))

    def _toggle_theme(self, *_args):
        mgr = Adw.StyleManager.get_default()
        mgr.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT if mgr.get_dark() else Adw.ColorScheme.FORCE_DARK)

    def _update_clock(self):
        self.status_label.set_label(GLib.DateTime.new_now_local().format("%Y-%m-%d %H:%M:%S"))
        return True


def main():
    app = SoundApp()
    app.run(sys.argv)

if __name__ == "__main__":
    main()

    # ── Welcome Dialog ───────────────────────────────────────

    def _show_welcome(self, win):
        dialog = Adw.Dialog()
        dialog.set_title(_("Welcome"))
        dialog.set_content_width(420)
        dialog.set_content_height(480)

        page = Adw.StatusPage()
        page.set_icon_name("ljudladan")
        page.set_title(_("Welcome to Sound Box"))
        page.set_description(_(
            "Explore sounds and practice sound sensitivity.\n\n✓ Categorized sound library\n✓ Adjustable volume levels\n✓ Gradual exposure training\n✓ Safe, controlled environment"
        ))

        btn = Gtk.Button(label=_("Get Started"))
        btn.add_css_class("suggested-action")
        btn.add_css_class("pill")
        btn.set_halign(Gtk.Align.CENTER)
        btn.set_margin_top(12)
        btn.connect("clicked", self._on_welcome_close, dialog)
        page.set_child(btn)

        box = Adw.ToolbarView()
        hb = Adw.HeaderBar()
        hb.set_show_title(False)
        box.add_top_bar(hb)
        box.set_content(page)
        dialog.present(win)

    def _on_welcome_close(self, btn, dialog):
        self.settings["welcome_shown"] = True
        _save_settings(self.settings)
        dialog.close()



# --- Fullscreen toggle (F11) ---
def _setup_fullscreen(window, app):
    """Add F11 fullscreen toggle."""
    from gi.repository import Gio
    if not app.lookup_action('toggle-fullscreen'):
        action = Gio.SimpleAction.new('toggle-fullscreen', None)
        action.connect('activate', lambda a, p: (
            window.unfullscreen() if window.is_fullscreen() else window.fullscreen()
        ))
        app.add_action(action)
        app.set_accels_for_action('app.toggle-fullscreen', ['F11'])


# --- Plugin system ---
import importlib.util
import os as _pos

def _load_plugins(app_name):
    """Load plugins from ~/.config/<app>/plugins/."""
    plugin_dir = _pos.path.join(_pos.path.expanduser('~'), '.config', app_name, 'plugins')
    plugins = []
    if not _pos.path.isdir(plugin_dir):
        return plugins
    for fname in sorted(_pos.listdir(plugin_dir)):
        if fname.endswith('.py') and not fname.startswith('_'):
            path = _pos.path.join(plugin_dir, fname)
            try:
                spec = importlib.util.spec_from_file_location(fname[:-3], path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                plugins.append(mod)
            except Exception as e:
                print(f"Plugin {fname}: {e}")
    return plugins
