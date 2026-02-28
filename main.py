from v2x_network import V2XBroker
from vehicle_agent import VehicleAgent
import time


def test_retea_v2x():
    print("--- Start Test V2X Broker ---\n")

    # 1. Inițializăm brokerul tău (Pornim "avizierul" central)
    broker = V2XBroker()

    # 2. Creăm datele pentru cele două mașini respectând "Contractul" stabilit
    stare_masina_a = {
        "pozitie_x": 10.0,
        "pozitie_y": 20.0,
        "viteza": 50,
        "intentie": "MERGE_INAINTE",
    }

    stare_masina_b = {
        "pozitie_x": 100.0,
        "pozitie_y": 20.0,
        "viteza": 60,
        "intentie": "FRANEAZA",
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
    stare_masina_a["pozitie_x"] = 15.0  # Actualizăm poziția X
    broker.publish("Masina_A", stare_masina_a)

    date_vazute_de_b_dupa_miscare = broker.receive("Masina_B")
    print(f"Ce vede Masina_B acum?")
    print(f"-> {date_vazute_de_b_dupa_miscare}")


def simulare_live():
    print("--- Start Simulare Integrată (AI + V2X) ---\n")

    # 1. Pornim rețeaua colegei tale (Broker-ul)
    broker = V2XBroker()

    # 2. Creăm agenții tăi AI
    # Mașina 1 (Normală), merge de la stânga la dreapta spre intersecție (100, 50)
    masina_1 = VehicleAgent(
        vehicle_id=1, start_x=0, start_y=50, speed=10, vehicle_type="normal"
    )

    # Mașina 2 (Ambulanță), merge de sus în jos spre intersecție (100, 50)
    masina_2 = VehicleAgent(
        vehicle_id=2, start_x=100, start_y=150, speed=10, vehicle_type="ambulance"
    )

    # Centrul intersecției
    intersectie_x = 100
    intersectie_y = 50

    # 3. BUCLA DE TIMP (Simulăm 10 cadre/secunde de mișcare)
    for cadru in range(1, 11):
        print(f"\n[ SECUNDA {cadru} ] =====================================")

        # A. Mașinile își pregătesc datele și le publică în V2X
        # Aici facem "traducerea" pentru rețeaua colegei tale
        stare_m1 = {
            "id": masina_1.id,
            "x": masina_1.x,
            "y": masina_1.y,
            "speed": masina_1.speed,
            "type": masina_1.type,
        }
        stare_m2 = {
            "id": masina_2.id,
            "x": masina_2.x,
            "y": masina_2.y,
            "speed": masina_2.speed,
            "type": masina_2.type,
        }

        broker.publish(f"Masina_{masina_1.id}", stare_m1)
        broker.publish(f"Masina_{masina_2.id}", stare_m2)

        # B. Mașinile "ascultă" rețeaua (Percepție)
        date_primite_de_1 = broker.receive(f"Masina_{masina_1.id}")
        for nume, date in date_primite_de_1.items():
            masina_1.receive_v2x_message(date)

        date_primite_de_2 = broker.receive(f"Masina_{masina_2.id}")
        for nume, date in date_primite_de_2.items():
            masina_2.receive_v2x_message(date)

        # C. Mașinile GÂNDESC (Calcul matematic coliziune + Negociere Groq)
        masina_1.decide_action(intersectie_x, intersectie_y)
        masina_2.decide_action(intersectie_x, intersectie_y)

        # D. Mașinile SE MIȘCĂ (Actualizăm poziția X, Y pe baza deciziei)
        # Presupunem că a trecut 1 secundă între cadre (delta_time = 1)
        masina_1.update_position(
            delta_time=1, target_x=intersectie_x, target_y=intersectie_y
        )
        masina_2.update_position(
            delta_time=1, target_x=intersectie_x, target_y=intersectie_y
        )

        # Afișăm pe ecran unde au ajuns
        print(
            f"-> M1 (Normal) e la coordonatele: ({masina_1.x}, {masina_1.y}) cu viteza {masina_1.speed}"
        )
        print(
            f"-> M2 (Ambulanță) e la coordonatele: ({masina_2.x}, {masina_2.y}) cu viteza {masina_2.speed}"
        )

        time.sleep(
            1
        )  # Punem o pauză ca să apucăm să citim în terminal cum decurge acțiunea


if __name__ == "__main__":
    # test_retea_v2x()
    simulare_live()
