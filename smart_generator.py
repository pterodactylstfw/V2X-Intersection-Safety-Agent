import json

def genereaza_scenariu_oras():
    cadre_scenariu = []
    
    # --- DATE INIȚIALE CONFORM NOII HARTI 1500x800 ---
    # 1. Mașina A: Merge spre EST (dreapta). Banda ei are Y = 420 fix.
    a_x, a_y = 0.0, 420.0
    a_v, a_max, a_acc = 0.0, 4.0, 0.1
    
    # 2. Ambulanța B: Merge spre SUD (în jos) la Intersecția 1. Banda ei are X = 420 fix.
    b_x, b_y = 420.0, 0.0
    b_v, b_max, b_acc = 0.0, 6.0, 0.2
    
    # 3. Mașina C: Merge spre NORD (în sus) la Intersecția 2. Banda ei are X = 1080 fix.
    c_x, c_y = 1080.0, 800.0 # Pornește de jos
    c_v, c_max, c_acc = 0.0, 3.5, 0.1

    # Generăm 300 de cadre (harta e mai lungă acum)
    for cadru in range(300):
        # Accelerează mașinile (Cinematică)
        if a_v < a_max: a_v += a_acc
        if b_v < b_max: b_v += b_acc
        if c_v < c_max: c_v += c_acc
        
        # Mișcarea pe direcții
        a_x += a_v       # EST (X crește)
        b_y += b_v       # SUD (Y crește)
        c_y -= c_v       # NORD (Y scade)

        frame = [
            {
                "agent_id": "Masina_A", "vehicle_type": "Normal", "priority_active": False,
                "position_x": round(a_x, 2), "position_y": a_y,
                "speed": round(a_v, 2), "heading": "EAST", "driving_style": "Normal"
            },
            {
                "agent_id": "Ambulanta_B", "vehicle_type": "Ambulance", "priority_active": True,
                "position_x": b_x, "position_y": round(b_y, 2),
                "speed": round(b_v, 2), "heading": "SOUTH", "driving_style": "Aggressive"
            },
            {
                "agent_id": "Masina_C", "vehicle_type": "Normal", "priority_active": False,
                "position_x": c_x, "position_y": round(c_y, 2),
                "speed": round(c_v, 2), "heading": "NORTH", "driving_style": "Cautious"
            }
        ]
        cadre_scenariu.append(frame)

    with open("scenariu.json", "w", encoding="utf-8") as f:
        json.dump(cadre_scenariu, f, indent=2, ensure_ascii=False)
        
    print("Scenariu generat cu succes pentru noua hartă cu 2 benzi!")

if __name__ == "__main__":
    genereaza_scenariu_oras()