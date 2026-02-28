import math
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# Încărcăm variabilele de mediu (cheia ta GROQ_API_KEY din fișierul .env)
load_dotenv()


class VehicleAgent:

    def __init__(self, vehicle_id, start_x, start_y, speed, vehicle_type="normal"):
        """
        Inițializează un nou agent autonom (o mașină) cu capabilități LLM.
        """
        self.id = vehicle_id
        self.x = start_x
        self.y = start_y
        self.speed = speed
        self.type = vehicle_type  # Poate fi 'normal' sau 'ambulance'

        self.state = "CRUISE"
        self.memory = {}

        # --- INIȚIALIZARE CREIER AI (LangChain + Groq) ---
        # Folosim llama3 pentru că este gratuit pe Groq și extrem de rapid
        self.llm = ChatGroq(temperature=0, model_name="llama-3.1-8b-instant")

        # Îi dăm instrucțiuni stricte agentului:
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Ești modulul de decizie AI pentru o mașină autonomă (ID: {my_id}, Tip: {my_type}). "
                    "Negociezi prioritatea într-o intersecție. "
                    "REGULI: 1. Ambulanța are mereu prioritate. 2. Dacă ambele sunt mașini normale, mașina cu ID-ul mai mic trece prima pentru a evita blocajele. "
                    "Răspunde STRICT cu un singur cuvânt: 'FRANEAZA' (dacă cedezi trecerea) sau 'TRECE' (dacă ai prioritate).",
                ),
                (
                    "human",
                    "Mașina adversă are ID: {other_id} și Tip: {other_type}. Ce decizie iei?",
                ),
            ]
        )

        # Creăm lanțul de gândire
        self.chain = self.prompt | self.llm

    def receive_v2x_message(self, message):
        """
        Primește un mesaj de pe canalul V2X și își actualizează memoria.
        Formatul așteptat al mesajului (dicționar): {'id': 2, 'x': 100, 'y': 200, 'speed': 15, 'type': 'normal'}
        """
        sender_id = message.get("id")

        # Nu vrem să ne memorăm pe noi înșine
        if sender_id is not None and sender_id != self.id:
            self.memory[sender_id] = message
            # Aici am putea adăuga o logică de a șterge mașinile foarte vechi din memorie

    def calculate_ttc(self, target_x, target_y):
        """
        Calculează Timpul-Până-La-Coliziune (Time-To-Collision) față de un punct (ex: centrul intersecției).
        Returnează timpul în secunde.
        """
        # Dacă stăm pe loc, nu vom ajunge niciodată la țintă (evităm împărțirea la zero)
        if self.speed <= 0:
            return float("inf")  # 'inf' înseamnă infinit

        # Calculăm distanța Euclidiană
        distance = math.sqrt((target_x - self.x) ** 2 + (target_y - self.y) ** 2)

        # TTC = distanța / viteză
        ttc = distance / self.speed

        return ttc

    def decide_action(self, intersection_x, intersection_y):
        """
        Analizează memoria și decide dacă mașina trebuie să frâneze sau să continue.
        """
        # 1. Calculăm timpul nostru până la intersecție
        my_ttc = self.calculate_ttc(intersection_x, intersection_y)

        # Presupunem că e sigur să mergem, până găsim un pericol
        self.state = "CRUISE"

        # 2. Ne uităm la fiecare mașină din memorie
        for other_id, other_data in self.memory.items():

            # Calculăm distanța celeilalte mașini până la centrul intersecției
            other_distance = math.sqrt(
                (intersection_x - other_data["x"]) ** 2
                + (intersection_y - other_data["y"]) ** 2
            )
            other_speed = other_data["speed"]

            # Calculăm TTC-ul celeilalte mașini
            if other_speed > 0:
                other_ttc = other_distance / other_speed
            else:
                other_ttc = float(
                    "inf"
                )  # Dacă cealaltă mașină stă pe loc, nu e un pericol imediat

            # 3. LOGICA DE COLIZIUNE: Dacă ajungem în intersecție cam în același timp
            # Verificăm dacă diferența de timp e mai mică de 2 secunde
            if abs(my_ttc - other_ttc) < 2.0:
                print(
                    f"\n[!] CONFLICT DETECTAT cu mașina ID {other_id}! Se inițiază negocierea AI..."
                )

                # Întrebăm LLM-ul cine are prioritate
                ai_response = self.chain.invoke(
                    {
                        "my_id": self.id,
                        "my_type": self.type,
                        "other_id": other_id,
                        "other_type": other_data.get("type", "normal"),
                    }
                )

                decizie = ai_response.content.strip().upper()

                if "FRANEAZA" in decizie:
                    self.state = "BRAKING"
                    self.speed = max(0, self.speed - 5)
                    print(
                        f"[{self.id} AI DECISION]: FRÂNEZ. Cedez trecerea mașinii {other_id}. Noua viteză: {self.speed}"
                    )
                else:
                    self.state = "CRUISE"
                    print(
                        f"[{self.id} AI DECISION]: TREC. Am prioritate în fața mașinii {other_id}. Viteza rămâne: {self.speed}"
                    )

                return

        # Dacă am ajuns aici, înseamnă că bucla a rulat și nu am găsit niciun risc
        print(f"[OK] Drum liber. Trec în starea: {self.state}. Viteza: {self.speed}")


# --- ZONĂ DE TESTARE LOCALĂ ---
# Codul de mai jos rulează doar dacă rulezi direct acest fișier,
# nu și dacă este importat în main.py
if __name__ == "__main__":
    # 1. Creăm mașina noastră (merge cu viteza 10, ajunge în 10 secunde)
    masina_mea = VehicleAgent(vehicle_id=1, start_x=0, start_y=50, speed=10)

    # 2. Simulăm mesajul V2X de la o ambulanță (merge cu 20, ajunge în 5 secunde)
    # Suntem safe, ea trece prima!
    masaj_ambulanță = {"id": 2, "x": 0, "y": 150, "speed": 20, "type": "ambulance"}
    masina_mea.receive_v2x_message(masaj_ambulanță)

    print("--- Test 1: Ambulanța e rapidă și trece mult înaintea noastră ---")
    masina_mea.decide_action(
        intersection_x=100, intersection_y=50
    )  # Coordonatele intersecției # Coordonatele intersecției

    # 3. Simulăm un mesaj V2X de la o altă mașină care are FIX același TTC ca noi (10 secunde)
    masaj_pericol = {"id": 3, "x": 100, "y": 150, "speed": 10, "type": "normal"}
    masina_mea.receive_v2x_message(masaj_pericol)

    print("\n--- Test 2: O mașină se apropie pe curs de coliziune ---")
    masina_mea.decide_action(intersection_x=100, intersection_y=50)
