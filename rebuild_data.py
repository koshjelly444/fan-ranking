#!/usr/bin/env python3
"""Rebuild fan_data_slim.js with cleaned city names, names, and masked emails."""
import csv, json, re, math
from collections import Counter, defaultdict
from datetime import datetime, date

CSV_FILE = "2026-03-02-kennedyryon-leads-5.csv"
OUTPUT_FILE = "fan_data_slim.js"
TODAY = date(2026, 3, 2)
TOP_N = 500

# ── City normalization ──────────────────────────────────────────────
# Map common aliases to canonical form
CITY_ALIASES = {
    "atl": "Atlanta", "dc": "Washington, DC", "nyc": "New York",
    "la": "Los Angeles", "h-town": "Houston", "ny": "New York",
    "kc": "Kansas City",
}

US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN",
    "IA","KS","KY","LA","MA","MD","ME","MI","MN","MS","MO","MT","NE","NV",
    "NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN",
    "TX","UT","VT","VA","WA","WV","WI","WY",
}

STATE_FULL_TO_ABBREV = {
    "alabama":"AL","alaska":"AK","arizona":"AZ","arkansas":"AR","california":"CA",
    "colorado":"CO","connecticut":"CT","delaware":"DE","florida":"FL","georgia":"GA",
    "hawaii":"HI","idaho":"ID","illinois":"IL","indiana":"IN","iowa":"IA","kansas":"KS",
    "kentucky":"KY","louisiana":"LA","maine":"ME","maryland":"MD","massachusetts":"MA",
    "michigan":"MI","minnesota":"MN","mississippi":"MS","missouri":"MO","montana":"MT",
    "nebraska":"NE","nevada":"NV","new hampshire":"NH","new jersey":"NJ","new mexico":"NM",
    "new york":"NY","north carolina":"NC","north dakota":"ND","ohio":"OH","oklahoma":"OK",
    "oregon":"OR","pennsylvania":"PA","rhode island":"RI","south carolina":"SC",
    "south dakota":"SD","tennessee":"TN","texas":"TX","utah":"UT","vermont":"VT",
    "virginia":"VA","washington":"WA","west virginia":"WV","wisconsin":"WI","wyoming":"WY",
    "d.c.":"DC","district of columbia":"DC",
}

def normalize_city(raw_city, raw_state):
    """Return (city, state) cleaned and normalized."""
    city = raw_city.strip().strip(",").strip()
    state = raw_state.strip().strip(",").strip()

    if not city:
        return ("", state.upper() if state else "")

    # Check alias first
    alias_key = city.lower().replace(",", "").strip()
    if alias_key in CITY_ALIASES:
        canonical = CITY_ALIASES[alias_key]
        if "," in canonical:
            parts = canonical.split(",")
            return (parts[0].strip(), parts[1].strip())
        return (canonical, state.upper() if state else "")

    # Split city field that contains state info like "Atlanta, GA" or "Atlanta, Georgia"
    parts = [p.strip() for p in city.split(",") if p.strip()]

    # Title-case the city name
    city_name = parts[0].strip()
    # Proper title case, preserving D.C.
    city_name = " ".join(w.capitalize() if w.lower() not in ("of","the","and","de","es","am") else w.lower()
                         for w in city_name.split())
    city_name = city_name.replace("D.c.", "D.C.").replace("D.C", "D.C.")

    # Try to extract state from city field parts
    inferred_state = ""
    for part in parts[1:]:
        p = part.strip().rstrip(".")
        if p.upper() in US_STATES:
            inferred_state = p.upper()
            break
        if p.lower() in STATE_FULL_TO_ABBREV:
            inferred_state = STATE_FULL_TO_ABBREV[p.lower()]
            break

    # Use CSV state column as fallback
    if not inferred_state and state:
        s = state.strip().rstrip(".")
        if s.upper() in US_STATES:
            inferred_state = s.upper()
        elif s.lower() in STATE_FULL_TO_ABBREV:
            inferred_state = STATE_FULL_TO_ABBREV[s.lower()]
        else:
            inferred_state = s.upper()[:2] if len(s) <= 3 else ""

    return (city_name, inferred_state)


# ── Name cleaning ───────────────────────────────────────────────────
def clean_name(first, last):
    """Clean and combine first/last names, removing duplicates."""
    first = first.strip()
    last = last.strip()

    if not first and not last:
        return "Anonymous"
    if not first:
        return last
    if not last:
        return first

    # If first == last (case insensitive), just use one
    if first.lower() == last.lower():
        return first

    # Combine first and last
    combined = f"{first} {last}"

    # Remove consecutive duplicate words: "Mya Hall Hall Hall" → "Mya Hall"
    words = combined.split()
    deduped = [words[0]]
    for w in words[1:]:
        if w.lower() != deduped[-1].lower():
            deduped.append(w)
    combined = " ".join(deduped)

    # Remove trailing word if it matches the one before (catches "Joshua T. Short Short")
    parts = combined.split()
    while len(parts) >= 2 and parts[-1].lower() == parts[-2].lower():
        parts = parts[:-1]
    combined = " ".join(parts)

    # If the last name still appears duplicated at the end, strip it
    # e.g. "Alice Ogadinma Ogadinma" (first) + "Ogadinma" (last) → after dedup still fine
    # but "Joshua T. Short Short" (first) + "Short" (last) → "Joshua T. Short Short Short" before dedup
    return combined


# ── Email masking ───────────────────────────────────────────────────
def mask_email(email):
    """Mask email: 'john.doe@gmail.com' → 'joh***@gmail.com'"""
    if not email or "@" not in email:
        return ""
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked = local[0] + "***"
    else:
        masked = local[:3] + "***"
    return f"{masked}@{domain}"


# ── Gender inference (simple heuristic for avatar colors) ───────────
FEMALE_NAMES = {
    "mary","patricia","jennifer","linda","barbara","elizabeth","susan","jessica",
    "sarah","karen","lisa","nancy","betty","margaret","sandra","ashley","dorothy",
    "kimberly","emily","donna","michelle","carol","amanda","melissa","deborah",
    "stephanie","rebecca","sharon","laura","cynthia","kathleen","amy","angela",
    "shirley","anna","brenda","pamela","emma","nicole","helen","samantha","katherine",
    "christine","debra","rachel","carolyn","janet","catherine","maria","heather",
    "diane","ruth","julie","olivia","joyce","virginia","victoria","kelly","lauren",
    "christina","joan","evelyn","judith","megan","andrea","cheryl","hannah","jacqueline",
    "martha","gloria","teresa","ann","sara","madison","frances","kathryn","janice",
    "jean","abigail","alice","judy","sophia","grace","denise","amber","doris","marilyn",
    "danielle","beverly","isabella","theresa","diana","natalie","brittany","charlotte",
    "marie","kayla","alexis","lori","tiffany","tina","tammy","crystal","madison",
    "nia","tee","shay","breonna","aaliyah","imani","keisha","latoya","shaniqua",
    "ebony","jasmine","diamond","destiny","precious","monique","tasha","lakisha",
    "tamika","aliyah","zoe","luna","mia","aisha","fatima","amara","nia","zara",
    "naomi","maya","asia","india","china","paris","london","savannah","kenya",
    "tara","meghan","carla","brianna","briana","kiara","tiara","ciara","sierra",
    "ariana","adriana","juliana","tatiana","liliana","mariana","alana","diana",
    "regina","deja","jada","kyla","layla","nyla","skyla","kayla","makayla",
}
MALE_NAMES = {
    "james","robert","john","michael","david","william","richard","joseph","thomas",
    "charles","christopher","daniel","matthew","anthony","mark","donald","steven",
    "paul","andrew","joshua","kenneth","kevin","brian","george","timothy","ronald",
    "edward","jason","jeffrey","ryan","jacob","gary","nicholas","eric","jonathan",
    "stephen","larry","justin","scott","brandon","benjamin","samuel","raymond",
    "gregory","frank","alexander","patrick","jack","dennis","jerry","tyler","aaron",
    "jose","nathan","henry","peter","douglas","zachary","kyle","noah","ethan",
    "jeremy","walter","christian","keith","roger","terry","austin","sean","gerald",
    "carl","harold","dylan","arthur","lawrence","jordan","jesse","bryan","billy",
    "bruce","gabriel","joe","logan","albert","willie","alan","eugene","russell",
    "louis","philip","randy","johnny","harry","vincent","bobby","dylan","ralph",
    "roy","eugene","randy","wayne","elijah","tim","edwin","marcus","terrence",
    "darius","jamal","malik","tyrone","deandre","jermaine","lamar","darnell",
    "maurice","reginald","terrell","andre","darryl","cedric","omar","jerome",
    "corey","marquis","devon","khalil","isaiah","xavier","dominique","quinton",
}

def infer_gender(first_name):
    """Return 'f', 'm', or 'n' (neutral)."""
    name = first_name.strip().lower().split()[0] if first_name else ""
    if name in FEMALE_NAMES:
        return "f"
    if name in MALE_NAMES:
        return "m"
    # Heuristic: names ending in 'a', 'ia', 'lyn', 'elle' tend female
    if name.endswith(("ia","lyn","elle","ette","ina","issa","isha")):
        return "f"
    return "n"


# ── Scoring (matching existing algorithm) ───────────────────────────
def parse_purchases(purchase_str):
    """Parse the Purchases column into list of item strings."""
    if not purchase_str:
        return []
    return [p.strip() for p in purchase_str.split(",") if p.strip()]

def categorize_purchase(item):
    """Categorize a purchase item."""
    item_lower = item.lower()
    if "support tier" in item_lower or "twin" in item_lower or "kinfolk" in item_lower or "bestie" in item_lower:
        return "support_tier"
    if "merch" in item_lower or "vinyl" in item_lower or "hoodie" in item_lower or "shirt" in item_lower or "hat" in item_lower or "tote" in item_lower or "poster" in item_lower or "signed" in item_lower:
        return "merch"
    if "livestream" in item_lower or "listening party" in item_lower:
        return "livestream"
    if "album" in item_lower or "deluxe" in item_lower or "sunny days" in item_lower:
        return "album"
    if "track" in item_lower or "snippet" in item_lower or "unreleased" in item_lower or "single" in item_lower:
        return "track"
    if "ticket" in item_lower or "concert" in item_lower or "show" in item_lower or "tour" in item_lower or "experience" in item_lower or "meet" in item_lower or "vip" in item_lower:
        return "ticket"
    if "bundle" in item_lower:
        return "bundle"
    return "ticket"  # default

def has_support_tier(purchases):
    return any("support tier" in p.lower() or "twin" in p.lower() or "kinfolk" in p.lower() or "bestie" in p.lower() for p in purchases)

def has_livestream(purchases):
    return any("livestream" in p.lower() or "listening party" in p.lower() for p in purchases)

def is_twin(purchases):
    return any("twin" in p.lower() for p in purchases)

def compute_score(amount, n_purchases, categories, tenure_days, touchpoints, tier_sub, has_live):
    """Compute fan score out of ~100."""
    # Spending: 0-35 (log scale, saturates around $500+)
    spending_score = min(35, (math.log10(amount + 1) / math.log10(500)) * 35) if amount > 0 else 0
    # Frequency: 0-20
    freq_score = min(20, (n_purchases / 15) * 20) if n_purchases > 0 else 0
    # Variety: 0-15
    variety_score = min(15, (len(categories) / 6) * 15)
    # Tenure: 0-10
    tenure_score = min(10, (tenure_days / 1200) * 10) if tenure_days > 0 else 0
    # Touchpoints: 0-10
    tp_score = min(10, (touchpoints / 3) * 10)
    # Tier bonus: 0-8
    tier_bonus = 6 if tier_sub else 0
    if tier_sub and is_twin.__code__.co_varnames:  # always add 2 for twin from support_tier
        tier_bonus = 6  # base tier bonus
    # Livestream: 0-2
    live_bonus = 2 if has_live else 0

    total = spending_score + freq_score + variety_score + tenure_score + tp_score + tier_bonus + live_bonus
    return {
        "total": round(total, 2),
        "spending": round(spending_score, 2),
        "frequency": round(freq_score, 2),
        "variety": round(variety_score, 2),
        "tenure": round(tenure_score, 2),
        "touchpoints": round(tp_score, 2),
        "tierBonus": round(tier_bonus, 2),
        "livestreamBonus": round(live_bonus, 2),
    }


# ── Main processing ─────────────────────────────────────────────────
def main():
    fans = []
    total_revenue = 0
    category_counts = Counter()
    monthly_joins = Counter()
    city_counts = Counter()

    with open(CSV_FILE, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            first = row.get("First Name", "").strip()
            last = row.get("Last Name", "").strip()
            name = clean_name(first, last)
            email = row.get("Email", "").strip()
            phone = row.get("Phone", "").strip()
            raw_city = row.get("City", "").strip()
            raw_state = row.get("State", "").strip()
            city, state = normalize_city(raw_city, raw_state)
            joined = row.get("Joined At", "").strip()
            ig = row.get("Instagram Username", "").strip()
            n_purchases = int(row.get("# Purchases", "0") or "0")
            amount = float(row.get("Amount Spent", "0") or "0")
            purchase_str = row.get("Purchases", "").strip()

            purchases = parse_purchases(purchase_str)
            cats = list(set(categorize_purchase(p) for p in purchases)) if purchases else []
            for c in cats:
                category_counts[c] += 1

            has_email = bool(email)
            has_ig = bool(ig)
            has_phone = bool(phone)
            touchpoints = sum([has_email, has_ig, has_phone])

            tier_sub = has_support_tier(purchases)
            has_live = has_livestream(purchases)
            tw = is_twin(purchases)

            # Tenure
            tenure_days = 0
            join_date = None
            if joined:
                try:
                    join_date = datetime.strptime(joined[:10], "%Y-%m-%d").date()
                    tenure_days = (TODAY - join_date).days
                except:
                    pass

            if join_date:
                monthly_joins[join_date.strftime("%Y-%m")] += 1

            total_revenue += amount

            scores = compute_score(amount, n_purchases, cats, tenure_days, touchpoints, tier_sub, has_live)

            # City counting
            if city:
                city_label = f"{city}, {state}" if state else city
                city_counts[city_label] += 1

            gender = infer_gender(first)

            fans.append({
                "name": name,
                "email": mask_email(email),
                "ig": ig,
                "purchases": n_purchases,
                "amount": amount,
                "score": scores["total"],
                "breakdown": scores,
                "tenure_days": tenure_days,
                "touchpoints": touchpoints,
                "categories": cats,
                "twin": tw,
                "livestream": has_live,
                "joined": joined[:10] if joined else "",
                "city": city,
                "state": state,
                "has_email": has_email,
                "has_ig": has_ig,
                "has_phone": has_phone,
                "purchase_items": purchases[:20],  # cap at 20
                "gender": gender,
                "tier_sub": tier_sub,
            })

    # Sort by score desc
    fans.sort(key=lambda f: -f["score"])

    # Assign tiers
    total_fans = len(fans)
    total_buyers = sum(1 for f in fans if f["purchases"] > 0)
    buyer_scores = sorted([f["score"] for f in fans if f["purchases"] > 0], reverse=True)

    top5_idx = max(1, int(total_buyers * 0.05))
    top20_idx = max(1, int(total_buyers * 0.20))
    superfan_threshold = buyer_scores[top5_idx - 1] if top5_idx <= len(buyer_scores) else 0
    core_threshold = buyer_scores[top20_idx - 1] if top20_idx <= len(buyer_scores) else 0

    tier_counts = Counter()
    for f in fans:
        if f["purchases"] > 0 and f["score"] >= superfan_threshold:
            tier = "Superfan"
        elif f["purchases"] > 0 and f["score"] >= core_threshold:
            tier = "Core Supporter"
        elif f["purchases"] > 0:
            tier = "Engaged"
        elif f["touchpoints"] >= 2 or f["tenure_days"] >= 365:
            tier = "Active Follower"
        else:
            tier = "Passive"
        f["tier"] = tier
        tier_counts[tier] += 1

    # Assign ranks
    for i, f in enumerate(fans):
        f["rank"] = i + 1

    top_score = fans[0]["score"] if fans else 0

    # Build slim output (top N only)
    slim_fans = []
    for f in fans[:TOP_N]:
        slim_fans.append({
            "r": f["rank"],
            "n": f["name"],
            "ig": f["ig"] or "",
            "em": f["email"],
            "p": f["purchases"],
            "s": round(f["amount"], 2),
            "sc": round(f["score"], 2),
            "t": f["tier"],
            "td": f["tenure_days"],
            "tp": f["touchpoints"],
            "cats": f["categories"],
            "tw": f["twin"],
            "ls": f["livestream"],
            "j": f["joined"],
            "ci": f["city"],
            "st": f["state"],
            "sb": {
                "spending": f["breakdown"]["spending"],
                "frequency": f["breakdown"]["frequency"],
                "variety": f["breakdown"]["variety"],
                "tenure": f["breakdown"]["tenure"],
                "touchpoints": f["breakdown"]["touchpoints"],
                "tierBonus": f["breakdown"]["tierBonus"],
                "livestreamBonus": f["breakdown"]["livestreamBonus"],
            },
            "pi": f["purchase_items"],
            "he": f["has_email"],
            "hi": f["has_ig"],
            "hp": f["has_phone"],
            "g": f["gender"],
        })

    # Top cities (merged, top 30)
    top_cities = dict(city_counts.most_common(30))

    summary = {
        "totalFans": total_fans,
        "totalBuyers": total_buyers,
        "totalRevenue": round(total_revenue, 2),
        "tierCounts": dict(tier_counts),
        "avgScore": round(sum(f["score"] for f in fans) / total_fans, 1) if total_fans else 0,
        "topScore": round(top_score, 2),
        "scoreThresholds": {
            "superfan": round(superfan_threshold, 1),
            "core": round(core_threshold, 1),
        },
        "categoryBreakdown": dict(category_counts),
        "topCities": top_cities,
        "monthlyJoins": dict(monthly_joins),
    }

    output = {"s": summary, "f": slim_fans}
    js_content = "const DATA = " + json.dumps(output, separators=(",", ":")) + ";"

    with open(OUTPUT_FILE, "w") as f:
        f.write(js_content)

    print(f"Generated {OUTPUT_FILE}")
    print(f"  Total fans: {total_fans}")
    print(f"  Buyers: {total_buyers}")
    print(f"  Revenue: ${total_revenue:,.2f}")
    print(f"  Top score: {top_score:.2f}")
    print(f"  Tiers: {dict(tier_counts)}")
    print(f"  Top cities (top 5): {dict(city_counts.most_common(5))}")
    print(f"  Slim fans output: {len(slim_fans)}")

    # Verify name cleaning
    duped = [f["name"] for f in fans[:TOP_N] if " " in f["name"] and f["name"].split()[-1] == f["name"].split()[-2] if len(f["name"].split()) >= 2]
    if duped:
        print(f"  WARNING: {len(duped)} names still have duplicates: {duped[:5]}")
    else:
        print(f"  Name cleaning: OK (no duplicate parts in top {TOP_N})")


if __name__ == "__main__":
    main()
