import pygame
import sys
import json

# --- CONFIGURAȚII ---
SCREEN_WIDTH = 1500
SCREEN_HEIGHT = 800
ROAD_WIDTH = 80  # Lățime totală drum (40px per bandă)

# Centrele axelor
INT_1_X = 400
INT_2_X = 1100
INTERSECTION_CENTER_Y = 400

# CULORI
COLOR_BACKGROUND = (0, 0, 0)
COLOR_ROAD = (50, 50, 50)  # Gri închis pentru asfalt
COLOR_LINE = (255, 255, 255)  # Alb pentru marcaje
COLOR_WALL = (160, 160, 160)
COLOR_TEXT = (102, 178, 255)
COLOR_NORMAL_CAR = (153, 153, 255)
COLOR_AMBULANCE_CAR = (204, 0, 0)
COLOR_RED = (255, 0, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_YELLOW = (255, 165, 0)
COLOR_OFF = (40, 40, 40)


class SimulationUI:
    def __init__(self, title="V2X Multi-Lane Simulator"):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("timesnewroman", 16, bold=True)
        self.small_font = pygame.font.SysFont("timesnewroman", 13)
        self.fps = 30
        self.system_on = True  # Starea sistemului de semaforizare
        self.button_rect = pygame.Rect(20, 20, 150, 40)
        self.COLOR_RED_OFF = (60, 0, 0)
        self.COLOR_YELLOW_OFF = (60, 60, 0)
        self.COLOR_GREEN_OFF = (0, 60, 0)
        self.COLOR_BLACK_BOX = (30, 30, 30)

        try:
            self.img_normal = pygame.image.load("car.png").convert_alpha()
            self.img_ambulance = pygame.image.load("ambulance.png").convert_alpha()
            # Scalare mașini să încapă bine pe banda de 40px
            self.img_normal = pygame.transform.scale(self.img_normal, (45, 25))
            self.img_ambulance = pygame.transform.scale(self.img_ambulance, (45, 25))
            self.use_images = True
        except Exception as e:
            print(f"Atenție: Imagini negăsite. Folosesc dreptunghiuri.")
            self.use_images = False

        self.rotation_map = {"EAST": 0, "NORTH": 90, "WEST": 180, "SOUTH": 270}

    def is_outside_bounds(self, v_data):
        """Returnează True dacă vehiculul a ieșit din cadru pe baza position_x/position_y."""
        if v_data.get("vehicle_type") == "Infrastructure":
            return False

        x = v_data.get("position_x", 0)
        y = v_data.get("position_y", 0)

        return x < 0 or x > SCREEN_WIDTH or y < 0 or y > SCREEN_HEIGHT

    def draw_dashed_line(self, start_pos, end_pos, vertical=False):
        """Funcție pentru a desena linia punctată de separare a benzilor."""
        dist = 20
        for i in range(start_pos, end_pos, dist * 2):
            if vertical:
                pygame.draw.line(
                    self.screen, COLOR_LINE, (INT_1_X, i), (INT_1_X, i + dist), 1
                )
                pygame.draw.line(
                    self.screen, COLOR_LINE, (INT_2_X, i), (INT_2_X, i + dist), 1
                )
            else:
                pygame.draw.line(
                    self.screen,
                    COLOR_LINE,
                    (i, INTERSECTION_CENTER_Y),
                    (i + dist, INTERSECTION_CENTER_Y),
                    1,
                )

    def draw_environment(self):
        """Desenează intersecția și zidurile tale originale."""
        self.screen.fill(COLOR_BACKGROUND)

        # --- DESENARE ASFALT ---
        # Drum Orizontal
        pygame.draw.rect(
            self.screen,
            COLOR_ROAD,
            (0, INTERSECTION_CENTER_Y - ROAD_WIDTH // 2, SCREEN_WIDTH, ROAD_WIDTH),
        )
        # Drum Vertical 1
        pygame.draw.rect(
            self.screen,
            COLOR_ROAD,
            (INT_1_X - ROAD_WIDTH // 2, 0, ROAD_WIDTH, SCREEN_HEIGHT),
        )
        # Drum Vertical 2
        pygame.draw.rect(
            self.screen,
            COLOR_ROAD,
            (INT_2_X - ROAD_WIDTH // 2, 0, ROAD_WIDTH, SCREEN_HEIGHT),
        )

        # --- MARCAJE BENZI (Linii punctate pe mijloc) ---
        self.draw_dashed_line(0, SCREEN_WIDTH, vertical=False)
        self.draw_dashed_line(0, SCREEN_HEIGHT, vertical=True)

        # --- ZIDURI ORIGINALE ---
        # Zid Intersecție 1
        pygame.draw.rect(
            self.screen,
            COLOR_WALL,
            (INT_1_X - 240, INTERSECTION_CENTER_Y - 140, 200, 100),
        )
        pygame.draw.rect(
            self.screen,
            COLOR_WALL,
            (INT_1_X + 40, INTERSECTION_CENTER_Y + 40, 100, 200),
        )
        # Zid Intersecție 2
        pygame.draw.rect(
            self.screen,
            COLOR_WALL,
            (INT_2_X - 240, INTERSECTION_CENTER_Y - 140, 200, 100),
        )

    def draw_button(self):
        """Desenează butonul de control al sistemului."""
        color = (0, 180, 0) if self.system_on else (180, 0, 0)
        pygame.draw.rect(self.screen, color, self.button_rect, border_radius=5)
        text = "SISTEM: ON" if self.system_on else "SISTEM: OFF"
        surf = self.font.render(text, True, (255, 255, 255))
        self.screen.blit(surf, (self.button_rect.x + 20, self.button_rect.y + 10))

    def draw_traffic_light_agent(self, current_traffic):
        """Desenează semafoare cu 3 becuri. 'flip' inversează ordinea culorilor."""
        cx, cy = 400, 400
        stop_dist = 80 
        offset = 65    

        # Date de la Broker
        sem_data = next(
            (
                v
                for v in current_traffic.values()
                if v.get("agent_id") == "Semafor_Centru"
            ),
            {},
        )

        # Stări
        state_ns = sem_data.get("state_NS", "RED")
        state_ew = sem_data.get("state_EW", "RED")

        def draw_pole(x, y, state, orientation="V", flip=False):
            # Cutia semaforului
            box_w, box_h = (22, 60) if orientation == "V" else (60, 22)
            pygame.draw.rect(self.screen, (20, 20, 20), (x - box_w//2, y - box_h//2, box_w, box_h))
            pygame.draw.rect(self.screen, (100, 100, 100), (x - box_w//2, y - box_h//2, box_w, box_h), 1) # Contur
            
            # Culori becuri
            r_col = COLOR_RED if state == "RED" and self.system_on else (60, 0, 0)
            y_col = (60, 60, 0)
            g_col = COLOR_GREEN if state == "GREEN" and self.system_on else (0, 60, 0)
            
            if not self.system_on and (pygame.time.get_ticks() // 500) % 2 == 0:
                y_col = COLOR_YELLOW

            # Calculăm pozițiile becurilor (inversăm dacă flip=True)
            if orientation == "V":
                # Sus/Jos
                pos_top = (x, y - 18) if not flip else (x, y + 18)
                pos_bot = (x, y + 18) if not flip else (x, y - 18)
                pygame.draw.circle(self.screen, r_col, pos_top, 7)
                pygame.draw.circle(self.screen, y_col, (x, y), 7)
                pygame.draw.circle(self.screen, g_col, pos_bot, 7)
            else:
                # Stânga/Dreapta
                pos_left = (x - 18, y) if not flip else (x + 18, y)
                pos_right = (x + 18, y) if not flip else (x - 18, y)
                pygame.draw.circle(self.screen, r_col, pos_left, 7)
                pygame.draw.circle(self.screen, y_col, (x, y), 7)
                pygame.draw.circle(self.screen, g_col, pos_right, 7)

        # --- AMPLASARE CU ORDINE CORECTATĂ ---
        
        # 1. NORD (Intrare de sus): Inversăm ordinea ca Verdele să fie "mai aproape" de intersecție
        draw_pole(INT_1_X - offset, INTERSECTION_CENTER_Y - stop_dist, state_ns, "V", flip=True)
        
        # 2. SUD (Intrare de jos): Ordine normală (Roșu sus, Verde jos)
        draw_pole(INT_1_X + offset, INTERSECTION_CENTER_Y + stop_dist, state_ns, "V", flip=False)
        
        # 3. VEST (Intrare din stânga): Inversăm ca Verdele să fie spre dreapta (spre intersecție)
        draw_pole(INT_1_X - stop_dist, INTERSECTION_CENTER_Y + offset, state_ew, "H", flip=True)
        
        # 4. EST (Intrare din dreapta): Ordine normală (Roșu stânga, Verde dreapta)
        draw_pole(INT_1_X + stop_dist, INTERSECTION_CENTER_Y - offset, state_ew, "H", flip=False)

    def render_vehicle(self, v_data):
        v_id = v_data.get("agent_id", "?")
        if v_id == "Semafor_Centru" or v_data.get("vehicle_type") == "Infrastructure":
            return
        v_type = v_data.get("vehicle_type", "Normal")
        x, y = v_data.get("position_x", 0), v_data.get("position_y", 0)
        heading = v_data.get("heading", "EAST")
        v_id = v_data.get("agent_id", "?")
        intent = v_data.get("intent", "IDLE")
        speed = v_data.get("speed", 0)

        # --- 2. DESENARE MAȘINĂ (V2V) ---
        if self.use_images:
            # Folosim imaginile încărcate (car.png / ambulance.png)
            base_img = self.img_ambulance if v_type == "Ambulance" else self.img_normal
            # Rotim imaginea în funcție de direcție (heading)
            angle = self.rotation_map.get(heading, 0)
            rotated_img = pygame.transform.rotate(base_img, angle)
            rect = rotated_img.get_rect(center=(int(x), int(y)))
            self.screen.blit(rotated_img, rect)
        else:
            # Dacă imaginile lipsesc, desenăm dreptunghiuri colorate
            color = COLOR_AMBULANCE_CAR if v_type == "Ambulance" else COLOR_NORMAL_CAR
            # Ajustăm mărimea în funcție de orientare
            if heading in ["NORTH", "SOUTH"]:
                rect_w, rect_h = 25, 45
            else:
                rect_w, rect_h = 45, 25
            pygame.draw.rect(
                self.screen,
                color,
                (int(x) - rect_w // 2, int(y) - rect_h // 2, rect_w, rect_h),
            )

        # --- 3. AFIȘARE TEXT INFORMATIV ---
        id_s = self.font.render(v_id, True, COLOR_TEXT)
        in_s = self.small_font.render(f"[{intent}]", True, COLOR_TEXT)
        sp_s = self.small_font.render(f"V: {speed:.1f} px/s", True, COLOR_TEXT)

        # Poziționăm textul deasupra și dedesubtul mașinii
        self.screen.blit(id_s, (int(x) - 20, int(y) - 45))
        self.screen.blit(in_s, (int(x) - 20, int(y) - 60))
        self.screen.blit(sp_s, (int(x) - 20, int(y) + 25))

    def start(self, broker):  # <--- Schimbat din scenario_file în broker
        """Citește datele LIVE din brokerul V2X și le desenează."""
        running = True
        print("Simularea UI a început. Ascultăm rețeaua V2X LIVE...")

        while running:
            # --- GESTIONARE EVENIMENTE ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                # Verificăm dacă s-a apăsat mouse-ul
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # VERIFICĂM DACĂ CLICK-UL A FOST PE BUTON
                    if self.button_rect.collidepoint(event.pos):
                        self.system_on = not self.system_on
                        
                        # TRIMITEM SEMNALUL CĂTRE LOGICA COLEGULUI (BROKER)
                        if hasattr(broker, 'infrastructure_active'):
                            broker.infrastructure_active = self.system_on
                        
                        print(f"Sistem V2I schimbat în: {'ON' if self.system_on else 'OFF'}")

                        broker.infrastructure_active = self.system_on

            self.draw_environment()
            self.draw_button()

            # --- CITIM DATELE LIVE DIN BROKER ---
            with broker.lock:
                vehicles_to_remove = [
                    v_id
                    for v_id, v_data in broker.vehicles_status.items()
                    if self.is_outside_bounds(v_data)
                ]

                for v_id in vehicles_to_remove:
                    del broker.vehicles_status[v_id]

                # Facem o copie a statusului mașinilor din rețea
                current_traffic = broker.vehicles_status.copy()

            self.draw_traffic_light_agent(current_traffic)

            # Desenăm fiecare mașină/semafor care este în rețea
            for v_id, v_data in current_traffic.items():
                self.render_vehicle(v_data)

            pygame.display.flip()
            self.clock.tick(60)  # Simularea UI la 60 FPS pentru fluiditate

        pygame.quit()


if __name__ == "__main__":
    SimulationUI().start("scenariu.json")
