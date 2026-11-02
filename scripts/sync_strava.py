"""Fetch Strava activities and write aggregated training data.

Writes two files:
  data/training.js        window.TRAINING_DATA = {...}; read by training.html
                          (a plain <script> tag, so it also works from file://)
  data/strava_state.json  progress for the personal-best search: hashed activity
                          IDs already checked, and the best time per distance

Only aggregates are kept. Routes, maps, coordinates and activity names are never
written. Activity IDs are stored only as SHA-256 hashes.

Each run checks at most MAX_DETAIL runs for best efforts, to stay within Strava's
request limits, and continues from the saved state on the next run.

Required environment variables (GitHub Actions secrets):
  STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN
"""
import datetime as dt
import hashlib
import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "training.js"
STATE = ROOT / "data" / "strava_state.json"
API = "https://www.strava.com/api/v3"
TOKEN_URL = "https://www.strava.com/oauth/token"

MAX_DETAIL = 80  # detail requests per run; Strava allows 100 per 15 minutes

CATEGORY = {
    "Run": "run", "TrailRun": "run", "VirtualRun": "run",
    "Ride": "ride", "VirtualRide": "ride", "EBikeRide": "ride",
    "MountainBikeRide": "ride", "GravelRide": "ride",
    "WeightTraining": "strength", "Workout": "strength", "Crossfit": "strength",
    "Swim": "swim",
}
RUN_TYPES = {"Run", "TrailRun", "VirtualRun"}


def category(sport_type):
    return CATEGORY.get(sport_type, "other")


def month_key(day):
    return day.strftime("%Y-%m")


def week_start(day):
    return day - dt.timedelta(days=day.weekday())


def activity_date(a):
    return dt.datetime.fromisoformat(a["start_date_local"].replace("Z", "+00:00")).date()


def build(activities, now):
    """Turn raw Strava activity summaries into the dashboard's 12-month data."""
    start = now - dt.timedelta(days=365)
    rows = []
    for a in activities:
        when = activity_date(a)
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
        return {"km": round(best["km"], 2), "seconds": best["seconds"], "date": best["date"].isoformat()}

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


# ---- Personal bests -------------------------------------------------------

def hash_id(activity_id):
    return hashlib.sha256(str(activity_id).encode()).hexdigest()


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"done": [], "pbs": {}}


def save_state(state):
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def update_pbs(state, detail):
    """Keep the fastest time for each best-effort distance, with its date."""
    for effort in detail.get("best_efforts") or []:
        name = effort.get("name")
        seconds = effort.get("elapsed_time")
        if not name or not seconds:
            continue
        current = state["pbs"].get(name)
        if current is None or seconds < current["seconds"]:
            state["pbs"][name] = {
                "distance": effort.get("distance") or 0,
                "seconds": seconds,
                "date": (effort.get("start_date_local") or "")[:10],
            }


def check_best_efforts(token, runs, state):
    """Request the detail of up to MAX_DETAIL unchecked runs. Returns how many were checked."""
    done = set(state["done"])
    checked = 0
    for a in runs:
        key = hash_id(a["id"])
        if key in done:
            continue
        if checked >= MAX_DETAIL:
            break
        req = urllib.request.Request(f"{API}/activities/{a['id']}",
                                     headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req) as resp:
                detail = json.load(resp)
        except urllib.error.HTTPError as err:
            if err.code == 429:
                print("Strava rate limit reached; the rest will be checked on the next run.")
                break
            raise SystemExit(f"Activity detail failed: HTTP {err.code} {err.reason}")
        update_pbs(state, detail)
        state["done"].append(key)
        done.add(key)
        checked += 1
    return checked


PB_DISTANCES = ["5k", "10k", "Half-Marathon", "Marathon"]  # 5 km, 10 km, 21 km, 42 km


def build_pbs(state, runs):
    """Personal bests for the four race distances (None until a run has one), plus progress."""
    total_runs = len(runs)
    checked = sum(1 for a in runs if hash_id(a["id"]) in set(state["done"]))
    best = []
    for name in PB_DISTANCES:
        v = state["pbs"].get(name)
        best.append({"name": name, "seconds": v["seconds"], "date": v["date"]} if v else None)
    return {
        "best": best,
        "runs_checked": checked,
        "runs_total": total_runs,
        "complete": checked >= total_runs,
    }


# ---- Strava access ---------------------------------------------------------

def read_secret(name):
    return os.environ[name].strip()


def open_or_explain(req, what):
    """Open a request; on HTTP errors print Strava's response, which has no secrets in it."""
    try:
        return urllib.request.urlopen(req)
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="replace")
        raise SystemExit(f"{what} failed: HTTP {err.code} {err.reason}\nStrava says: {detail}")


def refresh_access_token():
    used = read_secret("STRAVA_REFRESH_TOKEN")
    body = urllib.parse.urlencode({
        "client_id": read_secret("STRAVA_CLIENT_ID"),
        "client_secret": read_secret("STRAVA_CLIENT_SECRET"),
        "refresh_token": used,
        "grant_type": "refresh_token",
    }).encode()
    with open_or_explain(urllib.request.Request(TOKEN_URL, data=body), "Token refresh") as resp:
        payload = json.load(resp)
    if payload.get("refresh_token") and payload["refresh_token"] != used:
        print("WARNING: Strava issued a new refresh token. Update STRAVA_REFRESH_TOKEN, "
              "or the next run will fail. (The token itself is not printed.)")
    return payload["access_token"]


def fetch_activities(token, after_epoch):
    activities, page = [], 1
    while True:
        query = urllib.parse.urlencode({"after": after_epoch, "page": page, "per_page": 200})
        req = urllib.request.Request(f"{API}/athlete/activities?{query}",
                                     headers={"Authorization": f"Bearer {token}"})
        with open_or_explain(req, "Activity list") as resp:
            batch = json.load(resp)
        activities.extend(batch)
        if len(batch) < 200:
            return activities
        page += 1


def main():
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    token = refresh_access_token()

    # Full history: the 12-month view filters by date, and personal bests need every run.
    activities = fetch_activities(token, 0)
    data = build(activities, now)

    runs = [a for a in activities if a.get("sport_type") in RUN_TYPES]
    runs.sort(key=activity_date, reverse=True)  # newest first
    state = load_state()
    checked = check_best_efforts(token, runs, state)
    save_state(state)
    data["pbs"] = build_pbs(state, runs)

    OUT.write_text("window.TRAINING_DATA = " + json.dumps(data, indent=2) + ";\n", encoding="utf-8")
    print(f"wrote {OUT}: {data['totals']['sessions']} sessions in 12 months; "
          f"checked {checked} runs for personal bests "
          f"({data['pbs']['runs_checked']} of {data['pbs']['runs_total']} done)")


if __name__ == "__main__":
    main()
