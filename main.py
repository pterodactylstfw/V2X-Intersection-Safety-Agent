import threading
import time
from v2x_network import V2XBroker
from vehicle_agent import VehicleAgent
from simulation_ui import SimulationUI


def run_simulation():
    # 1. Infrastructura
    broker = V2XBroker()
    ui = SimulationUI()

    # 2. Agenții (REPARAT: am adăugat target_destination și desired_speed)
    # Masina_A pleacă de la (0, 400) spre (800, 400) cu viteza 3.5
    # Folosește viteze între 60 și 100 (pixeli pe secundă)
    # În main.py, în funcția run_simulation():
    # Masina_A: pleacă de la 0, vrea să ajungă la 800 (pe axa X), viteză 70
    # 2. Agenții: Viteze de 70-100 px/s pentru a se mișca natural
    # 2. Agenții: Viteze de 70-100 px/s pentru a se mișca natural
    # Folosește viteze între 60 și 90 pixeli pe secundă
    agent_a = VehicleAgent("Masina_A", 0, 400, [800, 400], 70.0, heading="EAST")
    agent_b = VehicleAgent(
        "Ambulanta_B",
        400,
        0,
        [400, 800],
        85.0,
        vehicle_type="Ambulance",
        heading="SOUTH",
    )
    agenti = {"Masina_A": agent_a, "Ambulanta_B": agent_b}

    def background_task():
        dt = 0.02
        while True:
            for a_id, agent in agenti.items():
                # 1. Comunicare V2X: Agentul preia datele din rețea
                traffic = broker.receive(a_id)
                for o_id, o_data in traffic.items():
                    agent.receive_v2x_message(o_data)

                # 2. Agentul decide și se mișcă (NU mai folosim coordonate din JSON)
                agent.decide_action(400, 400)
                agent.update_position(dt)

                # 3. Publicăm starea calculată de AI
                broker.publish(a_id, agent.get_emergency_status())
            time.sleep(dt)

    # Pornim thread-ul de simulare în fundal
    threading.Thread(target=background_task, daemon=True).start()

    # UI-ul afișează datele din broker în timp real
    ui.start(broker)


if __name__ == "__main__":
    run_simulation()
