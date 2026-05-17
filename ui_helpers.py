from db_manager import FeedbackReason

def feedback_reason_label(reason_value: str) -> str:
    mapping = {
        'colors_clash': 'Colors clash',
        'too_many_neutrals': 'Too neutral',
        'too_formal': 'Too formal',
        'too_casual': 'Too casual',
        'bad_layering': 'Layering feels off',
        'dont_like_combination': 'Bad combination',
        'boring': 'Boring',
        'too_flashy': 'Too flashy',
    }
    return mapping.get(reason_value, reason_value)

def get_feedback_reasons() -> list:
    return [(r.value, feedback_reason_label(r.value)) for r in FeedbackReason]

def season_options() -> list:
    return [
        ("auto", "Auto"),
        ("none", "No season"),
        ("spring", "Spring"),
        ("summer", "Summer"),
        ("autumn", "Autumn"),
        ("winter", "Winter"),
    ]

def occasion_options() -> list:
    return [
        ("none", "No specific occasion"),
        ("university", "University"),
        ("work_casual", "Work casual"),
        ("evening", "Evening"),
        ("event", "Event"),
    ]

def _value(obj, key, default=None):
    if hasattr(obj, 'get'):
        return obj.get(key, default)
    try:
        return obj[key]
    except Exception:
        return default


def garment_role_label(garment) -> str:
    role = _value(garment, 'layer_role', 'none')
    category = _value(garment, 'category', '')

    if role != 'none':
        return layer_role_label(role)
    if category == 'shoes':
        return 'Shoes'
    if category == 'trousers':
        return 'Trousers'
    return 'Garment'

def color_swatch_html(color_hex: str, size: str = "24px") -> str:
    return f'<div style="background-color: {color_hex}; width: {size}; height: {size}; border-radius: 50%; display: inline-block; border: 1px solid rgba(0,0,0,0.1);"></div>'

def active_badge_label(active: bool) -> str:
    return 'Active' if active else 'Inactive'

def active_badge_class(active: bool) -> str:
    return 'bg-green-100 text-green-800' if active else 'bg-gray-200 text-gray-600'

def category_label(category: str) -> str:
    mapping = {
        'shoes': 'Shoes',
        'trousers': 'Trousers',
        'top': 'Top',
        'outerwear': 'Outerwear',
        'accessory': 'Accessory',
        'other': 'Other',
    }
    return mapping.get(category, category.capitalize())

def layer_role_label(role: str) -> str:
    mapping = {
        'none': 'No layer',
        'base': 'Base',
        'mid': 'Mid layer',
        'outer': 'Outerwear',
    }
    return mapping.get(role, role.capitalize())

def occasion_tag_label(tag: str) -> str:
    """Convert occasion tag from database to user-friendly label."""
    mapping = {
        'university': 'University',
        'work_casual': 'Work casual',
        'evening': 'Evening',
        'event': 'Event',
    }
    return mapping.get(tag, tag.replace('_', ' ').capitalize())

def validate_hex_color(hex_str: str) -> bool:
    import re
    return bool(re.match(r'^#[0-9A-Fa-f]{6}$', hex_str))

def normalize_hex_display(hex_str: str) -> str:
    return hex_str.upper()

# ===== Learning / Advanced helpers =====
def formality_preference_label(value: float) -> str:
    if value <= 3.5:
        return "Casual leaning"
    elif value <= 6.5:
        return "Balanced"
    else:
        return "Formal leaning"

def neutral_sensitivity_label(value: float) -> str:
    if value <= 16:
        return "Low"
    elif value <= 28:
        return "Medium"
    else:
        return "High"

def weight_label(key: str) -> str:
    mapping = {
        'target_formality': 'Preferred formality',
        'neutral_saturation_threshold': 'Neutral sensitivity',
        'formality_threshold': 'Formality coherence tolerance',
        'color_weight': 'Color importance',
        'pattern_weight': 'Pattern importance',
        'formality_weight': 'Formality importance',
    }
    return mapping.get(key, key.replace('_', ' ').title())

def format_weight(value: float, decimal_places: int = 2) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return f"{value:.{decimal_places}f}"