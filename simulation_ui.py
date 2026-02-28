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
COLOR_ROAD = (50, 50, 50)          # Gri închis pentru asfalt
COLOR_LINE = (255, 255, 255)       # Alb pentru marcaje
COLOR_WALL = (160, 160, 160)
<<<<<<< HEAD
COLOR_TEXT = (102, 178, 255)       
COLOR_NORMAL_CAR = (153, 153, 255)    
COLOR_AMBULANCE_CAR = (204, 0, 0)      
=======
COLOR_TEXT_ALL = (102, 178, 255)  # Culoarea cerută pentru tot textul
COLOR_NORMAL_CAR = (153, 153, 255)  # Culoarea cerută pentru mașini normale
COLOR_AMBULANCE_CAR = (204, 0, 0)  # Culoarea cerută pentru ambulanță

>>>>>>> 4cbaa5a8598e7b5ce2f66d82e9a536e186924d4a

class SimulationUI:
    def __init__(self, title="V2X Multi-Lane Simulator"):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
<<<<<<< HEAD
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

    def draw_dashed_line(self, start_pos, end_pos, vertical=False):
        """Funcție pentru a desena linia punctată de separare a benzilor."""
        dist = 20
        for i in range(start_pos, end_pos, dist * 2):
            if vertical:
                pygame.draw.line(self.screen, COLOR_LINE, (INT_1_X, i), (INT_1_X, i + dist), 1)
                pygame.draw.line(self.screen, COLOR_LINE, (INT_2_X, i), (INT_2_X, i + dist), 1)
            else:
                pygame.draw.line(self.screen, COLOR_LINE, (i, INTERSECTION_CENTER_Y), (i + dist, INTERSECTION_CENTER_Y), 1)
=======
        # Fonturile folosesc culoarea ta (102, 178, 255)
        self.font = pygame.font.SysFont("timesnewroman", 18, bold=True)
        self.small_font = pygame.font.SysFont("timesnewroman", 14)
        self.fps = 60  # Setează viteza de redare a scenariului
>>>>>>> 4cbaa5a8598e7b5ce2f66d82e9a536e186924d4a

    def draw_environment(self):
        """Desenează intersecția și zidurile tale originale."""
        self.screen.fill(COLOR_BACKGROUND)
<<<<<<< HEAD
        
        # --- DESENARE ASFALT ---
        # Drum Orizontal
        pygame.draw.rect(self.screen, COLOR_ROAD, (0, INTERSECTION_CENTER_Y - ROAD_WIDTH//2, SCREEN_WIDTH, ROAD_WIDTH))
        # Drum Vertical 1
        pygame.draw.rect(self.screen, COLOR_ROAD, (INT_1_X - ROAD_WIDTH//2, 0, ROAD_WIDTH, SCREEN_HEIGHT))
        # Drum Vertical 2
        pygame.draw.rect(self.screen, COLOR_ROAD, (INT_2_X - ROAD_WIDTH//2, 0, ROAD_WIDTH, SCREEN_HEIGHT))

        # --- MARCAJE BENZI (Linii punctate pe mijloc) ---
        self.draw_dashed_line(0, SCREEN_WIDTH, vertical=False)
        self.draw_dashed_line(0, SCREEN_HEIGHT, vertical=True)
        
        # --- ZIDURI ORIGINALE ---
        # Zid Intersecție 1
        pygame.draw.rect(self.screen, COLOR_WALL, (INT_1_X - 240, INTERSECTION_CENTER_Y - 140, 200, 100))
        pygame.draw.rect(self.screen, COLOR_WALL, (INT_1_X + 40, INTERSECTION_CENTER_Y + 40, 100, 200))
        # Zid Intersecție 2
        pygame.draw.rect(self.screen, COLOR_WALL, (INT_2_X - 240, INTERSECTION_CENTER_Y - 140, 200, 100))
=======

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
>>>>>>> 4cbaa5a8598e7b5ce2f66d82e9a536e186924d4a

    def render_vehicle(self, v_data):
        x, y = v_data.get("position_x", 0), v_data.get("position_y", 0)
        v_type = v_data.get("vehicle_type", "Normal")
<<<<<<< HEAD
        heading = v_data.get("heading", "EAST")
        v_id, intent, speed = v_data.get("agent_id", "?"), v_data.get("intent", "IDLE"), v_data.get("speed", 0)
=======

        # Dacă 'heading' lipsește, presupunem că merge spre NORD (nu mai dă eroare)
        heading = v_data.get("heading", "NORTH")

        v_id = v_data.get("agent_id", "Unknown")
        intent = v_data.get("intent", "IDLE")
        priority = v_data.get("priority_active", False)
        # ... restul funcției rămâne la fel ...
>>>>>>> 4cbaa5a8598e7b5ce2f66d82e9a536e186924d4a

        if self.use_images:
            base_img = self.img_ambulance if v_type == "Ambulance" else self.img_normal
            rotated_img = pygame.transform.rotate(base_img, self.rotation_map.get(heading, 0))
            rect = rotated_img.get_rect(center=(x, y))
            self.screen.blit(rotated_img, rect)
        else:
            color = COLOR_AMBULANCE_CAR if v_type == "Ambulance" else COLOR_NORMAL_CAR
            w, h = (40, 20) if heading in ["EAST", "WEST"] else (20, 40)
            pygame.draw.rect(self.screen, color, (x - w//2, y - h//2, w, h))

<<<<<<< HEAD
        # Text informații
        id_s = self.font.render(v_id, True, COLOR_TEXT)
        in_s = self.small_font.render(f"[{intent}]", True, COLOR_TEXT)
        sp_s = self.small_font.render(f"V: {speed:.1f}", True, COLOR_TEXT)
        self.screen.blit(id_s, (x - 20, y - 40))
        self.screen.blit(in_s, (x - 20, y - 55))
        self.screen.blit(sp_s, (x - 20, y + 25))

    def start(self, scenario_file):
        try:
            with open(scenario_file, 'r') as f: scenario_data = json.load(f)
        except: return
        
        frame_idx = 0
        while frame_idx < len(scenario_data):
=======
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
>>>>>>> 4cbaa5a8598e7b5ce2f66d82e9a536e186924d4a
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return
            self.draw_environment()
            for v in scenario_data[frame_idx]: self.render_vehicle(v)
            pygame.display.flip()
<<<<<<< HEAD
            self.clock.tick(self.fps)
            frame_idx += 1
        pygame.quit()

if __name__ == "__main__":
    SimulationUI().start('scenariu.json')
=======
            self.clock.tick(60)  # UI-ul poate rula la 60 FPS pentru fluiditate

        pygame.quit()


# ===== EXECUTARE =====
if __name__ == "__main__":
    ui = SimulationUI()
    # Asigură-te că fișierul se numește exact 'scenariu.json' și este în același folder
    ui.start("scenariu.json")
>>>>>>> 4cbaa5a8598e7b5ce2f66d82e9a536e186924d4a
