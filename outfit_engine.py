from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from itertools import product, combinations
import random
import math
from datetime import datetime
from db_manager import DB_Manager, WeightsManager

#COLOR_WEIGHT = 0.55
#PATTERN_WEIGHT = 0.3
#FORMALITY_WEIGHT = 0.15

@dataclass
class Outfit:
    shoes: int # garment_id
    bottom: int # garment_id
    base_top: int # garment_id
    mid_top: Optional[int] = None # garment_id
    outerwear: Optional[int] = None # garment_id
    score: Optional[float] = None

    # Metodi della classe

class OutfitGenerator:
    weights = {
        'formality_threshold': 4,
        'neutral_saturation_threshold': 20,
        'color_weight': 0.55,
        'pattern_weight': 0.3,
        'formality_weight': 0.15,
        'target_formality': 5.0,
    }

    # Phase 3: season and occasion constants
    SEASON_WARMTH_PROFILES = {
        "summer": {"target": 8, "min": 3, "max": 13, "tolerance": 8},
        "spring": {"target": 12, "min": 6, "max": 18, "tolerance": 9},
        "autumn": {"target": 16, "min": 8, "max": 22, "tolerance": 9},
        "winter": {"target": 22, "min": 14, "max": 32, "tolerance": 10},
    }
    OCCASION_PROFILES = {
        "university": {"formality_min": 2, "formality_max": 6},
        "work_casual": {"formality_min": 4, "formality_max": 7},
        "evening": {"formality_min": 5, "formality_max": 8},
        "event": {"formality_min": 6, "formality_max": 10},
    }
    SEASON_WEIGHT = 0.10
    OCCASION_TAG_WEIGHT = 0.08
    OCCASION_FORMALITY_WEIGHT = 0.06

    @classmethod
    def load_weights(cls, weights_dict: dict):
        """Carica i pesi dal database"""
        cls.weights.update(weights_dict)
    
    @staticmethod
    def extract_lab(garment) -> tuple:
        """Estrae la tupla LAB da garment"""
        return (
            garment['color_lab_l'],
            garment['color_lab_a'],
            garment['color_lab_b']
        )
    
    @staticmethod
    def calculate_lab_distance(lab1: tuple, lab2: tuple) -> float:
        """Calcola distanza euclidea CIELAB tra due colori"""
        l1, a1, b1 = lab1
        l2, a2, b2 = lab2
        return math.sqrt((l2-l1)**2 + (a2-a1)**2 + (b2-b1)**2)
    
    @staticmethod
    def is_neutral_color(garment) -> bool:
        """
        Verifica se un garment ha colore neutrale
        Neutrali hanno bassa saturazione (a e b vicini a 0)
        """
        threshold = OutfitGenerator.weights.get('neutral_saturation_threshold', 20)
        a = garment['color_lab_a']
        b = garment['color_lab_b']
        # Calcola la saturazione (distanza dall'asse L)
        saturation = math.sqrt(a**2 + b**2)
        return saturation < threshold
    
    @staticmethod
    def score_color_pair(distance: float, is_neutral1: bool, is_neutral2: bool) -> float:
        """Score basato su distanza CIELAB"""
        # Gestisci neutrali
        if is_neutral1 or is_neutral2:
            if distance < 5:
                return 0.5
            elif distance < 20:
                return 0.75
            elif distance < 50:
                return 0.9
            elif distance < 70:
                return 0.85
            else:
                return 0.7
        else:
            if distance < 15:
                return 0.2
            elif distance > 60:
                return 0.3
            elif 25 <= distance <= 45:
                return 1.0
            else:
                return 0.7

    @staticmethod
    def calculate_neutral_penalty(outfit, db) -> float:
        """Penalizza outfit con troppi neutrali"""
        garments = [
            db.get_garment(outfit.shoes),
            db.get_garment(outfit.bottom),
            db.get_garment(outfit.base_top)
        ]
        if outfit.mid_top:
            garments.append(db.get_garment(outfit.mid_top))
        if outfit.outerwear:
            garments.append(db.get_garment(outfit.outerwear))

        neutral_count = sum(1 for g in garments if OutfitGenerator.is_neutral_color(g))
        total_count = len(garments)
        neutral_ratio = neutral_count / total_count

        # Penalità progressiva
        if neutral_ratio >= 0.75:  # 3/4 o più neutrali
            return -0.15
        elif neutral_ratio >= 0.60:  # 3/5 neutrali
            return -0.10
        elif neutral_ratio >= 0.50:  # metà neutrali
            return -0.05
        else:
            return 0.0  # nessuna penalità
    
    @staticmethod
    def calculate_color_diversity_bonus(outfit, db) -> float:
        """Bonus per outfit con colori diversificati"""
        garments = [
            db.get_garment(outfit.shoes),
            db.get_garment(outfit.bottom),
            db.get_garment(outfit.base_top)
        ]
        if outfit.mid_top:
            garments.append(db.get_garment(outfit.mid_top))
        if outfit.outerwear:
            garments.append(db.get_garment(outfit.outerwear))
        
        colored_count = sum(1 for g in garments if not OutfitGenerator.is_neutral_color(g))

        # Bonus progressivo
        if colored_count >= 3:
            return 0.10
        elif colored_count >= 2:
            return 0.05
        else:
            return 0.0
    
    @staticmethod
    def get_pattern_weight(pattern: str) -> int:
        """
        Restituisce peso del pattern:
        0 = plain/neutro
        1 = texture/logo leggero
        2 = pattern forte
        """
        pattern_lower = pattern.lower()

        # Plain o texture sottile
        if 'plain' in pattern_lower or 'velluto' in pattern_lower or 'trecce' in pattern_lower:
            return 0
        # Logo o pattern moderato
        elif 'logo' in pattern_lower:
            return 1
        # Pattern forti
        elif 'lightning' in pattern_lower or 'multi-zone' in pattern_lower or 'striped' in pattern_lower:
            return 2
        # Default: tratta come moderato
        else:
            return 1
    
    @staticmethod
    def calculate_pattern_coherence(outfit, db) -> float:
        """Score basato su coerenza pattern"""

        # Carica tutti i garment
        shoes = db.get_garment(outfit.shoes)
        bottom = db.get_garment(outfit.bottom)
        base_top = db.get_garment(outfit.base_top)
        mid_top = db.get_garment(outfit.mid_top) if outfit.mid_top else None
        outerwear = db.get_garment(outfit.outerwear) if outfit.outerwear else None
        
        # Lista dei garment visibili
        visible_garments = [shoes, bottom] # sempre visibili

        # Determina quale top è visibile
        if outerwear:
            # se c'è outer, è il top visibile
            visible_garments.append(outerwear)
        elif mid_top:
            # se c'è mid ma non outer, mid è visibile
            visible_garments.append(mid_top)
        else:
            # altrimenti base è visibile
            visible_garments.append(base_top)
        
        # Ottieni pesi pattern
        pattern_weights = [OutfitGenerator.get_pattern_weight(g['pattern']) for g in visible_garments]

        # Conta pattern per tipo
        plain_count = pattern_weights.count(0)
        moderate_count = pattern_weights.count(1)
        strong_count = pattern_weights.count(2)

        # Casi ottimi
        if strong_count == 0 and moderate_count <= 1:
            return 1.0  # tutto plain o 1 logo → perfetto

        if strong_count == 0 and moderate_count == 2:
            return 0.9  # 2 loghi → buono

        # Casi accettabili
        if strong_count == 1 and moderate_count == 0:
            return 0.85  # 1 pattern forte + resto plain → ok

        # Casi problematici
        if strong_count >= 2:
            return 0.4  # 2+ pattern forti → troppo

        if strong_count == 1 and moderate_count >= 2:
            return 0.5  # 1 forte + 2 moderati → caotico

        # Default
        return 0.8

    @staticmethod
    def calculate_formality_alignment(outfit, db) -> float:
        """Score basato su allineamento formality"""
        threshold = OutfitGenerator.weights.get('formality_threshold', 4)
        # Carica garment
        garments = [
            db.get_garment(outfit.shoes),
            db.get_garment(outfit.bottom),
            db.get_garment(outfit.base_top)
        ]
        if outfit.mid_top:
            garments.append(db.get_garment(outfit.mid_top))
        if outfit.outerwear:
            garments.append(db.get_garment(outfit.outerwear))

        # Estrai formality values
        formalities = [g['formality'] for g in garments]

        # Calcola gap
        min_form = min(formalities)
        max_form = max(formalities)
        gap = max_form - min_form

        # Score basato sul gap
        if gap <= threshold-3:
            return 1.0
        elif gap == threshold-2:
            return 0.95
        elif gap == threshold-1:
            return 0.85
        elif gap == threshold:
            return 0.6
        else:
            return 0.0  # non dovrebbe accadere
    
    @staticmethod
    def calculate_target_formality_score(outfit, db) -> float:
        """Rewards outfits whose average formality is close to target_formality."""
        target = OutfitGenerator.weights.get('target_formality', 5.0)
        garments = [
            db.get_garment(outfit.shoes),
            db.get_garment(outfit.bottom),
            db.get_garment(outfit.base_top)
        ]
        if outfit.mid_top:
            garments.append(db.get_garment(outfit.mid_top))
        if outfit.outerwear:
            garments.append(db.get_garment(outfit.outerwear))

        avg_formality = sum(g['formality'] for g in garments) / len(garments)
        distance = abs(avg_formality - target)
        # Score decreases linearly from 1.0 (distance 0) to 0.0 (distance >= 5)
        score = max(0.0, 1.0 - distance / 5.0)
        return score
    
    @staticmethod
    def calculate_simplicity_bonus(outfit) -> float:
        """Piccolo bonus per outfit con meno layer"""

        # Conta layer presenti
        layer_count = 3
        if outfit.mid_top:
            layer_count += 1
        if outfit.outerwear:
            layer_count += 1
        
        # Bonus decrescente (più layer = meno bonus)
        if layer_count == 3:
            return 0.03 # outfit minimale
        elif layer_count == 4:
            return 0.02 # con mid o outer
        elif layer_count == 5:
            return 0.01 # completo
        else:
            return 0.0
        
    @staticmethod
    def calculate_pair_penalties(outfit, db) -> float:
        """Calcola la somma delle penalità per tutte le coppie nell'outfit"""
        weights_mgr = WeightsManager(db)
        # Raccogli tutti i garment_id
        garment_ids = [outfit.shoes, outfit.bottom, outfit.base_top]
        if outfit.mid_top:
            garment_ids.append(outfit.mid_top)
        if outfit.outerwear:
            garment_ids.append(outfit.outerwear)
        
        # Calcola penalità totale
        total_penalty = 0.0
        for id1, id2 in combinations(garment_ids, 2):
            penalty = weights_mgr.get_pair_penalty(id1, id2)
            total_penalty += penalty
        return total_penalty
    
    @staticmethod
    def calculate_recently_worn_penalty(outfit, db) -> float:
        """Calcola penalità per capi indossati di recente"""
        garment_ids = [outfit.shoes, outfit.bottom, outfit.base_top]
        if outfit.mid_top:
            garment_ids.append(outfit.mid_top)
        if outfit.outerwear:
            garment_ids.append(outfit.outerwear)
        
        penalty = 0.0
        for gid in garment_ids:
            days_ago = db.get_garment_last_worn_days(gid)
            if days_ago is None:
                continue
            if days_ago == 0:
                penalty -= 0.08
            elif days_ago == 1:
                penalty -= 0.05
            elif 2 <= days_ago <= 3:
                penalty -= 0.03
            elif 4 <= days_ago <= 7:
                penalty -= 0.01
            # >7 days: no penalty
        return penalty
    
    # ========== Phase 3 helper methods ==========
    @staticmethod
    def parse_tags(tags_str: str) -> List[str]:
        """Split comma-separated tags, trim, lowercase, ignore empty."""
        if not tags_str:
            return []
        return [tag.strip().lower() for tag in tags_str.split(',') if tag.strip()]

    @staticmethod
    def infer_current_season() -> str:
        month = datetime.now().month
        if month in (12, 1, 2):
            return "winter"
        elif month in (3, 4, 5):
            return "spring"
        elif month in (6, 7, 8):
            return "summer"
        else:  # 9,10,11
            return "autumn"

    @classmethod
    def resolve_season(cls, season: Optional[str]) -> Optional[str]:
        """Return effective season name or None. Handles 'auto' and None."""
        if season is None or season == "none":
            return None
        if season == "auto":
            return cls.infer_current_season()
        if season in cls.SEASON_WARMTH_PROFILES:
            return season
        raise ValueError(f"Invalid season: {season}. Allowed: none, auto, spring, summer, autumn, winter")
    
    @classmethod
    def resolve_occasion(cls, occasion: Optional[str]) -> Optional[str]:
        """Return effective occasion name or None."""
        if occasion is None or occasion == "none":
            return None
        if occasion in cls.OCCASION_PROFILES:
            return occasion
        raise ValueError(
            f"Invalid occasion: {occasion}. "
            "Allowed: none, university, work_casual, evening, event"
        )

    @staticmethod
    def get_outfit_garments(outfit, db) -> List[Any]:
        """Return list of garment dicts for the outfit."""
        garments = [
            db.get_garment(outfit.shoes),
            db.get_garment(outfit.bottom),
            db.get_garment(outfit.base_top)
        ]
        if outfit.mid_top:
            garments.append(db.get_garment(outfit.mid_top))
        if outfit.outerwear:
            garments.append(db.get_garment(outfit.outerwear))
        return garments

    @staticmethod
    def calculate_total_warmth(outfit, db) -> int:
        return sum(g['warmth'] for g in OutfitGenerator.get_outfit_garments(outfit, db))

    @classmethod
    def is_seasonally_valid(cls, outfit, db, season: Optional[str]) -> bool:
        """Hard season filter: total_warmth within [min, max] of resolved season."""
        resolved = cls.resolve_season(season)
        if resolved is None:
            return True
        profile = cls.SEASON_WARMTH_PROFILES[resolved]
        total_warmth = cls.calculate_total_warmth(outfit, db)
        return profile["min"] <= total_warmth <= profile["max"]

    @classmethod
    def calculate_season_adjustment(cls, outfit, db, season: Optional[str]) -> float:
        """Soft penalty: (season_score - 1.0) * SEASON_WEIGHT"""
        resolved = cls.resolve_season(season)
        if resolved is None:
            return 0.0
        profile = cls.SEASON_WARMTH_PROFILES[resolved]
        total_warmth = cls.calculate_total_warmth(outfit, db)
        # inside hard bounds is guaranteed by is_seasonally_valid call before scoring
        distance = abs(total_warmth - profile["target"])
        season_score = max(0.0, 1.0 - distance / profile["tolerance"])
        return (season_score - 1.0) * cls.SEASON_WEIGHT

    @classmethod
    def calculate_occasion_tag_adjustment(cls, outfit, db, occasion: Optional[str]) -> float:
        """Soft penalty based on proportion of garments matching occasion in occasion_tags."""
        occasion = cls.resolve_occasion(occasion)
        if occasion is None:
            return 0.0
        garments = cls.get_outfit_garments(outfit, db)
        if not garments:
            return 0.0
        match_count = 0
        for g in garments:
            tags = cls.parse_tags(g['occasion_tags'])
            if occasion in tags:
                match_count += 1
        match_score = match_count / len(garments)
        return (match_score - 1.0) * cls.OCCASION_TAG_WEIGHT

    @classmethod
    def calculate_occasion_formality_adjustment(cls, outfit, db, occasion: Optional[str]) -> float:
        """Soft penalty if average formality is outside the occasion's recommended range."""
        occasion = cls.resolve_occasion(occasion)
        if occasion is None:
            return 0.0
        profile = cls.OCCASION_PROFILES[occasion]
        garments = cls.get_outfit_garments(outfit, db)
        avg_formality = sum(g['formality'] for g in garments) / len(garments)
        min_ok = profile["formality_min"]
        max_ok = profile["formality_max"]
        if min_ok <= avg_formality <= max_ok:
            return 0.0
        if avg_formality < min_ok:
            distance = min_ok - avg_formality
        else:
            distance = avg_formality - max_ok
        # clamp distance effect to max 1.0 (5 points)
        normalized = min(1.0, distance / 5.0)
        return -normalized * cls.OCCASION_FORMALITY_WEIGHT
    
    @classmethod
    def score_calculator(cls, outfit, db, season: Optional[str] = None, occasion: Optional[str] = None) -> float:
        color_weight = cls.weights['color_weight']
        pattern_weight = cls.weights['pattern_weight']
        formality_weight = cls.weights['formality_weight']
        # Caso 1: shoes + bottom + base_top
        if outfit.mid_top is None and outfit.outerwear is None:
            shoes = db.get_garment(outfit.shoes)
            bottom = db.get_garment(outfit.bottom)
            base_top = db.get_garment(outfit.base_top)
            lab_shoes = cls.extract_lab(shoes)
            lab_bottom = cls.extract_lab(bottom)
            lab_base_top = cls.extract_lab(base_top)
            is_shoes_neutral = cls.is_neutral_color(shoes)
            is_bottom_neutral = cls.is_neutral_color(bottom)
            is_base_top_neutral = cls.is_neutral_color(base_top)

            distance_base_top_to_bottom = cls.calculate_lab_distance(lab_bottom, lab_base_top)
            score_base_top_to_bottom = cls.score_color_pair(distance_base_top_to_bottom, is_base_top_neutral, is_bottom_neutral)
            distance_base_top_to_shoes = cls.calculate_lab_distance(lab_base_top, lab_shoes)
            score_base_top_to_shoes = cls.score_color_pair(distance_base_top_to_shoes, is_base_top_neutral, is_shoes_neutral)

            color_score = (score_base_top_to_bottom*1.0 + score_base_top_to_shoes*0.8)/1.8
        # Caso 2: shoes + bottom + base_top + mid_top
        elif outfit.outerwear is None:
            shoes = db.get_garment(outfit.shoes)
            bottom = db.get_garment(outfit.bottom)
            base_top = db.get_garment(outfit.base_top)
            mid_top = db.get_garment(outfit.mid_top)
            lab_shoes = cls.extract_lab(shoes)
            lab_bottom = cls.extract_lab(bottom)
            lab_base_top = cls.extract_lab(base_top)
            lab_mid_top = cls.extract_lab(mid_top)
            is_shoes_neutral = cls.is_neutral_color(shoes)
            is_bottom_neutral = cls.is_neutral_color(bottom)
            is_base_top_neutral = cls.is_neutral_color(base_top)
            is_mid_top_neutral = cls.is_neutral_color(mid_top)

            distance_mid_top_to_bottom = cls.calculate_lab_distance(lab_mid_top, lab_bottom)
            score_mid_top_to_bottom = cls.score_color_pair(distance_mid_top_to_bottom, is_mid_top_neutral, is_bottom_neutral)
            distance_mid_top_to_shoes = cls.calculate_lab_distance(lab_mid_top, lab_shoes)
            score_mid_top_to_shoes = cls.score_color_pair(distance_mid_top_to_shoes, is_mid_top_neutral, is_shoes_neutral)
            distance_mid_top_to_base_top = cls.calculate_lab_distance(lab_mid_top, lab_base_top)
            score_mid_top_to_base_top = cls.score_color_pair(distance_mid_top_to_base_top, is_mid_top_neutral, is_base_top_neutral)
            
            color_score = (score_mid_top_to_bottom*1.0 + score_mid_top_to_shoes*0.8 + score_mid_top_to_base_top*0.5)/(1.0+0.8+0.5)
        # Caso 3: shoes + bottom + base_top + outerwear
        elif outfit.mid_top is None:
            shoes = db.get_garment(outfit.shoes)
            bottom = db.get_garment(outfit.bottom)
            base_top = db.get_garment(outfit.base_top)
            outerwear = db.get_garment(outfit.outerwear)
            lab_shoes = cls.extract_lab(shoes)
            lab_bottom = cls.extract_lab(bottom)
            lab_base_top = cls.extract_lab(base_top)
            lab_outerwear = cls.extract_lab(outerwear)
            is_shoes_neutral = cls.is_neutral_color(shoes)
            is_bottom_neutral = cls.is_neutral_color(bottom)
            is_base_top_neutral = cls.is_neutral_color(base_top)
            is_outerwear_neutral = cls.is_neutral_color(outerwear)

            distance_base_to_bottom = cls.calculate_lab_distance(lab_base_top, lab_bottom)
            score_base_top_to_bottom = cls.score_color_pair(distance_base_to_bottom, is_base_top_neutral, is_bottom_neutral)
            distance_base_to_shoes = cls.calculate_lab_distance(lab_base_top, lab_shoes)
            score_base_top_to_shoes = cls.score_color_pair(distance_base_to_shoes, is_base_top_neutral, is_shoes_neutral)
            distance_outerwear_to_bottom = cls.calculate_lab_distance(lab_outerwear, lab_bottom)
            score_outerwear_to_bottom = cls.score_color_pair(distance_outerwear_to_bottom, is_outerwear_neutral, is_bottom_neutral)
            distance_outerwear_to_shoes = cls.calculate_lab_distance(lab_outerwear, lab_shoes)
            score_outerwear_to_shoes = cls.score_color_pair(distance_outerwear_to_shoes, is_outerwear_neutral, is_shoes_neutral)
            distance_outerwear_to_base_top = cls.calculate_lab_distance(lab_outerwear, lab_base_top)
            score_outerwear_to_base_top = cls.score_color_pair(distance_outerwear_to_base_top, is_outerwear_neutral, is_base_top_neutral)
            
            color_score = (score_base_top_to_bottom*1.0 + score_base_top_to_shoes*0.8 + score_outerwear_to_bottom*0.4 + score_outerwear_to_shoes*0.3 + score_outerwear_to_base_top*0.3)/(1.0+0.8+0.4+0.3+0.3)
        # Caso 4: shoes + bottom + base_top + mid_top + outerwear
        else:
            shoes = db.get_garment(outfit.shoes)
            bottom = db.get_garment(outfit.bottom)
            base_top = db.get_garment(outfit.base_top)
            mid_top = db.get_garment(outfit.mid_top)
            outerwear = db.get_garment(outfit.outerwear)
            lab_shoes = cls.extract_lab(shoes)
            lab_bottom = cls.extract_lab(bottom)
            lab_base_top = cls.extract_lab(base_top)
            lab_mid_top = cls.extract_lab(mid_top)
            lab_outerwear = cls.extract_lab(outerwear)
            is_shoes_neutral = cls.is_neutral_color(shoes)
            is_bottom_neutral = cls.is_neutral_color(bottom)
            is_base_top_neutral = cls.is_neutral_color(base_top)
            is_mid_top_neutral = cls.is_neutral_color(mid_top)
            is_outerwear_neutral = cls.is_neutral_color(outerwear)

            distance_mid_top_to_bottom = cls.calculate_lab_distance(lab_mid_top, lab_bottom)
            score_mid_top_to_bottom = cls.score_color_pair(distance_mid_top_to_bottom, is_mid_top_neutral, is_bottom_neutral)
            distance_mid_top_to_shoes = cls.calculate_lab_distance(lab_mid_top, lab_shoes)
            score_mid_top_to_shoes = cls.score_color_pair(distance_mid_top_to_shoes, is_mid_top_neutral, is_shoes_neutral)
            distance_mid_top_to_base_top = cls.calculate_lab_distance(lab_mid_top, lab_base_top)
            score_mid_top_to_base_top = cls.score_color_pair(distance_mid_top_to_base_top, is_mid_top_neutral, is_base_top_neutral)
            distance_outerwear_to_bottom = cls.calculate_lab_distance(lab_outerwear, lab_bottom)
            score_outerwear_to_bottom = cls.score_color_pair(distance_outerwear_to_bottom, is_outerwear_neutral, is_bottom_neutral)
            distance_outerwear_to_shoes = cls.calculate_lab_distance(lab_outerwear, lab_shoes)
            score_outerwear_to_shoes = cls.score_color_pair(distance_outerwear_to_shoes, is_outerwear_neutral, is_shoes_neutral)
            distance_outerwear_to_mid_top = cls.calculate_lab_distance(lab_outerwear, lab_mid_top)
            score_outerwear_to_mid_top = cls.score_color_pair(distance_outerwear_to_mid_top, is_outerwear_neutral, is_mid_top_neutral)
            
            color_score = (score_mid_top_to_bottom*1.0 + score_mid_top_to_shoes*0.8 + score_mid_top_to_base_top*0.5 + score_outerwear_to_bottom*0.3 + score_outerwear_to_shoes*0.3 + score_outerwear_to_mid_top*0.3)/(1.0+0.8+0.5+0.3+0.3+0.3)
        
        pattern_score = cls.calculate_pattern_coherence(outfit, db)
        coherence_score = cls.calculate_formality_alignment(outfit, db)

        target_score = cls.calculate_target_formality_score(outfit, db)

        # Combina coherence and target preference (70% coherence, 30% target)
        formality_score = 0.7 * coherence_score + 0.3 * target_score
        
        neutral_penalty = cls.calculate_neutral_penalty(outfit, db)
        color_bonus = cls.calculate_color_diversity_bonus(outfit, db)
        simplicity_bonus = cls.calculate_simplicity_bonus(outfit)
        pair_penalties = cls.calculate_pair_penalties(outfit, db)
        recently_worn_penalty = cls.calculate_recently_worn_penalty(outfit, db)
        
        # Phase 3 adjustments
        season_adjustment = cls.calculate_season_adjustment(outfit, db, season)
        occasion_tag_adjustment = cls.calculate_occasion_tag_adjustment(outfit, db, occasion)
        occasion_formality_adjustment = cls.calculate_occasion_formality_adjustment(outfit, db, occasion)

        total_score = (color_score * color_weight + 
                       pattern_score * pattern_weight + 
                       formality_score * formality_weight + 
                       neutral_penalty + color_bonus + simplicity_bonus + 
                       pair_penalties + recently_worn_penalty +
                       season_adjustment + occasion_tag_adjustment + occasion_formality_adjustment)

        return max(0.0, min(1.0, total_score))
    
    @classmethod
    def debug_score_breakdown(cls, outfit, db, season: Optional[str] = None, occasion: Optional[str] = None):
        """Mostra i dettagli dello scoring"""

        print("--- Garment Details ---")
        shoes = db.get_garment(outfit.shoes)
        bottom = db.get_garment(outfit.bottom)
        base = db.get_garment(outfit.base_top)
        print(f"Shoes: {shoes['name']} (neutral: {cls.is_neutral_color(shoes)}, formality: {shoes['formality']}, pattern: {shoes['pattern']})")
        print(f"Bottom: {bottom['name']} (neutral: {cls.is_neutral_color(bottom)}, formality: {bottom['formality']}, pattern: {bottom['pattern']})")
        print(f"Base: {base['name']} (neutral: {cls.is_neutral_color(base)}, formality: {base['formality']}, pattern: {base['pattern']})")
        if outfit.mid_top:
            mid = db.get_garment(outfit.mid_top)
            print(f"Mid: {mid['name']} (neutral: {cls.is_neutral_color(mid)}, formality: {mid['formality']}, pattern: {mid['pattern']})")
        if outfit.outerwear:
            outer = db.get_garment(outfit.outerwear)
            print(f"Outer: {outer['name']} (neutral: {cls.is_neutral_color(outer)}, formality: {outer['formality']}, pattern: {outer['pattern']})")
        
        # === LAYER COUNT ===
        layer_count = 3
        if outfit.mid_top:
            layer_count += 1
        if outfit.outerwear:
            layer_count += 1
        print(f"\nTotal layers: {layer_count}")

        # === COLOR DISTANCES ===
        print("\n--- Color Distances (CIELAB) ---")
    
        if outfit.mid_top:
            mid = db.get_garment(outfit.mid_top)
            lab_mid = cls.extract_lab(mid)
            lab_bottom = cls.extract_lab(bottom)
            lab_shoes = cls.extract_lab(shoes)
            lab_base = cls.extract_lab(base)

            dist_mid_bottom = cls.calculate_lab_distance(lab_mid, lab_bottom)
            dist_mid_shoes = cls.calculate_lab_distance(lab_mid, lab_shoes)
            dist_mid_base = cls.calculate_lab_distance(lab_mid, lab_base)

            print(f"Mid → Bottom: {dist_mid_bottom:.1f}")
            print(f"Mid → Shoes: {dist_mid_shoes:.1f}")
            print(f"Mid → Base: {dist_mid_base:.1f}")

            if outfit.outerwear:
                outer = db.get_garment(outfit.outerwear)
                lab_outer = cls.extract_lab(outer)
                dist_outer_bottom = cls.calculate_lab_distance(lab_outer, lab_bottom)
                dist_outer_shoes = cls.calculate_lab_distance(lab_outer, lab_shoes)
                dist_outer_mid = cls.calculate_lab_distance(lab_outer, lab_mid)

                print(f"Outer → Bottom: {dist_outer_bottom:.1f}")
                print(f"Outer → Shoes: {dist_outer_shoes:.1f}")
                print(f"Outer → Mid: {dist_outer_mid:.1f}")
        else:
            # Solo base (no mid)
            lab_base = cls.extract_lab(base)
            lab_bottom = cls.extract_lab(bottom)
            lab_shoes = cls.extract_lab(shoes)

            dist_base_bottom = cls.calculate_lab_distance(lab_base, lab_bottom)
            dist_base_shoes = cls.calculate_lab_distance(lab_base, lab_shoes)

            print(f"Base → Bottom: {dist_base_bottom:.1f}")
            print(f"Base → Shoes: {dist_base_shoes:.1f}")

            if outfit.outerwear:
                outer = db.get_garment(outfit.outerwear)
                lab_outer = cls.extract_lab(outer)
                dist_outer_bottom = cls.calculate_lab_distance(lab_outer, lab_bottom)
                dist_outer_shoes = cls.calculate_lab_distance(lab_outer, lab_shoes)
                dist_outer_base = cls.calculate_lab_distance(lab_outer, lab_base)

                print(f"Outer → Bottom: {dist_outer_bottom:.1f}")
                print(f"Outer → Shoes: {dist_outer_shoes:.1f}")
                print(f"Outer → Base: {dist_outer_base:.1f}")
        
        # === SCORE COMPONENTS ===
        print("\n--- Score Components ---")

        # Ricalcola i componenti individuali (potrebbero essere già calcolati, ma ricalicoliamoli per debug)
        pattern_score = cls.calculate_pattern_coherence(outfit, db)
        formality_score = cls.calculate_formality_alignment(outfit, db)
        neutral_penalty = cls.calculate_neutral_penalty(outfit, db)
        color_bonus = cls.calculate_color_diversity_bonus(outfit, db)
        simplicity_bonus = cls.calculate_simplicity_bonus(outfit)
        pair_penalties = cls.calculate_pair_penalties(outfit, db)

        print(f"Pattern coherence: {pattern_score:.3f}")
        print(f"Formality alignment: {formality_score:.3f}")
        print(f"Neutral penalty: {neutral_penalty:+.3f}")  # +/- sign
        print(f"Color diversity bonus: {color_bonus:+.3f}")
        print(f"Simplicity bonus: {simplicity_bonus:+.3f}")
        print(f"Pair penalties: {pair_penalties:+.3f}")

        # === FORMALITY DETAILS ===
        print("\n--- Formality Details ---")
        formalities = [shoes['formality'], bottom['formality'], base['formality']]
        if outfit.mid_top:
            formalities.append(db.get_garment(outfit.mid_top)['formality'])
        if outfit.outerwear:
            formalities.append(db.get_garment(outfit.outerwear)['formality'])

        print(f"Range: {min(formalities)} - {max(formalities)} (gap: {max(formalities) - min(formalities)})")

        # === PATTERN DETAILS ===
        print("\n--- Pattern Details ---")

        # Determina quale top è visibile
        if outfit.outerwear:
            visible_top = db.get_garment(outfit.outerwear)
            visible_top_name = "Outer"
        elif outfit.mid_top:
            visible_top = db.get_garment(outfit.mid_top)
            visible_top_name = "Mid"
        else:
            visible_top = base
            visible_top_name = "Base"

        print(f"Visible top: {visible_top_name}")
        print(f"  Shoes pattern weight: {cls.get_pattern_weight(shoes['pattern'])}")
        print(f"  Bottom pattern weight: {cls.get_pattern_weight(bottom['pattern'])}")
        print(f"  {visible_top_name} pattern weight: {cls.get_pattern_weight(visible_top['pattern'])}")

        print("\n--- Phase 3 Context Adjustments ---")
        if season is not None and season != "none":
            resolved = cls.resolve_season(season)
            if resolved:
                total_warmth = cls.calculate_total_warmth(outfit, db)
                profile = cls.SEASON_WARMTH_PROFILES[resolved]
                print(f"Season: {resolved} | total warmth: {total_warmth} (target {profile['target']}, tolerance {profile['tolerance']})")
                season_adj = cls.calculate_season_adjustment(outfit, db, season)
                print(f"Season adjustment: {season_adj:+.3f}")
        else:
            print("Season context: none")

        if occasion is not None and occasion != "none":
            occ_adj_tag = cls.calculate_occasion_tag_adjustment(outfit, db, occasion)
            occ_adj_form = cls.calculate_occasion_formality_adjustment(outfit, db, occasion)
            print(f"Occasion: {occasion} | tag adjustment: {occ_adj_tag:+.3f}, formality adjustment: {occ_adj_form:+.3f}")
        else:
            print("Occasion context: none")
        # === FINAL SCORE ===
        print(f"\n--- Final Score: {outfit.score:.3f} ---")

    @classmethod
    def generate(cls, shoes_list, bottoms_list, base_tops_list, mid_tops_list, outerwear_list, db, count: int = 1, top_pool: int = 150, season: Optional[str] = None, occasion: Optional[str] = None) -> list[Outfit]:
        # Use adaptive formality threshold for hard filtering
        formality_threshold = cls.weights.get('formality_threshold', 4)
        mid_options = [None] + mid_tops_list
        outer_options = [None] + outerwear_list

        all_combinations = product(
            shoes_list,
            bottoms_list,
            base_tops_list,
            mid_options,
            outer_options
        )
        
        valid_outfits = []
        for shoes, bottom, base, mid, outer in all_combinations:
            # Validazione formality range
            formalities = [shoes['formality'], bottom['formality'], base['formality']]
            if mid is not None: formalities.append(mid['formality'])
            if outer is not None: formalities.append(outer['formality'])
            if max(formalities) - min(formalities) > formality_threshold:
                continue # gap troppo grande
            # Crea outfit candidato
            outfit = Outfit(
                shoes=shoes['id'],
                bottom=bottom['id'],
                base_top=base['id'],
                mid_top=mid['id'] if mid else None,
                outerwear=outer['id'] if outer else None
            )

            if not cls.is_seasonally_valid(outfit, db, season):
                continue

            outfit.score = cls.score_calculator(outfit, db, season=season, occasion=occasion)
            valid_outfits.append(outfit)
        
        if not valid_outfits:
            print("Wardrobe insufficiente per generare outfit!")
            return []
        if len(valid_outfits) < count:
            print(f"Trovati solo {len(valid_outfits)} outfit validi")
            return valid_outfits  # ritorna tutti
        # Prima del sort
        print(f"Outfit validi generati: {len(valid_outfits)}")

        # Conta quante volte ogni capo appare
        #from collections import Counter
        #mid_usage = Counter(o.mid_top for o in valid_outfits if o.mid_top)
        #print("Uso mid_tops:", mid_usage)
        
        valid_outfits.sort(key=lambda x: x.score, reverse=True)

        # Dopo il sort, guarda i top 10
        print("\nTop 10 outfit per score:")
        for i, o in enumerate(valid_outfits[:10], 1):
            print(f"{i}. Score: {o.score:.3f} - Mid: {o.mid_top}")

        top_candidates = valid_outfits[:top_pool]
        pool_size = min(top_pool, len(top_candidates))
        # Sceglie random K da questo pool
        selected = random.sample(top_candidates, min(count, pool_size))
        return selected