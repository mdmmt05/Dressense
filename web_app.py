from nicegui import ui, app
from services import DressenseService
from ui_helpers import (
    feedback_reason_label, get_feedback_reasons,
    season_options, occasion_options, color_swatch_html,
    garment_role_label, active_badge_label, active_badge_class,
    category_label, layer_role_label, occasion_tag_label,
    validate_hex_color, normalize_hex_display, formality_preference_label,
    neutral_sensitivity_label,
    weight_label,
    format_weight,
)
from dataclasses import dataclass
from typing import Optional, Any, List

# Global service instance
service = DressenseService()

# Global state for the current outfit and generation context
@dataclass
class UIState:
    current_outfit: Optional[Any] = None
    season: str = "auto"
    occasion: Optional[Any] = None
    advanced_mode: bool = False
    wardrobe_category_filter: str = "all"
    wardrobe_active_filter: str = "all"

state = UIState()

def on_startup():
    """Ensure database is initialized (no action needed, service handles it)."""
    pass

def on_shutdown():
    service.close()

@ui.page('/')
def main_page():
    # Apply custom CSS for warm neutral theme
    ui.add_head_html('''
    <style>
        body {
            background-color: #F9F6F0;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }
        .q-card {
            background-color: #FFFFFF;
            border-radius: 1rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }
        .q-btn {
            border-radius: 2rem;
            text-transform: none;
            font-weight: 500;
        }
        .q-chip {
            border-radius: 2rem;
            background-color: #F0EDE8;
        }
        .accent-text {
            color: #6B705C;
        }
        .warm-bg {
            background-color: #F9F6F0;
        }
        .max-w-md {
            max-width: 540px;
            margin-left: auto;
            margin-right: auto;
        }
        .inactive-card {
            opacity: 0.7;
            filter: grayscale(0.1);
            transition: all 0.2s ease;
        }
        .inactive-card:hover {
            opacity: 0.85;
            filter: grayscale(0.05);
        }
    </style>
    ''')

    with ui.row().classes('w-full max-w-md mx-auto justify-between items-center px-2 py-3'):
        ui.label('Dressense').classes('text-2xl font-semibold text-[#6B705C]')
        dark = ui.dark_mode()
        ui.switch('Dark mode', on_change=lambda e: dark.set_value(e.value)).props('dense')

    # Bottom navigation
    with ui.tabs().classes('w-full bg-white shadow-sm') as tabs:
        generate_tab = ui.tab('Generate', icon='auto_awesome')
        wardrobe_tab = ui.tab('Wardrobe', icon='checkroom')
        add_tab = ui.tab('Add', icon='add')
        learning_tab = ui.tab('Learning', icon='insights')

    with ui.tab_panels(tabs, value=generate_tab).classes('w-full max-w-md mx-auto'):
        # Generate Panel
        with ui.tab_panel(generate_tab):
            generate_content()
        with ui.tab_panel(wardrobe_tab):
            wardrobe_content()
        with ui.tab_panel(add_tab):
            add_garment_content()
        with ui.tab_panel(learning_tab):
            learning_content()

def generate_content():
    # Season selection
    season_select = ui.select(
        label='',
        options={val: label for val, label in season_options()},
        value=state.season
    ).classes('w-40').props('filled dense')

    # Advanced mode toggle
    def toggle_advanced(e):
        state.advanced_mode = e.value
        update_outfit_display()
    advanced_toggle = ui.switch('Advanced mode', value=state.advanced_mode, on_change=toggle_advanced)
    advanced_toggle.classes('mb-4')

    # Generate button
    ui.button('Generate outfit', icon='auto_awesome', on_click=lambda: open_occasion_modal()).classes(
        'w-full bg-[#6B705C] text-white shadow-md py-3'
    )

    outfit_container = ui.column().classes('w-full mt-6 gap-4')

    def update_outfit_display():
        outfit_container.clear()
        if state.current_outfit is None:
            with outfit_container:
                ui.label('No outfit generated yet.').classes('text-gray-400 text-center p-4')
            return

        details = service.get_outfit_details(state.current_outfit)
        garments = details['garments']
        micro_palette = details['micro_palette']

        with outfit_container:
            with ui.card().classes('w-full p-4 gap-3'):
                with ui.row().classes('gap-2 justify-center mb-2'):
                    for hex_color in micro_palette:
                        ui.html(color_swatch_html(hex_color, '28px'))

                ui.label('Today’s outfit').classes('text-lg font-semibold text-center')

                for g in garments:
                    with ui.row().classes('items-center gap-3 py-1'):
                        ui.html(color_swatch_html(g['color_hex'], '20px'))
                        with ui.column().classes('flex-1'):
                            ui.label(g['name']).classes('font-medium')
                            ui.label(g.get('category', '')).classes('text-xs text-gray-400')
                        ui.label(garment_role_label(g)).classes('text-xs bg-gray-100 px-2 py-1 rounded-full')

                with ui.expansion('Details', icon='info').classes('w-full'):
                    resolved_season_label = service.resolve_season_label(state.season)
                    occasion_label = dict(occasion_options()).get(state.occasion, state.occasion) if state.occasion else "None"
                    ui.markdown(f'**Season:** {resolved_season_label}')
                    ui.markdown(f'**Occasion:** {occasion_label}')
                    ui.markdown(f'**Total warmth:** {details["total_warmth"]}')
                    ui.markdown(f'**Average formality:** {details["avg_formality"]}')
                    if state.advanced_mode and details['score'] is not None:
                        ui.markdown(f'**Score:** {details["score"]}')
                        # breakdown extra
                        try:
                            breakdown = service.get_outfit_context_breakdown(state.current_outfit, state.season, state.occasion)
                            if breakdown['season_adjustment'] != 0:
                                ui.markdown(f'Season adjustment: {breakdown["season_adjustment"]:+.3f}')
                            if breakdown['occasion_tag_adjustment'] != 0:
                                ui.markdown(f'Occasion tag adjustment: {breakdown["occasion_tag_adjustment"]:+.3f}')
                            if breakdown['occasion_formality_adjustment'] != 0:
                                ui.markdown(f'Occasion formality adjustment: {breakdown["occasion_formality_adjustment"]:+.3f}')
                            if breakdown['pair_penalties'] != 0:
                                ui.markdown(f'Pair penalties: {breakdown["pair_penalties"]:+.3f}')
                            if breakdown['recently_worn_penalty'] != 0:
                                ui.markdown(f'Recently worn penalty: {breakdown["recently_worn_penalty"]:+.3f}')
                        except Exception:
                            pass  # fallback silenzioso

                with ui.row().classes('justify-center gap-4 mt-2'):
                    ui.button(icon='thumb_up', on_click=lambda: positive_feedback()).props('flat round color=positive')
                    ui.button(icon='thumb_down', on_click=lambda: negative_feedback()).props('flat round color=negative')

    def positive_feedback():
        if state.current_outfit is None:
            return
        service.submit_feedback(state.current_outfit, liked=True)
        with ui.dialog() as dialog, ui.card():
            ui.label('Glad it works.').classes('text-lg')
            ui.label('Mark as worn today?').classes('mb-4')
            with ui.row().classes('gap-4'):
                def mark_and_close():
                    service.mark_outfit_worn(state.current_outfit)
                    ui.notify('Outfit marked as worn', type='positive')
                    dialog.close()
                ui.button('Yes, mark as worn', on_click=mark_and_close)
                ui.button('Not now', on_click=dialog.close)
        dialog.open()

    def negative_feedback():
        if state.current_outfit is None:
            return
        with ui.dialog() as dialog, ui.card().classes('w-80'):
            ui.label('Why did you dislike this outfit?').classes('text-md font-medium mb-2')
            with ui.row().classes('gap-2 flex-wrap'):
                for value, label in get_feedback_reasons():
                    def submit(v=value, d=dialog):
                        service.submit_feedback(state.current_outfit, liked=False, reason=v)
                        d.close()
                        ui.notify('Feedback saved', type='positive')
                        with ui.dialog() as gen_dialog, ui.card():
                            ui.label('Feedback saved.').classes('mb-4')
                            ui.button('Generate another', on_click=lambda: [gen_dialog.close(), open_occasion_modal()])
                        gen_dialog.open()
                    ui.button(label, on_click=submit).props('outline')
        dialog.open()

    def open_occasion_modal():
        state.season = season_select.value
        with ui.dialog() as dialog, ui.card().classes('w-80'):
            ui.label('What’s the occasion?').classes('text-md font-medium mb-2')
            with ui.row().classes('gap-2 flex-wrap'):
                for value, label in occasion_options():
                    def generate(v=value, d=dialog):
                        state.occasion = v if v != "none" else None
                        d.close()
                        ui.notify('Generating outfit...', type='info')
                        try:
                            outfit = service.generate_outfit(season=state.season, occasion=state.occasion)
                            if outfit is None:
                                ui.notify('No valid outfit found. Try changing season or adding more garments.', type='negative')
                                state.current_outfit = None
                            else:
                                state.current_outfit = outfit
                                season_display = service.resolve_season_label(state.season)
                                occasion_display = dict(occasion_options()).get(v, v)
                                ui.notify(f'Generated for {season_display}, {occasion_display}', type='positive')
                        except Exception as e:
                            ui.notify(f'Error: {str(e)}', type='negative')
                        update_outfit_display()
                    ui.button(label, on_click=generate).props('outline')
        dialog.open()

    update_outfit_display()

def wardrobe_content():
    # Filter row
    with ui.row().classes('w-full justify-between items-center mb-4 gap-2 flex-wrap'):
        category_filter = ui.select(
            label='Category',
            options={
                'all': 'All',
                'shoes': 'Shoes',
                'trousers': 'Trousers',
                'top': 'Tops',
                'outerwear': 'Outerwear',
                'accessory': 'Accessories',
                'other': 'Other'
            },
            value=state.wardrobe_category_filter,
            on_change=lambda e: set_filter('category', e.value)
        ).classes('w-32').props('filled dense')

        active_filter = ui.select(
            label='Status',
            options={
                'all': 'All',
                'active': 'Active only',
                'inactive': 'Inactive only'
            },
            value=state.wardrobe_active_filter,
            on_change=lambda e: set_filter('active', e.value)
        ).classes('w-32').props('filled dense')

        ui.button('Refresh', icon='refresh', on_click=lambda: refresh_grid()).props('flat')

    grid_container = ui.column().classes('w-full gap-4')

    def garment_matches_category_filter(g, filter_value):
        if filter_value == 'all':
            return True
        if filter_value == 'top':
            return g.get('layer_role') in {'base', 'mid', 'outer'}
        if filter_value == 'outerwear':
            return g.get('layer_role') == 'outer' or g.get('category') == 'outerwear'
        return g.get('category') == filter_value
    
    def render_garment_card(garment):
        card_classes = 'w-full sm:w-[calc(50%-0.5rem)] bg-white rounded-xl shadow-sm p-3 cursor-pointer transition-all'
        if not garment['active']:
            card_classes += ' inactive-card'
        with ui.card().classes(card_classes).on('click', lambda: open_garment_detail(garment['id'])):
            # Top row: color swatch + name + active badge
            with ui.row().classes('items-center justify-between w-full'):
                with ui.row().classes('items-center gap-2'):
                    ui.html(color_swatch_html(garment['color_hex'], '28px'))
                    ui.label(garment['name']).classes('font-medium')
                badge = ui.badge(active_badge_label(garment['active']), color='grey-3')
                badge.props('outline')
                badge.classes(active_badge_class(garment['active']))
            # Category and role
            with ui.row().classes('gap-2 mt-2 text-sm text-gray-500'):
                ui.label(category_label(garment['category']))
                ui.label('•')
                ui.label(layer_role_label(garment['layer_role']))
            # Warmth + Formality as simple indicators
            with ui.row().classes('gap-4 mt-2 text-sm'):
                ui.label(f'🔥 {garment["warmth"]}/10')
                ui.label(f'👔 {garment["formality"]}/10')
            # Occasion tags (small chips)
            tags = [t.strip() for t in garment['occasion_tags'].split(',') if t.strip()]
            if tags:
                with ui.row().classes('gap-1 mt-2 flex-wrap'):
                    for tag in tags[:2]:  # show max 2 tags
                        ui.chip(occasion_tag_label(tag)).props('flat')
        
    def refresh_grid():
        grid_container.clear()
        garments = service.list_garments(show_inactive=True)
        # Apply filters
        filtered = []
        for g in garments:
            # category filter
            if not garment_matches_category_filter(g, state.wardrobe_category_filter):
                continue
            # active filter
            if state.wardrobe_active_filter == 'active' and not g['active']:
                continue
            if state.wardrobe_active_filter == 'inactive' and g['active']:
                continue
            filtered.append(g)
        if not filtered:
            with grid_container:
                ui.label('No garments match the filters.').classes('text-gray-400 text-center p-4')
            return

        # Show as 2-column grid on mobile, adaptive
        with grid_container:
            with ui.row().classes('w-full gap-4 justify-center'):
                for g in filtered:
                    render_garment_card(g)

    def set_filter(filter_type, value):
        if filter_type == 'category':
            state.wardrobe_category_filter = value
        else:
            state.wardrobe_active_filter = value
        refresh_grid()

    def open_garment_detail(garment_id):
        garment = service.get_garment(garment_id)
        if not garment:
            ui.notify('Garment not found', type='negative')
            return
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-md p-4 gap-3'):
            ui.label(garment['name']).classes('text-xl font-semibold')
            with ui.row().classes('items-center gap-2'):
                ui.html(color_swatch_html(garment['color_hex'], '32px'))
                ui.label(garment['color_hex'].upper()).classes('font-mono')
            # Metadata in two columns
            with ui.grid(columns=2).classes('gap-2 w-full mt-2'):
                ui.label('Category:').classes('font-medium text-gray-600')
                ui.label(category_label(garment['category']))
                ui.label('Layer role:').classes('font-medium text-gray-600')
                ui.label(layer_role_label(garment['layer_role']))
                ui.label('Pattern:').classes('font-medium text-gray-600')
                ui.label(garment['pattern'] or 'plain')
                ui.label('Warmth:').classes('font-medium text-gray-600')
                ui.label(f'{garment["warmth"]}/10')
                ui.label('Formality:').classes('font-medium text-gray-600')
                ui.label(f'{garment["formality"]}/10')
                ui.label('Season tags:').classes('font-medium text-gray-600')
                ui.label(garment['season_tags'] or '—')
                ui.label('Occasion tags:').classes('font-medium text-gray-600')
                tags = [t.strip() for t in garment['occasion_tags'].split(',') if t.strip()]
                tags_label = ', '.join(occasion_tag_label(t) for t in tags) if tags else '—'
                ui.label(tags_label)
                ui.label('Status:').classes('font-medium text-gray-600')
                badge = ui.badge(active_badge_label(garment['active']), color='grey-3')
                badge.props('outline')
                badge.classes(active_badge_class(garment['active']))
            # Action buttons
            with ui.row().classes('justify-end gap-3 mt-4'):
                if garment['active']:
                    ui.button('Deactivate', color='negative', on_click=lambda: toggle_active(garment_id, False, dialog))
                else:
                    ui.button('Activate', color='positive', on_click=lambda: toggle_active(garment_id, True, dialog))
                ui.button('Close', on_click=dialog.close).props('flat')
        dialog.open()

    def toggle_active(garment_id, activate, dialog):
        try:
            if activate:
                success = service.activate_garment(garment_id)
                msg = 'Garment activated'
            else:
                success = service.deactivate_garment(garment_id)
                msg = 'Garment deactivated'
            if success:
                ui.notify(msg, type='positive')
                dialog.close()
                refresh_grid()
            else:
                ui.notify('Failed to update status', type='negative')
        except Exception as e:
            ui.notify(f'Error: {str(e)}', type='negative')

    refresh_grid()

def add_garment_content():
        # This list will hold selected occasion tags
    selected_occasions = []

    def rebuild_occasion_chips(container):
        container.clear()
        with container:
            ui.label('Occasion tags').classes('font-medium')
            with ui.row().classes('gap-2 flex-wrap'):
                for occ in ['university', 'work_casual', 'evening', 'event']:
                    is_selected = occ in selected_occasions
                    chip = ui.chip(occasion_tag_label(occ), selectable=True, selected=is_selected)
                    chip.on('update:selected', lambda e, o=occ: toggle_occasion(o, e.args))

    def toggle_occasion(occ, selected):
        if selected and occ not in selected_occasions:
            selected_occasions.append(occ)
        elif not selected and occ in selected_occasions:
            selected_occasions.remove(occ)
        rebuild_occasion_chips(occasion_container)

    # Outer column for the whole form
    form_column = ui.column().classes('w-full gap-4')

    # ---- Basic info card ----
    with form_column:
        with ui.card().classes('w-full p-4 gap-3'):
            ui.label('Basic info').classes('text-md font-semibold')
            name_input = ui.input('Garment name *', placeholder='e.g., Navy wool blazer')
            category_select = ui.select(
                options={
                    'shoes': 'Shoes',
                    'trousers': 'Trousers',
                    'top': 'Top',
                    'outerwear': 'Outerwear',
                    'accessory': 'Accessory',
                    'other': 'Other'
                },
                label='Category *',
                value='top'
            )
            layer_role_select = ui.select(
                options={
                    'none': 'No specific layer',
                    'base': 'Base layer',
                    'mid': 'Mid layer',
                    'outer': 'Outerwear'
                },
                label='Layer role *',
                value='none'
            )

        # ---- Color card ----
        with ui.card().classes('w-full p-4 gap-3'):
            ui.label('Color').classes('text-md font-semibold')
            ui.html('<div class="text-sm text-gray-500">Pick a color, enter hex, or type a CSS name (e.g., "navy") and click Resolve.</div>')
            color_row = ui.row().classes('items-center gap-3 flex-wrap')
            with color_row:
                color_picker = ui.color_input(label='Picker', value='#3B82F6').props('filled dense')
                hex_input = ui.input('Hex', value='#3B82F6', placeholder='#RRGGBB').classes('w-32').props('filled dense')
                css_input = ui.input('CSS name', placeholder='e.g., navy').classes('w-32').props('filled dense')
                resolve_btn = ui.button('Resolve', icon='search').props('flat')
            preview_swatch = ui.html('')
            # Helper to update preview
            def update_preview(hex_val):
                if validate_hex_color(hex_val):
                    preview_swatch.set_content(color_swatch_html(hex_val, '32px'))
                else:
                    preview_swatch.set_content('')
            # Sync between picker and hex
            def sync_from_picker(e):
                hex_input.set_value(e.value)
                update_preview(e.value)
            def sync_from_hex(e):
                val = e.value
                if validate_hex_color(val):
                    color_picker.set_value(val)
                    update_preview(val)
                else:
                    preview_swatch.set_content('')
            def resolve_css():
                name = css_input.value.strip()
                if not name:
                    ui.notify('Enter a CSS color name', type='warning')
                    return
                try:
                    from color_utils import css_to_hex
                    hex_val = css_to_hex(name)
                    hex_input.set_value(hex_val)
                    color_picker.set_value(hex_val)
                    update_preview(hex_val)
                    ui.notify(f'Resolved {name} → {hex_val}', type='positive')
                except Exception:
                    ui.notify(f'Unknown color name: {name}', type='negative')
            color_picker.on('update:model-value', sync_from_picker)
            hex_input.on('change', sync_from_hex)
            resolve_btn.on('click', resolve_css)
            update_preview('#3B82F6')

        # ---- Style & comfort card ----
        with ui.card().classes('w-full p-4 gap-3'):
            ui.label('Style & comfort').classes('text-md font-semibold')
            pattern_input = ui.input('Pattern', value='plain', placeholder='plain, striped, logo, etc.')
            # Warmth slider with live label
            warmth_label = ui.label('Warmth: 5')
            warmth_slider = ui.slider(min=1, max=10, step=1, value=5).props('label-always')
            warmth_slider.on_value_change(lambda e: warmth_label.set_text(f'Warmth: {int(e.value)}'))
            # Formality slider with live label
            formality_label = ui.label('Formality: 5')
            formality_slider = ui.slider(min=1, max=10, step=1, value=5).props('label-always')
            formality_slider.on_value_change(lambda e: formality_label.set_text(f'Formality: {int(e.value)}'))

        # ---- Context tags card ----
        with ui.card().classes('w-full p-4 gap-3'):
            ui.label('Context tags').classes('text-md font-semibold')
            season_tags_input = ui.input('Season tags', placeholder='e.g., summer, winter (comma separated)')
            occasion_container = ui.column().classes('gap-2')
            rebuild_occasion_chips(occasion_container)

        # ---- Status card ----
        with ui.card().classes('w-full p-4 gap-3'):
            ui.label('Status').classes('text-md font-semibold')
            active_checkbox = ui.checkbox('Garment is active', value=True)

    def submit_form():
        # Validation
        name = name_input.value.strip()
        if not name:
            ui.notify('Please enter a garment name', type='negative')
            return
        category = category_select.value
        if not category:
            ui.notify('Please select a category', type='negative')
            return
        layer_role = layer_role_select.value
        # Color
        hex_val = hex_input.value.strip()
        if not validate_hex_color(hex_val):
            ui.notify('Invalid hex color. Use format #RRGGBB', type='negative')
            return
        pattern = pattern_input.value.strip() or 'plain'
        warmth = warmth_slider.value
        formality = formality_slider.value
        season_tags = season_tags_input.value.strip()
        active = active_checkbox.value

        # Build payload
        payload = {
            'name': name,
            'category': category,
            'layer_role': layer_role,
            'color_hex': hex_val,
            'pattern': pattern,
            'warmth': warmth,
            'formality': formality,
            'season_tags': season_tags if season_tags else 'all_season',
            'occasion_tags': selected_occasions,
            'active': active,
        }
        try:
            garment_id = service.add_garment_from_payload(payload)
            ui.notify(f'"{name}" added successfully!', type='positive')
            # Reset form
            name_input.set_value('')
            category_select.set_value('top')
            layer_role_select.set_value('none')
            hex_input.set_value('#3B82F6')
            color_picker.set_value('#3B82F6')
            update_preview('#3B82F6')
            pattern_input.set_value('plain')
            warmth_slider.set_value(5)
            formality_slider.set_value(5)
            season_tags_input.set_value('')
            selected_occasions.clear()
            rebuild_occasion_chips(occasion_container)
            active_checkbox.set_value(True)
        except Exception as e:
            ui.notify(f'Error: {str(e)}', type='negative')

    # Submit button
    submit_btn = ui.button('Add to wardrobe', icon='add', on_click=submit_form).classes('w-full bg-[#6B705C] text-white py-3 mt-4')

# --- learning_content() completa ---
def learning_content():
    # Container principale
    learning_container = ui.column().classes('w-full gap-4')
    
    # Toggle Advanced mode locale (sincronizzato con state)
    advanced_toggle = ui.switch('Advanced mode', value=state.advanced_mode)
    
    def refresh_learning():
        learning_container.clear()
        with learning_container:
            # Ottieni riassunto
            summary = service.get_learning_summary()
            weights = summary['weights']
            target_f = summary['target_formality']
            neutral_th = summary['neutral_saturation_threshold']
            
            # Card 1 – Preferred formality
            with ui.card().classes('w-full p-4'):
                ui.label('Preferred formality').classes('text-sm text-gray-500')
                pref_label = formality_preference_label(target_f)
                ui.label(pref_label).classes('text-xl font-semibold')
                if state.advanced_mode:
                    ui.label(f'(numeric: {format_weight(target_f)})').classes('text-xs text-gray-400')
            
            # Card 2 – Neutral sensitivity
            with ui.card().classes('w-full p-4'):
                ui.label('Neutral sensitivity').classes('text-sm text-gray-500')
                neut_label = neutral_sensitivity_label(neutral_th)
                ui.label(neut_label).classes('text-xl font-semibold')
                if state.advanced_mode:
                    ui.label(f'(threshold: {format_weight(neutral_th)})').classes('text-xs text-gray-400')
            
            # Card 3 – Feedback given
            with ui.card().classes('w-full p-4'):
                ui.label('Feedback given').classes('text-sm text-gray-500')
                with ui.row().classes('justify-between'):
                    ui.label(f'👍 {summary["feedback_positive"]}')
                    ui.label(f'👎 {summary["feedback_negative"]}')
                    ui.label(f'📊 Total: {summary["feedback_total"]}')
            
            # Card 4 – Penalized combinations
            with ui.card().classes('w-full p-4'):
                ui.label('Penalized combinations').classes('text-sm text-gray-500')
                if summary['pair_penalty_count'] == 0:
                    ui.label('No disliked combinations learned yet.').classes('text-gray-500')
                else:
                    ui.label(f'{summary["pair_penalty_count"]} disliked pair(s)').classes('text-xl font-semibold')
            
            # Card 5 – Additional stats (opzionale ma utile)
            with ui.card().classes('w-full p-4'):
                ui.label('Wardrobe & wear').classes('text-sm text-gray-500')
                with ui.row().classes('justify-between'):
                    ui.label(f'🧥 Active: {summary["active_garment_count"]}')
                    ui.label(f'📦 Inactive: {summary["inactive_garment_count"]}')
                    ui.label(f'👔 Outfits worn: {summary["worn_outfit_count"]}')
            
            # Advanced expandable section
            with ui.expansion('Advanced details', icon='insights').bind_visibility_from(state, 'advanced_mode'):
                # Weights table
                ui.label('Current preferences').classes('font-semibold mt-2')
                for key in ['target_formality', 'neutral_saturation_threshold', 'formality_threshold',
                            'color_weight', 'pattern_weight', 'formality_weight']:
                    if key in weights:
                        label = weight_label(key)
                        value = format_weight(weights[key])
                        ui.label(f'{label}: {value}').classes('text-sm')
                
                # Top penalized pairs
                ui.label('Most disliked combinations').classes('font-semibold mt-4')
                top_pairs = service.get_top_pair_penalties(5)
                if not top_pairs:
                    ui.label('No penalized pairs yet.').classes('text-sm text-gray-400')
                else:
                    for p in top_pairs:
                        penalty = format_weight(p['penalty_score'], 2)
                        ui.label(f'{p["garment_1_name"]} + {p["garment_2_name"]}  →  {penalty}').classes('text-sm')
            
            # Reset button
            with ui.row().classes('justify-center mt-4'):
                def confirm_reset():
                    with ui.dialog() as dialog, ui.card().classes('w-80'):
                        ui.label('Reset learned preferences?').classes('text-md font-medium')
                        ui.label('This restores scoring preferences and clears learned combination penalties. Your wardrobe and outfit history will remain.').classes('text-sm text-gray-600 my-2')
                        with ui.row().classes('gap-4 justify-end'):
                            ui.button('Cancel', on_click=dialog.close).props('flat')
                            def do_reset():
                                service.reset_learning()
                                ui.notify('Preferences reset', type='positive')
                                dialog.close()
                                refresh_learning()
                            ui.button('Reset learning', on_click=do_reset, color='negative')
                    dialog.open()
                ui.button('Reset learning', icon='restore', on_click=confirm_reset, color='grey-8').props('outline')
    
    # Sincronizza toggle Advanced
    def on_advanced_change(e):
        state.advanced_mode = e.value
        refresh_learning()
    advanced_toggle.on_value_change(on_advanced_change)
    
    refresh_learning()

# Run the app
app.on_startup(on_startup)
app.on_shutdown(on_shutdown)

ui.run(
    title='Dressense',
    favicon='🧥',
    dark=False,
    port=8081,
    reload=True  # for development
)