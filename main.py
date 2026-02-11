from db_manager import DB_Manager, Garment
from color_utils import css_to_rgb, rgb_to_cielab, css_to_hex
import sys
from outfit_engine import OutfitGenerator

db = DB_Manager()

def add_new_garment(db: DB_Manager):
    name = input("Inserisci nome: ")
    category = input("Inserisci categoria: ")
    layer_role = input("Inserisci layer_role [base, mid, outer, none]: ")
    color = input("Inserisci color (CSS tables): ")
    # Conversione colore
    color_hex = css_to_hex(color)
    rgb = css_to_rgb(color)
    lab = rgb_to_cielab(rgb)
    color_lab_l = lab[0]
    color_lab_a = lab[1]
    color_lab_b = lab[2]
    pattern = input("Inserisci pattern: ")
    warmth = int(input("Inserisci warmth [1-10]: "))
    formality = int(input("Inserisci formality [1-10]: "))
    season_tags = input("Inserisci season_tags: ")
    occasion_tags = input("Inserisci occasion_tags: ")
    active_input = input("Attivo? [s/n]: ")
    active = active_input == 's'
    garment = Garment(name, category, layer_role, color_hex, color_lab_l, color_lab_a, color_lab_b, pattern, warmth, formality, season_tags, occasion_tags, active)
    garment_id = db.add_garment(garment)
    print(f"Capo '{name}' aggiunto correttamente con ID {garment_id}")

def garment_details(garment):
    print(f"\nNome: {garment['name']}")
    print(f"Categoria: {garment['category']}")
    print(f"Colore: {garment['color_hex']}")
    print(f"Parametro L: {garment['color_lab_l']}")
    print(f"Parametro A: {garment['color_lab_a']}")
    print(f"Parametro B: {garment['color_lab_b']}")
    print(f"Pattern: {garment['pattern']}")
    print(f"Warmth: {garment['warmth']}")
    print(f"Formality: {garment['formality']}")
    print(f"Season Tags: {garment['season_tags']}")
    print(f"Occasion Tags: {garment['occasion_tags']}")
    print(f"Active: {garment['active']}")

def generate_and_display_outfit(db: DB_Manager):
    """Genera e mostra outfit suggerito"""
    # Fetch garment
    shoes_list = db.get_garments_by_category('shoes')
    bottoms_list = db.get_garments_by_category('trousers')
    base_tops_list = db.get_garments_by_layer('base')
    
    # Validazione
    if not shoes_list or not bottoms_list or not base_tops_list:
        print("Wardrobe insufficiente (servono almeno: scarpe, pantaloni, base top)")
        return
    
    mid_tops_list = db.get_garments_by_layer('mid')
    outerwear_list = db.get_garments_by_layer('outer')
    
    # Genera
    outfits = OutfitGenerator.generate(
        shoes_list, bottoms_list, base_tops_list,
        mid_tops_list, outerwear_list, db, count=1
    )
    
    # Display
    if outfits:
        outfit = outfits[0]
        print("\n=== OUTFIT PER OGGI ===")
        print(f"Score: {outfit.score:.2f}/1.0")
        print(f"👟 {db.get_garment(outfit.shoes)['name']}")
        print(f"👖 {db.get_garment(outfit.bottom)['name']}")
        print(f"👕 {db.get_garment(outfit.base_top)['name']}")
        if outfit.mid_top:
            print(f"🧥 {db.get_garment(outfit.mid_top)['name']}")
        if outfit.outerwear:
            print(f"🧥 {db.get_garment(outfit.outerwear)['name']}")
        print("=======================\n")
        print(f"\n=== DEBUG SCORE ===")
        OutfitGenerator.debug_score_breakdown(outfit, db)
        print("===================\n")
    else:
        print("Nessun outfit valido trovato!")

print("Buongiorno Michele!")
print("Cosa vuoi fare?")
print("a -> Aggiungere nuovo capo")
print("l -> Listare capi esistenti")
print("deac -> Disattiva un capo")
print("ac -> Attiva un capo")
print("d -> Ottieni dettagli su un capo")
print("r -> Rimuovi un capo")
while True:
    try:
        option = input("> ").lower()
        if option == 'a':
            add_new_garment(db)
        elif option == 'l':
            garments = db.list_garments(show_inactive=True)
            for garment in garments:
                print(f"{garment['id']}: {garment['name']} ({garment['category']})")
        elif option == "deac":
            garment_id = int(input("Inserisci id: "))
            if db.deactivate_garment(garment_id):
                print("Capo disattivato")
            else:
                print("ID non trovato")
        elif option == "ac":
            garment_id = int(input("Inserisci id: "))
            if db.activate_garment(garment_id):
                print("Capo attivato")
            else:
                print("ID non trovato")
        elif option == "d":
            garment_id = int(input("Inserisci id: "))
            garment = db.get_garment(garment_id)
            if garment:
                garment_details(garment)
            else:
                print("✗ Capo non trovato")
        elif option == "r":
            garment_id = int(input("Inserisci id: "))
            db.delete_garment(garment_id)
        # Funzionalità fantasma, l'utente NON ne è a conoscenza
        elif option == 'm':
            garment_id = int(input("Inserisci id: "))
            field_name = input("Inserisci field_name: ")
            new_value = input("Inserisci il nuovo valore: ")
            edit = db.update_garment_field(garment_id, field_name, new_value)
            if edit:
                print("Elemento aggiornato con successo!")
            else:
                print("Id non valido")
        elif option == 'g':
            generate_and_display_outfit(db)
    except KeyboardInterrupt:
        print("Exiting...")
        db.close()
        sys.exit(0)