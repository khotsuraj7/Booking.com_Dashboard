from datetime import date, timedelta
from pathlib import Path
import json
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "reviews.json"

app = FastAPI(title="Booking Review Insights API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_reviews():
    if not DATA.exists():
        return []
    return json.loads(DATA.read_text(encoding="utf-8"))

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/properties")
def properties():
    reviews = load_reviews()
    return sorted({r["property"] for r in reviews})

@app.get("/api/reviews")
def reviews(
    property: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    sentiment: str | None = None,
):
    rows = load_reviews()
    if property:
        rows = [r for r in rows if r["property"] == property]
    if start_date:
        rows = [r for r in rows if date.fromisoformat(r["date"]) >= start_date]
    if end_date:
        rows = [r for r in rows if date.fromisoformat(r["date"]) <= end_date]
    if sentiment:
        rows = [r for r in rows if r["sentiment"] == sentiment]
    return rows

def avg(rows):
    return round(sum(r["rating"] for r in rows) / len(rows), 2) if rows else 0

@app.get("/api/summary")
def summary():
    rows = load_reviews()
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    prev_start = week_start - timedelta(days=7)
    prev_end = week_start - timedelta(days=1)

    current = [r for r in rows if date.fromisoformat(r["date"]) >= week_start]
    previous = [r for r in rows if prev_start <= date.fromisoformat(r["date"]) <= prev_end]

    property_breakdown = []
    for p in sorted({r["property"] for r in rows}):
        pr = [r for r in rows if r["property"] == p]
        property_breakdown.append({
            "property": p,
            "reviews": len(pr),
            "average_rating": avg(pr),
        })

    return {
        "current_week": {
            "start": week_start.isoformat(),
            "average_rating": avg(current),
            "review_count": len(current),
        },
        "previous_week": {
            "start": prev_start.isoformat(),
            "end": prev_end.isoformat(),
            "average_rating": avg(previous),
            "review_count": len(previous),
        },
        "property_breakdown": property_breakdown,
        "total_reviews": len(rows),
    }

@app.get("/api/trends")
def trends():
    rows = load_reviews()
    dates = sorted({r["date"] for r in rows})
    result = []
    for d in dates:
        day = [r for r in rows if r["date"] == d]
        pos = sum(r["sentiment"] == "positive" for r in day)
        neg = sum(r["sentiment"] == "negative" for r in day)
        result.append({"date": d, "positive": pos, "negative": neg, "average_rating": avg(day)})
    return result

@app.get("/api/insights")
def insights():
    rows = load_reviews()
    negative = [r for r in rows if r["sentiment"] == "negative"]
    topics = {}
    for r in negative:
        for topic in r.get("topics", []):
            topics[topic] = topics.get(topic, 0) + 1
    total = len(negative)
    return [
        {"topic": k, "count": v, "percentage": round(v / total * 100, 1) if total else 0}
        for k, v in sorted(topics.items(), key=lambda x: (-x[1], x[0]))
    ]

@app.get("/api/metadata")
def metadata():
    return {
        "source": "Sample review dataset included with the trial project",
        "properties": [
            "Olympic Hotel Paddington",
            "Potts Point",
            "Central Sydney",
            "Darling Harbour",
        ],
        "topic_method": "Transparent keyword-based classification",
        "sentiment_method": "Rating + keyword heuristic",
    }
