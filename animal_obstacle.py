# animal_obstacle.py


class AnimalObstacle:
    def __init__(self, x, y):
        self.agent_id = "Căprioară"
        self.start_x = x
        self.start_y = y
        self.position_x = x
        self.position_y = y
        self.speed = 30.0  # Se mișcă mai repede, ca un animal speriat
        self.state = "HIDDEN"  # Stările pot fi: HIDDEN, CROSSING

    def trigger(self):
        """Declanșat de butonul din UI."""
        if self.state == "HIDDEN":
            self.position_y = self.start_y  # O resetăm la poziția inițială
            self.state = "CROSSING"

    def update(self, dt):
        if self.state == "CROSSING":
            # Traversează strada (coboară pe axa Y)
            self.position_y += self.speed * dt

            # Dacă a ajuns pe iarbă în partea de jos (y > 730), dispare
            if self.position_y > 730:
                self.state = "HIDDEN"

    def get_status(self):
        # Publicăm poziția ei în rețea DOAR dacă este pe stradă
        if self.state == "CROSSING":
            return {
                "agent_id": self.agent_id,
                "position_x": self.position_x,
                "position_y": self.position_y,
                "speed": self.speed,
                "vehicle_type": "Animal",
                "heading": "CROSSING",
                "intent": "JUMPING",
            }
        return None
