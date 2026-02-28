import json

def genereaza_scenariu_unificat():
    cadre_scenariu = []
    
    # Configurări inițiale conform cerințelor UI (800x800) [cite: 13, 20]
    # Masina_A: Normală, vine din STÂNGA (West) -> EST
    a_x, a_y = 0.0, 400.0
    a_v, a_max, a_acc = 0.0, 3.5, 0.1
    
    # Ambulanta_B: Urgență, vine de SUS (North) -> SUD [cite: 12, 53]
    b_x, b_y = 400.0, 0.0
    b_v, b_max, b_acc = 0.0, 5.0, 0.2

    # Generăm 150 de cadre pentru o mișcare fluidă [cite: 42, 53]
    for cadru in range(150):
        # Logica de accelerare (IDM simplificat)
        if a_v < a_max: a_v += a_acc
        if b_v < b_max: b_v += b_acc
        
        # Actualizare poziții
        a_x += a_v
        b_y += b_v

        # Construim cadrul conform Contractului Unificat
        frame = [
            {
                "agent_id": "Masina_A",
                "vehicle_type": "Normal",
                "priority_active": False, # [cite: 12]
                "position_x": round(a_x, 2),
                "position_y": a_y,
                "speed": round(a_v, 2),
                "heading": "EAST",
                "intent": "GO_STRAIGHT", # [cite: 6, 11]
                "driving_style": "Cautious"
            },
            {
                "agent_id": "Ambulanta_B",
                "vehicle_type": "Ambulance",
                "priority_active": True, # [cite: 12, 53]
                "position_x": b_x,
                "position_y": round(b_y, 2),
                "speed": round(b_v, 2),
                "heading": "SOUTH",
                "intent": "GO_STRAIGHT",
                "driving_style": "Aggressive"
            }
        ]
        cadre_scenariu.append(frame)

    # Salvare în fișier pentru a fi citit de DataFeeder 
    with open("scenariu.json", "w", encoding="utf-8") as f:
        json.dump(cadre_scenariu, f, indent=2, ensure_ascii=False)
        
    print(f"Scenariu generat: 150 cadre, coliziune iminentă la (400, 400).")

if __name__ == "__main__":
    genereaza_scenariu_unificat()