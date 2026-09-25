"""
Booking review collector.

This is intentionally conservative: it fetches only public pages, identifies
review-like DOM blocks, normalizes fields, de-duplicates records, and writes
JSON. Booking.com can change its HTML or block automated requests, so failures
are logged rather than treated as successful collection.

For a real deployment, confirm Booking.com's current terms/robots rules and
obtain permission where required before automating collection.
"""
from pathlib import Path
import hashlib, json, logging, re, time
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
from config import PROPERTIES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "reviews.json"
LOG = ROOT / "data" / "scraper.log"

logging.basicConfig(
    filename=LOG, level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ReviewInsightsTrial/1.0)",
    "Accept-Language": "en-US,en;q=0.9",
}

def stable_id(property_name, text, review_date):
    raw = f"{property_name}|{review_date}|{text.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]

def classify(text, rating):
    t = text.lower()
    topic_terms = {
        "Cleanliness": ["clean", "dirty", "cleanliness", "hygiene"],
        "Check-in": ["check in", "check-in", "arrival", "reception"],
        "Staff": ["staff", "receptionist", "service", "friendly"],
        "Noise": ["noise", "noisy", "loud", "sound"],
        "Facilities": ["facility", "facilities", "pool", "gym", "lift", "elevator"],
        "Location": ["location", "central", "station", "walk", "transport"],
        "Room condition": ["room", "bed", "bathroom", "shower", "air conditioning"],
        "Value for money": ["value", "price", "expensive", "cheap", "money"],
    }
    topics = [k for k, terms in topic_terms.items() if any(x in t for x in terms)]
    if rating >= 8:
        sentiment = "positive"
    elif rating <= 5:
        sentiment = "negative"
    else:
        sentiment = "mixed"
    return sentiment, topics

def parse_page(html, property_name):
    soup = BeautifulSoup(html, "html.parser")
    candidates = soup.select('[data-testid="review-card"], .review_item, [data-testid="review"]')
    results = []
    for card in candidates:
        text_nodes = card.select('[data-testid="review-positive-text"], [data-testid="review-negative-text"], .review_pos, .review_neg')
        text = " ".join(x.get_text(" ", strip=True) for x in text_nodes).strip()
        if not text:
            text = card.get_text(" ", strip=True)
        rating_node = card.select_one('[data-testid="review-score"], .bui-review-score__badge, .review-score-badge')
        rating_match = re.search(r'(\d+(?:[.,]\d+)?)', rating_node.get_text(" ", strip=True) if rating_node else "")
        rating = float(rating_match.group(1).replace(",", ".")) if rating_match else None
        date_node = card.select_one('time, [data-testid="review-date"], .review_date')
        review_date = None
        if date_node:
            raw = date_node.get("datetime") or date_node.get_text(" ", strip=True)
            try:
                review_date = datetime.fromisoformat(raw.replace("Z", "+00:00")).date().isoformat()
            except Exception:
                pass
        if text and rating is not None:
            sentiment, topics = classify(text, rating)
            results.append({
                "id": stable_id(property_name, text, review_date or ""),
                "property": property_name,
                "date": review_date or datetime.now(timezone.utc).date().isoformat(),
                "rating": rating,
                "text": text,
                "sentiment": sentiment,
                "topics": topics,
                "source": "Booking.com public property page",
            })
    return results

def run():
    existing = []
    if OUT.exists():
        existing = json.loads(OUT.read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in existing}

    for prop in PROPERTIES:
        try:
            logging.info("Fetching %s", prop["name"])
            response = requests.get(prop["url"], headers=HEADERS, timeout=25)
            response.raise_for_status()
            new_rows = parse_page(response.text, prop["name"])
            for row in new_rows:
                by_id[row["id"]] = row
            logging.info("Parsed %s rows for %s", len(new_rows), prop["name"])
        except Exception as exc:
            logging.exception("Failed %s: %s", prop["name"], exc)
        time.sleep(2)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(list(by_id.values()), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(by_id)} reviews to {OUT}")

if __name__ == "__main__":
    run()
