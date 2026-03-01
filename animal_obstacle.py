# animal_obstacle.py


class AnimalObstacle:
    def __init__(self, x, y):
        self.agent_id = "Căprioară"
        self.start_x = x
        self.start_y = y
        self.position_x = x
        self.position_y = y
        self.speed = 30.0  
        self.state = "HIDDEN"  

    def trigger(self):
        """Declanșat de butonul din UI."""
        if self.state in ["HIDDEN", "CRASHED"]:
            self.position_y = self.start_y  
            self.state = "CROSSING"

    def update(self, dt):
        if self.state == "CROSSING":
            self.position_y += self.speed * dt

            if self.position_y > 730:
                self.state = "HIDDEN"

    def get_status(self):
        if self.state in ["CROSSING", "CRASHED"]:
            return {
                "agent_id": self.agent_id,
                "position_x": self.position_x,
                "position_y": self.position_y,
                "speed": self.speed if self.state != "CRASHED" else 0.0,
                "vehicle_type": "Animal",
                "heading": "CROSSING",
                "intent": "JUMPING",
                "is_crashed": self.state
                == "CRASHED",  
            }
        return None
