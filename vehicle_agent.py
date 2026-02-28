import math
import os
import time
import threading
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

import networkx as nx
from map_config import nodes, edges

load_dotenv()


class VehicleAgent:
    def __init__(
        self,
        agent_id,
        start_node,  # NOU: Folosim nume de noduri (ex: "W_START")
        target_node,  # NOU: Folosim nume de noduri (ex: "E_END")
        desired_speed,
        vehicle_type="Normal",
        driving_style="Cautious",
    ):
        self.agent_id = agent_id
        self.desired_speed = desired_speed
        self.speed = desired_speed
        self.vehicle_type = vehicle_type
        self.driving_style = driving_style
        self.current_state = "CRUISE"
        self.turn_intent = "GO_STRAIGHT"  # NOU: Pentru semnalizare/viraje
        self.memory = {}
        self.last_ai_decision = None
        self.last_ai_call_time = 0
        self.decision_cooldown = 1.0
        self.waiting_for_ai = False
        self.visual_angle = 0.0

        # --- NOU: 1. GENERAREA RUTEI (Dijkstra) ---
        self.graph = nx.DiGraph()
        for start, end, cost in edges:
            self.graph.add_edge(start, end, weight=cost)

        try:
            self.route = nx.shortest_path(
                self.graph, source=start_node, target=target_node, weight="weight"
            )
        except nx.NetworkXNoPath:
            print(
                f"[{self.agent_id}] EROARE: Nu există drum de la {start_node} la {target_node}!"
            )
            self.route = [start_node]

        self.current_node_index = 0

        # Setăm poziția inițială exact pe primul nod
        start_coords = nodes[self.route[0]]
        self.position_x = start_coords[0]
        self.position_y = start_coords[1]

        self.heading = "EAST"  # Default de siguranță
        if len(self.route) > 1:
            next_coords = nodes[self.route[1]]
            angle = math.atan2(
                next_coords[1] - self.position_y, next_coords[0] - self.position_x
            )
            deg = math.degrees(angle)
            if -45 <= deg <= 45:
                self.heading = "EAST"
            elif 45 < deg <= 135:
                self.heading = "SOUTH"
            elif -135 <= deg < -45:
                self.heading = "NORTH"
            else:
                self.heading = "WEST"

        # Setăm direcția inițială (Heading)
        self._update_heading_and_turn()

        self.llm = ChatGroq(temperature=0, model_name="llama-3.1-8b-instant")
        # --- PROMPT AI ÎMBUNĂTĂȚIT (Prioritate de Dreapta) ---
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Ești creierul autonom al unei mașini. Rolul tău este să eviți accidentele aplicând Prioritatea de Dreapta.\n"
                    "Reguli de orientare (tu decizi strict pentru tine):\n"
                    "- Dacă tu mergi spre NORTH și celălalt merge spre WEST, el vine din dreapta ta -> FRANEAZA.\n"
                    "- Dacă tu mergi spre SOUTH și celălalt merge spre EAST, el vine din dreapta ta -> FRANEAZA.\n"
                    "- Dacă tu mergi spre EAST și celălalt merge spre NORTH, el vine din dreapta ta -> FRANEAZA.\n"
                    "- Dacă tu mergi spre WEST și celălalt merge spre SOUTH, el vine din dreapta ta -> FRANEAZA.\n"
                    "În caz contrar, dacă el nu vine din dreapta ta, tu ai prioritate -> TRECE.\n"
                    "Ambulanțele au prioritate absolută indiferent de direcție.\n\n"
                    "Răspunde DOAR cu un singur cuvânt: FRANEAZA sau TRECE.",
                ),
                (
                    "human",
                    "Eu sunt {my_id} (Tip: {my_type}) și merg spre {my_heading}. "
                    "Celălalt este {other_id} (Tip: {other_type}) și merge spre {other_heading}. Ce decizie iei pentru MINE?",
                ),
            ]
        )
        self.chain = self.prompt | self.llm

    # ==========================================
    # FUNCȚIILE TALE VECHI (RESTAURATE)
    # ==========================================
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
            if oh == self.heading:
                ox = other_data.get("position_x", 0)
                oy = other_data.get("position_y", 0)

                is_in_front = False
                if (
                    self.heading == "EAST"
                    and ox > self.position_x
                    and abs(oy - self.position_y) < 20
                ):
                    is_in_front = True
                elif (
                    self.heading == "WEST"
                    and ox < self.position_x
                    and abs(oy - self.position_y) < 20
                ):
                    is_in_front = True
                elif (
                    self.heading == "SOUTH"
                    and oy > self.position_y
                    and abs(ox - self.position_x) < 20
                ):
                    is_in_front = True
                elif (
                    self.heading == "NORTH"
                    and oy < self.position_y
                    and abs(ox - self.position_x) < 20
                ):
                    is_in_front = True

                if is_in_front:
                    dist_to_front = math.sqrt(
                        (ox - self.position_x) ** 2 + (oy - self.position_y) ** 2
                    )
                    if dist_to_front < 90.0:
                        self._brake(f"ACC: Frânez ca să nu lovesc {other_id}")
                        return

        # 1. VERIFICARE: Am trecut complet de intersecție?
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

        # ==========================================
        # 2. V2I (SEMAFOR + GLOSA) UNIFICAT
        # ==========================================
        dist_to_int = math.sqrt(
            (int_x - self.position_x) ** 2 + (int_y - self.position_y) ** 2
        )
        semafor_data = self.memory.get("Semafor_Centru")

        is_light_here = False
        if semafor_data:
            light_x = semafor_data.get("position_x", 400)
            if abs(int_x - light_x) < 50:
                is_light_here = True

        in_intersection = dist_to_int <= 60.0

        if (
            semafor_data
            and is_light_here
            and self.vehicle_type != "Ambulance"
            and not in_intersection
        ):
            culoare_axa_mea = "GREEN"
            if self.heading in ["NORTH", "SOUTH"]:
                culoare_axa_mea = semafor_data.get("state_NS", "GREEN")
            elif self.heading in ["EAST", "WEST"]:
                culoare_axa_mea = semafor_data.get("state_EW", "GREEN")

            time_to_change = semafor_data.get("time_to_change", 5.0)

            if culoare_axa_mea == "YELLOW_BLINKING":
                pass

            elif culoare_axa_mea == "RED":
                if dist_to_int < 120.0:
                    self._brake("V2I: Opresc la Semafor ROȘU")
                    return
                elif dist_to_int < 400.0:
                    cadre_ramase = time_to_change * 20
                    if cadre_ramase > 0:
                        viteza_optima = dist_to_int / cadre_ramase
                        viteza_optima = min(self.desired_speed, max(1.0, viteza_optima))
                        if self.speed > viteza_optima:
                            self.speed = max(viteza_optima, self.speed - 0.2)
                            return

            elif culoare_axa_mea == "YELLOW":
                if dist_to_int > 120.0 or (dist_to_int > 60.0 and self.speed < 1.0):
                    self._brake("V2I: Opresc la Semafor GALBEN")
                    return

            elif culoare_axa_mea == "GREEN":
                if time_to_change < 1.0 and dist_to_int > 120.0:
                    self._brake("V2I GLOSA: Nu am timp să prind verdele!")
                    return

        # ==========================================
        # 3. PRIORITATE ABSOLUTĂ AMBULANȚĂ (V2V)
        # ==========================================
        if self.vehicle_type != "Ambulance":
            for other_id, other_data in list(self.memory.items()):
                if other_data.get("vehicle_type") == "Ambulance":
                    ox = other_data.get("position_x", 0)
                    oy = other_data.get("position_y", 0)
                    oh = other_data.get("heading", "")
                    o_speed = other_data.get("speed", 0)

                    # Calculăm distanța ambulanței față de intersecția MEA țintă
                    o_dist_to_int = math.sqrt((int_x - ox) ** 2 + (int_y - oy) ** 2)

                    # Verificăm dacă ambulanța a trecut DEJA de intersecție
                    amb_past = False
                    if oh == "SOUTH" and oy > int_y + 40:
                        amb_past = True
                    if oh == "NORTH" and oy < int_y - 40:
                        amb_past = True
                    if oh == "EAST" and ox > int_x + 40:
                        amb_past = True
                    if oh == "WEST" and ox < int_x - 40:
                        amb_past = True

                    # Dacă ambulanța se apropie de aceeași intersecție ca mine (e la sub 400px)
                    if not amb_past and o_dist_to_int < 400.0:
                        # Dacă eu sunt destul de aproape de intersecție (sub 150px)
                        # FRÂNEZ PÂNĂ LA 0, chiar dacă sunt fix pe linia de stop!
                        if dist_to_int < 150.0:
                            self._brake("Cedez trecerea Ambulanței!")
                            return
                        # Dacă sunt mai departe, doar încetinesc preventiv
                        else:
                            self.speed = max(1.0, self.speed - 0.2)
                            return

        # ==========================================
        # 4. NEGOCIERE V2V / AI (Pentru intersecții nesemaforizate sau avarie)
        # ==========================================
        if dist_to_int > 350.0:
            self._recover_speed()
            return

        conflict_detected = False

        for other_id, other_data in list(self.memory.items()):
            if other_data.get("vehicle_type") == "Infrastructure":
                continue
            if other_data.get("heading") == self.heading:
                continue

            ox, oy = other_data["position_x"], other_data["position_y"]
            oh = other_data.get("heading", "")

            # Verificăm dacă celălalt a trecut deja de centrul intersecției
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

            o_dist = math.sqrt((int_x - ox) ** 2 + (int_y - oy) ** 2)

            # FIXUL: Folosim DISTANȚĂ pură. Cât timp suntem amândoi în raza de 350px,
            # nu mai anulăm conflictul, forțând AI-ul să ia o decizie stabilă!
            if o_dist < 350.0:
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
        self.speed = max(0, self.speed - 4.5)

    def _recover_speed(self):
        self.current_state = "CRUISE"
        if self.speed < self.desired_speed:
            self.speed = min(self.desired_speed, self.speed + 2.0)

    def _negotiate_ai(self, other_id, other_data):
        if self.waiting_for_ai:
            # FIX: Cât timp AI-ul se gândește în fundal (aprox 1 secundă),
            # mașina ia piciorul de pe accelerație și pune frână preventiv (Conducere Defensivă)
            self.speed = max(0, self.speed - 2.0)
            return

        current_time = time.time()
        if self.last_ai_decision and (
            current_time - self.last_ai_call_time < self.decision_cooldown
        ):
            if "FRANEAZA" in self.last_ai_decision:
                # Frânăm decisiv pentru a lăsa mașina din dreapta să treacă
                self.speed = max(0, self.speed - 5.0)
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
                        "my_heading": self.heading,
                        "other_id": other_id,
                        "other_type": other_data.get("vehicle_type", "Normal"),
                        "other_heading": other_data.get("heading", "UNKNOWN"),
                    }
                )
                self.last_ai_decision = res.content.upper()
                print(
                    f"[AI Prioritate] {self.agent_id}({self.heading}) a vazut {other_id}({other_data.get('heading')}) -> A decis: {self.last_ai_decision}"
                )
                self.last_ai_call_time = time.time()
            except Exception as e:
                print(f"[AI EROARE] {self.agent_id} -> Frână de urgență!")
                self.last_ai_decision = "FRANEAZA"
            finally:
                self.waiting_for_ai = False

        threading.Thread(target=ai_task, daemon=True).start()

    # ==========================================
    # FUNCȚIILE NOI DE MIȘCARE PE GRAF
    # ==========================================
    def update_position(self, dt):
        if self.speed <= 0 or self.current_node_index >= len(self.route) - 1:
            return

        # 1. Luăm coordonatele URMĂTORULUI nod țintă
        next_node_name = self.route[self.current_node_index + 1]
        tx, ty = nodes[next_node_name]

        # 2. Calculăm distanța până la țintă
        dist = math.sqrt((tx - self.position_x) ** 2 + (ty - self.position_y) ** 2)

        # 3. Verificăm dacă am ajuns la nod (logica existentă)
        if dist < 5.0:
            self.current_node_index += 1
            if self.current_node_index >= len(self.route) - 1:
                return

            # Recalculăm intenția de viraj (pentru semnalizări)
            self._update_heading_and_turn()

            # Actualizăm ținta către nodul următor
            next_node_name = self.route[self.current_node_index + 1]
            tx, ty = nodes[next_node_name]

        # 4. CALCULĂM UNGHIUL EXACT DE DEPLASARE (Rotația Continuă)
        # math.atan2 returnează unghiul în radiani (-pi la pi)
        angle_rad = math.atan2(ty - self.position_y, tx - self.position_x)

        # Convertim în grade (necesar pentru Pygame)
        self.visual_angle = math.degrees(angle_rad)

        # 5. Mișcăm mașina (logica existentă)
        self.position_x += self.speed * dt * math.cos(angle_rad)
        self.position_y += self.speed * dt * math.sin(angle_rad)

        # 6. (Opțional - Păstrăm și heading discret pentru compatibilitate logica AI)
        deg = self.visual_angle
        if -45 <= deg <= 45:
            self.heading = "EAST"
        elif 45 < deg <= 135:
            self.heading = "SOUTH"
        elif -135 <= deg < -45:
            self.heading = "NORTH"
        else:
            self.heading = "WEST"

    def _update_heading_and_turn(self):
        if (
            self.current_node_index > 0
            and self.current_node_index < len(self.route) - 1
        ):
            p_prev = nodes[self.route[self.current_node_index - 1]]
            p_curr = nodes[self.route[self.current_node_index]]
            p_next = nodes[self.route[self.current_node_index + 1]]

            angle1 = math.atan2(p_curr[1] - p_prev[1], p_curr[0] - p_prev[0])
            angle2 = math.atan2(p_next[1] - p_curr[1], p_next[0] - p_curr[0])
            diff = math.degrees(angle2 - angle1)

            while diff <= -180:
                diff += 360
            while diff > 180:
                diff -= 360

            if -45 < diff < 45:
                self.turn_intent = "GO_STRAIGHT"
            elif diff <= -45:
                self.turn_intent = "TURN_LEFT"
            elif diff >= 45:
                self.turn_intent = "TURN_RIGHT"
        else:
            self.turn_intent = "GO_STRAIGHT"

    def get_emergency_status(self):
        return {
            "agent_id": self.agent_id,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "speed": self.speed,
            "vehicle_type": self.vehicle_type,
            # NOU: Trimitem unghiul vizual continuu
            "visual_angle": self.visual_angle,
            "intent": (
                self.current_state
                if self.current_state != "CRUISE"
                else self.turn_intent
            ),
            "heading": self.heading,
        }

    def has_decided_to_brake(self):
        return self.current_state == "BRAKING"
