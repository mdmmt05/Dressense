from typing import Optional, List, Dict, Any
from db_manager import DB_Manager, WeightsManager
from feedback_engine import FeedbackManager
from outfit_engine import OutfitGenerator
from color_utils import hex_to_rgb, rgb_to_cielab

class DressenseService:
    def __init__(self):
        self.db = DB_Manager()
        self.weights_manager = WeightsManager(self.db)
        self.feedback_manager = FeedbackManager(self.db)
        OutfitGenerator.load_weights(self.weights_manager.get_all_weights())

    def _row_to_dict(self, row) -> Optional[Dict]:
        return dict(row) if row is not None else None

    def get_garment_categories(self):
        shoes = self.db.get_garments_by_category('shoes')
        bottoms = self.db.get_garments_by_category('trousers')
        base_tops = self.db.get_garments_by_layer('base')
        mid_tops = self.db.get_garments_by_layer('mid')
        outerwear = self.db.get_garments_by_layer('outer')
        return shoes, bottoms, base_tops, mid_tops, outerwear

    def generate_outfit(self, season: str = "auto", occasion: Optional[str] = None):
        try:
            shoes, bottoms, base_tops, mid_tops, outerwear = self.get_garment_categories()
            if not shoes or not bottoms or not base_tops:
                return None
            outfits = OutfitGenerator.generate(
                shoes, bottoms, base_tops, mid_tops, outerwear,
                db=self.db, count=1, season=season, occasion=occasion
            )
            return outfits[0] if outfits else None
        except Exception as e:
            # Re-raise after logging? Simple re-raise for UI to catch.
            raise e

    def get_outfit_details(self, outfit) -> Dict[str, Any]:
        garments = []
        for field in ['shoes', 'bottom', 'base_top', 'mid_top', 'outerwear']:
            gid = getattr(outfit, field, None)
            if gid:
                row = self.db.get_garment(gid)
                if row:
                    garments.append(dict(row))
        micro_palette = [g['color_hex'] for g in garments]
        total_warmth = sum(g['warmth'] for g in garments) if garments else 0
        avg_formality = sum(g['formality'] for g in garments) / len(garments) if garments else 0
        return {
            'garments': garments,
            'micro_palette': micro_palette,
            'total_warmth': total_warmth,
            'avg_formality': round(avg_formality, 1),
            'score': round(outfit.score, 3) if outfit.score is not None else None
        }

    def submit_feedback(self, outfit, liked: bool, reason: Optional[str] = None):
        verdict = 1 if liked else 0
        self.feedback_manager.process_feedback(outfit, verdict, reason)

    def mark_outfit_worn(self, outfit):
        self.db.add_outfit_to_history(outfit)

    def resolve_season_label(self, season_mode: str) -> str:
        from outfit_engine import OutfitGenerator
        if season_mode == "auto":
            resolved = OutfitGenerator.infer_current_season()
            return f"Auto: {resolved.capitalize()}"
        elif season_mode == "none":
            return "No season"
        else:
            return season_mode.capitalize()

    def close(self):
        self.db.close()
    
    def list_garments(self, show_inactive: bool = True) -> list[dict]:
        """Return full garment dicts for the wardrobe grid."""
        rows = self.db.list_garments_full(show_inactive)
        return [dict(row) for row in rows]

    def get_garment(self, garment_id: int) -> dict | None:
        row = self.db.get_garment(garment_id)
        return dict(row) if row else None

    def activate_garment(self, garment_id: int) -> bool:
        return self.db.activate_garment(garment_id) > 0

    def deactivate_garment(self, garment_id: int) -> bool:
        return self.db.deactivate_garment(garment_id) > 0

    def _compute_lab_from_hex(self, hex_color: str) -> tuple[float, float, float]:
        from color_utils import hex_to_rgb, rgb_to_cielab
        rgb = hex_to_rgb(hex_color)
        lab = rgb_to_cielab(rgb)
        return lab[0], lab[1], lab[2]

    def add_garment_from_payload(self, payload: dict) -> int:
        from db_manager import Garment
        from color_utils import css_to_hex

        # Validate and normalize
        name = payload.get('name', '').strip()
        if not name:
            raise ValueError('Garment name is required')
        category = payload.get('category', '').strip()
        if not category:
            raise ValueError('Category is required')
        layer_role = payload.get('layer_role', 'none').strip()
        if layer_role not in ('none', 'base', 'mid', 'outer'):
            raise ValueError('Invalid layer_role')
        pattern = payload.get('pattern', 'plain').strip() or 'plain'
        try:
            warmth = int(payload.get('warmth', 5))
            if not 1 <= warmth <= 10:
                raise ValueError
        except ValueError:
            raise ValueError('Warmth must be between 1 and 10')
        try:
            formality = int(payload.get('formality', 5))
            if not 1 <= formality <= 10:
                raise ValueError
        except ValueError:
            raise ValueError('Formality must be between 1 and 10')

        # Color: either hex or css name
        color_input = payload.get('color_hex', '').strip()
        if not color_input:
            raise ValueError('Color is required')
        if color_input.startswith('#'):
            hex_color = color_input.upper()
        else:
            # try to resolve CSS name
            try:
                hex_color = css_to_hex(color_input)
            except Exception:
                raise ValueError(f'Unknown CSS color name: {color_input}')
        # validate hex format
        import re
        if not re.match(r'^#[0-9A-F]{6}$', hex_color):
            raise ValueError(f'Invalid hex color: {hex_color}')

        # Compute LAB
        lab_l, lab_a, lab_b = self._compute_lab_from_hex(hex_color)

        season_tags = payload.get('season_tags', '').strip() or 'all_season'
        occasion_tags_raw = payload.get('occasion_tags', [])
        if isinstance(occasion_tags_raw, list):
            occasion_tags = ','.join([t.strip() for t in occasion_tags_raw if t.strip()])
        else:
            occasion_tags = occasion_tags_raw.strip() if occasion_tags_raw else ''
        active = bool(payload.get('active', True))

        garment = Garment(
            name=name,
            category=category,
            layer_role=layer_role,
            color_hex=hex_color,
            color_lab_l=lab_l,
            color_lab_a=lab_a,
            color_lab_b=lab_b,
            pattern=pattern,
            warmth=warmth,
            formality=formality,
            season_tags=season_tags,
            occasion_tags=occasion_tags,
            active=active,
        )
        garment_id = self.db.add_garment(garment)
        return garment_id
    
    # ===== Learning & Advanced =====
    def get_learning_summary(self) -> dict:
        weights = self.weights_manager.get_all_weights()
        return {
            "weights": weights,
            "target_formality": weights.get('target_formality', 5.0),
            "neutral_saturation_threshold": weights.get('neutral_saturation_threshold', 20.0),
            "feedback_total": self.db.count_feedback(),
            "feedback_positive": self.db.count_feedback_by_verdict(1),
            "feedback_negative": self.db.count_feedback_by_verdict(0),
            "pair_penalty_count": self.db.count_pair_penalties(),
            "worn_outfit_count": self.db.count_outfit_history(),
            "active_garment_count": self.db.count_garments_by_active(True),
            "inactive_garment_count": self.db.count_garments_by_active(False),
        }

    def reset_learning(self) -> None:
        self.weights_manager.reset_all_weights()
        self.db.clear_pair_penalties()
        from outfit_engine import OutfitGenerator
        OutfitGenerator.load_weights(self.weights_manager.get_all_weights())

    def get_top_pair_penalties(self, limit: int = 5) -> list:
        return self.db.list_top_pair_penalties(limit)

    def get_outfit_context_breakdown(self, outfit, season: str, occasion: Optional[str]) -> dict:
        from outfit_engine import OutfitGenerator as OG
        db = self.db
        total_warmth = OG.calculate_total_warmth(outfit, db)
        garments = OG.get_outfit_garments(outfit, db)
        avg_formality = sum(g['formality'] for g in garments) / len(garments) if garments else 0
        score = outfit.score if hasattr(outfit, 'score') else None
        season_adj = OG.calculate_season_adjustment(outfit, db, season) if season and season != "none" else 0.0
        occasion_tag_adj = OG.calculate_occasion_tag_adjustment(outfit, db, occasion) if occasion else 0.0
        occasion_form_adj = OG.calculate_occasion_formality_adjustment(outfit, db, occasion) if occasion else 0.0
        pair_penalties = OG.calculate_pair_penalties(outfit, db)
        recently_worn_penalty = OG.calculate_recently_worn_penalty(outfit, db)
        return {
            "total_warmth": total_warmth,
            "avg_formality": round(avg_formality, 1),
            "score": round(score, 3) if score is not None else None,
            "season_adjustment": round(season_adj, 3),
            "occasion_tag_adjustment": round(occasion_tag_adj, 3),
            "occasion_formality_adjustment": round(occasion_form_adj, 3),
            "pair_penalties": round(pair_penalties, 3),
            "recently_worn_penalty": round(recently_worn_penalty, 3),
        }