# Kennedy Ryon — Fan Ranking Dashboard

Interactive fan ranking system that scores 80,000+ fans based on spending, purchase frequency, variety, tenure, touchpoints, and subscription status.

## How to View

Both files must be in the same directory. Because the HTML loads a local JS file, you need to serve it:

```bash
python3 -m http.server 8888
```

Then open http://localhost:8888/kennedy-ryon-fan-ranking.html

## Scoring Algorithm (out of ~100 points)

- **Spending (log scale):** 0–35 pts
- **Purchase Frequency:** 0–20 pts
- **Purchase Variety (categories):** 0–15 pts
- **Tenure:** 0–10 pts
- **Touchpoints (email/IG/phone):** 0–10 pts
- **Support Tier Bonus (Twin, etc):** 0–8 pts
- **Livestream Attendance:** 0–2 pts

## Tiers

- **Superfan (109)** — Top 5% of buyers
- **Core Supporter (325)** — Top 20% of buyers
- **Engaged (1,732)** — All other paying fans
- **Active Follower (58,867)** — Non-buyers with 2+ touchpoints or 1yr+ tenure
- **Passive (19,319)** — Everyone else

## Important

The source CSV contains PII (emails, phone numbers, Instagram accounts) and is excluded via `.gitignore`. Do not commit it.
