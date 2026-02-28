import math
import threading
import time

class TrafficLightAgent:
    def __init__(self, broker, agent_id="Semafor_Centru"):
        self.broker = broker
        self.agent_id = agent_id
        self.state_NS = "GREEN"  # Axa Nord-Sud
        self.state_EW = "RED"  # Axa Est-Vest
        self.running = True

    def start(self):
        """Pornim semaforul pe un thread separat pentru a nu bloca interfața grafică."""
        threading.Thread(target=self._run_loop, daemon=True).start()

    def _run_loop(self):
        while self.running:
            # 1. VERIFICARE BUTON AVARIE
            if not getattr(self.broker, "infrastructure_active", True):
                self._publish_state("YELLOW_BLINKING", "YELLOW_BLINKING", time_to_change=0.0)
                time.sleep(0.5)  # Rulăm frecvent pentru a detecta repornirea
                continue

            traffic_data = self.broker.receive(self.agent_id)
            emergency_heading = None
            
            for v_id, v_data in traffic_data.items():
                if v_data.get("vehicle_type") == "Ambulance":  # Dacă e ambulanță
                    dist_to_center = math.sqrt(
                        (400 - v_data.get("position_x", 0)) ** 2
                        + (400 - v_data.get("position_y", 0)) ** 2
                    )
                    if dist_to_center < 300:  # Și e aproape de intersecție
                        emergency_heading = v_data.get("heading")
                        break

            # URGENȚĂ: Ambulanța forțează culoarea
            if emergency_heading:
                if emergency_heading in ["NORTH", "SOUTH"]:
                    self._publish_state("GREEN", "RED", time_to_change=99.0)  # 99.0 = ține verde indefinit
                else:
                    self._publish_state("RED", "GREEN", time_to_change=99.0)
                time.sleep(0.1)
                continue  # Sari peste ciclul normal cât timp e urgență

            # 2. CICLUL NORMAL (Am integrat GLOSA aici)
            # Trimitem timpul rămas direct din funcția de așteptare!
            
            # NS Verde, EW Roșu (5 secunde)
            if not self._wait_interruptible(5.0, "GREEN", "RED"):
                continue

            # NS Galben, EW Roșu (2 secunde)
            if not self._wait_interruptible(2.0, "YELLOW", "RED"):
                continue

            # NS Roșu, EW Verde (5 secunde)
            if not self._wait_interruptible(5.0, "RED", "GREEN"):
                continue

            # NS Roșu, EW Galben (2 secunde)
            if not self._wait_interruptible(2.0, "RED", "YELLOW"):
                continue

    def _wait_interruptible(self, duration, state_ns, state_ew):
        """Așteaptă un anumit timp, dar publică numărătoarea inversă pentru mașini (GLOSA)."""
        steps = int(duration / 0.1)
        for step in range(steps):
            if not getattr(self.broker, "infrastructure_active", True):
                return False
            
            # CALCULĂM TIMPUL RĂMAS: total pași - pașii făcuți
            time_to_change = (steps - step) * 0.1
            
            # Publicăm starea la fiecare 0.1 secunde, cu tot cu timpul rămas!
            self._publish_state(state_ns, state_ew, time_to_change)
            
            time.sleep(0.1)
        return True

    def _publish_state(self, ns, ew, time_to_change):
        """Trimite starea curentă către toate mașinile din rețea."""
        self.state_NS = ns
        self.state_EW = ew
        data_package = {
            "agent_id": self.agent_id,
            "vehicle_type": "Infrastructure",
            "state_NS": self.state_NS,
            "state_EW": self.state_EW,
            "time_to_change": round(time_to_change, 1), # <--- AICI ESTE MAGIA GLOSA
            "position_x": 400,
            "position_y": 400,
        }
        self.broker.publish(self.agent_id, data_package)