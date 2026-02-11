from dataclasses import dataclass
from typing import Optional
from itertools import product
import random
import math
from db_manager import DB_Manager

FORMALITY_THRESHOLD = 4
NEUTRAL_SATURATION_THRESHOLD = 20

BASE_TOP_TO_BOTTOM_MULTIPLIER = 1.0
BASE_TOP_TO_SHOES_MULTIPLIER = 0.8

MID_TOP_TO_BOTTOM_MULTIPLIER = 1.0
MID_TOP_TO_SHOES_MULTIPLIER = 0.8
MID_TOP_TO_BASE_TOP_MULTIPLIER = 0.5

OUTERWEAR_TO_BOTTOM_MULTIPLIER = 0.6
OUTERWEAR_TO_SHOES_MULTIPLIER = 0.5
OUTERWEAR_TO_BASE_TOP_MULTIPLIER = 0.4

OUTERWEAR_TO_MID_TOP_MULTIPLIER = 0.4

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
        a = garment['color_lab_a']
        b = garment['color_lab_b']

        # Calcola la saturazione (distanza dall'asse L)
        saturation = math.sqrt(a**2 + b**2)
        return saturation < NEUTRAL_SATURATION_THRESHOLD
    
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
    def score_calculator(outfit, db) -> float:
        # Caso 1: shoes + bottom + base_top
        if outfit.mid_top is None and outfit.outerwear is None:
            shoes = db.get_garment(outfit.shoes)
            bottom = db.get_garment(outfit.bottom)
            base_top = db.get_garment(outfit.base_top)
            lab_shoes = OutfitGenerator.extract_lab(shoes)
            lab_bottom = OutfitGenerator.extract_lab(bottom)
            lab_base_top = OutfitGenerator.extract_lab(base_top)
            is_shoes_neutral = OutfitGenerator.is_neutral_color(shoes)
            is_bottom_neutral = OutfitGenerator.is_neutral_color(bottom)
            is_base_top_neutral = OutfitGenerator.is_neutral_color(base_top)

            distance_base_top_to_bottom = OutfitGenerator.calculate_lab_distance(lab_bottom, lab_base_top)
            score_base_top_to_bottom = OutfitGenerator.score_color_pair(distance_base_top_to_bottom, is_base_top_neutral, is_bottom_neutral)
            distance_base_top_to_shoes = OutfitGenerator.calculate_lab_distance(lab_base_top, lab_shoes)
            score_base_top_to_shoes = OutfitGenerator.score_color_pair(distance_base_top_to_shoes, is_base_top_neutral, is_shoes_neutral)
            total_score = (score_base_top_to_bottom*BASE_TOP_TO_BOTTOM_MULTIPLIER + score_base_top_to_shoes*BASE_TOP_TO_SHOES_MULTIPLIER)/(BASE_TOP_TO_BOTTOM_MULTIPLIER+BASE_TOP_TO_SHOES_MULTIPLIER)
        # Caso 2: shoes + bottom + base_top + mid_top
        elif outfit.outerwear is None:
            shoes = db.get_garment(outfit.shoes)
            bottom = db.get_garment(outfit.bottom)
            base_top = db.get_garment(outfit.base_top)
            mid_top = db.get_garment(outfit.mid_top)
            lab_shoes = OutfitGenerator.extract_lab(shoes)
            lab_bottom = OutfitGenerator.extract_lab(bottom)
            lab_base_top = OutfitGenerator.extract_lab(base_top)
            lab_mid_top = OutfitGenerator.extract_lab(mid_top)
            is_shoes_neutral = OutfitGenerator.is_neutral_color(shoes)
            is_bottom_neutral = OutfitGenerator.is_neutral_color(bottom)
            is_base_top_neutral = OutfitGenerator.is_neutral_color(base_top)
            is_mid_top_neutral = OutfitGenerator.is_neutral_color(mid_top)

            distance_mid_top_to_bottom = OutfitGenerator.calculate_lab_distance(lab_mid_top, lab_bottom)
            score_mid_top_to_bottom = OutfitGenerator.score_color_pair(distance_mid_top_to_bottom, is_mid_top_neutral, is_bottom_neutral)
            distance_mid_top_to_shoes = OutfitGenerator.calculate_lab_distance(lab_mid_top, lab_shoes)
            score_mid_top_to_shoes = OutfitGenerator.score_color_pair(distance_mid_top_to_shoes, is_mid_top_neutral, is_shoes_neutral)
            distance_mid_top_to_base_top = OutfitGenerator.calculate_lab_distance(lab_mid_top, lab_base_top)
            score_mid_top_to_base_top = OutfitGenerator.score_color_pair(distance_mid_top_to_base_top, is_mid_top_neutral, is_base_top_neutral)
            total_score = (score_mid_top_to_bottom*MID_TOP_TO_BOTTOM_MULTIPLIER + score_mid_top_to_shoes*MID_TOP_TO_SHOES_MULTIPLIER + score_mid_top_to_base_top*MID_TOP_TO_BASE_TOP_MULTIPLIER)/(MID_TOP_TO_BOTTOM_MULTIPLIER + MID_TOP_TO_SHOES_MULTIPLIER + MID_TOP_TO_BASE_TOP_MULTIPLIER)
        # Caso 3: shoes + bottom + base_top + outerwear
        elif outfit.mid_top is None:
            shoes = db.get_garment(outfit.shoes)
            bottom = db.get_garment(outfit.bottom)
            base_top = db.get_garment(outfit.base_top)
            outerwear = db.get_garment(outfit.outerwear)
            lab_shoes = OutfitGenerator.extract_lab(shoes)
            lab_bottom = OutfitGenerator.extract_lab(bottom)
            lab_base_top = OutfitGenerator.extract_lab(base_top)
            lab_outerwear = OutfitGenerator.extract_lab(outerwear)
            is_shoes_neutral = OutfitGenerator.is_neutral_color(shoes)
            is_bottom_neutral = OutfitGenerator.is_neutral_color(bottom)
            is_base_top_neutral = OutfitGenerator.is_neutral_color(base_top)
            is_outerwear_neutral = OutfitGenerator.is_neutral_color(outerwear)

            distance_outerwear_to_bottom = OutfitGenerator.calculate_lab_distance(lab_outerwear, lab_bottom)
            score_outerwear_to_bottom = OutfitGenerator.score_color_pair(distance_outerwear_to_bottom, is_outerwear_neutral, is_bottom_neutral)
            distance_outerwear_to_shoes = OutfitGenerator.calculate_lab_distance(lab_outerwear, lab_shoes)
            score_outerwear_to_shoes = OutfitGenerator.score_color_pair(distance_outerwear_to_shoes, is_outerwear_neutral, is_shoes_neutral)
            distance_outerwear_to_base_top = OutfitGenerator.calculate_lab_distance(lab_outerwear, lab_base_top)
            score_outerwear_to_base_top = OutfitGenerator.score_color_pair(distance_outerwear_to_base_top, is_outerwear_neutral, is_base_top_neutral)
            total_score = (score_outerwear_to_bottom*OUTERWEAR_TO_BOTTOM_MULTIPLIER + score_outerwear_to_shoes*OUTERWEAR_TO_SHOES_MULTIPLIER + score_outerwear_to_base_top*OUTERWEAR_TO_BASE_TOP_MULTIPLIER)/(OUTERWEAR_TO_BOTTOM_MULTIPLIER + OUTERWEAR_TO_SHOES_MULTIPLIER + OUTERWEAR_TO_BASE_TOP_MULTIPLIER)
        # Caso 4: shoes + bottom + base_top + mid_top + outerwear
        else:
            shoes = db.get_garment(outfit.shoes)
            bottom = db.get_garment(outfit.bottom)
            base_top = db.get_garment(outfit.base_top)
            mid_top = db.get_garment(outfit.mid_top)
            outerwear = db.get_garment(outfit.outerwear)
            lab_shoes = OutfitGenerator.extract_lab(shoes)
            lab_bottom = OutfitGenerator.extract_lab(bottom)
            lab_base_top = OutfitGenerator.extract_lab(base_top)
            lab_mid_top = OutfitGenerator.extract_lab(mid_top)
            lab_outerwear = OutfitGenerator.extract_lab(outerwear)
            is_shoes_neutral = OutfitGenerator.is_neutral_color(shoes)
            is_bottom_neutral = OutfitGenerator.is_neutral_color(bottom)
            is_base_top_neutral = OutfitGenerator.is_neutral_color(base_top)
            is_mid_top_neutral = OutfitGenerator.is_neutral_color(mid_top)
            is_outerwear_neutral = OutfitGenerator.is_neutral_color(outerwear)

            distance_mid_top_to_bottom = OutfitGenerator.calculate_lab_distance(lab_mid_top, lab_bottom)
            score_mid_top_to_bottom = OutfitGenerator.score_color_pair(distance_mid_top_to_bottom, is_mid_top_neutral, is_bottom_neutral)
            distance_mid_top_to_shoes = OutfitGenerator.calculate_lab_distance(lab_mid_top, lab_shoes)
            score_mid_top_to_shoes = OutfitGenerator.score_color_pair(distance_mid_top_to_shoes, is_mid_top_neutral, is_shoes_neutral)
            distance_mid_top_to_base_top = OutfitGenerator.calculate_lab_distance(lab_mid_top, lab_base_top)
            score_mid_top_to_base_top = OutfitGenerator.score_color_pair(distance_mid_top_to_base_top, is_mid_top_neutral, is_base_top_neutral)
            distance_outerwear_to_bottom = OutfitGenerator.calculate_lab_distance(lab_outerwear, lab_bottom)
            score_outerwear_to_bottom = OutfitGenerator.score_color_pair(distance_outerwear_to_bottom, is_outerwear_neutral, is_bottom_neutral)
            distance_outerwear_to_shoes = OutfitGenerator.calculate_lab_distance(lab_outerwear, lab_shoes)
            score_outerwear_to_shoes = OutfitGenerator.score_color_pair(distance_outerwear_to_shoes, is_outerwear_neutral, is_shoes_neutral)
            distance_outerwear_to_mid_top = OutfitGenerator.calculate_lab_distance(lab_outerwear, lab_mid_top)
            score_outerwear_to_mid_top = OutfitGenerator.score_color_pair(distance_outerwear_to_mid_top, is_outerwear_neutral, is_mid_top_neutral)
            total_score = (score_mid_top_to_bottom*MID_TOP_TO_BOTTOM_MULTIPLIER + score_mid_top_to_shoes*MID_TOP_TO_SHOES_MULTIPLIER + score_mid_top_to_base_top*MID_TOP_TO_BASE_TOP_MULTIPLIER + score_outerwear_to_bottom*OUTERWEAR_TO_BOTTOM_MULTIPLIER + score_outerwear_to_shoes*OUTERWEAR_TO_SHOES_MULTIPLIER + score_outerwear_to_mid_top*OUTERWEAR_TO_MID_TOP_MULTIPLIER)/(MID_TOP_TO_BOTTOM_MULTIPLIER + MID_TOP_TO_SHOES_MULTIPLIER + MID_TOP_TO_BASE_TOP_MULTIPLIER + OUTERWEAR_TO_BOTTOM_MULTIPLIER + OUTERWEAR_TO_SHOES_MULTIPLIER + OUTERWEAR_TO_MID_TOP_MULTIPLIER)
        neutral_penalty = OutfitGenerator.calculate_neutral_penalty(outfit, db)
        color_bonus = OutfitGenerator.calculate_color_diversity_bonus(outfit, db)
        return max(0.0, total_score+neutral_penalty+color_bonus)
    
    @staticmethod
    def debug_score_breakdown(outfit, db):
        """Mostra i dettagli dello scoring"""
        shoes = db.get_garment(outfit.shoes)
        bottom = db.get_garment(outfit.bottom)
        base = db.get_garment(outfit.base_top)

        print(f"Shoes: {shoes['name']} (neutral: {OutfitGenerator.is_neutral_color(shoes)})")
        print(f"Bottom: {bottom['name']} (neutral: {OutfitGenerator.is_neutral_color(bottom)})")
        print(f"Base: {base['name']} (neutral: {OutfitGenerator.is_neutral_color(base)})")

        if outfit.mid_top:
            mid = db.get_garment(outfit.mid_top)
            print(f"Mid: {mid['name']} (neutral: {OutfitGenerator.is_neutral_color(mid)})")

            # Mostra distanze
            lab_mid = OutfitGenerator.extract_lab(mid)
            lab_bottom = OutfitGenerator.extract_lab(bottom)
            dist = OutfitGenerator.calculate_lab_distance(lab_mid, lab_bottom)
            print(f"  Distance mid→bottom: {dist:.1f}")

    @staticmethod
    def generate(shoes_list, bottoms_list, base_tops_list, mid_tops_list, outerwear_list, db, count: int = 1, top_pool: int = 150) -> list[Outfit]:
        # Logica generazionale
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
            if max(formalities) - min(formalities) > FORMALITY_THRESHOLD:
                continue # gap troppo grande
            # Crea outfit candidato
            outfit = Outfit(
                shoes=shoes['id'],
                bottom=bottom['id'],
                base_top=base['id'],
                mid_top=mid['id'] if mid else None,
                outerwear=outer['id'] if outer else None
            )
            
            outfit.score = OutfitGenerator.score_calculator(outfit, db)

            valid_outfits.append(outfit)
        
        if len(valid_outfits) == 0:
            print("Wardrobe insufficiente per generare outfit!")
            return []
        if len(valid_outfits) < count:
            print(f"Trovati solo {len(valid_outfits)} outfit validi")
            return valid_outfits  # ritorna tutti
        # Prima del sort
        print(f"Outfit validi generati: {len(valid_outfits)}")

        # Conta quante volte ogni capo appare
        from collections import Counter
        mid_usage = Counter(o.mid_top for o in valid_outfits if o.mid_top)
        print("Uso mid_tops:", mid_usage)

        # Dopo il sort, guarda i top 10
        print("\nTop 10 outfit per score:")
        for i, outfit in enumerate(valid_outfits[:10], 1):
            print(f"{i}. Score: {outfit.score:.3f} - Mid: {outfit.mid_top}")
        
        valid_outfits.sort(key=lambda x: x.score, reverse=True)
        top_candidates = valid_outfits[:top_pool]
        pool_size = min(top_pool, len(top_candidates))
        # Sceglie random K da questo pool
        selected = random.sample(top_candidates, min(count, pool_size))
        return selected