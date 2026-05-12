"""fetch images from specific wikimedia categories that contain real instrument photos"""
import json, os, time, urllib.parse, requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAND = ROOT / "environments" / "analog_instrument" / "data" / "images" / "_candidates"
CAND.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "analog-instrument-eval/0.1"}


def get_with_retry(url, params, tries=5):
    for i in range(tries):
        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if r.status_code == 429:
            time.sleep(8 * (i + 1))
            continue
        r.raise_for_status()
        return r
    raise RuntimeError("exhausted")


def list_category(cat, n=20):
    """list files in a commons category"""
    url = "https://commons.wikimedia.org/w/api.php"
    params = {"action": "query", "format": "json", "list": "categorymembers",
              "cmtitle": "Category:" + cat, "cmtype": "file", "cmlimit": n}
    r = get_with_retry(url, params)
    return [m["title"] for m in r.json()["query"]["categorymembers"]]


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
        out.append({"title": p["title"],
                    "url": ii.get("thumburl") or ii["url"],
                    "description": (meta.get("ImageDescription", {}).get("value", "") or "")[:300],
                    "page": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(p["title"])})
    return out


def download(item, slot):
    safe = item["title"].replace(" ", "_").replace("File:", "")[:60]
    if "." not in safe: safe += ".jpg"
    fname = f"{slot:04d}_{safe}"
    path = CAND / fname
    if path.exists(): return path
    for tr in range(4):
        r = requests.get(item["url"], headers=HEADERS, timeout=60)
        if r.status_code == 429:
            time.sleep(8 * (tr + 1)); continue
        r.raise_for_status()
        path.write_bytes(r.content)
        return path


CATEGORIES = [
    "Analog_clocks",
    "Pressure_gauges",
    "Aneroid_barometers",
    "Bourdon_gauges",
    "Speedometers",
    "Tachometers",
    "Analog_voltmeters",
    "Analog_ammeters",
    "Hygrometers",
    "Bimetal_thermometers",
    "Dial_thermometers",
    "Spring_scales",
    "Kitchen_scales",
]

candidates = []
for ci, cat in enumerate(CATEGORIES):
    base = 2000 + ci * 50
    print(f"[{cat}]")
    try:
        titles = list_category(cat, n=6)
        time.sleep(1.5)
        # batch info in chunks of 5
        items = []
        for i in range(0, len(titles), 5):
            items.extend(info(titles[i:i+5]))
            time.sleep(1.5)
        for j, it in enumerate(items[:5]):
            try:
                p = download(it, base + j)
                if p:
                    print(f"  -> {p.name}")
                    candidates.append({"category": cat, **it, "path": str(p.relative_to(ROOT))})
                time.sleep(0.5)
            except Exception as e:
                print(f"  dl fail: {e}")
        time.sleep(2)
    except Exception as e:
        print(f"  cat fail: {e}")
        time.sleep(5)

(ROOT / "scripts" / "candidates_cats.json").write_text(json.dumps(candidates, indent=2))
print(f"\n{len(candidates)} from categories")
