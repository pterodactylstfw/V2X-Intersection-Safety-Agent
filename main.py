import threading
import time
from v2x_network import V2XBroker
from vehicle_agent import VehicleAgent
from simulation_ui import SimulationUI
from traffic_light import IntelligentTrafficLight


def run_simulation():
    # 1. Infrastructura
    broker = V2XBroker()
    semafor = IntelligentTrafficLight(broker)
    semafor.start()
    ui = SimulationUI()

    # 2. Agenții (Toți cei 4 conform regulilor de circulație RO)

    # Masina_A: Pleacă de la VEST(0) spre EST(1500), Banda de JOS (420)
    agent_a = VehicleAgent("Masina_A", 0, 420, [1500, 420], 80.0, heading="EAST")

    # Ambulanta_B: Pleacă de la NORD(0) spre SUD(800), Intersecția 1, Banda STÂNGA (380)
    agent_b = VehicleAgent(
        "Ambulanta_B",
        380,
        0,
        [380, 800],
        100.0,
        vehicle_type="Ambulance",
        heading="SOUTH",
    )

    # Masina_C: Pleacă de la SUD(800) spre NORD(0), Intersecția 2, Banda DREAPTA (1120)
    agent_c = VehicleAgent("Masina_C", 1120, 800, [1120, 0], 75.0, heading="NORTH")

    # Masina_D: Pleacă de la EST(1500) spre VEST(0), Banda de SUS (380)
    agent_d = VehicleAgent("Masina_D", 1500, 380, [0, 380], 85.0, heading="WEST")

    # Punem toți agenții în dicționar
    agenti = {
        "Masina_A": agent_a,
        "Ambulanta_B": agent_b,
        "Masina_C": agent_c,
        "Masina_D": agent_d,
    }

    def background_task():
        dt = 0.05  # Recomandat 0.05 pentru stabilitate pe Mac
        while True:
            for a_id, agent in agenti.items():
                # 1. Comunicare V2X
                traffic = broker.receive(a_id)
                for o_id, o_data in traffic.items():
                    agent.receive_v2x_message(o_data)

                # 2. Logica de decizie: Mașina alege cea mai apropiată intersecție
                # Avem Intersecția 1 la x=400 și Intersecția 2 la x=1100
                target_int_x = 400 if agent.position_x < 750 else 1100
                agent.decide_action(target_int_x, 400)

                agent.update_position(dt)

                # 3. Publicăm starea
                broker.publish(a_id, agent.get_emergency_status())
            time.sleep(dt)

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
