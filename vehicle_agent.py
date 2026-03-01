import math
import os
import time
import threading
import json
import hashlib
import requests

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

import networkx as nx
from map_config import nodes, edges

load_dotenv()


SECRET_KEY = os.getenv("HASH_SECRET_KEY", "default-fallback-key")


def sign_data(data):
    """Generează o amprentă digitală unică pentru pachetul de date."""
    clean_data = {k: v for k, v in data.items() if k != "signature"}
    payload = json.dumps(clean_data, sort_keys=True) + SECRET_KEY
    # algoritmul SHA-256
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class VehicleAgent:
    def __init__(
        self,
        agent_id,
        start_node, 
        target_node, 
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
        self.turn_intent = "GO_STRAIGHT" 
        self.memory = {}
        self.last_ai_decision = None
        self.last_ai_call_time = 0
        self.decision_cooldown = 1.0
        self.waiting_for_ai = False
        self.visual_angle = 0.0
        self.target_int = (0, 0) 
        self.is_crashed = False

        self.target_lane_offset = 0.0
        self.current_lane_offset = 0.0

        # GENERAREA RUTEI 
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

        start_coords = nodes[self.route[0]]
        self.base_x = start_coords[0]
        self.base_y = start_coords[1]

        self.position_x = self.base_x
        self.position_y = self.base_y

        self.heading = "EAST"
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

        self._update_heading_and_turn()

        self.llm = ChatGroq(temperature=0, model_name="llama-3.1-8b-instant")
        # PROMPT AI ÎMBUNĂTĂȚIT (Prioritate de Dreapta)
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

    def receive_v2x_message(self, message):
        sender_id = message.get("agent_id")
        if not sender_id or sender_id == self.agent_id:
            return

        if message.get("vehicle_type") == "Animal":
            self.memory[sender_id] = message
            return

        # SCUT DE SECURITATE V2X (3 Niveluri)
        # NIVEL 1: Sanity Checks (Prevenim crash-uri de la date corupte)
        try:
            x = float(message.get("position_x", 0))
            y = float(message.get("position_y", 0))
            speed = float(message.get("speed", 0))
        except (ValueError, TypeError):
            print(f"[{self.agent_id}] ❌ PACHET CORUPT respins de la {sender_id}!")
            return

        # NIVEL 2: Heartbeat & Anti-Ghosting (Prevenim mașinile blocate)=
        msg_time = message.get(
            "timestamp", time.time()
        )  # Folosim timpul curent ca fallback pentru JSON-urile vechi
        if time.time() - msg_time > 2.0:
            return  # Ignorăm mașina fantomă

        # NIVEL 3: Autenticitate (Prevenim Hackerii / Spoofing-ul)
        received_sig = message.get("signature", "")
        expected_sig = sign_data(message)

        if received_sig != expected_sig:
            print(
                f"[{self.agent_id}] ATAC CIBERNETIC DETECTAT! Semnătură falsă de la {sender_id}!"
            )
            return  

        self.memory[sender_id] = message

    def decide_action(self, int_x, int_y, ai_global_enabled=True):
        self.target_int = (int_x, int_y) 

        if self.is_crashed:
            self.speed = 0
            self.current_state = "CRASHED"
            return

        if not ai_global_enabled:
            self._recover_speed()
            self.last_ai_decision = None
            return

        # 0. URGENȚĂ ABSOLUTĂ: Evitare Animale
        for other_id, other_data in list(self.memory.items()):
            if other_data.get("vehicle_type") == "Animal":
                ax = other_data.get("position_x", 0)
                ay = other_data.get("position_y", 0)

                dist_to_animal = math.sqrt(
                    (ax - self.position_x) ** 2 + (ay - self.position_y) ** 2
                )

                if dist_to_animal < 250.0:
                    if self.heading == "EAST" and ax > self.position_x:
                        self._brake("ANIMAL PE DRUM!")
                        return
                    elif self.heading == "WEST" and ax < self.position_x:
                        self._brake("ANIMAL PE DRUM!")
                        return

        # 0.5 ACC & DEPĂȘIRE OBSTACOLE (Waze Rerouting)
        obstacle_in_front = False
        for other_id, other_data in list(self.memory.items()):
            if other_data.get("vehicle_type") == "Infrastructure":
                continue

            oh = other_data.get("heading", "")
            if oh == self.heading:
                ox, oy = other_data.get("position_x", 0), other_data.get(
                    "position_y", 0
                )

                is_in_front = False
                if (
                    self.heading == "EAST"
                    and ox > self.position_x - 15
                    and abs(oy - self.position_y) < 20
                ):
                    is_in_front = True
                elif (
                    self.heading == "WEST"
                    and ox < self.position_x + 15
                    and abs(oy - self.position_y) < 20
                ):
                    is_in_front = True
                elif (
                    self.heading == "SOUTH"
                    and oy > self.position_y - 15
                    and abs(ox - self.position_x) < 20
                ):
                    is_in_front = True
                elif (
                    self.heading == "NORTH"
                    and oy < self.position_y + 15
                    and abs(ox - self.position_x) < 20
                ):
                    is_in_front = True

                if is_in_front:
                    dist_to_front = math.sqrt(
                        (ox - self.position_x) ** 2 + (oy - self.position_y) ** 2
                    )

                    angle_diff = abs(
                        (self.visual_angle % 360)
                        - (other_data.get("visual_angle", 0) % 360)
                    )
                    if angle_diff > 180:
                        angle_diff = 360 - angle_diff
                    if angle_diff > 25.0:
                        continue  

                    if other_data.get("is_crashed", False) and dist_to_front < 160.0:
                        obstacle_in_front = True
                        self.target_lane_offset = (
                            80.0  
                        )
                        continue

                    safe_distance = 150.0  

                    if dist_to_front < safe_distance:
                        viteza_lider = other_data.get("speed", 0.0)

                        if self.driving_style == "Aggressive":
                            if dist_to_front > 60.0:
                                return

                            if dist_to_front < 47.0: 
                                self.speed = max(0.0, viteza_lider - 5.0)
                            else:
                                if self.speed > viteza_lider:
                                    self.speed = max(
                                        viteza_lider, self.speed - 15.0
                                    )  
                                else:
                                    self.speed = viteza_lider
                            self.current_state = "BRAKING"
                            return
                        else:
                            if dist_to_front < 60.0:
                                self.speed = max(0.0, viteza_lider - 2.0)
                            else:
                                if self.speed > viteza_lider:
                                    self.speed = max(viteza_lider, self.speed - 3.0)
                            self.current_state = "BRAKING"
                            return

        if not obstacle_in_front:
            self.target_lane_offset = 0.0

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

        dist_to_int = math.sqrt(
            (int_x - self.position_x) ** 2 + (int_y - self.position_y) ** 2
        )
        in_intersection = dist_to_int <= 60.0

        # IERARHIA 1: PRIORITATE AMBULANȚĂ
        if self.vehicle_type != "Ambulance":
            for other_id, other_data in list(self.memory.items()):
                if other_data.get("vehicle_type") == "Ambulance":
                    amb_int = other_data.get("target_int", (0, 0))
                    if (
                        math.sqrt((int_x - amb_int[0]) ** 2 + (int_y - amb_int[1]) ** 2)
                        > 50.0
                    ):
                        continue

                    ox, oy = other_data.get("position_x", 0), other_data.get(
                        "position_y", 0
                    )
                    oh, o_speed = other_data.get("heading", ""), other_data.get(
                        "speed", 0
                    )
                    o_dist_to_int = math.sqrt((int_x - ox) ** 2 + (int_y - oy) ** 2)

                    amb_past = False
                    if oh == "SOUTH" and oy > int_y + 40:
                        amb_past = True
                    if oh == "NORTH" and oy < int_y - 40:
                        amb_past = True
                    if oh == "EAST" and ox > int_x + 40:
                        amb_past = True
                    if oh == "WEST" and ox < int_x - 40:
                        amb_past = True

                    my_ttc = dist_to_int / max(self.speed, 1.0)
                    amb_ttc = o_dist_to_int / max(o_speed, 1.0)

                    if not amb_past and o_dist_to_int < 400.0:
                        if my_ttc < amb_ttc - 2.0:
                            continue
                        if dist_to_int < 150.0:
                            self._brake("Cedez trecerea Ambulanței!")
                            return
                        else:
                            self.speed = max(1.0, self.speed - 0.2)
                            return

        if self.vehicle_type == "Ambulance":
            self.turn_intent = "PRIORITY"
            self._recover_speed()
            return

        # IERARHIA 2: SEMAFOR (V2I)
        semafor_data = self.memory.get("Semafor_Centru")
        is_light_here = False
        has_green_light = False

        if semafor_data and int_x == 400 and int_y == 650 and dist_to_int < 150.0:
            culoare_axa_mea = "GREEN"

        if is_light_here and not in_intersection:
            culoare_axa_mea = "GREEN"
            if self.heading in ["NORTH", "SOUTH"]:
                culoare_axa_mea = semafor_data.get("state_NS", "GREEN")
            elif self.heading in ["EAST", "WEST"]:
                culoare_axa_mea = semafor_data.get("state_EW", "GREEN")
            time_to_change = semafor_data.get("time_to_change", 5.0)

            if culoare_axa_mea == "RED":
                if self.driving_style == "Aggressive":
                    if dist_to_int < 80.0:
                        self._brake("V2I: Opresc la Semafor ROȘU (Agresiv)")
                        return
                else:
                    if dist_to_int < 120.0:
                        self._brake("V2I: Opresc la Semafor ROȘU")
                        return
                    elif dist_to_int < 400.0:
                        cadre_ramase = time_to_change * 20
                        if cadre_ramase > 0:
                            viteza_optima = min(
                                self.desired_speed, max(1.0, dist_to_int / cadre_ramase)
                            )
                            if self.speed > viteza_optima:
                                self.speed = max(viteza_optima, self.speed - 0.2)
                            elif self.speed < viteza_optima:
                                self.speed = min(viteza_optima, self.speed + 1.0)
                            return

            elif culoare_axa_mea == "YELLOW":
                if self.driving_style == "Aggressive":
                    has_green_light = True
                else:
                    timp_pana_la_centru = dist_to_int / max(self.speed, 1.0)
                    if timp_pana_la_centru <= time_to_change + 0.5:
                        has_green_light = True
                    elif (
                        dist_to_int <= 150.0
                    ):  
                        self._brake("V2I: Opresc la Semafor GALBEN")
                        return
            elif culoare_axa_mea == "GREEN":
                has_green_light = True

        if has_green_light:
            self.turn_intent = "PRIORITY"
            self._recover_speed()
            return

        # IERARHIA 2.5: REFLEX PRIORITATE DE DREAPTA
        if dist_to_int < 130.0:
            for other_id, other_data in list(self.memory.items()):
                if other_data.get("vehicle_type") == "Infrastructure":
                    continue

                ox = other_data.get("position_x", 0)
                oy = other_data.get("position_y", 0)
                other_dist_to_int = math.sqrt((ox - int_x) ** 2 + (oy - int_y) ** 2)

                if other_dist_to_int < 130.0:
                    oh = other_data.get("heading", "")

                    vine_din_dreapta = False
                    if self.heading == "NORTH" and oh == "WEST":
                        vine_din_dreapta = True
                    elif self.heading == "SOUTH" and oh == "EAST":
                        vine_din_dreapta = True
                    elif self.heading == "EAST" and oh == "NORTH":
                        vine_din_dreapta = True
                    elif self.heading == "WEST" and oh == "SOUTH":
                        vine_din_dreapta = True

                    if (
                        other_data.get("vehicle_type") == "Ambulance"
                        and self.vehicle_type != "Ambulance"
                    ):
                        vine_din_dreapta = True

                    if vine_din_dreapta:
                        trecut_de_centru = False
                        if oh == "WEST" and ox < int_x - 20:
                            trecut_de_centru = True
                        elif oh == "EAST" and ox > int_x + 20:
                            trecut_de_centru = True
                        elif oh == "NORTH" and oy < int_y - 20:
                            trecut_de_centru = True
                        elif oh == "SOUTH" and oy > int_y + 20:
                            trecut_de_centru = True

                        if not trecut_de_centru:
                            if dist_to_int > 45.0:
                                self.speed = max(0.0, self.speed - 3.5)
                            else:
                                self.speed = 0.0 

                            self._brake(f"Prioritate de dreapta pentru {other_id}")
                            return 

        # IERARHIA 3A: ZIPPER MERGE
        if abs(int_x - 770) < 20 and abs(int_y - 455) < 20:
            conflict_merge = False
            for other_id, other_data in list(self.memory.items()):
                if other_data.get("vehicle_type") == "Infrastructure":
                    continue
                other_int = other_data.get("target_int", (0, 0))
                if (
                    math.sqrt((int_x - other_int[0]) ** 2 + (int_y - other_int[1]) ** 2)
                    > 50.0
                ):
                    continue

                ox, oy = other_data.get("position_x", 0), other_data.get(
                    "position_y", 0
                )
                o_dist = math.sqrt((int_x - ox) ** 2 + (int_y - oy) ** 2)

                if dist_to_int < 300.0 and o_dist < 300.0:
                    conflict_merge = True
                    if dist_to_int > o_dist + 15.0:
                        self._brake(f"Zipper: YIELD pt {other_id}")
                        return
                    elif abs(dist_to_int - o_dist) <= 15.0 and self.agent_id > other_id:
                        self._brake("Zipper: Tie-breaker YIELD")
                        return
                    self.turn_intent = "PRIORITY"
            if not conflict_merge:
                self._recover_speed()
            return

        # IERARHIA 3B: PRIORITATE DE DREAPTA
        if dist_to_int > 350.0:
            self._recover_speed()
            return

        conflict_detected = False
        for other_id, other_data in list(self.memory.items()):
            if other_data.get("vehicle_type") == "Infrastructure":
                continue
            if other_data.get("heading") == self.heading:
                continue

            other_int = other_data.get("target_int", (0, 0))
            if (
                math.sqrt((int_x - other_int[0]) ** 2 + (int_y - other_int[1]) ** 2)
                > 50.0
            ):
                continue

            ox, oy = other_data.get("position_x", 0), other_data.get("position_y", 0)
            oh = other_data.get("heading", "")

            if (self.heading in ["NORTH", "SOUTH"] and oh in ["NORTH", "SOUTH"]) or (
                self.heading in ["EAST", "WEST"] and oh in ["EAST", "WEST"]
            ):
                continue

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

            if o_dist < 350.0:
                my_ttc = dist_to_int / max(self.speed, 1.0)
                o_ttc = o_dist / max(other_data.get("speed", 0), 1.0)

                if abs(my_ttc - o_ttc) < 3.5 or o_dist < 80.0:
                    conflict_detected = True
                    yields_to = {
                        "EAST": "NORTH",
                        "NORTH": "WEST",
                        "WEST": "SOUTH",
                        "SOUTH": "EAST",
                    }

                    if yields_to.get(self.heading) == oh:
                        if self.turn_intent == "TURN_RIGHT":
                            continue
                        if dist_to_int > 90.0:
                            self.speed = max(1.5, self.speed - 0.5)
                            self.current_state = "BRAKING"
                            return
                        elif 50.0 <= dist_to_int <= 90.0:
                            self._brake(f"Cedez trecerea pt {other_id}")
                            return
                    elif yields_to.get(oh) == self.heading:
                        self.turn_intent = "PRIORITY"
                        continue
                    else:
                        self._negotiate_ai(other_id, other_data)
                        return
        if not conflict_detected:
            self.last_ai_decision = None
            self._recover_speed()

    def _brake(self, reason):
        self.current_state = "BRAKING"
        decel_rate = 6.0 if self.driving_style == "Aggressive" else 4.5
        self.speed = max(0, self.speed - decel_rate)

    def _recover_speed(self):
        self.current_state = "CRUISE"
        accel_rate = 4.0 if self.driving_style == "Aggressive" else 2.0
        if self.speed < self.desired_speed:
            self.speed = min(self.desired_speed, self.speed + accel_rate)

    def _negotiate_ai(self, other_id, other_data):
        if self.waiting_for_ai:
            self.speed = max(0, self.speed - 2.0)
            return

        current_time = time.time()
        if self.last_ai_decision and (
            current_time - self.last_ai_call_time < self.decision_cooldown
        ):
            if "FRANEAZA" in self.last_ai_decision:
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

    def update_position(self, dt):
        if self.speed <= 0:
            return

        if self.current_node_index >= len(self.route) - 1:
            angle_rad = math.radians(self.visual_angle)
            self.base_x += self.speed * dt * math.cos(angle_rad)
            self.base_y += self.speed * dt * math.sin(angle_rad)
        else:
            next_node_name = self.route[self.current_node_index + 1]
            tx, ty = nodes[next_node_name]
            dist = math.sqrt((tx - self.base_x) ** 2 + (ty - self.base_y) ** 2)

            if dist < 5.0:
                self.current_node_index += 1
                if self.current_node_index < len(self.route) - 1:
                    self._update_heading_and_turn()
                    tx, ty = nodes[self.route[self.current_node_index + 1]]

            if self.current_node_index < len(self.route) - 1:
                angle_rad = math.atan2(ty - self.base_y, tx - self.base_x)
                self.visual_angle = math.degrees(angle_rad)

                self.base_x += self.speed * dt * math.cos(angle_rad)
                self.base_y += self.speed * dt * math.sin(angle_rad)

        deg = self.visual_angle
        if -45 <= deg <= 45:
            self.heading = "EAST"
        elif 45 < deg <= 135:
            self.heading = "SOUTH"
        elif -135 <= deg < -45:
            self.heading = "NORTH"
        else:
            self.heading = "WEST"

        viteză_virare = 55.0 

        if self.current_lane_offset < self.target_lane_offset:
            self.current_lane_offset += viteză_virare * dt
            if self.current_lane_offset > self.target_lane_offset:
                self.current_lane_offset = self.target_lane_offset
        elif self.current_lane_offset > self.target_lane_offset:
            self.current_lane_offset -= viteză_virare * dt
            if self.current_lane_offset < self.target_lane_offset:
                self.current_lane_offset = self.target_lane_offset

        angle_rad = math.radians(self.visual_angle)
        perp_angle = angle_rad - math.pi / 2 

        self.position_x = self.base_x + math.cos(perp_angle) * self.current_lane_offset
        self.position_y = self.base_y + math.sin(perp_angle) * self.current_lane_offset

        # CLOUD TELEMETRY: Trimitem datele spre Docker (Grafana)
        if hasattr(self, "last_telemetry_time"):
            if time.time() - self.last_telemetry_time < 1.0:
                return
        self.last_telemetry_time = time.time()

        # InfluxDB
        is_braking = 1 if self.current_state == "BRAKING" else 0
        data_string = f"vehicle_stats,agent_id={self.agent_id} speed={self.speed},braking={is_braking}"

        headers = {"Authorization": "Token super-secret-auth-token"}

        def send_to_cloud():
            try:
                requests.post(
                    "http://localhost:8086/api/v2/write?org=v2x_org&bucket=telemetry&precision=s",
                    headers=headers,
                    data=data_string,
                    timeout=0.5,
                )
            except:
                pass 

        threading.Thread(target=send_to_cloud, daemon=True).start()

    def _update_heading_and_turn(self):
        idx = self.current_node_index
        if idx < len(self.route) - 2:
            p_curr = nodes[self.route[idx]]
            p_next = nodes[self.route[idx + 1]]
            p_next2 = nodes[self.route[idx + 2]]

            angle1 = math.atan2(p_next[1] - p_curr[1], p_next[0] - p_curr[0])
            angle2 = math.atan2(p_next2[1] - p_next[1], p_next2[0] - p_next[0])
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
        payload = {
            "agent_id": self.agent_id,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "speed": self.speed,
            "driving_style": self.driving_style,
            "vehicle_type": self.vehicle_type,
            "visual_angle": self.visual_angle,
            "intent": (
                "CRASHED"
                if self.is_crashed
                else (
                    self.current_state
                    if self.current_state != "CRUISE"
                    else self.turn_intent
                )
            ),
            "is_crashed": self.is_crashed,
            "heading": self.heading,
            "timestamp": time.time(),
            "target_int": self.target_int,
        }

        payload["signature"] = sign_data(payload)
        return payload

    def has_decided_to_brake(self):
        return self.current_state == "BRAKING"
