import threading
from v2x_network import V2XBroker, DataFeeder
from vehicle_agent import VehicleAgent
from simulation_ui import SimulationUI

def run_simulation():
    # 1. Infrastructura
    broker = V2XBroker()
    ui = SimulationUI()
    
    # 2. Agenții
    # În main.py, la crearea agenților:
    agent_a = VehicleAgent("Masina_A", 0, 400, 3.5, heading="EAST")
    agent_b = VehicleAgent("Ambulanta_B", 400, 0, 5.0, vehicle_type="Ambulance", heading="SOUTH")
    agenti = {"Masina_A": agent_a, "Ambulanta_B": agent_b}

    # 3. Thread-ul pentru logică și alimentare (rulează în fundal)
    def background_logic():
        feeder = DataFeeder(broker, "scenariu.json", agents_dict=agenti)
        feeder.load_scenario()
        feeder.play_scenario(delay_seconds=0.05)

    # ... în funcția run_simulation ...
    
    # Pornim thread-ul de LOGICĂ și FEEDER în spate (daemon=True)
    def background_task():
        # Pasul A: Încărcăm scenariul
        feeder = DataFeeder(broker, "scenariu.json", agents_dict=agenti)
        feeder.load_scenario()
        # Pasul B: Pornim redarea (aceasta va actualiza broker-ul la fiecare 0.05s)
        feeder.play_scenario(delay_seconds=0.05)

    logic_thread = threading.Thread(target=background_task, daemon=True)
    logic_thread.start()

    # UI-ul pornește ultimul și rămâne activ pe ecran
    ui.start(broker)

if __name__ == "__main__":
    run_simulation()