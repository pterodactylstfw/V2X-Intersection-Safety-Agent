import pytest
import time
from v2x_security import SecurityManager
from vehicle_agent import VehicleAgent


def test_security_valid_signature():
    """Testăm dacă un pachet valid semnat digital este acceptat."""
    data = {
        "agent_id": "Masina_Test",
        "position_x": 100.0,
        "position_y": 200.0,
        "speed": 50.0,
        "timestamp": time.time(),
    }
    data["signature"] = SecurityManager.sign_data(data)

    assert SecurityManager.is_payload_valid(data, "Semafor_Centru") == True


def test_security_tampered_payload():
    """Testăm dacă modificarea datelor pe parcurs invalidează semnătura."""
    data = {
        "agent_id": "Masina_Test",
        "position_x": 100.0,
        "position_y": 200.0,
        "speed": 50.0,
        "timestamp": time.time(),
    }
    data["signature"] = SecurityManager.sign_data(data)

    # Atacatorul modifică viteza după ce pachetul a fost semnat
    data["speed"] = 150.0

    assert SecurityManager.is_payload_valid(data, "Semafor_Centru") == False


def test_security_expired_payload():
    """Testăm anti-ghosting-ul: pachetele mai vechi de 2.0 secunde trebuie respinse."""
    data = {
        "agent_id": "Masina_Test",
        "position_x": 100.0,
        "position_y": 200.0,
        "speed": 50.0,
        "timestamp": time.time() - 3.0,  # Generat acum 3 secunde
    }
    data["signature"] = SecurityManager.sign_data(data)

    assert SecurityManager.is_payload_valid(data, "Semafor_Centru") == False


def test_vehicle_agent_initialization(mocker):
    """Testăm dacă un vehicul se inițializează corect (fără să facem call la API-ul Groq)."""
    # Mock-uim ChatGroq pentru a nu folosi rețeaua/API Key-ul
    mocker.patch("vehicle_agent.ChatGroq")

    agent = VehicleAgent("Car_1", "W_START", "E_END", desired_speed=60.0)

    assert agent.agent_id == "Car_1"
    assert agent.desired_speed == 60.0
    assert agent.current_state == "CRUISE"


def test_vehicle_agent_ambulance_priority(mocker):
    """Testăm dacă mașina normală trage pe dreapta (-35.0) când vede o ambulanță în spate."""
    mocker.patch("vehicle_agent.ChatGroq")

    agent = VehicleAgent("Car_1", "W_START", "E_END", desired_speed=60.0)

    # Forțăm valorile direct pe agent pentru a ocoli starea inițială "rece" a navigației
    mocker.patch(
        "vehicle_agent.VehicleAgent.heading",
        new_callable=mocker.PropertyMock,
        return_value="EAST",
    )
    mocker.patch(
        "vehicle_agent.VehicleAgent.visual_angle",
        new_callable=mocker.PropertyMock,
        return_value=0.0,
    )

    # Setăm poziția folosind setter-ul propriu al agentului (care actualizează și base_x)
    agent.position_x = 100.0
    agent.position_y = 675.0

    # Îi introducem artificial ambulanța în memoria V2X, fix în spatele ei
    agent.memory["Ambulanta_VIP"] = {
        "agent_id": "Ambulanta_VIP",
        "vehicle_type": "Ambulance",
        "position_x": 50.0,
        "position_y": 675.0,
        "heading": "EAST",
    }

    agent.decide_action(400, 650, ai_global_enabled=True)

    assert agent.target_lane_offset == -35.0
