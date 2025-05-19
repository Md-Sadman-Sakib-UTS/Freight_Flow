# Freight_Flow

**Freight_Flow** is a modular Streamlit application for intelligent, multi-agent freight route optimization. It leverages real-time traffic, hazard, toll, and cost data to recommend optimal freight routes in NSW, Australia. Designed for logistics, operations, and research use.

---

## Features

- **Multi-Agent System**: Route decisions use a blend of agents (cost, risk, emission, hazard, traffic, etc.).
- **Real Data Sources**: Integrates Mapbox Directions, Mapbox Geocoding, and TfNSW Toll APIs.
- **Hazard & Traffic Awareness**: Avoids hazards (floods, crashes) and live traffic incidents.
- **CO₂ & Cost Optimization**: Considers emissions and tolls in decision-making.
- **Streamlit UI**: Intuitive frontend for input, visualization, and decision table.
- **Extensible Backend**: Easy to add more agents for future needs.

---

## Quick Start

1. **Clone the Repository**
    ```sh
    git clone https://github.com/Md-Sadman-Sakib-UTS/Freight_Flow.git
    cd Freight_Flow
    ```

2. **Install Dependencies**
    ```sh
    pip install -r requirements.txt
    ```

3. **Set up Environment Variables**
    - Copy `.env.example` to `.env` and set your API keys (Mapbox, TfNSW, etc.).
    - Example:
      ```
      MAPBOX_TOKEN=your_mapbox_token
      TFNSW_API_KEY=your_tfnsw_api_key
      OPENAI_API_KEY=your key
      VITE_MAPBOX_TOKEN= your key
      ```

4. **Run the App**
    ```sh
    streamlit run app.py
    ```

---

## Project Structure

Freight_Flow/
├── app.py                 # Main Streamlit app
├── backend/               # Agents and backend logic
│   └── agents/
│       ├── cost.py
│       ├── risk.py
│       ├── toll.py
│       ├── hazard.py
│       ├── emission.py
│       └── …
├── data/                  # Hazard and other data files (can be .gitignored for privacy)
├── requirements.txt
├── .env.example
└── README.md




---

## Usage

1. **Set Origin and Destination**
   - Use the search boxes to pick places in NSW.
2. **Set Delivery Deadline**
   - Choose maximum allowed ETA in the sidebar.
3. **Find Best Route**
   - Click “Find best route” and review the map, table, and decision explanations.

---

## API Keys

You need your own [Mapbox](https://account.mapbox.com/) and [TfNSW](https://api.transport.nsw.gov.au/) API keys.
- **MAPBOX_TOKEN**: For maps and geocoding.
- **TFNSW_API_KEY**: For toll calculations.

---

## Notes

- **Private Repo**: This code is for educational/demo purposes. Do not publish or share API keys.
- **Data**: If you have privacy requirements, consider adding `data/` to `.gitignore`.
- **Extending**: You can add new agents by creating additional modules in `backend/agents/`.

---

## License

This project is for private and research use only. For other uses, contact the repository owner.

---

## Author

**Md Sadman Sakib**  
[sadmansakib99876@gmail.com](mailto:sadmansakib99876@gmail.com)

---