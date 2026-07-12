from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mireye_client import MireyeMCPClient
from candidates import CANDIDATES
from scoring import score_site
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import json
import asyncio

load_dotenv()
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

mireye = MireyeMCPClient()
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


@app.on_event("startup")
async def startup():
    await mireye.start()


@app.on_event("shutdown")
async def shutdown():
    await mireye.close()


def normalize_scores(results):
    scores = [r["score"] for r in results]
    lo, hi = min(scores), max(scores)
    span = (hi - lo) or 1
    for r in results:
        r["display_score"] = round(((r["score"] - lo) / span) * 100)
    return results


async def evaluate(candidate):
    raw = await mireye.call_tool(
        "mireye_fetch",
        {"lat": candidate["lat"], "lng": candidate["lng"], "preset": "site_selection"},
    )
    try:
        fields = json.loads(raw).get("fields", {})
    except json.JSONDecodeError:
        print(f"Could not parse response for {candidate['name']}: {raw[:300]}", flush=True)
        fields = {}
    result = score_site(fields)
    return {**candidate, **result}


@app.get("/rank")
async def rank():
    results = await asyncio.gather(*[evaluate(c) for c in CANDIDATES])
    ranked = normalize_scores(sorted(results, key=lambda r: r["score"], reverse=True))

    top = ranked[:3]
    prompt = (
        "These sites are ALREADY ranked 1st, 2nd, 3rd in this exact order — do not reorder them. "
        "For each, in order, write ONE sentence using its position word (first/second/third) "
        "matching its list position below, citing only the facts given.\n\n"
    )
    for i, s in enumerate(top, 1):
        prompt += f"Position {i} ({'first' if i==1 else 'second' if i==2 else 'third'}): {s['name']}\n"
        prompt += f"  Facts: {'; '.join(s['reasons']) if s['reasons'] else 'no major flags'}\n\n"

    rationale = (await llm.ainvoke(prompt)).content

    return {"ranked": ranked, "rationale": rationale}


@app.get("/")
async def root():
    return {"status": "ok", "message": "Coffee shop site-selection agent — try GET /rank"}