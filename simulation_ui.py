import pygame
import sys
import json

# --- CONFIGURAȚII ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 800
ROAD_WIDTH = 100
INTERSECTION_CENTER_X = SCREEN_WIDTH // 2
INTERSECTION_CENTER_Y = SCREEN_HEIGHT // 2

# CULORI DEFINITE DE TINE
COLOR_BACKGROUND = (0, 0, 0)
COLOR_ROAD = (255, 255, 255)
COLOR_WALL = (160, 160, 160)
COLOR_TEXT_ALL = (102, 178, 255)  # Culoarea cerută pentru tot textul
COLOR_NORMAL_CAR = (153, 153, 255)  # Culoarea cerută pentru mașini normale
COLOR_AMBULANCE_CAR = (204, 0, 0)  # Culoarea cerută pentru ambulanță


class SimulationUI:
    def __init__(self, title="V2X Intersection Scenario Player"):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        # Fonturile folosesc culoarea ta (102, 178, 255)
        self.font = pygame.font.SysFont("timesnewroman", 18, bold=True)
        self.small_font = pygame.font.SysFont("timesnewroman", 14)
        self.fps = 60  # Setează viteza de redare a scenariului

    def draw_environment(self):
        """Desenează intersecția și zidurile tale originale."""
        self.screen.fill(COLOR_BACKGROUND)

        # Drum Orizontal
        pygame.draw.rect(
            self.screen,
            COLOR_ROAD,
            (0, INTERSECTION_CENTER_Y - ROAD_WIDTH // 2, SCREEN_WIDTH, ROAD_WIDTH),
        )
        # Drum Vertical
        pygame.draw.rect(
            self.screen,
            COLOR_ROAD,
            (INTERSECTION_CENTER_X - ROAD_WIDTH // 2, 0, ROAD_WIDTH, SCREEN_HEIGHT),
        )

        # ZIDUL 1 (Coordonatele tale)
        wall_rect = pygame.Rect(
            INTERSECTION_CENTER_X - ROAD_WIDTH // 2 - 200,
            INTERSECTION_CENTER_Y - ROAD_WIDTH // 2 - 100,
            200,
            100,
        )
        pygame.draw.rect(self.screen, COLOR_WALL, wall_rect)

        # ZIDUL 2 (Coordonatele tale)
        wall_rect_2 = pygame.Rect(
            INTERSECTION_CENTER_X + ROAD_WIDTH // 2,
            INTERSECTION_CENTER_Y + ROAD_WIDTH // 2,
            100,
            200,
        )
        pygame.draw.rect(self.screen, COLOR_WALL, wall_rect_2)

    def render_vehicle(self, v_data):
        """Afișează mașina conform datelor primite (cu protecție la chei lipsă)."""
        x = v_data.get("position_x", 0)
        y = v_data.get("position_y", 0)
        v_type = v_data.get("vehicle_type", "Normal")

        # Dacă 'heading' lipsește, presupunem că merge spre NORD (nu mai dă eroare)
        heading = v_data.get("heading", "NORTH")

        v_id = v_data.get("agent_id", "Unknown")
        intent = v_data.get("intent", "IDLE")
        priority = v_data.get("priority_active", False)
        # ... restul funcției rămâne la fel ...

        # 1. Culoarea mașinii: Ambulanță (204,0,0) vs Normală (153,153,255)
        color = COLOR_AMBULANCE_CAR if v_type == "Ambulance" else COLOR_NORMAL_CAR

        # 2. Forma mașinii (Heading):
        # Dacă merge NORTH/SOUTH e verticală (|), dacă merge EAST/WEST e orizontală (--)
        if heading in ["NORTH", "SOUTH"]:
            width, height = 28, 48
        else:
            width, height = 48, 28

        # 3. Desenare Mașină
        rect = pygame.Rect(x - width // 2, y - height // 2, width, height)
        pygame.draw.rect(self.screen, color, rect)

        # 4. Efect Prioritate Activă (Sirenă)
        if priority and (pygame.time.get_ticks() // 250) % 2 == 0:
            # Contur de evidențiere (folosim alb pentru contrast la sirenă)
            pygame.draw.rect(self.screen, (255, 255, 255), rect, 3)

        # 5. Randare Text cu culoarea (102, 178, 255)
        id_surf = self.font.render(v_id, True, COLOR_TEXT_ALL)
        intent_surf = self.small_font.render(f"[{intent}]", True, COLOR_TEXT_ALL)

        speed_surf = self.small_font.render(
            f"V: {v_data.get('speed', 0):.1f} px/s", True, COLOR_TEXT_ALL
        )
        self.screen.blit(speed_surf, (x - 20, y + height // 2 + 5))

        # Poziționare text
        self.screen.blit(id_surf, (x - 20, y - height // 2 - 20))
        self.screen.blit(intent_surf, (x - 20, y - height // 2 - 35))

    def start(self, broker):  # Primim broker-ul, NU fisierul JSON
        """Citește datele LIVE din brokerul V2X și le desenează."""
        running = True
        print("Simularea UI a început. Ascultăm rețeaua V2X...")

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            self.draw_environment()

            # --- PARTEA CRITICĂ: Citim starea actuală a tuturor mașinilor din rețea ---
            # Folosim un 'receive' special sau accesăm direct statusul (fiind în același proces)
            with broker.lock:
                current_traffic = broker.vehicles_status.copy()

            # Desenăm fiecare mașină care este activă în rețea în acest moment
            for v_id, v_data in current_traffic.items():
                self.render_vehicle(v_data)

            pygame.display.flip()
            self.clock.tick(60)  # UI-ul poate rula la 60 FPS pentru fluiditate

        pygame.quit()


# ===== EXECUTARE =====
if __name__ == "__main__":
    ui = SimulationUI()
    # Asigură-te că fișierul se numește exact 'scenariu.json' și este în același folder
    ui.start("scenariu.json")
