# 🚦 Smart City C-V2X Simulator

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Pygame](https://img.shields.io/badge/Pygame-2.5.6-green.svg)](https://www.pygame.org/)
[![AI Powered](https://img.shields.io/badge/AI-LLaMA_3.1-orange.svg)]()

Un simulator de trafic autonom de ultimă generație creat pentru a demonstra puterea rețelelor **V2X (Vehicle-to-Everything)** într-un Smart City. Proiectul folosește Inteligență Artificială (LLM) pentru luarea deciziilor în timp real, algoritmi de rutare dinamică și un sistem fizic avansat pentru a simula un trafic fluid, sigur și predictibil.

---

## ✨ Funcționalități Principale

- 🧠 **Creier Autonom (AI & V2V):** Mașinile comunică între ele criptat (cu semnătură digitală). Cedează trecerea, negociază la intersecții folosind LLaMA 3.1 și previn coliziunile prin Adaptive Cruise Control (ACC).
- 🚥 **Infrastructură Inteligentă (V2I - GLOSA):** Semafoarele comunică timpul rămas până la schimbarea culorii. Mașinile își ajustează viteza din timp pentru a prinde "unda verde", reducând emisiile și frânările bruște.
- 🗺️ **Rerutare Dinamică (Waze-style Bypass):** La detectarea unui accident, vehiculele trec fluid pe contrasens pentru a ocoli obstacolul, revenind apoi pe banda lor.
- 🦌 **Detecție Animale Sălbatice:** Sistemul reacționează instantaneu la apariția obstacolelor imprevizibile (ex: căprioare pe carosabil), oprind vehiculele în condiții de siguranță.
- 📊 **C-V2X Command Center (HUD Live):** Dashboard transparent care afișează în timp real telemetria: număr vehicule, viteză medie, rata de pachete (ping) și intervenții AI (frânări salvatoare).
- 🎭 **Stiluri de Condus:** Suport pentru șoferi "Cautious" (Precauți) și "Aggressive" (Agresivi - ex: Ambulanțe), care forțează intersecțiile și au timpi de reacție diferiți.

---

## 💥 Funcția "AI OFF" (The Hackathon Showcase)

Cea mai importantă demonstrație a simulatorului:
- **AI ON (Verde):** Sistemul este activ. Mașinile colaborează perfect, ocolesc obstacole, respectă distanța de siguranță și adaptează viteza. Traficul este 100% fluid.
- **AI OFF (Roșu):** Rețeaua V2X cade. Vehiculele devin simple obiecte care merg "orbește" înainte. Ignoră prioritatea, semafoarele și obstacolele, generând coliziuni în lanț (randate cu efecte de explozie 🔥), demonstrând necesitatea vitală a sistemului nostru.

---

## 🛠️ Arhitectură și Tehnologii

- **Interfață Grafică:** `Pygame` (Glassmorphism UI, randare antialiased).
- **Rutare și Grafuri:** Algoritmul Dijkstra prin librăria `NetworkX` pentru navigarea hărții.
- **LLM / AI:** `LangChain` și `Groq API` (model LLaMA 3.1-8B-Instant) pentru deciziile complexe de prioritate și generarea dinamică a traficului.
- **Securitate V2X:** Pachete de date hașurate prin `SHA-256` pentru a preveni atacurile de tip *spoofing* în rețeaua auto.

---

## ⚙️ Instalare și Rulare

1. **Clonează repository-ul:**
   ```bash
   git clone [https://github.com/](https://github.com/)[nume-utilizator]/[nume-repo].git
   cd [nume-repo]
   ```

2. **Creează un mediu virtual și instalează dependențele:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Pe Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```
    (Dependențe principale: pygame, networkx, python-dotenv, langchain-groq)

3. **Configurează API Key-ul:**
Creează un fișier .env în rădăcina proiectului și adaugă cheia de la Groq:

    ```fragment
    GROQ_API_KEY=cheia_ta_secreta_aici
    ```

4. **Pornește Simulatorul:**
    ```bash
    python main.py
    ```


🎮 **Controale Interfață**
- SISTEM ON/OFF: Oprește infrastructura (semafoarele trec pe galben intermitent).

- AI ON/OFF: Activează/Dezactivează inteligența mașinilor și comunicarea V2X.

- SPAWN CĂPRIOARĂ: Trimite un animal pe carosabil pentru testarea frânării de urgență.

- SPAWN AI CAR: Directorul de trafic analizează harta și introduce dinamic o mașină nouă pentru a evita blocajele.

Echipa: [Trifecta], fondată din membrii Andaraș Bianca-Diana, Aranyosi Rebeka-Imola, Constantin Raul-Nicolae.
