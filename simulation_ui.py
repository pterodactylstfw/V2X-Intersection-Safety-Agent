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

        self.COLOR_RED_OFF = (60, 0, 0)
        self.COLOR_YELLOW_OFF = (60, 60, 0)
        self.COLOR_GREEN_OFF = (0, 60, 0)

        try:
            self.img_normal = pygame.image.load("car.png").convert_alpha()
            self.img_ambulance = pygame.image.load("ambulance.png").convert_alpha()
            self.use_images = True
        except Exception as e:
            print(f"Imagini negăsite. Folosesc forme geometrice. Eroare: {e}")
            self.use_images = False

        self.rotation_map = {"EAST": 0, "NORTH": 90, "WEST": 180, "SOUTH": 270}

    def is_outside_bounds(self, v_data):
        if v_data.get("vehicle_type") == "Infrastructure":
            return False
        x, y = v_data.get("position_x", 0), v_data.get("position_y", 0)
        return x < -50 or x > SCREEN_WIDTH + 50 or y < -50 or y > SCREEN_HEIGHT + 50

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

    def draw_environment(self):
        """Desenează harta curățată și corectată."""
        self.screen.fill(COLOR_BACKGROUND)

        # Funcție inteligentă pentru a detecta dacă drumul e secundar
        def is_main_segment(n1, n2):
            secondary_keywords = ["NW_", "NE_", "I3_", "I4_", "DIAG", "MERGE"]
            for kw in secondary_keywords:
                if kw in n1 or kw in n2:
                    return False
            return True  # Dacă nu e secundar, sigur e drumul principal

        # 1. STRATUL ASFALT (Linii groase și Pătrate la îmbinări)
        for start_id, end_id, _ in edges:
            p1 = nodes.get(start_id)
            p2 = nodes.get(end_id)

            if p1 and p2:
                width = (
                    ROAD_WIDTH_MAIN
                    if is_main_segment(start_id, end_id)
                    else ROAD_WIDTH_SECONDARY
                )

                pygame.draw.line(self.screen, COLOR_ROAD, p1, p2, width)

        # 2. STRATUL MARCAJE (Linii albe - punctate)
        for start_id, end_id, _ in edges:
            p1 = nodes.get(start_id)
            p2 = nodes.get(end_id)

            if p1 and p2:
                is_main = is_main_segment(start_id, end_id)
                # Nu desenăm marcaje în intersecția de Merge I4
                is_i4_related = (
                    "I4_" in start_id
                    or "I4_" in end_id
                    or "MERGE_POINT" in start_id
                    or "MERGE_POINT" in end_id
                )

                if is_main:
                    # Drum principal (2 benzi = offset de 20)
                    offset = ROAD_WIDTH_MAIN // 4
                    self.draw_dashed_line_segment(p1, p2, COLOR_LINE, offset=offset)
                    self.draw_dashed_line_segment(p1, p2, COLOR_LINE, offset=-offset)
                elif not is_i4_related:
                    # Drum secundar (1 bandă pe mijloc)
                    self.draw_dashed_line_segment(p1, p2, COLOR_LINE, offset=0)

        # 3. DESENARE CLĂDIRI (Ajustate ca să nu cadă pe drumurile diagonale)
        # pygame.draw.rect(
        #    self.screen, COLOR_WALL, (50, 50, 200, 150)
        # )  # Clădire Stânga-Sus
        # pygame.draw.rect(
        #     self.screen, COLOR_WALL, (50, 400, 200, 150)
        # )  # Clădire Centrală-Stânga
        # pygame.draw.rect(
        #     self.screen, COLOR_WALL, (1200, 710, 250, 80)
        # )  # Clădire Dreapta-Jos
        # pygame.draw.rect(
        #     self.screen, COLOR_WALL, (1150, 100, 250, 300)
        # )  # Clădire Sus-Dreapta (lângă I2/I4)

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

        def draw_pole(pos, state, orientation, flip):
            if not pos:
                return
            x, y = pos
            offset = 55
            if orientation == "V":
                x = x + offset if flip else x - offset
            else:
                y = y - offset if flip else y + offset

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

            offsets = [-18, 0, 18] if not flip else [18, 0, -18]
            cols = [r_c, y_c, g_c]
            for i in range(3):
                p = (x, y + offsets[i]) if orientation == "V" else (x + offsets[i], y)
                pygame.draw.circle(self.screen, cols[i], p, 7)

        # REPARAT: Folosim numele corecte din map_config.py (_STOP)
        draw_pole(nodes.get("I1_NW"), state_ns, "V", True)  # Sus-Stânga
        draw_pole(nodes.get("I1_SE"), state_ns, "V", False)  # Jos-Dreapta
        draw_pole(nodes.get("I1_SW"), state_ew, "H", False)  # Jos-Stânga
        draw_pole(nodes.get("I1_NE"), state_ew, "H", True)

    def draw_button(self):
        color = (0, 180, 0) if self.system_on else (180, 0, 0)
        pygame.draw.rect(self.screen, color, self.button_rect, border_radius=5)
        text = "SISTEM: ON" if self.system_on else "SISTEM: OFF"
        surf = self.font.render(text, True, (255, 255, 255))
        self.screen.blit(surf, (self.button_rect.x + 15, self.button_rect.y + 10))

    def render_vehicle(self, v_data):
        v_id = v_data.get("agent_id", "?")
        if v_id == "Semafor_Centru":
            return

        x, y = v_data.get("position_x", 0), v_data.get("position_y", 0)
        v_type = v_data.get("vehicle_type", "Normal")

        # NOU: Citim unghiul vizual continuu trimis de agent (Default 0.0)
        exact_angle = v_data.get("visual_angle", 0.0)

        intent = v_data.get("intent", "IDLE")
        speed = v_data.get("speed", 0)
        priority = v_data.get("priority_active", False)

        # Dimensiunile standard ale mașinii (lățime, înălțime) când heading e EST (0 grade)
        w, h = 45, 28

        if self.use_images:
            # Alegem imaginea de bază (Ambulantă sau Normală) orientată spre EST
            base_img = self.img_ambulance if v_type == "Ambulance" else self.img_normal
            # O scalăm la dimensiunile corecte
            base_img = pygame.transform.scale(base_img, (w, h))

            # --- REPARARE ROTATIE: Folosim Rotația Continuă ---
            # Pygame rotește în sens trigonometric invers (counter-clockwise).
            # Deoarece sistemul de coordonate al ecranului are Y-ul în jos,
            # math.atan2 funcționează corect, dar trebuie să inversăm unghiul pentru desenare.

            angle_to_draw = -exact_angle

            # Rotim imaginea cu unghiul precis
            rotated_img = pygame.transform.rotate(base_img, angle_to_draw)

            # Obținem noul rect centralizat (deoarece imaginea rotită își schimbă mărimea)
            rect = rotated_img.get_rect(center=(int(x), int(y)))

            # Desenăm imaginea rotită fluid pe ecran
            self.screen.blit(rotated_img, rect)
        else:
            color = COLOR_AMBULANCE_CAR if v_type == "Ambulance" else COLOR_NORMAL_CAR
            vw, vh = (w, h) if heading in ["EAST", "WEST"] else (h, w)
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
                    running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.button_rect.collidepoint(event.pos):
                        self.system_on = not self.system_on
                        if hasattr(broker, "infrastructure_active"):
                            broker.infrastructure_active = self.system_on

            self.draw_environment()
            self.draw_button()

            with broker.lock:
                to_remove = [
                    k
                    for k, v in broker.vehicles_status.items()
                    if self.is_outside_bounds(v)
                ]
                for k in to_remove:
                    del broker.vehicles_status[k]
                current_traffic = broker.vehicles_status.copy()

            self.draw_traffic_light_agent(current_traffic)

            for v_data in current_traffic.values():
                self.render_vehicle(v_data)

            pygame.display.flip()
            self.clock.tick(self.fps)
        pygame.quit()


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
