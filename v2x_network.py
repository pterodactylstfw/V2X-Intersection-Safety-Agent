import threading
import time
import json

class V2XBroker:
    def __init__(self):
        # dictionar in care salvez starea masinilor
        # cheia este id ul iar valoarea pachetul ei de date
        self.vehicles_status = {}

        # lacătul care ne asigură că doar un singur fir de execuție
        # (thread) poate citi sau scrie în dicționar la un moment dat
        self.lock = threading.Lock()
    
    def publish(self, vehicle_id: str, data_package: dict):
        """
        Primește un pachet de date de la un vehicul și îl salvează în rețea.
        Folosim lacătul pentru a ne asigura că nimeni nu citește datele exact
        în milisecunda în care noi le scriem.
        """
        # Instrucțiunea 'with' ia lacătul automat. 
        # Cât timp suntem în acest bloc indentat, niciun alt thread nu poate accesa dictionarul.
        with self.lock:
            # Salvăm sau actualizăm pachetul de date pentru acest ID
            self.vehicles_status[vehicle_id] = data_package
            
        # Odată ce ieșim din blocul 'with', Python eliberează automat lacătul,
        # permițând altor mașini sau interfeței UI să interacționeze cu brokerul.

    def receive(self, requesting_vehicle_id: str) -> dict:
        """
        Returnează stările tuturor celorlalte vehicule din rețea.
        Excludem vehiculul care face cererea, deoarece nu are nevoie 
        să se ferească de el însuși.
        """
        # Folosim din nou lacătul. Nimeni nu poate citi datele dacă altcineva
        # le scrie/modifică fix în acel moment.
        with self.lock:
            # Creăm un dicționar nou ('un raport') în care vom pune doar CELELALTE mașini
            surrounding_traffic = {}
            
            # Ne uităm la fiecare mașină din avizierul nostru
            for v_id, data in self.vehicles_status.items():
                # Dacă ID-ul mașinii pe care o citim NU este ID-ul celui care a cerut datele...
                if v_id != requesting_vehicle_id:
                    # ...atunci o adăugăm în raport
                    surrounding_traffic[v_id] = data
                    
            return surrounding_traffic


class DataFeeder:
    def __init__(self, broker: V2XBroker, file_path: str):
        """
        Alimentatorul are nevoie de 2 lucruri:
        1. broker-ul in care sa publice datele
        2. calea catre fisierul .json cu scenariul
        """
        self.broker = broker
        self.file_path = file_path
        self.scenario_data = []

    def load_scenario(self):
        """Citeste fisierul JSON de pe hard disk si il incarca in memorie."""
        try:
            with open(self.file_path, 'r') as file:
                self.scenario_data = json.load(file)
            print(f"[Feeder] Scenariu incarcat cu succes! Contine {len(self.scenario_data)} cadre.")
        except FileNotFoundError:
            print(f"[Eroare] Fisierul {self.file_path} nu a fost gasit!")

    def play_scenario(self, delay_seconds: float = 0.5):
        """
        Parcurge scenariul cadru cu cadru si publica datele in V2XBroker.
        Pune pauza (delay_seconds) intre cadre pentru a simula trecerea timpului.
        """
        print("[Feeder] Incepem redarea scenariului...")
        
        # Iterăm prin fiecare cadru (frame) din filmul nostru
        for numar_cadru, vehicule_in_cadru in enumerate(self.scenario_data):
            
            # Pentru fiecare masina din acel cadru, ii publicam starea in broker
            for stare_vehicul in vehicule_in_cadru:
                id_masina = stare_vehicul["agent_id"]
                
                # Aici folosim functia scrisa de tine anterior!
                self.broker.publish(id_masina, stare_vehicul)
            
            # Printam in consola sa vedem ca functioneaza (optional)
            print(f" -> Cadrul {numar_cadru} a fost publicat.")
            
            # MAGIA: Punem programul pe pauza. Asta permite UI-ului sa redeseneze 
            # ecranul si AI-ului sa citeasca noile date si sa gandeasca.
            time.sleep(delay_seconds)
            
        print("[Feeder] Scenariul s-a terminat!")