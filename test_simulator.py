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


def test_ambulance_prevent_head_on_overtake(mocker):
    """Testăm dacă o ambulanță renunță la depășirea pe contrasens când vine altă mașină frontal."""
    mocker.patch("vehicle_agent.ChatGroq")
    agent = VehicleAgent(
        "Amb_Test",
        "W_START",
        "E_END",
        desired_speed=80.0,
        vehicle_type="Ambulance",
        driving_style="Aggressive",
    )

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
    agent.speed = 80.0

    # Obstacol lent în față (ar declanșa depășirea în mod normal)
    agent.memory["Slow_Car"] = {
        "vehicle_type": "Normal",
        "position_x": 150.0,  # La 50px în fața ambulanței
        "position_y": 675.0,
        "speed": 20.0,
        "heading": "EAST",
    }

    # Altă ambulanță venind frontal pe contrasens, de la o distanță de 200px
    agent.memory["Opposite_Amb"] = {
        "vehicle_type": "Ambulance",
        "position_x": 300.0,
        "position_y": 675.0,
        "speed": 80.0,
        "heading": "WEST",
    }

    agent.decide_action(400, 650, ai_global_enabled=True)

    # Verificăm că a abandonat mutarea pe stânga (offset 40.0) și a rămas pe banda ei
    assert agent.target_lane_offset == 0.0
    # Trebuie să frâneze de urgență în spatele mașinii lente, pentru că nu o poate ocoli
    assert agent.current_state == "BRAKING"


def test_ambulance_vs_ambulance_intersection(mocker):
    """Testăm dacă o ambulanță cedează trecerea altei ambulanțe în intersecție (Tie-breaker ID/Distanță)."""
    mocker.patch("vehicle_agent.ChatGroq")
    # Amb_B are ID-ul mai 'mare' alfabetic, deci ar trebui să cedeze la egalitate de distanță.
    agent = VehicleAgent(
        "Amb_B", "W_START", "E_END", desired_speed=80.0, vehicle_type="Ambulance"
    )

    mocker.patch(
        "vehicle_agent.VehicleAgent.heading",
        new_callable=mocker.PropertyMock,
        return_value="EAST",
    )
    agent.position_x = 350.0
    agent.position_y = 650.0
    agent.speed = 80.0

    agent.memory["Amb_A"] = {
        "agent_id": "Amb_A",
        "vehicle_type": "Ambulance",
        "position_x": 400.0,
        "position_y": 700.0,  # Aceeași distanță față de centru (400,650)
        "heading": "NORTH",
        "target_int": (400, 650),
    }

    agent.decide_action(400, 650, ai_global_enabled=True)

    # Amb_B trebuie să fi decis să frâneze pentru a o lăsa pe Amb_A să treacă prima
    assert agent.current_state == "BRAKING"


def test_intersection_right_of_way(mocker):
    """Testăm reflexul de Prioritate de Dreapta la o intersecție nedirijată."""
    mocker.patch("vehicle_agent.ChatGroq")
    agent = VehicleAgent("Car_1", "W_START", "E_END", desired_speed=60.0)

    # Noi mergem spre EST
    mocker.patch(
        "vehicle_agent.VehicleAgent.heading",
        new_callable=mocker.PropertyMock,
        return_value="EAST",
    )
    agent.position_x = 320.0
    agent.position_y = 650.0

    # Celălalt vine dinspre Sud și merge spre NORD (adică vine din DREAPTA noastră)
    agent.memory["Car_2"] = {
        "agent_id": "Car_2",
        "vehicle_type": "Normal",
        "position_x": 400.0,
        "position_y": 730.0,
        "heading": "NORTH",
        "target_int": (400, 650),
        "speed": 50.0,
    }

    agent.decide_action(400, 650, ai_global_enabled=True)

    # Mașina 1 trebuie să se fi oprit pentru a ceda trecerea celei din dreapta
    assert agent.current_state == "BRAKING"


def test_no_pull_over_inside_intersection(mocker):
    """Verificăm ca mașina SĂ NU tragă pe dreapta (slide) dacă e surprinsă direct în intersecție de ambulanță."""
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

    # Punem mașina FOARTE aproape de centrul intersecției (în interiorul zonei de 85px)
    agent.position_x = 380.0
    agent.position_y = 650.0

    agent.memory["Ambulanta_Spate"] = {
        "agent_id": "Ambulanta_Spate",
        "vehicle_type": "Ambulance",
        "position_x": 300.0,
        "position_y": 650.0,
        "heading": "EAST",
    }

    agent.decide_action(400, 650, ai_global_enabled=True)

    # Distanța până la (400, 650) este de 20px (< 85px), deci mașina trebuie să își păstreze trasa dreaptă!
    assert agent.target_lane_offset == 0.0


def test_safe_re_entry_yielding(mocker):
    """Testăm dacă o mașină trasă pe dreapta așteaptă trecerea traficului înainte de a reintra pe bandă."""
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

    # Mașina se află pe drum (departe de intersecție) și este trasă pe dreapta deja
    agent.position_x = 100.0
    agent.position_y = 650.0
    agent.target_lane_offset = -35.0
    agent.speed = 15.0

    # O mașină normală (nu ambulanță) vine cu viteză din spate
    agent.memory["Car_Fast"] = {
        "agent_id": "Car_Fast",
        "vehicle_type": "Normal",
        "position_x": 50.0,  # E la 50px distanță fix în spatele nostru
        "position_y": 650.0,
        "heading": "EAST",
    }

    agent.decide_action(400, 650, ai_global_enabled=True)

    # Agentul trebuie să rămână pe banda de urgență (-35.0) și să frâneze
    assert agent.target_lane_offset == -35.0
    assert agent.current_state == "BRAKING"


def test_glosa_speed_adaptation(mocker):
    """Testăm GLOSA (Green Light Optimized Speed Advisory): Reducerea fluidă a vitezei fără frânare bruscă."""
    mocker.patch("vehicle_agent.ChatGroq")
    agent = VehicleAgent("Car_1", "W_START", "E_END", desired_speed=60.0)
    mocker.patch(
        "vehicle_agent.VehicleAgent.heading",
        new_callable=mocker.PropertyMock,
        return_value="EAST",
    )

    agent.position_x = 200.0
    agent.position_y = 650.0
    agent.speed = 60.0

    # Semaforul va fi roșu încă 10 secunde
    agent.memory["Semafor_Centru"] = {
        "agent_id": "Semafor_Centru",
        "vehicle_type": "Infrastructure",
        "state_NS": "GREEN",
        "state_EW": "RED",
        "time_to_change": 10.0,
        "position_x": 400.0,
        "position_y": 400.0,
    }

    agent.decide_action(400, 650, ai_global_enabled=True)

    # Nu trebuie să intre în modul BRAKING dur, ci doar să taie 0.2 din accelerație pe cadru
    assert agent.current_state != "BRAKING"
    assert agent.speed == 59.8


def test_four_way_deadlock_resolution(mocker):
    """Testăm mecanismul anti-deadlock (Tie-Breaker) când 2 mașini sunt oprite și își cedează trecerea reciproc."""
    mocker.patch("vehicle_agent.ChatGroq")
    agent = VehicleAgent("Car_A", "W_START", "E_END", desired_speed=60.0)
    mocker.patch(
        "vehicle_agent.VehicleAgent.heading",
        new_callable=mocker.PropertyMock,
        return_value="EAST",
    )

    agent.position_x = 350.0
    agent.position_y = 650.0
    agent.speed = 0.0  # Mașina e deja oprită la intersecție

    # Cealaltă mașină e tot oprită și vine din DREAPTA (SUD -> NORD)
    agent.memory["Car_B"] = {
        "agent_id": "Car_B",
        "vehicle_type": "Normal",
        "position_x": 400.0,
        "position_y": 700.0,
        "heading": "NORTH",
        "target_int": (400, 650),
        "speed": 0.0,
    }

    agent.decide_action(400, 650, ai_global_enabled=True)

    # Din cauza ID-ului alfabetic ("Car_A" < "Car_B"), Car_A va ceda trecerea în tie-breaker
    assert agent.current_state == "BRAKING"


def test_zipper_merge_tie_breaker(mocker):
    """Testăm rezolvarea conflictelor egale la intersecțiile de tip Zipper Merge."""
    mocker.patch("vehicle_agent.ChatGroq")
    agent = VehicleAgent("Car_Y", "W_START", "E_END", desired_speed=60.0)
    mocker.patch(
        "vehicle_agent.VehicleAgent.heading",
        new_callable=mocker.PropertyMock,
        return_value="EAST",
    )

    # Merge point e (770, 455). Punem mașina fix la 20px de el.
    agent.position_x = 750.0
    agent.position_y = 455.0

    # Cealaltă mașină e la fix 20px pe altă axă
    agent.memory["Car_X"] = {
        "agent_id": "Car_X",
        "vehicle_type": "Normal",
        "position_x": 770.0,
        "position_y": 435.0,
        "heading": "SOUTH",
        "target_int": (770, 455),
    }

    agent.decide_action(770, 455, ai_global_enabled=True)

    # Deoarece ID Car_Y > Car_X și sunt la distanță egală (<=15 diferență), Y execută YIELD.
    assert agent.current_state == "BRAKING"


def test_animal_overrides_ambulance_priority(mocker):
    """Testăm ierarhia zero: o ambulanță respectă frânarea absolută la animale, ignorând prioritatea ei V2X."""
    mocker.patch("vehicle_agent.ChatGroq")
    agent = VehicleAgent(
        "Amb_1", "W_START", "E_END", desired_speed=80.0, vehicle_type="Ambulance"
    )
    mocker.patch(
        "vehicle_agent.VehicleAgent.heading",
        new_callable=mocker.PropertyMock,
        return_value="EAST",
    )

    agent.position_x = 100.0
    agent.position_y = 650.0

    agent.memory["Căprioară"] = {
        "agent_id": "Căprioară",
        "vehicle_type": "Animal",
        "position_x": 150.0,
        "position_y": 650.0,
    }

    agent.decide_action(400, 650, ai_global_enabled=True)
    assert agent.current_state == "BRAKING"


def test_aggressive_driver_ignores_yellow(mocker):
    """Testăm comportamentul de condus: Șoferii 'Aggressive' forțează semaforul Galben."""
    mocker.patch("vehicle_agent.ChatGroq")
    agent = VehicleAgent(
        "Car_Aggro", "W_START", "E_END", desired_speed=60.0, driving_style="Aggressive"
    )
    mocker.patch(
        "vehicle_agent.VehicleAgent.heading",
        new_callable=mocker.PropertyMock,
        return_value="EAST",
    )

    agent.position_x = 350.0
    agent.position_y = 650.0

    agent.memory["Semafor_Centru"] = {
        "agent_id": "Semafor_Centru",
        "vehicle_type": "Infrastructure",
        "state_NS": "RED",
        "state_EW": "YELLOW",
        "time_to_change": 2.0,
        "position_x": 400.0,
        "position_y": 400.0,
    }

    agent.decide_action(400, 650, ai_global_enabled=True)
    # Forțează trecerea, deci își menține viteza
    assert agent.turn_intent == "PRIORITY"
    assert agent.current_state == "CRUISE"


def test_close_proximity_ignores_right_priority(mocker):
    """Testăm dacă o mașină eliberează intersecția și ignoră prioritatea de dreapta dacă e deja în interiorul ei."""
    mocker.patch("vehicle_agent.ChatGroq")
    agent = VehicleAgent("Car_A", "W_START", "E_END", desired_speed=60.0)
    mocker.patch(
        "vehicle_agent.VehicleAgent.heading",
        new_callable=mocker.PropertyMock,
        return_value="EAST",
    )

    agent.position_x = 380.0
    agent.position_y = 650.0  # Este la doar 20px de centrul 400, 650

    # Oponentul vine din dreapta, dar e la 100px distanță (750-650)
    agent.memory["Car_B"] = {
        "agent_id": "Car_B",
        "vehicle_type": "Normal",
        "position_x": 400.0,
        "position_y": 750.0,
        "heading": "NORTH",
        "target_int": (400, 650),
    }

    agent.decide_action(400, 650, ai_global_enabled=True)
    assert agent.current_state == "CRUISE"  # Nu pune frână aiurea!


def test_corrupt_v2x_message_rejected():
    """Testăm siguranța rețelei: O structură V2X defectă (string în loc de număr) trebuie respinsă de manager."""
    data = {
        "agent_id": "Hacker_Car",
        "position_x": "nu_sunt_float",
        "position_y": 200.0,
        "speed": 50.0,
        "timestamp": time.time(),
    }
    data["signature"] = SecurityManager.sign_data(data)
    assert SecurityManager.is_payload_valid(data, "Semafor_Centru") == False


def test_acc_platooning_compression(mocker):
    """Testăm frânarea ACC într-un pluton (Platooning) pentru comprimare elegantă."""
    mocker.patch("vehicle_agent.ChatGroq")
    agent = VehicleAgent(
        "Car_Follower", "W_START", "E_END", desired_speed=60.0, driving_style="Cautious"
    )
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
    agent.position_y = 650.0
    agent.speed = 60.0

    # Liderul e la 50px în față, mergând încet cu 20.0
    agent.memory["Car_Leader"] = {
        "agent_id": "Car_Leader",
        "vehicle_type": "Normal",
        "position_x": 150.0,
        "position_y": 650.0,
        "heading": "EAST",
        "speed": 20.0,
        "visual_angle": 0.0,
    }

    agent.decide_action(400, 650, ai_global_enabled=True)
    assert agent.current_state == "BRAKING"
    assert agent.speed < 60.0
