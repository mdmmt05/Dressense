from db_manager import DB_Manager, Garment, FeedbackReason, WeightsManager
from color_utils import css_to_rgb, rgb_to_cielab, css_to_hex
import sys
from outfit_engine import OutfitGenerator
from feedback_engine import FeedbackManager

feedback_manager = None

def add_new_garment(db: DB_Manager):
    name = input("Inserisci nome: ").strip()
    if not name:
        print("Nome non valido")
        return
    category = input("Inserisci categoria: ").strip()
    if not category:
        print("Categoria non valida")
        return
    while True:
        layer_role = input("Inserisci layer_role [base, mid, outer, none]: ").strip().lower()
        if layer_role in ('base', 'mid', 'outer', 'none'):
            break
        print("Valore non valido. Scegli tra base, mid, outer, none.")
    while True:
        color = input("Inserisci colore (CSS name, es. 'red'): ").strip()
        try:
            color_hex = css_to_hex(color)
            rgb = css_to_rgb(color)
            lab = rgb_to_cielab(rgb)
            break
        except ValueError as e:
            print(f"Errore colore: {e}. Riprova.")
    pattern = input("Inserisci pattern: ").strip()
    while True:
        try:
            warmth = int(input("Inserisci warmth [1-10]: "))
            if 1 <= warmth <= 10:
                break
            print("Deve essere tra 1 e 10")
        except ValueError:
            print("Inserisci un numero intero")
    while True:
        try:
            formality = int(input("Inserisci formality [1-10]: "))
            if 1 <= formality <= 10:
                break
            print("Deve essere tra 1 e 10")
        except ValueError:
            print("Inserisci un numero intero")
    season_tags = input("Inserisci season_tags: ").strip()
    occasion_tags = input("Inserisci occasion_tags: ").strip()
    active_input = input("Attivo? [s/n]: ").strip().lower()
    active = active_input == 's'
    garment = Garment(name, category, layer_role, color_hex, lab[0], lab[1], lab[2],
                      pattern, warmth, formality, season_tags, occasion_tags, active)
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
    valid_seasons = ["auto", "none", "spring", "summer", "autumn", "winter"]
    while True:
        season_input = input("Season context [auto/none/spring/summer/autumn/winter] (default: auto): ").strip().lower()
        if season_input == "":
            season_input = "auto"
        if season_input in valid_seasons:
            break
        print(f"Valore non valido. Scegli tra {', '.join(valid_seasons)}")
    valid_occasions = ["none", "university", "work_casual", "evening", "event"]
    while True:
        occasion_input = input("Occasion context [none/university/work_casual/evening/event] (default: none): ").strip().lower()
        if occasion_input == "":
            occasion_input = "none"
        if occasion_input in valid_occasions:
            break
        print(f"Valore non valido. Scegli tra {', '.join(valid_occasions)}")

    # Resolve season for display (auto -> actual season)
    if season_input == "auto":
        resolved_season = OutfitGenerator.infer_current_season()
        print(f"Context: season={resolved_season} (auto), occasion={occasion_input}")
    else:
        resolved_season = season_input if season_input != "none" else None
        print(f"Context: season={season_input}, occasion={occasion_input}")

    # Fetch garment
    shoes_list = db.get_garments_by_category('shoes')
    bottoms_list = db.get_garments_by_category('trousers')
    base_tops_list = db.get_garments_by_layer('base')
    
    # Validazione
    if not shoes_list or not bottoms_list or not base_tops_list:
        print("Wardrobe insufficiente (servono almeno: scarpe, pantaloni, base top)")
        return None
    
    mid_tops_list = db.get_garments_by_layer('mid')
    outerwear_list = db.get_garments_by_layer('outer')
    
    # Genera
    outfits = OutfitGenerator.generate(
        shoes_list, bottoms_list, base_tops_list,
        mid_tops_list, outerwear_list, db, count=1,
        season=season_input,
        occasion=occasion_input if occasion_input != "none" else None
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
        
        #print(f"\n=== DEBUG SCORE ===")
        #OutfitGenerator.debug_score_breakdown(outfit, db)
        #print("===================\n")

        try:
            verdict_input = input("Ti è piaciuto l'outfit? [s/n/skip]: ").lower()

            if verdict_input == 'skip':
                print("⏭️  Rating saltato\n")
            else:
                verdict = 1 if verdict_input == 's' else 0
                reason = None
                if verdict == 0:
                    reasons = [r.value for r in FeedbackReason]
                    for i, r in enumerate(reasons, 1):
                        print(f"{i}. {r}")
                    while True:
                        try:
                            choice = int(input("Scegli il motivo [1-8]: "))
                            if 1 <= choice <= len(reasons):
                                reason = reasons[choice - 1]
                                break
                            print(f"Scegli un numero tra 1 e {len(reasons)}")
                        except ValueError:
                            print("Inserisci un numero")
                feedback_manager.process_feedback(outfit, verdict, reason)
        except (KeyboardInterrupt, EOFError):
            print("\n⏭️  Rating saltato\n")
        try:
            mark = input("Vuoi segnare questo outfit come indossato oggi? [y/n]: ").lower()
            if mark == 'y':
                db.add_outfit_to_history(outfit)
                print("✓ Outfit registrato come indossato!")
            else:
                print("⏭️  Non registrato.")
        except (KeyboardInterrupt, EOFError):
            print("\n⏭️  Non registrato.")
        return outfit
    else:
        print("Nessun outfit valido trovato! Prova a modificare i vincoli stagionali o ad aggiungere più capi.")
        return None

def main():
    global feedback_manager

    db = DB_Manager()
    weights_manager = WeightsManager(db)
    feedback_manager = FeedbackManager(db)
    
    OutfitGenerator.load_weights(weights_manager.get_all_weights())

    current_outfit = None

    print("Buongiorno Michele!")
    print("Cosa vuoi fare?")
    print("a -> Aggiungere nuovo capo")
    print("l -> Listare capi esistenti")
    print("deac -> Disattiva un capo")
    print("ac -> Attiva un capo")
    print("d -> Ottieni dettagli su un capo")
    print("r -> Rimuovi un capo")
    print("g -> Genera outfit")
    while True:
        try:
            option = input("> ").lower()
            if option == 'a':
                add_new_garment(db)
            elif option == 'l':
                garments = db.list_garments(show_inactive=True)
                for g in garments:
                    print(f"{g['id']}: {g['name']} ({g['category']})")
            elif option == "deac":
                try:
                    garment_id = int(input("Inserisci id: "))
                    if db.deactivate_garment(garment_id):
                        print("Capo disattivato")
                    else:
                        print("ID non trovato")
                except ValueError:
                    print("ID non valido")
            elif option == "ac":
                try:
                    garment_id = int(input("Inserisci id: "))
                    if db.activate_garment(garment_id):
                        print("Capo attivato")
                    else:
                        print("ID non trovato")
                except ValueError:
                    print("ID non valido")
            elif option == "d":
                try:
                    garment_id = int(input("Inserisci id: "))
                    garment = db.get_garment(garment_id)
                    if garment:
                        garment_details(garment)
                    else:
                        print("✗ Capo non trovato")
                except ValueError:
                    print("ID non valido")
            elif option == "r":
                try:
                    garment_id = int(input("Inserisci id: "))
                    deleted = db.delete_garment(garment_id)
                    if deleted:
                        print("Capo rimosso")
                    else:
                        print("Impossibile rimuovere (capo ha riferimenti o ID non valido)")
                except ValueError:
                    print("ID non valido")
            # Funzionalità fantasma, l'utente NON ne è a conoscenza
            elif option == 'm':
                try:
                    garment_id = int(input("Inserisci id: "))
                    field_name = input("Inserisci field_name: ")
                    new_value = input("Inserisci il nuovo valore: ")
                    db.update_garment_field(garment_id, field_name, new_value)
                    print("Elemento aggiornato con successo!")
                except ValueError as e:
                    print(f"Errore: {e}")
            elif option == 'g':
                current_outfit = generate_and_display_outfit(db)
            else:
                print("Comando sconosciuto")
        except KeyboardInterrupt:
            print("Exiting...")
            db.close()
            sys.exit(0)

if __name__ == "__main__":
    main()