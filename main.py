from v2x_network import V2XBroker

def test_retea_v2x():
    print("--- Start Test V2X Broker ---\n")
    
    # 1. Inițializăm brokerul tău (Pornim "avizierul" central)
    broker = V2XBroker()
    
    # 2. Creăm datele pentru cele două mașini respectând "Contractul" stabilit
    stare_masina_a = {
        "pozitie_x": 10.0, 
        "pozitie_y": 20.0, 
        "viteza": 50, 
        "intentie": "MERGE_INAINTE"
    }
    
    stare_masina_b = {
        "pozitie_x": 100.0, 
        "pozitie_y": 20.0, 
        "viteza": 60, 
        "intentie": "FRANEAZA"
    }
    
    # 3. Mașinile își publică starea în canalul V2X
    print("Se publica datele...")
    broker.publish("Masina_A", stare_masina_a)
    broker.publish("Masina_B", stare_masina_b)
    print("Datele au fost publicate cu succes!\n")
    
    # 4. Testăm metoda de recepție (Citirea din rețea)
    # Masina_A cere datele. Ar trebui să vadă doar Masina_B.
    date_vazute_de_a = broker.receive("Masina_A")
    print(f"Ce vede Masina_A în rețea?")
    print(f"-> {date_vazute_de_a}\n")
    
    # Masina_B cere datele. Ar trebui să vadă doar Masina_A.
    date_vazute_de_b = broker.receive("Masina_B")
    print(f"Ce vede Masina_B în rețea?")
    print(f"-> {date_vazute_de_b}\n")
    
    # 5. Simulăm o actualizare a stării (Masina A se mișcă)
    print("Masina_A se deplasează...")
    stare_masina_a["pozitie_x"] = 15.0 # Actualizăm poziția X
    broker.publish("Masina_A", stare_masina_a)
    
    date_vazute_de_b_dupa_miscare = broker.receive("Masina_B")
    print(f"Ce vede Masina_B acum?")
    print(f"-> {date_vazute_de_b_dupa_miscare}")

if __name__ == "__main__":
    test_retea_v2x()