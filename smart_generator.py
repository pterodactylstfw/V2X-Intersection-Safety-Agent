import json


def genereaza_scenariu_oras():
    cadre_scenariu = []

    # Mașina A: Merge spre EST
    a_x, a_y = 0.0, 420.0
    a_v, a_max, a_acc = 0.0, 4.0, 0.1

    # --- ADĂUGAT: Mașina A2 (Urmăritorul) ---
    a2_x, a2_y = -120.0, 420.0
    a2_v, a2_max, a2_acc = 0.0, 4.5, 0.1

    # Ambulanța B: Merge spre SUD
    b_x, b_y = 380.0, 0.0
    b_v, b_max, b_acc = 0.0, 6.0, 0.2

    # Mașina C: Merge spre NORD
    c_x, c_y = 1120.0, 800.0
    c_v, c_max, c_acc = 0.0, 3.5, 0.1

    for cadru in range(300):
        # Accelerare
        if a_v < a_max:
            a_v += a_acc
        if a2_v < a2_max:
            a2_v += a2_acc  # Accelerează A2
        if b_v < b_max:
            b_v += b_acc
        if c_v < c_max:
            c_v += c_acc

        # Mișcare
        a_x += a_v
        a2_x += a2_v  # Mișcă A2
        b_y += b_v
        c_y -= c_v

        # Construim cadrul conform Contractului Unificat
        frame = [
            {
                "agent_id": "Masina_A",
                "vehicle_type": "Normal",
                "priority_active": False,
                "position_x": round(a_x, 2),
                "position_y": a_y,
                "speed": round(a_v, 2),
                "heading": "EAST",
                "driving_style": "Normal",
            },
            # --- ADĂUGAT: JSON pentru Masina_A2 ---
            {
                "agent_id": "Masina_A2",
                "vehicle_type": "Normal",
                "priority_active": False,
                "position_x": round(a2_x, 2),
                "position_y": a2_y,
                "speed": round(a2_v, 2),
                "heading": "EAST",
                "driving_style": "Cautious",
            },
            {
                "agent_id": "Ambulanta_B",
                "vehicle_type": "Ambulance",
                "priority_active": True,
                "position_x": b_x,
                "position_y": round(b_y, 2),
                "speed": round(b_v, 2),
                "heading": "SOUTH",
                "driving_style": "Aggressive",
            },
            {
                "agent_id": "Masina_C",
                "vehicle_type": "Normal",
                "priority_active": False,
                "position_x": c_x,
                "position_y": round(c_y, 2),
                "speed": round(c_v, 2),
                "heading": "NORTH",
                "driving_style": "Cautious",
            },
        ]
        cadre_scenariu.append(frame)

    # Salvare în fișier pentru a fi citit de DataFeeder
    with open("scenariu.json", "w", encoding="utf-8") as f:
        json.dump(cadre_scenariu, f, indent=2, ensure_ascii=False)

    print("Scenariu generat cu succes! Masina_A2 a fost inclusa.")


if __name__ == "__main__":
    genereaza_scenariu_oras()
