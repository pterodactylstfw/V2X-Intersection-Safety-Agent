import threading
import time
from v2x_network import V2XBroker
from vehicle_agent import VehicleAgent
from simulation_ui import SimulationUI


def run_simulation():
    # 1. Infrastructura
    broker = V2XBroker()
    ui = SimulationUI()

<<<<<<< Updated upstream
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
=======
    # 2. Agenții (Toți cei 4 conform regulilor de circulație RO)

    # Masina_A: Pleacă de la VEST(0) spre EST(1500), Banda de JOS (420)
    
    # 2. Agenții
    # 2. Agenții AI (Folosim parametri numiți pentru a evita erorile de poziție)
    # 2. Agenții AI (fără parametrul 'speed' care a fost scos de colegul tău)
    agent_a = VehicleAgent(
        agent_id="Masina_A", start_x=0.0, start_y=420.0, 
        target_destination=[1500, 420], desired_speed=70.0, heading="EAST"
    )
    
    agent_a2 = VehicleAgent(
        agent_id="Masina_A2", start_x=-120.0, start_y=420.0, 
        target_destination=[1500, 420], desired_speed=75.5, heading="EAST"
    )
    
    agent_b = VehicleAgent(
        agent_id="Ambulanta_B", start_x=380.0, start_y=0.0, 
        target_destination=[380, 800], desired_speed=70.0, 
        vehicle_type="Ambulance", heading="SOUTH", driving_style="Aggressive"
    )
    
    agent_c = VehicleAgent(
        agent_id="Masina_C", start_x=1120.0, start_y=800.0, 
        target_destination=[1120, 0], desired_speed=60.8, heading="NORTH"
    )

    agenti = {
        "Masina_A": agent_a,
        "Masina_A2": agent_a2,
        "Ambulanta_B": agent_b,
        "Masina_C": agent_c
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
>>>>>>> Stashed changes

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
