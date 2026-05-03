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
from navigation_system import Navigator
from v2x_security import SecurityManager

load_dotenv()


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

        # Inițializăm Navigația în loc de zeci de variabile individuale!
        self.navigator = Navigator(agent_id, start_node, target_node)

        self.memory = {}
        self.last_ai_decision = None
        self.last_ai_call_time = 0
        self.decision_cooldown = 1.0
        self.waiting_for_ai = False
        self.target_int = (0, 0)
        self.is_crashed = False

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

    @property
    def position_x(self):
        return self.navigator.position_x

    @position_x.setter
    def position_x(self, val):
        self.navigator.position_x = val
        self.navigator.base_x = val

    @property
    def position_y(self):
        return self.navigator.position_y

    @position_y.setter
    def position_y(self, val):
        self.navigator.position_y = val
        self.navigator.base_y = val

    @property
    def heading(self):
        return self.navigator.heading

    @property
    def visual_angle(self):
        return self.navigator.visual_angle

    @property
    def turn_intent(self):
        return self.navigator.turn_intent

    @turn_intent.setter
    def turn_intent(self, val):
        self.navigator.turn_intent = val

    @property
    def route(self):
        return self.navigator.route

    @property
    def current_node_index(self):
        return self.navigator.current_node_index

    @property
    def target_lane_offset(self):
        return self.navigator.target_lane_offset

    @target_lane_offset.setter
    def target_lane_offset(self, val):
        self.navigator.target_lane_offset = val

    @property
    def base_x(self):
        return self.navigator.base_x

    @base_x.setter
    def base_x(self, val):
        self.navigator.base_x = val

    @property
    def base_y(self):
        return self.navigator.base_y

    @base_y.setter
    def base_y(self, val):
        self.navigator.base_y = val

    # === ACTUALIZĂM METODA DE POZIȚIE (devine foarte curată) ===
    def update_position(self, dt):
        if self.speed <= 0:
            return

        # Navigația face treaba grea
        self.navigator.update_position(dt, self.speed)

        # CLOUD TELEMETRY: Rămâne neschimbat
        if hasattr(self, "last_telemetry_time"):
            if time.time() - self.last_telemetry_time < 1.0:
                return
        self.last_telemetry_time = time.time()

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

    def receive_v2x_message(self, message):
        sender_id = message.get("agent_id")
        if not sender_id or sender_id == self.agent_id:
            return

        if message.get("vehicle_type") == "Animal":
            self.memory[sender_id] = message
            return

        if SecurityManager.is_payload_valid(message, self.agent_id):
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

        # Calculăm distanța până la centrul intersecției curente din timp
        dist_to_int = math.sqrt(
            (int_x - self.position_x) ** 2 + (int_y - self.position_y) ** 2
        )

        # 0. URGENȚĂ ABSOLUTĂ: Evitare Animale
        for other_id, other_data in list(self.memory.items()):
            if other_data.get("vehicle_type") == "Animal":
                ax = other_data.get("position_x", 0)
                ay = other_data.get("position_y", 0)

                dist_to_animal = math.sqrt(
                    (ax - self.position_x) ** 2 + (ay - self.position_y) ** 2
                )

                if (
                    dist_to_animal < 100.0
                ):  # Redus pt ca mașinile din spate să folosească ACC-ul
                    if self.heading == "EAST" and ax > self.position_x:
                        self._brake("ANIMAL PE DRUM!")
                        return
                    elif self.heading == "WEST" and ax < self.position_x:
                        self._brake("ANIMAL PE DRUM!")
                        return

        # 0.1 TRAGERE PE DREAPTA PENTRU AMBULANȚĂ
        is_pulling_over = False
        # Interzicem tragerea pe dreapta dacă mașina este deja la linia de oprire sau în intersecție (dist_to_int < 85.0)
        # pentru a preveni glisarea (slide-ul) peste benzile perpendiculare.
        if self.vehicle_type != "Ambulance" and dist_to_int > 85.0:
            for other_id, other_data in list(self.memory.items()):
                if other_data.get("vehicle_type") == "Ambulance" and not other_data.get(
                    "is_crashed", False
                ):
                    ox, oy = other_data.get("position_x", 0), other_data.get(
                        "position_y", 0
                    )
                    oh = other_data.get("heading", "")
                    opposite_headings = {
                        "NORTH": "SOUTH",
                        "SOUTH": "NORTH",
                        "EAST": "WEST",
                        "WEST": "EAST",
                    }

                    dot_amb = 0
                    dist_amb = 999.0

                    if self.heading == oh:
                        dx_amb = self.position_x - ox
                        dy_amb = self.position_y - oy
                        rad = math.radians(self.visual_angle)
                        dot_amb = dx_amb * math.cos(rad) + dy_amb * math.sin(rad)
                        dist_amb = math.sqrt(dx_amb**2 + dy_amb**2)
                    elif opposite_headings.get(self.heading) == oh:
                        dx_amb = ox - self.position_x
                        dy_amb = oy - self.position_y
                        rad = math.radians(self.visual_angle)
                        dot_amb = dx_amb * math.cos(rad) + dy_amb * math.sin(rad)
                        dist_amb = math.sqrt(dx_amb**2 + dy_amb**2)

                    # Detectează ambulanța mai devreme pentru a avea timp să comprime coloana
                    if dot_amb > 0 and dist_amb < 350.0:
                        self.target_lane_offset = -20.0
                        is_pulling_over = True
                        break

        # 0.5 ACC & DEPĂȘIRE OBSTACOLE (Waze Rerouting)
        obstacle_in_front = False
        for other_id, other_data in list(self.memory.items()):
            if other_data.get("vehicle_type") == "Infrastructure":
                continue

            ox, oy = other_data.get("position_x", 0), other_data.get("position_y", 0)
            other_angle = other_data.get("visual_angle", 0)

            # Calculăm diferența reală de rotație a mașinilor
            angle_diff = abs((self.visual_angle % 360) - (other_angle % 360))
            if angle_diff > 180:
                angle_diff = 360 - angle_diff

            # Dacă merg relativ pe aceeași axă / direcție
            if angle_diff <= 35.0:
                dx = ox - self.base_x
                dy = oy - self.base_y

                rad = math.radians(self.visual_angle)
                vx = math.cos(rad)
                vy = math.sin(rad)

                # Produsul scalar (ne arată dacă e în față) și Produsul vectorial (dacă e pe bandă)
                dot = dx * vx + dy * vy
                cross = abs(dx * (-vy) + dy * vx)

                # Lărgim unghiul vizual lateral dacă mașina trage pe dreapta pentru a preveni suprapunerea (overlapping)
                cross_threshold = 60.0 if is_pulling_over else 25.0

                if dot > 0 and cross < cross_threshold:
                    dist_to_front = math.sqrt(dx**2 + dy**2)

                    if other_data.get("is_crashed", False) and dist_to_front < 160.0:
                        obstacle_in_front = True
                        self.target_lane_offset = 25.0
                        continue

                    safe_distance = 150.0

                    if dist_to_front < safe_distance:
                        viteza_lider = other_data.get("speed", 0.0)

                        # NOU: Ambulanța depășește fluid mașinile lente sau oprite din fața ei!
                        if (
                            self.vehicle_type == "Ambulance"
                            and viteza_lider < self.speed - 10.0
                            and dist_to_front < 120.0
                        ):
                            # --- PREVENIRE COLIZIUNE FRONTALĂ (DEPĂȘIRE SIGURĂ) ---
                            contrasens_liber = True
                            opposite_headings = {
                                "NORTH": "SOUTH",
                                "SOUTH": "NORTH",
                                "EAST": "WEST",
                                "WEST": "EAST",
                            }
                            my_opposite = opposite_headings.get(self.heading)

                            for opp_id, opp_data in list(self.memory.items()):
                                if opp_data.get(
                                    "heading"
                                ) == my_opposite and not opp_data.get(
                                    "is_crashed", False
                                ):
                                    dx_opp = (
                                        opp_data.get("position_x", 0) - self.position_x
                                    )
                                    dy_opp = (
                                        opp_data.get("position_y", 0) - self.position_y
                                    )

                                    rad_opp = math.radians(self.visual_angle)
                                    dot_opp = dx_opp * math.cos(
                                        rad_opp
                                    ) + dy_opp * math.sin(rad_opp)
                                    dist_opp = math.sqrt(dx_opp**2 + dy_opp**2)

                                    # Vine spre noi și e la o distanță periculoasă
                                    if dot_opp > 0 and dist_opp < 300.0:
                                        if (
                                            opp_data.get("vehicle_type") == "Ambulance"
                                            or dist_opp < 150.0
                                        ):
                                            contrasens_liber = False
                                            break

                            if contrasens_liber:
                                obstacle_in_front = True
                                self.target_lane_offset = 25.0
                                continue

                        if is_pulling_over:
                            self.current_state = "BRAKING"
                            if dist_to_front < 48.0:
                                self.speed = 0.0
                            else:
                                # Se apropie mai rapid (cu 20.0) ca să lase loc compact în spate
                                self.speed = max(20.0, self.speed - 2.0)
                            return

                        if self.driving_style == "Aggressive":
                            if dist_to_front < 48.0:
                                self.speed = max(
                                    0.0, min(self.speed, viteza_lider) - 5.0
                                )
                                self.current_state = "BRAKING"
                                return
                            elif (
                                dist_to_front < 75.0 and self.speed > viteza_lider + 2.0
                            ):
                                self.speed = max(viteza_lider, self.speed - 4.0)
                                self.current_state = "BRAKING"
                                return
                        else:
                            if dist_to_front < 55.0:
                                self.speed = max(
                                    0.0, min(self.speed, viteza_lider) - 2.0
                                )
                                self.current_state = "BRAKING"
                                return
                            elif (
                                dist_to_front < 85.0 and self.speed > viteza_lider + 2.0
                            ):
                                self.speed = max(viteza_lider, self.speed - 2.0)
                                self.current_state = "BRAKING"
                                return

        if not obstacle_in_front and not is_pulling_over:
            # --- ASIGURARE LA REINTRAREA PE BANDĂ ---
            safe_to_return = True
            if self.target_lane_offset < -10.0:  # Dacă suntem încă trași pe dreapta
                for other_id, other_data in list(self.memory.items()):
                    if other_data.get(
                        "vehicle_type"
                    ) == "Infrastructure" or other_data.get("is_crashed", False):
                        continue

                    if other_data.get("heading") == self.heading:
                        ox = other_data.get("position_x", 0)
                        oy = other_data.get("position_y", 0)

                        dx_rear = ox - self.position_x
                        dy_rear = oy - self.position_y
                        rad = math.radians(self.visual_angle)

                        # Produsul scalar (dot product) negativ înseamnă că e în SPATELE nostru
                        dot_rear = dx_rear * math.cos(rad) + dy_rear * math.sin(rad)
                        dist_rear = math.sqrt(dx_rear**2 + dy_rear**2)

                        # Dacă o mașină vine din spate pe banda noastră și e aproape (< 150px)
                        if dot_rear < 0 and dist_rear < 150.0:
                            # EVITARE DEADLOCK: Dacă mașina din spate e lentă sau oprită (așteptând în coloană), ne putem reîncadra.
                            v_spate = other_data.get("speed", 0.0)
                            if v_spate > max(15.0, self.speed):
                                safe_to_return = False
                                break

            if safe_to_return:
                self.target_lane_offset = 0.0
            else:
                self.target_lane_offset = -20.0
                self.current_state = "BRAKING"

                # --- PREVENIRE SLIDE PRIN INTERSECȚIE ---
                # Dacă suntem pe dreapta și am ajuns la linia de oprire, OPRIM complet!
                if 45.0 < dist_to_int < 80.0:
                    self.speed = 0.0
                else:
                    self.speed = max(
                        15.0, self.speed - 2.0
                    )  # Așteptăm pe dreapta să treacă traficul
                return

        if is_pulling_over:
            self.current_state = "BRAKING"
            self.speed = max(20.0, self.speed - 2.0)
            return

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

        in_intersection = dist_to_int <= 60.0

        # IERARHIA 1: PRIORITATE AMBULANȚĂ
        if self.vehicle_type != "Ambulance":
            for other_id, other_data in list(self.memory.items()):
                if other_data.get("vehicle_type") == "Ambulance":
                    if other_data.get("is_crashed", False):
                        continue

                    ox, oy = other_data.get("position_x", 0), other_data.get(
                        "position_y", 0
                    )
                    oh = other_data.get("heading", "")

                    amb_int = other_data.get("target_int", (0, 0))
                    if (
                        math.sqrt((int_x - amb_int[0]) ** 2 + (int_y - amb_int[1]) ** 2)
                        > 50.0
                    ):
                        continue
                    o_speed = other_data.get("speed", 0)
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
            # --- EVITARE COLIZIUNE ÎNTRE 2 AMBULANȚE ÎN INTERSECȚIE ---
            if dist_to_int < 150.0:
                for other_id, other_data in list(self.memory.items()):
                    if other_data.get(
                        "vehicle_type"
                    ) == "Ambulance" and not other_data.get("is_crashed", False):
                        ox, oy = other_data.get("position_x", 0), other_data.get(
                            "position_y", 0
                        )

                        # Ne asigurăm că cealaltă ambulanță vine spre aceeași intersecție
                        amb_int = other_data.get("target_int", (0, 0))
                        if (
                            math.sqrt(
                                (int_x - amb_int[0]) ** 2 + (int_y - amb_int[1]) ** 2
                            )
                            > 50.0
                        ):
                            continue

                        o_dist = math.sqrt((ox - int_x) ** 2 + (oy - int_y) ** 2)

                        if o_dist < 150.0:
                            if o_dist < dist_to_int - 20.0:
                                self._brake("Cedez pt altă ambulanță!")
                                return
                            elif (
                                abs(dist_to_int - o_dist) <= 20.0
                                and self.agent_id > other_id
                            ):
                                self._brake("Tie-breaker ambulanțe")
                                return

            self.turn_intent = "PRIORITY"
            self._recover_speed()
            return

        # IERARHIA 2: SEMAFOR (V2I)
        semafor_data = self.memory.get("Semafor_Centru")
        is_light_here = False
        has_green_light = False

        if semafor_data and abs(int_x - 400) < 20 and abs(int_y - 650) < 20:
            is_light_here = True

        if is_light_here:
            culoare_axa_mea = "GREEN"
            if self.heading in ["NORTH", "SOUTH"]:
                culoare_axa_mea = semafor_data.get("state_NS", "GREEN")
            elif self.heading in ["EAST", "WEST"]:
                culoare_axa_mea = semafor_data.get("state_EW", "GREEN")
            time_to_change = semafor_data.get("time_to_change", 5.0)

            # Verificăm dacă a forțat deja intersecția sau a trecut de linia de oprire
            has_passed_stop_line = False
            if self.heading == "EAST" and self.position_x > int_x - 45:
                has_passed_stop_line = True
            elif self.heading == "WEST" and self.position_x < int_x + 45:
                has_passed_stop_line = True
            elif self.heading == "SOUTH" and self.position_y > int_y - 45:
                has_passed_stop_line = True
            elif self.heading == "NORTH" and self.position_y < int_y + 45:
                has_passed_stop_line = True

            if has_passed_stop_line:
                has_green_light = True
            elif culoare_axa_mea == "RED":
                if self.driving_style == "Aggressive":
                    if dist_to_int < 80.0:
                        if dist_to_int < 65.0:
                            self.speed = 0.0
                        else:
                            self._brake("V2I: Opresc la Semafor ROȘU (Agresiv)")
                        return
                else:
                    if dist_to_int < 120.0:
                        if dist_to_int < 65.0:
                            self.speed = 0.0
                        else:
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
                    elif dist_to_int <= 150.0:
                        if dist_to_int < 65.0:
                            self.speed = 0.0
                        else:
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
                if other_data.get("is_crashed", False):
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
                        # --- NU CEDĂM DACĂ SUNTEM MULT MAI APROAPE DE CENTRU ---
                        if dist_to_int < other_dist_to_int - 25.0:
                            continue

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
                            # --- ANTI-DEADLOCK TIE-BREAKER ---
                            # Dacă celălalt stă pe loc și suntem blocați, forțăm trecerea după ID
                            if (
                                other_data.get("speed", 0) < 1.0
                                and self.agent_id > other_id
                            ):
                                continue

                            if dist_to_int > 45.0:
                                self.speed = max(0.0, self.speed - 3.5)
                            else:
                                self.speed = 0.0

                            self._brake(f"Prioritate de dreapta pentru {other_id}")
                            return

        # IERARHIA 3A: ZIPPER MERGE
        if abs(int_x - 770) < 20 and abs(int_y - 455) < 20:
            # --- NOU: EVITARE BLOCAJ POST-DIAGONALĂ ---
            if self.heading == "WEST" and self.position_x < int_x - 5:
                self._recover_speed()
                return
            if self.heading == "EAST" and self.position_x > int_x + 5:
                self._recover_speed()
                return
            if self.heading == "NORTH" and self.position_y < int_y - 5:
                self._recover_speed()
                return
            if self.heading == "SOUTH" and self.position_y > int_y + 5:
                self._recover_speed()
                return
            # ------------------------------------------

            conflict_merge = False
            for other_id, other_data in list(self.memory.items()):
                if other_data.get("vehicle_type") == "Infrastructure" or other_data.get(
                    "is_crashed", False
                ):
                    continue

                ox = other_data.get("position_x", 0)
                oy = other_data.get("position_y", 0)
                other_dist_to_int = math.sqrt((ox - int_x) ** 2 + (oy - int_y) ** 2)

                if other_dist_to_int < 80.0:
                    if other_dist_to_int < dist_to_int and dist_to_int > 30.0:
                        # Anti-deadlock la Zipper Merge
                        if (
                            other_data.get("speed", 0) < 1.0
                            and self.agent_id > other_id
                        ):
                            continue
                        conflict_merge = True
                        break

            if conflict_merge:
                self._brake("Zipper Merge: Cedez")
                return

        # IERARHIA 3B: AI LLM Negociere (Intersecții fără semafor)
        if not is_light_here and in_intersection and not self.waiting_for_ai:
            for other_id, other_data in list(self.memory.items()):
                if other_data.get("vehicle_type") == "Infrastructure" or other_data.get(
                    "is_crashed", False
                ):
                    continue

                ox = other_data.get("position_x", 0)
                oy = other_data.get("position_y", 0)
                o_dist = math.sqrt((ox - int_x) ** 2 + (oy - int_y) ** 2)

                if o_dist < 60.0:
                    self._negotiate_ai(other_id, other_data)
                    return

        self._recover_speed()
        self.last_ai_decision = None

    def _negotiate_ai(self, other_id, other_data):
        current_time = time.time()
        if current_time - self.last_ai_call_time < self.decision_cooldown:
            if self.last_ai_decision == "FRANEAZA":
                self._brake(f"AI Cooldown: Frânez pt {other_id}")
            return

        self.waiting_for_ai = True
        self._brake("AI gândește...")

        def call_llm():
            try:
                response = self.chain.invoke(
                    {
                        "my_id": self.agent_id,
                        "my_type": self.vehicle_type,
                        "my_heading": self.heading,
                        "other_id": other_id,
                        "other_type": other_data.get("vehicle_type", "Normal"),
                        "other_heading": other_data.get("heading", "UNKNOWN"),
                    }
                )
                decision = response.content.strip().upper()
                self.last_ai_decision = decision
                self.last_ai_call_time = time.time()

                if "FRANEAZA" in decision:
                    self._brake(f"AI Decizie: Frânez pt {other_id}")
                else:
                    self._recover_speed()
            except Exception as e:
                print(f"[{self.agent_id}] AI Eroare: {e}")
                self._brake("Eroare AI -> Opresc de siguranță")
            finally:
                self.waiting_for_ai = False

        threading.Thread(target=call_llm, daemon=True).start()

    def _brake(self, reason):
        self.current_state = "BRAKING"
        self.turn_intent = "YIELDING"
        self.speed = max(0.0, self.speed - 3.0)

    def _recover_speed(self):
        self.current_state = "CRUISE"
        if self.speed < self.desired_speed:
            self.speed += 1.0
        elif self.speed > self.desired_speed:
            self.speed -= 1.0

    def get_emergency_status(self):
        data = {
            "agent_id": self.agent_id,
            "vehicle_type": self.vehicle_type,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "speed": self.speed,
            "heading": self.heading,
            "visual_angle": self.visual_angle,
            "intent": self.current_state,
            "driving_style": self.driving_style,
            "target_int": self.target_int,
            "is_crashed": self.is_crashed,
            "timestamp": time.time(),
        }
        data["signature"] = SecurityManager.sign_data(data)
        return data

    def has_decided_to_brake(self):
        return self.current_state == "BRAKING"
