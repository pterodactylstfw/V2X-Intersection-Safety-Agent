import math
import os
import time
import threading
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()


class VehicleAgent:
    def __init__(
        self,
        agent_id,
        start_x,
        start_y,
        target_destination,
        desired_speed,
        vehicle_type="Normal",
        driving_style="Cautious",
        heading="NORTH",
    ):
        self.agent_id = agent_id
        self.position_x = start_x
        self.position_y = start_y
        self.target_destination = target_destination
        self.desired_speed = desired_speed
        self.speed = desired_speed
        self.heading = heading
        self.vehicle_type = vehicle_type
        self.driving_style = driving_style
        self.current_state = "CRUISE"
        self.memory = {}
        self.last_ai_decision = None
        self.last_ai_call_time = 0
        self.decision_cooldown = 1.0
        self.waiting_for_ai = False

        self.llm = ChatGroq(temperature=0, model_name="llama-3.1-8b-instant")
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Ești un agent de trafic AI. Răspunde DOAR: FRANEAZA sau TRECE.",
                ),
                (
                    "human",
                    "Eu sunt {my_id} ({my_type}). Celălalt e {other_id} ({other_type}). Cine trece?",
                ),
            ]
        )
        self.chain = self.prompt | self.llm

    def receive_v2x_message(self, message):
        sender_id = message.get("agent_id")
        if sender_id and sender_id != self.agent_id:
            self.memory[sender_id] = message

    def calculate_ttc(self, target_x, target_y):
        if self.speed < 1.0:
            return 999
        dist = math.sqrt(
            (target_x - self.position_x) ** 2 + (target_y - self.position_y) ** 2
        )
        return dist / self.speed

    def decide_action(self, int_x, int_y):
        # 1. VERIFICARE: Am trecut de intersecție?
        is_past = False
        if self.heading == "EAST" and self.position_x > int_x + 50:
            is_past = True
        if self.heading == "WEST" and self.position_x < int_x - 50:
            is_past = True
        if self.heading == "SOUTH" and self.position_y > int_y + 50:
            is_past = True
        if self.heading == "NORTH" and self.position_y < int_y - 50:
            is_past = True

        if is_past:
            self._recover_speed()
            self.last_ai_decision = None
            return

        # 2. ACC: Siguranță față de mașina din față (pe aceeași bandă)
        for other_id, other_data in list(self.memory.items()):
            if other_data.get("heading") == self.heading:
                ox, oy = other_data["position_x"], other_data["position_y"]
                dist = math.sqrt(
                    (ox - self.position_x) ** 2 + (oy - self.position_y) ** 2
                )

                # Dacă mașina e în față (calcul simplificat pe axe)
                if dist < 110.0:  # Creștem distanța de siguranță la 110px
                    if (
                        (self.heading == "EAST" and ox > self.position_x)
                        or (self.heading == "SOUTH" and oy > self.position_y)
                        or (self.heading == "NORTH" and oy < self.position_y)
                        or (self.heading == "WEST" and ox < self.position_x)
                    ):
                        self._brake(f"ACC: Distanță mică față de {other_id}")
                        return

        # 3. INTERSECȚIE: V2V & V2I
        dist_to_int = math.sqrt(
            (int_x - self.position_x) ** 2 + (int_y - self.position_y) ** 2
        )
        if dist_to_int > 250.0:
            self._recover_speed()
            return

        # --- LOGICA PENTRU SEMAFOR (V2I) ---
        used_infrastructure = False
        for other_id, other_data in list(self.memory.items()):
            if other_data.get("vehicle_type") == "Infrastructure":
                used_infrastructure = True

                if self.heading in ["NORTH", "SOUTH"]:
                    light_state = other_data.get("state_NS", "YELLOW_BLINKING")
                else:
                    light_state = other_data.get("state_EW", "YELLOW_BLINKING")

                # Dacă semaforul e pe avarie, trecem la V2V direct
                if light_state == "YELLOW_BLINKING":
                    used_infrastructure = False
                    break

                # La ROȘU sau GALBEN
                if light_state in ["RED", "YELLOW"]:
                    # Frânăm doar dacă nu am intrat deja adânc în intersecție (< 30px)
                    # Astfel, forțăm mașina să respecte roșul și să nu intre în V2V
                    if dist_to_int > 30.0:
                        # Printăm în consolă să vedem clar de ce oprește
                        # print(f"[{self.agent_id}] Opresc la SEMAFOR ({light_state}). Distanța: {dist_to_int:.1f}")
                        self._brake(f"Semafor {light_state}")
                        return

                # La VERDE
                if light_state == "GREEN":
                    # print(f"[{self.agent_id}] Am VERDE, trec fără V2V!")
                    break

            if other_data.get("vehicle_type") == "Ambulance":
                # REPARAȚIE: Cedăm doar dacă ambulanța are viteză (se deplasează)
                # SAU dacă e deja foarte aproape de centrul intersecției
                o_speed = other_data.get("speed", 0)
                o_dist_to_int = math.sqrt((int_x - ox) ** 2 + (int_y - oy) ** 2)

                if o_speed > 1.0 or o_dist_to_int < 50:
                    self._brake("Prioritate Ambulanță în mișcare")
                    return
                else:
                    # Dacă ambulanța stă la roșu, o ignorăm și mergem pe treaba noastră
                    continue

        my_ttc = self.calculate_ttc(int_x, int_y)
        conflict_detected = False

        for other_id, other_data in list(self.memory.items()):
            if other_data.get("vehicle_type") == "Infrastructure":
                continue
            if other_data.get("heading") == self.heading:
                continue

            ox, oy = other_data["position_x"], other_data["position_y"]
            oh = other_data.get("heading", "")

            # IGNORĂM mașinile care AU TRECUT de centru
            other_past = False
            if oh == "SOUTH" and oy > int_y + 40:
                other_past = True
            if oh == "NORTH" and oy < int_y - 40:
                other_past = True
            if oh == "EAST" and ox > int_x + 40:
                other_past = True
            if oh == "WEST" and ox < int_x - 40:
                other_past = True
            if other_past:
                continue

            # Calculăm TTC pentru celălalt
            o_speed = other_data["speed"]
            o_dist = math.sqrt((int_x - ox) ** 2 + (int_y - oy) ** 2)
            o_ttc = o_dist / o_speed if o_speed > 2.0 else 999

            if abs(my_ttc - o_ttc) < 4.5:  # Fereastră de conflict
                conflict_detected = True
                if self.vehicle_type == "Ambulance":
                    self._recover_speed()
                    return
                if other_data.get("vehicle_type") == "Ambulance":
                    self._brake("Prioritate Ambulanță")
                    return

                self._negotiate_ai(other_id, other_data)
                return

        if not conflict_detected:
            self.last_ai_decision = None
            self._recover_speed()

    def _brake(self, reason):
        self.current_state = "BRAKING"
        # Frânare mai agresivă dacă suntem foarte aproape
        self.speed = max(0, self.speed - 4.5)

    def _recover_speed(self):
        self.current_state = "CRUISE"
        if self.speed < self.desired_speed:
            self.speed = min(self.desired_speed, self.speed + 2.0)

    def _negotiate_ai(self, other_id, other_data):
        if self.waiting_for_ai:
            return

        current_time = time.time()
        if self.last_ai_decision and (
            current_time - self.last_ai_call_time < self.decision_cooldown
        ):
            if "FRANEAZA" in self.last_ai_decision:
                self._brake("AI Decision")
            else:
                self._recover_speed()
            return

        self.waiting_for_ai = True

        def ai_task():
            try:
                res = self.chain.invoke(
                    {
                        "my_id": self.agent_id,
                        "my_type": self.vehicle_type,
                        "other_id": other_id,
                        "other_type": other_data.get("vehicle_type"),
                    }
                )
                self.last_ai_decision = res.content.upper()
                self.last_ai_call_time = time.time()
            except:
                self.last_ai_decision = "FRANEAZA"
            finally:
                self.waiting_for_ai = False

        threading.Thread(target=ai_task, daemon=True).start()

    def update_position(self, dt):
        if self.speed <= 0:
            return
        tx, ty = self.target_destination
        angle = math.atan2(ty - self.position_y, tx - self.position_x)
        self.position_x += self.speed * dt * math.cos(angle)
        self.position_y += self.speed * dt * math.sin(angle)

    def get_emergency_status(self):
        return {
            "agent_id": self.agent_id,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "speed": self.speed,
            "vehicle_type": self.vehicle_type,
            "intent": self.current_state,
            "heading": self.heading,
        }

    def has_decided_to_brake(self):
        return self.current_state == "BRAKING"
