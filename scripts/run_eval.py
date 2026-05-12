"""run cross-model eval on public images. saves raw samples + aggregated metrics.

usage:
    ANTHROPIC_API_KEY=... python3 scripts/run_eval.py --model opus --n 8
    python3 scripts/run_eval.py --model all --n 8       # all three models
"""
import argparse, base64, json, os, sys, time
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parents[1]
ENV_DIR = ROOT / "environments" / "analog_instrument"
DATA = ENV_DIR / "data"
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

sys.path.insert(0, str(ENV_DIR))
import importlib.util
spec = importlib.util.spec_from_file_location("ai_mod", ENV_DIR / "analog_instrument.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

MODELS = {
    "opus": ("claude-opus-4-6", 15.0 / 1_000_000, 75.0 / 1_000_000),
    "sonnet": ("claude-sonnet-4-6", 3.0 / 1_000_000, 15.0 / 1_000_000),
    "haiku": ("claude-haiku-4-5", 1.0 / 1_000_000, 5.0 / 1_000_000),
}

SYSTEM_PROMPT = mod.SYSTEM_PROMPT


def encode_image(path):
    ext = path.suffix.lstrip(".").lower()
    media = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
             "webp": "image/webp"}.get(ext, "image/jpeg")
    with open(path, "rb") as f:
        return media, base64.standard_b64encode(f.read()).decode()


def run_one_model(model_key, model_id, price_in, price_out, manifest, n_samples,
                  cost_cap, temp=1.0):
    client = anthropic.Anthropic()
    raw_path = RESULTS / f"raw_samples_{model_key}.json"
    raw = json.loads(raw_path.read_text()) if raw_path.exists() else {}
    cost = 0.0
    total_in = total_out = 0

    for entry in manifest:
        img_rel = entry["image"]   # public/clock_001.png
        img_path = DATA / "images" / img_rel
        gt_path = DATA / "ground_truth" / entry["ground_truth_file"]
        if not img_path.exists() or not gt_path.exists():
            continue
        gt = json.loads(gt_path.read_text())
        img_name = img_path.name
        if img_name not in raw:
            raw[img_name] = []
        media, b64 = encode_image(img_path)
        needed = n_samples - len(raw[img_name])

        for s in range(needed):
            if cost >= cost_cap:
                print(f"[{model_key}] COST CAP HIT ${cost:.2f}, stopping")
                return raw, cost, total_in, total_out
            try:
                resp = client.messages.create(
                    model=model_id,
                    max_tokens=200,
                    temperature=temp,
                    system=SYSTEM_PROMPT,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64",
                                                          "media_type": media,
                                                          "data": b64}},
                            {"type": "text", "text": "Read this instrument."},
                        ],
                    }],
                )
                text = "".join(b.text for b in resp.content if hasattr(b, "text"))
                in_tok = resp.usage.input_tokens
                out_tok = resp.usage.output_tokens
                total_in += in_tok
                total_out += out_tok
                step_cost = in_tok * price_in + out_tok * price_out
                cost += step_cost
                raw[img_name].append({"text": text, "in_tok": in_tok,
                                       "out_tok": out_tok, "cost": step_cost})
                print(f"[{model_key}] {img_name} s{len(raw[img_name])}: {text[:60]!r}... [${cost:.3f}]")
                # save incrementally
                raw_path.write_text(json.dumps(raw, indent=2))
            except anthropic.RateLimitError:
                print(f"[{model_key}] rate limit, sleeping 10s")
                time.sleep(10)
            except Exception as e:
                print(f"[{model_key}] api error: {e}")
                time.sleep(3)
        time.sleep(0.3)
    return raw, cost, total_in, total_out


def score_one_model(model_key, manifest, gt_dir):
    """compute pass@1, pass@8, calibration metrics from raw samples"""
    raw = json.loads((RESULTS / f"raw_samples_{model_key}.json").read_text())
    results = {"per_image": [], "per_type": {}, "overall": {},
               "confidence": {"correct_high": 0, "correct_med": 0, "correct_low": 0,
                              "wrong_high": 0, "wrong_med": 0, "wrong_low": 0},
               "format_compliance": 0, "format_total": 0,
               "deterministic_wrong": []}
    n_p1 = n_p8 = 0
    n_samples_ok = 0
    n_samples_total = 0
    per_type_acc = {}
    for entry in manifest:
        img_rel = entry["image"]
        img_name = Path(img_rel).name
        if img_name not in raw:
            continue
        gt = json.loads((gt_dir / entry["ground_truth_file"]).read_text())
        samples = raw[img_name]
        correct = 0
        sample_readings = []
        first_correct = False
        diags = []
        for i, s in enumerate(samples):
            pred = mod.parse_completion(s["text"])
            parsed = pred is not None
            if parsed:
                results["format_compliance"] += 1
            results["format_total"] += 1
            ok = (mod.score_reading(pred, gt) == 1.0) if parsed else False
            if ok:
                correct += 1
                n_samples_ok += 1
            n_samples_total += 1
            if i == 0:
                first_correct = ok
            # collect reading for determinism check
            reading_str = ""
            if pred:
                reading_str = str(pred.get("reading", "")) + "|" + str(pred.get("unit", ""))
            sample_readings.append(reading_str)
            # confidence tracking
            if pred:
                c = str(pred.get("confidence", "")).strip().lower()
                key_prefix = "correct" if ok else "wrong"
                if c in ("high", "medium", "low"):
                    suffix = {"high": "high", "medium": "med", "low": "low"}[c]
                    results["confidence"][f"{key_prefix}_{suffix}"] += 1
            diags.append({"reading": pred.get("reading") if pred else None,
                          "unit": pred.get("unit") if pred else None,
                          "confidence": pred.get("confidence") if pred else None,
                          "correct": ok})
        n_p1 += int(first_correct)
        pass8 = correct > 0
        n_p8 += int(pass8)
        # determinism check: same wrong answer in ALL samples
        all_wrong = correct == 0 and len(samples) > 1
        all_same = len(set(sample_readings)) == 1 and sample_readings[0] != ""
        if all_wrong and all_same:
            results["deterministic_wrong"].append({
                "image": img_name,
                "type": gt["instrument_type"],
                "gt": gt["reading"],
                "predicted": sample_readings[0],
            })
        results["per_image"].append({
            "image": img_name,
            "type": gt["instrument_type"],
            "gt": gt["reading"],
            "unit": gt.get("unit"),
            "n_correct": correct,
            "n_total": len(samples),
            "pass1": first_correct,
            "pass8": pass8,
            "all_samples_same": all_same,
            "all_wrong_deterministic": all_wrong and all_same,
            "sample_diagnostics": diags,
        })
        t = mod.normalize_type(gt["instrument_type"])
        per_type_acc.setdefault(t, {"n": 0, "p1": 0, "p8": 0,
                                     "samples_ok": 0, "samples_total": 0})
        per_type_acc[t]["n"] += 1
        per_type_acc[t]["p1"] += int(first_correct)
        per_type_acc[t]["p8"] += int(pass8)
        per_type_acc[t]["samples_ok"] += correct
        per_type_acc[t]["samples_total"] += len(samples)
    n = len(results["per_image"])
    results["overall"] = {
        "n_images": n,
        "pass1": n_p1, "pass1_pct": round(100 * n_p1 / max(n, 1), 1),
        "pass8": n_p8, "pass8_pct": round(100 * n_p8 / max(n, 1), 1),
        "samples_ok": n_samples_ok, "samples_total": n_samples_total,
        "sample_acc_pct": round(100 * n_samples_ok / max(n_samples_total, 1), 1),
        "format_compliance_pct": round(100 * results["format_compliance"] /
                                       max(results["format_total"], 1), 1),
        "n_deterministic_wrong": len(results["deterministic_wrong"]),
    }
    for t in per_type_acc:
        v = per_type_acc[t]
        v["p1_pct"] = round(100 * v["p1"] / v["n"], 1)
        v["p8_pct"] = round(100 * v["p8"] / v["n"], 1)
        v["samples_pct"] = round(100 * v["samples_ok"] / v["samples_total"], 1)
    results["per_type"] = per_type_acc
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="all", choices=["opus", "sonnet", "haiku", "all"])
    parser.add_argument("--n", type=int, default=8)
    parser.add_argument("--cost-cap", type=float, default=15.0)
    parser.add_argument("--skip-run", action="store_true",
                        help="only score existing raw samples")
    args = parser.parse_args()

    manifest = json.loads((DATA / "manifest.json").read_text())
    gt_dir = DATA / "ground_truth"
    print(f"manifest: {len(manifest)} images")

    targets = [args.model] if args.model != "all" else ["opus", "sonnet", "haiku"]
    per_model_cost = args.cost_cap / len(targets)
    all_results = {}
    grand_cost = 0.0

    for mk in targets:
        model_id, p_in, p_out = MODELS[mk]
        if not args.skip_run:
            print(f"\n=== {mk} ({model_id}) budget=${per_model_cost:.2f} ===")
            _, cost, in_tok, out_tok = run_one_model(
                mk, model_id, p_in, p_out, manifest, args.n,
                cost_cap=per_model_cost,
            )
            grand_cost += cost
            print(f"[{mk}] cost=${cost:.3f}, in={in_tok}, out={out_tok}")
        print(f"\n=== scoring {mk} ===")
        res = score_one_model(mk, manifest, gt_dir)
        all_results[mk] = res
        print(f"[{mk}] pass@1={res['overall']['pass1_pct']}%, "
              f"pass@8={res['overall']['pass8_pct']}%, "
              f"format={res['overall']['format_compliance_pct']}%, "
              f"determ_wrong={res['overall']['n_deterministic_wrong']}")

    out = {"models": all_results, "manifest_size": len(manifest),
           "total_cost_usd": grand_cost}
    (RESULTS / "eval_full.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {RESULTS}/eval_full.json")
    print(f"grand cost: ${grand_cost:.3f}")


if __name__ == "__main__":
    main()
