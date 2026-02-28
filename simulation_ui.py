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


class SimulationUI:
    def __init__(self, title="V2X Multi-Lane Simulator"):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("timesnewroman", 16, bold=True)
        self.small_font = pygame.font.SysFont("timesnewroman", 13)
        self.fps = 30

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

    def render_vehicle(self, v_data):
        v_type = v_data.get("vehicle_type", "Normal")
        x, y = v_data.get("position_x", 0), v_data.get("position_y", 0)
        heading = v_data.get("heading", "EAST")
        v_id = v_data.get("agent_id", "?")
        intent = v_data.get("intent", "IDLE")
        speed = v_data.get("speed", 0)

        # --- 1. DESENARE SEMAFOR (V2I) ---
        if v_type == "Infrastructure":
            # Indicator Nord-Sud
            color_ns = (0, 255, 0) if v_data.get("state_NS") == "GREEN" else (255, 0, 0)
            pygame.draw.circle(self.screen, color_ns, (int(x), int(y) - 50), 10)
            # Indicator Est-Vest
            color_ew = (0, 255, 0) if v_data.get("state_EW") == "GREEN" else (255, 0, 0)
            pygame.draw.circle(self.screen, color_ew, (int(x) - 50, int(y)), 10)
            return  # Ieșim, restul funcției e doar pentru mașini

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
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            self.draw_environment()

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

            # Desenăm fiecare mașină/semafor care este în rețea
            for v_id, v_data in current_traffic.items():
                self.render_vehicle(v_data)

            pygame.display.flip()
            self.clock.tick(60)  # Simularea UI la 60 FPS pentru fluiditate

        pygame.quit()


if __name__ == "__main__":
    SimulationUI().start("scenariu.json")
