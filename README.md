# Coffee Shop Site-Selection Agent

A LangGraph agent that evaluates candidate coffee shop locations using [Mireye](https://mireye.com)'s geospatial API/MCP server  and returns a ranked, cited recommendation instead of a guess.

**Live demo:** https://mireye.onrender.com/rank
*(free-tier instance , first request after inactivity can take 30-50s to wake up)*

## What it does

Give it a handful of candidate coordinates in a city. For each one, it:

1. Calls Mireye's `mireye_fetch` tool (via their MCP server) with the `site_selection` preset
2. Scores each location on a deterministic rubric — terrain flatness, flood risk, road proximity, POI density, housing density, zoning, wetlands/protected areas
3. Has an LLM (Groq/Llama 3.3) write a short rationale for the top 3  constrained to only reference facts it was actually given
4. Returns everything ranked, with every claim traceable back to a specific field, value, and data source

Example output for one site:
```
"very high foot-traffic-adjacent density (751 POIs within 1km)"
→ poi_count_1km = 751 [OVERTURE_PLACES]
```


## A gap I found along the way

Mireye's field catalog has no direct foot-traffic or competitor-density signal which matters for retail siting. I used `poi_count_1km` and `housing_units_within_1km` as a proxy instead of inventing numbers that don't exist. The agent is instructed to say so explicitly rather than silently overclaim. (A `retail_siting` preset combining these with nearest-competitor distance could be a nice addition , happy to talk through this if useful.)

## Architecture

```
Candidates (lat/lng) 
   → LangGraph agent → Mireye MCP (mireye_fetch, site_selection preset)
   → deterministic scoring (scoring.py)
   → LLM rationale (Groq, grounded in returned facts only)
   → ranked JSON with citations
```

Built with `langgraph`, `mcp`, `langchain-groq`, `fastapi`. MCP client (`mireye_client.py`) speaks the protocol directly over stdio rather than through a higher-level wrapper.

## Running it locally

```bash
uv pip install -r requirements.txt
mireye-mcp login          # one-time auth with Mireye
python main.py             # terminal output
# or
python run.py               # serves the same thing at /rank
```

Needs `GROQ_API_KEY` in a `.env` file.

## Stack

Python · LangGraph · Mireye MCP · FastAPI · Groq (Llama 3.3) · deployed on Render
