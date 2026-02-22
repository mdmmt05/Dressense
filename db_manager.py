import sqlite3
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

db_path = Path('data/wardrobe.db')
db_path.parent.mkdir(exist_ok=True) # Crea la cartella data se non esiste

@dataclass
class Garment:
    name: str
    category: str
    layer_role: str
    color_hex: str
    color_lab_l: float
    color_lab_a: float
    color_lab_b: float
    pattern:str
    warmth: int
    formality:int
    season_tags: str
    occasion_tags: str
    active: bool

@dataclass
class FeedbackReason(Enum):
    COLORS_CLASH = 'colors_clash'
    TOO_MANY_NEUTRALS = 'too_many_neutrals'
    TOO_FORMAL = 'too_formal'
    TOO_CASUAL = 'too_casual'
    BAD_LAYERING = 'bad_layering'
    DONT_LIKE_COMBINATION = 'dont_like_combination'
    BORING = 'boring'
    TOO_FLASHY = 'too_flashy'

class DB_Manager():
    def __init__(self):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._initialize_tables()
        self._initialize_defaults()

    def _initialize_tables(self):
        # Verifichiamo che la tabella 'garments' esista già
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS garment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                layer_role TEXT NOT NULL CHECK(layer_role IN ('base', 'mid', 'outer', 'none')),
                color_hex TEXT(7) NOT NULL,
                color_lab_l REAL NOT NULL,
                color_lab_a REAL NOT NULL,
                color_lab_b REAL NOT NULL,
                pattern TEXT NOT NULL,
                warmth INTEGER NOT NULL CHECK(warmth >= 1 AND warmth <= 10),
                formality INTEGER NOT NULL CHECK(formality >= 1 AND formality <= 10),
                season_tags TEXT NOT NULL,
                occasion_tags TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1))
            )               
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                outfit_signature TEXT NOT NULL,
                shoes_id INTEGER NOT NULL,
                bottom_id INTEGER NOT NULL,
                base_top_id INTEGER NOT NULL,
                mid_top_id INTEGER,
                outerwear_id INTEGER,
                verdict INTEGER NOT NULL CHECK(verdict IN (0, 1)),
                reason TEXT CHECK(reason IN ('colors_clash', 'too_many_neutrals', 'too_formal', 
                                               'too_casual', 'bad_layering', 
                                               'dont_like_combination', 'boring', 'too_flashy')),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shoes_id) REFERENCES garment(id),
                FOREIGN KEY (bottom_id) REFERENCES garment(id),
                FOREIGN KEY (base_top_id) REFERENCES garment(id),
                FOREIGN KEY (mid_top_id) REFERENCES garment(id),
                FOREIGN KEY (outerwear_id) REFERENCES garment(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weights (
                key TEXT PRIMARY KEY,
                value REAL NOT NULL,
                default_value REAL NOT NULL,
                min_value REAL NOT NULL,
                max_value REAL NOT NULL,
                last_modified DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS item_penalties (
                garment_id INTEGER PRIMARY KEY,
                penalty_score REAL NOT NULL DEFAULT 0.0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (garment_id) REFERENCES garment(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pair_penalties (
                garment_id_1 INTEGER NOT NULL,
                garment_id_2 INTEGER NOT NULL,
                penalty_score REAL NOT NULL DEFAULT 0.0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (garment_id_1, garment_id_2),
                FOREIGN KEY (garment_id_1) REFERENCES garment(id),
                FOREIGN KEY (garment_id_2) REFERENCES garment(id),
                CHECK (garment_id_1 < garment_id_2)
            )
        ''')
        self.conn.commit()

    def _initialize_defaults(self):
        '''Popola i pesi di default se la tabella è vuota'''
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM weights")
        count = cursor.fetchone()[0]

        if count == 0:
            defaults = [
                ('formality_threshold', 4, 4, 2, 8),
                ('neutral_saturation_threshold', 20, 20, 10, 40),
                ('color_weight', 0.55, 0.55, 0.1, 0.9),
                ('pattern_weight', 0.3, 0.3, 0.05, 0.7),
                ('formality_weight', 0.15, 0.15, 0.05, 0.5),
            ]
            cursor.executemany('''
                INSERT INTO weights (key, value, default_value, min_value, max_value)
                VALUES (?, ?, ?, ?, ?)
            ''', defaults)
            self.conn.commit()
    
    def add_garment(self, garment: Garment):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO garment (name, category, layer_role, color_hex, color_lab_l, color_lab_a, color_lab_b, pattern, warmth, formality, season_tags, occasion_tags, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (garment.name, garment.category, garment.layer_role, garment.color_hex, garment.color_lab_l, garment.color_lab_a, garment.color_lab_b, garment.pattern, garment.warmth, garment.formality, garment.season_tags, garment.occasion_tags, int(garment.active)))
            self.conn.commit()
            garment_id = cursor.lastrowid
            return garment_id
        except sqlite3.IntegrityError as e:
            print(f"Errore inserimento garment: {e}")
            raise
    
    def list_garments(self, show_inactive=False):
        cursor = self.conn.cursor()
        query = "SELECT id, name, category FROM garment"
        if not show_inactive:
            query += "WHERE active = 1"
        cursor.execute(query)
        return cursor.fetchall()
    
    def deactivate_garment(self, garment_id: int):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE garment SET active = 0 WHERE id = ?", (garment_id,))
        self.conn.commit()
        return cursor.rowcount
    
    def activate_garment(self, garment_id: int):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE garment SET active = 1 WHERE id = ?", (garment_id,))
        self.conn.commit()
        return cursor.rowcount
    
    def delete_garment(self, garment_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM garment WHERE id = ?", (garment_id,))
        self.conn.commit()
        return cursor.rowcount
    
    def get_garment(self, garment_id: int):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM garment WHERE id = ?", (garment_id,))
        return cursor.fetchone()
    
    def update_garment_field(self, garment_id: int, field_name: str, new_value):
        cursor = self.conn.cursor()
        query = f"UPDATE garment SET {field_name} = ? WHERE id = ?"
        cursor.execute(query, (new_value, garment_id))
        self.conn.commit()
        return cursor.rowcount

    def get_garments_by_category(self, category: str, active_only: bool = True) -> list:
        cursor = self.conn.cursor()
        query = "SELECT * FROM garment WHERE category = ?"
        if active_only:
            query += "AND active = 1"
        cursor.execute(query, (category,))
        return cursor.fetchall()

    def get_garments_by_layer(self, layer_role: str, active_only: bool = True) -> list:
        cursor = self.conn.cursor()
        query = "SELECT * FROM garment WHERE layer_role = ?"
        if active_only:
            query += "AND active = 1"
        cursor.execute(query, (layer_role,))
        return cursor.fetchall()
    
    def add_feedback(self, shoes_id, bottom_id, base_top_id, mid_top_id, outerwear_id, verdict, reason=None):
        """
        Aggiunge un feedback per un outfit

        Args:
            verdict: 1 per like, 0 per dislike
            reason: FeedbackReason enum value (opzionale se verdict=1)
        """
        # 1. Genera outfit signature
        outfit_signature = f"{shoes_id}-{bottom_id}-{base_top_id}-{mid_top_id or 0}-{outerwear_id or 0}"
        if verdict == 1 and reason is not None:
            #print("Non ci può essere una ragione, se l'outfit ti è piaciuto")
            raise ValueError("Non ci può essere una ragione se l'outfit ti è piaciuto")
        if verdict == 0 and reason is None:
            #print("Se un outfit non ti è piaciuto, devi inserire una ragione")
            raise ValueError("Se un outfit non ti è piaciuto, devi inserire una ragione")
        if reason is not None:
            valid_reasons = [r.value for r in FeedbackReason]
            if reason not in valid_reasons:
                raise ValueError(f"Ragione non valida. Valori accettati: {valid_reasons}")
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO feedback (outfit_signature, shoes_id, bottom_id, base_top_id, mid_top_id, outerwear_id, verdict, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (outfit_signature, shoes_id, bottom_id, base_top_id, mid_top_id, outerwear_id, verdict, reason))
            self.conn.commit()
            feedback_id = cursor.lastrowid
            return feedback_id
        except sqlite3.IntegrityError as e:
            print(f"Errore inserimento feedback: {e}")
            raise
    
    #def get_feedback_by_outfit(self, outfit_signature):
    #    cursor = self.conn.cursor()
    #    cursor.execute('''
    #        SELECT * FROM feedback WHERE outfit_signature = ?
    #    ''', (outfit_signature,))
    #    return cursor.fetchall()

    def list_all_feedback(self, limit=None):
        """
        Lista tutti i feedback, ordinati dal più recente

        Args:
            limit: numero massimo di risultati (None = tutti)
        """
        cursor = self.conn.cursor()
        query = "SELECT * FROM feedback ORDER BY timestamp DESC"
        if limit:
            query += f" LIMIT {limit}"
        cursor.execute(query)
        return cursor.fetchall()
    
    def delete_feedback(self, feedback_id: int):
        """Elimina un feedback specifico"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
        self.conn.commit()
        return cursor.rowcount  # Restituisce 1 se cancellato, 0 se non trovato

    def close(self):
        """Close connection when finished"""
        if self.conn:
            self.conn.close()

class WeightsManager:
    def __init__(self, db_manager: DB_Manager):
        self.db = db_manager
        self.conn = db_manager.conn
    
    def get_weight(self, key: str) -> float:
        '''Recupera un peso dal database'''
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM weights WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row is None:
            raise KeyError(f"Weight '{key}' non trovato nel database")
        return row['value']
    
    def get_all_weights(self) -> dict:
        '''Restituisce tutti i pesi come dizionario'''
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM weights")
        return {row['key']: row['value'] for row in cursor.fetchall()}
    
    def set_weight(self, key: str, value: float):
        """Aggiorna un peso con validazione min/max"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT min_value, max_value FROM weights WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        if row is None:
            raise KeyError(f"Weight '{key}' non trovato")
        
        min_val, max_val = row['min_value'], row['max_value']
        if value < min_val or value > max_val:
            print(f"Valore {value} fuori range. Uso valori di clamping.")
        clamped_value = max(min_val, min(max_val, value))

        cursor.execute(
            "UPDATE weights SET value = ?, last_modified = CURRENT_TIMESTAMP WHERE key = ?",
            (clamped_value, key)
        )
        self.conn.commit()
        return clamped_value
    
    def adjust_weight(self, key: str, delta: float):
        """Modifica incrementalmente un peso"""
        current = self.get_weight(key)
        new_value = current + delta
        return self.set_weight(key, new_value)
    
    def reset_weight(self, key: str):
        """Resetta un peso al valore di default"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE weights SET value = default_value, last_modified = CURRENT_TIMESTAMP WHERE key = ?",
            (key,)
        )
        self.conn.commit()
        return cursor.rowcount
    
    def reset_all_weights(self):
        """Resetta tutti i pesi ai valori di default"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE weights SET value = default_value, last_modified = CURRENT_TIMESTAMP"
        )
        self.conn.commit()
        return cursor.rowcount
    
    def get_item_penalty(self, garment_id: int) -> float:
        """Recupera la penalità di un item (0.0 se non esiste)"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT penalty_score FROM item_penalties WHERE garment_id = ?", (garment_id,))
        row = cursor.fetchone()
        return row['penalty_score'] if row else 0.0
    
    def add_item_penalty(self, garment_id: int, penalty_delta: float):
        """Aggiunge/aggiorna penalità per un item"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO item_penalties (garment_id, penalty_score, last_updated)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(garment_id) DO UPDATE SET
                penalty_score = penalty_score + ?,
                last_updated = CURRENT_TIMESTAMP
        ''', (garment_id, penalty_delta, penalty_delta))
        self.conn.commit()

    def get_pair_penalty(self, garment_id_1: int, garment_id_2: int) -> float:
        """Recupera penalità di una coppia (0.0 se non esiste)"""
        # Ordina gli ID per garantire consistenza
        id1, id2 = min (garment_id_1, garment_id_2), max(garment_id_1, garment_id_2)
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT penalty_score FROM pair_penalties WHERE garment_id_1 = ? AND garment_id_2 = ?",
            (id1, id2)
        )
        row = cursor.fetchone()
        return row['penalty_score'] if row else 0.0
    
    def add_pair_penalty(self, garment_id_1: int, garment_id_2: int, penalty_delta: float):
        """Aggiunge/aggiorna penalità per una coppia"""
        id1, id2 = min(garment_id_1, garment_id_2), max(garment_id_1, garment_id_2)
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO pair_penalties (garment_id_1, garment_id_2, penalty_score, last_updated)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(garment_id_1, garment_id_2) DO UPDATE SET
                penalty_score = penalty_score + ?,
                last_updated = CURRENT_TIMESTAMP
        ''', (id1, id2, penalty_delta, penalty_delta))
        self.conn.commit()