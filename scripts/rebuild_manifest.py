"""rebuild data/manifest.json from data/ground_truth/*.json and data/images/{public,personal}/*."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "environments" / "analog_instrument" / "data"
GT_DIR = DATA / "ground_truth"
IMG_DIRS = [DATA / "images" / "public", DATA / "images" / "personal"]

manifest = []
for gt_path in sorted(GT_DIR.glob("*.json")):
    if gt_path.name.startswith("_"):
        continue
    gt = json.loads(gt_path.read_text())
    image = gt["image"]
    # find image in public or personal
    img_path = None
    img_subdir = None
    for d in IMG_DIRS:
        p = d / image
        if p.exists():
            img_path = p
            img_subdir = d.name
            break
    if not img_path:
        print(f"MISSING IMAGE: {image} (gt={gt_path.name})")
        continue
    manifest.append({
        "image": f"{img_subdir}/{image}",
        "ground_truth_file": gt_path.name,
        "instrument_type": gt["instrument_type"],
        "difficulty": gt.get("difficulty", "medium"),
        "tags": gt.get("tags", []),
        "source_kind": "personal" if img_subdir == "personal" else "public",
    })

out = DATA / "manifest.json"
out.write_text(json.dumps(manifest, indent=2))
print(f"wrote {out} with {len(manifest)} entries")

# breakdown
by_type = {}
by_kind = {"public": 0, "personal": 0}
for m in manifest:
    by_type[m["instrument_type"]] = by_type.get(m["instrument_type"], 0) + 1
    by_kind[m["source_kind"]] += 1
print("\nby type:")
for t, n in sorted(by_type.items()):
    print(f"  {t}: {n}")
print(f"\npublic={by_kind['public']}, personal={by_kind['personal']}")
