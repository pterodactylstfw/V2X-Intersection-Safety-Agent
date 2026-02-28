import threading

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