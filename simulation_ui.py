import pygame

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 800
ROAD_WIDTH = 150
COLOR_BACKGROUND = (0, 0, 0)
COLOR_ROAD = (255, 255, 255)
COLOR_WALL = (160, 160, 160)
COLOR_TEXT = (102, 178, 224)

class DummyVehicle:
    def __init__(self, id, x, y, color):
        self.id = id
        self.x = x
        self.y = y
        self.width = 40
        self.height = 25
        self.color = color

class SimulationUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("V2X Intersection Simulator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("timesnewroman", 20)

    def draw_environment(self):
        self.screen.fill(COLOR_BACKGROUND)
        # drumuri orizontale / verticale
        pygame.draw.rect(self.screen, COLOR_ROAD, (0, SCREEN_HEIGHT//2 - ROAD_WIDTH//2, SCREEN_WIDTH, ROAD_WIDTH))
        pygame.draw.rect(self.screen, COLOR_ROAD, (SCREEN_WIDTH//2 - ROAD_WIDTH//2, 0, ROAD_WIDTH, SCREEN_HEIGHT))
        
        # ziduri
        wall_rect = pygame.Rect(SCREEN_WIDTH//2 - ROAD_WIDTH//2 - 100, 
                                SCREEN_HEIGHT//2 - ROAD_WIDTH//2 - 100, 100, 100)
        pygame.draw.rect(self.screen, COLOR_WALL, wall_rect)

    def update_display(self, vehicles):
        self.draw_environment()

        for vehicle in vehicles:
            rect = pygame.Rect(vehicle.x, vehicle.y, vehicle.width, vehicle.height)
            pygame.draw.rect(self.screen, vehicle.color, rect)
            
            text_surface = self.font.render(f"ID: {vehicle.id}", True, COLOR_TEXT)
            self.screen.blit(text_surface, (vehicle.x, vehicle.y - 25))

        pygame.display.flip()
        self.clock.tick(60)

    def quit(self):
        pygame.quit()

# TEST 
if __name__ == "__main__":
    ui = SimulationUI()
    
    # Creăm 2 mașini de test
    car1 = DummyVehicle("V2X_01", 100, 335, (0, 0, 255))  # Albastră
    car2 = DummyVehicle("V2X_02", 435, 100, (255, 0, 0))  # Roșie
    list_of_vehicles = [car1, car2]

    running = True
    while running:
        # inchidere fereastra
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Simulăm o mică mișcare
        car1.x += 2
        car2.y += 2

        # Resetăm mașinile dacă ies din ecran (loop)
        if car1.x > 800: car1.x = 0
        if car2.y > 800: car2.y = 0

        # Desenăm totul
        ui.update_display(list_of_vehicles)

    ui.quit()
    sys.exit()