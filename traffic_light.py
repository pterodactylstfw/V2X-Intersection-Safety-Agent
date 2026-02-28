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
            # 1. VERIFICARE BUTON AVARIE (folosim getattr pentru siguranță în caz că uităm flag-ul)
            if not getattr(self.broker, "infrastructure_active", True):
                self._publish_state("YELLOW_BLINKING", "YELLOW_BLINKING")
                time.sleep(0.5)  # Rulăm frecvent pentru a detecta repornirea
                continue

            traffic_data = self.broker.receive(self.agent_id)
            emergency_heading = None
            for v_id, v_data in traffic_data.items():
                if v_data.get("vehicle_type") == "Ambulance":  # Dacă e ambulanță
                    dist_to_center = math.sqrt(
                        (400 - v_data["position_x"]) ** 2
                        + (400 - v_data["position_y"]) ** 2
                    )
                    if dist_to_center < 300:  # Și e aproape de intersecție
                        emergency_heading = v_data.get("heading")
                        break

            if emergency_heading:
                if emergency_heading in ["NORTH", "SOUTH"]:
                    self._publish_state("GREEN", "RED")  # Forțăm verde pe Nord-Sud
                else:
                    self._publish_state("RED", "GREEN")  # Forțăm verde pe Est-Vest
                time.sleep(0.1)
                continue  # Sari peste ciclul normal cât timp e urgență

            # 2. CICLUL NORMAL
            # NS Verde, EW Roșu
            self._publish_state("GREEN", "RED")
            if not self._wait_interruptible(5.0):
                continue

            # NS Galben, EW Roșu
            self._publish_state("YELLOW", "RED")
            if not self._wait_interruptible(2.0):
                continue

            # NS Roșu, EW Verde
            self._publish_state("RED", "GREEN")
            if not self._wait_interruptible(5.0):
                continue

            # NS Roșu, EW Galben
            self._publish_state("RED", "YELLOW")
            if not self._wait_interruptible(2.0):
                continue

    def _wait_interruptible(self, duration):
        """Așteaptă un anumit timp, dar se oprește imediat dacă utilizatorul apasă butonul de avarie.
        Returnează True dacă ciclul s-a terminat normal, False dacă a fost întrerupt."""
        steps = int(duration / 0.1)
        for _ in range(steps):
            if not getattr(self.broker, "infrastructure_active", True):
                return False
            time.sleep(0.1)
        return True

    def _publish_state(self, ns, ew):
        """Trimite starea curentă către toate mașinile din rețea."""
        self.state_NS = ns
        self.state_EW = ew
        data_package = {
            "agent_id": self.agent_id,
            "vehicle_type": "Infrastructure",
            "state_NS": self.state_NS,
            "state_EW": self.state_EW,
            # Poți ajusta coordonatele centrului intersecției tale aici:
            "position_x": 400,
            "position_y": 400,
        }
        self.broker.publish(self.agent_id, data_package)
