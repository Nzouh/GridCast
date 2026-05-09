# GridCast — Team Split

## Person A: Data, ML, and Backend

- Set up accounts and API keys (EIA, Grid Status, IBM Cloud, Open-Meteo)
- Build data pipelines: pull historical EIA demand, Grid Status LMP, and Open-Meteo weather for the 4 nodes
- Train the Temporal Fusion Transformer on Colab (encoder 168h, decoder 240h, 5 quantiles)
- Validate model on 3 historical stress events (Texas 2021, PNW 2022, PJM 2023)
- Serialize model checkpoint and upload to IBM Cloud Object Storage
- Build FastAPI backend with the 5 API endpoints, containerize, and deploy to IBM Cloud Code Engine
- Wire up watsonx.ai for model serving (IBM prize integration)

## Person B: Frontend and UI

- Scaffold React + Vite + Tailwind app
- Build the interactive US map (Mapbox GL JS) with the 4 node markers
- Build all charts and time-series plots: 10-day forecast ribbon, LMP history, fuel mix, stress timeline, allocation gauge, ensemble spread, scenario compare, weather overlay
- Develop against mock JSON files (`MOCK_MODE=true`) matching the API contract
- Swap mock flag to live IBM URL on integration day

## Boundary

The API contract (5 endpoint shapes) is the handoff point. Person B mocks locally; Person A delivers the real backend. Integration = one env variable swap.
