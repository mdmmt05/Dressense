import sqlite3
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import re
from typing import Any

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
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._initialize_tables()
        self._initialize_defaults()

    def _initialize_tables(self) -> None:
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS outfit_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                outfit_signature TEXT NOT NULL,
                shoes_id INTEGER NOT NULL,
                bottom_id INTEGER NOT NULL,
                base_top_id INTEGER NOT NULL,
                mid_top_id INTEGER,
                outerwear_id INTEGER,
                worn_date DATE NOT NULL DEFAULT (date('now')),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shoes_id) REFERENCES garment(id),
                FOREIGN KEY (bottom_id) REFERENCES garment(id),
                FOREIGN KEY (base_top_id) REFERENCES garment(id),
                FOREIGN KEY (mid_top_id) REFERENCES garment(id),
                FOREIGN KEY (outerwear_id) REFERENCES garment(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ui_preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        self.conn.commit()
    
    def get_ui_preference(self, key: str, default=None):
        """Retrieve a UI preference value by key."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT value FROM ui_preferences WHERE key = ?', (key,))
        row = cursor.fetchone()
        if row is None:
            return default
        return row[0]

    def set_ui_preference(self, key: str, value: str) -> None:
        """Persist a UI preference key/value pair."""
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO ui_preferences (key, value) VALUES (?, ?)',
            (key, str(value))
        )
        self.conn.commit()

    def _ensure_default_weights(self) -> None:
        """Insert any missing weight keys without overwriting existing values."""
        defaults = [
            ('formality_threshold', 4.0, 4.0, 2.0, 8.0),
            ('neutral_saturation_threshold', 20.0, 20.0, 10.0, 40.0),
            ('color_weight', 0.55, 0.55, 0.1, 0.9),
            ('pattern_weight', 0.3, 0.3, 0.05, 0.7),
            ('formality_weight', 0.15, 0.15, 0.05, 0.5),
            ('target_formality', 5.0, 5.0, 1.0, 10.0),   # new weight
        ]
        cursor = self.conn.cursor()
        for key, val, default, minv, maxv in defaults:
            cursor.execute('''
                INSERT OR IGNORE INTO weights (key, value, default_value, min_value, max_value)
                VALUES (?, ?, ?, ?, ?)
            ''', (key, val, default, minv, maxv))
        self.conn.commit()

    def _initialize_defaults(self) -> None:
        '''Popola i pesi di default se la tabella è vuota'''
        self._ensure_default_weights();
        
    def _validate_garment(self, garment: Garment) -> None:
        if not garment.name or not garment.name.strip():
            raise ValueError("Nome del capo non può essere vuoto")
        if not garment.category or not garment.category.strip():
            raise ValueError("Categoria non può essere vuota")
        allowed_roles = {'base', 'mid', 'outer', 'none'}
        if garment.layer_role not in allowed_roles:
            raise ValueError(f"layer_role deve essere uno di {allowed_roles}")
        if not re.match(r'^#[0-9A-Fa-f]{6}$', garment.color_hex):
            raise ValueError(f"color_hex '{garment.color_hex}' non è un esadecimale valido (es. #FF00AA)")
        if not (1 <= garment.warmth <= 10):
            raise ValueError("warmth deve essere intero tra 1 e 10")
        if not (1 <= garment.formality <= 10):
            raise ValueError("formality deve essere intero tra 1 e 10")
        if garment.active not in (True, False):
            raise ValueError("active deve essere booleano")
    
    def add_garment(self, garment: Garment) -> int | None:
        self._validate_garment(garment)
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO garment (name, category, layer_role, color_hex, color_lab_l, color_lab_a, color_lab_b, pattern, warmth, formality, season_tags, occasion_tags, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (garment.name, garment.category, garment.layer_role, garment.color_hex, garment.color_lab_l, garment.color_lab_a, garment.color_lab_b, garment.pattern, garment.warmth, garment.formality, garment.season_tags, garment.occasion_tags, int(garment.active)))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            print(f"Errore inserimento garment: {e}")
            raise
    
    def list_garments(self, show_inactive=False) -> list[Any]:
        cursor = self.conn.cursor()
        if show_inactive:
            query = "SELECT id, name, category FROM garment"
        else:
            query = "SELECT id, name, category FROM garment WHERE active = 1"
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
    
    def _garment_has_references(self, garment_id: int) -> bool:
        cursor = self.conn.cursor()
        tables = ['feedback', 'outfit_history', 'pair_penalties']
        for table in tables:
            if table == 'feedback':
                cursor.execute('SELECT 1 FROM feedback WHERE shoes_id=? OR bottom_id=? OR base_top_id=? OR mid_top_id=? OR outerwear_id=? LIMIT 1',
                               (garment_id, garment_id, garment_id, garment_id, garment_id))
            elif table == 'outfit_history':
                cursor.execute('SELECT 1 FROM outfit_history WHERE shoes_id=? OR bottom_id=? OR base_top_id=? OR mid_top_id=? OR outerwear_id=? LIMIT 1',
                               (garment_id, garment_id, garment_id, garment_id, garment_id))
            else:  # pair_penalties
                cursor.execute('SELECT 1 FROM pair_penalties WHERE garment_id_1=? OR garment_id_2=? LIMIT 1', (garment_id, garment_id))
            if cursor.fetchone():
                return True
        return False
    
    def delete_garment(self, garment_id: int):
        if self._garment_has_references(garment_id):
            print(f"Impossibile eliminare il capo {garment_id}: è referenziato in feedback, storico o penalità. Disattivalo invece.")
            return 0
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM garment WHERE id = ?", (garment_id,))
        self.conn.commit()
        return cursor.rowcount
    
    def get_garment(self, garment_id: int):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM garment WHERE id = ?", (garment_id,))
        return cursor.fetchone()
    
    ALLOWED_FIELDS = {
        'name': str,
        'category': str,
        'layer_role': str,
        'color_hex': str,
        'pattern': str,
        'warmth': int,
        'formality': int,
        'season_tags': str,
        'occasion_tags': str,
        'active': int,
    }
    LAYER_ROLES = {'base', 'mid', 'outer', 'none'}

    def update_garment_field(self, garment_id: int, field_name: str, new_value):
        if field_name not in self.ALLOWED_FIELDS:
            raise ValueError(f"Campo '{field_name}' non è modificabile. Campi consentiti: {list(self.ALLOWED_FIELDS.keys())}")
        
        if field_name == 'layer_role':
            if new_value not in self.LAYER_ROLES:
                raise ValueError(f"layer_role deve essere uno di {self.LAYER_ROLES}")
        elif field_name in ('warmth', 'formality'):
            try:
                val = int(new_value)
                if not (1 <= val <= 10):
                    raise ValueError
                new_value = val
            except ValueError:
                raise ValueError(f"{field_name} deve essere intero tra 1 e 10")
        elif field_name == 'active':
            try:
                int_val = int(new_value)
                if int_val not in (0, 1):
                    raise ValueError
                new_value = int_val
            except ValueError:
                raise ValueError("active deve essere 0 o 1")
        elif field_name == 'color_hex':
            if not re.match(r'^#[0-9A-Fa-f]{6}$', new_value):
                raise ValueError(f"color_hex '{new_value}' non è valido (es. #FF00AA)")
            # Recompute LAB colors
            from color_utils import hex_to_rgb, rgb_to_cielab
            rgb = hex_to_rgb(new_value)
            lab = rgb_to_cielab(rgb)
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE garment
                SET color_hex = ?, color_lab_l = ?, color_lab_a = ?, color_lab_b = ?
                WHERE id = ?
            ''', (new_value, lab[0], lab[1], lab[2], garment_id))
            self.conn.commit()
            return cursor.rowcount
        
        # Aggiornamento normale
        cursor = self.conn.cursor()
        query = f"UPDATE garment SET {field_name} = ? WHERE id = ?"
        cursor.execute(query, (new_value, garment_id))
        self.conn.commit()
        return cursor.rowcount

    def get_garments_by_category(self, category: str, active_only: bool = True) -> list:
        cursor = self.conn.cursor()
        if active_only:
            query = "SELECT * FROM garment WHERE category = ? AND active = 1"
        else:
            query = "SELECT * FROM garment WHERE category = ?"
        cursor.execute(query, (category,))
        return cursor.fetchall()

    def get_garments_by_layer(self, layer_role: str, active_only: bool = True) -> list:
        cursor = self.conn.cursor()
        if active_only:
            query = "SELECT * FROM garment WHERE layer_role = ? AND active = 1"
        else:
            query = "SELECT * FROM garment WHERE layer_role = ?"
        cursor.execute(query, (layer_role,))
        return cursor.fetchall()
    
    def add_feedback(self, shoes_id, bottom_id, base_top_id, mid_top_id, outerwear_id, verdict, reason=None) -> int | None:
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
            return cursor.lastrowid
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
    
    def add_outfit_to_history(self, outfit):
        """Registra un outfit come indossato oggi"""
        outfit_signature = f"{outfit.shoes}-{outfit.bottom}-{outfit.base_top}-{outfit.mid_top or 0}-{outfit.outerwear or 0}"
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO outfit_history (outfit_signature, shoes_id, bottom_id, base_top_id, mid_top_id, outerwear_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (outfit_signature, outfit.shoes, outfit.bottom, outfit.base_top, outfit.mid_top, outfit.outerwear))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_garment_last_worn_days(self, garment_id: int) -> int | None:
        """
        Restituisce quanti giorni fa un capo è stato indossato l'ultima volta.ù
        Returns None se mai indossato.
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT julianday('now') - julianday(worn_date) as days_ago
            FROM outfit_history
            WHERE shoes_id = ? OR bottom_id = ? OR base_top_id = ? OR mid_top_id = ? OR outerwear_id = ?
            ORDER BY worn_date DESC
            LIMIT 1
        ''', (garment_id, garment_id, garment_id, garment_id, garment_id))
        row = cursor.fetchone()
        return int(row['days_ago']) if row else None

    def close(self):
        """Close connection when finished"""
        if self.conn:
            self.conn.close()
    
    def list_garments_full(self, show_inactive: bool = True) -> list:
        """Return all garment rows (all columns) ordered by active DESC, category, name."""
        cursor = self.conn.cursor()
        if show_inactive:
            query = "SELECT * FROM garment ORDER BY active DESC, category, name"
        else:
            query = "SELECT * FROM garment WHERE active = 1 ORDER BY category, name"
        cursor.execute(query)
        return cursor.fetchall()

    # ===== Metodi per reporting / Learning page =====
    def count_feedback(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM feedback")
        return cursor.fetchone()[0]

    def count_feedback_by_verdict(self, verdict: int) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM feedback WHERE verdict = ?", (verdict,))
        return cursor.fetchone()[0]

    def count_pair_penalties(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pair_penalties WHERE penalty_score < 0")
        return cursor.fetchone()[0]

    def clear_pair_penalties(self):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM pair_penalties")
        self.conn.commit()

    def count_outfit_history(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM outfit_history")
        return cursor.fetchone()[0]

    def count_garments_by_active(self, active: bool) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM garment WHERE active = ?", (1 if active else 0,))
        return cursor.fetchone()[0]

    def list_top_pair_penalties(self, limit: int = 5) -> list:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT
                pp.garment_id_1,
                pp.garment_id_2,
                g1.name AS garment_1_name,
                g2.name AS garment_2_name,
                pp.penalty_score
            FROM pair_penalties pp
            JOIN garment g1 ON g1.id = pp.garment_id_1
            JOIN garment g2 ON g2.id = pp.garment_id_2
            WHERE pp.penalty_score < 0
            ORDER BY pp.penalty_score ASC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]

class WeightsManager:
    # Bounds for penalties
    PAIR_PENALTY_MIN = -0.30
    PAIR_PENALTY_MAX = 0.0

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
        current = self.get_pair_penalty(id1, id2)
        new_value = current + penalty_delta
        clamped = max(self.PAIR_PENALTY_MIN, min(self.PAIR_PENALTY_MAX, new_value))
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO pair_penalties (garment_id_1, garment_id_2, penalty_score, last_updated)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(garment_id_1, garment_id_2) DO UPDATE SET
                penalty_score = ?,
                last_updated = CURRENT_TIMESTAMP
        ''', (id1, id2, clamped, clamped))
        self.conn.commit()