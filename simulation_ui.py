import pygame
import sys
import json
import math
# Importăm configurația grafului
from map_config import nodes, edges

# --- CONFIGURAȚII ---
SCREEN_WIDTH = 1500
SCREEN_HEIGHT = 800
ROAD_WIDTH = 80  # Lățime asfalt

# CULORI
COLOR_BACKGROUND = (10, 10, 10)
COLOR_ROAD = (50, 50, 50)
COLOR_LINE = (200, 200, 200)
COLOR_WALL = (100, 100, 100)
COLOR_TEXT = (102, 178, 255)
COLOR_NORMAL_CAR = (153, 153, 255)
COLOR_AMBULANCE_CAR = (204, 0, 0)
COLOR_RED = (255, 0, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_YELLOW = (255, 165, 0)

class SimulationUI:
    def __init__(self, title="V2X Graph-Based Simulator"):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("timesnewroman", 16, bold=True)
        self.small_font = pygame.font.SysFont("timesnewroman", 13)
        self.fps = 60
        
        self.system_on = True  
        self.button_rect = pygame.Rect(20, 20, 180, 40)
        
        # Culori stinse becuri
        self.COLOR_RED_OFF = (60, 0, 0)
        self.COLOR_YELLOW_OFF = (60, 60, 0)
        self.COLOR_GREEN_OFF = (0, 60, 0)

        try:
            self.img_normal = pygame.image.load("car.png").convert_alpha()
            self.img_ambulance = pygame.image.load("ambulance.png").convert_alpha()
            self.img_normal = pygame.transform.scale(self.img_normal, (50, 28))
            self.img_ambulance = pygame.transform.scale(self.img_ambulance, (50, 28))
            self.use_images = True
        except:
            self.use_images = False

        self.rotation_map = {"EAST": 0, "NORTH": 90, "WEST": 180, "SOUTH": 270}

    def draw_environment(self):
        """Desenează DOAR nodurile cu puncte roșii pentru verificare."""
        self.screen.fill((0, 0, 0)) # Fundal negru

        # Importăm nodurile direct din map_config pentru a fi siguri că le avem
        from map_config import nodes

        for node_name, pos in nodes.items():
            # 1. Desenează punctul roșu
            pygame.draw.circle(self.screen, (255, 0, 0), pos, 6)
            
            # 2. Scrie numele nodului lângă punct (util pentru debug)
            label = self.small_font.render(node_name, True, (255, 255, 255))
            self.screen.blit(label, (pos[0] + 10, pos[1] - 10))

        # (Opțional) Dacă vrei să vezi și cum sunt unite, lasă liniile de mai jos:
         
        for start_id, end_id, _ in edges:
             p1, p2 = nodes.get(start_id), nodes.get(end_id)
             if p1 and p2:
                 pygame.draw.line(self.screen, (50, 50, 50), p1, p2, 1)

    def draw_button(self):
        color = (0, 150, 0) if self.system_on else (150, 0, 0)
        pygame.draw.rect(self.screen, color, self.button_rect, border_radius=8)
        text = "SISTEM V2X: ON" if self.system_on else "SISTEM V2X: OFF"
        surf = self.font.render(text, True, (255, 255, 255))
        self.screen.blit(surf, (self.button_rect.x + 20, self.button_rect.y + 10))

    def draw_traffic_light_agent(self, current_traffic):
        """Desenează semafoarele la Intersecția 1 folosind noile noduri."""
        sem_data = next((v for v in current_traffic.values() if v.get("agent_id") == "Semafor_Centru"), {})
        state_ns = sem_data.get("state_NS", "RED")
        state_ew = sem_data.get("state_EW", "RED")

        def draw_pole(pos, state, orientation="V", flip=False):
            if not pos: return
            x, y = pos
            box_w, box_h = (22, 60) if orientation == "V" else (60, 22)
            pygame.draw.rect(self.screen, (20, 20, 20), (x - box_w//2, y - box_h//2, box_w, box_h))
            
            r_c, y_c, g_c = self.COLOR_RED_OFF, self.COLOR_YELLOW_OFF, self.COLOR_GREEN_OFF
            if not self.system_on:
                if (pygame.time.get_ticks() // 500) % 2 == 0: y_c = COLOR_YELLOW
            else:
                if state == "GREEN": g_c = COLOR_GREEN
                elif state == "RED": r_c = COLOR_RED

            offsets = [-18, 0, 18] if not flip else [18, 0, -18]
            cols = [r_c, y_c, g_c]
            for i in range(3):
                p = (x, y + offsets[i]) if orientation == "V" else (x + offsets[i], y)
                pygame.draw.circle(self.screen, cols[i], p, 7)

        # --- PLASARE PE NOILE NODURI ---
        # NORD (pe banda care coboară)
        draw_pole(nodes.get("I1_N"), state_ns, "V", True)
        # SUD (pe banda care urcă)
        draw_pole(nodes.get("I1_S"), state_ns, "V", False)
        # VEST (pe banda care merge la dreapta)
        draw_pole(nodes.get("I1_W"), state_ew, "H", True)
        # EST (pe banda care merge la stânga)
        draw_pole(nodes.get("I1_E"), state_ew, "H", False)

    def render_vehicle(self, v_data):
        v_id = v_data.get("agent_id", "?")
        if v_id == "Semafor_Centru": return

        x, y = v_data.get("position_x", 0), v_data.get("position_y", 0)
        v_type = v_data.get("vehicle_type", "Normal")
        heading = v_data.get("heading", "EAST")
        intent = v_data.get("intent", "IDLE")
        speed = v_data.get("speed", 0)

        # Desenare Corp
        if self.use_images:
            base_img = self.img_ambulance if v_type == "Ambulance" else self.img_normal
            angle = self.rotation_map.get(heading, 0)
            rotated_img = pygame.transform.rotate(base_img, angle)
            rect = rotated_img.get_rect(center=(int(x), int(y)))
            self.screen.blit(rotated_img, rect)
        else:
            color = COLOR_AMBULANCE_CAR if v_type == "Ambulance" else COLOR_NORMAL_CAR
            pygame.draw.rect(self.screen, color, (int(x)-20, int(y)-12, 40, 24))

        # Texte cu culoarea (102, 178, 255)
        id_s = self.font.render(v_id, True, COLOR_TEXT)
        in_s = self.small_font.render(f"[{intent}]", True, COLOR_TEXT)
        sp_s = self.small_font.render(f"V: {speed:.1f}", True, COLOR_TEXT)
        
        self.screen.blit(id_s, (int(x) - 20, int(y) - 45))
        self.screen.blit(in_s, (int(x) - 20, int(y) - 60))
        self.screen.blit(sp_s, (int(x) - 20, int(y) + 25))

    def start(self, broker):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.button_rect.collidepoint(event.pos):
                        self.system_on = not self.system_on
                        if hasattr(broker, 'infrastructure_active'):
                            broker.infrastructure_active = self.system_on

            self.draw_environment()
            self.draw_button()

            with broker.lock:
                current_traffic = broker.vehicles_status.copy()

            self.draw_traffic_light_agent(current_traffic)

            for v_data in current_traffic.values():
                self.render_vehicle(v_data)

            pygame.display.flip()
            self.clock.tick(self.fps)
        pygame.quit()

if __name__ == "__main__":
    # Această parte va fi apelată din main.py
    pass