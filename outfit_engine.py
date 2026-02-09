from dataclasses import dataclass
from typing import Optional
from itertools import product
import random
import math
from db_manager import DB_Manager

FORMALITY_THRESHOLD = 3
NEUTRAL_SATURATION_THRESHOLD = 15
BASE_TOP_TO_BOTTOM_MULTIPLIER = 1.0
BASE_TOP_TO_SHOES_MULTIPLIER = 0.8

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
                return 0.7
            elif distance > 70:
                return 0.8
            else:
                return 0.95
        else:
            if distance < 15:
                return 0.4
            elif distance > 60:
                return 0.3
            elif 25 <= distance <= 45:
                return 1.0
            else:
                return 0.7

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
            return total_score
        # Caso 2: shoes + bottom + base_top + mid_top
        # Caso 3: shoes + bottom + base_top + mid_top + outerwear
        # Caso 2: shoes + bottom + base_top + outerwear
        return 0.0

    @staticmethod
    def generate(shoes_list, bottoms_list, base_tops_list, mid_tops_list, outerwear_list, db, count: int = 1, top_pool: int = 20) -> list[Outfit]:
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
        valid_outfits.sort(key=lambda x: x.score, reverse=True)
        top_candidates = valid_outfits[:top_pool]
        pool_size = min(top_pool, len(top_candidates))
        # Sceglie random K da questo pool
        selected = random.sample(top_candidates, min(count, pool_size))
        return selected