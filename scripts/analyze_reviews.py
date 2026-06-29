"""One-off analysis of scrubbed reviews for Phase 3 planning."""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
reviews = json.loads((ROOT / "data/scrubbed/groww_reviews.json").read_text(encoding="utf-8"))["reviews"]
n = len(reviews)

THEMES = [
    ("onboarding_kyc", ["kyc", "verification", "onboard", "pan", "aadhaar", "document", "signup", "register", "ddpi"]),
    ("payments_withdrawals", ["payment", "upi", "withdraw", "redeem", "credit", "debit", "autopay", "charges", "bank"]),
    ("trading_orders", ["order", "trade", "trading", "execute", "buy", "sell", "demat", "fno", "option", "intraday", "brokerage"]),
    ("mutual_funds_sip", ["mutual", "sip", "fund", "nav", "elss", "portfolio"]),
    ("app_ux_support", ["crash", "bug", "slow", "lag", "freeze", "update", "login", "otp", "ui", "interface", "chart", "support", "customer", "help"]),
]

assigned = defaultdict(list)
other = []
for r in reviews:
    text = r["text"].lower()
    matched = False
    for theme, kws in THEMES:
        if any(k in text for k in kws):
            assigned[theme].append(r)
            matched = True
            break
    if not matched:
        other.append(r)

print(f"Total reviews: {n}")
print(f"Negative (1-2 stars): {sum(1 for r in reviews if r['rating'] <= 2)} ({100*sum(1 for r in reviews if r['rating'] <= 2)/n:.1f}%)")
print(f"Positive (4-5 stars): {sum(1 for r in reviews if r['rating'] >= 4)} ({100*sum(1 for r in reviews if r['rating'] >= 4)/n:.1f}%)")
print()
for theme, _ in THEMES:
    rs = assigned[theme]
    if not rs:
        continue
    avg = sum(x["rating"] for x in rs) / len(rs)
    low = 100 * sum(1 for x in rs if x["rating"] <= 2) / len(rs)
    print(f"{theme}: count={len(rs)} ({100*len(rs)/n:.1f}%) avg_rating={avg:.2f} low_star%={low:.1f}")
print(f"unassigned: {len(other)} ({100*len(other)/n:.1f}%)")
total_chars = sum(len(r["title"]) + len(r["text"]) for r in reviews)
print(f"\nEst tokens if all reviews sent: ~{total_chars // 4}")
