"""fetch additional candidate images from wikimedia commons.
this script is used to expand the public set. images need MANUAL verification
of ground truth after download - we save them to data/images/_candidates and
review them before promoting to data/images/public.
"""
import json, os, time, urllib.parse, requests, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_DATA = ROOT / "environments" / "analog_instrument" / "data"
CAND_DIR = ENV_DATA / "images" / "_candidates"
CAND_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "analog-instrument-eval/0.1 (research; kartikkapoor@github)"}


def get_with_retry(url, params, tries=5):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=30)
            if r.status_code == 429:
                time.sleep(8 * (i + 1))
                continue
            r.raise_for_status()
            return r
        except requests.exceptions.HTTPError:
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))


def search(query, n=6):
    url = "https://commons.wikimedia.org/w/api.php"
    params = {"action": "query", "format": "json", "list": "search",
              "srsearch": query + " filetype:bitmap", "srnamespace": "6", "srlimit": n}
    r = get_with_retry(url, params)
    return [h["title"] for h in r.json()["query"]["search"]]


def info(titles):
    url = "https://commons.wikimedia.org/w/api.php"
    params = {"action": "query", "format": "json", "titles": "|".join(titles),
              "prop": "imageinfo", "iiprop": "url|extmetadata|size",
              "iiurlwidth": "1024"}
    r = get_with_retry(url, params)
    out = []
    for pid, p in r.json()["query"]["pages"].items():
        if "imageinfo" not in p:
            continue
        ii = p["imageinfo"][0]
        meta = ii.get("extmetadata", {})
        out.append({
            "title": p["title"],
            "url": ii.get("thumburl") or ii["url"],
            "description": (meta.get("ImageDescription", {}).get("value", "") or "")[:400],
            "page": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(p["title"]),
        })
    return out


def download(item, slot):
    safe = item["title"].replace(" ", "_").replace("File:", "")[:60]
    if "." not in safe:
        safe += ".jpg"
    fname = f"{slot:03d}_{safe}"
    path = CAND_DIR / fname
    if path.exists():
        return path
    for tr in range(4):
        r = requests.get(item["url"], headers=HEADERS, timeout=60)
        if r.status_code == 429:
            time.sleep(8 * (tr + 1))
            continue
        r.raise_for_status()
        path.write_bytes(r.content)
        return path


# focused queries — emphasize OFF-ZERO needle positions
QUERIES = [
    ("pressure_gauge_psi_active", "pressure gauge dial reading psi compressed"),
    ("pressure_gauge_bar", "bourdon tube pressure gauge bar"),
    ("manometer_running", "industrial manometer needle reading"),
    ("steam_gauge", "steam pressure gauge dial vintage"),
    ("water_pressure", "water pressure gauge plumbing"),
    ("ammeter_dial", "panel ammeter dial reading current"),
    ("voltmeter_dial", "panel voltmeter analog needle"),
    ("galvanometer", "galvanometer needle deflection"),
    ("tire_gauge", "tire pressure gauge analog dial reading"),
    ("speedometer_car", "car speedometer dashboard cluster mph"),
    ("speedometer_motorcycle", "motorcycle speedometer needle"),
    ("oven_thermometer", "oven thermometer dial fahrenheit"),
    ("outdoor_thermometer", "outdoor analog thermometer fahrenheit dial garden"),
    ("clock_train_station", "train station analog clock"),
    ("clock_church", "church tower clock face"),
    ("clock_grandfather", "grandfather clock face roman numerals"),
    ("hygrometer", "hygrometer humidity dial relative"),
    ("barometer", "aneroid barometer face dial reading"),
    ("vacuum_gauge", "vacuum gauge reading needle"),
    ("kitchen_scale", "kitchen analog spring scale grams"),
]


def main():
    candidates = []
    for slot, (label, q) in enumerate(QUERIES):
        base = 1000 + slot * 10
        print(f"[{label}] {q}")
        try:
            titles = search(q, n=4)
            items = info(titles) if titles else []
            for j, it in enumerate(items[:2]):
                try:
                    path = download(it, base + j)
                    if path:
                        print(f"  -> {path.name}")
                        candidates.append({"label": label, **it,
                                           "path": str(path.relative_to(ROOT))})
                except Exception as e:
                    print(f"  dl fail: {e}")
            time.sleep(2.5)
        except Exception as e:
            print(f"  search fail: {e}")
            time.sleep(5)
    out = ROOT / "scripts" / "candidates.json"
    out.write_text(json.dumps(candidates, indent=2))
    print(f"\n{len(candidates)} candidates saved to {out}")


if __name__ == "__main__":
    main()
