from nicegui import ui, app
from services import DressenseService
from ui_helpers import (
    get_feedback_reasons,
    season_options, occasion_options, color_swatch_html,
    garment_role_label,
    category_label, layer_role_label, occasion_tag_label,
    validate_hex_color,
    formality_preference_label, neutral_sensitivity_label,
    weight_label, format_weight,
)
from dataclasses import dataclass
from typing import Optional, Any

service = DressenseService()

@dataclass
class UIState:
    current_outfit: Optional[Any] = None
    season: str = "auto"
    occasion: Optional[Any] = None
    advanced_mode: bool = False
    dark_mode: bool = False
    active_tab: str = "generate"
    wardrobe_category_filter: str = "all"
    wardrobe_active_filter: str = "all"

state = UIState()

def _load_preferences():
    prefs = service.get_ui_preferences()
    state.dark_mode = prefs.get("dark_mode", False)
    state.advanced_mode = prefs.get("advanced_mode", False)

def on_startup():
    _load_preferences()

def on_shutdown():
    service.close()

APP_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
:root {
    --bg: #F5F1EB; --surface: #FDFAF6; --surface-muted: #EDE9E2;
    --text: #1C1917; --text-muted: #78716C; --border: #E2DDD7;
    --accent: #6B705C; --accent-light: #8A9070; --accent-contrast: #FFFFFF;
    --danger: #B45309; --success: #4D7C60; --nav-height: 64px;
}
body.theme-dark {
    --bg: #1C1917; --surface: #28251F; --surface-muted: #332E27;
    --text: #F5EFE6; --text-muted: #A8A29E; --border: #3D3730;
    --accent: #9DA882; --accent-light: #B3BC9B; --accent-contrast: #1C1917;
    --danger: #D97706; --success: #6DAB87;
}
body { background-color: var(--bg) !important; font-family: 'Inter', -apple-system, sans-serif; color: var(--text); transition: background-color .25s ease, color .25s ease; }
.nicegui-content, .q-page { width: 100% !important; display: flex !important; flex-direction: column !important; align-items: center !important; background-color: var(--bg) !important; }
.app-shell { width: 100%; display: flex; flex-direction: column; align-items: center; background-color: var(--bg); }
.app-header { padding: 1.25rem 1rem .5rem; width: 100%; max-width: 580px; box-sizing: border-box; }
.app-page { max-width: 580px; width: 100%; padding: 0 1rem calc(var(--nav-height) + 1.5rem); box-sizing: border-box; display: flex; flex-direction: column; align-items: stretch; }
.app-page > .nicegui-column { width: 100% !important; align-items: stretch !important; }
.app-card { background-color: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 1rem !important; box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important; color: var(--text) !important; }
.app-title { color: var(--accent); font-weight: 600; letter-spacing: -.5px; }
.section-title { color: var(--text); font-weight: 600; font-size: 1rem; }
.muted-text { color: var(--text-muted) !important; font-size: .8125rem; }
.app-button-primary { background-color: var(--accent) !important; color: var(--accent-contrast) !important; border-radius: 2rem !important; text-transform: none !important; font-weight: 500 !important; box-shadow: 0 2px 6px rgba(0,0,0,.15) !important; }
.app-button-outline { border: 1.5px solid var(--border) !important; color: var(--text) !important; border-radius: 2rem !important; text-transform: none !important; background: transparent !important; }
.q-card { border-radius: 1rem; }
.q-btn { text-transform: none; border-radius: 2rem; }
.q-chip { border-radius: 2rem; }
body.theme-dark .q-card { background-color: var(--surface) !important; color: var(--text) !important; }
body.theme-dark .q-dialog .q-card { background-color: var(--surface) !important; color: var(--text) !important; border: 1px solid var(--border); }
body.theme-dark .q-field__native, body.theme-dark .q-field__label, body.theme-dark .q-field__control, body.theme-dark .q-select__dropdown-icon { color: var(--text) !important; }
body.theme-dark .q-field--filled .q-field__control { background-color: var(--surface-muted) !important; }
body.theme-dark .q-menu,
body.theme-dark .q-virtual-scroll__content,
body.theme-dark .q-select__dialog,
body.theme-dark .q-popup-proxy > div { background-color: var(--surface) !important; color: var(--text) !important; border: 1px solid var(--border); }
body.theme-dark .q-item { color: var(--text) !important; background-color: var(--surface) !important; }
body.theme-dark .q-item:hover, body.theme-dark .q-item--active { background-color: var(--surface-muted) !important; }
body.theme-dark .q-expansion-item__content { background-color: var(--surface) !important; color: var(--text) !important; }
body.theme-dark .q-expansion-item__header { color: var(--text) !important; }
body.theme-dark .q-chip { background-color: var(--surface-muted) !important; color: var(--text) !important; }
.app-bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; z-index: 1000; background-color: var(--surface) !important; border-top: 1px solid var(--border); box-shadow: 0 -2px 12px rgba(0,0,0,.08); height: var(--nav-height); display: flex; align-items: center; justify-content: space-around; padding: 0 .5rem; }
.nav-item { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; flex: 1; cursor: pointer; padding: .5rem .25rem; border-radius: .75rem; transition: background .15s ease; min-height: 52px; }
.nav-item:hover { background-color: var(--surface-muted); }
.nav-item .nav-icon { font-size: 1.25rem; color: var(--text-muted); transition: color .15s ease; }
.nav-item.nav-active .nav-icon { color: var(--accent); }
.nav-item .nav-label { font-size: .6875rem; font-weight: 500; color: var(--text-muted); transition: color .15s ease; line-height: 1; }
.nav-item.nav-active .nav-label { color: var(--accent); }
.inactive-card { opacity: .65; }
.wardrobe-grid { display: grid; grid-template-columns: 1fr; gap: .75rem; }
@media (min-width: 480px) { .wardrobe-grid { grid-template-columns: 1fr 1fr; } }
.q-dialog__inner > .q-card { max-width: 520px !important; width: calc(100vw - 2rem) !important; border-radius: 1.25rem !important; }
.q-tab-panels { background: transparent !important; }
.q-tab-panel { padding: 0 !important; }
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
"""

def _apply_theme():
    if state.dark_mode:
        ui.run_javascript("document.body.classList.add('theme-dark')")
    else:
        ui.run_javascript("document.body.classList.remove('theme-dark')")


def build_bottom_nav(panels: dict):
    tabs_def = [
        ("generate", "auto_awesome", "Generate"),
        ("wardrobe",  "checkroom",   "Wardrobe"),
        ("add",       "add_circle",  "Add"),
        ("learning",  "insights",    "Learning"),
        ("settings",  "settings",    "Settings"),
    ]
    nav_container = ui.element("div").classes("app-bottom-nav")
    nav_items = {}

    def _switch(tab_key):
        state.active_tab = tab_key
        for k, p in panels.items():
            p.set_visibility(k == tab_key)
        _refresh_nav()

    def _refresh_nav():
        for key, el in nav_items.items():
            if key == state.active_tab:
                el.classes(add="nav-active")
            else:
                # remove active class manually
                el._props.pop("class", None)
                el.classes(remove="nav-active")
                el.update()

    with nav_container:
        for tab_key, icon_name, label in tabs_def:
            extra = " nav-active" if tab_key == state.active_tab else ""
            item_el = ui.element("div").classes(f"nav-item{extra}")
            item_el.on("click", lambda tk=tab_key: _switch(tk))
            nav_items[tab_key] = item_el
            with item_el:
                ui.icon(icon_name).classes("nav-icon")
                ui.label(label).classes("nav-label")


@ui.page("/")
def main_page():
    ui.add_head_html(f"<style>{APP_CSS}</style>")
    # Disable NiceGUI built-in dark so we manage it ourselves
    ui.dark_mode().disable()

    with ui.element("div").classes("app-shell"):
        with ui.element("div").classes("app-header"):
            ui.label("Dressense").classes("app-title text-2xl")

        panels: dict = {}

        with ui.column().classes("app-page items-stretch"):
            gen_panel = ui.column().classes("w-full items-stretch gap-4 pt-4")
            panels["generate"] = gen_panel
            with gen_panel:
                generate_content()

            ward_panel = ui.column().classes("w-full items-stretch gap-4 pt-4")
            panels["wardrobe"] = ward_panel
            ward_panel.set_visibility(False)
            with ward_panel:
                wardrobe_content()

            add_panel = ui.column().classes("w-full items-stretch gap-4 pt-4")
            panels["add"] = add_panel
            add_panel.set_visibility(False)
            with add_panel:
                add_garment_content()

            learn_panel = ui.column().classes("w-full items-stretch gap-4 pt-4")
            panels["learning"] = learn_panel
            learn_panel.set_visibility(False)
            with learn_panel:
                learning_content()

            settings_panel = ui.column().classes("w-full items-stretch gap-4 pt-4")
            panels["settings"] = settings_panel
            settings_panel.set_visibility(False)
            with settings_panel:
                settings_content()

        build_bottom_nav(panels)

    ui.timer(0.05, _apply_theme, once=True)


# ── Generate ─────────────────────────────────────────────────────────────────
def generate_content():
    season_select = ui.select(
        label="Season",
        options={val: label for val, label in season_options()},
        value=state.season
    ).classes("w-full").props("filled dense")

    ui.element("div").classes("h-2")

    ui.button(
        "Generate outfit", icon="auto_awesome",
        on_click=lambda: open_occasion_modal()
    ).classes("w-full app-button-primary py-3")

    outfit_container = ui.column().classes("w-full gap-3")

    def update_outfit_display():
        outfit_container.clear()
        if state.current_outfit is None:
            with outfit_container:
                ui.label("No outfit generated yet.").classes("muted-text text-center p-6")
            return
        details = service.get_outfit_details(state.current_outfit)
        garments = details["garments"]
        micro_palette = details["micro_palette"]
        with outfit_container:
            with ui.card().classes("app-card w-full p-5"):
                with ui.row().classes("gap-2 justify-center mb-3"):
                    for hex_color in micro_palette:
                        ui.html(color_swatch_html(hex_color, "26px"))
                ui.label("Today\u2019s outfit").classes("section-title text-center mb-1")
                for g in garments:
                    with ui.row().classes("items-center gap-3 py-2"):
                        ui.html(color_swatch_html(g["color_hex"], "20px"))
                        with ui.column().classes("flex-1 gap-0"):
                            ui.label(g["name"]).classes("font-medium text-sm")
                            ui.label(g.get("category", "")).classes("muted-text")
                        ui.label(garment_role_label(g)).classes("text-xs px-2 py-1 rounded-full").style(
                            "background:var(--surface-muted); color:var(--text-muted);"
                        )
                with ui.expansion("Details", icon="info").classes("w-full mt-2"):
                    resolved_season_label = service.resolve_season_label(state.season)
                    occasion_label = (
                        dict(occasion_options()).get(state.occasion, state.occasion)
                        if state.occasion else "None"
                    )
                    ui.label(f"Season: {resolved_season_label}").classes("text-sm")
                    ui.label(f"Occasion: {occasion_label}").classes("text-sm")
                    ui.label(f"Total warmth: {details['total_warmth']}").classes("text-sm")
                    ui.label(f"Average formality: {details['avg_formality']}").classes("text-sm")
                    if state.advanced_mode and details["score"] is not None:
                        ui.label(f"Score: {details['score']}").classes("text-sm font-medium mt-1")
                        try:
                            bd = service.get_outfit_context_breakdown(
                                state.current_outfit, state.season, state.occasion
                            )
                            for k, lbl in [
                                ("season_adjustment", "Season adj."),
                                ("occasion_tag_adjustment", "Occasion tag adj."),
                                ("occasion_formality_adjustment", "Occasion formality adj."),
                                ("pair_penalties", "Pair penalties"),
                                ("recently_worn_penalty", "Recently worn penalty"),
                            ]:
                                if bd.get(k, 0) != 0:
                                    ui.label(f"{lbl}: {bd[k]:+.3f}").classes("muted-text text-xs")
                        except Exception:
                            pass
                with ui.row().classes("justify-center gap-4 mt-3"):
                    ui.button(icon="thumb_up", on_click=lambda: positive_feedback()).props(
                        "flat round"
                    ).style("color: var(--success)")
                    ui.button(icon="thumb_down", on_click=lambda: negative_feedback()).props(
                        "flat round"
                    ).style("color: var(--danger)")

    def positive_feedback():
        if state.current_outfit is None:
            return
        service.submit_feedback(state.current_outfit, liked=True)
        with ui.dialog() as dialog, ui.card().classes("app-card p-5"):
            ui.label("Glad it works.").classes("section-title mb-1")
            ui.label("Mark as worn today?").classes("muted-text mb-4")
            with ui.row().classes("gap-3 justify-end"):
                def mark_and_close():
                    service.mark_outfit_worn(state.current_outfit)
                    ui.notify("Outfit marked as worn", type="positive")
                    dialog.close()
                ui.button("Yes, mark as worn", on_click=mark_and_close).classes("app-button-primary")
                ui.button("Not now", on_click=dialog.close).props("flat")
        dialog.open()

    def negative_feedback():
        if state.current_outfit is None:
            return
        with ui.dialog() as dialog, ui.card().classes("app-card p-5 w-full"):
            ui.label("What didn\u2019t you like?").classes("section-title mb-3")
            with ui.row().classes("gap-2 flex-wrap"):
                for value, label in get_feedback_reasons():
                    def submit(v=value, d=dialog):
                        service.submit_feedback(state.current_outfit, liked=False, reason=v)
                        d.close()
                        ui.notify("Feedback saved", type="positive")
                        with ui.dialog() as gen_dialog, ui.card().classes("app-card p-5"):
                            ui.label("Feedback saved.").classes("mb-4")
                            ui.button(
                                "Generate another",
                                on_click=lambda: [gen_dialog.close(), open_occasion_modal()]
                            ).classes("app-button-primary")
                        gen_dialog.open()
                    ui.button(label, on_click=submit).classes("app-button-outline text-sm")
        dialog.open()

    def open_occasion_modal():
        state.season = season_select.value
        with ui.dialog() as dialog, ui.card().classes("app-card p-5 w-full"):
            ui.label("What\u2019s the occasion?").classes("section-title mb-3")
            with ui.row().classes("gap-2 flex-wrap"):
                for value, label in occasion_options():
                    def generate(v=value, d=dialog):
                        state.occasion = v if v != "none" else None
                        d.close()
                        try:
                            outfit = service.generate_outfit(season=state.season, occasion=state.occasion)
                            if outfit is None:
                                ui.notify("No valid outfit found. Try adding more garments.", type="negative")
                                state.current_outfit = None
                            else:
                                state.current_outfit = outfit
                                season_display = service.resolve_season_label(state.season)
                                occasion_display = dict(occasion_options()).get(v, v)
                                ui.notify(f"Generated for {season_display}, {occasion_display}", type="positive")
                        except Exception as e:
                            ui.notify(f"Error: {str(e)}", type="negative")
                        update_outfit_display()
                    ui.button(label, on_click=generate).classes("app-button-outline text-sm")
        dialog.open()

    update_outfit_display()


# ── Wardrobe ─────────────────────────────────────────────────────────────────
def wardrobe_content():
    with ui.row().classes("w-full justify-between items-center mb-2 gap-2 flex-wrap"):
        category_filter = ui.select(
            label="Category",
            options={
                "all": "All", "shoes": "Shoes", "trousers": "Trousers",
                "top": "Tops", "outerwear": "Outerwear",
                "accessory": "Accessories", "other": "Other"
            },
            value=state.wardrobe_category_filter,
            on_change=lambda e: set_filter("category", e.value)
        ).classes("flex-1").props("filled dense")
        active_filter = ui.select(
            label="Status",
            options={"all": "All", "active": "Active", "inactive": "Inactive"},
            value=state.wardrobe_active_filter,
            on_change=lambda e: set_filter("active", e.value)
        ).classes("flex-1").props("filled dense")
        ui.button(icon="refresh", on_click=lambda: refresh_grid()).props("flat round")

    grid_container = ui.column().classes("w-full")

    def garment_matches(g, cat_f, act_f):
        if cat_f != "all":
            if cat_f == "top" and g.get("layer_role") not in {"base", "mid", "outer"}:
                return False
            if cat_f == "outerwear" and not (
                g.get("layer_role") == "outer" or g.get("category") == "outerwear"
            ):
                return False
            if cat_f not in ("top", "outerwear") and g.get("category") != cat_f:
                return False
        if act_f == "active" and not g["active"]:
            return False
        if act_f == "inactive" and g["active"]:
            return False
        return True

    def render_garment_card(garment):
        inactive = not garment["active"]
        card = ui.card().classes(f"app-card p-4 cursor-pointer w-full{'  inactive-card' if inactive else ''}")
        card.on("click", lambda: open_garment_detail(garment["id"]))
        with card:
            with ui.row().classes("items-center justify-between w-full"):
                with ui.row().classes("items-center gap-2"):
                    ui.html(color_swatch_html(garment["color_hex"], "26px"))
                    ui.label(garment["name"]).classes("font-medium text-sm")
                color = "var(--success)" if garment["active"] else "var(--surface-muted)"
                text_color = "var(--accent-contrast)" if garment["active"] else "var(--text-muted)"
                ui.label("Active" if garment["active"] else "Inactive").classes(
                    "text-xs px-2 py-1 rounded-full"
                ).style(f"background:{color}; color:{text_color}; opacity:.85;")
            with ui.row().classes("gap-2 mt-2"):
                ui.label(category_label(garment["category"])).classes("muted-text text-xs")
                ui.label("\u00b7").classes("muted-text text-xs")
                ui.label(layer_role_label(garment["layer_role"])).classes("muted-text text-xs")
            with ui.row().classes("gap-4 mt-2"):
                ui.label(f"\U0001F525 {garment['warmth']}/10").classes("text-xs")
                ui.label(f"\U0001F454 {garment['formality']}/10").classes("text-xs")
            tags = [t.strip() for t in garment["occasion_tags"].split(",") if t.strip()]
            if tags:
                with ui.row().classes("gap-1 mt-2 flex-wrap"):
                    for tag in tags[:3]:
                        ui.label(occasion_tag_label(tag)).classes("text-xs px-2 py-0.5 rounded-full").style(
                            "background:var(--surface-muted); color:var(--text-muted);"
                        )

    def refresh_grid():
        grid_container.clear()
        garments = service.list_garments(show_inactive=True)
        filtered = [g for g in garments if garment_matches(
            g, state.wardrobe_category_filter, state.wardrobe_active_filter
        )]
        if not filtered:
            with grid_container:
                ui.label("No garments match the filters.").classes("muted-text text-center p-6")
            return
        with grid_container:
            with ui.element("div").classes("wardrobe-grid w-full"):
                for g in filtered:
                    render_garment_card(g)

    def set_filter(filter_type, value):
        if filter_type == "category":
            state.wardrobe_category_filter = value
        else:
            state.wardrobe_active_filter = value
        refresh_grid()

    def open_garment_detail(garment_id):
        garment = service.get_garment(garment_id)
        if not garment:
            ui.notify("Garment not found", type="negative")
            return
        with ui.dialog() as dialog, ui.card().classes("app-card p-5 w-full"):
            ui.label(garment["name"]).classes("section-title text-xl mb-2")
            with ui.row().classes("items-center gap-2 mb-3"):
                ui.html(color_swatch_html(garment["color_hex"], "32px"))
                ui.label(garment["color_hex"].upper()).classes("font-mono muted-text text-sm")
            with ui.grid(columns=2).classes("gap-2 w-full"):
                for key_label, value in [
                    ("Category", category_label(garment["category"])),
                    ("Layer role", layer_role_label(garment["layer_role"])),
                    ("Pattern", garment["pattern"] or "plain"),
                    ("Warmth", f'{garment["warmth"]}/10'),
                    ("Formality", f'{garment["formality"]}/10'),
                    ("Season tags", garment["season_tags"] or "\u2014"),
                ]:
                    ui.label(key_label + ":").classes("muted-text text-sm")
                    ui.label(value).classes("text-sm")
                ui.label("Occasion tags:").classes("muted-text text-sm")
                tags = [t.strip() for t in garment["occasion_tags"].split(",") if t.strip()]
                ui.label(", ".join(occasion_tag_label(t) for t in tags) if tags else "\u2014").classes("text-sm")
                ui.label("Status:").classes("muted-text text-sm")
                ui.label("Active" if garment["active"] else "Inactive").classes("text-sm")
            with ui.row().classes("justify-end gap-3 mt-4"):
                if garment["active"]:
                    ui.button("Deactivate", color="negative",
                              on_click=lambda: toggle_active(garment_id, False, dialog))
                else:
                    ui.button("Activate", color="positive",
                              on_click=lambda: toggle_active(garment_id, True, dialog))
                ui.button("Close", on_click=dialog.close).props("flat")
        dialog.open()

    def toggle_active(garment_id, activate, dialog):
        try:
            if activate:
                success = service.activate_garment(garment_id)
                msg = "Garment activated"
            else:
                success = service.deactivate_garment(garment_id)
                msg = "Garment deactivated"
            if success:
                ui.notify(msg, type="positive")
                dialog.close()
                refresh_grid()
            else:
                ui.notify("Failed to update status", type="negative")
        except Exception as e:
            ui.notify(f"Error: {str(e)}", type="negative")

    refresh_grid()


# ── Add garment ───────────────────────────────────────────────────────────────
def add_garment_content():
    selected_occasions = []

    def rebuild_occasion_chips(container):
        container.clear()
        with container:
            with ui.row().classes("gap-2 flex-wrap"):
                for occ in ["university", "work_casual", "evening", "event"]:
                    is_selected = occ in selected_occasions
                    chip = ui.chip(
                        occasion_tag_label(occ), selectable=True, selected=is_selected
                    )
                    chip.on("update:selected", lambda e, o=occ: toggle_occasion(o, e.args))

    def toggle_occasion(occ, selected):
        if selected and occ not in selected_occasions:
            selected_occasions.append(occ)
        elif not selected and occ in selected_occasions:
            selected_occasions.remove(occ)
        rebuild_occasion_chips(occasion_container)

    with ui.card().classes("app-card w-full p-4"):
        ui.label("Basic info").classes("section-title mb-3")
        name_input = ui.input("Garment name *", placeholder="e.g., Navy wool blazer").classes("w-full")
        category_select = ui.select(
            options={"shoes": "Shoes", "trousers": "Trousers", "top": "Top",
                     "outerwear": "Outerwear", "accessory": "Accessory", "other": "Other"},
            label="Category *", value="top"
        ).classes("w-full")
        layer_role_select = ui.select(
            options={"none": "No specific layer", "base": "Base layer",
                     "mid": "Mid layer", "outer": "Outerwear"},
            label="Layer role *", value="none"
        ).classes("w-full")

    with ui.card().classes("app-card w-full p-4"):
        ui.label("Color").classes("section-title mb-1")
        ui.label("Pick a color, enter a hex code, or type a CSS name and click Resolve.").classes("muted-text mb-3")
        with ui.row().classes("items-center gap-3 flex-wrap"):
            color_picker = ui.color_input(label="Picker", value="#3B82F6").props("filled dense")
            hex_input = ui.input("Hex", value="#3B82F6", placeholder="#RRGGBB").classes("w-32").props("filled dense")
            css_input = ui.input("CSS name", placeholder="e.g., navy").classes("w-32").props("filled dense")
            resolve_btn = ui.button("Resolve", icon="search").props("flat")
        preview_swatch = ui.html("")

        def update_preview(hex_val):
            if validate_hex_color(hex_val):
                preview_swatch.set_content(color_swatch_html(hex_val, "32px"))
            else:
                preview_swatch.set_content("")

        def sync_from_picker(e):
            hex_input.set_value(e.value)
            update_preview(e.value)

        def sync_from_hex(e):
            val = e.value
            if validate_hex_color(val):
                color_picker.set_value(val)
                update_preview(val)
            else:
                preview_swatch.set_content("")

        def resolve_css():
            name = css_input.value.strip()
            if not name:
                ui.notify("Enter a CSS color name", type="warning")
                return
            try:
                from color_utils import css_to_hex
                hex_val = css_to_hex(name)
                hex_input.set_value(hex_val)
                color_picker.set_value(hex_val)
                update_preview(hex_val)
                ui.notify(f"Resolved {name} \u2192 {hex_val}", type="positive")
            except Exception:
                ui.notify(f"Unknown color name: {name}", type="negative")

        color_picker.on("update:model-value", sync_from_picker)
        hex_input.on("change", sync_from_hex)
        resolve_btn.on("click", resolve_css)
        update_preview("#3B82F6")

    with ui.card().classes("app-card w-full p-4"):
        ui.label("Style & comfort").classes("section-title mb-3")
        pattern_input = ui.input("Pattern", value="plain", placeholder="plain, striped, logo\u2026").classes("w-full")
        warmth_label = ui.label("Warmth: 5").classes("muted-text text-sm")
        warmth_slider = ui.slider(min=1, max=10, step=1, value=5).props("label-always").classes("w-full")
        warmth_slider.on_value_change(lambda e: warmth_label.set_text(f"Warmth: {int(e.value)}"))
        formality_label = ui.label("Formality: 5").classes("muted-text text-sm")
        formality_slider = ui.slider(min=1, max=10, step=1, value=5).props("label-always").classes("w-full")
        formality_slider.on_value_change(lambda e: formality_label.set_text(f"Formality: {int(e.value)}"))

    with ui.card().classes("app-card w-full p-4"):
        ui.label("Context tags").classes("section-title mb-3")
        season_tags_input = ui.input(
            "Season tags", placeholder="e.g., summer, winter"
        ).classes("w-full")
        ui.label("Occasion tags").classes("muted-text text-sm mt-2 mb-1")
        occasion_container = ui.column().classes("gap-2")
        rebuild_occasion_chips(occasion_container)

    with ui.card().classes("app-card w-full p-4"):
        ui.label("Status").classes("section-title mb-2")
        active_checkbox = ui.checkbox("Garment is active", value=True)

    def submit_form():
        name = name_input.value.strip()
        if not name:
            ui.notify("Please enter a garment name", type="negative")
            return
        category = category_select.value
        if not category:
            ui.notify("Please select a category", type="negative")
            return
        layer_role = layer_role_select.value
        hex_val = hex_input.value.strip()
        if not validate_hex_color(hex_val):
            ui.notify("Invalid hex color. Use format #RRGGBB", type="negative")
            return
        pattern = pattern_input.value.strip() or "plain"
        warmth = warmth_slider.value
        formality = formality_slider.value
        season_tags = season_tags_input.value.strip()
        active = active_checkbox.value
        payload = {
            "name": name, "category": category, "layer_role": layer_role,
            "color_hex": hex_val, "pattern": pattern, "warmth": warmth,
            "formality": formality,
            "season_tags": season_tags if season_tags else "all_season",
            "occasion_tags": selected_occasions, "active": active,
        }
        try:
            service.add_garment_from_payload(payload)
            ui.notify(f'"{name}" added successfully!', type="positive")
            name_input.set_value("")
            category_select.set_value("top")
            layer_role_select.set_value("none")
            hex_input.set_value("#3B82F6")
            color_picker.set_value("#3B82F6")
            update_preview("#3B82F6")
            pattern_input.set_value("plain")
            warmth_slider.set_value(5)
            formality_slider.set_value(5)
            season_tags_input.set_value("")
            selected_occasions.clear()
            rebuild_occasion_chips(occasion_container)
            active_checkbox.set_value(True)
        except Exception as e:
            ui.notify(f"Error: {str(e)}", type="negative")

    ui.button("Add to wardrobe", icon="add", on_click=submit_form).classes(
        "w-full app-button-primary py-3 mt-2"
    )


# ── Learning ──────────────────────────────────────────────────────────────────
def learning_content():
    learning_container = ui.column().classes("w-full gap-3")

    def refresh_learning():
        learning_container.clear()
        with learning_container:
            summary = service.get_learning_summary()
            weights = summary["weights"]
            target_f = summary["target_formality"]
            neutral_th = summary["neutral_saturation_threshold"]

            with ui.card().classes("app-card w-full p-4"):
                ui.label("Preferred formality").classes("muted-text text-sm mb-1")
                ui.label(formality_preference_label(target_f)).classes("section-title text-xl")
                if state.advanced_mode:
                    ui.label(f"(numeric: {format_weight(target_f)})").classes("muted-text text-xs")

            with ui.card().classes("app-card w-full p-4"):
                ui.label("Neutral sensitivity").classes("muted-text text-sm mb-1")
                ui.label(neutral_sensitivity_label(neutral_th)).classes("section-title text-xl")
                if state.advanced_mode:
                    ui.label(f"(threshold: {format_weight(neutral_th)})").classes("muted-text text-xs")

            with ui.card().classes("app-card w-full p-4"):
                ui.label("Feedback given").classes("muted-text text-sm mb-2")
                with ui.row().classes("gap-4"):
                    ui.label(f"\U0001F44D {summary['feedback_positive']}").classes("text-sm")
                    ui.label(f"\U0001F44E {summary['feedback_negative']}").classes("text-sm")
                    ui.label(f"Total: {summary['feedback_total']}").classes("muted-text text-sm")

            with ui.card().classes("app-card w-full p-4"):
                ui.label("Penalized combinations").classes("muted-text text-sm mb-1")
                if summary["pair_penalty_count"] == 0:
                    ui.label("No disliked combinations learned yet.").classes("muted-text")
                else:
                    ui.label(f"{summary['pair_penalty_count']} disliked pair(s)").classes("section-title text-xl")

            with ui.card().classes("app-card w-full p-4"):
                ui.label("Wardrobe & wear").classes("muted-text text-sm mb-2")
                with ui.row().classes("gap-4 flex-wrap"):
                    ui.label(f"\U0001F9E5 Active: {summary['active_garment_count']}").classes("text-sm")
                    ui.label(f"\U0001F4E6 Inactive: {summary['inactive_garment_count']}").classes("text-sm")
                    ui.label(f"\U0001F454 Worn: {summary['worn_outfit_count']}").classes("text-sm")

            if state.advanced_mode:
                with ui.expansion("Advanced details", icon="insights").classes("w-full"):
                    ui.label("Current preferences").classes("font-semibold mt-2 mb-1")
                    for key in ["target_formality", "neutral_saturation_threshold",
                                "formality_threshold", "color_weight",
                                "pattern_weight", "formality_weight"]:
                        if key in weights:
                            ui.label(f"{weight_label(key)}: {format_weight(weights[key])}").classes("text-sm")
                    ui.label("Most disliked combinations").classes("font-semibold mt-4 mb-1")
                    top_pairs = service.get_top_pair_penalties(5)
                    if not top_pairs:
                        ui.label("No penalized pairs yet.").classes("muted-text text-sm")
                    else:
                        for p in top_pairs:
                            penalty = format_weight(p["penalty_score"], 2)
                            ui.label(
                                f"{p['garment_1_name']} + {p['garment_2_name']}  \u2192  {penalty}"
                            ).classes("text-sm")

            with ui.row().classes("justify-center mt-2"):
                def confirm_reset():
                    with ui.dialog() as dialog, ui.card().classes("app-card p-5 w-full"):
                        ui.label("Reset learned preferences?").classes("section-title mb-2")
                        ui.label(
                            "This restores default scoring preferences and clears learned "
                            "combination penalties. Your wardrobe and outfit history will remain."
                        ).classes("muted-text text-sm mb-4")
                        with ui.row().classes("gap-3 justify-end"):
                            ui.button("Cancel", on_click=dialog.close).props("flat")
                            def do_reset():
                                service.reset_learning()
                                ui.notify("Preferences reset", type="positive")
                                dialog.close()
                                refresh_learning()
                            ui.button("Reset learning", on_click=do_reset, color="negative")
                    dialog.open()
                ui.button("Reset learning", icon="restore", on_click=confirm_reset).props("outline").style(
                    "color:var(--text-muted); border-color:var(--border);"
                )

    refresh_learning()


# ── Settings ──────────────────────────────────────────────────────────────────
def settings_content():
    with ui.card().classes("app-card w-full p-5"):
        ui.label("Appearance").classes("section-title mb-4")

        with ui.row().classes("items-center justify-between w-full mb-4"):
            with ui.column().classes("gap-0"):
                ui.label("Dark mode").classes("font-medium text-sm")
                ui.label("Switch to a warm dark theme").classes("muted-text text-xs")
            dark_toggle = ui.switch(value=state.dark_mode)

        with ui.row().classes("items-center justify-between w-full"):
            with ui.column().classes("gap-0"):
                ui.label("Advanced mode").classes("font-medium text-sm")
                ui.label("Show scores and technical details").classes("muted-text text-xs")
            adv_toggle = ui.switch(value=state.advanced_mode)

    ui.label("Preferences are saved locally on this device.").classes(
        "muted-text text-xs text-center mt-2"
    )

    def on_dark_change(e):
        state.dark_mode = e.value
        service.set_dark_mode(e.value)
        _apply_theme()

    def on_advanced_change(e):
        state.advanced_mode = e.value
        service.set_advanced_mode(e.value)

    dark_toggle.on_value_change(on_dark_change)
    adv_toggle.on_value_change(on_advanced_change)

    with ui.card().classes("app-card w-full p-4 mt-2"):
        ui.label("About").classes("section-title mb-2")
        ui.label("Dressense").classes("font-medium text-sm")
        ui.label(
            "Local single-user outfit assistant. All data stays on your device."
        ).classes("muted-text text-sm")


# ── Run ───────────────────────────────────────────────────────────────────────
app.on_startup(on_startup)
app.on_shutdown(on_shutdown)

ui.run(
    title="Dressense",
    favicon="\U0001F9E5",
    dark=False,
    port=8081,
    reload=False,
)