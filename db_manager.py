import sqlite3
from pathlib import Path
from dataclasses import dataclass

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
    
    def close(self):
        """Close connection when finished"""
        if self.conn:
            self.conn.close()