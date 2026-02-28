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

    def draw_dashed_line(self, start_pos, end_pos, vertical=False):
        """Funcție pentru a desena linia punctată de separare a benzilor."""
        dist = 20
        for i in range(start_pos, end_pos, dist * 2):
            if vertical:
                pygame.draw.line(self.screen, COLOR_LINE, (INT_1_X, i), (INT_1_X, i + dist), 1)
                pygame.draw.line(self.screen, COLOR_LINE, (INT_2_X, i), (INT_2_X, i + dist), 1)
            else:
                pygame.draw.line(self.screen, COLOR_LINE, (i, INTERSECTION_CENTER_Y), (i + dist, INTERSECTION_CENTER_Y), 1)

    def draw_environment(self):
        """Desenează intersecția și zidurile tale originale."""
        self.screen.fill(COLOR_BACKGROUND)
        
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

    def render_vehicle(self, v_data):
        x, y = v_data.get("position_x", 0), v_data.get("position_y", 0)
        v_type = v_data.get("vehicle_type", "Normal")
        heading = v_data.get("heading", "EAST")
        v_id, intent, speed = v_data.get("agent_id", "?"), v_data.get("intent", "IDLE"), v_data.get("speed", 0)

        if self.use_images:
            base_img = self.img_ambulance if v_type == "Ambulance" else self.img_normal
            rotated_img = pygame.transform.rotate(base_img, self.rotation_map.get(heading, 0))
            rect = rotated_img.get_rect(center=(x, y))
            self.screen.blit(rotated_img, rect)
        else:
            color = COLOR_AMBULANCE_CAR if v_type == "Ambulance" else COLOR_NORMAL_CAR
            w, h = (40, 20) if heading in ["EAST", "WEST"] else (20, 40)
            pygame.draw.rect(self.screen, color, (x - w//2, y - h//2, w, h))

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
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return
            self.draw_environment()
            for v in scenario_data[frame_idx]: self.render_vehicle(v)
            pygame.display.flip()
            self.clock.tick(self.fps)
            frame_idx += 1
        pygame.quit()

if __name__ == "__main__":
    SimulationUI().start('scenariu.json')