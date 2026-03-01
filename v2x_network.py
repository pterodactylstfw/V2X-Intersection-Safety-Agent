import threading
import time
import json


class V2XBroker:
    def __init__(self):
        self.vehicles_status = {}
        self.lock = threading.Lock()
        self.infrastructure_active = True
        self.ai_enabled = True

    def publish(self, vehicle_id: str, data_package: dict):
        with self.lock:
            self.vehicles_status[vehicle_id] = data_package

    def receive(self, requesting_vehicle_id: str) -> dict:
        with self.lock:
            return {
                v_id: data
                for v_id, data in self.vehicles_status.items()
                if v_id != requesting_vehicle_id
            }


class DataFeeder:
    def __init__(self, broker, file_path, agents_dict=None):
        self.broker = broker
        self.file_path = file_path
        self.scenario_data = []
        self.agents = agents_dict or {}

    def load_scenario(self):
        with open(self.file_path, "r", encoding="utf-8") as file:
            self.scenario_data = json.load(file)

    def play_scenario(self, delay_seconds=0.05):
        print("[Feeder] Începem redarea scenariului...")

        for frame in self.scenario_data:
            for vehicle_data in frame:
                agent_id = vehicle_data["agent_id"]

                if agent_id in self.agents:
                    agent = self.agents[agent_id]

                    if agent.has_decided_to_brake():
                        agent.update_position(delay_seconds, 400, 400)
                        final_data = agent.get_emergency_status()
                    else:
                        final_data = vehicle_data
                        agent.position_x = vehicle_data["position_x"]
                        agent.position_y = vehicle_data["position_y"]
                        agent.speed = vehicle_data["speed"]
                else:
                    final_data = vehicle_data

                self.broker.publish(agent_id, final_data)

            time.sleep(delay_seconds)
