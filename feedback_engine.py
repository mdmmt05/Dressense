from db_manager import DB_Manager, FeedbackReason, WeightsManager
from itertools import combinations
from outfit_engine import OutfitGenerator

# === COSTANTI DI CALIBRAZIONE ===
# Pesi globali
WEIGHT_ADJUSTMENT_SMALL = 0.02
WEIGHT_ADJUSTMENT_MEDIUM = 0.03
WEIGHT_ADJUSTMENT_LARGE = 0.05

# Threshold
THRESHOLD_ADJUSTMENT_FORMALITY = 0.5
THRESHOLD_ADJUSTMENT_NEUTRAL = 2.0

# Penalità coppie
PAIR_PENALTY_LIGHT = -0.03
PAIR_PENALTY_MEDIUM = -0.05
PAIR_PENALTY_HEAVY = -0.08

class FeedbackManager:
    def __init__(self, db: DB_Manager):
        self.db = db
    
    def _get_garment_ids_from_outfit(self, outfit) -> list[int]:
        """Estrae tutti i garment_id dall'outfit (esclusi None)"""
        ids = [outfit.shoes, outfit.bottom, outfit.base_top]
        if outfit.mid_top:
            ids.append(outfit.mid_top)
        if outfit.outerwear:
            ids.append(outfit.outerwear)
        return ids
    
    def _generate_all_pairs(self, garment_ids: list[int]) -> list[tuple]:
        """Genera tutte le coppie possibili da una lista di ID"""
        return list(combinations(garment_ids, 2))
    
    def _apply_weight_adjustments(self, reason: str, weights_mgr: WeightsManager):
        """Modifica i pesi globali in base alla reason"""

        if reason == FeedbackReason.TOO_FORMAL.value:
            old_fw = weights_mgr.get_weight('formality_weight')
            new_fw = weights_mgr.adjust_weight('formality_weight', -WEIGHT_ADJUSTMENT_SMALL)
            print(f"  → formality_weight: {old_fw:.3f} → {new_fw:.3f}")
            
            old_ft = weights_mgr.get_weight('formality_threshold')
            new_ft = weights_mgr.adjust_weight('formality_threshold', -THRESHOLD_ADJUSTMENT_FORMALITY)
            print(f"  → formality_threshold: {old_ft:.1f} → {new_ft:.1f}")
    
        elif reason == FeedbackReason.TOO_CASUAL.value:
            old_fw = weights_mgr.get_weight('formality_weight')
            new_fw = weights_mgr.adjust_weight('formality_weight', +WEIGHT_ADJUSTMENT_SMALL)
            print(f"  → formality_weight: {old_fw:.3f} → {new_fw:.3f}")

        elif reason == FeedbackReason.TOO_MANY_NEUTRALS.value:
            old_ns = weights_mgr.get_weight('neutral_saturation_threshold')
            new_ns = weights_mgr.adjust_weight('neutral_saturation_threshold', -THRESHOLD_ADJUSTMENT_NEUTRAL)
            print(f"  → neutral_saturation_threshold: {old_ns:.1f} → {new_ns:.1f}")

        elif reason == FeedbackReason.BORING.value:
            old_cw = weights_mgr.get_weight('color_weight')
            new_cw = weights_mgr.adjust_weight('color_weight', +WEIGHT_ADJUSTMENT_MEDIUM)
            print(f"  → color_weight: {old_cw:.3f} → {new_cw:.3f}")

            old_pw = weights_mgr.get_weight('pattern_weight')
            new_pw = weights_mgr.adjust_weight('pattern_weight', -WEIGHT_ADJUSTMENT_SMALL)
            print(f"  → pattern_weight: {old_pw:.3f} → {new_pw:.3f}")

        elif reason == FeedbackReason.TOO_FLASHY.value:
            old_cw = weights_mgr.get_weight('color_weight')
            new_cw = weights_mgr.adjust_weight('color_weight', -WEIGHT_ADJUSTMENT_MEDIUM)
            print(f"  → color_weight: {old_cw:.3f} → {new_cw:.3f}")

        elif reason == FeedbackReason.BAD_LAYERING.value:
            old_pw = weights_mgr.get_weight('pattern_weight')
            new_pw = weights_mgr.adjust_weight('pattern_weight', +WEIGHT_ADJUSTMENT_SMALL)
            print(f"  → pattern_weight: {old_pw:.3f} → {new_pw:.3f}")

        # COLORS_CLASH e DONT_LIKE_COMBINATION non modificano pesi globali
    
    def _apply_pair_penalties(self, outfit, reason: str, weights_mgr: WeightsManager):
        """Applica penalità alle coppie di item dell'outfit"""

        # Solo alcune reason causano penalità di coppia
        if reason not in [FeedbackReason.COLORS_CLASH.value, FeedbackReason.DONT_LIKE_COMBINATION.value]:
            return
        
        # Determina l'entità della penalità
        if reason == FeedbackReason.COLORS_CLASH.value:
            penalty = PAIR_PENALTY_HEAVY
        else:
            penalty = PAIR_PENALTY_MEDIUM
        
        # Genera tutte le coppie
        garment_ids = self._get_garment_ids_from_outfit(outfit)
        pairs = self._generate_all_pairs(garment_ids)

        # Applica penalità
        for id1, id2 in pairs:
            weights_mgr.add_pair_penalty(id1, id2, penalty)
        
        print(f"  → {len(pairs)} coppie penalizzate ({penalty:.3f} ciascuna)")
    
    def process_feedback(self, outfit, verdict, reason=None):
        """Processa feedback e aggiorna pesi/penalità"""
        # 1. Registra nel database
        self.db.add_feedback(
            shoes_id=outfit.shoes,
            bottom_id=outfit.bottom,
            base_top_id=outfit.base_top,
            mid_top_id=outfit.mid_top,
            outerwear_id=outfit.outerwear,
            verdict=verdict,
            reason=reason
        )
        
        # Se positivo, stop
        if verdict == 1:
            print("✓ Feedback positivo registrato!")
            return
        
        print("✓ Feedback negativo registrato")
        print("\n📊 Applicazione adattamenti...")

        # 2. Crea WeightsManager
        weights_mgr = WeightsManager(self.db)

        # 3. Applica modifiche
        self._apply_weight_adjustments(reason, weights_mgr)
        self._apply_pair_penalties(outfit, reason, weights_mgr)

        # 4. Ricarica pesi nell'engine
        OutfitGenerator.load_weights(weights_mgr.get_all_weights())

        print("\n✓ Adattamenti completati!\n")