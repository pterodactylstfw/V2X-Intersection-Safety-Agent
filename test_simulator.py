import pytest
import time
from v2x_security import SecurityManager
from v2x_network import V2XBroker
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


def test_vehicle_agent_ambulance_opposite_priority(mocker):
    """Testăm dacă mașina trage pe dreapta când vede o ambulanță venind din sens OPUS."""
    mocker.patch("vehicle_agent.ChatGroq")
    agent = VehicleAgent("Car_1", "E_START", "W_END", desired_speed=60.0)

    mocker.patch(
        "vehicle_agent.VehicleAgent.heading",
        new_callable=mocker.PropertyMock,
        return_value="WEST",
    )
    mocker.patch(
        "vehicle_agent.VehicleAgent.visual_angle",
        new_callable=mocker.PropertyMock,
        return_value=180.0,
    )

    agent.position_x = 200.0
    agent.position_y = 635.0

    # Injectăm ambulanța în fața ei pe contrasens (venind spre Est)
    agent.memory["Ambulanta_VIP"] = {
        "agent_id": "Ambulanta_VIP",
        "vehicle_type": "Ambulance",
        "position_x": 100.0,
        "position_y": 675.0,
        "heading": "EAST",
    }

    agent.decide_action(400, 650, ai_global_enabled=True)

    assert agent.target_lane_offset == -35.0


def test_vehicle_agent_red_light(mocker):
    """Testăm dacă mașina frânează corect la culoarea ROȘU a semaforului (V2I)."""
    mocker.patch("vehicle_agent.ChatGroq")
    agent = VehicleAgent("Car_1", "W_START", "E_END", desired_speed=60.0)

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

    # O punem destul de aproape de intersecția de la X=400
    agent.position_x = 320.0
    agent.position_y = 675.0

    # Injectăm semaforul în memorie
    agent.memory["Semafor_Centru"] = {
        "agent_id": "Semafor_Centru",
        "vehicle_type": "Infrastructure",
        "state_NS": "GREEN",
        "state_EW": "RED",  # Roșu pe direcția ei (Est-Vest)
        "time_to_change": 3.0,
        "position_x": 400.0,
        "position_y": 400.0,
    }

    agent.decide_action(400, 650, ai_global_enabled=True)

    # Verificăm dacă a detectat semaforul și a trecut în stare de frânare
    assert agent.current_state == "BRAKING"


def test_vehicle_agent_acc_braking(mocker):
    """Testăm dacă frânarea de siguranță (ACC) se activează când o mașină e prea aproape de lider."""
    mocker.patch("vehicle_agent.ChatGroq")
    agent = VehicleAgent("Car_Fast", "W_START", "E_END", desired_speed=80.0)

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

    agent.position_x = 100.0
    agent.position_y = 675.0

    # Injectăm o mașină lentă la doar 40 de pixeli în fața ei
    agent.memory["Car_Slow"] = {
        "agent_id": "Car_Slow",
        "vehicle_type": "Normal",
        "position_x": 140.0,
        "position_y": 675.0,
        "speed": 20.0,
        "heading": "EAST",
        "visual_angle": 0.0,
    }

    agent.decide_action(400, 650, ai_global_enabled=True)

    assert agent.current_state == "BRAKING"
    assert agent.speed < 80.0  # Viteza trebuie să fi scăzut automat


def test_vehicle_agent_animal_obstacle(mocker):
    """Testăm frânarea de urgență la detecția unui animal pe carosabil."""
    mocker.patch("vehicle_agent.ChatGroq")
    agent = VehicleAgent("Car_1", "W_START", "E_END", desired_speed=60.0)

    mocker.patch(
        "vehicle_agent.VehicleAgent.heading",
        new_callable=mocker.PropertyMock,
        return_value="EAST",
    )

    agent.position_x = 100.0
    agent.position_y = 675.0

    # Injectăm căprioara la 50 de metri în fața mașinii
    agent.memory["Caprioara"] = {
        "agent_id": "Caprioara",
        "vehicle_type": "Animal",
        "position_x": 150.0,
        "position_y": 675.0,
    }

    agent.decide_action(400, 650, ai_global_enabled=True)

    assert agent.current_state == "BRAKING"


def test_vehicle_agent_crashed_state(mocker):
    """Testăm dacă o mașină implicată într-un accident (CRASHED) paralizează corect."""
    mocker.patch("vehicle_agent.ChatGroq")
    agent = VehicleAgent("Car_1", "W_START", "E_END", desired_speed=60.0)

    agent.is_crashed = True
    agent.decide_action(400, 650, ai_global_enabled=True)

    assert agent.speed == 0.0
    assert agent.current_state == "CRASHED"


def test_v2x_broker_isolation():
    """Testăm dacă brokerul izolează pachetele (vehiculul nu își primește propriul mesaj)."""
    broker = V2XBroker()
    broker.publish("Masina_A", {"speed": 50.0})
    broker.publish("Masina_B", {"speed": 40.0})

    # Mașina A ascultă rețeaua
    traffic_for_a = broker.receive("Masina_A")

    assert "Masina_A" not in traffic_for_a
    assert "Masina_B" in traffic_for_a


def test_ai_negotiation_brake(mocker):
    """Testăm dacă vehiculul procesează corect comanda AI de a frâna la cedează trecerea."""
    mocker.patch("vehicle_agent.ChatGroq")
    agent = VehicleAgent("Car_1", "W_START", "E_END", desired_speed=60.0)

    # Simulăm că AI-ul i-a spus să frâneze și timpul se află în interiorul cooldown-ului (1 secundă)
    agent.last_ai_decision = "FRANEAZA"
    agent.last_ai_call_time = time.time()

    agent._negotiate_ai("Car_Other", {})

    assert agent.speed < 60.0  # Vehiculul ar trebui să piardă viteză
