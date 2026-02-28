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
        # ==========================================
        # 0. ACC (Adaptive Cruise Control) - Evitarea Coliziunilor Frontale
        # ==========================================
        for other_id, other_data in list(self.memory.items()):
            if other_data.get("vehicle_type") == "Infrastructure":
                continue
            
            oh = other_data.get("heading", "")
            if oh == self.heading:  # Verificăm doar mașinile care merg în aceeași direcție
                ox = other_data.get("position_x", 0)
                oy = other_data.get("position_y", 0)
                
                is_in_front = False
                # Verificăm dacă e pe aceeași bandă (toleranță de 20px la Y) și e fizic în fața noastră
                if self.heading == "EAST" and ox > self.position_x and abs(oy - self.position_y) < 20: is_in_front = True
                elif self.heading == "WEST" and ox < self.position_x and abs(oy - self.position_y) < 20: is_in_front = True
                elif self.heading == "SOUTH" and oy > self.position_y and abs(ox - self.position_x) < 20: is_in_front = True
                elif self.heading == "NORTH" and oy < self.position_y and abs(ox - self.position_x) < 20: is_in_front = True

                if is_in_front:
                    dist_to_front = math.sqrt((ox - self.position_x)**2 + (oy - self.position_y)**2)
                    if dist_to_front < 90.0:  # 90 pixeli este distanța de siguranță
                        self._brake(f"ACC: Frânez ca să nu lovesc {other_id}")
                        return 

        # 1. VERIFICARE: Am trecut de intersecție?
        is_past = False
        if self.heading == "EAST" and self.position_x > int_x + 50: is_past = True
        if self.heading == "WEST" and self.position_x < int_x - 50: is_past = True
        if self.heading == "SOUTH" and self.position_y > int_y + 50: is_past = True
        if self.heading == "NORTH" and self.position_y < int_y - 50: is_past = True

        if is_past:
            self._recover_speed()
            self.last_ai_decision = None
            return

        # ==========================================
        # 2. V2I (GLOSA) & VERIFICARE POZIȚIE SEMAFOR
        # ==========================================
        distance_to_center = math.sqrt((int_x - self.position_x)**2 + (int_y - self.position_y)**2)
        semafor_data = self.memory.get("Semafor_Centru")
        
        is_light_here = False
        if semafor_data:
            light_x = semafor_data.get("position_x", 400)
            if abs(int_x - light_x) < 50: 
                is_light_here = True
        
        if semafor_data and is_light_here and self.vehicle_type != "Ambulance":
            culoare_axa_mea = "GREEN"
            if self.heading in ["NORTH", "SOUTH"]: 
                culoare_axa_mea = semafor_data.get("state_NS", "GREEN")
            elif self.heading in ["EAST", "WEST"]: 
                culoare_axa_mea = semafor_data.get("state_EW", "GREEN")
                
            time_to_change = semafor_data.get("time_to_change", 5.0)

            # SCENARIUL A: Este ROȘU în față
            if culoare_axa_mea == "RED":
                # FIX: Am modificat de la 150.0 la 80.0 ca să oprească fix la linia intersecției!
                if distance_to_center < 80.0:
                    self._brake("V2I: Opresc la Semafor ROȘU")
                    return 
                elif distance_to_center < 400.0:
                    cadre_ramase = time_to_change * 20 
                    if cadre_ramase > 0:
                        viteza_optima = distance_to_center / cadre_ramase
                        viteza_optima = min(self.desired_speed, max(1.0, viteza_optima))
                        
                        if self.speed > viteza_optima:
                            self.speed = max(viteza_optima, self.speed - 0.2)
                            return

            # SCENARIUL B: Este VERDE în față
            elif culoare_axa_mea == "GREEN":
                # FIX: Am modificat și aici la 80.0
                if time_to_change < 1.0 and distance_to_center > 80.0:
                    self._brake("V2I GLOSA: Nu am timp să prind verdele!")
                    return

        # ==========================================
        # 3. PRIORITATE ABSOLUTĂ AMBULANȚĂ (V2V)
        # ==========================================
        dist_to_int = distance_to_center
        
        if self.vehicle_type != "Ambulance":
            for other_id, other_data in list(self.memory.items()):
                if other_data.get("vehicle_type") == "Ambulance":
                    ox = other_data.get("position_x", 0)
                    oy = other_data.get("position_y", 0)
                    oh = other_data.get("heading", "")
                    o_speed = other_data.get("speed", 0)
                    o_dist_to_int = math.sqrt((int_x - ox)**2 + (int_y - oy)**2)
                    
                    amb_past = False
                    if oh == "SOUTH" and oy > int_y + 40: amb_past = True
                    if oh == "NORTH" and oy < int_y - 40: amb_past = True
                    if oh == "EAST" and ox > int_x + 40: amb_past = True
                    if oh == "WEST" and ox < int_x - 40: amb_past = True
                    
                    if not amb_past and o_speed > 1.0 and o_dist_to_int < 350.0:
                        # FIX: Nu mai oprim oriunde! 
                        # Dacă suntem între 60 și 120px, punem frână ca să stăm la linie
                        if 60.0 < dist_to_int < 120.0: 
                            self._brake("Cedez trecerea Ambulanței!")
                            return 
                        # Dacă suntem departe (> 120px), doar încetinim elegant ca să ne apropiem de linie
                        elif dist_to_int >= 120.0:
                            self.speed = max(1.5, self.speed - 0.2)
                            return

        if dist_to_int > 250.0:
            self._recover_speed()
            return

        # ==========================================
        # 4. LOGICA PENTRU SEMAFOR (V2I) - Fără GLOSA
        # ==========================================
        for other_id, other_data in list(self.memory.items()):
            if other_data.get("vehicle_type") == "Infrastructure":
                
                light_x = other_data.get("position_x", 400)
                if abs(int_x - light_x) > 50:
                    continue 

                if self.heading in ["NORTH", "SOUTH"]:
                    light_state = other_data.get("state_NS", "YELLOW_BLINKING")
                else:
                    light_state = other_data.get("state_EW", "YELLOW_BLINKING")

                if light_state == "YELLOW_BLINKING":
                    break 

                if light_state in ["RED", "YELLOW"]:
                    if self.vehicle_type == "Ambulance":
                        pass 
                    # FIX: Frânăm de urgență la roșu doar dacă suntem între 50 și 150px de intersecție
                    elif 50.0 < dist_to_int < 150.0:
                        self._brake(f"Semafor {light_state}")
                        return

                if light_state == "GREEN":
                    break
        # ==========================================
        # 5. NEGOCIERE V2V / AI (Când nu e semafor sau e pe avarie)
        # ==========================================
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
            if oh == "SOUTH" and oy > int_y + 40: other_past = True
            if oh == "NORTH" and oy < int_y - 40: other_past = True
            if oh == "EAST" and ox > int_x + 40: other_past = True
            if oh == "WEST" and ox < int_x - 40: other_past = True
            
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
