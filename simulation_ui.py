import pygame
import sys
import json
import math
from map_config import nodes, edges

SCREEN_WIDTH = 1500
SCREEN_HEIGHT = 800
ROAD_WIDTH_MAIN = 80
ROAD_WIDTH_SECONDARY = 40

# CULORI
COLOR_BACKGROUND = (20, 22, 28)
COLOR_ROAD = (55, 58, 70)
COLOR_LINE = (230, 230, 240)
COLOR_WALL = (100, 105, 120)
COLOR_TEXT_UI = (220, 225, 240)
COLOR_TEXT_CAR = (102, 178, 255)
COLOR_RED = (255, 80, 80)
COLOR_GREEN = (80, 255, 120)
COLOR_YELLOW = (255, 220, 100)
COLOR_GRASS = (55, 85, 40)
COLOR_NORMAL_CAR = (100, 150, 255)
COLOR_AMBULANCE_CAR = (255, 50, 50)


def get_font(size, bold=False):
    """Încarcă un font de sistem."""
    fonts = ["sfprodisplay", "arial", "helvetica"]
    return pygame.font.SysFont(fonts, size, bold=bold)


def scale_aspect_ratio(image, width):
    """Scalează o imagine la lățimea dorită, păstrând aspect ratio."""
    if image is None:
        return None
    original_rect = image.get_rect()
    aspect_ratio = original_rect.width / original_rect.height
    new_height = int(width / aspect_ratio)
    return pygame.transform.scale(image, (width, new_height))


def draw_modern_button(
    surface, rect, text, font, base_color, text_color=(255, 255, 255), is_hovered=False
):
    """
    Desenează un buton modern.
    """
    x, y, w, h = rect

    btn_surf = pygame.Surface((w, h), pygame.SRCALPHA)

    alpha = 220 if not is_hovered else 255
    r, g, b = base_color

    pygame.draw.rect(btn_surf, (r, g, b, alpha), (0, 0, w, h), border_radius=10)

    highlight_color = (min(255, r + 30), min(255, g + 30), min(255, b + 30), 150)
    pygame.draw.rect(
        btn_surf,
        highlight_color,
        (0, 0, w, 2),
        border_top_left_radius=10,
        border_top_right_radius=10,
    )

    shadow_color = (max(0, r - 30), max(0, g - 30), max(0, b - 30), 150)
    pygame.draw.rect(
        btn_surf,
        shadow_color,
        (0, h - 4, w, 4),
        border_bottom_left_radius=10,
        border_bottom_right_radius=10,
    )

    is_antialiased = True
    text_surf = font.render(text, is_antialiased, text_color)

    text_rect = text_surf.get_rect(center=(w // 2, h // 2))
    btn_surf.blit(text_surf, text_rect)

    surface.blit(btn_surf, (x, y))


class SimulationUI:
    def __init__(self, title="C-V2X Command Center"):
        pygame.init()
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)

        self.screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.HWSURFACE | pygame.DOUBLEBUF
        )
        self.screen.fill(COLOR_BACKGROUND)
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()

        self.title_font = get_font(22, bold=True)
        self.font = get_font(18, bold=True)
        self.small_font = get_font(15)
        self.micro_font = get_font(13)
        self.fps = 60

        self.system_on = True
        self.button_rect = pygame.Rect(20, 20, 160, 45)

        self.ai_enabled = True
        self.ai_button_rect = pygame.Rect(200, 20, 160, 45)

        self.animal_button_rect = pygame.Rect(20, 80, 160, 40)

        self.spawn_car_button_rect = pygame.Rect(200, 80, 160, 40)

        self.DEER_DECOR_POINTS = [
            (1270, 590, "FX"),
            (1330, 565, "N"),
            (1320, 590, "N"),
            (1290, 560, "FX"),
            (1410, 730, "FX"),
            (1390, 760, "N"),
        ]

        self.COLOR_RED_OFF = (60, 0, 0)
        self.COLOR_YELLOW_OFF = (60, 60, 0)
        self.COLOR_GREEN_OFF = (0, 60, 0)

        self.img_normal = None
        self.img_aggressive = None
        self.img_ambulance = None
        self.img_indicator = None
        self.img_deer = None
        self.use_images = False

        try:
            self.img_normal = pygame.image.load("images/car.png").convert_alpha()
            self.img_ambulance = pygame.image.load(
                "images/ambulance.png"
            ).convert_alpha()

            try:
                self.img_aggressive = pygame.image.load(
                    "images/car-aggressive.png"
                ).convert_alpha()
            except:
                print("car-aggressive.png lipsește, folosesc imaginea normală.")
                self.img_aggressive = self.img_normal

            indicator_base = pygame.image.load("images/indicator.png").convert_alpha()
            self.img_indicator = pygame.transform.scale(indicator_base, (30, 30))

            self.img_deer = pygame.image.load("images/deer.png").convert_alpha()
            self.use_images = True

        except Exception as e:
            print(f"Probleme la încărcarea imaginilor principale. Eroare: {e}")

        self.rotation_map = {"EAST": 0, "NORTH": 90, "WEST": 180, "SOUTH": 270}

    def draw_indicator(self):
        if self.img_indicator is None:
            return

        x1, y1 = 1400, 580
        x2, y2 = 1300, 700
        img_left = pygame.transform.rotate(self.img_indicator, 90)
        img_right = pygame.transform.rotate(self.img_indicator, -90)
        self.screen.blit(img_left, (x1, y1))
        self.screen.blit(img_right, (x2, y2))

        pygame.draw.rect(self.screen, (0, 0, 0), (1425, 593, 50, 4))
        pygame.draw.rect(self.screen, (0, 0, 0), (1255, 712, 50, 4))

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
            if i % 2 == 0:
                start_x = x1 + (x2 - x1) * (i / dashes)
                start_y = y1 + (y2 - y1) * (i / dashes)
                end_x = x1 + (x2 - x1) * ((i + 1) / dashes)
                end_y = y1 + (y2 - y1) * ((i + 1) / dashes)
                pygame.draw.line(
                    surface, color, (start_x, start_y), (end_x, end_y), width
                )

    def is_outside_bounds(self, v_data):
        if not v_data:
            return True
        if v_data.get("vehicle_type") == "Infrastructure":
            return False
        x, y = v_data.get("position_x", 0), v_data.get("position_y", 0)
        return x < -50 or x > SCREEN_WIDTH + 50 or y < -50 or y > SCREEN_HEIGHT + 50

    def draw_risk_aura(self, center, radius, color_rgb, max_alpha=120, rings=6):
        x, y = int(center[0]), int(center[1])
        aura = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        cx, cy = radius, radius
        for i in range(rings):
            t = i / max(1, rings - 1)
            r = int(radius * (1.0 - 0.12 * i))
            a = int(max_alpha * (1.0 - t) ** 2)
            pygame.draw.circle(aura, (*color_rgb, a), (cx, cy), r)
        self.screen.blit(aura, (x - radius, y - radius))

    def _intersection_centers_and_degree(self):
        intersections = ["I1", "I2", "I3"]
        results = []
        for inter in intersections:
            corners = [f"{inter}_NW", f"{inter}_NE", f"{inter}_SE", f"{inter}_SW"]
            pts = [nodes.get(c) for c in corners if nodes.get(c)]
            if len(pts) != 4:
                continue
            cx = sum(p[0] for p in pts) / 4
            cy = sum(p[1] for p in pts) / 4
            degree = 0
            for u, v, _ in edges:
                u_is = u.startswith(inter + "_")
                v_is = v.startswith(inter + "_")
                if u_is and not v_is:
                    degree += 1
                if v_is and not u_is:
                    degree += 1
            results.append(((cx, cy), degree))
        return results

    def draw_risk_overlays(self, current_traffic=None):
        for center, degree in self._intersection_centers_and_degree():
            if degree >= 8:
                self.draw_risk_aura(
                    center, radius=85, color_rgb=(255, 0, 0), max_alpha=120
                )
            else:
                self.draw_risk_aura(
                    center, radius=70, color_rgb=(255, 0, 0), max_alpha=70
                )

        if current_traffic:
            for v in current_traffic.values():
                if v and v.get("vehicle_type") == "Animal":
                    x = v.get("position_x", 0)
                    y = v.get("position_y", 0)
                    self.draw_risk_aura(
                        (x, y), radius=40, color_rgb=(255, 140, 0), max_alpha=100
                    )

    def draw_dashed_line_segment(
        self, p1, p2, color, dash_length=15, gap_length=10, offset=0
    ):
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length == 0:
            return
        unit_dx = dx / length
        unit_dy = dy / length
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
        x1, y1 = p1
        x2, y2 = p2
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length < 2 * node_offset:
            return
        ux = dx / length
        uy = dy / length
        x1 += ux * node_offset
        y1 += uy * node_offset
        x2 -= ux * node_offset
        y2 -= uy * node_offset
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
        """Desenează harta"""
        self.screen.fill(COLOR_BACKGROUND)
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

        for u, v, _ in edges:
            p1 = nodes.get(u)
            p2 = nodes.get(v)
            if p1 and p2:
                pygame.draw.line(self.screen, COLOR_ROAD, p1, p2, ROAD_WIDTH_SECONDARY)

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

        drawn_dashed = set()
        for u, v, _ in edges:
            if (u, v) in drawn_dashed:
                continue
            if u.startswith("I") and v.startswith("I") and u[:2] == v[:2]:
                continue
            p1 = nodes.get(u)
            p2 = nodes.get(v)
            if not p1 or not p2:
                continue
            for u2, v2, _ in edges:
                if (u2, v2) in drawn_dashed or (u2, v2) == (u, v):
                    continue
                p1_rev = nodes.get(u2)
                p2_rev = nodes.get(v2)
                if not p1_rev or not p2_rev:
                    continue
                dist_starts = math.hypot(p1_rev[0] - p2[0], p1_rev[1] - p2[1])
                dist_ends = math.hypot(p2_rev[0] - p1[0], p2_rev[1] - p1[1])
                if dist_starts < 100 and dist_ends < 100:
                    center_start = ((p1[0] + p2_rev[0]) / 2, (p1[1] + p2_rev[1]) / 2)
                    center_end = ((p2[0] + p1_rev[0]) / 2, (p2[1] + p1_rev[1]) / 2)
                    self.draw_dashed_line_segment(
                        center_start, center_end, COLOR_LINE, offset=0
                    )
                    drawn_dashed.add((u, v))
                    drawn_dashed.add((u2, v2))
                    break

        if self.use_images and self.img_deer is not None:
            base = pygame.transform.scale(self.img_deer, (35, 35))
            deer_n = base
            deer_fx = pygame.transform.flip(base, True, False)

            for x, y, v in self.DEER_DECOR_POINTS:
                img = deer_n if v == "N" else deer_fx
                rect = img.get_rect(center=(int(x), int(y)))
                self.screen.blit(img, rect)
        else:
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
                elif state == "YELLOW" or state == "YELLOW_BLINKING":
                    y_c = COLOR_YELLOW
            offsets = [-18, 0, 18]
            cols = [r_c, y_c, g_c] if not flip else [g_c, y_c, r_c]
            for i in range(3):
                p = (x, y + offsets[i]) if orientation == "V" else (x + offsets[i], y)
                pygame.draw.circle(self.screen, cols[i], p, 7)

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

    def draw_buttons(self, mouse_pos):
        """Desenează toate butoanele folosind funcția helper."""

        c1 = COLOR_GREEN if self.system_on else COLOR_RED
        text1 = "SISTEM: ON" if self.system_on else "SISTEM: OFF"
        h1 = self.button_rect.collidepoint(mouse_pos)
        draw_modern_button(
            self.screen, self.button_rect, text1, self.font, c1, is_hovered=h1
        )

        c2 = COLOR_GREEN if self.ai_enabled else COLOR_RED
        text2 = "AI: ON" if self.ai_enabled else "AI: OFF"
        h2 = self.ai_button_rect.collidepoint(mouse_pos)
        draw_modern_button(
            self.screen, self.ai_button_rect, text2, self.font, c2, is_hovered=h2
        )

        h3 = self.animal_button_rect.collidepoint(mouse_pos)
        draw_modern_button(
            self.screen,
            self.animal_button_rect,
            "SPAWN CĂPRIOARĂ",
            self.small_font,
            (139, 69, 19),
            is_hovered=h3,
        )

        h4 = self.spawn_car_button_rect.collidepoint(mouse_pos)
        draw_modern_button(
            self.screen,
            self.spawn_car_button_rect,
            "SPAWN AI CAR",
            self.small_font,
            (0, 100, 200),
            is_hovered=h4,
        )

    def render_vehicle(self, v_data):
        v_id = v_data.get("agent_id", "?")
        if v_id == "Semafor_Centru":
            return
        x, y = v_data.get("position_x", 0), v_data.get("position_y", 0)
        v_type = v_data.get("vehicle_type", "Normal")
        is_crashed = v_data.get("is_crashed", False)

        if is_crashed:
            pygame.draw.circle(self.screen, (255, 69, 0), (int(x), int(y)), 25)
            pygame.draw.circle(self.screen, (200, 0, 0), (int(x), int(y)), 15)

        if v_type == "Animal":
            if self.use_images and self.img_deer is not None:
                deer_scaled = pygame.transform.scale(self.img_deer, (35, 35))
                rect = deer_scaled.get_rect(center=(int(x), int(y)))
                self.screen.blit(deer_scaled, rect)
            else:
                pygame.draw.circle(self.screen, (139, 69, 19), (int(x), int(y)), 10)

            animal_text = self.small_font.render(v_id, True, (255, 150, 150))
            self.screen.blit(animal_text, (int(x) - 25, int(y) - 30))
            return

        exact_angle = v_data.get("visual_angle", 0.0)
        intent = v_data.get("intent", "IDLE")
        speed = v_data.get("speed", 0)
        priority = v_data.get("priority_active", False)

        target_width = 45

        if self.use_images:
            driving_style = v_data.get("driving_style", "Cautious")

            if v_type == "Ambulance":
                base_img = self.img_ambulance
            elif driving_style == "Aggressive" and self.img_aggressive is not None:
                base_img = self.img_aggressive
            else:
                base_img = self.img_normal

            scaled_img = scale_aspect_ratio(base_img, target_width)
            if scaled_img is None:
                return  # Failsafe

            angle_to_draw = -exact_angle
            rotated_img = pygame.transform.rotate(scaled_img, angle_to_draw)
            rect = rotated_img.get_rect(center=(int(x), int(y)))
            self.screen.blit(rotated_img, rect)
        else:
            color = COLOR_AMBULANCE_CAR if v_type == "Ambulance" else COLOR_NORMAL_CAR
            h = 28
            vw, vh = (
                (target_width, h)
                if exact_angle == 0 or exact_angle == 180
                else (h, target_width)
            )
            pygame.draw.rect(
                self.screen, color, (int(x) - vw // 2, int(y) - vh // 2, vw, vh)
            )

        if priority and (pygame.time.get_ticks() // 200) % 2 == 0:
            pygame.draw.circle(self.screen, (255, 255, 255), (int(x), int(y)), 35, 2)

        is_antialiased = True
        id_s = self.font.render(v_id, is_antialiased, COLOR_TEXT_CAR)
        in_s = self.micro_font.render(f"[{intent}]", is_antialiased, COLOR_TEXT_CAR)
        display_speed = 0.0 if is_crashed else speed
        sp_s = self.micro_font.render(
            f"V: {display_speed:.1f}", is_antialiased, COLOR_TEXT_CAR
        )

        self.screen.blit(id_s, (int(x) - 20, int(y) - 45))
        self.screen.blit(in_s, (int(x) - 20, int(y) - 60))
        self.screen.blit(sp_s, (int(x) - 20, int(y) + 25))

    def draw_dashboard(self, current_traffic):
        """Desenează un panou în colțul din dreapta-sus."""
        if current_traffic is None:
            return

        total_cars, crashed_cars, total_speed, active_brakes, ambulances_active = (
            0,
            0,
            0.0,
            0,
            0,
        )

        for v in current_traffic.values():
            if not v:
                continue
            v_type = v.get("vehicle_type", "")
            if v_type in ["Normal", "Ambulance"]:
                total_cars += 1
                total_speed += v.get("speed", 0)
                if v.get("is_crashed", False):
                    crashed_cars += 1
                elif v.get("intent") == "BRAKING":
                    active_brakes += 1
            if v_type == "Ambulance":
                ambulances_active += 1

        avg_speed = (total_speed / total_cars) if total_cars > 0 else 0.0

        dash_width, dash_height = 280, 240
        hud = pygame.Surface((dash_width, dash_height), pygame.SRCALPHA)

        pygame.draw.rect(
            hud, (0, 0, 0, 200), (0, 0, dash_width, dash_height), border_radius=12
        )
        pygame.draw.rect(
            hud,
            (100, 150, 255, 255),
            (0, 0, dash_width, dash_height),
            width=2,
            border_radius=12,
        )

        title = self.title_font.render("● Command Center", True, (255, 215, 0))
        hud.blit(title, (40, 15))
        pygame.draw.line(hud, (100, 150, 255), (15, 42), (dash_width - 15, 42), 2)

        is_aa = True
        y_offset, spacing = 55, 23
        text_w = (255, 255, 255)

        hud.blit(
            self.small_font.render(
                f"● Vehicule conectate: {total_cars}", is_aa, text_w
            ),
            (15, y_offset),
        )
        y_offset += spacing

        speed_color = (
            (100, 255, 100)
            if avg_speed > 30
            else ((255, 255, 100) if avg_speed > 10 else (255, 100, 100))
        )
        hud.blit(
            self.small_font.render(
                f"● Viteza medie: {avg_speed:.1f} km/h", is_aa, speed_color
            ),
            (15, y_offset),
        )
        y_offset += spacing
        hud.blit(
            self.small_font.render(
                f"● Intervenții AI active: {active_brakes}", is_aa, (100, 200, 255)
            ),
            (15, y_offset),
        )
        y_offset += spacing

        crash_color = (255, 80, 80) if crashed_cars > 0 else (100, 255, 100)
        hud.blit(
            self.small_font.render(
                f"● Accidente detectate: {crashed_cars}", is_aa, crash_color
            ),
            (15, y_offset),
        )
        y_offset += spacing

        if ambulances_active > 0:
            if (pygame.time.get_ticks() // 300) % 2 == 0:
                hud.blit(
                    self.small_font.render(
                        f"● URGENȚĂ: Culoar verde!", is_aa, (255, 50, 50)
                    ),
                    (15, y_offset),
                )
        else:
            hud.blit(
                self.small_font.render(f"● Trafic normal", is_aa, (150, 150, 150)),
                (15, y_offset),
            )
        y_offset += spacing

        pygame.draw.line(
            hud, (100, 100, 100), (15, y_offset), (dash_width - 15, y_offset), 1
        )
        y_offset += 10

        v2x_st, v2x_co = (
            ("ONLINE (5G Secured)", (100, 255, 100))
            if self.ai_enabled
            else ("OFFLINE (Dangerous!)", (255, 80, 80))
        )
        lat = 12 + (pygame.time.get_ticks() % 5) if self.ai_enabled else 999
        msg = total_cars * 20 if self.ai_enabled else 0
        hud.blit(
            self.micro_font.render(f"● Rețea: {v2x_st}", is_aa, v2x_co), (15, y_offset)
        )
        y_offset += 20
        hud.blit(
            self.micro_font.render(
                f"   Ping: {lat}ms | Pkts: {msg}/s", is_aa, (200, 200, 200)
            ),
            (15, y_offset),
        )

        self.screen.blit(hud, (SCREEN_WIDTH - dash_width - 20, 20))

    def draw_graph_debug_overlay(self):
        """Desenează Graful Logic peste harta vizuală pentru debugging."""
        # 1. Desenează muchiile (drumurile logice) cu o linie subțire cyan
        for u, v, _ in edges:
            p1 = nodes.get(u)
            p2 = nodes.get(v)
            if p1 and p2:
                pygame.draw.line(self.screen, (0, 255, 255), p1, p2, 2)

                # Săgeată direcțională la jumătatea drumului (opțional, să vezi sensul)
                mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
                pygame.draw.circle(self.screen, (0, 200, 255), (int(mx), int(my)), 3)

        # 2. Desenează nodurile și textul (Nume + Coordonate)
        for node_name, pos in nodes.items():
            # Punctul exact (Magenta)
            pygame.draw.circle(self.screen, (255, 0, 255), pos, 5)

            # Eticheta cu Numele și Coordonatele
            label = f"{node_name} {pos}"
            text_surf = self.micro_font.render(
                label, True, (255, 255, 255), (0, 0, 0)
            )  # Text alb pe fundal negru

            # Plasăm textul puțin decalat față de punct
            self.screen.blit(text_surf, (pos[0] + 8, pos[1] - 8))

    def start(self, broker):
        running = True
        print("Simularea UI a început. Harta rețea (grilă).")
        while running:
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.button_rect.collidepoint(event.pos):
                        self.system_on = not self.system_on
                        if hasattr(broker, "infrastructure_active"):
                            broker.infrastructure_active = self.system_on
                    elif self.ai_button_rect.collidepoint(event.pos):
                        self.ai_enabled = not self.ai_enabled
                        if hasattr(broker, "ai_enabled"):
                            broker.ai_enabled = self.ai_enabled
                    elif self.animal_button_rect.collidepoint(event.pos):
                        if hasattr(broker, "trigger_animal_event"):
                            broker.trigger_animal_event()
                    elif self.spawn_car_button_rect.collidepoint(event.pos):
                        if hasattr(broker, "trigger_spawn_car"):
                            broker.trigger_spawn_car()

            self.draw_environment()
            self.draw_graph_debug_overlay()  # pentru debugging vizual al grafului logic peste harta
            self.draw_buttons(mouse_pos)
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

            self.draw_dashboard(current_traffic)

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
