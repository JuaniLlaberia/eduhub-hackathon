"""
End-to-end run through the real HTTP API: analysis -> report -> drafts -> simulation, per account, with and
without a creator brief. Records latency, AI cost per step (from the test-only /_e2e/usage route), failures and
quality checks. Usage: python e2e_api.py [base_url] [audience_size]
"""
import asyncio
import json
import sys
import time
import unicodedata
from pathlib import Path
import httpx

HERE = Path(__file__).parent
REPO = HERE.parents[3]
BRIEFS = REPO / "src/ai/docs/results/2026-10-31-e2e/briefs"
OUT = REPO / "src/ai/tests/data/real/reports/e2e-2026-10-31"
ACCOUNTS = ["bilinkis", "mercadolibre", "paulina_cocina", "valearvejita"]

def norm(text: str) -> str:
    """
    Lowercase and strip accents, for loose text checks.
    """
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")

def save(name: str, data: object) -> None:
    """
    Write data as pretty JSON into OUT.
    """
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=1))

async def usage(client: httpx.AsyncClient) -> dict:
    """
    Current AI usage totals.
    """
    resp = await client.get("/_e2e/usage")
    return resp.json() if resp.status_code == 200 else {"analyzer": None, "generator": None, "simulator": None}

def delta(before: dict, after: dict, name: str) -> dict:
    """
    Usage of one AI client between two snapshots.
    """
    b, a = before[name] or {}, after[name] or {}
    return {k: round(a.get(k, 0) - b.get(k, 0), 6) for k in a}

async def run_analysis(client: httpx.AsyncClient, handle: str, brief: dict | None) -> dict:
    """
    POST /analyses and poll until done or failed, keeping the progress messages.
    """
    body = {"handle": handle, "max_posts": 200, **({"context": brief} if brief else {})}
    started = time.perf_counter()
    resp = await client.post("/analyses", json=body)
    if resp.status_code != 202:
        return {"ok": False, "status": resp.status_code, "body": resp.text, "seconds": time.perf_counter() - started}
    job = resp.json()
    messages: list[str] = []
    while job["status"] not in ("done", "failed"):
        await asyncio.sleep(0.4)
        job = (await client.get(f"/analyses/{job['id']}")).json()
        if not messages or messages[-1] != job["message"]:
            messages.append(job["message"])
    return {"ok": job["status"] == "done", "job": job, "messages": messages,
            "seconds": round(time.perf_counter() - started, 2)}

def report_checks(report: dict, brief: dict | None) -> dict:
    """
    Shape and brief checks on a report.
    """
    insights = report.get("insights", [])
    recs = report.get("recommendations", [])
    posts = report.get("posts", [])
    scored = [p for p in posts if p.get("score") is not None]
    labeled = [p for p in scored if (p.get("features") or {}).get("tone")]
    parts = [report.get("summary", "")]
    parts += [i.get("title", "") + " " + i.get("description", "") for i in insights]
    parts += [r.get("action", "") + " " + r.get("rationale", "") for r in recs]
    text = " ".join(parts)
    avoid_hits = [t for t in (brief or {}).get("avoid_topics", []) if norm(t) in norm(text)]
    return {"engine": report.get("engine"), "posts": len(posts), "scored": len(scored),
            "labeled_share": round(len(labeled) / len(scored), 3) if scored else None,
            "insights": len(insights), "recommendations": len(recs),
            "context_echoed": report.get("context") == brief if brief else report.get("context") is None,
            "avoid_topic_mentions": avoid_hits, "summary": report.get("summary")}

def draft_checks(drafts: list[dict], brief: dict | None) -> dict:
    """
    Count, avoided topics, offering and CTA checks on drafts.
    """
    texts = [d["text"] for d in drafts]
    out: dict = {"count": len(drafts), "lengths": [len(t) for t in texts],
                 "scores": [d.get("estimated_score") for d in drafts],
                 "with_rationale": sum(1 for d in drafts if d.get("rationale")),
                 "with_insight_ids": sum(1 for d in drafts if d.get("based_on_insight_ids"))}
    if brief:
        out["avoid_topic_mentions"] = [t for t in brief.get("avoid_topics", []) for x in texts if norm(t) in norm(x)]
        offering = brief.get("offering") or ""
        keys = [w for w in norm(offering).replace("'", " ").split() if len(w) > 5][:4]
        out["offering_keywords"] = keys
        out["drafts_naming_offering"] = sum(1 for x in texts if any(k in norm(x) for k in keys)) if keys else None
        out["drafts_with_link_mention"] = sum(1 for x in texts if "link" in norm(x) or "enlace" in norm(x))
    return out

async def run_case(client: httpx.AsyncClient, handle: str, brief: dict | None, size: int) -> dict:
    """
    One account, one brief mode: analysis, report, drafts, simulation.
    """
    case: dict = {"handle": handle, "brief": brief is not None, "failures": []}
    u0 = await usage(client)
    analysis = await run_analysis(client, handle, brief)
    u1 = await usage(client)
    case["analysis"] = {"ok": analysis["ok"], "seconds": analysis["seconds"], "messages": analysis.get("messages"),
                        "cost": delta(u0, u1, "analyzer")}
    if not analysis["ok"]:
        case["failures"].append({"step": "analysis", "detail": analysis.get("job", analysis)})
        return case
    report_id = analysis["job"]["report_id"]
    t = time.perf_counter()
    r1 = await client.get(f"/reports/{report_id}")
    r2 = await client.get(f"/accounts/{handle}/report")
    case["report"] = {"status": [r1.status_code, r2.status_code], "seconds": round(time.perf_counter() - t, 3),
                      "latest_is_this": r2.status_code == 200 and r2.json()["id"] == report_id}
    if r1.status_code != 200:
        case["failures"].append({"step": "report", "detail": r1.text})
        return case
    report = r1.json()
    case["report"].update(report_checks(report, brief))
    save(f"{handle}_{'brief' if brief else 'nobrief'}.report.json", report)
    t = time.perf_counter()
    d = await client.post("/drafts", json={"handle": handle, "count": 3})
    u2 = await usage(client)
    case["drafts"] = {"status": d.status_code, "seconds": round(time.perf_counter() - t, 2),
                      "cost": delta(u1, u2, "generator")}
    if d.status_code != 200:
        case["failures"].append({"step": "drafts", "detail": d.text})
        return case
    drafts = d.json()["drafts"]
    case["drafts"].update(draft_checks(drafts, brief))
    case["drafts"]["texts"] = [x["text"] for x in drafts]
    variants = [x["text"] for x in drafts][:3]
    sim_body = {"handle": handle, "variants": variants, "audience_size": size, **({"context": brief} if brief else {})}
    t = time.perf_counter()
    s = await client.post("/simulations", json=sim_body)
    u3 = await usage(client)
    case["simulation"] = {"status": s.status_code, "seconds": round(time.perf_counter() - t, 2),
                          "cost": delta(u2, u3, "simulator")}
    if s.status_code != 200:
        case["failures"].append({"step": "simulation", "detail": s.text})
        return case
    sim = s.json()
    save(f"{handle}_{'brief' if brief else 'nobrief'}.sim.json", sim)
    expected = len(sim["personas"]) * len(variants)
    filters = (brief or {}).get("audience_filters") or {}
    ages = set(filters.get("age_groups") or [])
    case["simulation"].update({
        "personas": len(sim["personas"]), "reactions": len(sim["reactions"]), "expected": expected,
        "rates": [round(v["interaction_rate"], 3) for v in sim["variants"]], "best": sim["best_variant_index"],
        "brief_filters_respected": all(p["age_group"] in ages for p in sim["personas"]) if ages else None,
        "summary": sim["summary"],
    })
    return case

async def error_paths(client: httpx.AsyncClient) -> dict:
    """
    A few contract error paths through the real stack.
    """
    out = {}
    r = await client.post("/simulations", json={"variants": ["a", "b"], "audience_size": 492})
    out["simulation_size_492"] = [r.status_code, r.json().get("error", {}).get("code")]
    r = await client.post("/analyses", json={"handle": "no_existe_esta_cuenta_xyz"})
    out["unknown_handle"] = [r.status_code, r.json().get("error", {}).get("code")]
    r = await client.post("/drafts", json={"handle": "no_existe_esta_cuenta_xyz"})
    out["drafts_without_report"] = [r.status_code, r.json().get("error", {}).get("code")]
    return out

async def main(base: str, size: int) -> None:
    """
    Run every account with and without its brief, sequentially (clean latency and cost per step).
    """
    OUT.mkdir(exist_ok=True)
    results = []
    async with httpx.AsyncClient(base_url=base, timeout=300) as client:
        for handle in ACCOUNTS:
            brief = json.loads((BRIEFS / f"{handle}.json").read_text())
            for b in (None, brief):
                case = await run_case(client, handle, b, size)
                results.append(case)
                a, d, s = case.get("analysis", {}), case.get("drafts", {}), case.get("simulation", {})
                print(f"{handle:15} brief={b is not None!s:5} analysis {a.get('seconds')}s "
                      f"${a.get('cost', {}).get('cost')} | drafts {d.get('seconds')}s ${d.get('cost', {}).get('cost')} "
                      f"| sim {s.get('seconds')}s ${s.get('cost', {}).get('cost')} rates={s.get('rates')} "
                      f"| failures={len(case['failures'])}", flush=True)
        errors = await error_paths(client)
        print("error paths:", errors)
    save("e2e_results.json", {"cases": results, "error_paths": errors})

if __name__ == "__main__":
    args = sys.argv[1:]
    asyncio.run(main(args[0] if args else "http://127.0.0.1:8765", int(args[1]) if len(args) > 1 else 100))
