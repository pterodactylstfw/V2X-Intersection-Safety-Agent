import math
import os
import time
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import threading

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
        self.target_destination = target_destination  # [target_x, target_y]
        self.desired_speed = desired_speed  # Viteza de croazieră (ex: 70)
        self.speed = desired_speed
        self.heading = heading
        self.vehicle_type = vehicle_type
        self.driving_style = driving_style
        self.current_state = "CRUISE"
        self.memory = {}
        self.last_ai_decision = None
        self.last_ai_call_time = 0
        self.decision_cooldown = 2.0

        self.llm = ChatGroq(temperature=0, model_name="llama-3.1-8b-instant")
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Ești un agent de trafic AI autonom. Decizi cine trece intersecția.\n"
                    "Mașina ta: ID {my_id}, tip {my_type}.\n"
                    "Mașina adversă: ID {other_id}, tip {other_type}.\n\n"
                    "REGULI STRICTE:\n"
                    "1. Dacă adversarul este 'Ambulance' și tu ești 'Normal', răspunzi obligatoriu: FRANEAZA\n"
                    "2. Dacă tu ești 'Ambulance', răspunzi obligatoriu: TRECE\n"
                    "3. Dacă ambele sunt 'Normal', mașina cu ID mai mic răspunde TRECE.\n\n"
                    "Răspunde DOAR cu un singur cuvânt: FRANEAZA sau TRECE.",
                ),
                ("human", "Analizează datele și ia decizia."),
            ]
        )
        self.chain = self.prompt | self.llm

    def receive_v2x_message(self, message):
        sender_id = message.get("agent_id")
        if sender_id and sender_id != self.agent_id:
            self.memory[sender_id] = message

    def calculate_ttc(self, target_x, target_y):
        if self.speed <= 0.5:
            return float("inf")
        distance = math.sqrt(
            (target_x - self.position_x) ** 2 + (target_y - self.position_y) ** 2
        )
        return distance / self.speed

    def decide_action(self, intersection_x, intersection_y):
        # Dacă deja așteptăm decizia AI-ului, punem frână ca să nu intrăm orbește în intersecție!
        if getattr(self, "waiting_for_ai", False):
            self._brake("Aștept decizie AI (Frânare preventivă)")
            return

<<<<<<< Updated upstream
        if dist_to_int > 250:
            self._recover_speed()
=======
        # ==========================================
        # 1. ACC (Păstrarea distanței față de mașina din față)
        # ==========================================
        for other_id, other_data in list(self.memory.items()):
            if other_data.get("vehicle_type") == "Infrastructure":
                continue

            ox, oy = other_data.get("position_x", 0), other_data.get("position_y", 0)
            oh = other_data.get("heading", "")

            if oh == self.heading:
                is_in_front = False
                if self.heading == "EAST" and ox > self.position_x and abs(oy - self.position_y) < 20: is_in_front = True
                elif self.heading == "WEST" and ox < self.position_x and abs(oy - self.position_y) < 20: is_in_front = True
                elif self.heading == "SOUTH" and oy > self.position_y and abs(ox - self.position_x) < 20: is_in_front = True
                elif self.heading == "NORTH" and oy < self.position_y and abs(ox - self.position_x) < 20: is_in_front = True

                if is_in_front:
                    dist_to_front = math.sqrt((ox - self.position_x)**2 + (oy - self.position_y)**2)
                    if dist_to_front < 80.0:  # 80px distanță de siguranță
                        self._brake(f"ACC: Frânez pentru {other_id}")
                        return 

        # ==========================================
        # 2. V2I (Semaforul)
        # ==========================================
        distance_to_center = math.sqrt((intersection_x - self.position_x)**2 + (intersection_y - self.position_y)**2)
        semafor_data = self.memory.get("Semafor_Centru")
        
        if semafor_data and self.vehicle_type != "Ambulance":
            culoare_axa_mea = "GREEN"
            if self.heading in ["NORTH", "SOUTH"]: culoare_axa_mea = semafor_data.get("state_NS", "GREEN")
            elif self.heading in ["EAST", "WEST"]: culoare_axa_mea = semafor_data.get("state_EW", "GREEN")
                
            if culoare_axa_mea == "RED" and distance_to_center < 150.0:
                self._brake("V2I: Opresc la Semafor ROȘU")
                return 

        # ==========================================
        # 3. V2V (Negociere Intersecție)
        # ==========================================
        # Dacă suntem departe de intersecție, nu ne stresăm încă
        if distance_to_center > 200.0:
            self.current_state = "CRUISE"
>>>>>>> Stashed changes
            return

        my_ttc = self.calculate_ttc(intersection_x, intersection_y)
        
        for other_id, other_data in list(self.memory.items()):
<<<<<<< Updated upstream
            # --- REPARAȚIE: Ignorăm mașinile care au trecut deja de centru ---
            ox, oy = other_data["position_x"], other_data["position_y"]
            oh = other_data.get("heading", "")

            past = False
            if oh == "SOUTH" and oy > intersection_y + 50:
                past = True
            if oh == "NORTH" and oy < intersection_y - 50:
                past = True
            if oh == "EAST" and ox > intersection_x + 50:
                past = True
            if oh == "WEST" and ox < intersection_x - 50:
                past = True

            if past:
                continue  # Această mașină a trecut, nu ne mai temem de ea
            # -------------------------------------------------------------

            other_speed = other_data["speed"]
            other_dist = math.sqrt(
                (intersection_x - ox) ** 2 + (intersection_y - oy) ** 2
            )
            other_ttc = other_dist / other_speed if other_speed > 5.0 else 999

            if abs(my_ttc - other_ttc) < 6.0:
                conflict_detected = True
                self._negotiate_ai(other_id, other_data)
                return

        if not conflict_detected:
            self._recover_speed()
=======
            if other_data.get("vehicle_type") == "Infrastructure":
                continue
            
            # REPARAȚIA MAGICĂ: Nu negociem intersecția cu mașini de pe același sens!
            if other_data.get("heading", "") == self.heading:
                continue

            ox, oy = other_data.get("position_x", 0), other_data.get("position_y", 0)
            other_dist = math.sqrt((intersection_x - ox)**2 + (intersection_y - oy)**2)
            other_speed = other_data.get("speed", 0)
            other_ttc = other_dist / other_speed if other_speed > 0 else float("inf")

            # Dacă există risc de coliziune (ajungem în același timp)
            if abs(my_ttc - other_ttc) < 3.0:
                if self.driving_style == "Cautious" and other_data.get("driving_style") == "Aggressive":
                    self._brake("Defensiv: Cedez agresivului")
                    return
                if self.vehicle_type == "Normal" and other_data.get("vehicle_type") == "Ambulance":
                    self._brake("Prioritate ambulanță")
                    return
                
                # Doar ca ultimă soluție chemăm AI-ul Groq
                self._negotiate_ai(other_id, other_data)
                return

        self.current_state = "CRUISE"
        
        # RECUPERAREA VITEZEI: Dacă viteza e mai mică decât cea dorită, accelerăm treptat
        if hasattr(self, 'desired_speed') and self.speed < self.desired_speed:
            self.speed = min(self.desired_speed, self.speed + 10.2)
            # (Opțional) Poți lăsa acest print ca să vezi în consolă cum accelerează la loc
            print(f"[{self.agent_id}]: Drum liber. Accelerez... Viteză: {self.speed:.2f}")
>>>>>>> Stashed changes

    def _brake(self, reason):
        self.current_state = "BRAKING"
        self.speed = max(0, self.speed - 2.0)  # Decelerație fermă
        print(f"[{self.agent_id}]: {reason}. Viteză: {self.speed:.1f}")

    def _recover_speed(self):
        self.current_state = "CRUISE"
        if self.speed < self.desired_speed:
            # Crește valoarea de la 0.5 la 2.0 sau 3.0 pentru accelerare sportivă
            self.speed = min(self.desired_speed, self.speed + 2.5)

    def _negotiate_ai(self, other_id, other_data):
        current_time = time.time()

        # 1. Dacă deja așteptăm un răspuns de la AI, nu mai facem alt apel!
        if getattr(self, "waiting_for_ai", False):
            # În timp ce așteptăm, aplicăm o frână ușoară de siguranță (Fail-safe)
            self._brake("Aștept decizie AI...")
            return

        # 2. Cooldown pentru a nu bombarda API-ul
        if (
            self.last_ai_decision
            and (current_time - self.last_ai_call_time) < self.decision_cooldown
        ):
            if "FRANEAZA" in self.last_ai_decision:
                self._brake("Decizie AI (cached): cedez")
            else:
                self._recover_speed()
            return

        # 3. Lansăm apelul AI într-un THREAD SEPARAT ca să nu blocheze simularea
        self.waiting_at = current_time
        self.waiting_for_ai = True

        # Creăm o funcție internă care va rula în fundal
        def ai_thread_task():
            try:
                print(f"[{self.agent_id}] Fir de execuție separat: Apelăm Groq...")
                response = self.chain.invoke(
                    {
                        "my_id": self.agent_id,
                        "my_type": self.vehicle_type,
                        "other_id": other_id,
                        "other_type": other_data.get("vehicle_type"),
                    }
                )

                self.last_ai_decision = response.content.upper()
                self.last_ai_call_time = time.time()
                print(f"[{self.agent_id}] AI-ul a răspuns: {self.last_ai_decision}")
            except Exception as e:
                print(f"Eroare AI: {e}")
                self.last_ai_decision = "FRANEAZA"  # Fail-safe la eroare
            finally:
                self.waiting_for_ai = False  # Eliberăm flag-ul

        # Pornim thread-ul și plecăm mai departe (nu așteptăm după el!)
        threading.Thread(target=ai_thread_task, daemon=True).start()

    def update_position(self, delta_time):
        if self.speed <= 0:
            return
        t_x, t_y = self.target_destination
        angle = math.atan2(t_y - self.position_y, t_x - self.position_x)
        dist = self.speed * delta_time
        self.position_x += dist * math.cos(angle)
        self.position_y += dist * math.sin(angle)

    def has_decided_to_brake(self):
        return self.current_state == "BRAKING"

    def get_emergency_status(self):
        return {
            "agent_id": self.agent_id,
            "position_x": round(self.position_x, 2),
            "position_y": round(self.position_y, 2),
            "speed": round(self.speed, 2),
            "vehicle_type": self.vehicle_type,
            "driving_style": self.driving_style,
            "intent": self.current_state,
            "heading": self.heading,
        }
