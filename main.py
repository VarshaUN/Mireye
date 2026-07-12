import asyncio
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq

from Mireye.mireye_client import MireyeMCPClient
from Mireye.candidates import CANDIDATES
from Mireye.scoring import score_site

load_dotenv()


async def evaluate_candidate(mireye, candidate):
    raw = await mireye.call_tool(
        "mireye_fetch",
        {"lat": candidate["lat"], "lng": candidate["lng"], "preset": "site_selection"},
    )
    data = json.loads(raw)
    fields = data.get("fields", data)
    result = score_site(fields)
    return {
        "name": candidate["name"],
        "lat": candidate["lat"],
        "lng": candidate["lng"],
        "score": result["score"],
        "reasons": result["reasons"],
        "citations": result["citations"],
    }


def normalize_scores(results):
    scores = [r["score"] for r in results]
    lo, hi = min(scores), max(scores)
    span = (hi - lo) or 1
    for r in results:
        r["display_score"] = round(((r["score"] - lo) / span) * 100)
    return results


async def write_rationale(llm, ranked):
    top = ranked[:3]
    prompt = (
        "You are writing a short site-selection report for a coffee shop. "
        "For each of these top 3 candidate locations, write ONE sentence explaining "
        "why it ranks where it does relative to the others. ONLY use the exact facts "
        "given below — cite real numbers, never invent or vaguely gesture at them.\n\n"
    )
    for i, site in enumerate(top, 1):
        prompt += f"{i}. {site['name']}\n   Facts: {'; '.join(site['reasons'])}\n"

    response = await llm.ainvoke(prompt)
    return response.content


async def main():
    mireye = MireyeMCPClient()
    await mireye.start()
    print(f"Evaluating {len(CANDIDATES)} candidates...\n")

    results = await asyncio.gather(*[evaluate_candidate(mireye, c) for c in CANDIDATES])
    ranked = normalize_scores(sorted(results, key=lambda r: r["score"], reverse=True))

    print("=== Ranked results ===")
    for i, site in enumerate(ranked, 1):
        print(f"{i}. {site['name']} — score {site['display_score']}/100")
        for reason in site["reasons"]:
            print(f"   - {reason}")
        print()

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    print("=== AI-written rationale (top 3) ===")
    print(await write_rationale(llm, ranked))

    await mireye.close()
    return ranked


if __name__ == "__main__":
    asyncio.run(main())