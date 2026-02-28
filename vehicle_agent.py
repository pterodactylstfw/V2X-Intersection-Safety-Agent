import math
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# Încărcăm variabilele de mediu (cheia ta GROQ_API_KEY din fișierul .env)
load_dotenv()


class VehicleAgent:
    def __init__(
        self,
        agent_id,
        start_x,
        start_y,
        speed,
        vehicle_type="Normal",
        driving_style="Cautious",
    ):
        """
        Inițializează un nou agent autonom (o mașină) cu capabilități LLM și stil de condus.
        """
        self.agent_id = agent_id
        self.position_x = start_x
        self.position_y = start_y
        self.speed = speed
        self.vehicle_type = vehicle_type  # 'Normal' sau 'Ambulance'
        self.driving_style = driving_style  # 'Cautious' sau 'Aggressive'

        self.current_state = "CRUISE"
        self.memory = {}

        # --- INIȚIALIZARE CREIER AI (LangChain + Groq) ---
        self.llm = ChatGroq(temperature=0, model_name="llama-3.1-8b-instant")

        # Îi dăm instrucțiuni stricte agentului adaptate la noile denumiri:
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
                    "3. Dacă ambele sunt 'Normal', mașina cu ID mai mic răspunde TRECE, iar cea cu ID mai mare răspunde FRANEAZA.\n\n"
                    "Răspunde DOAR cu un singur cuvânt: FRANEAZA sau TRECE.",
                ),
                ("human", "Analizează datele și ia decizia."),
            ]
        )

        self.chain = self.prompt | self.llm

    def receive_v2x_message(self, message):
        """
        Primește un mesaj de pe canalul V2X (JSON) și își actualizează memoria.
        """
        sender_id = message.get("agent_id")

        if sender_id is not None and sender_id != self.agent_id:
            self.memory[sender_id] = message

    def calculate_ttc(self, target_x, target_y):
        """
        Calculează Timpul-Până-La-Coliziune (Time-To-Collision) față de intersecție.
        """
        if self.speed <= 0:
            return float("inf")

        distance = math.sqrt(
            (target_x - self.position_x) ** 2 + (target_y - self.position_y) ** 2
        )
        return distance / self.speed

    def decide_action(self, intersection_x, intersection_y):
        """
        Analizează memoria și decide dacă mașina trebuie să frâneze sau să continue.
        """
        my_ttc = self.calculate_ttc(intersection_x, intersection_y)
        self.current_state = "CRUISE"

        for other_id, other_data in self.memory.items():
            other_dist = math.sqrt(
                (intersection_x - other_data["position_x"]) ** 2
                + (intersection_y - other_data["position_y"]) ** 2
            )
            other_speed = other_data["speed"]

            if other_speed > 0:
                other_ttc = other_dist / other_speed
            else:
                other_ttc = float("inf")

            # 3. LOGICA DE COLIZIUNE: Fereastră de 20 de secunde (deoarece vitezele sunt mici, ex: 3 px/cadru)
            if abs(my_ttc - other_ttc) < 20.0:
                print(f"\n[!] CONFLICT DETECTAT cu mașina ID {other_id}!")

                other_type = other_data.get("vehicle_type", "Normal")
                other_style = other_data.get("driving_style", "Cautious")

                # --- REGULA SUPREMĂ 1: COMPORTAMENT AGRESIV ---
                # Dacă adversarul e Agresiv și tu ești Cautious, frânezi indiferent de cine are prioritate!
                if self.driving_style == "Cautious" and other_style == "Aggressive":
                    self.current_state = "BRAKING"
                    self.speed = max(0, self.speed - 0.5)  # Frânare treptată (pixeli)
                    print(
                        f"[{self.agent_id} LOGIC]: FRÂNEZ DE URGENȚĂ! Șofer agresiv detectat (ID {other_id}). Noua viteză: {self.speed:.2f}"
                    )
                    return

                # --- REGULA 2: AMBULANȚA ---
                if self.vehicle_type == "Normal" and other_type == "Ambulance":
                    self.current_state = "BRAKING"
                    self.speed = max(0, self.speed - 0.5)
                    print(
                        f"[{self.agent_id} LOGIC]: FRÂNEZ. Cedez ambulanței (ID {other_id}). Noua viteză: {self.speed:.2f}"
                    )
                    return
                elif self.vehicle_type == "Ambulance" and other_type == "Normal":
                    self.current_state = "CRUISE"
                    print(
                        f"[{self.agent_id} LOGIC]: TREC. Sunt vehicul de urgență. Viteza rămâne: {self.speed:.2f}"
                    )
                    return

                # --- NEGOCIEREA AI (PENTRU DEADLOCK-URI SIMPLE) ---
                print(f"[{self.agent_id}] Se inițiază negocierea AI pentru deadlock...")
                try:
                    ai_response = self.chain.invoke(
                        {
                            "my_id": self.agent_id,
                            "my_type": self.vehicle_type,
                            "other_id": other_id,
                            "other_type": other_type,
                        }
                    )
                    decizie = ai_response.content.strip().upper()

                    if "FRANEAZA" in decizie:
                        self.current_state = "BRAKING"
                        self.speed = max(0, self.speed - 0.5)
                        print(
                            f"[{self.agent_id} AI DECISION]: FRÂNEZ. Cedez trecerea mașinii {other_id}. Noua viteză: {self.speed:.2f}"
                        )
                    else:
                        self.current_state = "CRUISE"
                        print(
                            f"[{self.agent_id} AI DECISION]: TREC. Am prioritate în fața mașinii {other_id}. Viteza rămâne: {self.speed:.2f}"
                        )
                except Exception as e:
                    print(
                        f"[{self.agent_id} EROARE AI]: Nu m-am putut conecta la Groq. Aplic fail-safe (frânez)."
                    )
                    self.current_state = "BRAKING"
                    self.speed = max(0, self.speed - 0.5)

                return

        print(
            f"[OK] Drum liber. Trec în starea: {self.current_state}. Viteza: {self.speed:.2f}"
        )

    def update_position(self, delta_time, target_x, target_y):
        """
        Mută fizic mașina pe hartă spre o țintă, în funcție de viteza ei.
        Această funcție va fi folosită DOAR dacă mașina frânează (suprascrie JSON-ul).
        """
        if self.speed <= 0:
            return

        distance_to_move = self.speed * delta_time
        dx = target_x - self.position_x
        dy = target_y - self.position_y

        if abs(dx) < 0.1 and abs(dy) < 0.1:
            self.speed = 0
            return

        angle = math.atan2(dy, dx)

        self.position_x += distance_to_move * math.cos(angle)
        self.position_y += distance_to_move * math.sin(angle)

        self.position_x = round(self.position_x, 2)
        self.position_y = round(self.position_y, 2)


# --- ZONĂ DE TESTARE LOCALĂ ---
if __name__ == "__main__":
    # Testăm exact structura din json-ul vostru
    masina_mea = VehicleAgent(
        agent_id="Masina_A",
        start_x=150.5,
        start_y=400.0,
        speed=3.2,
        vehicle_type="Normal",
        driving_style="Cautious",
    )

    masaj_ambulanță = {
        "agent_id": "Ambulanta_B",
        "vehicle_type": "Ambulance",
        "position_x": 400.0,
        "position_y": 200.0,
        "speed": 5.8,
        "driving_style": "Aggressive",
    }

    masina_mea.receive_v2x_message(masaj_ambulanță)

    print("--- Test: Șofer Cautious vs Șofer Aggressive ---")
    masina_mea.decide_action(intersection_x=400, intersection_y=400)


def has_decided_to_brake(self):
    """
    Returnează True dacă AI-ul a decis că trebuie să frâneze.
    Folosit de Network pentru a ști când să ignore coordonatele din JSON.
    """
    return self.current_state == "BRAKING"


def get_emergency_status(self):
    """
    Returnează starea curentă calculată de AI (poziție și viteză).
    Aceasta va suprascrie datele din scenariu.json.
    """
    return {
        "agent_id": self.agent_id,
        "position_x": self.position_x,
        "position_y": self.position_y,
        "speed": self.speed,
        "current_state": self.current_state,
        "vehicle_type": self.vehicle_type,
        "driving_style": self.driving_style,
    }
