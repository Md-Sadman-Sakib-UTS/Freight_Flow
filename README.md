# Freight_Flow

Freight_Flow is a **modular, multi-agent route-planning system** built with Streamlit.  
It ingests live traffic, hazard, toll and cost data to recommend the most efficient freight routes within **New South Wales, Australia**.

Designed for **logistics planners, fleet operators, researchers and educators**, Freight_Flow offers an extensible backend and an intuitive web UI so that you can experiment, integrate and deploy quickly.

---

## Table of Contents
1. [Key Features](#key-features)  
2. [System Architecture](#system-architecture)  
3. [Quick Start](#quick-start)  
4. [Configuration](#configuration)  
5. [How to Use the App](#how-to-use-the-app)  
6. [Project Structure](#project-structure)  
7. [Extending Freight_Flow](#extending_freight_flow)  
8. [Contributing](#contributing)  
9. [License](#license)  
10. [Author](#author)

---

## Key Features

| Category | Description |
|----------|-------------|
| **Multi-Agent Decision Engine** | Combines specialised agents—**Cost**, **Risk**, **Emission**, **Hazard**, **Traffic**, **Toll**—to score candidate routes from complementary viewpoints. |
| **Real-Time Data Sources** | Fetches live directions & traffic from **Mapbox Directions** and **Traffic NSW**, and toll information from **TfNSW Toll API**. |
| **Hazard Awareness** | Automatically avoids floods, crashes and roadworks by overlaying incident feeds onto the route graph. |
| **Carbon-Aware Planning** | Estimates CO₂ emissions and can minimise environmental impact when the emission agent is enabled. |
| **Streamlit Frontend** | One-click deployment; the UI shows an interactive map, KPIs and a decision explanation table. |
| **Plug-and-Play Backend** | Agents are plain Python classes—add, remove or customise them without touching the UI. |

---

## System Architecture

```
┌──────────────┐       APIs           ┌──────────────┐
│ Streamlit UI │◀────────────────────▶│  Mapbox      │
└──────────────┘                      └──────────────┘
        ▲                                   ▲
        │ Websocket / Callback              │ HTTPS
        ▼                                   ▼
┌────────────────────────────────────────────────────┐
│                Decision Controller                │
│  (orchestrates agents & selects best route)       │
└────────────────────────────────────────────────────┘
        ▲            ▲              ▲
        │            │              │
┌───────┴───┐  ┌─────┴────┐   ┌─────┴────┐
│ CostAgent │  │ RiskAgent│   │ …others… │
└───────────┘  └──────────┘   └──────────┘
```

Each agent receives the same set of candidate routes and returns a **score**; the controller then applies a configurable weighting scheme to pick the optimal path.

---

## Quick Start

1. **Clone the repository**

   ```bash
   git clone https://github.com/Md-Sadman-Sakib-UTS/Freight_Flow.git
   cd Freight_Flow
   ```

2. **Create a virtual environment (recommended)**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # on Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Add your API keys**

   - Copy `.env.example` to `.env`.
   - Fill in your credentials:

     ```dotenv
     MAPBOX_TOKEN=<your_mapbox_token>
     TFNSW_API_KEY=<your_tfnsw_api_key>
     OPENAI_API_KEY=<optional_for_future_llm_features>
     VITE_MAPBOX_TOKEN=<duplicate_for_streamlit_components>
     ```

5. **Run the application**

   ```bash
   streamlit run app.py
   ```

   The web UI will open in your browser (default: <http://localhost:8501>).

---

## Configuration

| Variable | Required | Purpose |
|----------|----------|---------|
| `MAPBOX_TOKEN` | ✔ | Geocoding, routing and base-map tiles |
| `TFNSW_API_KEY` | ✔ | Toll pricing data |
| `OPENAI_API_KEY` |  | Reserved for future language-model agents |
| `VITE_MAPBOX_TOKEN` | ✔ | Needed by some Streamlit Mapbox components |

You can also tweak **agent weights, maximum search radius, fallback strategies** and more under `backend/config.py`.

---

## How to Use the App

1. **Origin & Destination** – Type any address or place in NSW (powered by Mapbox autocomplete).  
2. **Delivery Deadline** – Select the latest acceptable ETA.  
3. **Click “Find best route”** – The map updates with the chosen path, and a table explains how each agent influenced the decision.

### Example Scenario

> *A truck must leave Port Botany and deliver to Newcastle by 15:00. Hazards include heavy rain near Gosford and a crash on the M1.*  
>
> Freight_Flow will:
> 1. Query Mapbox for candidate routes.  
> 2. Discard routes crossing the crash location (RiskAgent) and flooded segments (HazardAgent).  
> 3. Compare remaining options on toll cost, expected fuel usage and CO₂ output.  
> 4. Display the recommended path, illustrating that paying a small toll to detour via the Hunter Expressway both saves 18 min and cuts 2 kg CO₂.

---

## Project Structure

```text
Freight_Flow/
├── app.py               # Streamlit entry point
├── backend/
│   ├── agents/          # Individual agent modules
│   │   ├── cost.py
│   │   ├── risk.py
│   │   ├── emission.py
│   │   ├── hazard.py
│   │   ├── traffic.py
│   │   └── toll.py
│   ├── controller.py    # Orchestrates agents
│   └── config.py        # Weights & global settings
├── data/                # Sample hazard feeds (git-ignored by default)
├── requirements.txt
├── .env.example
└── README.md
```

---


## Contributing

Contributions are welcome! Please open an issue to discuss major changes first.

```text
1. Fork   → 2. Create feature branch  → 3. Commit  → 4. Push  → 5. Pull Request
```

All pull requests must pass **flake8**, **pytest** and **mypy** checks. See `CONTRIBUTING.md` for guidelines.

---

## License

This repository is **private and for research / educational use only**.  
For commercial licensing, please contact the author.

---

## Author

**Md Sadman Sakib**   
✉️  <sadmansakib99876@gmail.com>
