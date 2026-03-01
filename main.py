import math
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
                """Ești 'Directorul de Trafic AI' al unui oraș inteligent. Rolul tău este să adaugi un vehicul nou pe o stradă LIBERĂ, asigurând un trafic DIVERS și FLUID.
        
        AI LA DISPOZIȚIE ACESTE RUTE VALIDE (Alege STRICT una din combinațiile de mai jos):
        - W_START (Vest) -> E_END, S2_END sau NW_END
        - E_START (Est) -> W_END, S1_END sau NW_END
        - S1_START (Sud 1) -> NW_END sau E_END
        - S2_START (Sud 2) -> W_END sau NW_END
        - NW_START (Nord-Vest) -> S1_END, E_END sau S2_END
        - NE_ONEWAY_START (Nord-Est) -> S2_END, W_END sau S1_END

        REGULI STRICTE:
        1. INTERZIS U-TURN! Nu trimite niciodată o mașină la aceeași ieșire de unde a plecat (ex: interzis W_START -> W_END). Alege DOAR din rutele de mai sus.
        2. FII IMPREVIZIBIL: Alege puncte de plecare diferite față de mașinile deja existente. Răspândește traficul pe toată harta!
        3. Alege o viteză realistă între 55.0 și 75.0.
        4. Alege tipul: 'Normal' (90% din cazuri) sau 'Ambulance' (10%).
        5. Dacă s-a aglomerat prea mult pe o rută, evit-o și alege alta liberă.
        
        RĂSPUNDE STRICT CU UN JSON VALID, fără niciun alt text, fix în acest format:
        {{"start_node": "...", "target_node": "...", "speed": 65.5, "v_type": "Normal"}}
        """,
            ),
            (
                "human",
                "Trafic curent pe hartă:\n{traffic_info}\n(Zar de diversitate: {rand_val})\nTe rog, analizează și trimite un vehicul nou pe o rută logică și liberă!",
            ),
        ]
    )

    spawn_chain = spawn_prompt | llm_spawn

    def ai_spawn_car():
        def task():
            print(
                "🧠 [Traffic Director] Scanează străzile și calculează ruta optimă..."
            )

            # 1. Colectăm pozițiile reale ale tuturor mașinilor din dicționarul 'agenti'
            active_cars = []
            for a_id, a in list(agenti.items()):
                if hasattr(a, "position_x") and hasattr(a, "position_y"):
                    active_cars.append(
                        f"{a_id} la (X:{a.position_x:.0f}, Y:{a.position_y:.0f}) mergand spre {a.heading}"
                    )

            traffic_info = "\n".join(active_cars)
            if not traffic_info:
                traffic_info = "Nicio mașină pe hartă. Orașul este complet gol."

            # 2. Injectăm un număr aleator pentru a forța AI-ul să schimbe mereu răspunsul (Diversitate)
            rand_val = random.randint(1, 10000)

            try:
                # 3. Pasăm informația reală către AI
                response = spawn_chain.invoke(
                    {"traffic_info": traffic_info, "rand_val": rand_val}
                )

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

                # 4. Creăm mașina pe nodul ales de el
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
                    f"✅ [Traffic Director] Succes! A evitat aglomerația și a creat {new_id} ({v_type}) la {start_n} -> {target_n}"
                )

            except Exception as e:
                print(
                    f"⚠️ [Traffic Director] Eroare format: {e}. Aplic Fallback Random."
                )
                rute_fallback = [
                    ("W_START", "E_END"),
                    ("NW_START", "S1_END"),
                    ("S2_START", "W_END"),
                    ("E_START", "W_END"),
                    ("S1_START", "NW_END"),
                ]
                sn, tn = random.choice(rute_fallback)
                fid = f"Fallback_{random.randint(10,99)}"
                agenti[fid] = VehicleAgent(fid, sn, tn, 60.0)

        threading.Thread(target=task, daemon=True).start()

    broker.trigger_spawn_car = ai_spawn_car
    # ==========================================
    # ==========================================
    # ==========================================

    # ==========================================
    # 2. SCENARII DE TESTARE PREDEFINITE (Haos Controlat)
    # ==========================================

    # --- SCENARIUL 1: ACC (Frânare la mașina din față) ---
    agent_lider = VehicleAgent(
        agent_id="Masina_Lider",
        start_node="W_START",
        target_node="E_END",
        desired_speed=34.0,  # Merge încet
    )

    agent_urmaritor = VehicleAgent(
        agent_id="Masina_Urmaritor",
        start_node="W_START",
        target_node="E_END",
        desired_speed=85.0,  # Vine glonț din spate
        driving_style="Aggressive",
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
                broker.publish(caprioara.agent_id, status_caprioara)
            else:
                with broker.lock:
                    broker.vehicles_status.pop(caprioara.agent_id, None)

            # ==================================================
            # DETECȚIE ACCIDENTE MAI REALISTĂ (Mașini + Căprioară)
            # ==================================================
            agent_ids = list(agenti.keys())
            for i in range(len(agent_ids)):
                a1 = agenti[agent_ids[i]]

                # --- NOU: 1. Coliziune cu CĂPRIOARA ---
                if status_caprioara is not None and not getattr(
                    a1, "is_crashed", False
                ):
                    dist_animal = math.sqrt(
                        (a1.position_x - caprioara.position_x) ** 2
                        + (a1.position_y - caprioara.position_y) ** 2
                    )
                    # Hitbox de 25px pentru căprioară. Se lovește doar dacă AI e oprit!

                    if dist_animal < 25 and not getattr(broker, "ai_enabled", True):
                        a1.is_crashed = True
                        caprioara.state = "CRASHED"  # NOU: Omorâm și căprioara!
                        print(f"🦌💥 ACCIDENT: {a1.agent_id} a lovit căprioara!")

                # --- 2. Coliziune între mașini ---
                for j in range(i + 1, len(agent_ids)):
                    a2 = agenti[agent_ids[j]]

                    if getattr(a1, "is_crashed", False) and getattr(
                        a2, "is_crashed", False
                    ):
                        continue

                    dist = math.sqrt(
                        (a1.position_x - a2.position_x) ** 2
                        + (a1.position_y - a2.position_y) ** 2
                    )

                    if dist < 16 and not getattr(broker, "ai_enabled", True):
                        a1.is_crashed = True
                        a2.is_crashed = True
                        print(
                            f"💥 ACCIDENT FATAL: {a1.agent_id} s-a izbit violent de {a2.agent_id}!"
                        )

            # Procesăm fiecare mașină
            for a_id, agent in list(agenti.items()):

                agent.memory.clear()

                # 1. V2X
                traffic = broker.receive(a_id)
                for o_id, o_data in traffic.items():
                    agent.receive_v2x_message(o_data)

                # 2. Alegem intersecția către care se îndreaptă mașina BAZAT PE RUTĂ
                target_int = (agent.position_x, agent.position_y)  # Fallback

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

                # 3. TRUCUL: Transmitem starea butonului AI către creierul mașinii!
                ai_este_pornit = getattr(broker, "ai_enabled", True)
                agent.decide_action(
                    target_int[0], target_int[1], ai_global_enabled=ai_este_pornit
                )

                agent.update_position(dt)

                # Marcăm agentul când intră în cadru
                if not is_outside_screen(agent):
                    seen_on_screen.add(a_id)

                # Îl ștergem doar dacă a ieșit din ecran ȘI NU E CRASHED
                # (Dacă e crashed, va rămâne pe ecran ca epavă)
                if (
                    a_id in seen_on_screen
                    and is_outside_screen(agent)
                    and not getattr(agent, "is_crashed", False)
                ):
                    with broker.lock:
                        broker.vehicles_status.pop(a_id, None)
                    del agenti[a_id]
                    seen_on_screen.discard(a_id)
                    continue

                # 4. Publicăm
                broker.publish(a_id, agent.get_emergency_status())
            time.sleep(dt)

    # PORNEȘTE DOAR ACEST THREAD (asigură-te că nu ai altul mai jos în main.py)
    threading.Thread(target=background_task, daemon=True).start()

    # UI-ul afișează datele din broker în timp real
    ui.start(broker)


if __name__ == "__main__":
    run_simulation()
