import threading
import time
import json
import random
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from traffic_light import TrafficLightAgent
from v2x_network import V2XBroker
from vehicle_agent import VehicleAgent
from simulation_ui import SimulationUI
from animal_obstacle import AnimalObstacle

load_dotenv()


def run_simulation():
    # 1. Infrastructura
    broker = V2XBroker()
    ui = SimulationUI()

    semafor = TrafficLightAgent(broker)
    semafor.start()

    caprioara = AnimalObstacle(1350, 610)

    def trigger_animal():
        caprioara.trigger()

    broker.trigger_animal_event = trigger_animal

    # ==========================================
    # LOGICA DE SPAWN DINAMIC CU AI (Traffic Director)
    # ==========================================
    llm_spawn = ChatGroq(temperature=0.8, model_name="llama-3.1-8b-instant")

    spawn_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """Ești 'Directorul de Trafic' al unui oraș inteligent. Rolul tău este să generezi un vehicul nou.
        Intrări valide în oraș: W_START, E_START, S1_START, S2_START, NW_START, NE_ONEWAY_START
        Ieșiri valide din oraș: W_END, E_END, S1_END, S2_END, NW_END
        
        Reguli:
        1. Alege o intrare și o ieșire care să aibă sens (ex. de la W_START la E_END). Nu alege aceeași parte cardinală.
        2. Alege o viteză realistă între 55.0 și 75.0.
        3. Alege tipul vehiculului: 'Normal' sau 'Ambulance' (ai un buget mic de ambulanțe, folosește-le rar).
        
        RĂSPUNDE STRICT CU UN JSON VALID, fără niciun alt text, folosind exact acest format:
        {{"start_node": "...", "target_node": "...", "speed": 65.5, "v_type": "Normal"}}
        """,
            ),
            ("human", "Te rog, trimite un vehicul nou în oraș!"),
        ]
    )
    spawn_chain = spawn_prompt | llm_spawn

    def ai_spawn_car():
        # Rulăm apelul către AI într-un thread separat ca să nu înghețăm jocul (Pygame)
        def task():
            print("🧠 [Traffic Director] Se gândește la un traseu...")
            try:
                response = spawn_chain.invoke({})

                # Curățăm textul ca să fim siguri că citim doar JSON-ul
                raw_content = (
                    response.content.replace("```json", "").replace("```", "").strip()
                )
                data = json.loads(raw_content)

                start_n = data.get("start_node", "W_START")
                target_n = data.get("target_node", "E_END")
                speed = float(data.get("speed", 60.0))
                v_type = data.get("v_type", "Normal")

                new_id = f"AI_Car_{random.randint(100, 999)}"
                d_style = "Aggressive" if v_type == "Ambulance" else "Cautious"

                agent_nou = VehicleAgent(
                    agent_id=new_id,
                    start_node=start_n,
                    target_node=target_n,
                    desired_speed=speed,
                    vehicle_type=v_type,
                    driving_style=d_style,
                )

                agenti[new_id] = agent_nou
                print(
                    f"✅ [Traffic Director] A creat {new_id} ({v_type})! Traseu: {start_n} -> {target_n} (V: {speed:.1f})"
                )

            except Exception as e:
                # Fallback de siguranță dacă AI-ul dă un JSON greșit
                print(
                    f"⚠️ [Traffic Director] Eroare format: {e}. Aplic Fallback Random."
                )
                rute_fallback = [
                    ("W_START", "E_END"),
                    ("NW_START", "S1_END"),
                    ("S2_START", "W_END"),
                ]
                sn, tn = random.choice(rute_fallback)
                agenti[f"Fallback_{random.randint(10,99)}"] = VehicleAgent(
                    f"Fallback_{random.randint(10,99)}", sn, tn, 60.0
                )

        threading.Thread(target=task, daemon=True).start()

    # Legăm butonul de noua funcție AI
    broker.trigger_spawn_car = ai_spawn_car
    # ==========================================

    # ==========================================
    # 2. SCENARII DE TESTARE PREDEFINITE (Haos Controlat)
    # ==========================================

    # --- SCENARIUL 1: ACC (Frânare la mașina din față) ---
    agent_lider = VehicleAgent(
        agent_id="Masina_Lider",
        start_node="W_START",
        target_node="E_END",
        desired_speed=35.0,  # Merge încet
    )

    agent_urmaritor = VehicleAgent(
        agent_id="Masina_Urmaritor",
        start_node="W_START",
        target_node="E_END",
        desired_speed=85.0,  # Vine glonț din spate
    )
    # TRUC: O mutăm manual 150px mai în spate ca să vedem cum o ajunge din urmă și frânează
    agent_urmaritor.position_x -= 150

    # --- SCENARIUL 2: Prioritate de Dreapta ---
    # Vine de jos spre sus (SUD -> NORD). Se va întâlni cu Liderul la I1.
    # Liderul merge spre EST, deci agent_s1 vine din dreapta Liderului! Liderul trebuie să frâneze.
    agent_s1 = VehicleAgent(
        agent_id="Masina_Sud1",
        start_node="S1_START",
        target_node="NW_END",
        desired_speed=55.0,
    )
    agent_s1.position_y += (
        80  # O întârziem puțin ca să se întâlnească fix în mijloc cu Liderul
    )

    # Vine din Dreapta spre Stânga (EST -> VEST).
    agent_est = VehicleAgent(
        agent_id="Masina_Est",
        start_node="E_START",
        target_node="W_END",
        desired_speed=65.0,
    )

    # Vine de jos spre sus (SUD -> NORD) la I2.
    # Se va intersecta cu Masina_Est.
    agent_s2 = VehicleAgent(
        agent_id="Masina_Sud2",
        start_node="S2_START",
        target_node="NW_END",
        desired_speed=60.0,
    )

    # Vine de sus spre jos (NORD -> SUD).
    agent_nord = VehicleAgent(
        agent_id="Masina_Nord",
        start_node="NW_START",
        target_node="S1_END",
        desired_speed=60.0,
    )

    # Și adăugăm Ambulanța pe fuziune (Zipper Merge) ca să testăm filtrul V2X
    agent_amb = VehicleAgent(
        agent_id="Ambulanta_VIP",
        start_node="NE_ONEWAY_START",
        target_node="S2_END",
        desired_speed=75.0,
        vehicle_type="Ambulance",
    )

    agenti = {
        "Masina_Lider": agent_lider,
        "Masina_Urmaritor": agent_urmaritor,
        "Masina_Sud1": agent_s1,
        "Masina_Est": agent_est,
        "Masina_Sud2": agent_s2,
        "Masina_Nord": agent_nord,
        "Ambulanta_VIP": agent_amb,
    }

    # Agenți care au fost deja vizibili cel puțin o dată pe ecran
    seen_on_screen = set()

    def is_outside_screen(agent):
        return (
            agent.position_x < -50
            or agent.position_x > 1550
            or agent.position_y < -50
            or agent.position_y > 850
        )

    def background_task():
        dt = 0.05

        # Coordonatele aproximative ale celor 4 intersecții noi (I1, I2, I3, I4)
        intersections = [
            (380, 650),  # I1
            (1100, 650),  # I2
            (380, 320),  # I3
            (800, 435),  # I4 (Punctul de merge)
        ]

        while True:

            caprioara.update(dt)
            status_caprioara = caprioara.get_status()

            if status_caprioara is not None:
                # Dacă e pe stradă, îi publicăm datele
                broker.publish(caprioara.agent_id, status_caprioara)
            else:
                # Dacă e ascunsă, ne asigurăm că e ștearsă din rețea ca să nu dea eroare
                with broker.lock:
                    broker.vehicles_status.pop(caprioara.agent_id, None)

            # Folosim un "list()" în jurul items() pentru a putea modifica (adăuga/șterge)
            # agenți în timp ce iterăm prin ei
            for a_id, agent in list(agenti.items()):

                agent.memory.clear()

                # 1. V2X
                traffic = broker.receive(a_id)
                for o_id, o_data in traffic.items():
                    agent.receive_v2x_message(o_data)

                # 2. Alegem intersecția către care se îndreaptă mașina BAZAT PE RUTĂ
                target_int = (agent.position_x, agent.position_y)  # Fallback

                # Căutăm în viitorul rutei ce intersecție urmează
                for idx in range(agent.current_node_index + 1, len(agent.route)):
                    n = agent.route[idx]
                    if "I1" in n:
                        target_int = (400, 650)
                        break
                    elif "I2" in n:
                        target_int = (1100, 650)
                        break
                    elif "I3" in n:
                        target_int = (400, 300)
                        break
                    elif "MERGE" in n or "I4" in n:
                        target_int = (770, 455)
                        break

                # Trimitem coordonatele corecte către AI
                agent.decide_action(target_int[0], target_int[1])

                agent.update_position(dt)

                # Marcăm agentul când intră în cadru (prima apariție)
                if not is_outside_screen(agent):
                    seen_on_screen.add(a_id)

                # Îl ștergem doar dacă a fost văzut deja și apoi a ieșit
                if a_id in seen_on_screen and is_outside_screen(agent):
                    with broker.lock:
                        broker.vehicles_status.pop(a_id, None)
                    del agenti[a_id]
                    seen_on_screen.discard(a_id)
                    continue

                # 3. Publicăm
                broker.publish(a_id, agent.get_emergency_status())
            time.sleep(dt)

    # PORNEȘTE DOAR ACEST THREAD (asigură-te că nu ai altul mai jos în main.py)
    threading.Thread(target=background_task, daemon=True).start()

    # UI-ul afișează datele din broker în timp real
    ui.start(broker)


if __name__ == "__main__":
    run_simulation()
