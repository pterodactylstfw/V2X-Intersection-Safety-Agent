import threading
import time
from traffic_light import TrafficLightAgent
from v2x_network import V2XBroker
from vehicle_agent import VehicleAgent
from simulation_ui import SimulationUI


def run_simulation():
    # 1. Infrastructura
    broker = V2XBroker()
    ui = SimulationUI()

    semafor = TrafficLightAgent(broker)
    semafor.start()

    # 2. Agenții (Toți cei 4 conform regulilor de circulație RO)

    # Masina_A: Pleacă de la VEST(0) spre EST(1500), Banda de JOS (420)

    # 2. Agenții
    # 2. Agenții AI (Folosim parametri numiți pentru a evita erorile de poziție)
    # 2. Agenții AI (fără parametrul 'speed' care a fost scos de colegul tău)
    # ==========================================
    # 2. SCENARII DE TESTARE (Haos Controlat)
    # ==========================================

    # --- SCENARIUL 1: ACC (Frânare la mașina din față) ---
    agent_lider = VehicleAgent(
        agent_id="Masina_Lider",
        start_node="W_START",
        target_node="E_END",
        desired_speed=35.0, # Merge încet
    )

    agent_urmaritor = VehicleAgent(
        agent_id="Masina_Urmaritor",
        start_node="W_START",
        target_node="E_END",
        desired_speed=85.0, # Vine glonț din spate
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
    agent_s1.position_y += 80 # O întârziem puțin ca să se întâlnească fix în mijloc cu Liderul

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
        "Ambulanta_VIP": agent_amb
    }

    # Agenți care au fost deja vizibili cel puțin o dată pe ecran
    seen_on_screen = set()

    def is_outside_screen(agent):
        return (
            agent.position_x < 0
            or agent.position_x > 1500
            or agent.position_y < 0
            or agent.position_y > 800
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
            for a_id, agent in list(agenti.items()):
                # 1. V2X
                traffic = broker.receive(a_id)
                for o_id, o_data in traffic.items():
                    agent.receive_v2x_message(o_data)

                # 2. Alegem dinamic CEA MAI APROPIATĂ intersecție
                # 2. Alegem intersecția către care se îndreaptă mașina BAZAT PE RUTĂ
                target_int = (agent.position_x, agent.position_y) # Fallback
                
                # Căutăm în viitorul rutei ce intersecție urmează
                for idx in range(agent.current_node_index + 1, len(agent.route)):
                    n = agent.route[idx]
                    if "I1" in n: target_int = (400, 650); break
                    elif "I2" in n: target_int = (1100, 650); break
                    elif "I3" in n: target_int = (400, 300); break
                    elif "MERGE" in n or "I4" in n: target_int = (770, 455); break

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
