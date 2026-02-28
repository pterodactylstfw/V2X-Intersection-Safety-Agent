import time
import threading

class IntelligentTrafficLight:
    def __init__(self, broker, agent_id="Semafor_Centru"):
        self.broker = broker
        self.agent_id = agent_id
        
        # Starea inițială a intersecției (Verde pentru Nord-Sud, Roșu pentru Est-Vest)
        self.state_NS = "GREEN"  # Axa Nord-Sud (Vertical)
        self.state_EW = "RED"    # Axa Est-Vest (Orizontal)
        
        self.timer = 0
        self.switch_interval = 50 # Schimbă culoarea la fiecare 5 secunde (50 cicluri de 0.1s)

    def start(self):
        """Pornește "creierul" semaforului pe un thread separat."""
        threading.Thread(target=self._run_logic, daemon=True).start()

    def _run_logic(self):
        print(f"[{self.agent_id}] V2I pornit! Monitorizez intersecția...")
        while True:
            # 1. Ascultăm traficul din rețeaua V2X
            traffic_data = self.broker.receive(self.agent_id)
            emergency_detected = False
            
            for v_id, v_data in traffic_data.items():
                # Dacă mașina curentă a declarat că are PRIORITATE ACTIVĂ (ex: Ambulanță)
                if v_data.get("priority_active") == True:
                    emergency_detected = True
                    heading = v_data.get("heading", "")
                    
                    # Funcția de Preemption: Îi dăm verde instantaneu pe axa pe care vine!
                    if heading in ["NORTH", "SOUTH"]:
                        self.state_NS = "GREEN"
                        self.state_EW = "RED"
                    elif heading in ["EAST", "WEST"]:
                        self.state_NS = "RED"
                        self.state_EW = "GREEN"
                        
                    print(f"!!! [V2I ALARMĂ] Semaforul a detectat {v_id}. S-a forțat VERDE pentru {heading}! !!!")
                    break # Ieșim din buclă, am rezolvat urgența

            # 2. Dacă NU e nicio urgență, semaforul își vede de ciclul lui normal
            if not emergency_detected:
                self.timer += 1
                if self.timer >= self.switch_interval:
                    self.timer = 0 # Resetăm timer-ul
                    # Inversăm culorile
                    if self.state_NS == "GREEN":
                        self.state_NS = "RED"
                        self.state_EW = "GREEN"
                    else:
                        self.state_NS = "GREEN"
                        self.state_EW = "RED"

            # 3. Publicăm starea semaforului înapoi în rețea (mesaj SPaT)
            spat_message = {
                "agent_id": self.agent_id,
                "vehicle_type": "Infrastructure", # Ca să știe interfața și logica ce e
                "state_NS": self.state_NS,
                "state_EW": self.state_EW,
                # Recomandăm viteză mașinilor în funcție de culoare
                "recommended_speed_NS": 5.0 if self.state_NS == "GREEN" else 0.0,
                "recommended_speed_EW": 5.0 if self.state_EW == "GREEN" else 0.0
            }
            
            self.broker.publish(self.agent_id, spat_message)
            
            time.sleep(0.1) # Bucla rulează de 10 ori pe secundă