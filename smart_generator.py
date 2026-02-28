import json


def genereaza_scenariu_oras():
    cadre_scenariu = []

    # --- CONFIGURĂRI AXE ȘI BENZI (ROMÂNIA) ---
    # Drum Orizontal (Y=400): EST (Y:420), VEST (Y:380)
    # Intersecția 1 (X=400): NORD (X:420), SUD (X:380)
    # Intersecția 2 (X=1100): NORD (X:1120), SUD (X:1080)

    # 1. Mașina A: Merge spre EST (Dreapta). Banda de JOS.
    a_x, a_y = 0.0, 420.0
    a_v, a_max = 0.0, 4.0  # Viteza max

    # 2. Ambulanța B: Merge spre SUD (În jos) la Intersecția 1. Banda din STÂNGA.
    b_x, b_y = 380.0, 0.0
    b_v, b_max = 0.0, 5.5

    # 3. Mașina C: Merge spre NORD (În sus) la Intersecția 2. Banda din DREAPTA.
    c_x, c_y = 1120.0, 800.0
    c_v, c_max = 0.0, 3.8

    # 4. Mașina D (Nouă): Merge spre VEST (Stânga). Banda de SUS.
    d_x, d_y = 1500.0, 380.0
    d_v, d_max = 0.0, 4.2

    # Generăm 400 de cadre pentru a acoperi toată harta de 1500px
    for cadru in range(400):
        # Accelerare simplă până la viteza maximă
        if a_v < a_max:
            a_v += 0.1
        if b_v < b_max:
            b_v += 0.15
        if c_v < c_max:
            c_v += 0.08
        if d_v < d_max:
            d_v += 0.12

        # Actualizare poziții conform direcției (heading)
        a_x += a_v  # EST: X crește
        b_y += b_v  # SUD: Y crește
        c_y -= c_v  # NORD: Y scade
        d_x -= d_v  # VEST: X scade

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
            {
                "agent_id": "Masina_D",
                "vehicle_type": "Normal",
                "priority_active": False,
                "position_x": round(d_x, 2),
                "position_y": d_y,
                "speed": round(d_v, 2),
                "heading": "WEST",
                "driving_style": "Normal",
            },
        ]
        cadre_scenariu.append(frame)

    with open("scenariu.json", "w", encoding="utf-8") as f:
        json.dump(cadre_scenariu, f, indent=2, ensure_ascii=False)

    print(f"Scenariu V2X generat cu succes!")
    print(
        f"Reguli RO aplicate: Orizontal (Y:420/380), Vertical 1 (X:380), Vertical 2 (X:1120)"
    )


if __name__ == "__main__":
    genereaza_scenariu_oras()
