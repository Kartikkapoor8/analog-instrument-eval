"""aggressive v0.2 candidate fetch.

strategy: pull many candidates from each Wikimedia category, save to
_candidates/ for manual review. category-based fetch tends to give actual
photos of the instrument vs keyword search which often returns book
diagrams.

after running this, manually inspect candidates and promote verified ones.
"""
import json, os, time, urllib.parse, requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAND = ROOT / "environments" / "analog_instrument" / "data" / "images" / "_candidates_v02"
CAND.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "analog-instrument-eval/0.2 (research)"}


def get_retry(url, params, tries=5):
    for i in range(tries):
        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if r.status_code == 429:
            time.sleep(8 * (i + 1)); continue
        r.raise_for_status()
        return r


def list_category(cat, n=30, cmcontinue=None):
    url = "https://commons.wikimedia.org/w/api.php"
    params = {"action": "query", "format": "json", "list": "categorymembers",
              "cmtitle": "Category:" + cat, "cmtype": "file", "cmlimit": n}
    if cmcontinue:
        params["cmcontinue"] = cmcontinue
    r = get_retry(url, params)
    data = r.json()
    titles = [m["title"] for m in data["query"]["categorymembers"]]
    cont = data.get("continue", {}).get("cmcontinue")
    return titles, cont


def info(titles):
    url = "https://commons.wikimedia.org/w/api.php"
    out = []
    # batch 10
    for i in range(0, len(titles), 10):
        chunk = titles[i:i+10]
        params = {"action": "query", "format": "json", "titles": "|".join(chunk),
                  "prop": "imageinfo", "iiprop": "url|extmetadata|size",
                  "iiurlwidth": "1024"}
        r = get_retry(url, params)
        for pid, p in r.json()["query"]["pages"].items():
            if "imageinfo" not in p:
                continue
            ii = p["imageinfo"][0]
            # skip if too small or non-photo
            w = ii.get("width", 0)
            h = ii.get("height", 0)
            if w < 500 or h < 500:
                continue
            meta = ii.get("extmetadata", {})
            out.append({"title": p["title"],
                        "url": ii.get("thumburl") or ii["url"],
                        "description": (meta.get("ImageDescription", {}).get("value", "") or "")[:300],
                        "page": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(p["title"]),
                        "size": (w, h)})
        time.sleep(1)
    return out


def download(item, slot):
    safe = item["title"].replace(" ", "_").replace("File:", "")[:60]
    safe = safe.replace("/", "_").replace("\\", "_").replace('"', "").replace("'", "")
    if "." not in safe:
        safe += ".jpg"
    fname = f"{slot:04d}_{safe}"
    path = CAND / fname
    if path.exists():
        return path
    for tr in range(4):
        try:
            r = requests.get(item["url"], headers=HEADERS, timeout=60)
            if r.status_code == 429:
                time.sleep(8 * (tr + 1)); continue
            r.raise_for_status()
            path.write_bytes(r.content)
            return path
        except requests.exceptions.RequestException:
            if tr == 3:
                return None
            time.sleep(3)


# target categories with the type of image we want
CATS = {
    "clock": ["Analog_clocks", "Wristwatches", "Wall_clocks", "Station_clocks",
              "Mantel_clocks"],
    "pressure_gauge": ["Pressure_gauges", "Bourdon_gauges",
                        "Steam_pressure_gauges", "Air_pressure_gauges"],
    "thermometer": ["Dial_thermometers", "Bimetal_thermometers",
                    "Mercury_thermometers"],
    "ammeter_voltmeter": ["Analog_voltmeters", "Analog_ammeters", "Galvanometers",
                          "Panel_meters"],
    "tachometer": ["Tachometers", "Tachometer_dials"],
    "scale": ["Spring_scales", "Hanging_scales", "Postal_scales",
              "Bathroom_scales"],
    "oscilloscope": ["Oscilloscopes", "Analog_oscilloscopes"],
    "speedometer": ["Speedometers", "Speedometer_dials"],
    "barometer": ["Aneroid_barometers", "Mercury_barometers"],
}

candidates = []
slot = 3000
for group, cats in CATS.items():
    print(f"\n=== {group} ===")
    for cat in cats:
        try:
            print(f"  [{cat}]")
            titles, cont = list_category(cat, n=30)
            print(f"    {len(titles)} titles")
            items = info(titles)
            print(f"    {len(items)} infos (filtered to >=500x500)")
            for it in items[:15]:
                p = download(it, slot)
                slot += 1
                if p:
                    candidates.append({"group": group, "category": cat, **it,
                                       "path": str(p.relative_to(ROOT))})
            time.sleep(2)
        except Exception as e:
            print(f"    fail: {e}")
            time.sleep(5)

(ROOT / "scripts" / "candidates_v02.json").write_text(json.dumps(candidates, indent=2))
print(f"\nTOTAL: {len(candidates)} candidates downloaded to {CAND}")
