# 🚦 Smart City C-V2X Simulator

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Pygame](https://img.shields.io/badge/Pygame-2.5.6-green.svg)](https://www.pygame.org/)
[![AI Powered](https://img.shields.io/badge/AI-LLaMA_3.1-orange.svg)]()

Built by **Team Trifecta** (Andaraș Bianca-Diana, Aranyosi Rebeka-Imola, Constantin Raul-Nicolae)

🥈 2nd Place Winning Project

A state-of-the-art autonomous traffic simulator created to demonstrate the power of **V2X (Vehicle-to-Everything)** networks in a Smart City. The project leverages Large Language Models (LLMs) for real-time decision making, dynamic routing algorithms, and an advanced physics engine to simulate fluid, safe, and predictable traffic.

---

## ✨ Key Features

- 🧠 **Autonomous Brain (AI & V2V)**: Vehicles communicate with each other using digitally signed, encrypted packets. They yield, negotiate intersection right-of-way using LLaMA 3.1, and prevent collisions via Adaptive Cruise Control (ACC).
- 🚥 **Smart Infrastructure (V2I - GLOSA)**: Traffic lights broadcast the remaining time until color changes. Vehicles adjust their speed in advance to catch the "green wave," reducing carbon emissions and harsh braking.
- 🗺️ **Dynamic Rerouting (Waze-style Bypass)**: Upon detecting an accident ahead, vehicles fluidly switch to the oncoming lane to bypass the obstacle before returning to their original lane.
- 🦌 **Wildlife Detection**: The system reacts instantly to unpredictable physical obstacles (e.g., deer on the road), executing emergency braking to stop vehicles safely.
- 📊 **C-V2X Command Center (Live HUD)**: A transparent dashboard displaying real-time telemetry: active vehicle count, average speed, packet rate (ping), and AI interventions (life-saving brakes).
- 🎭 **Driving Styles**: Support for both "Cautious" and "Aggressive" drivers (e.g., Ambulances), featuring different reaction times and priority forcing.

---

## 💥 The "AI OFF" Showcase (Hackathon Highlight)

Cea mai importantă demonstrație a simulatorului:
- 🟢 **AI ON (Green)**: The V2X system is fully active. Vehicles collaborate perfectly, avoid obstacles, maintain safe distances, and adapt speeds. Traffic is 100% fluid.
- 🔴 **AI OFF (Red)**: The V2X network goes dark. Vehicles revert to "blind" objects moving rigidly forward. They ignore right-of-way, traffic lights, and obstacles, resulting in chain collisions (rendered with 🔥 explosion effects)—proving the absolute necessity of our V2X architecture.

---

## 🛠️ Architecture & Technologies

- **Graphical Interface**: Pygame (Glassmorphism UI, anti-aliased rendering).
- **Routing & Graphs**: Dijkstra's algorithm via the NetworkX library for map navigation.
- **LLM / AI**: LangChain and Groq API (LLaMA 3.1-8B-Instant model) for complex right-of-way decisions and dynamic traffic generation.
- **V2X Security**: Data packets are hashed using SHA-256 to prevent spoofing and cyber attacks on the vehicle network.

---

## ⚙️ Installation & Running
1. **Clone the repository:**
   ```bash
   git clone https://github.com/pterodactylstfw/V2X-Intersection-Safety-Agent.git
   cd V2X-Intersection-Safety-Agent
   ```

2. **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Or, on Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```
    (Main dependencies: pygame, networkx, python-dotenv, langchain-groq)

3. **Configure the API Key:**
Create a .env file in the root directory and add your Groq API key:

    ```fragment
    GROQ_API_KEY=cheia_ta_secreta_aici
    ```

4. **Start the Simulator:**
    ```bash
    python main.py
    ```


🎮 **UI Controls**
- SYSTEM ON/OFF: Shuts down the city infrastructure (traffic lights switch to flashing yellow).

- AI ON/OFF: Toggles the vehicles' V2X communication and AI brains (triggers the chaos mode).

- SPAWN DEER: Spawns a wild animal on the road to test the emergency braking systems.

- SPAWN AI CAR: The AI Traffic Director analyzes the map and dynamically spawns a new vehicle to maintain traffic diversity without causing instant gridlocks.
