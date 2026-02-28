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

        # 1. Ignorăm calculele dacă suntem departe
        if dist_to_int > 250:
            self._recover_speed()
            return

        my_ttc = self.calculate_ttc(int_x, int_y)
        conflict_detected = False

        for other_id, other_data in list(self.memory.items()):
            # --- REPARAȚIE 1: IGNORĂM SEMAFORUL ÎN CALCULUL DE COLIZIUNE ---
            # Nu ne lovim fizic de semafor, el e infrastructură!
            if other_data.get("vehicle_type") == "Infrastructure":
                # Aici poți adăuga logică de semafor mai târziu (ex: dacă e RED, frânezi)
                continue

            # --- REPARAȚIE 2: IGNORĂM MAȘINILE CARE AU TRECUT ---
            ox, oy = other_data["position_x"], other_data["position_y"]
            oh = other_data.get("heading", "")

            past = False
            if oh == "SOUTH" and oy > intersection_y + 60:
                past = True
            if oh == "NORTH" and oy < intersection_y - 60:
                past = True
            if oh == "EAST" and ox > intersection_x + 60:
                past = True
            if oh == "WEST" and ox < intersection_x - 60:
                past = True

            if past:
                continue

            # --- CALCUL COLIZIUNE ---
            other_speed = other_data["speed"]
            # Prevenim erori dacă viteza e aproape 0
            if other_speed < 1.0:
                other_ttc = 999
            else:
                other_dist = math.sqrt(
                    (intersection_x - ox) ** 2 + (intersection_y - oy) ** 2
                )
                other_ttc = other_dist / other_speed

            # Dacă riscăm să ajungem în același timp (fereastră de 5 secunde)
            if abs(my_ttc - other_ttc) < 5.0:
                conflict_detected = True
                if self.vehicle_type == "Ambulance":
                    self._recover_speed()
                    return
                if other_data.get("vehicle_type") == "Ambulance":
                    self._brake("Prioritate Ambulanță")
                    return

                self._negotiate_ai(other_id, other_data)
                return

        # Dacă am ajuns aici, nu e niciun conflict activ
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
