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
    agent_a = VehicleAgent(
        agent_id="Masina_A",
        start_x=0.0,
        start_y=420.0,
        target_destination=[1500, 420],
        desired_speed=60.0,
        heading="EAST",
    )

    agent_a2 = VehicleAgent(
        agent_id="Masina_A2",
        start_x=-120.0,
        start_y=420.0,
        target_destination=[1500, 420],
        desired_speed=75.5,
        heading="EAST",
    )

    agent_b = VehicleAgent(
        agent_id="Ambulanta_B",
        start_x=380.0,
        start_y=0.0,
        target_destination=[380, 800],
        desired_speed=60.0,
        vehicle_type="Ambulance",
        heading="SOUTH",
        driving_style="Aggressive",
    )

    agent_c = VehicleAgent(
        agent_id="Masina_C",
        start_x=1120.0,
        start_y=800.0,
        target_destination=[1120, 0],
        desired_speed=60.8,
        heading="NORTH",
    )

    agenti = {
        "Masina_A": agent_a,
        "Masina_A2": agent_a2,
        "Ambulanta_B": agent_b,
        "Masina_C": agent_c,
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
        while True:
            for a_id, agent in list(agenti.items()):
                # 1. V2X
                traffic = broker.receive(a_id)
                for o_id, o_data in traffic.items():
                    agent.receive_v2x_message(o_data)

                # 2. Alegem intersecția cea mai apropiată (ZONARE)
                # Intersecția 1 e la x=400, Intersecția 2 la x=1100
                target_int_x = 400 if agent.position_x < 750 else 1100
                agent.decide_action(target_int_x, 400)

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
