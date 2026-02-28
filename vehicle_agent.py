import math
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# Încărcăm variabilele de mediu pentru cheia API Groq
load_dotenv()

class VehicleAgent:
    def __init__(self, agent_id, start_x, start_y, speed, vehicle_type="Normal", driving_style="Cautious", heading="NORTH"):
        """
        Inițializează un agent autonom cu memorie proprie și capabilități AI[cite: 7, 60, 61].
        """
        self.agent_id = agent_id
        self.position_x = start_x
        self.position_y = start_y
        self.speed = speed
        self.heading = heading
        self.vehicle_type = vehicle_type  # 'Normal' sau 'Ambulance' [cite: 12]
        self.driving_style = driving_style  # 'Cautious' sau 'Aggressive'

        self.current_state = "CRUISE"
        self.memory = {} # Memorie locală pentru percepția mesajelor V2X [cite: 7, 61]

        # --- INIȚIALIZARE CREIER AI (LangChain + Groq) [cite: 60] ---
        self.llm = ChatGroq(temperature=0, model_name="llama-3.1-8b-instant")

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "Ești un agent de trafic AI autonom. Decizi cine trece intersecția.\n"
                       "Mașina ta: ID {my_id}, tip {my_type}.\n"
                       "Mașina adversă: ID {other_id}, tip {other_type}.\n\n"
                       "REGULI STRICTE:\n"
                       "1. Dacă adversarul este 'Ambulance' și tu ești 'Normal', răspunzi obligatoriu: FRANEAZA\n"
                       "2. Dacă tu ești 'Ambulance', răspunzi obligatoriu: TRECE\n"
                       "3. Dacă ambele sunt 'Normal', mașina cu ID mai mic răspunde TRECE.\n\n"
                       "Răspunde DOAR cu un singur cuvânt: FRANEAZA sau TRECE."),
            ("human", "Analizează datele și ia decizia."),
        ])

        self.chain = self.prompt | self.llm

    def receive_v2x_message(self, message):
        """Actualizează memoria agentului cu datele primite de la ceilalți[cite: 7, 61]."""
        sender_id = message.get("agent_id")
        if sender_id and sender_id != self.agent_id:
            self.memory[sender_id] = message

    def calculate_ttc(self, target_x, target_y):
        """Calculează timpul estimat până la punctul de coliziune[cite: 11]."""
        if self.speed <= 0: return float("inf")
        distance = math.sqrt((target_x - self.position_x)**2 + (target_y - self.position_y)**2)
        return distance / self.speed

    def decide_action(self, intersection_x, intersection_y):
        """Evaluează riscul și ia o decizie autonomă de frânare[cite: 8, 11, 18]."""
        my_ttc = self.calculate_ttc(intersection_x, intersection_y)
        self.current_state = "CRUISE"

        for other_id, other_data in self.memory.items():
            other_dist = math.sqrt((intersection_x - other_data["position_x"])**2 + (intersection_y - other_data["position_y"])**2)
            other_speed = other_data["speed"]
            other_ttc = other_dist / other_speed if other_speed > 0 else float("inf")

            # Prag de siguranță: 5 secunde [cite: 11]
            if abs(my_ttc - other_ttc) < 5.0:
                print(f"\n[!] CONFLICT DETECTAT cu {other_id}!")
                
                # Prioritate: Șofer Agresiv sau Ambulanță [cite: 12]
                if self.driving_style == "Cautious" and other_data.get("driving_style") == "Aggressive":
                    self._brake("Defensiv: șofer agresiv")
                    return
                
                if self.vehicle_type == "Normal" and other_data.get("vehicle_type") == "Ambulance":
                    self._brake("Prioritate ambulanță")
                    return

                # Negociere prin LLM pentru cazuri complexe [cite: 60]
                self._negotiate_ai(other_id, other_data)
                return

    def _brake(self, reason):
        self.current_state = "BRAKING"
        self.speed = max(0, self.speed - 0.4)
        print(f"[{self.agent_id}]: {reason}. Viteză nouă: {self.speed:.2f}")

    def _negotiate_ai(self, other_id, other_data):
        try:
            response = self.chain.invoke({
                "my_id": self.agent_id, "my_type": self.vehicle_type,
                "other_id": other_id, "other_type": other_data.get("vehicle_type")
            })
            if "FRANEAZA" in response.content.upper():
                self._brake("Decizie AI: cedez")
            else:
                self.current_state = "CRUISE"
        except:
            self._brake("Fail-safe: eroare conexiune AI")

    def update_position(self, delta_time, target_x, target_y):
        """Actualizează coordonatele dacă AI-ul a preluat controlul manual[cite: 10]."""
        if self.speed <= 0: return
        dist = self.speed * delta_time
        angle = math.atan2(target_y - self.position_y, target_x - self.position_x)
        self.position_x += dist * math.cos(angle)
        self.position_y += dist * math.sin(angle)

    # --- FUNCȚII REPARATE (MUTATE ÎN INTERIORUL CLASEI) ---
    def has_decided_to_brake(self):
        """Verifică dacă mașina este în stare de frânare de urgență[cite: 18]."""
        return self.current_state == "BRAKING"

    def get_emergency_status(self):
        """Returnează datele calculate de AI pentru a suprascrie JSON-ul[cite: 11]."""
        return {
            "agent_id": self.agent_id,
            "position_x": round(self.position_x, 2),
            "position_y": round(self.position_y, 2),
            "speed": round(self.speed, 2),
            "vehicle_type": self.vehicle_type,
            "driving_style": self.driving_style,
            "intent": self.current_state,
            "heading": self.heading
        }