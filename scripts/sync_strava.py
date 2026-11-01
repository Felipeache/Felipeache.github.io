"""Fetch the last 12 months of Strava activities and write aggregated data.

Writes data/training.js as `window.TRAINING_DATA = {...};`, so the dashboard
page can load it with a plain <script> tag (this also works from file://).

Only aggregates and the fields the dashboard needs are kept. Routes, maps,
coordinates, activity names and descriptions are never written.

Required environment variables (GitHub Actions secrets):
  STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN
"""
import datetime as dt
import json
import os
import pathlib
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "training.js"
API = "https://www.strava.com/api/v3"
TOKEN_URL = "https://www.strava.com/oauth/token"

CATEGORY = {
    "Run": "run", "TrailRun": "run", "VirtualRun": "run",
    "Ride": "ride", "VirtualRide": "ride", "EBikeRide": "ride",
    "MountainBikeRide": "ride", "GravelRide": "ride",
    "WeightTraining": "strength", "Workout": "strength", "Crossfit": "strength",
    "Swim": "swim",
}


def category(sport_type):
    return CATEGORY.get(sport_type, "other")


def month_key(day):
    return day.strftime("%Y-%m")


def week_start(day):
    return day - dt.timedelta(days=day.weekday())


def build(activities, now):
    """Turn raw Strava activity summaries into the dashboard's data shape."""
    start = now - dt.timedelta(days=365)
    rows = []
    for a in activities:
        when = dt.datetime.fromisoformat(a["start_date_local"].replace("Z", "+00:00")).date()
        if when < start.date():
            continue
        rows.append({
            "date": when,
            "category": category(a.get("sport_type") or a.get("type", "")),
            "km": (a.get("distance") or 0) / 1000,
            "seconds": a.get("moving_time") or 0,
            "elevation": a.get("total_elevation_gain") or 0,
        })
    rows.sort(key=lambda r: r["date"])

    totals = {
        "km": round(sum(r["km"] for r in rows), 1),
        "hours": round(sum(r["seconds"] for r in rows) / 3600, 1),
        "elevation": round(sum(r["elevation"] for r in rows)),
        "sessions": len(rows),
    }

    empty = {"km": 0.0, "hours": 0.0, "elevation": 0.0, "sessions": 0}
    months = {}
    for r in rows:
        m = months.setdefault(month_key(r["date"]), dict(empty))
        m["km"] += r["km"]
        m["hours"] += r["seconds"] / 3600
        m["elevation"] += r["elevation"]
        m["sessions"] += 1
    month_list = []
    cursor = dt.date(start.year, start.month, 1)
    while cursor <= now.date():
        key = month_key(cursor)
        m = months.get(key, empty)
        month_list.append({"month": key, "km": round(m["km"], 1), "hours": round(m["hours"], 1),
                           "elevation": round(m["elevation"]), "sessions": m["sessions"]})
        cursor = (cursor.replace(day=28) + dt.timedelta(days=4)).replace(day=1)

    this_week = week_start(now.date())
    weeks = {}
    for r in rows:
        w = week_start(r["date"]).isoformat()
        weeks[w] = weeks.get(w, 0) + 1
    week_list = []
    for i in range(52, -1, -1):
        w = (this_week - dt.timedelta(weeks=i)).isoformat()
        week_list.append({"week": w, "sessions": weeks.get(w, 0)})

    mix = {}
    for r in rows:
        mix[r["category"]] = mix.get(r["category"], 0) + 1

    def record(cat):
        pool = [r for r in rows if cat is None or r["category"] == cat]
        if not pool:
            return None
        best = max(pool, key=lambda r: r["km"])
        return {"km": round(best["km"], 2), "date": best["date"].isoformat()}

    records = {"run": record("run"), "ride": record("ride"), "longest": record(None)}

    recent = [{"date": r["date"].isoformat(), "category": r["category"],
               "km": round(r["km"], 2), "seconds": r["seconds"], "elevation": round(r["elevation"])}
              for r in rows[-10:]][::-1]

    return {
        "generated_at": now.replace(microsecond=0).isoformat() + "Z",
        "period_start": start.date().isoformat(),
        "period_end": now.date().isoformat(),
        "totals": totals,
        "months": month_list,
        "weeks": week_list,
        "mix": mix,
        "records": records,
        "recent": recent,
    }


def refresh_access_token():
    body = urllib.parse.urlencode({
        "client_id": os.environ["STRAVA_CLIENT_ID"],
        "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
        "refresh_token": os.environ["STRAVA_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    with urllib.request.urlopen(urllib.request.Request(TOKEN_URL, data=body)) as resp:
        return json.load(resp)["access_token"]


def fetch_activities(token, after_epoch):
    activities, page = [], 1
    while True:
        query = urllib.parse.urlencode({"after": after_epoch, "page": page, "per_page": 200})
        req = urllib.request.Request(f"{API}/athlete/activities?{query}",
                                     headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req) as resp:
            batch = json.load(resp)
        activities.extend(batch)
        if len(batch) < 200:
            return activities
        page += 1


def main():
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    after = int((now - dt.timedelta(days=365)).replace(tzinfo=dt.timezone.utc).timestamp())
    token = refresh_access_token()
    data = build(fetch_activities(token, after), now)
    OUT.write_text("window.TRAINING_DATA = " + json.dumps(data, indent=2) + ";\n", encoding="utf-8")
    print(f"wrote {OUT} with {data['totals']['sessions']} sessions")


if __name__ == "__main__":
    main()
