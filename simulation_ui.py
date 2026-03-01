import pygame
import sys
import json
import math  # Importăm modulul math pentru calcule vectoriale
from map_config import nodes, edges  # Importăm configurația complexă a hărții

# --- CONFIGURAȚII ---
SCREEN_WIDTH = 1500
SCREEN_HEIGHT = 800
ROAD_WIDTH_MAIN = 80  # Lățimea drumurilor principale (2 benzi)
ROAD_WIDTH_SECONDARY = 40  # Lățimea drumurilor secundare (1 bandă)

# CULORI
COLOR_BACKGROUND = (15, 15, 15)
COLOR_ROAD = (50, 50, 50)  # Asfalt
COLOR_LINE = (200, 200, 200)  # Linii albe
COLOR_WALL = (80, 80, 80)  # Clădiri (pentru reintroducere opțională)
COLOR_TEXT = (102, 178, 255)
COLOR_NORMAL_CAR = (153, 153, 255)
COLOR_AMBULANCE_CAR = (204, 0, 0)
COLOR_RED = (255, 0, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_YELLOW = (255, 165, 0)
COLOR_GRASS = (69, 108, 46)


class SimulationUI:
    def __init__(self, title="V2X Stylized Grid Simulator"):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.screen.fill(COLOR_BACKGROUND)
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("timesnewroman", 16, bold=True)
        self.small_font = pygame.font.SysFont("timesnewroman", 13)
        self.fps = 60

        self.system_on = True
        self.button_rect = pygame.Rect(20, 20, 150, 40)

        self.ai_enabled = True
        self.ai_button_rect = pygame.Rect(190, 20, 150, 40)

        # NOU: Butonul pentru căprioară (sub cel de sistem)
        self.animal_button_rect = pygame.Rect(20, 70, 150, 40)

        self.spawn_car_button_rect = pygame.Rect(190, 70, 150, 40)

        self.DEER_DECOR_POINTS = [
            (1270, 590),
            (1330, 565),
            (1320, 590),
            (1290, 560),
            (1400, 730),
            (1390, 760),
        ]

        self.COLOR_RED_OFF = (60, 0, 0)
        self.COLOR_YELLOW_OFF = (60, 60, 0)
        self.COLOR_GREEN_OFF = (0, 60, 0)

        try:
            self.img_normal = pygame.image.load("car.png").convert_alpha()
            self.img_ambulance = pygame.image.load("ambulance.png").convert_alpha()
            self.img_indicator = pygame.image.load("indicator.png").convert_alpha()
            self.img_indicator = pygame.transform.scale(self.img_indicator, (30, 30))
            # NOU: Încărcăm poza cu căprioara
            self.img_deer = pygame.image.load("deer.png").convert_alpha()
            self.use_images = True
        except Exception as e:
            print(f"Imagini negăsite. Folosesc forme geometrice. Eroare: {e}")
            self.use_images = False

        self.rotation_map = {"EAST": 0, "NORTH": 90, "WEST": 180, "SOUTH": 270}

    def draw_indicator(self):
        x1, y1 = 1400, 580  # indicator 1 (sus)
        x2, y2 = 1300, 700  # indicator 2 (jos)

        # Rotiri
        img_left = pygame.transform.rotate(self.img_indicator, 90)
        img_right = pygame.transform.rotate(self.img_indicator, -90)

        # Desenare imagini
        self.screen.blit(img_left, (x1, y1))
        self.screen.blit(img_right, (x2, y2))

        # Două dreptunghiuri subțiri
        pygame.draw.rect(self.screen, (0, 0, 0), (1425, 593, 50, 4))  # bară 1
        pygame.draw.rect(self.screen, (0, 0, 0), (1255, 712, 50, 4))  # bară 2

    def draw_dashed_line(
        self, surface, color, start_pos, end_pos, width=2, dash_length=20
    ):
        x1, y1 = start_pos
        x2, y2 = end_pos
        dl = math.hypot(x2 - x1, y2 - y1)
        if dl == 0:
            return

        dashes = int(dl / dash_length)
        for i in range(dashes):
            if i % 2 == 0:  # Desenăm doar segmentele pare (efectul de "punctat")
                start_x = x1 + (x2 - x1) * (i / dashes)
                start_y = y1 + (y2 - y1) * (i / dashes)
                end_x = x1 + (x2 - x1) * ((i + 1) / dashes)
                end_y = y1 + (y2 - y1) * ((i + 1) / dashes)
                pygame.draw.line(
                    surface, color, (start_x, start_y), (end_x, end_y), width
                )

    def is_outside_bounds(self, v_data):
        # PROTECȚIE CĂPRIOARĂ: Evită erorile când datele lipsesc
        if not v_data:
            return True
        if v_data.get("vehicle_type") == "Infrastructure":
            return False
        x, y = v_data.get("position_x", 0), v_data.get("position_y", 0)
        return x < -50 or x > SCREEN_WIDTH + 50 or y < -50 or y > SCREEN_HEIGHT + 50

    def draw_risk_aura(self, center, radius, color_rgb, max_alpha=120, rings=6):
        """
        Desenează un glow circular (aura) în jurul unui punct.
        color_rgb: (r,g,b)
        max_alpha: transparență maximă
        rings: câte "inele" pentru gradient
        """
        x, y = int(center[0]), int(center[1])

        aura = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        cx, cy = radius, radius

        # gradient: exterior mai transparent, interior mai intens
        for i in range(rings):
            t = i / max(1, rings - 1)
            r = int(radius * (1.0 - 0.12 * i))
            a = int(max_alpha * (1.0 - t) ** 2)
            pygame.draw.circle(aura, (*color_rgb, a), (cx, cy), r)

        self.screen.blit(aura, (x - radius, y - radius))

    def _intersection_centers_and_degree(self):
        """
        Returnează listă de (center_xy, degree) pentru intersecții I1/I2/I3.
        degree ~ câte drumuri ies din intersecție (aprox).
        """
        intersections = ["I1", "I2", "I3"]
        results = []

        # construim set de muchii pentru numărare
        for inter in intersections:
            corners = [f"{inter}_NW", f"{inter}_NE", f"{inter}_SE", f"{inter}_SW"]
            pts = [nodes.get(c) for c in corners if nodes.get(c)]
            if len(pts) != 4:
                continue

            cx = sum(p[0] for p in pts) / 4
            cy = sum(p[1] for p in pts) / 4

            # numărăm muchii care ating intersecția și merg spre "afară"
            degree = 0
            for u, v, _ in edges:
                u_is = u.startswith(inter + "_")
                v_is = v.startswith(inter + "_")
                # o muchie care pleacă din intersecție spre un nod care NU e din intersecție
                if u_is and not v_is:
                    degree += 1
                # și una care intră din afară în intersecție
                if v_is and not u_is:
                    degree += 1

            results.append(((cx, cy), degree))
        return results

    def draw_risk_overlays(self, current_traffic=None):
        # 1) intersecții: 4 ramuri = roșu intens, 3 ramuri = roșu mai soft
        for center, degree in self._intersection_centers_and_degree():
            # praguri simple: ajustează după ce vezi “degree” în practică
            if (
                degree >= 8
            ):  # de obicei intersecțiile “mari” au mai multe intrări/ieșiri în graf
                self.draw_risk_aura(
                    center, radius=85, color_rgb=(255, 0, 0), max_alpha=140
                )
            else:
                self.draw_risk_aura(
                    center, radius=70, color_rgb=(255, 0, 0), max_alpha=85
                )

        # 2) căprioară: portocaliu, dacă există în trafic
        if current_traffic:
            for v in current_traffic.values():
                if v and v.get("vehicle_type") == "Animal":
                    x = v.get("position_x", 0)
                    y = v.get("position_y", 0)
                    self.draw_risk_aura(
                        (x, y), radius=40, color_rgb=(255, 140, 0), max_alpha=110
                    )

    def draw_dashed_line_segment(
        self, p1, p2, color, dash_length=15, gap_length=10, offset=0
    ):
        """Desenează o linie punctată, cu un offset opțional pentru benzi multiple."""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length == 0:
            return

        # Calculează vectorul unitar al liniei
        unit_dx = dx / length
        unit_dy = dy / length

        # Calculează vectorul normal (perpendicular) pentru offset
        norm_dx = -unit_dy * offset
        norm_dy = unit_dx * offset

        current_x, current_y = p1[0] + norm_dx, p1[1] + norm_dy
        total_drawn = 0

        while total_drawn < length:
            draw_len = min(dash_length, length - total_drawn)
            end_x = current_x + unit_dx * draw_len
            end_y = current_y + unit_dy * draw_len

            pygame.draw.line(
                self.screen,
                color,
                (int(current_x), int(current_y)),
                (int(end_x), int(end_y)),
                1,
            )

            total_drawn += dash_length + gap_length
            current_x += unit_dx * (dash_length + gap_length)
            current_y += unit_dy * (dash_length + gap_length)

    def draw_building_along_road(self, p1, p2, width=60, offset=80, node_offset=50):
        """
        Clădire paralelă cu drumul, cu:
        - offset lateral față de drum
        - offset față de noduri (capete)
        """
        x1, y1 = p1
        x2, y2 = p2

        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length < 2 * node_offset:
            return

        ux = dx / length
        uy = dy / length

        # mutăm punctele mai în interior (offset față de noduri)
        x1 += ux * node_offset
        y1 += uy * node_offset
        x2 -= ux * node_offset
        y2 -= uy * node_offset

        # vector perpendicular
        px = -uy
        py = ux

        ox = px * offset
        oy = py * offset

        pA = (x1 + ox, y1 + oy)
        pB = (x2 + ox, y2 + oy)
        pC = (x2 + ox + px * width, y2 + oy + py * width)
        pD = (x1 + ox + px * width, y1 + oy + py * width)

        pygame.draw.polygon(self.screen, COLOR_WALL, [pA, pB, pC, pD])

    def draw_environment(self):
        """Desenează harta clasică, curată, exact ca într-o schiță."""
        self.screen.fill(COLOR_BACKGROUND)
        # iarba
        pygame.draw.polygon(
            self.screen,
            COLOR_GRASS,
            [
                (1000, 0),
                (SCREEN_WIDTH, 0),
                (SCREEN_WIDTH, SCREEN_HEIGHT),
                (600, SCREEN_HEIGHT),
            ],
            width=0,
        )
        pygame.draw.polygon(
            self.screen,
            COLOR_BACKGROUND,
            [(0, 100), (0, SCREEN_HEIGHT), (1140, 800), (1140, 675)],
            width=0,
        )

        # ====================================================
        # 1. STRATUL ASFALT: Desenăm fiecare bandă individual
        # ====================================================
        # Grosimea de 40px per bandă, așezate unele lângă altele pe coordonate,
        # acoperă și formează perfect intersecțiile la 90 de grade și fuziunile!
        for u, v, _ in edges:
            p1 = nodes.get(u)
            p2 = nodes.get(v)
            if p1 and p2:
                pygame.draw.line(self.screen, COLOR_ROAD, p1, p2, ROAD_WIDTH_SECONDARY)

        # DESENARE CLĂDIRI (Ajustate ca să nu cadă pe drumurile diagonale)
        self.draw_building_along_road(
            nodes["W_START"], nodes["I1_SW"], width=50, offset=40, node_offset=100
        )
        self.draw_building_along_road(
            nodes["MERGE_UP"], nodes["I3_NE"], width=50, offset=40, node_offset=50
        )
        self.draw_building_along_road(
            nodes["MERGE_UP"],
            nodes["NE_ONEWAY_START"],
            width=50,
            offset=40,
            node_offset=110,
        )
        self.draw_building_along_road(
            nodes["NW_START"], nodes["I3_NW"], width=50, offset=40, node_offset=100
        )
        self.draw_building_along_road(
            nodes["I3_SW"], nodes["I1_NW"], width=50, offset=40, node_offset=100
        )
        self.draw_building_along_road(
            nodes["W_END"], nodes["I1_NW"], width=50, offset=-90, node_offset=60
        )
        self.draw_building_along_road(
            nodes["I1_SE"], nodes["I2_SW"], width=50, offset=40, node_offset=100
        )
        self.draw_building_along_road(
            nodes["I1_NE"], nodes["I3_SE"], width=50, offset=40, node_offset=100
        )
        self.draw_building_along_road(
            nodes["I3_SE"], nodes["I2_NW"], width=40, offset=40, node_offset=250
        )

        # ====================================================
        # 2. STRATUL MARCAJE (Linii punctate pe axul drumurilor)
        # ====================================================
        drawn_dashed = set()
        for u, v, _ in edges:
            if (u, v) in drawn_dashed:
                continue

            # Sărim peste liniile punctate din interiorul intersecțiilor (ex: I1_NW -> I1_SW)
            # Vrem ca intersecția să fie goală pe mijloc, exact ca în realitate.
            if u.startswith("I") and v.startswith("I") and u[:2] == v[:2]:
                continue

            p1 = nodes.get(u)
            p2 = nodes.get(v)
            if not p1 or not p2:
                continue

            # Căutăm perechea (sensul opus) pentru a trasa linia punctată fix între ele
            for u2, v2, _ in edges:
                if (u2, v2) in drawn_dashed or (u2, v2) == (u, v):
                    continue

                p1_rev = nodes.get(u2)
                p2_rev = nodes.get(v2)
                if not p1_rev or not p2_rev:
                    continue

                # Verificăm dacă sunt benzi paralele (distanța dintre capete e mică)
                dist_starts = math.hypot(p1_rev[0] - p2[0], p1_rev[1] - p2[1])
                dist_ends = math.hypot(p2_rev[0] - p1[0], p2_rev[1] - p1[1])

                if dist_starts < 100 and dist_ends < 100:
                    # Am găsit contrasensul! Calculăm axul drumului (mijlocul perfect).
                    center_start = ((p1[0] + p2_rev[0]) / 2, (p1[1] + p2_rev[1]) / 2)
                    center_end = ((p2[0] + p1_rev[0]) / 2, (p2[1] + p1_rev[1]) / 2)

                    self.draw_dashed_line_segment(
                        center_start, center_end, COLOR_LINE, offset=0
                    )

                    # Marcăm ambele benzi ca procesate
                    drawn_dashed.add((u, v))
                    drawn_dashed.add((u2, v2))
                    break
        # la finalul draw_environment()
        if self.use_images and hasattr(self, "img_deer"):
            deer_scaled = pygame.transform.scale(self.img_deer, (35, 35))
            for x, y in self.DEER_DECOR_POINTS:
                rect = deer_scaled.get_rect(center=(int(x), int(y)))
                self.screen.blit(deer_scaled, rect)
        else:
            # fallback dacă nu ai imagine
            for x, y in getattr(self, "DEER_DECOR_POINTS", []):
                pygame.draw.circle(self.screen, (139, 69, 19), (int(x), int(y)), 8)

    def draw_traffic_light_agent(self, current_traffic):
        """Semafoare la Intersecția 1 (Stânga-Jos)."""
        sem_data = next(
            (
                v
                for v in current_traffic.values()
                if v.get("agent_id") == "Semafor_Centru"
            ),
            {},
        )
        state_ns = sem_data.get("state_NS", "RED")
        state_ew = sem_data.get("state_EW", "RED")

        def draw_pole(pos, state, orientation, dx=0, dy=0, flip=False):
            if not pos:
                return
            x, y = pos
            x += dx
            y += dy

            box_w, box_h = (22, 60) if orientation == "V" else (60, 22)
            pygame.draw.rect(
                self.screen,
                (30, 30, 30),
                (x - box_w // 2, y - box_h // 2, box_w, box_h),
            )

            r_c, y_c, g_c = (
                self.COLOR_RED_OFF,
                self.COLOR_YELLOW_OFF,
                self.COLOR_GREEN_OFF,
            )
            if not self.system_on:
                if (pygame.time.get_ticks() // 500) % 2 == 0:
                    y_c = COLOR_YELLOW
            else:
                if state == "GREEN":
                    g_c = COLOR_GREEN
                elif state == "RED":
                    r_c = COLOR_RED

            # Ordinea becurilor depinde de flip (doar culorile, nu pozițiile)
            offsets = [-18, 0, 18]
            cols = [r_c, y_c, g_c] if not flip else [g_c, y_c, r_c]
            for i in range(3):
                p = (x, y + offsets[i]) if orientation == "V" else (x + offsets[i], y)
                pygame.draw.circle(self.screen, cols[i], p, 7)

        # Mută semafoarele "în exterior" (dreapta benzii din dreapta, per colț)
        OFFSET_X = 40
        OFFSET_Y = 60

        draw_pole(
            nodes.get("I1_NW"), state_ns, "V", dx=-OFFSET_X, dy=-OFFSET_Y, flip=True
        )
        draw_pole(nodes.get("I1_SE"), state_ns, "V", dx=+OFFSET_X, dy=+OFFSET_Y)
        draw_pole(
            nodes.get("I1_SW"), state_ew, "H", dx=-OFFSET_Y, dy=+OFFSET_X, flip=True
        )
        draw_pole(nodes.get("I1_NE"), state_ew, "H", dx=+OFFSET_Y, dy=-OFFSET_X)

    def draw_button(self):
        # Buton Sistem
        color = (0, 180, 0) if self.system_on else (180, 0, 0)
        pygame.draw.rect(self.screen, color, self.button_rect, border_radius=5)
        text = "SISTEM: ON" if self.system_on else "SISTEM: OFF"
        surf = self.font.render(text, True, (255, 255, 255))
        self.screen.blit(surf, (self.button_rect.x + 15, self.button_rect.y + 10))

        # NOU: Buton Căprioară
        pygame.draw.rect(
            self.screen, (139, 69, 19), self.animal_button_rect, border_radius=5
        )
        text_animal = self.small_font.render("SPAWN CĂPRIOARĂ", True, (255, 255, 255))
        self.screen.blit(
            text_animal,
            (self.animal_button_rect.x + 10, self.animal_button_rect.y + 12),
        )
        # Desenăm butonul de Spawn AI Car
        pygame.draw.rect(
            self.screen, (0, 100, 200), self.spawn_car_button_rect, border_radius=5
        )
        text_spawn = self.small_font.render("🤖 SPAWN AI CAR", True, (255, 255, 255))
        self.screen.blit(
            text_spawn,
            (self.spawn_car_button_rect.x + 15, self.spawn_car_button_rect.y + 12),
        )

    def draw_ai_button(self):
        color = (0, 180, 0) if self.ai_enabled else (180, 0, 0)
        pygame.draw.rect(self.screen, color, self.ai_button_rect, border_radius=5)
        text = "AI: ON" if self.ai_enabled else "AI: OFF"
        surf = self.font.render(text, True, (255, 255, 255))
        self.screen.blit(surf, (self.ai_button_rect.x + 40, self.ai_button_rect.y + 10))

    def render_vehicle(self, v_data):
        v_id = v_data.get("agent_id", "?")
        if v_id == "Semafor_Centru":
            return

        x, y = v_data.get("position_x", 0), v_data.get("position_y", 0)
        v_type = v_data.get("vehicle_type", "Normal")

        # NOU: Verificăm dacă mașina este "Crashed" (lovită)
        is_crashed = v_data.get("is_crashed", False)

        # DESENEAZĂ EFECTUL DE EXPLOZIE DACĂ E CRASHED
        if is_crashed:
            # Cerc portocaliu-roșiatic sub mașină pentru a arăta accidentul
            pygame.draw.circle(self.screen, (255, 69, 0), (int(x), int(y)), 25)
            pygame.draw.circle(self.screen, (200, 0, 0), (int(x), int(y)), 15)

        # ==========================================
        # NOU: Desenăm Căprioara (Imaginea)
        # ==========================================
        if v_type == "Animal":
            if self.use_images and hasattr(self, "img_deer"):
                # Scalăm poza căprioarei ca să nu fie uriașă
                deer_scaled = pygame.transform.scale(self.img_deer, (35, 35))
                rect = deer_scaled.get_rect(center=(int(x), int(y)))
                self.screen.blit(deer_scaled, rect)
            else:
                # Dacă nu găsește poza din vreo eroare, pune un cerculeț maro
                pygame.draw.circle(self.screen, (139, 69, 19), (int(x), int(y)), 10)

            # Scriem numele "Căprioară" deasupra ei
            animal_text = self.small_font.render(v_id, True, (255, 150, 150))
            self.screen.blit(animal_text, (int(x) - 25, int(y) - 30))
            return

        exact_angle = v_data.get("visual_angle", 0.0)
        intent = v_data.get("intent", "IDLE")
        speed = v_data.get("speed", 0)
        priority = v_data.get("priority_active", False)
        heading = v_data.get("heading", "EAST")  # Fallback for old mode

        w, h = 45, 28

        if self.use_images:
            base_img = self.img_ambulance if v_type == "Ambulance" else self.img_normal
            base_img = pygame.transform.scale(base_img, (w, h))

            angle_to_draw = -exact_angle
            rotated_img = pygame.transform.rotate(base_img, angle_to_draw)
            rect = rotated_img.get_rect(center=(int(x), int(y)))
            self.screen.blit(rotated_img, rect)
        else:
            color = COLOR_AMBULANCE_CAR if v_type == "Ambulance" else COLOR_NORMAL_CAR
            vw, vh = (w, h) if exact_angle == 0 or exact_angle == 180 else (h, w)
            pygame.draw.rect(
                self.screen, color, (int(x) - vw // 2, int(y) - vh // 2, vw, vh)
            )

        if priority and (pygame.time.get_ticks() // 200) % 2 == 0:
            pygame.draw.circle(self.screen, (255, 255, 255), (int(x), int(y)), 35, 2)

        id_s = self.font.render(v_id, True, COLOR_TEXT)
        in_s = self.small_font.render(f"[{intent}]", True, COLOR_TEXT)
        sp_s = self.small_font.render(f"V: {speed:.1f}", True, COLOR_TEXT)

        self.screen.blit(id_s, (int(x) - 20, int(y) - 45))
        self.screen.blit(in_s, (int(x) - 20, int(y) - 60))
        self.screen.blit(sp_s, (int(x) - 20, int(y) + 25))

    def start(self, broker):
        running = True
        print("Simularea UI a început. Harta rețea (grilă).")

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)

                # REPARAT: Închidere și pe butonul ESCAPE de pe tastatură
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit(0)

                if event.type == pygame.MOUSEBUTTONDOWN:
                    # 1. Click pe butonul SISTEM
                    if self.button_rect.collidepoint(event.pos):
                        self.system_on = not self.system_on
                        if hasattr(broker, "infrastructure_active"):
                            broker.infrastructure_active = self.system_on

                    # 2. Click pe butonul SPAWN AI CAR
                    elif self.spawn_car_button_rect.collidepoint(event.pos):
                        if hasattr(broker, "trigger_spawn_car"):
                            broker.trigger_spawn_car()

                    # 3. NOU REPARAT: Click pe butonul AI ON/OFF
                    elif self.ai_button_rect.collidepoint(event.pos):
                        self.ai_enabled = not self.ai_enabled
                        if hasattr(broker, "ai_enabled"):
                            broker.ai_enabled = self.ai_enabled

                    # 4. Click pe butonul CĂPRIOARĂ
                    elif self.animal_button_rect.collidepoint(event.pos):
                        if hasattr(broker, "trigger_animal_event"):
                            broker.trigger_animal_event()

            self.draw_environment()
            self.draw_button()
            self.draw_ai_button()
            self.draw_indicator()

            with broker.lock:
                to_remove = [
                    k
                    for k, v in broker.vehicles_status.items()
                    if self.is_outside_bounds(v)
                ]
                for k in to_remove:
                    del broker.vehicles_status[k]
                current_traffic = broker.vehicles_status.copy()

            self.draw_risk_overlays(current_traffic)
            self.draw_traffic_light_agent(current_traffic)

            for v_data in current_traffic.values():
                self.render_vehicle(v_data)

            pygame.display.flip()
            self.clock.tick(self.fps)
        pygame.quit()
        sys.exit(0)


if __name__ == "__main__":

    class DummyBroker:
        def __init__(self):
            self.vehicles_status = {}
            self.lock = type(
                "obj",
                (object,),
                {"__enter__": lambda s: None, "__exit__": lambda s, x, y, z: None},
            )()

    SimulationUI().start(DummyBroker())
