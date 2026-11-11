"""Fetch Paris metro disruptions from Île-de-France Mobilités PRIM and write dashboard data.

Writes two files:
  data/metro.js         window.METRO_DATA = {...}; read by metro.html
  data/metro_state.json per-day disruption flags + first-seen disruption IDs

History starts at go-live: monthly/yearly counts and clear-day streaks are derived
from observations collected by this script (PRIM has no multi-year archive).

Required environment variable:
  PRIM_API_KEY  — API token from https://prim.iledefrance-mobilites.fr

Scheduled syncs only call PRIM between 07:00 and 21:00 Europe/Paris.
Manual runs (workflow_dispatch / push) and METRO_FORCE_SYNC=1 always call the API.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9
    ZoneInfo = None  # type: ignore

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "metro.js"
STATE = ROOT / "data" / "metro_state.json"
PARIS = ZoneInfo("Europe/Paris") if ZoneInfo else dt.timezone(dt.timedelta(hours=1))

# Inclusive start, exclusive end → last scheduled slot is 20:50 Paris.
SYNC_HOUR_START = 7
SYNC_HOUR_END = 21

API_BASE = (
    "https://prim.iledefrance-mobilites.fr/marketplace/v2/navitia/"
    "line_reports/physical_modes/physical_mode%3AMetro/line_reports"
)

# Official RATP metro line colours and termini (short display names).
LINES = [
    {"code": "1", "idfm": "C01371", "name": "La Défense ↔ Château de Vincennes", "color": "#FFCD00"},
    {"code": "2", "idfm": "C01372", "name": "Porte Dauphine ↔ Nation", "color": "#003CA6"},
    {"code": "3", "idfm": "C01373", "name": "Pont de Levallois ↔ Gallieni", "color": "#837902"},
    {"code": "3bis", "idfm": "C01386", "name": "Porte des Lilas ↔ Gambetta", "color": "#6EC4E8"},
    {"code": "4", "idfm": "C01374", "name": "Porte de Clignancourt ↔ Bagneux", "color": "#CF009E"},
    {"code": "5", "idfm": "C01375", "name": "Bobigny ↔ Place d'Italie", "color": "#FF7E2B"},
    {"code": "6", "idfm": "C01376", "name": "Charles de Gaulle–Étoile ↔ Nation", "color": "#6ECA97"},
    {"code": "7", "idfm": "C01377", "name": "La Courneuve ↔ Mairie d'Ivry / Villejuif", "color": "#FA9ABA"},
    {"code": "7bis", "idfm": "C01387", "name": "Louis Blanc ↔ Pré-Saint-Gervais", "color": "#6ECA97"},
    {"code": "8", "idfm": "C01378", "name": "Balard ↔ Créteil / Pointe du Lac", "color": "#E19BDF"},
    {"code": "9", "idfm": "C01379", "name": "Pont de Sèvres ↔ Mairie de Montreuil", "color": "#B6BD00"},
    {"code": "10", "idfm": "C01380", "name": "Boulogne ↔ Gare d'Austerlitz", "color": "#C9910D"},
    {"code": "11", "idfm": "C01381", "name": "Châtelet ↔ Rosny–Bois-Perrier", "color": "#704B1C"},
    {"code": "12", "idfm": "C01382", "name": "Front Populaire ↔ Mairie d'Issy", "color": "#007852"},
    {"code": "13", "idfm": "C01383", "name": "Asnières / Gennevilliers ↔ Châtillon", "color": "#6EC4E8"},
    {"code": "14", "idfm": "C01384", "name": "Saint-Denis–Pleyel ↔ Aéroport d'Orly", "color": "#62259D"},
]

IDFM_TO_CODE = {f"line:IDFM:{row['idfm']}": row["code"] for row in LINES}
CODE_TO_META = {row["code"]: row for row in LINES}

SEVERITY_RANK = {
    "information": 1,
    "perturbed": 2,
    "blocked": 3,
}


def normalize_severity(raw: str | None) -> str:
    s = (raw or "").strip().lower()
    s = (
        s.replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("ù", "u")
    )
    if "bloquan" in s or s in {"blocking", "blocked", "critical"}:
        return "blocked"
    if "perturb" in s or s in {"warning", "reduced_service", "disrupted"}:
        return "perturbed"
    return "information"


def is_service_disruption(severity: str) -> bool:
    return severity in ("perturbed", "blocked")


def paris_today() -> dt.date:
    return dt.datetime.now(PARIS).date()


def paris_now() -> dt.datetime:
    return dt.datetime.now(PARIS)


def within_sync_window(when: dt.datetime | None = None) -> bool:
    """True if local Paris time is in [07:00, 21:00)."""
    local = when or paris_now()
    if local.tzinfo is None:
        local = local.replace(tzinfo=PARIS)
    else:
        local = local.astimezone(PARIS)
    return SYNC_HOUR_START <= local.hour < SYNC_HOUR_END


def should_call_api() -> bool:
    """Scheduled jobs respect the Paris window; manual/forced runs always sync."""
    if os.environ.get("METRO_FORCE_SYNC", "").strip().lower() in {"1", "true", "yes"}:
        return True
    event = (os.environ.get("GITHUB_EVENT_NAME") or "").strip()
    if event in {"workflow_dispatch", "push"}:
        return True
    return within_sync_window()


def load_state() -> dict:
    if not STATE.exists():
        return {"days": {}, "disruptions": {}}
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"days": {}, "disruptions": {}}
    data.setdefault("days", {})
    data.setdefault("disruptions", {})
    return data


def api_get(url: str, api_key: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "apiKey": api_key,
            "Accept": "application/json",
            "User-Agent": "henao.me-metro-sync/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


CODE_ALIASES = {
    "3B": "3bis",
    "3b": "3bis",
    "7B": "7bis",
    "7b": "7bis",
}


def resolve_line_code(line: dict | None) -> str | None:
    if not line or not isinstance(line, dict):
        return None
    line_id = line.get("id") or ""
    if line_id in IDFM_TO_CODE:
        return IDFM_TO_CODE[line_id]
    raw = (line.get("code") or line.get("name") or "").strip()
    if raw in CODE_TO_META:
        return raw
    if raw in CODE_ALIASES:
        return CODE_ALIASES[raw]
    return None


def fetch_metro_payload(api_key: str) -> dict:
    """Paginate PRIM metro line_reports; merge disruptions + line_reports."""
    all_reports: list[dict] = []
    all_disruptions: dict[str, dict] = {}
    page = 0
    while True:
        qs = urllib.parse.urlencode({"count": 100, "start_page": page})
        url = f"{API_BASE}?{qs}"
        payload = api_get(url, api_key)
        for d in payload.get("disruptions") or []:
            if isinstance(d, dict) and d.get("id"):
                all_disruptions[str(d["id"])] = d
        batch = payload.get("line_reports") or []
        if isinstance(batch, list):
            all_reports.extend(batch)
        pagination = payload.get("pagination") or {}
        total = pagination.get("total_result")
        items_on_page = pagination.get("items_on_page", len(batch) if isinstance(batch, list) else 0)
        if not batch or items_on_page < 100:
            break
        if total is not None and (page + 1) * 100 >= int(total):
            break
        page += 1
        if page > 20:
            break
    return {"line_reports": all_reports, "disruptions": all_disruptions}


def disruption_message(d: dict) -> str:
    msgs = d.get("messages") or []
    for m in msgs:
        text = (m.get("text") or "").strip()
        if text:
            return text
    return (d.get("cause") or d.get("category") or "").strip() or "Disruption"


def message_from_disruption(d: dict) -> dict:
    severity = normalize_severity(
        ((d.get("severity") or {}).get("name") if isinstance(d.get("severity"), dict) else None)
        or d.get("severity")
        or ""
    )
    periods = d.get("application_periods") or []
    begin = end = None
    if periods:
        begin = periods[0].get("begin")
        end = periods[0].get("end")
    return {
        "id": str(d.get("id") or ""),
        "severity": severity,
        "cause": (d.get("cause") or "").strip() or None,
        "title": disruption_message(d)[:280],
        "begin": begin,
        "end": end,
    }


def codes_from_impacted(d: dict) -> set[str]:
    codes: set[str] = set()
    for obj in d.get("impacted_objects") or []:
        if not isinstance(obj, dict):
            continue
        line = obj.get("line") if isinstance(obj.get("line"), dict) else None
        if line:
            code = resolve_line_code(line)
            if code:
                codes.add(code)
        elif obj.get("embedded_type") == "line" or (obj.get("id") or "").startswith("line:"):
            code = resolve_line_code(obj if obj.get("id") else {"id": obj.get("id")})
            if not code and obj.get("id"):
                code = resolve_line_code({"id": obj["id"]})
            if code:
                codes.add(code)
    for obj in d.get("pt_objects") or []:
        if not isinstance(obj, dict):
            continue
        line = obj.get("line") if isinstance(obj.get("line"), dict) else obj
        code = resolve_line_code(line)
        if code:
            codes.add(code)
    return codes


def extract_active_by_line(payload: dict) -> dict[str, list[dict]]:
    """Map line code -> list of active message dicts from a PRIM/Navitia payload."""
    by_line: dict[str, list[dict]] = {code: [] for code in CODE_TO_META}
    seen_per_line: dict[str, set[str]] = {code: set() for code in CODE_TO_META}
    disruptions: dict[str, dict] = payload.get("disruptions") or {}

    def attach(code: str | None, disruption: dict) -> None:
        if not code or code not in CODE_TO_META:
            return
        msg = message_from_disruption(disruption)
        if not msg["id"] or msg["id"] in seen_per_line[code]:
            return
        seen_per_line[code].add(msg["id"])
        by_line[code].append(msg)

    # From top-level disruptions → impacted lines
    for d in disruptions.values():
        for code in codes_from_impacted(d):
            attach(code, d)

    # From line_reports → linked disruption IDs
    for report in payload.get("line_reports") or []:
        if not isinstance(report, dict):
            continue
        code = resolve_line_code(report.get("line") or {})
        linked_ids: list[str] = []
        for link in report.get("links") or []:
            if isinstance(link, dict) and (link.get("rel") == "disruptions" or link.get("type") == "disruption"):
                if link.get("id"):
                    linked_ids.append(str(link["id"]))
        for obj in report.get("pt_objects") or []:
            if not isinstance(obj, dict):
                continue
            for link in obj.get("links") or []:
                if isinstance(link, dict) and link.get("id"):
                    linked_ids.append(str(link["id"]))
            if not code:
                code = resolve_line_code(obj.get("line") or obj)
        for did in linked_ids:
            if did in disruptions:
                attach(code, disruptions[did])
        for d in report.get("disruptions") or []:
            if isinstance(d, dict):
                attach(code, d)

    return by_line


def worst_status(messages: list[dict]) -> str:
    if not messages:
        return "normal"
    rank = 0
    status = "information"
    for m in messages:
        sev = m.get("severity") or "information"
        r = SEVERITY_RANK.get(sev, 1)
        if r > rank:
            rank = r
            status = sev
    return status


def update_state(
    state: dict,
    today: dt.date,
    by_line: dict[str, list[dict]],
) -> dict:
    day_key = today.isoformat()
    day_entry = state["days"].setdefault(day_key, {})
    disruptions = state["disruptions"]

    for code, messages in by_line.items():
        disrupted = any(is_service_disruption(m["severity"]) for m in messages)
        prev = day_entry.get(code) or {}
        day_entry[code] = {
            "disrupted": bool(prev.get("disrupted")) or disrupted,
        }
        for m in messages:
            if not is_service_disruption(m["severity"]):
                continue
            did = m["id"]
            if did not in disruptions:
                disruptions[did] = {
                    "line": code,
                    "first_seen": day_key,
                    "severity": m["severity"],
                    "title": m.get("title"),
                }

    # Ensure every catalog line has a flag for today
    for code in CODE_TO_META:
        day_entry.setdefault(code, {"disrupted": False})

    return state


def compute_stats(state: dict, code: str) -> dict:
    by_month: dict[str, int] = {}
    by_year: dict[str, int] = {}
    for meta in state.get("disruptions", {}).values():
        if meta.get("line") != code:
            continue
        first = meta.get("first_seen") or ""
        if len(first) < 7:
            continue
        month = first[:7]
        year = first[:4]
        by_month[month] = by_month.get(month, 0) + 1
        by_year[year] = by_year.get(year, 0) + 1

    days = state.get("days") or {}
    ordered = sorted(days.keys())
    max_clear = 0
    run = 0
    for day in ordered:
        entry = (days[day] or {}).get(code) or {}
        if entry.get("disrupted"):
            run = 0
        else:
            run += 1
            if run > max_clear:
                max_clear = run

    current = 0
    for day in reversed(ordered):
        entry = (days[day] or {}).get(code) or {}
        if entry.get("disrupted"):
            break
        current += 1

    return {
        "by_month": dict(sorted(by_month.items())),
        "by_year": dict(sorted(by_year.items())),
        "max_clear_days": max_clear,
        "current_clear_streak": current,
    }


def build_payload(state: dict, by_line: dict[str, list[dict]], now: dt.datetime) -> dict:
    lines = []
    disrupted_now = 0
    for meta in LINES:
        code = meta["code"]
        messages = by_line.get(code) or []
        status = worst_status(messages)
        if is_service_disruption(status):
            disrupted_now += 1
        lines.append(
            {
                "code": code,
                "name": meta["name"],
                "color": meta["color"],
                "status": status,
                "messages": [
                    {
                        "severity": m["severity"],
                        "cause": m.get("cause"),
                        "title": m.get("title"),
                        "begin": m.get("begin"),
                        "end": m.get("end"),
                    }
                    for m in messages
                ],
                "stats": compute_stats(state, code),
            }
        )
    return {
        "generated_at": now.astimezone(PARIS).isoformat(timespec="seconds"),
        "history_start": min(state["days"].keys()) if state.get("days") else now.date().isoformat(),
        "summary": {
            "lines_total": len(LINES),
            "lines_disrupted": disrupted_now,
            "lines_normal": len(LINES) - disrupted_now,
        },
        "lines": lines,
    }


def write_metro_js(payload: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    body = "window.METRO_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n"
    OUT.write_text(body, encoding="utf-8")


def write_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def bootstrap_payload(now: dt.datetime) -> dict:
    """Empty catalog so the page works before the first successful API sync."""
    state = {"days": {}, "disruptions": {}}
    by_line = {code: [] for code in CODE_TO_META}
    return build_payload(state, by_line, now)


def main() -> int:
    now = dt.datetime.now(dt.timezone.utc)
    today = paris_today()
    api_key = (os.environ.get("PRIM_API_KEY") or "").strip()

    if not api_key:
        if not OUT.exists():
            write_metro_js(bootstrap_payload(now))
            write_state({"days": {}, "disruptions": {}})
            print("No PRIM_API_KEY; wrote bootstrap metro data.")
            return 0
        print("PRIM_API_KEY is not set; leaving existing data unchanged.")
        return 0

    if not should_call_api():
        local = paris_now()
        print(
            f"Outside Paris sync window "
            f"({SYNC_HOUR_START:02d}:00–{SYNC_HOUR_END:02d}:00); "
            f"now {local.isoformat()}. Skipping PRIM call."
        )
        return 0

    try:
        raw = fetch_metro_payload(api_key)
    except urllib.error.HTTPError as e:
        print(f"PRIM HTTP error: {e.code} {e.reason}")
        if not OUT.exists():
            write_metro_js(bootstrap_payload(now))
            write_state({"days": {}, "disruptions": {}})
        return 1
    except urllib.error.URLError as e:
        print(f"PRIM network error: {e.reason}")
        if not OUT.exists():
            write_metro_js(bootstrap_payload(now))
            write_state({"days": {}, "disruptions": {}})
        return 1

    by_line = extract_active_by_line(raw)

    state = load_state()
    update_state(state, today, by_line)
    payload = build_payload(state, by_line, now)
    write_state(state)
    write_metro_js(payload)
    print(
        f"Wrote {OUT.name}: {payload['summary']['lines_disrupted']} disrupted / "
        f"{payload['summary']['lines_total']} lines "
        f"({len(raw.get('line_reports') or [])} report rows, "
        f"{len(raw.get('disruptions') or {})} disruptions in response, "
        f"{len(state['disruptions'])} known disruption IDs)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
