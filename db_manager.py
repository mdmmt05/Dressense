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
    DONT_LIKE_ITEM = 'dont_like_item'
    DONT_LIKE_COMBINATION = 'dont_like_combination'
    BORING = 'boring'
    TOO_FLASHY = 'too_flashy'

class DB_Manager():
    def __init__(self):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._initialize_tables()

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
                                               'too_casual', 'bad_layering', 'dont_like_item', 
                                               'dont_like_combination', 'boring', 'too_flashy')),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shoes_id) REFERENCES garment(id),
                FOREIGN KEY (bottom_id) REFERENCES garment(id),
                FOREIGN KEY (base_top_id) REFERENCES garment(id),
                FOREIGN KEY (mid_top_id) REFERENCES garment(id),
                FOREIGN KEY (outerwear_id) REFERENCES garment(id)
            )
        ''')
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